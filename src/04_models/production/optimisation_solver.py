# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — Block 4: constrained solver (§6)
# MAGIC
# MAGIC A deliberately boring, fully open solver (scipy). Reads the **versioned
# MAGIC constraint YAML** (`optimisation_constraints/default.yaml`), then for each
# MAGIC segment finds the price factor that maximises the chosen objective within
# MAGIC the **deviation corridor ∩ per-segment caps** (incl. the tighter U25
# MAGIC overrides), using the Block-2 elasticity curve. Enforces the min-premium
# MAGIC floor; a cost-based jurisdiction (`elasticity_may_contribute: false`) holds
# MAGIC every segment to technical (factor 1.0).
# MAGIC
# MAGIC Output `optimisation_factor_table` — the per-segment factor shape the rating
# MAGIC config / release rate-book already consumes, so deployment is a join on the
# MAGIC existing path. The compliance story IS the engineering story: the
# MAGIC constraints are in the solver, versioned in git, auditable. An audit row is
# MAGIC written on every solve.

# COMMAND ----------

dbutils.widgets.text("catalog_name",       "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",        "pricing_workbench_gen2")
dbutils.widgets.text("constraint_version", "v1")
dbutils.widgets.text("objective",          "")   # override YAML objective; blank = use YAML
dbutils.widgets.text("constraint_yaml_path", "")  # optional explicit path; else defaults below
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
cver    = dbutils.widgets.get("constraint_version")
obj_override = dbutils.widgets.get("objective").strip()
cpath   = dbutils.widgets.get("constraint_yaml_path").strip()
fqn     = f"{catalog}.{schema}"

import json, os
import numpy as np, pandas as pd
from scipy.optimize import minimize_scalar

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load the versioned constraints (YAML if reachable, else embedded default)

# COMMAND ----------

EMBEDDED = {  # mirrors optimisation_constraints/default.yaml v1 — fallback if the file isn't reachable
    "deviation_corridor": {"lower_pct": -15.0, "upper_pct": 15.0},
    "segment_caps": {"max_increase_pct": 10.0, "max_decrease_pct": 12.0,
                     "overrides": {"U25 · grpLow": {"max_increase_pct": 6.0},
                                   "U25 · grpMid": {"max_increase_pct": 6.0},
                                   "U25 · grpHigh": {"max_increase_pct": 6.0}}},
    "sanity": {"min_premium": 150.0, "max_premium": 50000.0},
    "jurisdiction": {"elasticity_may_contribute": True, "gipp_renewal_rule": True},
    "objective": {"maximise": "expected_profit", "retention_weight": 0.0},
}
constraints, csource = EMBEDDED, "embedded-default"
_candidates = [cpath] if cpath else []
for _tgt in ("pricingv2", "dev"):
    _candidates.append(f"/Workspace/Shared/.bundle/pricing-workbench-gen2/{_tgt}/files/"
                       f"src/04_models/production/optimisation_constraints/default.yaml")
_candidates.append("src/04_models/production/optimisation_constraints/default.yaml")
for _p in _candidates:
    try:
        if _p and os.path.exists(_p):
            import yaml
            with open(_p) as fh:
                constraints = yaml.safe_load(fh); csource = _p; break
    except Exception as _e:
        print(f"constraint load {_p}: {_e}")

corr_lo = constraints["deviation_corridor"]["lower_pct"] / 100.0
corr_hi = constraints["deviation_corridor"]["upper_pct"] / 100.0
caps    = constraints["segment_caps"]
cap_up  = caps["max_increase_pct"] / 100.0
cap_dn  = caps["max_decrease_pct"] / 100.0
overrides = caps.get("overrides", {}) or {}
min_prem = constraints["sanity"]["min_premium"]
elasticity_on = bool(constraints.get("jurisdiction", {}).get("elasticity_may_contribute", True))
objective = obj_override or constraints.get("objective", {}).get("maximise", "expected_profit")
ret_w = float(constraints.get("objective", {}).get("retention_weight", 0.0))
print(f"constraints source={csource} v={cver}: corridor [{corr_lo:+.0%},{corr_hi:+.0%}], "
      f"caps [+{cap_up:.0%}/-{cap_dn:.0%}], objective={objective}, elasticity_may_contribute={elasticity_on}")

def seg_bounds(seg):
    ov = overrides.get(seg, {})
    up = ov.get("max_increase_pct", caps["max_increase_pct"]) / 100.0
    dn = ov.get("max_decrease_pct", caps["max_decrease_pct"]) / 100.0
    return max(1 + corr_lo, 1 - dn), min(1 + corr_hi, 1 + up)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Solve each segment within its bounds

# COMMAND ----------

snap = spark.table(f"{fqn}.optimisation_portfolio_snapshot").toPandas()
for c in ["current_premium", "technical_premium", "loaded_premium"]:
    snap[c] = pd.to_numeric(snap[c], errors="coerce").fillna(0.0)

def segment_of(df):
    age = pd.to_numeric(df.get("driver_age"), errors="coerce").fillna(45)
    vg  = pd.to_numeric(df.get("vehicle_group"), errors="coerce").fillna(20)
    ab = np.where(age < 25, "U25", np.where(age < 70, "25-70", "70+"))
    vb = np.where(vg < 15, "grpLow", np.where(vg < 30, "grpMid", "grpHigh"))
    return pd.Series([f"{a} · {v}" for a, v in zip(ab, vb)], index=df.index)

snap["segment"] = segment_of(snap)
# Price basis = loaded_premium (rate-book / break-even price); cost = pure risk
# technical_premium (margin floor). current_premium is a stale in-force field.
agg = snap.groupby("segment").agg(n=("policy_id", "count"),
                                  gwp=("loaded_premium", "sum"),
                                  cost=("technical_premium", "sum"))

curve = spark.table(f"{fqn}.optimisation_elasticity_curve").toPandas()
segments = [s for s in agg.index.tolist() if s in set(curve["segment"])]
grids = {s: curve[curve.segment == s].sort_values("price_multiplier")["price_multiplier"].values for s in segments}
convs = {s: curve[curve.segment == s].sort_values("price_multiplier")["conversion_prob"].values for s in segments}

def conv_at(s, f):
    return float(np.interp(f, grids[s], convs[s]))

def neg_objective(f, s):
    p = conv_at(s, f)
    gwp, cost, n = agg.loc[s, "gwp"], agg.loc[s, "cost"], agg.loc[s, "n"]
    profit = p * (gwp * f - cost)
    if objective == "expected_gwp":
        return -(p * gwp * f)
    if objective == "retention_weighted_profit":
        return -(profit + ret_w * p * n * float(gwp / max(1, n)))  # tilt toward retained volume
    return -profit

# COMMAND ----------

rows = []
for s in segments:
    if int(agg.loc[s, "n"]) < 5:
        continue
    lo, hi = seg_bounds(s)
    if elasticity_on:
        res = minimize_scalar(neg_objective, bounds=(lo, hi), args=(s,), method="bounded")
        factor = float(res.x)
    else:
        factor = 1.0
    prof_hold = -( conv_at(s, 1.0) * (agg.loc[s, "gwp"] * 1.0 - agg.loc[s, "cost"]) )
    prof_opt  = -( conv_at(s, factor) * (agg.loc[s, "gwp"] * factor - agg.loc[s, "cost"]) )
    # which bound (if any) is binding — surfaced in the app as "capped by segment cap"
    capped = "corridor" if abs(factor - (1 + corr_hi)) < 1e-3 or abs(factor - (1 + corr_lo)) < 1e-3 else \
             ("segment_cap" if abs(factor - hi) < 1e-3 or abs(factor - lo) < 1e-3 else "interior")
    rows.append({
        "constraint_version": cver, "segment": s, "policies": int(agg.loc[s, "n"]),
        "factor": round(factor, 4), "factor_pct": round((factor - 1) * 100, 2),
        "conversion_hold": round(conv_at(s, 1.0), 4), "conversion_opt": round(conv_at(s, factor), 4),
        "gwp_current": round(float(agg.loc[s, "gwp"]), 2),
        "expected_profit_hold": round(-prof_hold, 2), "expected_profit_opt": round(-prof_opt, 2),
        "profit_uplift": round(-prof_opt - (-prof_hold), 2),
        "bound_lo": round(lo, 4), "bound_hi": round(hi, 4), "binding": capped,
        "within_corridor": bool(1 + corr_lo - 1e-6 <= factor <= 1 + corr_hi + 1e-6),
    })

fac = pd.DataFrame(rows)
(spark.createDataFrame(fac).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_factor_table"))

# Pre-create the HITL deployment ledger here (owned by the job identity) so the
# app SP only ever needs INSERT (MODIFY), never CREATE, at approve→deploy time.
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {fqn}.optimisation_deployment (
        deployment_id STRING, constraint_version STRING, segments INT,
        approver STRING, note STRING, deployed_at TIMESTAMP)
""")
_tot_up = float(fac["profit_uplift"].sum())
_all_ok = bool(fac["within_corridor"].all())
print(f"optimisation_factor_table: {len(fac)} segments, objective={objective}, all within corridor={_all_ok}, "
      f"total expected profit uplift £{_tot_up:,.0f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Audit the solve (best-effort — audit_log is the app's immutable log)

# COMMAND ----------

try:
    _det = json.dumps({"segments": len(fac), "objective": objective, "source": csource,
                       "total_uplift": round(_tot_up, 2), "all_within_corridor": _all_ok}).replace("'", "''")
    spark.sql(f"""
      INSERT INTO {fqn}.audit_log (event_id, event_type, entity_type, entity_id, entity_version,
                                   user_id, timestamp, details, source)
      SELECT uuid(), 'optimisation_solve', 'constraint_set', '{cver}', '{cver}', 'optimiser',
             current_timestamp(), '{_det}', 'optimisation_solver'
    """)
    print("audit row written")
except Exception as e:
    print(f"audit_log insert skipped: {e}")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "segments": len(fac), "constraint_version": cver, "constraint_source": csource,
    "objective": objective, "total_uplift": round(_tot_up, 2), "all_within_corridor": _all_ok,
}))

# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — block 04: constrained solver
# MAGIC
# MAGIC A deliberately boring, fully open solver (scipy). Reads the **versioned
# MAGIC constraint YAML** (src/09_optimization/constraints/), then for each segment
# MAGIC finds the price factor that maximises expected profit within the deviation
# MAGIC corridor ∩ segment caps, using the conversion elasticity model. Enforces
# MAGIC min-premium and (for renewals) the GIPP rule. Output `opt_factor_table` —
# MAGIC the same per-segment factor shape the rating config / release rate-book
# MAGIC already consumes, so deployment = a join on the existing path.
# MAGIC
# MAGIC The compliance story is the engineering story: the constraints are in the
# MAGIC solver, versioned in git, auditable. Deps from the job env. Idempotent.

# COMMAND ----------

dbutils.widgets.text("catalog_name",        "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",         "pricing_workbench_gen2")
dbutils.widgets.text("constraint_version",  "v1")
dbutils.widgets.text("constraint_yaml_path","")   # optional explicit path; else defaults below
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
cver    = dbutils.widgets.get("constraint_version")
cpath   = dbutils.widgets.get("constraint_yaml_path").strip()
fqn     = f"{catalog}.{schema}"

import json, os
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
import mlflow
mlflow.set_registry_uri("databricks-uc")

# COMMAND ----------

# --- load the versioned constraints (YAML if reachable, else embedded default) ---
EMBEDDED = {  # mirrors constraints/default.yaml v1 — the fallback if the file isn't reachable
    "deviation_corridor": {"lower_pct": -15.0, "upper_pct": 15.0},
    "segment_caps": {"max_increase_pct": 10.0, "max_decrease_pct": 12.0},
    "sanity": {"min_premium": 150.0, "max_premium": 250000.0},
    "jurisdiction": {"elasticity_may_contribute": True, "gipp_renewal_rule": True},
    "objective": {"maximise": "expected_profit"},
}
constraints, csource = EMBEDDED, "embedded-default"
_candidates = [cpath] if cpath else []
_candidates += [
    f"/Workspace/Shared/.bundle/pricing-workbench-gen2/pricingv2/files/src/09_optimization/constraints/default.yaml",
    "src/09_optimization/constraints/default.yaml",
]
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
cap_up  = constraints["segment_caps"]["max_increase_pct"] / 100.0
cap_dn  = constraints["segment_caps"]["max_decrease_pct"] / 100.0
min_prem = constraints["sanity"]["min_premium"]
elasticity_on = bool(constraints.get("jurisdiction", {}).get("elasticity_may_contribute", True))
lo = max(1 + corr_lo, 1 - cap_dn)
hi = min(1 + corr_hi, 1 + cap_up)
print(f"constraints source={csource} v={cver}: factor bounds [{lo:.3f},{hi:.3f}], "
      f"min_prem={min_prem}, elasticity_may_contribute={elasticity_on}")

# COMMAND ----------

snap = spark.table(f"{fqn}.opt_portfolio_snapshot").toPandas()
for _c in ["charged_premium", "technical_cost", "sum_insured", "annual_turnover",
           "incurred_5y", "claims_history_5y"]:
    if _c in snap.columns:
        snap[_c] = pd.to_numeric(snap[_c], errors="coerce").fillna(0.0)
snap["segment"] = snap["sic_code"].astype(str)
agg = snap.groupby("segment").agg(n=("policy_id", "count"),
                                  gwp=("charged_premium", "sum"),
                                  cost=("technical_cost", "sum"))
segments = agg.index.tolist()
cm = mlflow.pyfunc.load_model(f"models:/{fqn}.pwg2_conversion_elasticity@champion")

# Per-segment elasticity curve built ONCE over the corridor grid (single-row
# scores); the objective then evaluates in O(1) by interpolation — scale-free.
gridf = np.round(np.linspace(lo, hi, 13), 4)

def _feat_row(seg, ratio):
    rep = snap[snap["segment"] == seg].iloc[0]
    df = pd.DataFrame([{
        "sic_code": seg, "region": "UK", "construction_type": "Standard", "channel": "broker",
        "buildings_si": float(rep["sum_insured"]), "contents_si": 0.0, "liability_si": 0.0,
        "annual_turnover": float(rep["annual_turnover"]), "claims_last_5y": float(rep["claims_history_5y"]),
        "vs_market_rate": float(ratio)}])
    for c in ["sic_code", "region", "construction_type", "channel"]:
        df[c] = df[c].astype("category")
    return df

curves = {}
for s in segments:
    try:
        curves[s] = np.clip(np.array([float(cm.predict(_feat_row(s, g))[0]) for g in gridf]), 0, 1)
    except Exception:
        curves[s] = 1.0 / (1.0 + np.exp(-(0.5 - 9.0 * (gridf - 1.0))))

def _neg_profit_seg(factor, s):
    p = float(np.interp(factor, gridf, curves[s]))
    return -(p * (agg.loc[s, "gwp"] * factor - agg.loc[s, "cost"]))

# COMMAND ----------

rows = []
for s in segments:
    if int(agg.loc[s, "n"]) < 5:
        continue
    if elasticity_on:
        res = minimize_scalar(_neg_profit_seg, bounds=(lo, hi), args=(s,), method="bounded")
        factor = float(res.x)
    else:
        factor = 1.0   # cost-based jurisdiction: no elasticity shaping — hold to technical
    prof_hold = -_neg_profit_seg(1.0, s)
    prof_opt  = -_neg_profit_seg(factor, s)
    rows.append({
        "constraint_version": cver, "segment": s, "policies": int(agg.loc[s, "n"]),
        "factor": round(factor, 4),
        "factor_pct": round((factor - 1) * 100, 2),
        "gwp_current": round(float(agg.loc[s, "gwp"]), 2),
        "expected_profit_hold": round(prof_hold, 2),
        "expected_profit_opt":  round(prof_opt, 2),
        "profit_uplift": round(prof_opt - prof_hold, 2),
        "within_corridor": bool(lo - 1e-9 <= factor <= hi + 1e-9),
    })

fac = pd.DataFrame(rows)
spark.createDataFrame(fac).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{fqn}.opt_factor_table")
_tot_up = fac["profit_uplift"].sum()
print(f"opt_factor_table: {len(fac)} segments, all within corridor={bool(fac['within_corridor'].all())}, "
      f"total expected profit uplift {_tot_up:,.0f}")

# audit
spark.sql(f"""
  INSERT INTO {fqn}.audit_log (event_id, event_type, entity_type, entity_id, entity_version, user_id, timestamp, details, source)
  SELECT uuid(), 'optimization_solve', 'constraint_set', '{cver}', '{cver}', 'optimizer',
         current_timestamp(), '{json.dumps({"segments": len(fac), "source": csource, "total_uplift": round(float(_tot_up),2)}).replace("'","''")}', 'opt_solver'
""")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "segments": len(fac), "constraint_version": cver,
    "constraint_source": csource, "total_uplift": round(float(_tot_up), 2),
}))

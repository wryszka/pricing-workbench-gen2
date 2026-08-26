# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — renewal solver with SOLVE-TIME GIPP (§6 renewals)
# MAGIC
# MAGIC Phase-1 optimised new business only; this adds the **renewal** book and makes
# MAGIC the UK **GIPP** rule (renewal never priced above equivalent new business)
# MAGIC **enforced in the solve**, not just monitored — closing the review's biggest
# MAGIC honesty gap.
# MAGIC
# MAGIC For each segment it picks the renewal rate-change factor that maximises
# MAGIC **retention-weighted margin**, using the governed `retention_elasticity_motor`
# MAGIC champion. GIPP holds **by construction, per policy**: the offered renewal is
# MAGIC `min(prior × factor, equivalent_new_business)` — so no policy can ever be
# MAGIC priced above its fresh new-business quote. The corridor + segment caps still
# MAGIC bound the move. Output `optimisation_renewal_factor_table`.

# COMMAND ----------

dbutils.widgets.text("catalog_name",       "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",        "pricing_workbench_gen2")
dbutils.widgets.text("constraint_version", "v1")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
cver    = dbutils.widgets.get("constraint_version")
fqn = f"{catalog}.{schema}"

import os, json
import numpy as np, pandas as pd
import mlflow
mlflow.set_registry_uri("databricks-uc")

CORR = 0.15
# renewal caps: renewals are anti-shock — tighter increase cap than new business.
REN_CAP_UP, REN_CAP_DN = 0.10, 0.12
try:
    for _p in [f"/Workspace/Shared/.bundle/pricing-workbench-gen2/pricingv2/files/"
               f"src/04_models/production/optimisation_constraints/default.yaml"]:
        if os.path.exists(_p):
            import yaml
            c = yaml.safe_load(open(_p))
            REN_CAP_UP = float(c.get("renewal", {}).get("max_year_on_year_increase_pct", 25)) / 100.0
            break
except Exception as e:
    print(f"constraint read fallback: {e}")

def segment_of(df):
    age = pd.to_numeric(df.get("driver_age"), errors="coerce").fillna(45)
    vg  = pd.to_numeric(df.get("vehicle_group"), errors="coerce").fillna(20)
    ab = np.where(age < 25, "U25", np.where(age < 70, "25-70", "70+"))
    vb = np.where(vg < 15, "grpLow", np.where(vg < 30, "grpMid", "grpHigh"))
    return pd.Series([f"{a} · {v}" for a, v in zip(ab, vb)], index=df.index)

RET_FEATURES = ["rate_change", "vs_technical", "tenure_years", "gipp_breach", "month_idx"]

# COMMAND ----------

# renewals + segment (join the snapshot for age/vehicle)
rr = spark.table(f"{fqn}.optimisation_renewal_response").toPandas()
snap = spark.table(f"{fqn}.optimisation_portfolio_snapshot").select(
    "policy_id", "driver_age", "vehicle_group").toPandas()
rr = rr.merge(snap, on="policy_id", how="left")
rr["segment"] = segment_of(rr)
for c in ["prior_premium", "equiv_new_business_premium", "technical_premium", "tenure_years", "vs_technical", "month_idx"]:
    rr[c] = pd.to_numeric(rr[c], errors="coerce")
rr = rr.dropna(subset=["prior_premium", "equiv_new_business_premium", "technical_premium"])
segments = sorted(rr["segment"].unique())

ret_m = mlflow.lightgbm.load_model(f"models:/{fqn}.retention_elasticity_motor@champion")

# per-segment retention curve over the renewal rate-change grid (gipp_breach=0:
# we are enforcing no breach, so the model sees a compliant offer).
lo, hi = 1 - min(CORR, REN_CAP_DN), 1 + min(CORR, REN_CAP_UP)
grid = np.round(np.linspace(lo, hi, 13), 4)

def seg_curve(seg):
    g = rr[rr.segment == seg]
    med = {"vs_technical": float(g["vs_technical"].median()),
           "tenure_years": float(g["tenure_years"].median()),
           "gipp_breach": 0.0, "month_idx": float(g["month_idx"].median())}
    X = pd.DataFrame([{**med, "rate_change": float(rc)} for rc in grid])[RET_FEATURES]
    return np.clip(ret_m.predict_proba(X)[:, 1], 0, 1)

# COMMAND ----------

rows = []
for s in segments:
    g = rr[rr.segment == s]
    if len(g) < 5:
        continue
    prior = g["prior_premium"].values
    enb   = g["equiv_new_business_premium"].values     # equivalent new business = the GIPP ceiling
    tech  = g["technical_premium"].values
    curve = seg_curve(s)

    def value_at(f):
        # GIPP BY CONSTRUCTION: offered = min(prior*f, equiv_new_business) per policy.
        offered = np.minimum(prior * f, enb)
        rc_eff  = offered / prior
        ret     = np.interp(rc_eff, grid, curve)          # retention at the effective change
        return float(np.sum(ret * (offered - tech))), float(ret.mean()), int(np.sum(offered > enb + 1e-6))

    best_f, best_val, best_ret, best_breach = 1.0, -np.inf, None, None
    for f in np.round(np.linspace(lo, hi, 31), 4):
        v, r, b = value_at(f)
        if v > best_val:
            best_f, best_val, best_ret, best_breach = f, v, r, b
    hold_val, hold_ret, _ = value_at(1.0)
    rows.append({
        "constraint_version": cver, "segment": s, "policies": int(len(g)),
        "renewal_factor": round(best_f, 4), "renewal_factor_pct": round((best_f - 1) * 100, 2),
        "retention_hold": round(hold_ret, 4), "retention_opt": round(best_ret, 4),
        "margin_hold": round(hold_val, 2), "margin_opt": round(best_val, 2),
        "margin_uplift": round(best_val - hold_val, 2),
        "gipp_breaches": int(best_breach),                # 0 by construction (the clamp)
        "gipp_enforced": True,
    })

fac = pd.DataFrame(rows)
(spark.createDataFrame(fac).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_renewal_factor_table"))
tot_breach = int(fac["gipp_breaches"].sum())
print(f"optimisation_renewal_factor_table: {len(fac)} segments, retention-weighted margin uplift "
      f"£{fac['margin_uplift'].sum():,.0f}, GIPP breaches {tot_breach} (enforced by per-policy clamp)")

# COMMAND ----------

try:
    _d = json.dumps({"segments": len(fac), "gipp_breaches": tot_breach,
                     "margin_uplift": round(float(fac["margin_uplift"].sum()), 2)}).replace("'", "''")
    spark.sql(f"""
      INSERT INTO {fqn}.audit_log (event_id, event_type, entity_type, entity_id, entity_version,
                                   user_id, timestamp, details, source)
      SELECT uuid(), 'optimisation_renewal_solve', 'renewal_factor_table', '{cver}', '{cver}',
             'optimiser', current_timestamp(), '{_d}', 'optimisation_renewal_solver'
    """)
except Exception as e:
    print(f"audit skipped: {e}")

dbutils.notebook.exit(json.dumps({"segments": len(fac), "gipp_breaches": tot_breach}))

# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — Block 2: elasticity models (§4)
# MAGIC
# MAGIC Two governed demand models on the motor behavioural layer Block 1 built,
# MAGIC plus the artifacts that make the modelling **defensible on screen**:
# MAGIC
# MAGIC  * **`conversion_elasticity_motor`** — P(bound) for new business. Price
# MAGIC    enters as the **ratio to technical price** (`vs_technical`) and as
# MAGIC    competitiveness (`vs_market`), **never raw** (raw price is endogenous to
# MAGIC    risk). **Monotonicity enforced** (`monotone_constraints`): conversion can
# MAGIC    only *fall* as price rises — the solver would otherwise exploit any
# MAGIC    non-monotone wrinkle.
# MAGIC  * **`retention_elasticity_motor`** — P(retained) for renewals, monotone in
# MAGIC    `rate_change` (offered / prior).
# MAGIC  * **`optimisation_elasticity_curve`** — per-segment price→conversion curve,
# MAGIC    surfaced in the app and reused in the talk track.
# MAGIC  * **Red-team panels** (§13): `optimisation_redteam_endogeneity` (why raw
# MAGIC    price gives the wrong elasticity) and `optimisation_param_recovery` (the
# MAGIC    pipeline recovers the *known injected* month-by-month elasticity — a
# MAGIC    parameter-recovery check on synthetic data).
# MAGIC
# MAGIC Models are plain LightGBM (not FE-wrapped) → they load cleanly on the driver
# MAGIC for the simulation/solver blocks. `@champion` alias set inline, mirroring
# MAGIC `demand_gbm_motor`.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
fqn = f"{catalog}.{schema}"

import numpy as np, pandas as pd
import lightgbm as lgb
import mlflow
from mlflow.models.signature import infer_signature
from sklearn.linear_model import LogisticRegression
mlflow.set_registry_uri("databricks-uc")
mlflow.autolog(disable=True)
np.random.seed(42)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Shared segment scheme
# MAGIC A legible 3×3 grid (driver-age band × vehicle-group band) — the segments the
# MAGIC simulation, solver, frontier and waterfall all key on. Defined once here and
# MAGIC replicated (identically) in the downstream blocks.

# COMMAND ----------

def segment_of(df: pd.DataFrame) -> pd.Series:
    age = pd.to_numeric(df.get("driver_age"), errors="coerce").fillna(45)
    vg  = pd.to_numeric(df.get("vehicle_group"), errors="coerce").fillna(20)
    age_band = np.where(age < 25, "U25", np.where(age < 70, "25-70", "70+"))
    veh_band = np.where(vg < 15, "grpLow", np.where(vg < 30, "grpMid", "grpHigh"))
    return pd.Series([f"{a} · {v}" for a, v in zip(age_band, veh_band)], index=df.index)

CONV_FEATURES = ["vs_technical", "vs_market", "driver_age", "no_claims_years",
                 "annual_mileage", "vehicle_value", "vehicle_group", "month_idx"]
# monotone: conversion can only FALL as vs_technical / vs_market rise; free elsewhere.
CONV_MONOTONE = [-1, -1, 0, 0, 0, 0, 0, 0]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Conversion elasticity — monotone in price

# COMMAND ----------

qr = spark.table(f"{fqn}.optimisation_quote_response").toPandas()
for c in CONV_FEATURES + ["converted"]:
    qr[c] = pd.to_numeric(qr[c], errors="coerce")
qr = qr.dropna(subset=CONV_FEATURES + ["converted"])
Xc, yc = qr[CONV_FEATURES], qr["converted"].astype(int)

conv = lgb.LGBMClassifier(
    n_estimators=300, learning_rate=0.05, num_leaves=31, min_child_samples=200,
    monotone_constraints=CONV_MONOTONE, subsample=0.8, colsample_bytree=0.9, verbose=-1)
conv.fit(Xc, yc)
_auc = None
try:
    from sklearn.metrics import roc_auc_score
    _auc = roc_auc_score(yc, conv.predict_proba(Xc)[:, 1])
except Exception:
    pass
print(f"conversion model: {len(Xc):,} quotes, train AUC {_auc:.3f}" if _auc else f"conversion model on {len(Xc):,} quotes")

with mlflow.start_run(run_name="conversion_elasticity_motor") as run:
    mlflow.log_params({"features": ",".join(CONV_FEATURES), "monotone": str(CONV_MONOTONE),
                       "n_train": len(Xc)})
    if _auc: mlflow.log_metric("train_auc", float(_auc))
    sig = infer_signature(Xc, conv.predict_proba(Xc)[:, 1])
    # mlflow.lightgbm (not .sklearn): newer mlflow serialises sklearn models via
    # skops, which rejects LightGBM's Booster as an "untrusted type". The native
    # lightgbm flavor round-trips the LGBMClassifier cleanly (predict_proba intact).
    mlflow.lightgbm.log_model(conv, artifact_path="model", signature=sig,
                              input_example=Xc.head(2),
                              registered_model_name=f"{fqn}.conversion_elasticity_motor")

mc = mlflow.tracking.MlflowClient()
_cv = max(int(v.version) for v in mc.search_model_versions(f"name='{fqn}.conversion_elasticity_motor'"))
mc.set_registered_model_alias(f"{fqn}.conversion_elasticity_motor", "champion", _cv)
print(f"registered conversion_elasticity_motor v{_cv} @champion")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Retention elasticity — monotone in rate change

# COMMAND ----------

RET_FEATURES = ["rate_change", "vs_technical", "tenure_years", "gipp_breach", "month_idx"]
RET_MONOTONE = [-1, 0, 0, 0, 0]   # retention can only fall as the renewal rate change rises

rr = spark.table(f"{fqn}.optimisation_renewal_response").toPandas()
for c in RET_FEATURES + ["retained"]:
    rr[c] = pd.to_numeric(rr[c], errors="coerce")
rr = rr.dropna(subset=RET_FEATURES + ["retained"])
Xr, yr = rr[RET_FEATURES], rr["retained"].astype(int)

ret = lgb.LGBMClassifier(
    n_estimators=250, learning_rate=0.05, num_leaves=31, min_child_samples=200,
    monotone_constraints=RET_MONOTONE, subsample=0.8, colsample_bytree=0.9, verbose=-1)
ret.fit(Xr, yr)
_rauc = None
try:
    from sklearn.metrics import roc_auc_score
    _rauc = roc_auc_score(yr, ret.predict_proba(Xr)[:, 1])
except Exception:
    pass
print(f"retention model: {len(Xr):,} renewals, train AUC {_rauc:.3f}" if _rauc else f"retention model on {len(Xr):,}")

with mlflow.start_run(run_name="retention_elasticity_motor"):
    mlflow.log_params({"features": ",".join(RET_FEATURES), "monotone": str(RET_MONOTONE),
                       "n_train": len(Xr)})
    if _rauc: mlflow.log_metric("train_auc", float(_rauc))
    sigr = infer_signature(Xr, ret.predict_proba(Xr)[:, 1])
    mlflow.lightgbm.log_model(ret, artifact_path="model", signature=sigr,
                              input_example=Xr.head(2),
                              registered_model_name=f"{fqn}.retention_elasticity_motor")
_rv = max(int(v.version) for v in mc.search_model_versions(f"name='{fqn}.retention_elasticity_motor'"))
mc.set_registered_model_alias(f"{fqn}.retention_elasticity_motor", "champion", _rv)
print(f"registered retention_elasticity_motor v{_rv} @champion")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. `optimisation_elasticity_curve` — per-segment price→conversion
# MAGIC For each segment, hold the risk features at the segment median and sweep the
# MAGIC **price ratio to technical** across the ±15% corridor, reading P(bound) off
# MAGIC the monotone model. `vs_market` is moved in lock-step (a uniform price move
# MAGIC shifts both ratios) so the curve reflects a real repricing.

# COMMAND ----------

qr["segment"] = segment_of(qr)
grid = np.round(np.linspace(0.85, 1.15, 13), 4)      # price multiplier on today's position
curve_rows = []
for seg, g in qr.groupby("segment"):
    if len(g) < 30:
        continue
    med = g[CONV_FEATURES].median()
    base_vt, base_vm = float(med["vs_technical"]), float(med["vs_market"])
    for m in grid:
        row = med.copy()
        row["vs_technical"] = base_vt * m
        row["vs_market"]    = base_vm * m
        p = float(conv.predict_proba(pd.DataFrame([row])[CONV_FEATURES])[:, 1][0])
        curve_rows.append({"segment": seg, "price_multiplier": float(m),
                           "vs_technical": round(base_vt * m, 4),
                           "conversion_prob": round(p, 4),
                           "policies": int(len(g))})
curve_df = pd.DataFrame(curve_rows)
(spark.createDataFrame(curve_df).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_elasticity_curve"))
print(f"optimisation_elasticity_curve: {curve_df['segment'].nunique()} segments × {len(grid)} points")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Red-team A — endogeneity (why raw price gives the WRONG elasticity)
# MAGIC The naive model regresses conversion on **raw log price**; the correct model
# MAGIC uses **price ÷ technical**. Because expensive risks command both a high
# MAGIC price *and* a high market benchmark, raw price barely correlates with
# MAGIC *competitiveness* — so the naive model reports demand as almost price-insensitive
# MAGIC (a dangerous, over-flat elasticity). We quantify both implied curves so the
# MAGIC app can overlay them.

# COMMAND ----------

d = qr.copy()
d["log_price"] = np.log(pd.to_numeric(d["offered_premium"], errors="coerce"))
# Naive: converted ~ raw log price. Correct: converted ~ vs_technical.
naive = LogisticRegression(max_iter=1000).fit(d[["log_price"]], d["converted"])
good  = LogisticRegression(max_iter=1000).fit(d[["vs_technical"]], d["converted"])

pct = np.round(np.linspace(-15, 15, 13), 2)               # price change %
med_price = float(d["offered_premium"].median())
med_vt    = float(d["vs_technical"].median())
naive_p = naive.predict_proba(np.log(med_price * (1 + pct / 100)).reshape(-1, 1))[:, 1]
good_p  = good.predict_proba((med_vt * (1 + pct / 100)).reshape(-1, 1))[:, 1]
endo = pd.DataFrame({
    "price_change_pct": pct,
    "naive_rawprice_conversion": np.round(naive_p, 4),
    "correct_vs_technical_conversion": np.round(good_p, 4),
})
# headline: conversion drop for a +10% move under each model.
def _drop(series):
    base = float(series[endo["price_change_pct"] == 0.0].iloc[0])
    hi   = float(series[np.isclose(endo["price_change_pct"], 10.0)].iloc[0])
    return round((base - hi) * 100, 2)     # percentage points lost
endo.attrs["naive_drop_pp_at_plus10"]   = _drop(endo["naive_rawprice_conversion"])
endo.attrs["correct_drop_pp_at_plus10"] = _drop(endo["correct_vs_technical_conversion"])
(spark.createDataFrame(endo).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_redteam_endogeneity"))
print(f"endogeneity panel: +10% price → conversion loss "
      f"naive {endo.attrs['naive_drop_pp_at_plus10']}pp vs correct {endo.attrs['correct_drop_pp_at_plus10']}pp")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Red-team B — parameter recovery
# MAGIC Block 1 injected a *known* month-by-month conversion elasticity:
# MAGIC `slope(m) = −base_conv_elasticity × (1 + 0.20·sin(2π·m/N))` in `vs_market`.
# MAGIC We refit a plain per-month logistic and check the pipeline **recovers** it —
# MAGIC the standard "can you get back what you put in?" validity check on synthetic
# MAGIC data. (base_conv_elasticity read back from the generator default of 6.0.)

# COMMAND ----------

BASE_CONV_E = 6.0
NMON = int(qr["month_idx"].max()) + 1
rec_rows = []
for m, g in qr.groupby("month_idx"):
    if len(g) < 200 or g["converted"].nunique() < 2:
        continue
    lr = LogisticRegression(max_iter=1000).fit(g[["vs_market"]], g["converted"])
    recovered = float(lr.coef_[0][0])                    # slope in vs_market
    true_slope = -BASE_CONV_E * (1 + 0.20 * np.sin(2 * np.pi * int(m) / max(1, NMON)))
    rec_rows.append({"month_idx": int(m), "true_slope": round(true_slope, 3),
                     "recovered_slope": round(recovered, 3), "n_quotes": int(len(g))})
rec = pd.DataFrame(rec_rows).sort_values("month_idx")
_corr = float(np.corrcoef(rec["true_slope"], rec["recovered_slope"])[0, 1]) if len(rec) > 2 else None
(spark.createDataFrame(rec).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_param_recovery"))
print(f"param recovery: {len(rec)} months, true↔recovered corr {_corr:.3f}" if _corr else f"param recovery: {len(rec)} months")

# COMMAND ----------

print("Block 2 complete → conversion_elasticity_motor, retention_elasticity_motor, "
      "optimisation_elasticity_curve, optimisation_redteam_endogeneity, optimisation_param_recovery")

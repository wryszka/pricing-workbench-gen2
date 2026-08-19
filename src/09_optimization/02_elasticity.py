# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — block 02: elasticity models
# MAGIC
# MAGIC Two LightGBM models with **price monotonicity enforced** (the demo beat —
# MAGIC the solver exploits any non-monotone wrinkle, so we forbid it):
# MAGIC  * `pwg2_conversion_elasticity` — P(bind) for new business, monotone
# MAGIC    DECREASING in our price ratio (vs_market_rate). Trained on
# MAGIC    `opt_quote_response`.
# MAGIC  * `pwg2_retention_elasticity`  — P(retain) at renewal, monotone
# MAGIC    DECREASING in the rate change. Trained on `opt_renewal_response`.
# MAGIC
# MAGIC Registered to UC with `@champion` aliases (pwg2_ naming). The existing
# MAGIC demand_gbm is left untouched — these are the optimizer's own price-aware
# MAGIC models. Also writes `opt_elasticity_curves` (price→P(convert) per segment)
# MAGIC for the app page + talk track. MLflow-tracked. Idempotent.
# MAGIC
# MAGIC Deps (lightgbm, mlflow, pandas, scikit-learn) come from the job environment
# MAGIC (resources/optimization.yml) — never %pip + restartPython on serverless.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
fqn     = f"{catalog}.{schema}"

import json
import numpy as np
import pandas as pd
import lightgbm as lgb
import mlflow
from mlflow.tracking import MlflowClient

mlflow.set_registry_uri("databricks-uc")
mc = MlflowClient(registry_uri="databricks-uc")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conversion elasticity (new business) — monotone ↓ in price ratio

# COMMAND ----------

qr = spark.table(f"{fqn}.opt_quote_response").toPandas()
# Price lever = vs_market_rate (our price / market). Categorical risk features
# alongside; the price feature carries a monotone_decreasing constraint.
PRICE_FEAT = "vs_market_rate"
CAT_FEATS  = ["sic_code", "region", "construction_type", "channel"]
NUM_FEATS  = ["buildings_si", "contents_si", "liability_si", "annual_turnover",
              "claims_last_5y", "flood_zone", PRICE_FEAT]
for c in CAT_FEATS:
    qr[c] = qr[c].astype("category")
feat_cols = CAT_FEATS + NUM_FEATS
X = qr[feat_cols]
y = qr["converted"].astype(int)

# monotone_constraints: -1 on the price feature (P(bind) falls as price rises),
# 0 elsewhere. Order matches feat_cols.
mono = [(-1 if c == PRICE_FEAT else 0) for c in feat_cols]

with mlflow.start_run(run_name="pwg2_conversion_elasticity") as run:
    ds = lgb.Dataset(X, label=y, categorical_feature=CAT_FEATS, free_raw_data=False)
    params = dict(objective="binary", metric="auc", learning_rate=0.05,
                  num_leaves=31, min_data_in_leaf=200, monotone_constraints=mono,
                  verbose=-1)
    model = lgb.train(params, ds, num_boost_round=300)
    auc = float(model.best_score.get("training", {}).get("auc", 0) or 0)
    mlflow.log_params({"price_feature": PRICE_FEAT, "monotone": "price:-1"})
    # sanity: P(bind) must fall as vs_market_rate rises, holding a base row fixed
    base = X.iloc[[0]].copy()
    grid = np.linspace(0.85, 1.20, 8)
    probs = []
    for g in grid:
        b = base.copy(); b[PRICE_FEAT] = g
        probs.append(float(model.predict(b)[0]))
    monotone_ok = all(probs[i] >= probs[i+1] - 1e-6 for i in range(len(probs)-1))
    mlflow.log_metric("monotone_ok", 1 if monotone_ok else 0)
    print(f"conversion model: {len(qr):,} rows, monotone_ok={monotone_ok}, curve={[round(p,3) for p in probs]}")
    mlflow.lightgbm.log_model(model, artifact_path="model",
                              registered_model_name=f"{fqn}.pwg2_conversion_elasticity")

# alias @champion → latest
_v = max(int(v.version) for v in mc.search_model_versions(f"name='{fqn}.pwg2_conversion_elasticity'"))
mc.set_registered_model_alias(f"{fqn}.pwg2_conversion_elasticity", "champion", _v)
print(f"pwg2_conversion_elasticity @champion → v{_v}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Retention elasticity (renewal) — monotone ↓ in rate change

# COMMAND ----------

rr = spark.table(f"{fqn}.opt_renewal_response").toPandas()
R_CAT = ["sic_code", "postcode_sector"]
R_NUM = ["tenure_years", "prior_premium", "rate_change"]
for c in R_CAT:
    rr[c] = rr[c].astype("category")
r_cols = R_CAT + R_NUM
Xr = rr[r_cols]; yr = rr["retained"].astype(int)
r_mono = [(-1 if c == "rate_change" else 0) for c in r_cols]

with mlflow.start_run(run_name="pwg2_retention_elasticity"):
    dsr = lgb.Dataset(Xr, label=yr, categorical_feature=R_CAT, free_raw_data=False)
    rparams = dict(objective="binary", metric="auc", learning_rate=0.05,
                   num_leaves=31, min_data_in_leaf=200, monotone_constraints=r_mono, verbose=-1)
    rmodel = lgb.train(rparams, dsr, num_boost_round=300)
    mlflow.lightgbm.log_model(rmodel, artifact_path="model",
                              registered_model_name=f"{fqn}.pwg2_retention_elasticity")
_rv = max(int(v.version) for v in mc.search_model_versions(f"name='{fqn}.pwg2_retention_elasticity'"))
mc.set_registered_model_alias(f"{fqn}.pwg2_retention_elasticity", "champion", _rv)
print(f"pwg2_retention_elasticity @champion → v{_rv}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Elasticity curves per segment (price → P(convert)) for the app page

# COMMAND ----------

# For the top trade segments, sweep the price ratio and record modelled P(bind)
# at the segment's median risk row — the curve the app + talk track use.
curves = []
top_segments = (qr.groupby("sic_code", observed=True)["offered_premium"].count()
                  .sort_values(ascending=False).head(8).index.tolist())
grid = [round(g, 3) for g in np.linspace(0.85, 1.20, 12)]
for seg in top_segments:
    sub = qr[qr["sic_code"] == seg]
    if len(sub) < 20:
        continue
    row = sub[feat_cols].median(numeric_only=True)
    base = sub[feat_cols].iloc[[0]].copy()
    for nf in NUM_FEATS:
        if nf in row: base[nf] = row[nf]
    for g in grid:
        b = base.copy(); b[PRICE_FEAT] = g
        curves.append({"segment": str(seg), "price_ratio": g, "p_convert": round(float(model.predict(b)[0]), 4)})

cur_df = spark.createDataFrame(pd.DataFrame(curves)) if curves else None
if cur_df is not None:
    cur_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{fqn}.opt_elasticity_curves")
    print(f"opt_elasticity_curves: {len(curves)} points across {len(top_segments)} segments")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "conversion_version": _v, "retention_version": _rv,
    "curve_points": len(curves),
}))

# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — Block 5: monitoring / feedback (§8)
# MAGIC
# MAGIC The reality check on the loop. Over the rolling-month timeline Block 1 built:
# MAGIC  * **`optimisation_monitoring`** — actual vs model-expected conversion per
# MAGIC    month + drift (the elasticity-drift sentinel's signal).
# MAGIC  * **`optimisation_deviation_dist`** — distribution of price ÷ technical
# MAGIC    across the book (are we living inside the corridor?).
# MAGIC  * **`optimisation_constraint_breaches`** — count of quotes/renewals outside
# MAGIC    the corridor and the GIPP rule (the fair-value / Consumer-Duty tile).
# MAGIC
# MAGIC Expected conversion comes from the governed `conversion_elasticity_motor`
# MAGIC champion (loaded on the driver — plain LightGBM, no FE wrapper).

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
dbutils.widgets.text("corridor_pct", "15")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
CORR    = float(dbutils.widgets.get("corridor_pct")) / 100.0
fqn     = f"{catalog}.{schema}"

import numpy as np, pandas as pd
import mlflow
mlflow.set_registry_uri("databricks-uc")

CONV_FEATURES = ["vs_technical", "vs_market", "driver_age", "no_claims_years",
                 "annual_mileage", "vehicle_value", "vehicle_group", "month_idx"]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Actual vs expected conversion per month → drift

# COMMAND ----------

qr = spark.table(f"{fqn}.optimisation_quote_response").toPandas()
for c in CONV_FEATURES + ["converted"]:
    qr[c] = pd.to_numeric(qr[c], errors="coerce")
qr = qr.dropna(subset=CONV_FEATURES + ["converted", "quote_month"])

conv = mlflow.lightgbm.load_model(f"models:/{fqn}.conversion_elasticity_motor@champion")
qr["expected"] = conv.predict_proba(qr[CONV_FEATURES])[:, 1]

mon = (qr.groupby("quote_month")
         .agg(quotes=("converted", "size"),
              actual_conversion=("converted", "mean"),
              expected_conversion=("expected", "mean"))
         .reset_index().sort_values("quote_month"))
mon["drift"] = (mon["actual_conversion"] - mon["expected_conversion"]).round(4)
mon["actual_conversion"] = mon["actual_conversion"].round(4)
mon["expected_conversion"] = mon["expected_conversion"].round(4)
(spark.createDataFrame(mon).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_monitoring"))
print(f"optimisation_monitoring: {len(mon)} months, latest drift {mon['drift'].iloc[-1]:+.4f}, "
      f"max |drift| {mon['drift'].abs().max():.4f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Deviation-from-technical distribution

# COMMAND ----------

vt = pd.to_numeric(qr["vs_technical"], errors="coerce").dropna()
edges = np.array([0.70, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.35])
labels = [f"{edges[i]:.2f}–{edges[i+1]:.2f}" for i in range(len(edges) - 1)]
cats = pd.cut(vt, bins=edges, labels=labels, include_lowest=True)
dist = cats.value_counts().reindex(labels).fillna(0).astype(int).reset_index()
dist.columns = ["vs_technical_band", "count"]
dist["pct"] = (dist["count"] / max(1, dist["count"].sum())).round(4)
dist["outside_corridor"] = [not (0.85 - 1e-9 <= (edges[i] + edges[i + 1]) / 2 <= 1.15 + 1e-9)
                            for i in range(len(labels))]
(spark.createDataFrame(dist).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_deviation_dist"))
print(f"optimisation_deviation_dist: {len(dist)} bands over {int(dist['count'].sum()):,} quotes")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Constraint-breach tile (corridor + GIPP)

# COMMAND ----------

rr = spark.table(f"{fqn}.optimisation_renewal_response").toPandas()
rr_vt = pd.to_numeric(rr["vs_technical"], errors="coerce")
gipp = pd.to_numeric(rr["gipp_breach"], errors="coerce").fillna(0)

nb_out = int(((vt < 1 + -CORR) | (vt > 1 + CORR)).sum())   # new-business quotes outside corridor
rn_out = int(((rr_vt < 1 - CORR) | (rr_vt > 1 + CORR)).sum())
breaches = pd.DataFrame([
    {"check": "new_business_outside_corridor", "breaches": nb_out, "total": int(len(vt)),
     "rate": round(nb_out / max(1, len(vt)), 4),
     "note": f"quotes with price÷technical outside ±{CORR:.0%}"},
    {"check": "renewal_outside_corridor", "breaches": rn_out, "total": int(len(rr_vt)),
     "rate": round(rn_out / max(1, len(rr_vt)), 4),
     "note": f"renewals with price÷technical outside ±{CORR:.0%}"},
    {"check": "gipp_renewal_above_new_business", "breaches": int(gipp.sum()), "total": int(len(gipp)),
     "rate": round(float(gipp.mean()), 4),
     "note": "renewal offered above equivalent new-business price (UK GIPP)"},
])
(spark.createDataFrame(breaches).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_constraint_breaches"))
print("optimisation_constraint_breaches:")
for _, r in breaches.iterrows():
    print(f"  {r['check']}: {r['breaches']:,}/{r['total']:,} ({r['rate']:.1%})")

# COMMAND ----------

print("Block 5 complete → optimisation_monitoring, optimisation_deviation_dist, optimisation_constraint_breaches")

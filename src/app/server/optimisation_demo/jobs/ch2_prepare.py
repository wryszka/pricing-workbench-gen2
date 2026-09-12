# Databricks notebook source
# MAGIC %md
# MAGIC # Optimisation demo — Chapter 2 PREPARE
# MAGIC Freeze the synthetic data, train + validate the demand model, and persist the frozen
# MAGIC model artifact + manifest. Run this once before recording; the Choose runs reuse it.
# MAGIC Uses the shared pure modules (data / demand / economics) — one copy inside the app.

# COMMAND ----------
import hashlib, json, sys
from datetime import datetime, timezone

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name", "pricing_workbench_gen2")
dbutils.widgets.text("app_src_base", "")
dbutils.widgets.text("model_version", "ch2-demand-v1")
catalog = dbutils.widgets.get("catalog_name"); schema = dbutils.widgets.get("schema_name")
model_version = dbutils.widgets.get("model_version"); fqn = f"{catalog}.{schema}"

src_base = dbutils.widgets.get("app_src_base").strip()
if src_base and src_base not in sys.path:
    sys.path.insert(0, src_base)
from server.optimisation_demo.data import make_historic, time_split, make_future, GENERATOR_VERSION  # noqa: E402
from server.optimisation_demo.demand import train_logistic, validate  # noqa: E402
import joblib  # noqa: E402

# COMMAND ----------
# 1. Generate + freeze data; train + validate on the out-of-time split.
hist = make_historic(); train, val, test = time_split(hist); future = make_future()
model = train_logistic(train)
report = validate(model, test, future)

# COMMAND ----------
# 2. Persist the frozen model artifact to a UC volume + hash it.
spark.sql(f"CREATE VOLUME IF NOT EXISTS {fqn}.optimisation_demo_artifacts")
vol_dir = f"/Volumes/{catalog}/{schema}/optimisation_demo_artifacts"
artifact_path = f"{vol_dir}/ch2_demand_{model_version}.joblib"
joblib.dump(model, artifact_path)
with open(artifact_path, "rb") as fh:
    artifact_hash = hashlib.sha256(fh.read()).hexdigest()

# COMMAND ----------
# 3. Persist the future opportunity snapshot (the governed input for Choose runs).
spark.sql(f"DROP TABLE IF EXISTS {fqn}.optimisation_demo_ch2_future")
spark.createDataFrame(future).write.mode("overwrite").saveAsTable(f"{fqn}.optimisation_demo_ch2_future")
future_version = spark.sql(f"DESCRIBE HISTORY {fqn}.optimisation_demo_ch2_future LIMIT 1").collect()[0]["version"]

# 4. Model manifest + validation report tables.
spark.sql(f"""CREATE TABLE IF NOT EXISTS {fqn}.optimisation_demo_ch2_model_manifest (
  model_version STRING, generator_version STRING, artifact_path STRING, artifact_hash STRING,
  future_table STRING, future_delta_version LONG, passes BOOLEAN, failures STRING,
  thresholds STRING, trained_at TIMESTAMP)""")
spark.sql(f"DELETE FROM {fqn}.optimisation_demo_ch2_model_manifest WHERE model_version = '{model_version}'")
from pyspark.sql import Row
spark.createDataFrame([Row(
    model_version=model_version, generator_version=GENERATOR_VERSION, artifact_path=artifact_path,
    artifact_hash=artifact_hash, future_table=f"{fqn}.optimisation_demo_ch2_future",
    future_delta_version=int(future_version), passes=bool(report["passes"]),
    failures=json.dumps(report["failures"]), thresholds=json.dumps(report["thresholds"]),
    trained_at=datetime.now(timezone.utc))]).write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_ch2_model_manifest")

spark.sql(f"""CREATE TABLE IF NOT EXISTS {fqn}.optimisation_demo_ch2_validation (
  model_version STRING, metric STRING, value DOUBLE)""")
spark.sql(f"DELETE FROM {fqn}.optimisation_demo_ch2_validation WHERE model_version = '{model_version}'")
mrows = [Row(model_version=model_version, metric=k, value=float(v))
         for k, v in report["metrics"].items() if isinstance(v, (int, float, bool))]
spark.createDataFrame(mrows).write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_ch2_validation")

dbutils.notebook.exit(json.dumps({
    "model_version": model_version, "passes": report["passes"], "failures": report["failures"],
    "metrics": {k: v for k, v in report["metrics"].items() if isinstance(v, (int, float, bool))},
    "artifact_hash": artifact_hash, "future_delta_version": int(future_version)}))

# Databricks notebook source
# MAGIC %md
# MAGIC # Optimisation demo — Chapter 2 CHECK (synthetic outcome check)
# MAGIC Evaluate the ACTIVE approved release on an independently generated synthetic next
# MAGIC period, drawing outcomes from the frozen generator (not the model). Advances one
# MAGIC synthetic period per run. Labelled synthetic — not real-demand validation.

# COMMAND ----------
import json, sys
from datetime import datetime, timezone

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name", "pricing_workbench_gen2")
dbutils.widgets.text("app_src_base", "")
catalog = dbutils.widgets.get("catalog_name"); schema = dbutils.widgets.get("schema_name")
fqn = f"{catalog}.{schema}"
src_base = dbutils.widgets.get("app_src_base").strip()
if src_base and src_base not in sys.path:
    sys.path.insert(0, src_base)
from server.optimisation_demo.monitoring import simulate_outcomes, compare  # noqa: E402
from pyspark.sql import Row  # noqa: E402

# COMMAND ----------
rel = spark.sql(f"SELECT release_id, run_id FROM {fqn}.optimisation_demo_ch2_releases ORDER BY released_at DESC LIMIT 1").collect()
if not rel:
    raise ValueError("no active demo release — approve a plan first")
release_id, run_id = rel[0]["release_id"], rel[0]["run_id"]

sel = spark.sql(f"SELECT segment, factor, expected_sales, expected_margin FROM {fqn}.optimisation_demo_ch2_candidate_scores WHERE run_id='{run_id}' AND selected").collect()
selection = {r["segment"]: float(r["factor"]) for r in sel}
expected = {r["segment"]: {"expected_sales": float(r["expected_sales"]), "expected_margin": float(r["expected_margin"])} for r in sel}
future = spark.table(f"{fqn}.optimisation_demo_ch2_future").toPandas()

spark.sql(f"""CREATE TABLE IF NOT EXISTS {fqn}.optimisation_demo_ch2_monitoring (
  release_id STRING, period INT, segment STRING, expected_sales DOUBLE, observed_sales DOUBLE,
  expected_margin DOUBLE, observed_margin DOUBLE, n INT, evaluated_at TIMESTAMP)""")
prev = spark.sql(f"SELECT max(period) p FROM {fqn}.optimisation_demo_ch2_monitoring WHERE release_id='{release_id}'").collect()[0]["p"]
period = int(prev or 0) + 1

obs = simulate_outcomes(future, selection, seed=20260900 + period)   # advance = fresh draw per period
rows = compare(expected, obs)
mrows = [Row(release_id=release_id, period=period, segment=r["segment"],
             expected_sales=float(r["expected_sales"]), observed_sales=float(r["observed_sales"]),
             expected_margin=float(r["expected_margin"]), observed_margin=float(r["observed_margin"]),
             n=int(r["n"]), evaluated_at=datetime.now(timezone.utc)) for r in rows]
spark.createDataFrame(mrows).write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_ch2_monitoring")
dbutils.notebook.exit(json.dumps({"release_id": release_id, "period": period, "segments": len(rows)}))

# Databricks notebook source
# MAGIC %md
# MAGIC # Optimisation demo — run (Chapter 1)
# MAGIC
# MAGIC The real job behind the "Run on Databricks" panel. It:
# MAGIC 1. ensures the demo tables exist (idempotent; never touches the workbench tables),
# MAGIC 2. seeds the input example into `optimisation_demo_inputs`,
# MAGIC 3. reads the example **back from the governed table** (capturing its Delta version),
# MAGIC 4. runs the shared pure calculation (`server.optimisation_demo.core`),
# MAGIC 5. asserts the arithmetic, then
# MAGIC 6. saves candidate rows + a run record keyed by the **application run id**.
# MAGIC
# MAGIC The calculation lives in ONE place (`core.py`) shared with the app — this notebook
# MAGIC imports it, it does not re-implement the numbers.

# COMMAND ----------

import json
import sys
from datetime import datetime, timezone

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name", "pricing_workbench_gen2")
dbutils.widgets.text("example_id", "grandma_bmw_v1")
dbutils.widgets.text("app_run_id", "")
dbutils.widgets.text("min_expected_customers", "")   # blank = no sales requirement
dbutils.widgets.text("app_src_base", "")             # <files>/src/app — so `server.*` imports

catalog = dbutils.widgets.get("catalog_name")
schema = dbutils.widgets.get("schema_name")
example_id = dbutils.widgets.get("example_id")
app_run_id = dbutils.widgets.get("app_run_id").strip()
_min_raw = dbutils.widgets.get("min_expected_customers").strip()
min_expected = None if _min_raw in ("", "none", "None") else float(_min_raw)
fqn = f"{catalog}.{schema}"

if not app_run_id:
    raise ValueError("app_run_id is required (the application-generated run id)")

# Import the shared calculation module (one canonical copy, shipped inside the app).
src_base = dbutils.widgets.get("app_src_base").strip()
if src_base and src_base not in sys.path:
    sys.path.insert(0, src_base)
from server.optimisation_demo.core import load_example, optimise, validate_result  # noqa: E402

# COMMAND ----------

# 1. Idempotent table creation — distinct optimisation_demo_* names, never the workbench tables.
spark.sql(f"""CREATE TABLE IF NOT EXISTS {fqn}.optimisation_demo_inputs (
  example_id STRING, example_version STRING, segment_label STRING,
  opportunities DOUBLE, modelled_variable_cost_per_sale DOUBLE, baseline_price DOUBLE,
  candidate_price DOUBLE, purchase_probability DOUBLE, assumptions STRING
)""")
spark.sql(f"""CREATE TABLE IF NOT EXISTS {fqn}.optimisation_demo_runs (
  run_id STRING, example_id STRING, example_version STRING, input_delta_version LONG,
  requirement_json STRING, objective STRING, code_revision STRING,
  status STRING, winner_price DOUBLE, winner_expected_customers DOUBLE,
  winner_expected_total_margin DOUBLE, winner_expected_premium DOUBLE,
  job_run_id STRING, created_at TIMESTAMP
)""")
spark.sql(f"""CREATE TABLE IF NOT EXISTS {fqn}.optimisation_demo_candidate_results (
  run_id STRING, candidate_price DOUBLE, purchase_probability DOUBLE,
  expected_customers DOUBLE, expected_premium DOUBLE, expected_total_margin DOUBLE,
  margin_per_sale DOUBLE, feasible BOOLEAN, feasibility_reason STRING, selected BOOLEAN
)""")

# COMMAND ----------

# 2. Seed the input example (idempotent upsert for this example_id) from the canonical fixture.
ex = load_example()
from pyspark.sql import Row
assumptions_json = json.dumps(ex.get("assumptions", {}))
input_rows = [Row(
    example_id=ex["example_id"], example_version=str(ex.get("example_version", "1")),
    segment_label=ex.get("segment_label"), opportunities=float(ex["opportunities"]),
    modelled_variable_cost_per_sale=float(ex["modelled_variable_cost_per_sale"]),
    baseline_price=float(ex["baseline_price"]),
    candidate_price=float(c["price"]), purchase_probability=float(c["purchase_probability"]),
    assumptions=assumptions_json,
) for c in ex["candidates"]]
spark.sql(f"DELETE FROM {fqn}.optimisation_demo_inputs WHERE example_id = '{example_id}'")
spark.createDataFrame(input_rows).write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_inputs")

# 3. Read the example BACK from the governed table + capture its Delta version.
in_rows = spark.sql(
    f"SELECT * FROM {fqn}.optimisation_demo_inputs WHERE example_id = '{example_id}' ORDER BY candidate_price"
).collect()
if not in_rows:
    raise ValueError(f"no input rows for example_id '{example_id}'")
input_delta_version = spark.sql(f"DESCRIBE HISTORY {fqn}.optimisation_demo_inputs LIMIT 1").collect()[0]["version"]

example = {
    "example_id": example_id,
    "example_version": in_rows[0]["example_version"],
    "segment_label": in_rows[0]["segment_label"],
    "opportunities": in_rows[0]["opportunities"],
    "modelled_variable_cost_per_sale": in_rows[0]["modelled_variable_cost_per_sale"],
    "baseline_price": in_rows[0]["baseline_price"],
    "candidates": [{"price": r["candidate_price"], "purchase_probability": r["purchase_probability"]} for r in in_rows],
}

# COMMAND ----------

# 4-5. Run the shared calculation and assert the arithmetic before saving anything.
result = optimise(example, min_expected)
validate_result(example, result)

status = "no_feasible" if result["no_feasible"] else "complete"
w = result["winner"] or {}

# 6. Save keyed by the application run id — idempotent (delete-then-insert this run only).
spark.sql(f"DELETE FROM {fqn}.optimisation_demo_candidate_results WHERE run_id = '{app_run_id}'")
spark.sql(f"DELETE FROM {fqn}.optimisation_demo_runs WHERE run_id = '{app_run_id}'")

cand_rows = [Row(
    run_id=app_run_id, candidate_price=float(c["price"]), purchase_probability=float(c["purchase_probability"]),
    expected_customers=float(c["expected_customers"]), expected_premium=float(c["expected_premium"]),
    expected_total_margin=float(c["expected_total_margin"]), margin_per_sale=float(c["margin_per_sale"]),
    feasible=bool(c["feasible"]), feasibility_reason=c["feasibility_reason"], selected=bool(c["selected"]),
) for c in result["candidates"]]
spark.createDataFrame(cand_rows).write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_candidate_results")

try:
    job_run_id = str(dbutils.notebook.entry_point.getDbutils().notebook().getContext().jobId().get())
except Exception:
    job_run_id = ""

run_row = [Row(
    run_id=app_run_id, example_id=example_id, example_version=str(example["example_version"]),
    input_delta_version=int(input_delta_version),
    requirement_json=json.dumps({"min_expected_customers": min_expected}),
    objective=result["objective"], code_revision="",
    status=status,
    winner_price=(float(w["price"]) if w else None),
    winner_expected_customers=(float(w["expected_customers"]) if w else None),
    winner_expected_total_margin=(float(w["expected_total_margin"]) if w else None),
    winner_expected_premium=(float(w["expected_premium"]) if w else None),
    job_run_id=job_run_id, created_at=datetime.now(timezone.utc),
)]
spark.createDataFrame(run_row).write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_runs")

dbutils.notebook.exit(json.dumps({
    "app_run_id": app_run_id, "status": status,
    "winner": (None if not w else {"price": w["price"], "expected_customers": w["expected_customers"],
                                   "expected_total_margin": w["expected_total_margin"]}),
    "input_delta_version": int(input_delta_version),
}))

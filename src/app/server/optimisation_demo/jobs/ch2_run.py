# Databricks notebook source
# MAGIC %md
# MAGIC # Optimisation demo — Chapter 2 RUN (score → solve)
# MAGIC Loads the frozen model + future snapshot, scores every candidate factor, solves the
# MAGIC portfolio MILP for the requirement, and saves candidate scores + selected plan + a run
# MAGIC record keyed by the application run id. Verifies the model artifact hash against the
# MAGIC manifest before scoring (never trusts a loose alias).

# COMMAND ----------
import hashlib, json, sys
from datetime import datetime, timezone

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name", "pricing_workbench_gen2")
dbutils.widgets.text("app_src_base", "")
dbutils.widgets.text("app_run_id", "")
dbutils.widgets.text("model_version", "ch2-demand-v1")
dbutils.widgets.text("min_portfolio_sales_ratio", "")   # blank = margin-first; e.g. 0.98
catalog = dbutils.widgets.get("catalog_name"); schema = dbutils.widgets.get("schema_name")
app_run_id = dbutils.widgets.get("app_run_id").strip(); model_version = dbutils.widgets.get("model_version")
_r = dbutils.widgets.get("min_portfolio_sales_ratio").strip()
ratio = None if _r in ("", "none", "None") else float(_r)
fqn = f"{catalog}.{schema}"
if not app_run_id:
    raise ValueError("app_run_id is required")

src_base = dbutils.widgets.get("app_src_base").strip()
if src_base and src_base not in sys.path:
    sys.path.insert(0, src_base)
from server.optimisation_demo.demand import predict_at  # noqa: E402
from server.optimisation_demo.economics import coefficients_from_future  # noqa: E402
from server.optimisation_demo.portfolio import solve_portfolio  # noqa: E402
from server.optimisation_demo.schemas import DEFAULT_FACTORS, normalise_policy  # noqa: E402
import joblib  # noqa: E402

# COMMAND ----------
# Load the frozen manifest + verify the artifact hash before trusting the model.
man = spark.sql(f"SELECT * FROM {fqn}.optimisation_demo_ch2_model_manifest WHERE model_version='{model_version}'").collect()
if not man:
    raise ValueError(f"no model manifest for {model_version} — run PREPARE first")
man = man[0]
with open(man["artifact_path"], "rb") as fh:
    h = hashlib.sha256(fh.read()).hexdigest()
if h != man["artifact_hash"]:
    raise ValueError("model artifact hash mismatch vs manifest — refusing to score")
if not man["passes"]:
    raise ValueError(f"model {model_version} failed validation and is not eligible: {man['failures']}")
model = joblib.load(man["artifact_path"])

future = spark.table(f"{fqn}.optimisation_demo_ch2_future").toPandas()
policy = normalise_policy(min_portfolio_sales_ratio=ratio)
factors = policy["candidate_factors"]

# COMMAND ----------
# Score → coefficients → solve. Baseline = model's predicted sales at factor 1.0.
predict_fn = lambda f: predict_at(model, future, f)
coeffs = coefficients_from_future(future, factors, predict_fn)
segs = sorted(future["segment"].unique().tolist())
cands = {s: factors for s in segs}
baseline_key = {s: 1.0 for s in segs}
baseline_sales = float(predict_at(model, future, 1.0).sum())
baseline_margin = float(sum(coeffs[(s, 1.0)]["expected_margin"] for s in segs))
floor = None if ratio is None else ratio * baseline_sales
res = solve_portfolio(segs, cands, coeffs, baseline_key, min_portfolio_sales=floor)

status = "complete" if res["feasible"] else "infeasible"

# COMMAND ----------
# Persist candidate scores + selected plan + run record, keyed by app_run_id (idempotent).
from pyspark.sql import Row
for t, cols in [
    ("optimisation_demo_ch2_candidate_scores",
     "run_id STRING, segment STRING, factor DOUBLE, expected_sales DOUBLE, expected_premium DOUBLE, expected_claims DOUBLE, expected_margin DOUBLE, selected BOOLEAN"),
    ("optimisation_demo_ch2_runs",
     "run_id STRING, model_version STRING, objective STRING, min_portfolio_sales_ratio DOUBLE, status STRING, baseline_sales DOUBLE, baseline_margin DOUBLE, total_sales DOUBLE, total_margin DOUBLE, future_delta_version LONG, job_run_id STRING, created_at TIMESTAMP")]:
    spark.sql(f"CREATE TABLE IF NOT EXISTS {fqn}.{t} ({cols})")
    spark.sql(f"DELETE FROM {fqn}.{t} WHERE run_id = '{app_run_id}'")

selection = res.get("selection", {})
score_rows = []
for (s, f), c in coeffs.items():
    score_rows.append(Row(run_id=app_run_id, segment=s, factor=float(f),
                          expected_sales=c["expected_sales"], expected_premium=c["expected_premium"],
                          expected_claims=c["expected_claims"], expected_margin=c["expected_margin"],
                          selected=bool(selection.get(s) == f)))
spark.createDataFrame(score_rows).write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_ch2_candidate_scores")

try:
    job_run_id = str(dbutils.notebook.entry_point.getDbutils().notebook().getContext().jobId().get())
except Exception:
    job_run_id = ""
spark.createDataFrame([Row(
    run_id=app_run_id, model_version=model_version, objective=policy["objective"],
    min_portfolio_sales_ratio=(None if ratio is None else float(ratio)), status=status,
    baseline_sales=baseline_sales, baseline_margin=baseline_margin,
    total_sales=(res.get("total_expected_sales") if res["feasible"] else None),
    total_margin=(res.get("total_expected_margin") if res["feasible"] else None),
    future_delta_version=int(man["future_delta_version"]), job_run_id=job_run_id,
    created_at=datetime.now(timezone.utc))]).write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_ch2_runs")

dbutils.notebook.exit(json.dumps({
    "app_run_id": app_run_id, "status": status, "selection": selection,
    "baseline_sales": round(baseline_sales, 1), "baseline_margin": round(baseline_margin, 0),
    "total_sales": (round(res["total_expected_sales"], 1) if res["feasible"] else None),
    "total_margin": (round(res["total_expected_margin"], 0) if res["feasible"] else None)}))

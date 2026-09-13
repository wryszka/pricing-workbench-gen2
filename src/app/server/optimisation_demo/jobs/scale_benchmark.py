# Databricks notebook source
# MAGIC %md
# MAGIC # Optimisation demo — scale benchmark (WP5, bounded)
# MAGIC Scores the SAME frozen population + model two ways — a serial reference and a
# MAGIC Spark-partitioned distributed path — VERIFIES the coefficients agree within a declared
# MAGIC tolerance BEFORE comparing timings, then measures cold vs warm (hash-keyed coefficient
# MAGIC cache). Reports phases separately and honest counts/partition evidence. Bounded to the
# MAGIC demo population and a capped opportunity count — never provisions unbounded compute, and
# MAGIC never claims a speedup that was not measured.

# COMMAND ----------
import json, sys, time, hashlib
from datetime import datetime, timezone

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name", "pricing_workbench_gen2")
dbutils.widgets.text("app_src_base", "")
dbutils.widgets.text("app_run_id", "")
dbutils.widgets.text("model_version", "ch2-demand-v1")
dbutils.widgets.text("preset", "live")             # live | full
dbutils.widgets.text("n_partitions", "8")
catalog = dbutils.widgets.get("catalog_name"); schema = dbutils.widgets.get("schema_name")
app_run_id = dbutils.widgets.get("app_run_id").strip()
model_version = dbutils.widgets.get("model_version")
preset = dbutils.widgets.get("preset").strip().lower()
n_parts = int(dbutils.widgets.get("n_partitions") or "8")
fqn = f"{catalog}.{schema}"
if not app_run_id:
    raise ValueError("app_run_id is required")

src_base = dbutils.widgets.get("app_src_base").strip()
if src_base and src_base not in sys.path:
    sys.path.insert(0, src_base)
from server.optimisation_demo.economics import coefficients_from_future  # noqa: E402
from server.optimisation_demo.demand import predict_at, FEATURES  # noqa: E402
from server.optimisation_demo.schemas import DEFAULT_FACTORS  # noqa: E402
from server.optimisation_demo import scale  # noqa: E402
import joblib, pandas as pd  # noqa: E402

# COMMAND ----------
# Frozen model (hash-verified) + population. FULL preset replicates the demo population up
# to a BOUNDED cap so scale is exercised without unbounded compute; counts are reported.
man = spark.sql(f"SELECT * FROM {fqn}.optimisation_demo_ch2_model_manifest WHERE model_version='{model_version}'").collect()[0]
with open(man["artifact_path"], "rb") as fh:
    if hashlib.sha256(fh.read()).hexdigest() != man["artifact_hash"]:
        raise ValueError("model artifact hash mismatch vs manifest — refusing to benchmark")
model = joblib.load(man["artifact_path"])
artifact_path = man["artifact_path"]

future0 = spark.table(f"{fqn}.optimisation_demo_ch2_future").toPandas()
CAP = 250_000
target = len(future0) if preset != "full" else min(CAP, 50 * len(future0))
reps = max(1, target // len(future0))
future = pd.concat([future0] * reps, ignore_index=True) if reps > 1 else future0
n_opps = len(future)
factors = DEFAULT_FACTORS

# COMMAND ----------
# 1. Serial reference scoring (driver, pure functions).
t0 = time.monotonic()
serial = coefficients_from_future(future, factors, lambda f: predict_at(model, future, f))
serial_s = time.monotonic() - t0

# COMMAND ----------
# 2. Distributed scoring — partition the population; each partition scores with the model
#    loaded on the executor (same pure functions) and emits partial (segment,factor) sums;
#    Spark aggregates. This is the exact same arithmetic, summed in a different order (hence
#    a tolerance check, not bit-equality).
sdf = spark.createDataFrame(future).repartition(n_parts)
_factors = list(factors); _base = src_base; _apath = artifact_path

def _score_partition(pdf_iter):
    import sys as _sys, joblib as _jl
    if _base and _base not in _sys.path:
        _sys.path.insert(0, _base)
    from server.optimisation_demo.economics import coefficients_from_future as _cff
    from server.optimisation_demo.demand import predict_at as _pa
    _m = _jl.load(_apath)
    for pdf in pdf_iter:
        if len(pdf) == 0:
            continue
        c = _cff(pdf, _factors, lambda f: _pa(_m, pdf, f))
        rows = [{"segment": s, "factor": float(fa),
                 "margin": float(v["expected_margin"]), "sales": float(v["expected_sales"])}
                for (s, fa), v in c.items()]
        yield pd.DataFrame(rows, columns=["segment", "factor", "margin", "sales"])

schema_out = "segment string, factor double, margin double, sales double"

def _run_distributed():
    part = sdf.mapInPandas(_score_partition, schema=schema_out)
    agg = part.groupBy("segment", "factor").sum("margin", "sales").collect()
    return {(r["segment"], round(float(r["factor"]), 6)):
            {"expected_margin": float(r["sum(margin)"]), "expected_sales": float(r["sum(sales)"])}
            for r in agg}

# Cold = full distributed scoring; then persist the scored coefficients to a hash-keyed
# cache. Warm = a COMPATIBLE re-solve (e.g. a different objective/threshold, which does not
# change the coefficients) reads the cache and skips scoring entirely. (`.cache()` is a
# PERSIST that serverless rejects, so the reuse is demonstrated via the coefficient cache,
# which is also what the brief asks for.)
grid_h = scale.hash_grid(factors)
world_h = scale.hash_world(1.0, 1.0)
input_h = hashlib.sha256(f"{man['future_delta_version']}|{n_opps}".encode()).hexdigest()
cache_key = scale.coeff_cache_key(input_hash=input_h, model_hash=man["artifact_hash"],
                                  feature_hash=scale._h(list(FEATURES)), grid_hash=grid_h, world_hash=world_h)
spark.sql(f"""CREATE TABLE IF NOT EXISTS {fqn}.optimisation_demo_scale_coeff_cache (
  cache_key STRING, segment STRING, factor DOUBLE, expected_margin DOUBLE, expected_sales DOUBLE)""")
spark.sql(f"DELETE FROM {fqn}.optimisation_demo_scale_coeff_cache WHERE cache_key = '{cache_key}'")

t0 = time.monotonic(); dist_cold = _run_distributed(); dist_cold_s = time.monotonic() - t0
from pyspark.sql import Row as _Row
spark.createDataFrame([_Row(cache_key=cache_key, segment=s, factor=float(f),
                            expected_margin=v["expected_margin"], expected_sales=v["expected_sales"])
                       for (s, f), v in dist_cold.items()]) \
     .write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_scale_coeff_cache")

t0 = time.monotonic()
cached = spark.sql(f"SELECT segment, factor, expected_margin, expected_sales FROM "
                   f"{fqn}.optimisation_demo_scale_coeff_cache WHERE cache_key = '{cache_key}'").collect()
dist_warm = {(r["segment"], round(float(r["factor"]), 6)):
             {"expected_margin": float(r["expected_margin"]), "expected_sales": float(r["expected_sales"])}
             for r in cached}
dist_warm_s = time.monotonic() - t0

# COMMAND ----------
# 3. Verify agreement BEFORE reporting timings. Normalise serial keys to rounded factors.
serial_norm = {(s, round(float(f), 6)): v for (s, f), v in serial.items()}
agree = scale.coefficients_agree(serial_norm, dist_cold, rtol=1e-6, atol=1e-4)
timings = scale.duration_breakdown(prep_s=0.0, score_s=dist_cold_s, solve_s=0.0, startup_s=0.0)

# COMMAND ----------
# 4. Persist receipts (counts, partitions, durations, agreement). Honest: we report measured
#    durations only; we do NOT assert a speedup unless the numbers show one.
spark.sql(f"""CREATE TABLE IF NOT EXISTS {fqn}.optimisation_demo_scale_runs (
  run_id STRING, preset STRING, n_opportunities LONG, n_factors INT, n_partitions INT,
  serial_score_s DOUBLE, distributed_cold_s DOUBLE, distributed_warm_s DOUBLE,
  coefficients_agree BOOLEAN, max_abs_diff DOUBLE, max_rel_diff DOUBLE,
  measured_speedup_cold DOUBLE, job_run_id STRING, created_at TIMESTAMP)""")
spark.sql(f"DELETE FROM {fqn}.optimisation_demo_scale_runs WHERE run_id = '{app_run_id}'")
try:
    job_run_id = str(dbutils.notebook.entry_point.getDbutils().notebook().getContext().jobId().get())
except Exception:
    job_run_id = ""
speedup = round(serial_s / dist_cold_s, 3) if dist_cold_s > 0 else None
from pyspark.sql import Row
schema_runs = spark.table(f"{fqn}.optimisation_demo_scale_runs").schema
row = {"run_id": app_run_id, "preset": preset, "n_opportunities": int(n_opps), "n_factors": int(len(factors)),
       "n_partitions": int(n_parts), "serial_score_s": float(serial_s),
       "distributed_cold_s": float(dist_cold_s), "distributed_warm_s": float(dist_warm_s),
       "coefficients_agree": bool(agree["ok"]), "max_abs_diff": float(agree["max_abs_diff"]),
       "max_rel_diff": float(agree["max_rel_diff"]),
       "measured_speedup_cold": (float(speedup) if speedup is not None else None),
       "job_run_id": job_run_id, "created_at": datetime.now(timezone.utc)}
spark.createDataFrame([tuple(row[f.name] for f in schema_runs.fields)], schema=schema_runs) \
    .write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_scale_runs")

dbutils.notebook.exit(json.dumps({
    "app_run_id": app_run_id, "preset": preset, "n_opportunities": n_opps,
    "n_factors": len(factors), "n_partitions": n_parts,
    "coefficients_agree": agree["ok"], "max_abs_diff": agree["max_abs_diff"],
    "serial_score_s": round(serial_s, 3), "distributed_cold_s": round(dist_cold_s, 3),
    "distributed_warm_s": round(dist_warm_s, 3), "measured_speedup_cold": speedup,
    "note": ("scale is primarily in scoring/scenario evaluation; the segment-level MILP is "
             "unchanged unless solver dimensions grow")}))

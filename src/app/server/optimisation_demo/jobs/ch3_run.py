# Databricks notebook source
# MAGIC %md
# MAGIC # Optimisation demo — Chapter 3 RUN (robust decision across worlds)
# MAGIC Build the world set (validated demand models × declared market/cost scenarios),
# MAGIC score each world, and solve baseline / nominal / robust plans on the SAME inherited
# MAGIC candidate grid + sales-protection ratio. Saves worlds + plan-by-world comparison,
# MAGIC keyed by the application run id. Live preset only; honest model count.

# COMMAND ----------
import json, sys
from datetime import datetime, timezone

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name", "pricing_workbench_gen2")
dbutils.widgets.text("app_src_base", "")
dbutils.widgets.text("app_run_id", "")
dbutils.widgets.text("sales_ratio", "0.98")
catalog = dbutils.widgets.get("catalog_name"); schema = dbutils.widgets.get("schema_name")
app_run_id = dbutils.widgets.get("app_run_id").strip()
sales_ratio = float(dbutils.widgets.get("sales_ratio") or "0.98")
fqn = f"{catalog}.{schema}"
if not app_run_id:
    raise ValueError("app_run_id is required")
src_base = dbutils.widgets.get("app_src_base").strip()
if src_base and src_base not in sys.path:
    sys.path.insert(0, src_base)
from server.optimisation_demo.data import make_historic, time_split, make_future  # noqa: E402
from server.optimisation_demo.demand import train_logistic, train_monotone_gbt, predict_at, monotone_along_price  # noqa: E402
from server.optimisation_demo.economics import coefficients_from_future  # noqa: E402
from server.optimisation_demo.robustness import solve_robust  # noqa: E402
from server.optimisation_demo.schemas import DEFAULT_FACTORS  # noqa: E402
from pyspark.sql import Row  # noqa: E402

# COMMAND ----------
# Validated demand model set — only models whose price path is monotone are eligible.
train, _, _ = time_split(make_historic())
future = make_future()
candidate_models = {"logistic": train_logistic(train), "gbt_monotone": train_monotone_gbt(train)}
models = {name: m for name, m in candidate_models.items() if monotone_along_price(m, future)}
if not models:
    raise ValueError("no demand model passed the monotone price-path check")

# Declared market/cost stress scenarios (Live preset): unchanged, benchmark -3%, claims +5%.
scenarios = [(1.00, 1.00, "unchanged"), (0.97, 1.00, "market -3%"), (1.00, 1.05, "claims +5%")]
factors = DEFAULT_FACTORS

# COMMAND ----------
# Score every world (model × scenario): segment-candidate margin/sales + baseline.
worlds, world_meta = [], []
M, V, BM, BS = {}, {}, {}, {}
segments = sorted(future["segment"].unique().tolist())
for mname, model in models.items():
    for mkt, cost, label in scenarios:
        wid = f"{mname}|{label}"
        worlds.append(wid)
        world_meta.append((wid, mname, float(mkt), float(cost), label))
        fut_w = future.copy()
        fut_w["market_premium"] = fut_w["market_premium"] * mkt
        fut_w["expected_claims"] = fut_w["expected_claims"] * cost
        coeffs = coefficients_from_future(fut_w, factors, lambda f, _m=model, _fw=fut_w: predict_at(_m, _fw, f))
        for (s, f), c in coeffs.items():
            M[(wid, s, f)] = c["expected_margin"]; V[(wid, s, f)] = c["expected_sales"]
        BM[wid] = sum(coeffs[(s, 1.0)]["expected_margin"] for s in segments)
        BS[wid] = sum(coeffs[(s, 1.0)]["expected_sales"] for s in segments)

cands = {s: factors for s in segments}
robust = solve_robust(worlds, segments, cands, M, V, BM, BS, sales_ratio=sales_ratio, objective="robust")
nominal = solve_robust(worlds, segments, cands, M, V, BM, BS, sales_ratio=sales_ratio, objective="nominal")
plans = {"baseline": {s: 1.0 for s in segments}}
if robust["feasible"]:
    plans["robust"] = robust["selection"]
if nominal["feasible"]:
    plans["nominal"] = nominal["selection"]

# COMMAND ----------
# Persist worlds + plan-by-world comparison + run record, keyed by app_run_id (idempotent).
for t, cols in [
    ("optimisation_demo_ch3_worlds", "run_id STRING, world_id STRING, model STRING, market_scale DOUBLE, cost_scale DOUBLE, label STRING"),
    ("optimisation_demo_ch3_comparison", "run_id STRING, plan STRING, world_id STRING, uplift DOUBLE, margin DOUBLE, sales DOUBLE, meets_floor BOOLEAN"),
    ("optimisation_demo_ch3_selection", "run_id STRING, plan STRING, segment STRING, factor DOUBLE"),
    ("optimisation_demo_ch3_runs", "run_id STRING, sales_ratio DOUBLE, n_models INT, n_worlds INT, robust_worst_uplift DOUBLE, nominal_worst_uplift DOUBLE, job_run_id STRING, created_at TIMESTAMP")]:
    spark.sql(f"CREATE TABLE IF NOT EXISTS {fqn}.{t} ({cols})")
    spark.sql(f"DELETE FROM {fqn}.{t} WHERE run_id = '{app_run_id}'")

spark.createDataFrame([Row(run_id=app_run_id, world_id=w, model=m, market_scale=mkt, cost_scale=cost, label=lab)
                       for (w, m, mkt, cost, lab) in world_meta]).write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_ch3_worlds")

def plan_worst(sel):
    return min(sum(M[(w, s, sel[s])] for s in segments) - BM[w] for w in worlds)

comp_rows, sel_rows = [], []
for pname, sel in plans.items():
    for w in worlds:
        margin = sum(M[(w, s, sel[s])] for s in segments)
        sales = sum(V[(w, s, sel[s])] for s in segments)
        comp_rows.append(Row(run_id=app_run_id, plan=pname, world_id=w, uplift=float(margin - BM[w]),
                             margin=float(margin), sales=float(sales),
                             meets_floor=bool(sales >= sales_ratio * BS[w] - 1e-6)))
    for s in segments:
        sel_rows.append(Row(run_id=app_run_id, plan=pname, segment=s, factor=float(sel[s])))
spark.createDataFrame(comp_rows).write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_ch3_comparison")
spark.createDataFrame(sel_rows).write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_ch3_selection")

try:
    job_run_id = str(dbutils.notebook.entry_point.getDbutils().notebook().getContext().jobId().get())
except Exception:
    job_run_id = ""
spark.createDataFrame([Row(run_id=app_run_id, sales_ratio=float(sales_ratio), n_models=len(models), n_worlds=len(worlds),
                           robust_worst_uplift=(float(robust["worst_uplift"]) if robust["feasible"] else None),
                           nominal_worst_uplift=(float(plan_worst(plans["nominal"])) if "nominal" in plans else None),
                           job_run_id=job_run_id, created_at=datetime.now(timezone.utc))]
                      ).write.mode("append").saveAsTable(f"{fqn}.optimisation_demo_ch3_runs")

dbutils.notebook.exit(json.dumps({
    "app_run_id": app_run_id, "n_models": len(models), "n_worlds": len(worlds),
    "robust_worst_uplift": robust.get("worst_uplift"),
    "nominal_worst_uplift": (plan_worst(plans["nominal"]) if "nominal" in plans else None)}))

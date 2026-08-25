# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — immutable decision records (§11)
# MAGIC
# MAGIC Every factor deployment leaves a reproducible decision record: the data
# MAGIC snapshot it was solved on, the elasticity model versions, the constraint
# MAGIC YAML version, the CHOSEN scenario **and the rejected alternatives with their
# MAGIC trade-offs**, the fairness review, the approver + timestamp, and a pointer to
# MAGIC re-run the exact solve. This notebook (a) creates the table, (b) seeds an
# MAGIC initial deployment if the demo has none yet, and (c) backfills a record for
# MAGIC every deployment that lacks one. The app writes records inline on each new
# MAGIC deploy; this is the canonical/backfill builder (it resolves real model
# MAGIC versions via MLflow).

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
fqn = f"{catalog}.{schema}"

import json, uuid
import pyspark.sql.functions as F
import mlflow
mlflow.set_registry_uri("databricks-uc")
mc = mlflow.tracking.MlflowClient()

SOLVER_JOB = "Price optimisation — constrained solver (gen2)"

def champion_version(name):
    try:
        return mc.get_model_version_by_alias(f"{fqn}.{name}", "champion").version
    except Exception:
        try:
            return str(max(int(v.version) for v in mc.search_model_versions(f"name='{fqn}.{name}'")))
        except Exception:
            return None

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Table + (if empty) seed an initial deployment

# COMMAND ----------

spark.sql(f"""
  CREATE TABLE IF NOT EXISTS {fqn}.optimisation_decision_records (
    decision_id STRING, deployment_id STRING, created_at TIMESTAMP, approver STRING,
    constraint_version STRING,
    conversion_model STRING, conversion_model_version STRING,
    retention_model STRING, retention_model_version STRING,
    data_snapshot STRING, objective STRING,
    chosen_json STRING, rejected_json STRING,
    fairness_pass BOOLEAN, fairness_summary STRING,
    rerun_pointer STRING, factors_json STRING)
""")

# ensure a deployment exists so the demo has a record to show
dep = spark.table(f"{fqn}.optimisation_deployment").toPandas() if spark.catalog.tableExists(f"{fqn}.optimisation_deployment") else None
if dep is None or len(dep) == 0:
    cver = spark.table(f"{fqn}.optimisation_factor_table").select("constraint_version").limit(1).collect()
    cver = cver[0][0] if cver else "v1"
    nseg = spark.table(f"{fqn}.optimisation_factor_table").count()
    spark.sql(f"""INSERT INTO {fqn}.optimisation_deployment
                  SELECT uuid(), '{cver}', {nseg}, 'pricing_committee@bricksurance.example',
                         'initial rate deployment', current_timestamp()""")
    dep = spark.table(f"{fqn}.optimisation_deployment").toPandas()
print(f"{len(dep)} deployment(s) on the timeline")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Assemble chosen + rejected alternatives from the frontier

# COMMAND ----------

fac = spark.table(f"{fqn}.optimisation_factor_table").toPandas()
for c in ["factor", "factor_pct", "conversion_opt", "policies", "expected_profit_opt", "expected_profit_hold", "profit_uplift"]:
    if c in fac.columns:
        fac[c] = fac[c].astype(float)
chosen = {
    "objective": "expected_profit",
    "segments": int(len(fac)),
    "expected_profit_opt": round(float(fac["expected_profit_opt"].sum()), 2),
    "expected_profit_hold": round(float(fac["expected_profit_hold"].sum()), 2),
    "profit_uplift": round(float(fac["profit_uplift"].sum()), 2),
    "expected_volume": round(float((fac["conversion_opt"] * fac["policies"]).sum()), 0),
}
factors_json = fac[["segment", "factor_pct", "conversion_opt", "profit_uplift", "binding"]].to_dict("records")

scen = spark.table(f"{fqn}.optimisation_scenarios").toPandas()
for c in ["expected_profit", "expected_volume"]:
    scen[c] = scen[c].astype(float)
hold = scen[scen.scenario_id == "hold"]
best_profit = scen.sort_values("expected_profit", ascending=False).iloc[0]
best_volume = scen.sort_values("expected_volume", ascending=False).iloc[0]
def _alt(label, row, note):
    return {"label": label, "expected_profit": round(float(row["expected_profit"]), 2),
            "expected_volume": round(float(row["expected_volume"]), 0), "note": note}
rejected = []
if len(hold):
    rejected.append(_alt("Hold (no change)", hold.iloc[0], "status quo — the book as priced today"))
rejected.append(_alt("Max-volume frontier point", best_volume,
                     f"+{best_volume['expected_volume']-chosen['expected_volume']:,.0f} volume but "
                     f"£{chosen['expected_profit_opt']-best_volume['expected_profit']:,.0f} less profit vs chosen"))
rejected.append(_alt("Max-profit frontier point", best_profit,
                     f"£{best_profit['expected_profit']-chosen['expected_profit_opt']:,.0f} more profit but "
                     f"{chosen['expected_volume']-best_volume['expected_volume']:,.0f} less volume — beyond the retention appetite"))

# fairness + snapshot + versions
try:
    fs = spark.table(f"{fqn}.optimisation_fairness_summary").toPandas().iloc[0]
    fairness_pass = bool(fs["overall_pass"]); fairness_summary = str(fs["evidence"])[:1500]
except Exception:
    fairness_pass, fairness_summary = None, "fairness screen not available"
try:
    qr = spark.table(f"{fqn}.optimisation_quote_response")
    latest = qr.agg(F.max("quote_month")).collect()[0][0]
    snap = f"optimisation_quote_response @ {latest}, {qr.count():,} quotes; book {spark.table(f'{fqn}.optimisation_portfolio_snapshot').count():,} policies"
except Exception:
    snap = "snapshot unavailable"
cv, rv = champion_version("conversion_elasticity_motor"), champion_version("retention_elasticity_motor")
rerun = f"job='{SOLVER_JOB}' params: objective=expected_profit, constraint_version={fac['constraint_version'].iloc[0] if len(fac) else 'v1'}"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Backfill a record for every deployment lacking one

# COMMAND ----------

have = set(r["deployment_id"] for r in
           spark.table(f"{fqn}.optimisation_decision_records").select("deployment_id").collect())
new_rows = []
for _, d in dep.iterrows():
    if d["deployment_id"] in have:
        continue
    new_rows.append({
        "decision_id": str(uuid.uuid4()), "deployment_id": d["deployment_id"],
        "created_at": d["deployed_at"], "approver": d["approver"],
        "constraint_version": d["constraint_version"],
        "conversion_model": f"{fqn}.conversion_elasticity_motor@champion", "conversion_model_version": cv,
        "retention_model": f"{fqn}.retention_elasticity_motor@champion", "retention_model_version": rv,
        "data_snapshot": snap, "objective": chosen["objective"],
        "chosen_json": json.dumps(chosen), "rejected_json": json.dumps(rejected),
        "fairness_pass": fairness_pass, "fairness_summary": fairness_summary,
        "rerun_pointer": rerun, "factors_json": json.dumps(factors_json),
    })

if new_rows:
    import pandas as pd
    (spark.createDataFrame(pd.DataFrame(new_rows))
        .write.mode("append").option("mergeSchema", "true")
        .saveAsTable(f"{fqn}.optimisation_decision_records"))
print(f"optimisation_decision_records: +{len(new_rows)} backfilled; "
      f"{spark.table(f'{fqn}.optimisation_decision_records').count()} total")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({"backfilled": len(new_rows)}))

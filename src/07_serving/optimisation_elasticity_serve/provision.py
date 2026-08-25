# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — real-time elasticity scorer (§7B, defined-but-dormant)
# MAGIC
# MAGIC Arms Pattern B: the conversion-elasticity model as a **Model Serving
# MAGIC endpoint** (`pwg2_elasticity_scorer`), so the pricing function can query
# MAGIC "what is P(convert) at this candidate price?" in real time instead of reading
# MAGIC the batch curve. The model is a plain LightGBM (no FeatureLookup), so callers
# MAGIC send a feature vector directly — no online store required.
# MAGIC
# MAGIC This tier ships **dormant**; run this job to arm it (scale-to-zero, so it costs
# MAGIC nothing idle) and the teardown job to remove it. The batch spine is unaffected
# MAGIC either way — execution mode is a config flag, not an architecture.

# COMMAND ----------

dbutils.widgets.text("catalog_name",  "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",   "pricing_workbench_gen2")
dbutils.widgets.text("endpoint_name", "pwg2_elasticity_scorer")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
endpoint_name = dbutils.widgets.get("endpoint_name")
model_name = f"{catalog}.{schema}.conversion_elasticity_motor"

import time, json
import mlflow
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import (EndpointCoreConfigInput, ServedEntityInput,
                                            TrafficConfig, Route)
mlflow.set_registry_uri("databricks-uc")
mc = mlflow.MlflowClient()
w = WorkspaceClient()

# COMMAND ----------

# Resolve the champion version (fall back to latest).
try:
    ver = mc.get_model_version_by_alias(model_name, "champion").version
except Exception:
    ver = sorted(mc.search_model_versions(f"name='{model_name}'"),
                 key=lambda v: int(v.version), reverse=True)[0].version
print(f"serving {model_name} v{ver} → {endpoint_name}")

served = [ServedEntityInput(entity_name=model_name, entity_version=ver, name="champion",
                            workload_size="Small", scale_to_zero_enabled=True)]
routes = [Route(served_model_name="champion", traffic_percentage=100)]
config = EndpointCoreConfigInput(served_entities=served, traffic_config=TrafficConfig(routes=routes))

try:
    w.serving_endpoints.get(endpoint_name)
    w.serving_endpoints.update_config(name=endpoint_name, served_entities=served,
                                      traffic_config=TrafficConfig(routes=routes))
    print("updated existing endpoint")
except Exception:
    w.serving_endpoints.create(name=endpoint_name, config=config)
    print("creating new endpoint")

# COMMAND ----------

for i in range(60):
    ep = w.serving_endpoints.get(endpoint_name)
    state = str(ep.state.ready) if ep.state else "UNKNOWN"
    if state == "EndpointStateReady.READY":
        print(f"✓ {endpoint_name} READY (~{i*10}s)")
        break
    print(f"  {state} ({i*10}s)")
    time.sleep(10)

# COMMAND ----------

# MAGIC %run ../../utils/audit

# COMMAND ----------

try:
    log_event(spark, catalog, schema, event_type="optimisation_serving_armed",
              entity_type="endpoint", entity_id=endpoint_name, entity_version=f"champion=v{ver}",
              user_id="optimiser", details={"model": model_name, "version": ver}, source="notebook")
except Exception as e:
    print(f"audit skipped: {e}")

dbutils.notebook.exit(json.dumps({"endpoint": endpoint_name, "version": ver, "state": "armed"}))

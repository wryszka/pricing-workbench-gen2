# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — real-time elasticity scorer: teardown
# MAGIC Removes the `pwg2_elasticity_scorer` endpoint. The batch spine is unaffected.
# MAGIC Idempotent — a no-op if the endpoint isn't there.

# COMMAND ----------

dbutils.widgets.text("catalog_name",  "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",   "pricing_workbench_gen2")
dbutils.widgets.text("endpoint_name", "pwg2_elasticity_scorer")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
endpoint_name = dbutils.widgets.get("endpoint_name")

import json
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

# COMMAND ----------

try:
    w.serving_endpoints.delete(endpoint_name)
    print(f"✓ deleted endpoint {endpoint_name}")
    state = "torn_down"
except Exception as e:
    print(f"endpoint {endpoint_name} not deleted (may not exist): {str(e)[:120]}")
    state = "absent"

# COMMAND ----------

# MAGIC %run ../../utils/audit

# COMMAND ----------

try:
    log_event(spark, catalog, schema, event_type="optimisation_serving_torn_down",
              entity_type="endpoint", entity_id=endpoint_name, entity_version="-",
              user_id="optimiser", details={"endpoint": endpoint_name}, source="notebook")
except Exception as e:
    print(f"audit skipped: {e}")

dbutils.notebook.exit(json.dumps({"endpoint": endpoint_name, "state": state}))

# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimisation — deploy as a governed UC PROCEDURE (the gate = a UC privilege)
# MAGIC
# MAGIC **Platform-native gate (playbook v2.3 §6.C/D):** the deploy action — the
# MAGIC server-side corridor re-check, the write to `optimisation_deployment`, and the
# MAGIC immutable `audit_log` row — lives in a **Unity Catalog stored procedure**, not
# MAGIC in app Python. RBAC is a **UC `EXECUTE` grant** on the procedure, not an
# MAGIC `ADMIN_USERS` check in the app. Called as the user via OBO, UC enforces the
# MAGIC grant per-person; `p_approver` carries the trusted forwarded email for the
# MAGIC audit record.
# MAGIC
# MAGIC `SQL SECURITY DEFINER` so the body's writes run with the owner's privileges —
# MAGIC the caller needs only `EXECUTE`, nothing else. Idempotent.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
dbutils.widgets.text("admin_users",  "laurence.ryszka@databricks.com,sa-presenter@databricks.com")
dbutils.widgets.text("app_service_principal_id", "")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
admins  = [u.strip() for u in dbutils.widgets.get("admin_users").split(",") if u.strip()]
app_sp  = dbutils.widgets.get("app_service_principal_id").strip()
fqn = f"{catalog}.{schema}"

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE PROCEDURE {fqn}.deploy_factor_set(p_note STRING, p_approver STRING)
LANGUAGE SQL
SQL SECURITY DEFINER
COMMENT 'Governed deploy of the solved factor set: server-side corridor re-check + writes optimisation_deployment + audit_log. RBAC = EXECUTE grant on this procedure (playbook v2.3 platform-native gate). Call as the user via OBO so UC enforces the grant per-person; p_approver = trusted forwarded email for the audit record.'
AS BEGIN
  DECLARE v_breaches INT DEFAULT 0;
  DECLARE v_cver STRING;
  DECLARE v_segs INT;
  DECLARE v_raise STRING;
  DECLARE v_who STRING;
  SET v_who = COALESCE(NULLIF(p_approver, ''), current_user());
  SET v_breaches = (SELECT count(*) FROM {fqn}.optimisation_factor_table WHERE within_corridor = false);
  IF v_breaches > 0 THEN
    SET v_raise = RAISE_ERROR('deploy blocked: ' || CAST(v_breaches AS STRING) || ' segment(s) outside the corridor');
  END IF;
  SET v_cver = (SELECT max(constraint_version) FROM {fqn}.optimisation_factor_table);
  SET v_segs = (SELECT count(*) FROM {fqn}.optimisation_factor_table);
  INSERT INTO {fqn}.optimisation_deployment
    SELECT uuid(), v_cver, v_segs, v_who, p_note, current_timestamp();
  INSERT INTO {fqn}.audit_log (event_id, event_type, entity_type, entity_id, entity_version, user_id, timestamp, details, source)
    SELECT uuid(), 'optimisation_deploy_approved', 'factor_table', v_cver, v_cver, v_who, current_timestamp(),
           to_json(named_struct('segments', v_segs, 'note', p_note, 'via', 'uc_procedure', 'uc_caller', current_user())), 'deploy_factor_set';
END
""")
print("procedure deploy_factor_set created")

# COMMAND ----------

# RBAC as UC privilege: only admins (and, for the pre-OBO interim, the app SP) may
# EXECUTE. When app user-authorization (OBO) is enabled, the CALL runs as the user
# and UC enforces this grant per-person — the app-side ADMIN_USERS check is then
# removed and the app-SP grant revoked.
grantees = list(admins) + ([app_sp] if app_sp else [])
for g in grantees:
    spark.sql(f"GRANT EXECUTE ON PROCEDURE {fqn}.deploy_factor_set TO `{g}`")
    print("granted EXECUTE to", g)

import json
dbutils.notebook.exit(json.dumps({"procedure": f"{fqn}.deploy_factor_set", "execute_granted_to": grantees}))

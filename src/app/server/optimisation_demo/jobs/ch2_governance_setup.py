# Databricks notebook source
# MAGIC %md
# MAGIC # Optimisation demo — Chapter 2 GOVERNANCE setup
# MAGIC Creates the append-only approval + release tables and a UC stored procedure
# MAGIC `optimisation_demo_ch2_approve` whose **EXECUTE grant is the approval gate**.
# MAGIC Called via OBO as the logged-in user → Unity Catalog enforces per-person: only
# MAGIC approvers can approve/release. Idempotent.

# COMMAND ----------
import json

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name", "pricing_workbench_gen2")
dbutils.widgets.text("approver_users", "laurence.ryszka@databricks.com")
catalog = dbutils.widgets.get("catalog_name"); schema = dbutils.widgets.get("schema_name")
approvers = [u.strip() for u in dbutils.widgets.get("approver_users").split(",") if u.strip()]
fqn = f"{catalog}.{schema}"

# COMMAND ----------
# Append-only approval + release event tables (never updated in place).
spark.sql(f"""CREATE TABLE IF NOT EXISTS {fqn}.optimisation_demo_ch2_approvals (
  approval_id STRING, run_id STRING, plan_hash STRING, approver STRING, note STRING, approved_at TIMESTAMP
) TBLPROPERTIES ('delta.appendOnly' = 'true')""")
spark.sql(f"""CREATE TABLE IF NOT EXISTS {fqn}.optimisation_demo_ch2_releases (
  release_id STRING, run_id STRING, plan_hash STRING, approver STRING,
  previous_release_id STRING, released_at TIMESTAMP
) TBLPROPERTIES ('delta.appendOnly' = 'true')""")
for t in ("optimisation_demo_ch2_approvals", "optimisation_demo_ch2_releases"):
    try:
        spark.sql(f"ALTER TABLE {fqn}.{t} SET TBLPROPERTIES ('delta.appendOnly' = 'true')")
    except Exception as e:
        print("appendOnly set skipped:", str(e)[:100])

# COMMAND ----------
# The approval action as a governed UC procedure. SQL SECURITY DEFINER so the caller
# needs only EXECUTE (the gate); the append-only writes run with the owner's rights.
# The active release is resolved as the most recent row — rollback is a new release
# event pointing at an earlier run, never an in-place update.
spark.sql(f"""
CREATE OR REPLACE PROCEDURE {fqn}.optimisation_demo_ch2_approve(
    p_run_id STRING, p_plan_hash STRING, p_approver STRING, p_note STRING)
LANGUAGE SQL
SQL SECURITY DEFINER
COMMENT 'Approve + release a Chapter 2 plan. Approval gate = EXECUTE grant on this procedure (approver-only), called via OBO as the user. Appends approval + release events.'
AS BEGIN
  DECLARE v_status STRING;
  DECLARE v_prev STRING;
  DECLARE v_rel STRING;
  DECLARE v_who STRING;
  DECLARE v_raise STRING;
  SET v_who = COALESCE(NULLIF(p_approver, ''), current_user());
  SET v_status = (SELECT status FROM {fqn}.optimisation_demo_ch2_runs WHERE run_id = p_run_id);
  IF v_status IS NULL THEN
    SET v_raise = RAISE_ERROR('approve blocked: run not found ' || p_run_id);
  END IF;
  IF v_status <> 'complete' THEN
    SET v_raise = RAISE_ERROR('approve blocked: run status is ' || v_status || ', not complete');
  END IF;
  SET v_prev = (SELECT release_id FROM {fqn}.optimisation_demo_ch2_releases ORDER BY released_at DESC LIMIT 1);
  SET v_rel = uuid();
  INSERT INTO {fqn}.optimisation_demo_ch2_releases
    SELECT v_rel, p_run_id, p_plan_hash, v_who, v_prev, current_timestamp();
  INSERT INTO {fqn}.optimisation_demo_ch2_approvals
    SELECT uuid(), p_run_id, p_plan_hash, v_who, p_note, current_timestamp();
END
""")
print("procedure optimisation_demo_ch2_approve created")

# COMMAND ----------
# EXECUTE grant = the gate. Approvers only. Resilient per-grantee (placeholder-safe).
granted, skipped = [], []
for g in approvers:
    try:
        spark.sql(f"GRANT EXECUTE ON PROCEDURE {fqn}.optimisation_demo_ch2_approve TO `{g}`")
        granted.append(g)
    except Exception as e:
        skipped.append(f"{g}: {str(e)[:100]}")
print("granted EXECUTE:", granted, "| skipped:", skipped)
dbutils.notebook.exit(json.dumps({"procedure": f"{fqn}.optimisation_demo_ch2_approve",
                                  "granted": granted, "skipped": skipped}))

# Databricks notebook source
# MAGIC %md
# MAGIC # Demo reset
# MAGIC
# MAGIC One-shot reset to clean demo state. Run from the landing page reset
# MAGIC button. Idempotent — safe to re-run.
# MAGIC
# MAGIC What it does:
# MAGIC
# MAGIC | Item | Reset to |
# MAGIC |---|---|
# MAGIC | UC champion aliases (4 model families) | re-assert @champion → latest version (kept if already set) |
# MAGIC | `rating_engine_config` table | re-seeded rolling — v2.0 champion effective ~6 months ago, history rebased to today |
# MAGIC | `pricing_engine_releases` table | re-seeded rolling — LIVE release = current month, history steps back month-by-month |
# MAGIC | Dataset dates (quotes, policies, claims, inference, UPT) | uniform shift forward so latest activity = today (no retrain) |
# MAGIC | `compare_results` table | truncate (transient demo output) |
# MAGIC | `historical_quote_scores` table | truncate (transient demo output) |
# MAGIC | `inference_logs` rows where `is_mta = true` | delete (transient MTA simulations) |
# MAGIC | Geospatial vendor refresh state | re-seed so the impact tab shows the 25k-policy story |
# MAGIC | Audit log | NOT cleared — append a `demo_reset` event so the reset itself is auditable |

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
# App service principal + warehouse — passed by the bundle so the reset can
# self-heal the CAN_USE grant that external ACL rewrites keep wiping (the
# recurring "app shows 500 on SQL-backed pages" failure). Blank = skip.
dbutils.widgets.text("app_service_principal_id", "")
dbutils.widgets.text("warehouse_id", "")

catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
app_sp  = dbutils.widgets.get("app_service_principal_id").strip()
wh_id   = dbutils.widgets.get("warehouse_id").strip()
fqn     = f"{catalog}.{schema}"

import json
from datetime import datetime

# Families whose champion alias we (re)assert on reset. We resolve the version
# at runtime rather than hardcoding it — hardcoded version numbers don't exist
# on a fresh deploy, so the aliases would silently fail and the demo would show
# stale/missing champions.
FAMILIES = ["freq_glm", "sev_glm", "demand_gbm", "fraud_gbm"]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Reset UC champion aliases

# COMMAND ----------

from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

# --- Self-heal: ensure the app SP can use the SQL warehouse -----------------
# External ACL rewrites in this workspace periodically strip the app SP's
# CAN_USE grant on the warehouse, which 500s every SQL-backed page. Re-assert
# it here (idempotent, additive PATCH — leaves other grantees untouched).
if app_sp and wh_id:
    try:
        from databricks.sdk.service.sql import (
            WarehouseAccessControlRequest, WarehousePermissionLevel,
        )
        w.warehouses.update_permissions(
            warehouse_id=wh_id,
            access_control_list=[WarehouseAccessControlRequest(
                service_principal_name=app_sp,
                permission_level=WarehousePermissionLevel.CAN_USE,
            )],
        )
        print(f"✓ warehouse grant re-asserted: {app_sp} → CAN_USE on {wh_id}")
    except Exception as e:
        print(f"⚠ warehouse grant re-assert failed (non-fatal): {str(e)[:160]}")
else:
    print("ℹ warehouse grant self-heal skipped (app_service_principal_id / warehouse_id not set)")

def _latest_version(full_name: str) -> int | None:
    """Highest registered version for a UC model, or None if unregistered."""
    try:
        vers = [int(v.version) for v in w.model_versions.list(full_name=full_name)]
        return max(vers) if vers else None
    except Exception:
        return None

alias_results = {}
for fam in FAMILIES:
    full = f"{fqn}.{fam}"
    # Keep the existing champion if one is set; otherwise pin the latest version.
    try:
        existing = w.registered_models.get_alias(full_name=full, alias="champion")
        ver = int(existing.version_num)
        alias_results[fam] = f"champion already set → v{ver} (unchanged)"
        continue
    except Exception:
        pass
    ver = _latest_version(full)
    if ver is None:
        alias_results[fam] = "SKIPPED: model not registered on this workspace"
        continue
    try:
        w.registered_models.set_alias(full_name=full, alias="champion", version_num=ver)
        alias_results[fam] = f"champion → v{ver} (latest)"
    except Exception as e:
        alias_results[fam] = f"FAILED: {str(e)[:120]}"
print("Champion aliases:")
for k, v in alias_results.items(): print(f"  {k}: {v}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Re-anchor the rolling rate-book to the current month
# MAGIC
# MAGIC Re-run the release + rating-config seeds (idempotent CREATE OR REPLACE).
# MAGIC They rebuild a rolling series anchored on today, so the LIVE release is
# MAGIC THIS month (champion) and the history steps back month-by-month — never
# MAGIC a fixed date that ages.

# COMMAND ----------

# The seed notebooks are siblings of this notebook (04_models/production/).
for _nb, _label in [("pricing_engine_releases_seed", "pricing engine releases"),
                    ("rating_engine_seed",           "rating engine config")]:
    try:
        dbutils.notebook.run(_nb, 600, {"catalog_name": catalog, "schema_name": schema})
        print(f"✓ re-seeded {_label} → rolling, champion = current month")
    except Exception as _e:
        print(f"⚠ re-seed {_label} failed (non-fatal): {str(_e)[:160]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Re-anchor dataset dates to today (uniform block shift)
# MAGIC
# MAGIC Shift every dated fact table forward by the SAME delta so "latest
# MAGIC activity = today" while preserving all relative gaps (inception→renewal,
# MAGIC loss timing, quote window). No retrain — dates are labels here, not model
# MAGIC features. The delta is measured from the newest quote, so a fresh build
# MAGIC (already current) shifts by 0 and this is a no-op.

# COMMAND ----------

shift_info = {"delta_days": 0, "shifted": []}
try:
    _d = spark.sql(
        f"SELECT datediff(current_date(), to_date(max(created_at))) AS d FROM {fqn}.quotes"
    ).collect()
    delta = int(_d[0]["d"]) if _d and _d[0]["d"] is not None else 0
except Exception as _e:
    delta = 0
    print(f"⚠ could not compute shift delta (defaulting to 0): {str(_e)[:140]}")
shift_info["delta_days"] = delta

if delta > 0:
    # (table, column, kind): 'ts' = timestamp column, 'ds' = date-like column
    # (string 'yyyy-MM-dd' or DATE — the date_format expr casts back either way).
    _targets = [
        ("quotes",                        "created_at",     "ts"),
        ("inference_logs",                "scored_at",      "ts"),
        ("internal_commercial_policies",  "inception_date", "ds"),
        ("internal_commercial_policies",  "renewal_date",   "ds"),
        ("internal_claims_history",       "loss_date",      "ds"),
        ("unified_pricing_table_live",    "renewal_date",   "ds"),
        ("unified_pricing_table_live",    "inception_date", "ds"),
    ]
    for _t, _c, _k in _targets:
        try:
            if _k == "ts":
                spark.sql(f"UPDATE {fqn}.{_t} SET {_c} = {_c} + INTERVAL {delta} DAYS "
                          f"WHERE {_c} IS NOT NULL")
            else:
                spark.sql(f"UPDATE {fqn}.{_t} SET {_c} = "
                          f"date_format(date_add(to_date({_c}), {delta}), 'yyyy-MM-dd') "
                          f"WHERE {_c} IS NOT NULL")
            shift_info["shifted"].append(f"{_t}.{_c}")
        except Exception as _e:
            print(f"  shift {_t}.{_c} skipped: {str(_e)[:120]}")
    print(f"Shifted {len(shift_info['shifted'])} columns forward by {delta} days: "
          f"{shift_info['shifted']}")
else:
    print(f"Data already current (delta={delta}d) — no shift needed.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Truncate transient demo outputs

# COMMAND ----------

cleanup_counts = {}
# compare_results is intentionally NOT truncated — the Compare & Test tab
# auto-hydrates from the most recent cached run for the active family, so
# preserving prior runs gives the demo a populated landing state without
# needing a fresh job to fire mid-presentation.
for tbl in ("historical_quote_scores",):
    try:
        before = spark.table(f"{fqn}.{tbl}").count()
        spark.sql(f"TRUNCATE TABLE {fqn}.{tbl}")
        cleanup_counts[tbl] = f"{before} rows truncated"
    except Exception as e:
        cleanup_counts[tbl] = f"skipped: {str(e)[:120]}"

# Delete only MTA-simulated rows from inference_logs (keep the backfill)
try:
    n = spark.sql(f"SELECT COUNT(*) AS n FROM {fqn}.inference_logs WHERE is_mta = true").collect()[0]["n"]
    spark.sql(f"DELETE FROM {fqn}.inference_logs WHERE is_mta = true")
    cleanup_counts["inference_logs (is_mta=true)"] = f"{n} rows deleted"
except Exception as e:
    cleanup_counts["inference_logs (is_mta=true)"] = f"skipped: {str(e)[:120]}"

# Revert the geospatial dataset to pending-approval so the demo can walk
# through the HITL approval flow from a fresh state. The other ingestion
# datasets (market_pricing_benchmark, credit_bureau_summary) stay approved
# since they're the "already in production" baseline.
try:
    n = spark.sql(
        f"SELECT COUNT(*) AS n FROM {fqn}.dataset_approvals "
        f"WHERE dataset_name = 'geospatial_hazard_enrichment'"
    ).collect()[0]["n"]
    spark.sql(
        f"DELETE FROM {fqn}.dataset_approvals "
        f"WHERE dataset_name = 'geospatial_hazard_enrichment'"
    )
    cleanup_counts["dataset_approvals (geospatial)"] = f"{n} rows deleted — back to pending"
except Exception as e:
    cleanup_counts["dataset_approvals (geospatial)"] = f"skipped: {str(e)[:120]}"

print("Cleanup:")
for k, v in cleanup_counts.items(): print(f"  {k}: {v}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Re-seed geospatial vendor refresh
# MAGIC
# MAGIC So the Data Ingestion → Geospatial → Impact tab shows the 25k-policy
# MAGIC pricing impact story.

# COMMAND ----------

# Inline the seed (same as src/00_setup/seed_geospatial_vendor_refresh.sql)
spark.sql(f"""
    CREATE OR REPLACE TABLE {fqn}.raw_geospatial_hazard_enrichment AS
    WITH shifted_silver AS (
        SELECT
            postcode_sector,
            CASE
                WHEN abs(hash(concat(postcode_sector, 'flood_v2'))) % 100 < 15
                    THEN LEAST(10, flood_zone_rating + (abs(hash(postcode_sector)) % 3 + 1))
                WHEN abs(hash(concat(postcode_sector, 'flood_v2'))) % 100 < 30
                    THEN GREATEST(1, flood_zone_rating - (abs(hash(postcode_sector)) % 2 + 1))
                ELSE flood_zone_rating
            END AS flood_zone_rating,
            proximity_to_fire_station_km,
            CASE
                WHEN abs(hash(concat(postcode_sector, 'crime_v2'))) % 100 < 20
                    THEN ROUND(crime_theft_index * 1.15, 1)
                WHEN abs(hash(concat(postcode_sector, 'crime_v2'))) % 100 < 35
                    THEN ROUND(crime_theft_index * 0.90, 1)
                ELSE crime_theft_index
            END AS crime_theft_index,
            CASE
                WHEN abs(hash(concat(postcode_sector, 'subs_v2'))) % 100 < 8
                    THEN ROUND(LEAST(10.0, subsidence_risk + 1.5), 1)
                ELSE subsidence_risk
            END AS subsidence_risk,
            current_timestamp()                              AS _ingested_at,
            'manual_upload:vendor_refresh_2026_q2.csv'       AS _source_file
        FROM {fqn}.silver_geospatial_hazard_enrichment
    )
    SELECT * FROM shifted_silver
""")
n = spark.table(f"{fqn}.raw_geospatial_hazard_enrichment").count()
print(f"Geospatial raw vendor refresh re-seeded: {n} rows.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Re-seed protected-attribute cohorts on policy_demographics
# MAGIC
# MAGIC Idempotent. Adds ethnicity_proxy + director_age_band if missing — the
# MAGIC bias monitor reads four attributes off this table.

# COMMAND ----------

spark.sql(f"""
    CREATE OR REPLACE TABLE {fqn}.policy_demographics AS
    SELECT
      policy_id, director_gender, postcode_demographic,
      CASE postcode_demographic
        WHEN 'Q1_majority_white' THEN
          CASE WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 90 THEN 'White'
               WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 95 THEN 'Asian'
               WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 98 THEN 'Black'
               ELSE 'Mixed/Other' END
        WHEN 'Q2' THEN
          CASE WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 75 THEN 'White'
               WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 87 THEN 'Asian'
               WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 95 THEN 'Black'
               ELSE 'Mixed/Other' END
        WHEN 'Q3' THEN
          CASE WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 60 THEN 'White'
               WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 78 THEN 'Asian'
               WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 92 THEN 'Black'
               ELSE 'Mixed/Other' END
        WHEN 'Q4' THEN
          CASE WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 45 THEN 'White'
               WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 67 THEN 'Asian'
               WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 89 THEN 'Black'
               ELSE 'Mixed/Other' END
        WHEN 'Q5_most_diverse' THEN
          CASE WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 25 THEN 'White'
               WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 53 THEN 'Asian'
               WHEN abs(hash(concat(policy_id,'eth'))) % 100 < 85 THEN 'Black'
               ELSE 'Mixed/Other' END
        ELSE 'White'
      END AS ethnicity_proxy,
      CASE
        WHEN abs(hash(concat(policy_id,'age'))) % 100 < 18 THEN '25-34'
        WHEN abs(hash(concat(policy_id,'age'))) % 100 < 42 THEN '35-44'
        WHEN abs(hash(concat(policy_id,'age'))) % 100 < 68 THEN '45-54'
        WHEN abs(hash(concat(policy_id,'age'))) % 100 < 88 THEN '55-64'
        ELSE '65+'
      END AS director_age_band
    FROM {fqn}.policy_demographics
""")
print("policy_demographics rebuilt — ethnicity_proxy correlates with postcode_demographic.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Governance pack history
# MAGIC
# MAGIC No fake history is seeded here. Real, live-dated packs come from the
# MAGIC `generate_governance_packs` job (one multi-section PDF per champion), so
# MAGIC the Governance "by date" tab shows genuine, current packs — not rows that
# MAGIC point at PDF filenames which may not exist (the old cause of "no file"
# MAGIC errors). We only purge any legacy seed-history rows a prior build left.

# COMMAND ----------

try:
    _n = spark.sql(
        f"SELECT COUNT(*) AS n FROM {fqn}.governance_packs_index "
        f"WHERE story LIKE '[seed-history]%'"
    ).collect()[0]["n"]
    if _n:
        spark.sql(f"DELETE FROM {fqn}.governance_packs_index WHERE story LIKE '[seed-history]%'")
        print(f"Purged {_n} legacy seed-history pack rows.")
    else:
        print("No legacy seed-history pack rows to purge.")
except Exception as _e:
    print(f"⚠ governance pack purge skipped (non-fatal): {str(_e)[:140]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7.6 Reset the motor live-demo story (John → clean good driver)
# MAGIC
# MAGIC The black-box events accumulate in `motor_telematics_aggregate` and the
# MAGIC UPT; reset the demo driver back to a pristine good-driver baseline
# MAGIC (behaviour 75, zero recent events) in BOTH tables, then refresh the
# MAGIC Lakebase online store so the live endpoint serves the clean state.

# COMMAND ----------

MOTOR_DEMO_POLICY = "POL-MOTOR-00000001"
motor_reset = {"policy": MOTOR_DEMO_POLICY, "tables": [], "online_refresh": "skipped"}
try:
    for _tbl in ("motor_telematics_aggregate", "unified_motor_table_live"):
        try:
            spark.sql(f"""
                UPDATE {fqn}.{_tbl} SET
                    behaviour_score          = 75,
                    recent_speeding_events   = 0,
                    recent_curfew_breaches   = 0,
                    recent_harsh_braking_30d = 0
                WHERE policy_id = '{MOTOR_DEMO_POLICY}'
            """)
            motor_reset["tables"].append(_tbl)
        except Exception as _e:
            print(f"  motor reset {_tbl}: {_e}")
    # telematics_recent_event_count lives only on the UPT
    try:
        spark.sql(f"""
            UPDATE {fqn}.unified_motor_table_live
            SET telematics_recent_event_count = 0
            WHERE policy_id = '{MOTOR_DEMO_POLICY}'
        """)
    except Exception:
        pass
    # Refresh the motor online store so the live endpoint sees the reset.
    try:
        _rid = spark.sql(
            f"SELECT value FROM {fqn}.live_motor_runtime_state WHERE key='publish_pipeline_id' LIMIT 1"
        ).collect()
        if _rid and _rid[0].value:
            upd = w.pipelines.start_update(pipeline_id=_rid[0].value, full_refresh=False)
            motor_reset["online_refresh"] = f"triggered ({getattr(upd,'update_id','?')})"
        else:
            motor_reset["online_refresh"] = "no publish_pipeline_id (system off)"
    except Exception as _e:
        motor_reset["online_refresh"] = f"skip: {str(_e)[:120]}"
    print(f"✓ motor demo reset: {motor_reset}")
except Exception as _e:
    print(f"⚠ motor reset skipped (non-fatal): {_e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Audit the reset

# COMMAND ----------

try:
    user = dbutils.notebook.entry_point.getDbutils().notebook().getContext().userName().get()
except Exception:
    user = "system"

try:
    active_release = spark.sql(
        f"SELECT release_id FROM {fqn}.pricing_engine_releases WHERE status='champion' LIMIT 1"
    ).collect()[0]["release_id"]
except Exception:
    active_release = "current"
det = json.dumps({
    "champion_aliases":  alias_results,
    "rating_engine":     "v2.0 champion",
    "active_release":    active_release,
    "date_shift_days":   shift_info.get("delta_days", 0),
    "tables_truncated":  list(cleanup_counts.keys()),
}).replace("'", "''")
spark.sql(f"""
    INSERT INTO {fqn}.audit_log
      (event_id, event_type, entity_type, entity_id, entity_version,
       user_id, timestamp, details, source)
    SELECT uuid(), 'demo_reset', 'workbench', 'all',
           '-', '{user}', current_timestamp(), '{det}', 'reset_notebook'
""")

# COMMAND ----------

warm_outcome = {"called": False}
try:
    from databricks.sdk import WorkspaceClient as _W
    import requests as _rq
    _w = _W()
    _host = _w.config.host.rstrip("/")
    _token_hdr = _w.config._header_factory()
    # Find the workbench app on this workspace — name is stable across targets.
    _app_url = None
    try:
        for _a in _w.apps.list():
            if (_a.name or "").startswith("pricing-workbench"):
                _app_url = (_a.url or "").rstrip("/")
                break
    except Exception:
        _app_url = None
    if _app_url:
        # Wipe stale cached AI responses (champions / packs just got rebuilt)
        # then re-warm so a recorded demo lands on instant, identical answers.
        try:
            _rq.delete(f"{_app_url}/api/admin/ai-cache",
                       headers=_token_hdr, timeout=30)
        except Exception as _e:
            print(f"⚠ ai-cache clear failed (non-fatal): {_e}")
        try:
            r = _rq.post(f"{_app_url}/api/admin/ai-cache/warm",
                         headers=_token_hdr, timeout=600)
            warm_outcome = {"called": True, "status": r.status_code,
                            "body": r.text[:300]}
            print(f"ai-cache warm: {r.status_code}")
        except Exception as _e:
            warm_outcome = {"called": True, "error": str(_e)[:200]}
            print(f"⚠ ai-cache warm failed (non-fatal): {_e}")
    else:
        print("ℹ pricing-workbench app not found in this workspace — skipping warm-up")
except Exception as _e:
    print(f"⚠ ai-cache step skipped (non-fatal): {_e}")

dbutils.notebook.exit(json.dumps({
    "champion_aliases": alias_results,
    "active_release":   active_release,
    "date_shift":       shift_info,
    "cleanup":          cleanup_counts,
    "geospatial_rows":  n,
    "motor_reset":      motor_reset,
    "reset_at":         datetime.utcnow().isoformat() + "Z",
    "ai_cache_warm":    warm_outcome,
}))

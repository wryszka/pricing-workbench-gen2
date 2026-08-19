# Databricks notebook source
# MAGIC %md
# MAGIC # Pricing engine releases — rolling monthly rate book
# MAGIC
# MAGIC Creates `{fqn}.pricing_engine_releases` — one row per monthly rate-book
# MAGIC release. A release bundles one version of each of the 4 production model
# MAGIC families + one rating-engine config version + an effective date + a human
# MAGIC narrative. The Pricing Engine tab talks about **releases**, not raw model
# MAGIC versions — matching how real rate books ship through a committee.
# MAGIC
# MAGIC **Rolling by design.** The series is anchored to the CURRENT month so the
# MAGIC demo is never stale: the newest release is THIS month (`champion`), last
# MAGIC month is `previous_champion`, older months are `archived`. Version labels
# MAGIC descend from the live champion version per family (queried from UC), so
# MAGIC the "live rate book" always shows the versions that are actually deployed.
# MAGIC Exactly one row carries `status='champion'`. Idempotent (CREATE OR
# MAGIC REPLACE); re-run by demo_reset to re-anchor to today.

# COMMAND ----------

dbutils.widgets.text("catalog_name",         "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",          "pricing_workbench_gen2")
dbutils.widgets.text("num_releases",         "13")   # current month + 12 prior = trailing year
dbutils.widgets.text("rating_v2_months_back", "6")   # months ago the rating engine moved to v2.0

catalog          = dbutils.widgets.get("catalog_name")
schema           = dbutils.widgets.get("schema_name")
num_releases     = max(1, int(dbutils.widgets.get("num_releases")))
rating_v2_back   = int(dbutils.widgets.get("rating_v2_months_back"))
fqn              = f"{catalog}.{schema}"

# COMMAND ----------

import json
from datetime import date
from pyspark.sql.types import StructType, StructField, StringType, DateType
from mlflow.tracking import MlflowClient

mc = MlflowClient(registry_uri="databricks-uc")


def _month_start_back(anchor: date, k: int) -> date:
    """First-of-month k months before `anchor` (which is itself a day-1 date)."""
    m = anchor.month - 1 - k
    y = anchor.year + (m // 12)
    return date(y, (m % 12) + 1, 1)


def _latest_version(family: str, default: int = 1) -> int:
    """The highest registered UC version for a model family — the version that
    the @champion alias points at after a fresh train. Falls back to `default`
    if the model doesn't exist yet (e.g. releases seeded before training)."""
    try:
        vs = [int(v.version) for v in mc.search_model_versions(f"name='{fqn}.{family}'")]
        return max(vs) if vs else default
    except Exception:
        return default


# Anchor everything on the first of the CURRENT month.
_anchor = date.today().replace(day=1)

CHAMP = {
    "freq_glm":   _latest_version("freq_glm"),
    "sev_glm":    _latest_version("sev_glm"),
    "demand_gbm": _latest_version("demand_gbm"),
    "fraud_gbm":  _latest_version("fraud_gbm"),
}

# Narrative rotation for the "ordinary" months (index by k). The current month
# and the rating-engine-change month get their own bespoke narratives below.
_NARR = [
    "Calibration stable across all four families; no material data changes this month.",
    "Frequency model refreshed with the latest ONSPD postcode enrichment — small lift on the IMD-decile signal.",
    "Calibration-drift flag cleared with an isotonic-regression overlay on the frequency model; severity unchanged.",
    "Severity model recalibrated after a large-loss review; frequency and demand held.",
    "Demand model retuned on the latest quote-conversion data; price-elasticity bands widened slightly.",
    "Routine monthly refresh; committee noted stable loss-ratio trend and approved without changes.",
]


def _release(k: int) -> dict:
    eff = _month_start_back(_anchor, k)
    if k == 0:
        status = "champion"
    elif k == 1:
        status = "previous_champion"
    else:
        status = "archived"
    rating_version = "v2.0" if k <= rating_v2_back else "v1.1"
    # Version ladder: current champion at k=0, one lower per month back (>=1).
    ver = lambda fam: str(max(1, CHAMP[fam] - k))
    if k == 0:
        narrative = ("Current rate book. All four champion families are the live "
                     "deployed versions, refreshed from the current Modelling Mart. "
                     "Committee approved after the bias-monitor scan cleared on both "
                     "director_gender and postcode_demographic.")
    elif k == rating_v2_back:
        narrative = ("Rating engine v2.0 activated (broker commission cut to 15%, "
                     "fraud loading tightened to 6% at the 0.20 trigger, minimum "
                     "premium raised to £150). Frequency model also refreshed with "
                     "the ONSPD postcode enrichment.")
    else:
        narrative = _NARR[k % len(_NARR)]
    return {
        "release_id":            f"{eff.strftime('%b').lower()}_{eff.year}",
        "display_name":          eff.strftime("%B %Y"),
        "effective_date":        eff,
        "status":                status,
        "freq_glm_version":      ver("freq_glm"),
        "sev_glm_version":       ver("sev_glm"),
        "demand_gbm_version":    ver("demand_gbm"),
        "fraud_gbm_version":     ver("fraud_gbm"),
        "rating_engine_version": rating_version,
        "approved_by":           "pricing_committee@bricksurance.com",
        "narrative":             narrative,
    }


RELEASES = [_release(k) for k in range(num_releases)]

schema_struct = StructType([
    StructField("release_id",              StringType(),  False),
    StructField("display_name",            StringType(),  False),
    StructField("effective_date",          DateType(),    False),
    StructField("status",                  StringType(),  False),
    StructField("freq_glm_version",        StringType(),  False),
    StructField("sev_glm_version",         StringType(),  False),
    StructField("demand_gbm_version",      StringType(),  False),
    StructField("fraud_gbm_version",       StringType(),  False),
    StructField("rating_engine_version",   StringType(),  False),
    StructField("approved_by",             StringType(),  True),
    StructField("narrative",               StringType(),  True),
])

df = spark.createDataFrame(RELEASES, schema_struct)
df.write.mode("overwrite").option("overwriteSchema", "true") \
  .saveAsTable(f"{fqn}.pricing_engine_releases")

print(f"Seeded {fqn}.pricing_engine_releases with {df.count()} rolling releases "
      f"(champion = {RELEASES[0]['release_id']}):")
spark.sql(f"""
    SELECT release_id, status, cast(effective_date as string) as effective_date,
           freq_glm_version AS freq, sev_glm_version AS sev,
           demand_gbm_version AS demand, fraud_gbm_version AS fraud,
           rating_engine_version AS rating
    FROM {fqn}.pricing_engine_releases
    ORDER BY effective_date DESC
""").show(truncate=False)

# COMMAND ----------

# Audit — one event per seed release, timestamped at each release's effective
# date (which is now current, so the audit trail is fresh too).
for r in RELEASES:
    det = json.dumps({
        "action":        "publish" if r["status"] == "champion" else "seed",
        "release_id":    r["release_id"],
        "freq_glm":      r["freq_glm_version"],
        "sev_glm":       r["sev_glm_version"],
        "demand_gbm":    r["demand_gbm_version"],
        "fraud_gbm":     r["fraud_gbm_version"],
        "rating_engine": r["rating_engine_version"],
        "narrative":     (r["narrative"] or "")[:220],
    }).replace("'", "''")
    spark.sql(f"""
        INSERT INTO {fqn}.audit_log
          (event_id, event_type, entity_type, entity_id, entity_version, user_id, timestamp, details, source)
        SELECT uuid(), 'pricing_engine_release_published', 'pricing_engine_release',
               '{r["release_id"]}', '{r["release_id"]}',
               '{r["approved_by"]}', cast('{r["effective_date"]} 09:00:00' as timestamp),
               '{det}', 'seed_notebook'
    """)
print(f"Audit: {len(RELEASES)} release events logged.")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "rows":     len(RELEASES),
    "champion": RELEASES[0]["release_id"],
    "table":    f"{fqn}.pricing_engine_releases",
}))

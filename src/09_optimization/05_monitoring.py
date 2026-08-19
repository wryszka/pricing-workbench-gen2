# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — block 05: monitoring / feedback
# MAGIC
# MAGIC The reality-check loop. Over the rolling-month timeline (so it MOVES, not a
# MAGIC static snapshot), builds:
# MAGIC  * `opt_conversion_actuals` — actual conversion by month + a drift metric
# MAGIC    (month-over-month change in the conversion rate) — the drift sentinel's
# MAGIC    signal.
# MAGIC  * `opt_deviation_dist` — distribution of the optimised factors' deviation
# MAGIC    from technical price (the fair-value / corridor evidence).
# MAGIC  * `opt_constraint_breaches` — any solved factor outside the corridor
# MAGIC    (should be zero — the gate proof).
# MAGIC
# MAGIC SQL-only (no deps). Idempotent. Feeds the Monitoring tile + the fairness /
# MAGIC fair-value evidence path.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
fqn     = f"{catalog}.{schema}"
import json

# COMMAND ----------

# Actual conversion by month + drift (month-over-month delta) — moves with the
# rolling timeline; the drift sentinel watches the latest month's delta.
spark.sql(f"""
CREATE OR REPLACE TABLE {fqn}.opt_conversion_actuals AS
WITH by_month AS (
  SELECT date_trunc('month', created_at) AS month,
         COUNT(*) AS quotes,
         ROUND(AVG(converted), 4) AS actual_conversion,
         ROUND(AVG(vs_market_rate), 4) AS avg_price_ratio
  FROM {fqn}.opt_quote_response
  GROUP BY 1
)
SELECT month, quotes, actual_conversion, avg_price_ratio,
       ROUND(actual_conversion - LAG(actual_conversion) OVER (ORDER BY month), 4) AS conversion_drift_mom
FROM by_month ORDER BY month
""")
print("opt_conversion_actuals: monthly conversion + drift")
spark.table(f"{fqn}.opt_conversion_actuals").show(24, truncate=False)

# COMMAND ----------

# Deviation-from-technical distribution + constraint-breach check (needs the
# solver's factor table; skip gracefully if the solver hasn't run yet).
try:
    spark.sql(f"""
    CREATE OR REPLACE TABLE {fqn}.opt_deviation_dist AS
    SELECT
      CASE WHEN factor_pct < -10 THEN '<-10%'
           WHEN factor_pct <  -5 THEN '-10..-5%'
           WHEN factor_pct <   0 THEN '-5..0%'
           WHEN factor_pct <   5 THEN '0..5%'
           WHEN factor_pct <=  10 THEN '5..10%'
           ELSE '>10%' END AS deviation_band,
      COUNT(*) AS segments, SUM(policies) AS policies
    FROM {fqn}.opt_factor_table GROUP BY 1 ORDER BY 1
    """)
    breaches = spark.sql(f"SELECT COUNT(*) n FROM {fqn}.opt_factor_table WHERE within_corridor = false").collect()[0]["n"]
    spark.sql(f"""
    CREATE OR REPLACE TABLE {fqn}.opt_constraint_breaches AS
    SELECT constraint_version, segment, factor, factor_pct
    FROM {fqn}.opt_factor_table WHERE within_corridor = false
    """)
    print(f"opt_deviation_dist built; constraint breaches: {breaches} (should be 0)")
except Exception as e:
    breaches = None
    print(f"deviation/breach skipped (solver not run yet?): {str(e)[:150]}")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "months": spark.table(f"{fqn}.opt_conversion_actuals").count(),
    "constraint_breaches": breaches,
}))

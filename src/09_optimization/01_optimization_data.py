# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — block 01: data
# MAGIC
# MAGIC Derives the optimization inputs from the EXISTING governed quote stream +
# MAGIC policy book — no separate ingestion, no changes to the core generators (so
# MAGIC the live demo is untouched). Builds three `opt_*` tables:
# MAGIC
# MAGIC * `opt_quote_response`    — one row per priced quote: features, offered price,
# MAGIC   vs-market rate, outcome (bound/lost). The conversion/elasticity training set.
# MAGIC * `opt_portfolio_snapshot`— the current in-force book for simulation, with a
# MAGIC   technical-cost floor per policy.
# MAGIC * `opt_renewal_response`  — renewal offers derived from the book (prior vs
# MAGIC   offered premium, tenure, retained/lapsed) — the retention training set.
# MAGIC
# MAGIC The quote stream already carries the price-elasticity DGP (vs_market_rate →
# MAGIC bind logit), so conversion elasticity is learnable here without injecting
# MAGIC generator variation. Idempotent (CREATE OR REPLACE).

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
fqn     = f"{catalog}.{schema}"

import json

# COMMAND ----------

# --- opt_quote_response: conversion/elasticity training set -----------------
spark.sql(f"""
CREATE OR REPLACE TABLE {fqn}.opt_quote_response AS
SELECT
  transaction_id, policy_id, created_at, channel,
  sic_code, region, postcode_sector, construction_type, year_built, flood_zone,
  claims_last_5y, buildings_si, contents_si, liability_si, sum_insured, annual_turnover,
  gross_premium   AS offered_premium,
  market_premium,
  vs_market_rate,
  CASE WHEN quote_status = 'BOUND'  THEN 'bound'
       WHEN quote_status = 'QUOTED' THEN 'lost'
       ELSE 'abandoned' END              AS outcome,
  CASE WHEN quote_status = 'BOUND' THEN 1 ELSE 0 END AS converted,
  CASE WHEN quote_status = 'BOUND' THEN created_at END AS bound_ts
FROM {fqn}.quotes
WHERE gross_premium IS NOT NULL
""")
_qr = spark.table(f"{fqn}.opt_quote_response")
print(f"opt_quote_response: {_qr.count():,} priced quotes; "
      f"conversion rate {_qr.selectExpr('avg(converted)').first()[0]:.1%}")

# COMMAND ----------

# --- opt_portfolio_snapshot: the in-force book for simulation ----------------
# technical_cost = the risk/cost FLOOR the optimiser shapes margin above:
# max(5-yr incurred run-rate, an expense-loaded fraction of charged premium).
spark.sql(f"""
CREATE OR REPLACE TABLE {fqn}.opt_portfolio_snapshot AS
WITH claims AS (
  SELECT policy_id, SUM(incurred_amount) AS incurred_5y
  FROM {fqn}.internal_claims_history GROUP BY policy_id
)
SELECT
  p.policy_id, p.sic_code, p.postcode_sector, p.annual_turnover,
  p.sum_insured, p.claims_history_5y,
  p.current_premium                              AS charged_premium,
  cast(p.inception_date AS date)                 AS inception_date,
  cast(p.renewal_date  AS date)                  AS renewal_date,
  coalesce(c.incurred_5y, 0)                     AS incurred_5y,
  round(greatest(coalesce(c.incurred_5y,0)/5.0, p.current_premium*0.55), 2) AS technical_cost
FROM {fqn}.internal_commercial_policies p
LEFT JOIN claims c USING (policy_id)
""")
print(f"opt_portfolio_snapshot: {spark.table(f'{fqn}.opt_portfolio_snapshot').count():,} in-force policies")

# COMMAND ----------

# --- opt_renewal_response: retention training set ----------------------------
# Deterministic per-policy: a rate change in [0.95, 1.15]; retention falls as the
# increase rises (a retention elasticity the solver must respect via the GIPP +
# corridor rules). Hash-based so it's stable across resets.
spark.sql(f"""
CREATE OR REPLACE TABLE {fqn}.opt_renewal_response AS
SELECT
  policy_id, sic_code, postcode_sector,
  current_premium                                       AS prior_premium,
  round(current_premium * rate_change, 2)               AS offered_premium,
  rate_change,
  tenure_years,
  prob_retain,
  CASE WHEN uni < prob_retain THEN 1 ELSE 0 END          AS retained,
  CASE WHEN uni < prob_retain THEN 'retained' ELSE 'lapsed' END AS outcome
FROM (
  SELECT
    p.policy_id, p.sic_code, p.postcode_sector, p.current_premium,
    0.95 + (abs(hash(concat(p.policy_id,'rc'))) % 21)/100.0            AS rate_change,
    1 + abs(hash(concat(p.policy_id,'ten'))) % 8                        AS tenure_years,
    (abs(hash(concat(p.policy_id,'ret'))) % 1000)/1000.0               AS uni,
    1.0/(1.0 + exp(6.0 * ((0.95 + (abs(hash(concat(p.policy_id,'rc'))) % 21)/100.0) - 1.0))) AS prob_retain
  FROM {fqn}.internal_commercial_policies p
) t
""")
_rr = spark.table(f"{fqn}.opt_renewal_response")
print(f"opt_renewal_response: {_rr.count():,} renewal offers; "
      f"retention {_rr.selectExpr('avg(retained)').first()[0]:.1%}")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "opt_quote_response":     spark.table(f"{fqn}.opt_quote_response").count(),
    "opt_portfolio_snapshot": spark.table(f"{fqn}.opt_portfolio_snapshot").count(),
    "opt_renewal_response":   spark.table(f"{fqn}.opt_renewal_response").count(),
}))

# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — explain-this-price UC function (§11)
# MAGIC
# MAGIC A governed UC scalar function `explain_price(quote_id)` that decomposes any
# MAGIC motor quote into the three things a customer, a regulator or an ombudsman
# MAGIC asks about: the **technical price** (which risk models + the expense/commission
# MAGIC loading), the **optimisation factor** (which segment, how much, tied to the
# MAGIC governing decision record), and whether a **corridor clamp** was applied.
# MAGIC Returns JSON so the app + the price-explainer agent can consume it.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
fqn = f"{catalog}.{schema}"

# COMMAND ----------

# Segment expression mirrors segment_of() in the notebooks (age band · vehicle band).
spark.sql(f"""
CREATE OR REPLACE FUNCTION {fqn}.explain_price(p_quote_id STRING)
RETURNS STRING
COMMENT 'Decompose a motor quote: technical price (freq_glm_motor × sev_glm_motor champions + loading) + optimisation factor (segment, decision record) + corridor clamp. Returns JSON.'
RETURN
  -- max() over the single matched row: a scalar SQL function body must be
  -- guaranteed single-row (the planner rejects an un-aggregated query body).
  SELECT max(to_json(named_struct(
    'quote_id',                       s.quote_id,
    'segment',                        s.segment,
    'driver_age',                     s.driver_age,
    'vehicle_group',                  s.vehicle_group,
    'technical_premium',              s.technical_premium,
    'loaded_premium',                 s.loaded_premium,
    'offered_premium',                s.offered_premium,
    'expense_commission_loading_pct', round((s.loaded_premium / nullif(s.technical_premium, 0) - 1) * 100, 1),
    'vs_technical',                   s.vs_technical,
    'vs_market',                      s.vs_market,
    'optimisation_factor_pct',        f.factor_pct,
    'factor_binding',                 f.binding,
    'indicated_after_factor',         round(s.loaded_premium * (1 + coalesce(f.factor_pct, 0) / 100), 2),
    'corridor',                       '±15% of the technical (break-even) price',
    'corridor_clamped',               CASE WHEN f.binding IN ('corridor', 'segment_cap') THEN true ELSE false END,
    'constraint_version',             f.constraint_version,
    'conversion_at_factor',           f.conversion_opt,
    'models',                         'technical = freq_glm_motor × sev_glm_motor (champions); demand = conversion_elasticity_motor (monotone)'
  )))
  FROM (
    SELECT q.*,
           concat(CASE WHEN q.driver_age < 25 THEN 'U25' WHEN q.driver_age < 70 THEN '25-70' ELSE '70+' END,
                  ' · ',
                  CASE WHEN q.vehicle_group < 15 THEN 'grpLow' WHEN q.vehicle_group < 30 THEN 'grpMid' ELSE 'grpHigh' END) AS segment
    FROM {fqn}.optimisation_quote_response q
    WHERE q.quote_id = p_quote_id
  ) s
  LEFT JOIN {fqn}.optimisation_factor_table f ON f.segment = s.segment
""")
print(f"created {fqn}.explain_price(quote_id)")

# COMMAND ----------

# Smoke: pick a 70+ · grpHigh quote (the grandma-in-a-BMW known-good demo case) and explain it.
demo = spark.sql(f"""
    SELECT quote_id FROM {fqn}.optimisation_quote_response
    WHERE driver_age >= 70 AND vehicle_group >= 30 LIMIT 1
""").collect()
if demo:
    qid = demo[0][0]
    out = spark.sql(f"SELECT {fqn}.explain_price('{qid}') AS j").collect()[0][0]
    print(f"explain_price('{qid}'):\n{out}")
    # stash a known-good demo quote id for the app / runbook
    spark.sql(f"CREATE TABLE IF NOT EXISTS {fqn}.optimisation_explain_demo (label STRING, quote_id STRING)")
    spark.sql(f"DELETE FROM {fqn}.optimisation_explain_demo WHERE label = 'grandma_bmw'")
    spark.sql(f"INSERT INTO {fqn}.optimisation_explain_demo VALUES ('grandma_bmw', '{qid}')")

import json as _j
dbutils.notebook.exit(_j.dumps({"function": f"{fqn}.explain_price", "demo_quote": demo[0][0] if demo else None}))

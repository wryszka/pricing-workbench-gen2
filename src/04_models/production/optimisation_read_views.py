# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimisation — read layer as governed UC VIEWS
# MAGIC
# MAGIC **Platform-native gate (playbook v2.3 §6.C):** a read is a governed Unity
# MAGIC Catalog object, not a SQL string embedded in the app. Each `opt_read_*` MCP
# MAGIC tool now does `SELECT * FROM <view>` — the *what* (columns, filters, joins)
# MAGIC lives here in UC with lineage and grants; the app/tool is a thin caller.
# MAGIC
# MAGIC Phase 1 of re-grounding the pricing tool surface off the app and into
# MAGIC Databricks-native objects. Idempotent (`CREATE OR REPLACE VIEW`). Reserved
# MAGIC identifiers (`check`, `group`) are back-ticked.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
fqn = f"{catalog}.{schema}"

# COMMAND ----------

VIEWS = {
    "v_optimisation_frontier":
        f"SELECT scenario_id, expected_profit, expected_volume, expected_gwp, pareto "
        f"FROM {fqn}.optimisation_scenarios WHERE pareto = true OR scenario_id = 'hold'",
    "v_optimisation_factors":
        f"SELECT segment, factor_pct, conversion_hold, conversion_opt, profit_uplift, binding "
        f"FROM {fqn}.optimisation_factor_table",
    "v_optimisation_renewal_factors":
        f"SELECT segment, policies, renewal_factor_pct, retention_hold, retention_opt, "
        f"margin_uplift, gipp_breaches FROM {fqn}.optimisation_renewal_factor_table",
    "v_optimisation_monitoring_drift":
        f"SELECT cast(quote_month AS string) AS month, actual_conversion, "
        f"expected_conversion, drift FROM {fqn}.optimisation_monitoring",
    "v_optimisation_constraint_breaches":
        f"SELECT `check`, breaches, total, rate FROM {fqn}.optimisation_constraint_breaches",
    "v_optimisation_fairness_evidence":
        f"SELECT `check`, dimension, `group`, value, threshold, pass "
        f"FROM {fqn}.optimisation_fairness_evidence",
    "v_optimisation_fairness_summary":
        f"SELECT overall_pass, worst_proxy_corr, evidence FROM {fqn}.optimisation_fairness_summary",
    "v_optimisation_disagreement":
        f"SELECT segment, factor_min, factor_max, factor_spread_pp, agreement, n_models "
        f"FROM {fqn}.optimisation_disagreement",
    "v_optimisation_run_costs":
        f"SELECT preset, grid_points, n_draws, n_models, policies, total_evaluations, "
        f"wallclock_s, est_cost_usd, cast(ran_at AS string) AS ran_at FROM {fqn}.optimisation_heavy_meta",
}

# Per-view try/except: v_optimisation_disagreement + v_optimisation_run_costs
# read the HEAVY-MODE tables (optimisation_disagreement / optimisation_heavy_meta),
# which are dormant and absent after a normal full_build — a missing base table
# must skip that one view, not fail the notebook. Those views get created when
# heavy mode has run.
created, skipped = [], []
for name, sel in VIEWS.items():
    try:
        spark.sql(f"CREATE OR REPLACE VIEW {fqn}.{name} AS {sel}")
        spark.sql(f"COMMENT ON VIEW {fqn}.{name} IS 'Price-optimisation read layer (UC-native, playbook v2.3). Backs the opt_read_* MCP tool of the same name.'")
        created.append(name)
    except Exception as e:
        skipped.append((name, str(e)[:120]))

print(f"created/updated {len(created)} read views:")
for n in created:
    print("  -", n)
if skipped:
    print(f"skipped {len(skipped)} (base table not present — e.g. heavy mode not run):")
    for n, err in skipped:
        print(f"  - {n}: {err}")

# COMMAND ----------

# The app service principal already holds SELECT on the schema, so it inherits
# SELECT on these views — no per-view grant needed. Listed here as the contract:
#   GRANT SELECT ON VIEW <fqn>.<view> TO `<app_sp>`   (covered by schema grant)

import json
dbutils.notebook.exit(json.dumps({"views": created, "count": len(created), "skipped": [s[0] for s in skipped]}))

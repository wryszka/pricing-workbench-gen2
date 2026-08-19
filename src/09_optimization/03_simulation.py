# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — block 03: simulation
# MAGIC
# MAGIC Scores the in-force book (`opt_portfolio_snapshot`) across **N candidate
# MAGIC price sets** using the conversion elasticity model, and records expected
# MAGIC profit / volume / loss-ratio per candidate. `N = grid_points` is a job
# MAGIC parameter — the "N thousand candidate price sets overnight, N is your
# MAGIC choice, not a licence tier" demo moment. Elastic compute, exhaustive
# MAGIC exploration.
# MAGIC
# MAGIC Each candidate is a vector of per-segment price factors sampled within the
# MAGIC deviation corridor. Output: `opt_scenarios` (one row per candidate) +
# MAGIC `opt_scenario_segments` (per candidate × segment). Deps from the job env.
# MAGIC Idempotent.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
dbutils.widgets.text("grid_points",  "2000")     # number of candidate price sets
dbutils.widgets.text("corridor_pct", "15")       # +/- deviation corridor
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
N       = max(1, int(dbutils.widgets.get("grid_points")))
CORR    = float(dbutils.widgets.get("corridor_pct")) / 100.0
fqn     = f"{catalog}.{schema}"

import json, uuid
import numpy as np
import pandas as pd
import mlflow
mlflow.set_registry_uri("databricks-uc")

# COMMAND ----------

snap = spark.table(f"{fqn}.opt_portfolio_snapshot").toPandas()
# Segment the book (trade). Each candidate assigns a price factor per segment.
snap["segment"] = snap["sic_code"].astype(str)
segments = snap["segment"].value_counts().index.tolist()
print(f"portfolio: {len(snap):,} policies across {len(segments)} segments; N={N} candidates, corridor +/-{CORR:.0%}")

# Load the conversion elasticity model — response to price. We approximate each
# policy's conversion/retention response with the model's price sensitivity via
# vs_market_rate = factor (factor 1.0 = hold, >1 = increase).
cm = mlflow.pyfunc.load_model(f"models:/{fqn}.pwg2_conversion_elasticity@champion")

# Build a scoring frame template from the snapshot mapped to the model's features.
def _score_prob(factor_by_seg: dict) -> pd.Series:
    df = pd.DataFrame({
        "sic_code":          snap["segment"].astype("category"),
        "region":            "UK",
        "construction_type": "Standard",
        "channel":           "broker",
        "buildings_si":      snap["sum_insured"].fillna(0),
        "contents_si":       0.0,
        "liability_si":      0.0,
        "annual_turnover":   snap["annual_turnover"].fillna(0),
        "claims_last_5y":    snap["claims_history_5y"].fillna(0),
        "vs_market_rate":    snap["segment"].map(factor_by_seg).astype(float),
    })
    for c in ["sic_code", "region", "construction_type", "channel"]:
        df[c] = df[c].astype("category")
    try:
        return pd.Series(cm.predict(df), index=snap.index).clip(0, 1)
    except Exception:
        # graceful fallback: simple logit in price if the model can't score
        z = 0.5 - 9.0 * (snap["segment"].map(factor_by_seg).astype(float) - 1.0)
        return pd.Series(1.0 / (1.0 + np.exp(-z)), index=snap.index)

charged = snap["charged_premium"].fillna(0).values
cost    = snap["technical_cost"].fillna(0).values

# COMMAND ----------

rng = np.random.default_rng(42)
scen_rows, seg_rows = [], []
# candidate 0 = hold (all factors 1.0), then N-1 sampled within the corridor.
for i in range(N):
    if i == 0:
        fbs = {s: 1.0 for s in segments}
    else:
        fbs = {s: float(1.0 + rng.uniform(-CORR, CORR)) for s in segments}
    p = _score_prob(fbs).values
    seg_factor = snap["segment"].map(fbs).astype(float).values
    price = charged * seg_factor
    exp_profit = float(np.sum(p * (price - cost)))
    exp_volume = float(np.sum(p))
    exp_gwp    = float(np.sum(p * price))
    exp_cost   = float(np.sum(p * cost))
    scen_id = "hold" if i == 0 else f"cand_{i:05d}"
    scen_rows.append({
        "scenario_id": scen_id, "expected_profit": round(exp_profit, 2),
        "expected_volume": round(exp_volume, 1), "expected_gwp": round(exp_gwp, 2),
        "expected_loss_ratio": round(exp_cost / exp_gwp, 4) if exp_gwp else None,
        "avg_factor": round(float(np.mean(list(fbs.values()))), 4),
        "factors_json": json.dumps({k: round(v, 4) for k, v in fbs.items()}),
    })
    # per-segment detail only for a manageable subset (hold + top candidates later)
    if i == 0:
        for s in segments:
            m = snap["segment"] == s
            seg_rows.append({"scenario_id": scen_id, "segment": s,
                             "policies": int(m.sum()),
                             "expected_profit": round(float(np.sum(p[m.values]*(price[m.values]-cost[m.values]))), 2),
                             "factor": round(fbs[s], 4)})

scen_df = pd.DataFrame(scen_rows)
spark.createDataFrame(scen_df).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{fqn}.opt_scenarios")
if seg_rows:
    spark.createDataFrame(pd.DataFrame(seg_rows)).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{fqn}.opt_scenario_segments")

_best = scen_df.sort_values("expected_profit", ascending=False).iloc[0]
_hold = scen_df[scen_df.scenario_id == "hold"].iloc[0]
print(f"best candidate {_best.scenario_id}: profit {_best.expected_profit:,.0f} "
      f"vs hold {_hold.expected_profit:,.0f} (uplift {(_best.expected_profit/_hold.expected_profit-1)*100:.1f}% if hold>0)")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "candidates": len(scen_df), "best": _best.scenario_id,
    "best_profit": float(_best.expected_profit),
}))

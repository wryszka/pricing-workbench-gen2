# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — block 03: simulation (scale-independent)
# MAGIC
# MAGIC Scores the in-force book across **N candidate price sets** (`grid_points`
# MAGIC param — the "N is your choice, not a licence tier" beat). Designed to scale
# MAGIC to any book size: it builds a per-segment elasticity curve ONCE (a handful
# MAGIC of single-row model calls per segment), reduces the book to per-segment
# MAGIC aggregates, then evaluates every candidate by interpolation — O(candidates
# MAGIC × segments), independent of policy count. Output `opt_scenarios` (one row
# MAGIC per candidate) + `opt_scenario_segments` (the hold baseline, per segment).
# MAGIC Deps from the job env. Idempotent.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
dbutils.widgets.text("grid_points",  "2000")
dbutils.widgets.text("corridor_pct", "15")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
N       = max(1, int(dbutils.widgets.get("grid_points")))
CORR    = float(dbutils.widgets.get("corridor_pct")) / 100.0
fqn     = f"{catalog}.{schema}"

import json
import numpy as np
import pandas as pd
import mlflow
mlflow.set_registry_uri("databricks-uc")

# COMMAND ----------

snap = spark.table(f"{fqn}.opt_portfolio_snapshot").toPandas()
for _c in ["charged_premium", "technical_cost", "sum_insured", "annual_turnover", "claims_history_5y"]:
    if _c in snap.columns:
        snap[_c] = pd.to_numeric(snap[_c], errors="coerce").fillna(0.0)
snap["segment"] = snap["sic_code"].astype(str)

# Per-segment aggregates — the whole book reduced to O(segments) rows.
agg = snap.groupby("segment").agg(n=("policy_id", "count"),
                                  gwp=("charged_premium", "sum"),
                                  cost=("technical_cost", "sum"))
segments = agg.index.tolist()
print(f"portfolio: {len(snap):,} policies -> {len(segments)} segments; N={N} candidates, corridor +/-{CORR:.0%}")

# COMMAND ----------

# Build a per-segment conversion curve ONCE (single representative row per
# segment scored across the price grid). O(segments x grid) model calls total.
cm = mlflow.pyfunc.load_model(f"models:/{fqn}.pwg2_conversion_elasticity@champion")
grid = np.round(np.linspace(1 - CORR, 1 + CORR, 9), 4)

def _feat_row(seg: str, ratio: float) -> pd.DataFrame:
    rep = snap[snap["segment"] == seg].iloc[0]
    df = pd.DataFrame([{
        "sic_code": seg, "region": "UK", "construction_type": "Standard", "channel": "broker",
        "buildings_si": float(rep["sum_insured"]), "contents_si": 0.0, "liability_si": 0.0,
        "annual_turnover": float(rep["annual_turnover"]), "claims_last_5y": float(rep["claims_history_5y"]),
        "vs_market_rate": float(ratio),
    }])
    for c in ["sic_code", "region", "construction_type", "channel"]:
        df[c] = df[c].astype("category")
    return df

curves = {}
for s in segments:
    try:
        curves[s] = np.array([float(cm.predict(_feat_row(s, g))[0]) for g in grid])
    except Exception:
        # fallback logit curve if the model can't score this segment
        curves[s] = 1.0 / (1.0 + np.exp(-(0.5 - 9.0 * (grid - 1.0))))
print(f"built {len(curves)} per-segment elasticity curves over grid {list(grid)}")

# COMMAND ----------

rng = np.random.default_rng(42)
gwp_arr = agg["gwp"].values; cost_arr = agg["cost"].values; n_arr = agg["n"].values
scen_rows, seg_rows = [], []
for i in range(N):
    factors = np.ones(len(segments)) if i == 0 else 1.0 + rng.uniform(-CORR, CORR, len(segments))
    p = np.array([np.interp(factors[j], grid, curves[segments[j]]) for j in range(len(segments))])
    seg_gwp = gwp_arr * factors
    profit  = float(np.sum(p * (seg_gwp - cost_arr)))
    volume  = float(np.sum(p * n_arr))
    gwp     = float(np.sum(p * seg_gwp))
    cost_e  = float(np.sum(p * cost_arr))
    sid = "hold" if i == 0 else f"cand_{i:05d}"
    scen_rows.append({
        "scenario_id": sid, "expected_profit": round(profit, 2),
        "expected_volume": round(volume, 1), "expected_gwp": round(gwp, 2),
        "expected_loss_ratio": round(cost_e / gwp, 4) if gwp else None,
        "avg_factor": round(float(np.mean(factors)), 4),
    })
    if i == 0:
        for j, s in enumerate(segments):
            seg_rows.append({"scenario_id": sid, "segment": s, "policies": int(n_arr[j]),
                             "expected_profit": round(float(p[j] * (seg_gwp[j] - cost_arr[j])), 2),
                             "factor": 1.0})

scen_df = pd.DataFrame(scen_rows)
spark.createDataFrame(scen_df).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{fqn}.opt_scenarios")
spark.createDataFrame(pd.DataFrame(seg_rows)).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{fqn}.opt_scenario_segments")

_best = scen_df.sort_values("expected_profit", ascending=False).iloc[0]
_hold = scen_df[scen_df.scenario_id == "hold"].iloc[0]
_up = (_best.expected_profit / _hold.expected_profit - 1) * 100 if _hold.expected_profit else 0
print(f"{len(scen_df)} candidates; best {_best.scenario_id} profit {_best.expected_profit:,.0f} "
      f"vs hold {_hold.expected_profit:,.0f} (+{_up:.1f}%)")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "candidates": len(scen_df), "best": _best.scenario_id,
    "best_profit": float(_best.expected_profit), "hold_profit": float(_hold.expected_profit),
}))

# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — Block 3: simulation (§5)
# MAGIC
# MAGIC Scores the in-force motor book across **N candidate price sets** (`grid_points`
# MAGIC — the "N is your choice, not a licence tier" beat). Scale-independent: the
# MAGIC per-segment elasticity curve is built **once** by Block 2
# MAGIC (`optimisation_elasticity_curve`); the book is reduced to per-segment
# MAGIC aggregates; every candidate is then evaluated by interpolation — cost is
# MAGIC O(candidates × segments), independent of policy count.
# MAGIC
# MAGIC Output `optimisation_scenarios` (one row per candidate: profit / volume /
# MAGIC GWP / loss-ratio / avg factor + a **Pareto** flag for the efficient frontier)
# MAGIC and `optimisation_scenario_segments` (the hold baseline per segment, for the
# MAGIC waterfall).

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
dbutils.widgets.text("grid_points",  "3000")
dbutils.widgets.text("corridor_pct", "15")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
N       = max(1, int(dbutils.widgets.get("grid_points")))
CORR    = float(dbutils.widgets.get("corridor_pct")) / 100.0
fqn     = f"{catalog}.{schema}"

import json, time
import numpy as np, pandas as pd
np.random.seed(42)
t0 = time.time()

# COMMAND ----------

def segment_of(df: pd.DataFrame) -> pd.Series:
    age = pd.to_numeric(df.get("driver_age"), errors="coerce").fillna(45)
    vg  = pd.to_numeric(df.get("vehicle_group"), errors="coerce").fillna(20)
    age_band = np.where(age < 25, "U25", np.where(age < 70, "25-70", "70+"))
    veh_band = np.where(vg < 15, "grpLow", np.where(vg < 30, "grpMid", "grpHigh"))
    return pd.Series([f"{a} · {v}" for a, v in zip(age_band, veh_band)], index=df.index)

snap = spark.table(f"{fqn}.optimisation_portfolio_snapshot").toPandas()
for c in ["current_premium", "technical_premium", "loaded_premium"]:
    snap[c] = pd.to_numeric(snap[c], errors="coerce").fillna(0.0)
snap["segment"] = segment_of(snap)
# Price basis = loaded_premium (the rate-book / break-even price we optimise around);
# cost = pure risk technical_premium (the margin floor). current_premium is a stale
# in-force field and is not the optimisation baseline.
agg = snap.groupby("segment").agg(n=("policy_id", "count"),
                                  gwp=("loaded_premium", "sum"),
                                  cost=("technical_premium", "sum"))

# Per-segment conversion curve from Block 2 (price_multiplier → conversion_prob).
curve = spark.table(f"{fqn}.optimisation_elasticity_curve").toPandas()
segments = [s for s in agg.index.tolist() if s in set(curve["segment"])]
agg = agg.loc[segments]
grids  = {s: curve[curve.segment == s].sort_values("price_multiplier")["price_multiplier"].values for s in segments}
convs  = {s: curve[curve.segment == s].sort_values("price_multiplier")["conversion_prob"].values for s in segments}
gwp_arr, cost_arr, n_arr = agg["gwp"].values, agg["cost"].values, agg["n"].values
print(f"portfolio {len(snap):,} policies → {len(segments)} segments; N={N} candidates, corridor ±{CORR:.0%}")

def conv_at(seg, factor):
    return float(np.interp(factor, grids[seg], convs[seg]))

# COMMAND ----------

rng = np.random.default_rng(7)
rows, seg_rows = [], []
for i in range(N):
    factors = np.ones(len(segments)) if i == 0 else 1.0 + rng.uniform(-CORR, CORR, len(segments))
    p = np.array([conv_at(segments[j], factors[j]) for j in range(len(segments))])
    seg_gwp = gwp_arr * factors
    profit  = float(np.sum(p * (seg_gwp - cost_arr)))
    volume  = float(np.sum(p * n_arr))
    gwp_e   = float(np.sum(p * seg_gwp))
    cost_e  = float(np.sum(p * cost_arr))
    rows.append({"scenario_id": "hold" if i == 0 else f"cand_{i:05d}",
                 "expected_profit": round(profit, 2), "expected_volume": round(volume, 1),
                 "expected_gwp": round(gwp_e, 2),
                 "expected_loss_ratio": round(cost_e / gwp_e, 4) if gwp_e else None,
                 "avg_factor": round(float(np.mean(factors)), 4)})
    if i == 0:
        for j, s in enumerate(segments):
            seg_rows.append({"scenario_id": "hold", "segment": s, "policies": int(n_arr[j]),
                             "conversion": round(float(p[j]), 4),
                             "expected_profit": round(float(p[j] * (seg_gwp[j] - cost_arr[j])), 2),
                             "gwp": round(float(gwp_arr[j]), 2), "factor": 1.0})

scen = pd.DataFrame(rows)

# Pareto frontier over (volume↑, profit↑): a candidate is efficient if nothing
# beats it on both axes. Flag them so the app draws the frontier directly.
order = scen.sort_values(["expected_volume", "expected_profit"], ascending=[True, False]).reset_index()
best_profit, pareto_idx = -np.inf, []
for _, r in order.iterrows():
    if r["expected_profit"] >= best_profit:
        pareto_idx.append(r["index"]); best_profit = r["expected_profit"]
scen["pareto"] = scen.index.isin(pareto_idx)

elapsed = round(time.time() - t0, 2)
scen["grid_points"] = N
scen["wallclock_s"] = elapsed
(spark.createDataFrame(scen).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_scenarios"))
(spark.createDataFrame(pd.DataFrame(seg_rows)).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_scenario_segments"))

_best = scen.sort_values("expected_profit", ascending=False).iloc[0]
_hold = scen[scen.scenario_id == "hold"].iloc[0]
_up = (_best.expected_profit / _hold.expected_profit - 1) * 100 if _hold.expected_profit else 0
print(f"optimisation_scenarios: {len(scen):,} candidates in {elapsed}s, {int(scen['pareto'].sum())} on frontier; "
      f"best profit {_best.expected_profit:,.0f} vs hold {_hold.expected_profit:,.0f} (+{_up:.1f}%)")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "candidates": len(scen), "pareto": int(scen["pareto"].sum()),
    "best_profit": float(_best.expected_profit), "hold_profit": float(_hold.expected_profit),
    "wallclock_s": elapsed,
}))

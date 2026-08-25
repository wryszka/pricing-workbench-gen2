# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — HEAVY MODE (§11a): the big-hammer run
# MAGIC
# MAGIC The optional second gear. The default optimiser is deliberately light
# MAGIC (segment-collapsed, scale-free). Heavy mode is what you run **because you
# MAGIC can**, not because you must — the flex an appliance can't match:
# MAGIC
# MAGIC 1. **Ensemble disagreement map** — refit the demand model as an **ensemble of
# MAGIC    candidate specs** (different model types / depths / feature subsets / seeds),
# MAGIC    re-solve the optimal factor under **each**, and measure how much they
# MAGIC    disagree per segment. Where they agree = high decision confidence; where
# MAGIC    they split = treat the factor as uncertain. → `optimisation_disagreement`.
# MAGIC 2. **Exhaustive stochastic run** — score the WHOLE book **per policy** across a
# MAGIC    candidate price grid with **K Monte-Carlo demand draws**, producing the full
# MAGIC    profit/volume DISTRIBUTION (P5/P95, probability-of-missing-plan, tail) per
# MAGIC    candidate. → `optimisation_scenarios_stochastic`.
# MAGIC
# MAGIC Real measured cost is captured to `optimisation_heavy_meta` (row count,
# MAGIC wall-clock, rough DBU cost) — the caption in the app is never hardcoded.
# MAGIC
# MAGIC **DORMANT by default** — never chained into full_build; run on demand. Two
# MAGIC presets: `default` (pre-computed demo artifact, genuinely heavy) and `live`
# MAGIC (smaller, safe to re-run in the room).

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
dbutils.widgets.text("preset", "default")          # default (heavy) | live (small)
dbutils.widgets.text("grid_points", "")            # override candidate count
dbutils.widgets.text("n_draws", "")                # override MC draws
dbutils.widgets.text("n_models", "")               # override ensemble size
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
preset  = dbutils.widgets.get("preset").strip().lower()
fqn = f"{catalog}.{schema}"

import time, json
import numpy as np, pandas as pd
import lightgbm as lgb
from sklearn.linear_model import LogisticRegression

# presets — default is the pre-computed heavy demo artifact; live is room-safe.
P = {"default": {"grid": 300, "draws": 300, "models": 8},
     "live":    {"grid": 60,  "draws": 60,  "models": 4}}.get(preset, {"grid": 300, "draws": 300, "models": 8})
def _ov(w, d):
    v = dbutils.widgets.get(w).strip(); return int(v) if v else d
GRID, DRAWS, NMODELS = _ov("grid_points", P["grid"]), _ov("n_draws", P["draws"]), _ov("n_models", P["models"])
CORR = 0.15
np.random.seed(20260825)
t0 = time.time()

def segment_of(df):
    age = pd.to_numeric(df.get("driver_age"), errors="coerce").fillna(45)
    vg  = pd.to_numeric(df.get("vehicle_group"), errors="coerce").fillna(20)
    ab = np.where(age < 25, "U25", np.where(age < 70, "25-70", "70+"))
    vb = np.where(vg < 15, "grpLow", np.where(vg < 30, "grpMid", "grpHigh"))
    return pd.Series([f"{a} · {v}" for a, v in zip(ab, vb)], index=df.index)

CONV_FEATURES = ["vs_technical", "vs_market", "driver_age", "no_claims_years",
                 "annual_mileage", "vehicle_value", "vehicle_group", "month_idx"]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Ensemble disagreement map — re-solve under each candidate demand spec

# COMMAND ----------

qr = spark.table(f"{fqn}.optimisation_quote_response").toPandas()
for c in CONV_FEATURES + ["converted"]:
    qr[c] = pd.to_numeric(qr[c], errors="coerce")
qr = qr.dropna(subset=CONV_FEATURES + ["converted"])
qr["segment"] = segment_of(qr)
Xc, yc = qr[CONV_FEATURES], qr["converted"].astype(int)
segments = sorted(qr["segment"].unique())
grid_mult = np.round(np.linspace(1 - CORR, 1 + CORR, 13), 4)

# candidate demand specs — genuinely different models (types, depth, features, seed)
specs = []
for i in range(NMODELS):
    if i % 4 == 3:
        specs.append(("logit", None))
    else:
        specs.append(("lgbm", dict(n_estimators=120 + 40 * i, num_leaves=15 + 6 * i,
                                   max_depth=3 + (i % 4), subsample=0.7 + 0.03 * (i % 5),
                                   min_child_samples=100 + 50 * i, random_state=i, verbose=-1,
                                   monotone_constraints=[-1, -1, 0, 0, 0, 0, 0, 0])))

def seg_medians(seg):
    return qr[qr.segment == seg][CONV_FEATURES].median()

# per model → per segment optimal factor (grid argmax of conv·margin proxy within corridor)
agg = spark.table(f"{fqn}.optimisation_portfolio_snapshot").toPandas()
for c in ["loaded_premium", "technical_premium"]:
    agg[c] = pd.to_numeric(agg[c], errors="coerce").fillna(0.0)
agg["segment"] = segment_of(agg)
seg_econ = agg.groupby("segment").agg(gwp=("loaded_premium", "sum"), cost=("technical_premium", "sum"))

factors_by_model = {s: [] for s in segments}
for kind, params in specs:
    if kind == "lgbm":
        m = lgb.LGBMClassifier(**params).fit(Xc, yc)
        prob = lambda X: m.predict_proba(X)[:, 1]
    else:
        m = LogisticRegression(max_iter=800).fit(qr[["vs_technical", "vs_market"]], yc)
        prob = lambda X: m.predict_proba(X[["vs_technical", "vs_market"]])[:, 1]
    for s in segments:
        med = seg_medians(s); base_vt, base_vm = float(med["vs_technical"]), float(med["vs_market"])
        rows = []
        for g in grid_mult:
            r = med.copy(); r["vs_technical"] = base_vt * g; r["vs_market"] = base_vm * g
            rows.append(r)
        conv = prob(pd.DataFrame(rows)[CONV_FEATURES])
        if s in seg_econ.index:
            gwp, cost = seg_econ.loc[s, "gwp"], seg_econ.loc[s, "cost"]
            profit = conv * (gwp * grid_mult - cost)
            factors_by_model[s].append(float(grid_mult[int(np.argmax(profit))]))

dis_rows = []
for s in segments:
    fs = np.array(factors_by_model[s])
    if len(fs) == 0:
        continue
    spread_pp = float((fs.max() - fs.min()) * 100)
    dis_rows.append({"segment": s, "factor_min": float(fs.min()), "factor_max": float(fs.max()),
                     "factor_spread_pp": round(spread_pp, 2),
                     "agreement": round(float(max(0.0, 1 - spread_pp / (2 * CORR * 100))), 3),
                     "n_models": int(len(fs))})
dis = pd.DataFrame(dis_rows)
(spark.createDataFrame(dis).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_disagreement"))
print(f"optimisation_disagreement: {len(dis)} segments across {NMODELS} demand specs; "
      f"max spread {dis['factor_spread_pp'].max():.1f}pp, min agreement {dis['agreement'].min():.2f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Exhaustive stochastic run — per-policy, candidate grid, K Monte-Carlo draws

# COMMAND ----------

# per-segment base conversion curve (from the champion elasticity curve table)
curve = spark.table(f"{fqn}.optimisation_elasticity_curve").toPandas()
cg = {s: curve[curve.segment == s].sort_values("price_multiplier")["price_multiplier"].values for s in segments}
cc = {s: curve[curve.segment == s].sort_values("price_multiplier")["conversion_prob"].values for s in segments}

book = agg.copy()
seg_idx = book["segment"].values
loaded = book["loaded_premium"].values
technical = book["technical_premium"].values
N = len(book)
# plan = the hold expected profit (factor 1.0) — "prob of missing plan" is P(profit < plan)
def conv_vec(seg_arr, factor):
    out = np.empty(len(seg_arr))
    for s in segments:
        m = seg_arr == s
        if m.any():
            out[m] = np.interp(factor, cg[s], cc[s]) if s in cg else 0.6
    return out
hold_p = conv_vec(seg_idx, 1.0)
plan_profit = float(np.sum(hold_p * (loaded - technical)))

rng = np.random.default_rng(7)
stoch_rows = []
eval_count = 0
for i in range(GRID):
    factor = 1.0 if i == 0 else float(1.0 + rng.uniform(-CORR, CORR))   # global candidate multiplier
    offered = loaded * factor
    p = conv_vec(seg_idx, factor)
    margin = offered - technical
    # K Monte-Carlo demand draws over the whole book
    draws = (rng.random((DRAWS, N)) < p)                    # DRAWS x N Bernoulli
    profit_draws = draws @ margin                            # DRAWS portfolio profits
    volume_draws = draws.sum(axis=1)
    eval_count += DRAWS * N
    stoch_rows.append({
        "candidate_id": "hold" if i == 0 else f"cand_{i:05d}", "avg_factor": round(factor, 4),
        "mean_profit": round(float(profit_draws.mean()), 2),
        "p5_profit":  round(float(np.percentile(profit_draws, 5)), 2),
        "p95_profit": round(float(np.percentile(profit_draws, 95)), 2),
        "mean_volume": round(float(volume_draws.mean()), 1),
        "prob_below_plan": round(float((profit_draws < plan_profit).mean()), 4),
    })
stoch = pd.DataFrame(stoch_rows)
(spark.createDataFrame(stoch).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_scenarios_stochastic"))

elapsed = time.time() - t0
total_evals = int(eval_count + NMODELS * len(segments) * len(grid_mult))
# rough cost estimate — serverless job compute at ~$0.70/DBU, ~1 DBU/min single node (LABELLED estimate)
est_cost = round((elapsed / 60.0) * 0.70, 2)
meta = pd.DataFrame([{
    "preset": preset, "grid_points": GRID, "n_draws": DRAWS, "n_models": NMODELS,
    "policies": int(N), "total_evaluations": total_evals,
    "wallclock_s": round(elapsed, 1), "est_cost_usd": est_cost,
    "ran_at": pd.Timestamp.utcnow(),
}])
(spark.createDataFrame(meta).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_heavy_meta"))
print(f"optimisation_scenarios_stochastic: {len(stoch)} candidates × {DRAWS} draws over {N:,} policies; "
      f"{total_evals:,} evaluations in {elapsed:.1f}s (~${est_cost} est).")

# COMMAND ----------

dbutils.notebook.exit(json.dumps({
    "preset": preset, "disagreement_segments": len(dis), "stochastic_candidates": len(stoch),
    "total_evaluations": total_evals, "wallclock_s": round(elapsed, 1), "est_cost_usd": est_cost,
}))

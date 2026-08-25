# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — closed loop: advance one month (§3 tail, Principle 6)
# MAGIC
# MAGIC The "did it work?" beat, run live in the room. Takes the **deployed factor
# MAGIC table** (the decision the human just approved), rolls the synthetic timeline
# MAGIC forward one month, and generates that month's new-business outcomes **under
# MAGIC the deployed prices** — conversion responds to the new price via the same
# MAGIC governed elasticity curve. Then it compares what the solver **predicted** to
# MAGIC what the book **realized**, and appends the realized month to the monitoring
# MAGIC series so the drift chart visibly moves.
# MAGIC
# MAGIC Writes:
# MAGIC  * `optimisation_advance_result` — per-segment predicted vs realized
# MAGIC    (conversion, GWP, profit) for the advanced month + the portfolio roll-up.
# MAGIC  * appends the realized month to `optimisation_monitoring` (actual vs expected).
# MAGIC  * appends the new month's quotes to `optimisation_quote_response` (so a
# MAGIC    re-fit would see the book reacting — the loop is genuinely closed).

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
fqn = f"{catalog}.{schema}"

import numpy as np, pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pyspark.sql.functions as F

# reproducible per advanced month, but advances with the calendar
np.random.seed(int(datetime.utcnow().strftime("%Y%m")) % 100000)

def segment_of(df):
    age = pd.to_numeric(df.get("driver_age"), errors="coerce").fillna(45)
    vg  = pd.to_numeric(df.get("vehicle_group"), errors="coerce").fillna(20)
    ab = np.where(age < 25, "U25", np.where(age < 70, "25-70", "70+"))
    vb = np.where(vg < 15, "grpLow", np.where(vg < 30, "grpMid", "grpHigh"))
    return pd.Series([f"{a} · {v}" for a, v in zip(ab, vb)], index=df.index)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Inputs — the deployed decision + the governed elasticity

# COMMAND ----------

snap = spark.table(f"{fqn}.optimisation_portfolio_snapshot").toPandas()
for c in ["loaded_premium", "technical_premium"]:
    snap[c] = pd.to_numeric(snap[c], errors="coerce").fillna(0.0)
snap["segment"] = segment_of(snap)

# Prefer the DEPLOYED factor set; fall back to the solved factor table.
fac = spark.table(f"{fqn}.optimisation_factor_table").toPandas()
fac["factor"] = pd.to_numeric(fac["factor"], errors="coerce").fillna(1.0)
factor_by_seg = dict(zip(fac["segment"], fac["factor"]))
pred_conv_by_seg = dict(zip(fac["segment"], pd.to_numeric(fac["conversion_opt"], errors="coerce")))

curve = spark.table(f"{fqn}.optimisation_elasticity_curve").toPandas()
grids = {s: curve[curve.segment == s].sort_values("price_multiplier")["price_multiplier"].values
         for s in curve["segment"].unique()}
convs = {s: curve[curve.segment == s].sort_values("price_multiplier")["conversion_prob"].values
         for s in curve["segment"].unique()}

def conv_at(seg, f):
    if seg not in grids:
        return 0.6
    return float(np.clip(np.interp(f, grids[seg], convs[seg]), 0.0, 1.0))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Advance the month — realize outcomes under the deployed prices
# MAGIC The new month sits one after the latest quote month. Each policy is re-offered
# MAGIC at its segment's **deployed** factor; conversion is drawn from the governed
# MAGIC elasticity curve at that price, with a small fresh shock so realized ≠ exactly
# MAGIC predicted (the world has noise). This is the honest "did it work" test.

# COMMAND ----------

qr_prev = spark.table(f"{fqn}.optimisation_quote_response")
prev_max_month = qr_prev.agg(F.max("month_idx")).collect()[0][0] or 0
new_month_idx = int(prev_max_month) + 1
anchor = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
new_month_start = (anchor + relativedelta(months=1)).date()

n = len(snap)
seg = snap["segment"].values
factors = np.array([factor_by_seg.get(s, 1.0) for s in seg], dtype=float)
loaded = snap["loaded_premium"].values
technical = snap["technical_premium"].values
offered = loaded * factors                                  # the deployed price
p_pred = np.array([conv_at(seg[i], factors[i]) for i in range(n)])
# small realized shock (±3pp) so the book doesn't reproduce the prediction exactly
p_real = np.clip(p_pred + np.random.normal(0.0, 0.03, n), 0.01, 0.99)
bound = (np.random.random(n) < p_real).astype(int)

realized_gwp = float(np.sum(offered * bound))
realized_profit = float(np.sum((offered - technical) * bound))
realized_conv = float(bound.mean())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Predicted vs realized — per segment + roll-up

# COMMAND ----------

rows = []
for s in sorted(set(seg)):
    m = seg == s
    if m.sum() == 0:
        continue
    pred_c = float(pred_conv_by_seg.get(s, np.nan))
    real_c = float(bound[m].mean())
    pred_profit = float(np.sum((offered[m] - technical[m]) * conv_at(s, factor_by_seg.get(s, 1.0))))
    real_profit = float(np.sum((offered[m] - technical[m]) * bound[m]))
    rows.append({
        "advanced_month": new_month_start, "segment": s, "policies": int(m.sum()),
        "factor": round(float(factor_by_seg.get(s, 1.0)), 4),
        "predicted_conversion": round(pred_c, 4) if pred_c == pred_c else None,
        "realized_conversion": round(real_c, 4),
        "predicted_profit": round(pred_profit, 2), "realized_profit": round(real_profit, 2),
        "profit_delta_pct": round((real_profit / pred_profit - 1) * 100, 2) if pred_profit else None,
    })
res = pd.DataFrame(rows)
(spark.createDataFrame(res).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_advance_result"))

pred_profit_total = float(res["predicted_profit"].sum())
print(f"advanced to month {new_month_idx} ({new_month_start}): realized profit £{realized_profit:,.0f} "
      f"vs predicted £{pred_profit_total:,.0f} "
      f"({(realized_profit/pred_profit_total-1)*100:+.1f}%), realized conversion {realized_conv:.1%}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Append the realized month to monitoring + the quote stream (close the loop)

# COMMAND ----------

# monitoring row for the new month (expected = the governed curve; actual = realized)
exp_conv = float(np.mean([conv_at(seg[i], factors[i]) for i in range(n)]))
mon_row = pd.DataFrame([{
    "quote_month": new_month_start, "quotes": int(n),
    "actual_conversion": round(realized_conv, 4),
    "expected_conversion": round(exp_conv, 4),
    "drift": round(realized_conv - exp_conv, 4),
}])
(spark.createDataFrame(mon_row).write.mode("append").saveAsTable(f"{fqn}.optimisation_monitoring"))

# append the new month's quotes so a re-fit sees the reaction (genuinely closed loop)
vs_market_est = offered / np.clip(loaded * np.random.lognormal(0.0, 0.10, n), 1e-6, None)
new_quotes = pd.DataFrame({
    "quote_id": [f"MQ-ADV{new_month_idx:02d}-{i:07d}" for i in range(n)],
    "policy_id": snap["policy_id"].values,
    "quote_month": [new_month_start] * n,
    "driver_age": pd.to_numeric(snap.get("driver_age"), errors="coerce").fillna(45).values,
    "vehicle_group": snap.get("vehicle_group").values,
    "region": snap.get("region").values,
    "no_claims_years": pd.to_numeric(snap.get("no_claims_years", 0), errors="coerce").fillna(0).values,
    "annual_mileage": pd.to_numeric(snap.get("annual_mileage", 0), errors="coerce").fillna(0).values,
    "vehicle_value": pd.to_numeric(snap.get("vehicle_value", 0), errors="coerce").fillna(0).values,
    "technical_premium": np.round(technical, 2),
    "loaded_premium": np.round(loaded, 2),
    "offered_premium": np.round(offered, 2),
    "market_premium": np.round(loaded * np.random.lognormal(0.0, 0.10, n), 2),
    "vs_technical": np.round(offered / loaded, 4),
    "vs_market": np.round(vs_market_est, 4),
    "month_idx": np.full(n, new_month_idx, dtype=int),
    "outcome": np.where(bound == 1, "bound", "lost"),
    "converted": bound.astype(int),
})
new_quotes["bound_ts"] = [ (datetime.combine(new_month_start, datetime.min.time())
                            + timedelta(days=int(np.random.randint(0, 27)))) if bound[i] else None
                           for i in range(n) ]
(spark.createDataFrame(new_quotes).write.mode("append").option("mergeSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_quote_response"))
print(f"appended {n:,} realized quotes for month {new_month_idx}; monitoring now has the new month")

# COMMAND ----------

import json
dbutils.notebook.exit(json.dumps({
    "advanced_month_idx": new_month_idx, "advanced_month": str(new_month_start),
    "realized_profit": round(realized_profit, 2), "predicted_profit": round(pred_profit_total, 2),
    "realized_conversion": round(realized_conv, 4),
}))

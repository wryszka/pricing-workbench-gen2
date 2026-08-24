# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — Block 1: motor quote-response + renewal data (§3)
# MAGIC
# MAGIC The optimization module runs on **personal motor** (optimization's native
# MAGIC habitat). Motor is a *policies-only* book today — no quote stream, no
# MAGIC bound/lost outcomes, no renewal offers. This notebook manufactures that
# MAGIC missing behavioural layer **on top of the real risk models**, so elasticity
# MAGIC is learnable and the price variable can enter as a **ratio to technical
# MAGIC price** (never raw price — raw price is endogenous to risk).
# MAGIC
# MAGIC Writes three governed tables (naming: `optimisation_*`, evolved in place —
# MAGIC this module deliberately keeps the existing British/`optimisation_` prefix
# MAGIC rather than the spec's `opt_*`, per the build decision):
# MAGIC  * `optimisation_quote_response`    — one row per new-business quote: risk
# MAGIC     features, technical premium, offered premium, market benchmark, the
# MAGIC     price ratios, month, and the outcome (bound/lost) + bound_ts.
# MAGIC  * `optimisation_renewal_response`  — one row per renewal offer: prior vs
# MAGIC     offered premium, technical, tenure, GIPP flag, retained/lapsed.
# MAGIC  * `optimisation_portfolio_snapshot`— the current in-force book for
# MAGIC     simulation, with technical premium stamped.
# MAGIC
# MAGIC **Key design (the endogeneity answer, made concrete):** technical premium
# MAGIC comes from the live `freq_glm_motor × sev_glm_motor` champions. Historical
# MAGIC *offers* are scattered around the loaded premium by an injected
# MAGIC `price_variation_sd` (test-cell / pricing noise) — otherwise a deterministic
# MAGIC engine emits one price per risk and elasticity is unidentifiable. Conversion
# MAGIC is driven by price **competitiveness vs market**, with the sensitivity
# MAGIC **drifting month over month** so monitoring has real movement.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
dbutils.widgets.text("price_variation_sd", "0.12")   # log-normal sd of offer vs loaded premium (~±12%)
dbutils.widgets.text("n_months",          "13")      # rolling months of history to synthesise
dbutils.widgets.text("max_policies",       "120000") # cap the book sampled into pandas for scoring
dbutils.widgets.text("base_conv_elasticity", "6.0")  # new-business price sensitivity (logit slope vs market)
dbutils.widgets.text("base_ret_elasticity",  "9.0")  # renewal price sensitivity (higher: renewals stickier to shocks)

catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
PVAR    = float(dbutils.widgets.get("price_variation_sd"))
NMON    = int(dbutils.widgets.get("n_months"))
MAXPOL  = int(dbutils.widgets.get("max_policies"))
CONV_E  = float(dbutils.widgets.get("base_conv_elasticity"))
RET_E   = float(dbutils.widgets.get("base_ret_elasticity"))
fqn = f"{catalog}.{schema}"

import numpy as np, pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pyspark.sql.functions as F

np.random.seed(42)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Technical premium — a transparent risk cost line
# MAGIC `technical = annual_frequency × severity`, both readable functions of the
# MAGIC policy's risk features (age, NCD, prior accidents, mileage, telematics
# MAGIC behaviour; vehicle value/group). This is the **cost floor** optimisation
# MAGIC shapes margin above — and the denominator for the price ratio in §4, so
# MAGIC price never enters the demand model raw (raw price is endogenous to risk).
# MAGIC Open code on purpose; swappable for the `freq_glm_motor × sev_glm_motor`
# MAGIC champions (identical `technical = freq/exposure × sev` shape) once the FE
# MAGIC score_batch signature typing is reconciled. `loaded` adds expenses +
# MAGIC commission from the champion `rating_engine_config` row.

# COMMAND ----------

cfg = spark.sql(f"""
    SELECT * FROM {fqn}.rating_engine_config
    WHERE status = 'champion' ORDER BY effective_date DESC LIMIT 1
""").toPandas().iloc[0].to_dict()
EXP_LOAD   = float(cfg.get("expense_loading_pct", 22.0)) / 100.0
COMMISSION = float(cfg.get("commission_bp", 0.0)) / 10_000.0
MIN_PREM   = float(cfg.get("min_premium", 150.0))
MAX_PREM   = float(cfg.get("max_premium", 50_000.0))
print(f"expense_load={EXP_LOAD:.3f} commission={COMMISSION:.4f} floors=[{MIN_PREM},{MAX_PREM}]")

# In-force book (sampled) → pandas for the transparent cost line + quote generation.
book_sdf = spark.table(f"{fqn}.unified_motor_table_live")
n_book = book_sdf.count()
frac = min(1.0, MAXPOL / max(1, n_book))
book = (book_sdf.sample(frac, seed=7) if frac < 1.0 else book_sdf).toPandas()
print(f"book={n_book:,} scored_sample={len(book):,} (frac={frac:.3f})")

def col(name, default):
    return pd.to_numeric(book[name], errors="coerce").fillna(default).values if name in book.columns \
        else np.full(len(book), default, dtype=float)

age   = col("driver_age", 45.0)
ncd   = np.clip(col("no_claims_years", 3.0), 0, 15)
acc   = col("prior_accidents_5y", 0.0)
miles = col("annual_mileage", 8000.0)
beh   = col("behaviour_score", 75.0)          # 0–100, higher = safer
vval  = col("vehicle_value", 12000.0)
vgrp  = col("vehicle_group", 20.0)            # ABI-style group

# Annual claim frequency — monotone in the obvious directions.
age_mult  = np.where(age < 25, 2.4, np.clip(1.8 - 0.02 * (age - 25), 0.6, 1.8))
ncd_mult  = 1.0 / (1.0 + 0.07 * ncd)
acc_mult  = 1.0 + 0.20 * acc
mile_mult = np.sqrt(np.clip(miles / 8000.0, 0.6, 2.0))
beh_mult  = np.clip(1.4 - beh / 125.0, 0.7, 1.4)
annual_freq = np.clip(0.11 * age_mult * ncd_mult * acc_mult * mile_mult * beh_mult, 0.02, 1.2)

# Severity — scales with vehicle value + group.
severity = 3200.0 * np.power(np.clip(vval / 12000.0, 0.4, 4.0), 0.6) * np.clip(vgrp / 20.0, 0.5, 2.2)

technical = np.clip(annual_freq * severity, MIN_PREM, MAX_PREM)   # pure risk cost line
loaded    = np.clip(technical * (1.0 + EXP_LOAD) * (1.0 + COMMISSION), MIN_PREM, MAX_PREM)
book["technical_premium"] = np.round(technical, 2)
book["loaded_premium"]    = np.round(loaded, 2)
print(f"annual_freq mean {annual_freq.mean():.3f}  technical mean £{technical.mean():,.0f}  loaded mean £{loaded.mean():,.0f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. `optimisation_quote_response` — new-business quotes with outcomes
# MAGIC For each sampled risk we emit one quote in a randomly-assigned rolling
# MAGIC month. The **offer** is the loaded premium scattered by `price_variation_sd`
# MAGIC (the injected variation). The **market** benchmark tracks risk with its own
# MAGIC noise (competitors also price on risk). Conversion is logistic in
# MAGIC competitiveness `offered/market`, with the slope drifting by month.

# COMMAND ----------

n = len(book)
anchor = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
# Month index 0 = oldest, NMON-1 = current month.
month_idx = np.random.randint(0, NMON, size=n)
month_start = np.array([anchor - relativedelta(months=int(NMON - 1 - m)) for m in month_idx])

offer_noise  = np.random.lognormal(mean=0.0, sigma=PVAR, size=n)      # our historical offer scatter
market_noise = np.random.lognormal(mean=0.0, sigma=0.10, size=n)      # competitor benchmark scatter

offered = np.clip(loaded * offer_noise, MIN_PREM, MAX_PREM)
market  = np.clip(loaded * market_noise, MIN_PREM, MAX_PREM)
vs_technical = offered / technical                                    # THE price variable for §4
vs_market    = offered / market                                      # competitiveness (drives bind)

# Elasticity drifts subtly month to month (±20% sinusoid) so monitoring moves and
# the drift sentinel has a genuine signal.
drift = 1.0 + 0.20 * np.sin(2 * np.pi * month_idx / max(1, NMON))
z = 0.9 - CONV_E * drift * (vs_market - 1.0)                          # competitiveness → bind
# Young drivers shop harder (extra sensitivity); loyal/low-risk convert a touch more.
age = pd.to_numeric(book.get("driver_age", pd.Series([40]*n)), errors="coerce").fillna(40).values
z = z - np.where(age < 25, 0.5, 0.0)
p_bind = 1.0 / (1.0 + np.exp(-z))
bound = (np.random.random(n) < p_bind).astype(int)

# bound_ts within the quote's month (only meaningful for bound rows).
bound_ts = [ (month_start[i] + timedelta(days=int(np.random.randint(0, 27)),
                                         hours=int(np.random.randint(0, 24)))) if bound[i] else None
             for i in range(n) ]

qr = pd.DataFrame({
    "quote_id":          [f"MQ-{i:08d}" for i in range(n)],
    "policy_id":         book["policy_id"].values,
    "quote_month":       [d.date() for d in month_start],
    "driver_age":        age,
    "vehicle_group":     book.get("vehicle_group"),
    "region":            book.get("region"),
    "no_claims_years":   pd.to_numeric(book.get("no_claims_years", 0), errors="coerce").fillna(0).values,
    "annual_mileage":    pd.to_numeric(book.get("annual_mileage", 0), errors="coerce").fillna(0).values,
    "vehicle_value":     pd.to_numeric(book.get("vehicle_value", 0), errors="coerce").fillna(0).values,
    "technical_premium": np.round(technical, 2),
    "loaded_premium":    np.round(loaded, 2),
    "offered_premium":   np.round(offered, 2),
    "market_premium":    np.round(market, 2),
    "vs_technical":      np.round(vs_technical, 4),
    "vs_market":         np.round(vs_market, 4),
    "month_idx":         month_idx.astype(int),
    "outcome":           np.where(bound == 1, "bound", "lost"),
    "converted":         bound.astype(int),
})
qr["bound_ts"] = bound_ts
(spark.createDataFrame(qr)
     .write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_quote_response"))
print(f"optimisation_quote_response: {n:,} quotes, bind rate {bound.mean():.1%}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. `optimisation_renewal_response` — renewal offers (prior vs offered)
# MAGIC Prior premium = the in-force `current_premium`; the offered renewal is the
# MAGIC loaded premium scattered. Retention is logistic in the **rate change**
# MAGIC (offered/prior). GIPP flag marks offers above the equivalent new-business
# MAGIC price (renewal must not exceed new business).

# COMMAND ----------

_cur = pd.to_numeric(book.get("current_premium", pd.Series([np.nan] * n)), errors="coerce").values
prior = np.clip(np.where(np.isnan(_cur), loaded, _cur), MIN_PREM, MAX_PREM)
# Renewals move MODESTLY off the prior (anchored, not re-quoted from scratch) —
# a small inflation-ish change with scatter — so rate_change is realistic.
ren_change  = np.random.lognormal(mean=0.03, sigma=0.06, size=n)     # ~+3% ± 6%
offered_ren = np.clip(prior * ren_change, MIN_PREM, MAX_PREM)
rate_change = offered_ren / prior
equiv_new_business = loaded                                          # fresh new-business price, same risk
gipp_breach = (offered_ren > equiv_new_business + 1e-6).astype(int)  # renewal above equivalent new business

zr = 2.2 - RET_E * (rate_change - 1.0)                                # small increase tolerated; big shocks lapse
ncd = pd.to_numeric(book.get("no_claims_years", 0), errors="coerce").fillna(0).values
zr = zr + np.clip(ncd, 0, 15) * 0.05                                 # loyal customers stickier
p_retain = 1.0 / (1.0 + np.exp(-zr))
retained = (np.random.random(n) < p_retain).astype(int)
ren_month = np.random.randint(0, NMON, size=n)

rr = pd.DataFrame({
    "renewal_id":        [f"MR-{i:08d}" for i in range(n)],
    "policy_id":         book["policy_id"].values,
    "renewal_month":     [ (anchor - relativedelta(months=int(NMON - 1 - m))).date() for m in ren_month ],
    "tenure_years":      np.clip(ncd, 0, 25).astype(int),
    "technical_premium": np.round(technical, 2),
    "prior_premium":     np.round(prior, 2),
    "offered_premium":   np.round(offered_ren, 2),
    "equiv_new_business_premium": np.round(equiv_new_business, 2),
    "rate_change":       np.round(rate_change, 4),
    "vs_technical":      np.round(offered_ren / technical, 4),
    "gipp_breach":       gipp_breach,
    "month_idx":         ren_month.astype(int),
    "outcome":           np.where(retained == 1, "retained", "lapsed"),
    "retained":          retained.astype(int),
})
(spark.createDataFrame(rr)
     .write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_renewal_response"))
print(f"optimisation_renewal_response: {n:,} renewals, retention {retained.mean():.1%}, GIPP breaches {gipp_breach.sum():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. `optimisation_portfolio_snapshot` — current book for simulation

# COMMAND ----------

snap = book[["policy_id", "driver_age", "vehicle_group", "region", "no_claims_years",
             "annual_mileage", "vehicle_value", "technical_premium", "loaded_premium",
             "current_premium"]].copy()
snap["current_premium"] = pd.to_numeric(snap["current_premium"], errors="coerce").fillna(snap["loaded_premium"])
snap["vs_technical_now"] = np.round(snap["current_premium"] / snap["technical_premium"], 4)
(spark.createDataFrame(snap)
     .write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_portfolio_snapshot"))
print(f"optimisation_portfolio_snapshot: {len(snap):,} in-force policies")

# COMMAND ----------

print("Block 1 complete → optimisation_quote_response, optimisation_renewal_response, optimisation_portfolio_snapshot")

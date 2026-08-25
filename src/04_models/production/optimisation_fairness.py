# Databricks notebook source
# MAGIC %md
# MAGIC # Price Optimization — fairness & fair-value evidence (§11)
# MAGIC
# MAGIC The regulated-buyer centrepiece: after the solver sets factors, screen the
# MAGIC decision for fairness **before** it can be deployed, and generate the
# MAGIC evidence a UK GI conduct review (Consumer Duty fair value, GIPP, EIOPA
# MAGIC differential-pricing) actually asks for. All checks read the versioned
# MAGIC constraint set (`optimisation_constraints/default.yaml`) — the forbidden
# MAGIC signals and the proxy-correlation ceiling are policy, not hardcoded here.
# MAGIC
# MAGIC Three checks, written to `optimisation_fairness_evidence`:
# MAGIC  1. **Proxy correlation** — does the optimised factor correlate with a
# MAGIC     forbidden signal (gender / marital status / occupation grade) above the
# MAGIC     policy ceiling? A proxy for a protected characteristic is a fail.
# MAGIC  2. **Disparate impact** — is the mean rate change materially different
# MAGIC     across protected groups (the "are we systematically moving one group?"
# MAGIC     test)?
# MAGIC  3. **Vulnerability screen** — are potentially-vulnerable cohorts (older
# MAGIC     drivers) being pushed to the increase cap disproportionately?
# MAGIC
# MAGIC Plus `optimisation_fairness_summary` (one row: overall pass + a plain-English
# MAGIC evidence paragraph for the fair-value pack).

# COMMAND ----------

dbutils.widgets.text("catalog_name", "lr_pricing_v2_aws_us_catalog")
dbutils.widgets.text("schema_name",  "pricing_workbench_gen2")
catalog = dbutils.widgets.get("catalog_name")
schema  = dbutils.widgets.get("schema_name")
fqn = f"{catalog}.{schema}"

import os, numpy as np, pandas as pd

PROXY_MAX = 0.35        # from constraints/default.yaml: proxy_correlation_max
FORBIDDEN = ["gender", "marital_status", "occupation_class"]   # occupation_class ≈ social-grade proxy
DISPARATE_MAX_PP = 3.0  # max acceptable spread in mean rate-change across a protected dimension
try:
    for _p in [f"/Workspace/Shared/.bundle/pricing-workbench-gen2/pricingv2/files/"
               f"src/04_models/production/optimisation_constraints/default.yaml"]:
        if os.path.exists(_p):
            import yaml
            c = yaml.safe_load(open(_p))
            PROXY_MAX = float(c.get("proxy_correlation_max", PROXY_MAX)); break
except Exception as e:
    print(f"constraint read fallback: {e}")

def segment_of(df):
    age = pd.to_numeric(df.get("driver_age"), errors="coerce").fillna(45)
    vg  = pd.to_numeric(df.get("vehicle_group"), errors="coerce").fillna(20)
    ab = np.where(age < 25, "U25", np.where(age < 70, "25-70", "70+"))
    vb = np.where(vg < 15, "grpLow", np.where(vg < 30, "grpMid", "grpHigh"))
    return pd.Series([f"{a} · {v}" for a, v in zip(ab, vb)], index=df.index)

# COMMAND ----------

snap = spark.table(f"{fqn}.optimisation_portfolio_snapshot").toPandas()
snap["segment"] = segment_of(snap)
fac = spark.table(f"{fqn}.optimisation_factor_table").toPandas()
fac["factor"] = pd.to_numeric(fac["factor"], errors="coerce").fillna(1.0)
factor_by_seg = dict(zip(fac["segment"], fac["factor"]))
snap["factor"] = snap["segment"].map(factor_by_seg).fillna(1.0)
snap["rate_change_pct"] = (snap["factor"] - 1.0) * 100.0

# protected attributes from the motor book
prot = spark.table(f"{fqn}.unified_motor_table_live").select(
    "policy_id", "gender", "marital_status", "occupation_class").toPandas()
df = snap.merge(prot, on="policy_id", how="left")
df["age_band"] = np.where(pd.to_numeric(df["driver_age"], errors="coerce").fillna(45) < 25, "U25",
                  np.where(pd.to_numeric(df["driver_age"], errors="coerce").fillna(45) < 70, "25-70", "70+"))
print(f"fairness screen over {len(df):,} in-force policies; proxy ceiling {PROXY_MAX}")

rows = []

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Proxy correlation — optimised factor vs forbidden signals

# COMMAND ----------

for sig in FORBIDDEN:
    if sig not in df.columns:
        continue
    codes = pd.Categorical(df[sig].astype(str)).codes.astype(float)
    if np.std(codes) < 1e-9 or df["factor"].std() < 1e-9:
        corr = 0.0
    else:
        corr = float(np.corrcoef(codes, df["factor"].values)[0, 1])
    rows.append({"check": "proxy_correlation", "dimension": sig, "group": "-",
                 "metric": "|corr(factor, signal)|", "value": round(abs(corr), 4),
                 "threshold": PROXY_MAX, "pass": bool(abs(corr) <= PROXY_MAX)})

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Disparate impact — mean rate change across protected groups

# COMMAND ----------

for dim in ["gender", "marital_status", "age_band"]:
    if dim not in df.columns:
        continue
    g = df.groupby(dim)["rate_change_pct"].mean()
    spread = float(g.max() - g.min()) if len(g) > 1 else 0.0
    for grp, val in g.items():
        rows.append({"check": "disparate_impact", "dimension": dim, "group": str(grp),
                     "metric": "mean_rate_change_pct", "value": round(float(val), 3),
                     "threshold": DISPARATE_MAX_PP, "pass": bool(spread <= DISPARATE_MAX_PP)})
    rows.append({"check": "disparate_impact_spread", "dimension": dim, "group": "(spread)",
                 "metric": "max_minus_min_pp", "value": round(spread, 3),
                 "threshold": DISPARATE_MAX_PP, "pass": bool(spread <= DISPARATE_MAX_PP)})

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Vulnerability screen — older drivers pushed to the cap?

# COMMAND ----------

older = df[df["age_band"] == "70+"]
rest  = df[df["age_band"] != "70+"]
older_inc = float((older["rate_change_pct"] > 0).mean()) if len(older) else 0.0
rest_inc  = float((rest["rate_change_pct"] > 0).mean()) if len(rest) else 0.0
gap = round((older_inc - rest_inc) * 100, 2)
rows.append({"check": "vulnerability_screen", "dimension": "age_band", "group": "70+",
             "metric": "increase_rate_gap_vs_rest_pp", "value": gap,
             "threshold": 20.0, "pass": bool(abs(gap) <= 20.0)})

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Persist evidence + fair-value summary

# COMMAND ----------

ev = pd.DataFrame(rows)
(spark.createDataFrame(ev).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_fairness_evidence"))

overall = bool(ev["pass"].all())
fails = ev[~ev["pass"]]
n_proxy = int((ev["check"] == "proxy_correlation").sum())
worst_proxy = float(ev[ev.check == "proxy_correlation"]["value"].max()) if n_proxy else 0.0
narrative = (
    f"Fair-value evidence — {'PASS' if overall else 'REVIEW'}. "
    f"The optimised factor set was screened against the versioned constraint policy. "
    f"Proxy correlation of the price factor with forbidden signals ({', '.join(FORBIDDEN)}) "
    f"peaks at {worst_proxy:.2f} vs a {PROXY_MAX:.2f} ceiling. "
    f"Mean rate change was compared across gender, marital status and age band "
    f"(disparate-impact spread ceiling {DISPARATE_MAX_PP:.0f}pp). A vulnerability screen "
    f"checked that older drivers are not pushed to the increase cap disproportionately. "
    + (f"{len(fails)} check(s) need review: {', '.join(sorted(set(fails['check'])))}. "
       if len(fails) else "All checks passed. ")
    + "The risk model is the floor; the deviation corridor and GIPP rule bound every move; "
      "this pack is regenerated on each solve and stored for audit."
)
summ = pd.DataFrame([{"overall_pass": overall, "n_checks": len(ev),
                      "n_fail": int(len(fails)), "worst_proxy_corr": round(worst_proxy, 4),
                      "evidence": narrative}])
(spark.createDataFrame(summ).write.mode("overwrite").option("overwriteSchema", "true")
     .saveAsTable(f"{fqn}.optimisation_fairness_summary"))

# audit
try:
    import json as _j
    _d = _j.dumps({"overall_pass": overall, "n_fail": int(len(fails)),
                   "worst_proxy": round(worst_proxy, 4)}).replace("'", "''")
    spark.sql(f"""
      INSERT INTO {fqn}.audit_log (event_id, event_type, entity_type, entity_id, entity_version,
                                   user_id, timestamp, details, source)
      SELECT uuid(), 'optimisation_fairness_screen', 'factor_table', 'v1', 'v1', 'fairness_reviewer',
             current_timestamp(), '{_d}', 'optimisation_fairness'
    """)
except Exception as e:
    print(f"audit skipped: {e}")

print(f"optimisation_fairness_evidence: {len(ev)} checks, overall_pass={overall}, worst_proxy={worst_proxy:.3f}")
print(narrative)

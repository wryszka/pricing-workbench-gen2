# Optimization Inventory — pricing-workbench-gen2

> **⚠️ SUPERSEDED 2026-08-25 — Phase 1 (offline spine, motor) SHIPPED.** This file
> describes the *pre-build* state (the commercial worked-example). The motor spine
> now replaces it: data → monotone elasticity (price ÷ technical) → simulation →
> constrained solver (versioned YAML) → monitoring → app (frontier, waterfall,
> objective front door, approve→deploy HITL, red-team panels). The commercial
> `price_optimiser.py` + its job were removed. **See `docs/optimisation_runbook.md`
> for the current state.** GATE-1 (below) remains the one open item.

Read-only inventory of what the repo **actually contains and runs today** (not intent),
to reconcile against `OPTIMIZATION_MODULE_SPEC.md`. Produced 2026-08-24.

- Repo: `wryszka/pricing-workbench-gen2`
- Live workspace inspected: `fevm-lr-pricing-v2-aws-us` (profile `PRICING_V2`),
  catalog `lr_pricing_v2_aws_us_catalog`, schema `pricing_workbench_gen2`.
- Where a thing is a placeholder / legacy / mock, it is called out explicitly.

## ⛔ OPEN GATES (must close before external demo)

- **GATE-1 · technical_premium must be champion-scored.** `technical_premium`
  must be scored by the champion `freq_glm_motor × sev_glm_motor` before any
  external demo. Status: **PARTIAL — champion-scored ✓, lineage-edge OPEN**
  (updated 2026-08-24).
  - **Scoring: DONE.** `optimisation_motor_data.py` now defaults to
    `technical_source=champion` — technical stamped from the real champions
    (mean £654) via rung (c): load the inner sklearn flavor on the driver
    (`download_artifacts` → deepest `MLmodel`, the motor scorer's own pattern)
    and score in pandas. The transparent `annual_freq × severity` line remains
    only as `technical_source=transparent` dev scaffolding.
  - **Escalation record:** rung (a) [cast int→double before `fe.score_batch`]
    cleared the signature error but failed at model load inside FE's distributed
    `score_batch` UDF (`_clear_dependencies_schemas`); rung (b) [re-log/re-alias
    champions] skipped — targets a signature problem (a) already solved and would
    re-alias the live motor champions (invasive); rung (c) succeeded.
  - **Lineage-edge: OPEN.** UC lineage for `optimisation_quote_response` shows
    only the source table upstream — **no `champion model version → technical_premium`
    edge**, because the inner-artifact load bypasses mlflow's model-load lineage
    registration. Closing this needs the score to go through `mlflow.pyfunc`
    model loading (which threw the load error) or a lineage-emitting FE path.
    Until this edge exists, GATE-1 stays listed.

---

## 1. GIT STATE

- **Branch:** `main` · **HEAD:** `4699787` · **in sync with `origin/main`** (0 ahead, 0 behind after `git fetch`).
- **Remote:** `https://github.com/wryszka/pricing-workbench-gen2.git` (push needs `gh auth switch --user wryszka`).

**Last 10 commits (hash — message):**
```
4699787  gen2 optimisation: driven Walkthrough tab + real-asset deep-links + monitoring
57d5e2e  gen2 optimisation: add a "How it works" tab (data / model / tech)
a406749  gen2 optimization: drop the new 09_optimization module, restore the AXA worked-example optimizer
dcfafcb  optimizer: constraints endpoint reads the YAML via Workspace API (app container lacks the sibling file)
629ffd0  optimizer: fix /api/optimization/overview scenarios query (rounded a string)
fcc7724  optimizer: app page (PriceOptimisation) + /api/optimization; scale to 500k + enable optimization
19d587a  optimizer: scale-free simulation+solver (curve/aggregate), block 05 monitoring, /api/optimization router, opt_full orchestrator
358e5db  optimizer: force float cast on charged/cost in simulation (Decimal survived coercion loop)
57264dc  optimizer: coerce snapshot decimals->float in simulation/solver (fixes float-Decimal TypeError)
95492d7  optimizer: coerce retention numerics (Spark decimal->object) in elasticity block
```

**History note (important for reconciliation):** commits `95492d7 → fcc7724` and `dcfafcb`/`629ffd0`
built a **different, larger** optimization module (`src/09_optimization/*`, American-spelled
`/api/optimization`, `opt_*` tables, `pwg2_conversion_elasticity`/`pwg2_retention_elasticity`
LightGBM models, an `opt_full` orchestrator). That module was **deleted** in `a406749` and replaced
by the restored worked-example optimiser. The current optimisation work is the last three commits
(`a406749`, `57d5e2e`, `4699787`). The `opt_*` tables/models were dropped from the schema.

**Uncommitted / untracked:**
- `M src/app/frontend/src/pages/RatingEngineIntegration.tsx` — **not pushed.** Adds a hardcoded
  `docs.google.com` link constant (`ACTUARIAL_SW_INTEGRATIONS_DOC`). **Not** optimization- or
  Learn-related.
- No untracked files.

**Flag:** nothing optimization- or Learn-related is unpushed — all three optimisation/Learn commits
are on `origin/main`. The only local diff is the unrelated `RatingEngineIntegration.tsx` edit.

---

## 2. APP SURFACES

### Sidebar pages (`src/app/frontend/src/App.tsx`, `NAV_ITEMS` L28–38 + Learn tile L74–81)
`/` Home · `/datasets` Data Ingestion · `/pricing-table` Modelling Mart · `/development` Model
Development · `/deployment` Model Deployment · `/pricing-engine` Pricing Engine · **`/optimisation`
Price Optimisation** · `/governance` Model Governance · `/pricing-ai` Pricing AI · `/models` Model
Factory · `/add-ons` Add-ons · **`/learn` Learn · Pricing 101** (separate tile in sidebar footer).
Full-screen routes (outside chrome): `/quote`, `/quote-chat`, `/blackbox`, `/quotetester`.

### FastAPI routers (`src/app/app.py` L56–76)
`datasets, agent, features, deployment, governance, quote_stream, genie, development, review,
compare, factory, factory_real, pricing, admin, supervisor, live_pricing, mcp, broker, distribution,
optimisation, overview`. **`optimisation.router` = the only optimisation surface.**

### Optimization surface — `/optimisation` → `src/app/frontend/src/pages/PriceOptimisation.tsx` (three tabs)
| Tab | Renders | API calls | Live vs static |
|---|---|---|---|
| **Optimiser** | Interactive per-segment solve: levers (objective profit/volume/blend, rate-change cap, margin floor), portfolio roll-up KPIs, efficient frontier (SVG), per-segment demand/profit curve, per-segment table, governed-scenario config. The *decision* re-solves **client-side** (`choose()`/`frontier` in-browser) over precomputed curves. | `api.optimisationSummary()` → `/api/optimisation/summary` | **LIVE** — reads `optimisation_summary`, `optimisation_curve`, `optimisation_config`. |
| **Walkthrough** | 7-beat driven story (market event → change to X → run → result → monitor → govern → agent). Sets the Optimiser levers, triggers the **real** job, renders a monitor chart, calls an agent. | `api.optRun()`/`api.optRunStatus()` (POST `/api/optimisation/run` + poll `/run/{id}`), `api.optMonitoring()` (`/monitoring`), `api.agentLead({persona:'rate_change'})` (`/api/agent/lead` → `pwg2_chat_agent`), `api.optAssets()` (`/assets`) for deep-link chips | **LIVE** — real `run-now` on the `price_optimiser` job, live `optimisation_monitoring`, live agent endpoint. |
| **How it works** | Pipeline strip, Data / Model & method / Underlying tech cards, the decision formula, governed-config row. | `api.optAssets()` (deep-link chips) + counts from the loaded summary | **Mostly static prose** + **live** deep-link chips + live `segCount`/`totalQuotes`. |

### Learn surface — `/learn` → `src/app/frontend/src/pages/Learn.tsx` (207 lines)
**Fully STATIC** "Pricing 101" explainer. Only JS is an `IntersectionObserver` scroll-spy over
static `PANELS` (`what … platform & deploy`). **No API calls, no live data, no optimisation data.**

### `/api/optimisation/*` endpoints (`src/app/server/routes/optimisation.py`)
`GET /summary` (L68) · `GET /assets` (L107) · `POST /run` (L139) · `GET /run/{run_id}` (L162) ·
`GET /monitoring` (L180).

---

## 3. OPTIMIZATION ASSETS

### Notebook (the optimiser)
`src/04_models/production/price_optimiser.py` (234 lines). Per-segment **sklearn
`LogisticRegression`** of `converted ~ vs_market_rate`; illustrative cost line
(`SEGMENT_LR × market_premium`, LRs 0.54→0.80); grid-search over `MULT_GRID = 0.80..1.30 step 0.02`
maximising `demand·(price−cost)` under a rate-change cap and a margin floor. Writes
`optimisation_curve`, `optimisation_summary`, `optimisation_config`, **`optimisation_monitoring`**;
logs an MLflow run `price_optimisation`.

### Job / resource
`resources/price_optimiser.yml` — job **"Price optimisation — worked example (new-business profit)
(gen2)"** (live `job_id 476495512210624`). Serverless (`environment` `client: "5"`, deps
mlflow/scikit-learn/pandas/numpy). **Job parameters:** `catalog_name, schema_name, rate_change_cap,
target_loss_ratio, margin_floor`, flowing to notebook widgets via `{{job.parameters.*}}`. App SP
`db717199-…` has `CAN_MANAGE_RUN`. **Wired into `full_build`** (`resources/full_build.yml` task
`price_optimiser`, L123; also a dep of the `tags` task L163).

### Tables (LIVE, in `pricing_workbench_gen2`)
`optimisation_summary`, `optimisation_curve`, `optimisation_config`, `optimisation_monitoring`.
- **Naming:** British `optimisation_*`, **unprefixed**, in-schema. Does **not** use `opt_*` or the
  `pwg2_` prefix (the removed module used `opt_*`; `pwg2_` is reserved for workspace-global
  endpoints/stores, not tables).
- `optimisation_monitoring` = monthly `actual_conversion` vs model-expected `expected_conversion`
  + `drift` (13 rows live; latest month Aug-2026, drift ≈ −0.19pp). Written by `price_optimiser.py`.

### Assets that do NOT exist (removed with the old module)
No `opt_scenarios`, `opt_factor_table`, `opt_elasticity_curves`, `opt_quote_response`,
`opt_portfolio_snapshot`, `opt_renewal_response`, `opt_conversion_actuals`, `opt_deviation_dist`,
`opt_scenario_segments`, `opt_constraint_breaches`. No `pwg2_conversion_elasticity` /
`pwg2_retention_elasticity` models. No `src/09_optimization/` dir. No constraints YAML
(`09_optimization/constraints/default.yaml` gone). No `opt_full` orchestrator. No `enable_optimization`
bundle var. (`factory_runs`, `factory_variants`, `derived_factors` tables exist but belong to the
**Model Factory**, not optimisation.)

### Serving / endpoints / UC functions
- **No optimisation serving endpoint.** Live endpoints: `pwg2_pricing_scorer`,
  `pwg2_motor_scorer_direct`, `pwg2_motor_scorer`, `pwg2_chat_agent`, `pwg2_governance_agent` — none
  optimisation-specific. Optimiser output is batch tables only.
- No optimisation-specific UC functions.

---

## 4. DEMAND MODEL

There are **three** demand notebooks with **three different registration names**; only two are the
production path, and **none is used by the optimiser.**

### 4a. `src/04_models/production/demand_gbm.py` — the wired commercial demand model
- **Predicts:** `P(convert)` — LightGBM binary classifier on `quotes.converted`.
- **Training table:** `{fqn}.quotes` (registered as a Feature Engineering feature table, PK
  `transaction_id`; label built as `converted ∈ {Y,1,true,True} → 1`).
- **Features** (L86–98, filtered to columns that exist): `channel, region, construction_type,
  flood_zone, year_built, floor_area_sqm, buildings_si, contents_si, liability_si, voluntary_excess,
  gross_premium_quoted, log_gross_premium, log_buildings_si, rate_per_1k_si, vs_market_rate,
  gross_premium, market_premium, market_median_rate, competitor_a_min_rate, price_index,
  annual_turnover, credit_score, flood_zone_rating, crime_theft_index, sprinklered, alarmed`.
- **Does price enter raw or as ratio?** **Both — and the ratio is vs MARKET, not vs technical
  price.** Raw: `gross_premium`, `gross_premium_quoted`, `log_gross_premium`. Ratio/market:
  `vs_market_rate` (= `gross_premium / market_premium`), `rate_per_1k_si`, `market_median_rate`,
  `competitor_a_min_rate`, `price_index`. **There is no technical-price feature and no
  price-vs-technical deviation** — the model has no notion of technical cost.
- **Registration:** `{fqn}.demand_gbm` via `fe.log_model` (LightGBM flavor, `infer_signature`).
  **`@champion` alias** is set by `src/00_setup/set_champion_aliases.py` (default families
  `freq_glm,sev_glm,demand_gbm,fraud_gbm`), **not** inline in the notebook. **Confirmed registered
  live.** Wired via `resources/production_training.yml` (task `train_demand_gbm`), which
  `full_build` runs.

### 4b. `src/04_models/production/demand_gbm_motor.py` — motor demand (parallel dataset)
- **Predicts:** synthetic `accepted` (LightGBM binary). Label is generated in-notebook:
  logistic of price-per-value `_ppk = current_premium/(vehicle_value/1000)`, NCD, behaviour_score, age.
- **Training table:** `{fqn}.unified_motor_table_live`.
- **Features:** `driver_age, license_years_held, no_claims_years, gender, marital_status,
  occupation_class, vehicle_group, vehicle_value, vehicle_age, fuel_type, annual_mileage,
  parking_overnight, business_use, current_premium, behaviour_score, claim_count_5y,
  at_fault_count_5y`. **Price enters RAW** (`current_premium`); no market ratio; no technical price.
- **Registration:** `{fqn}.demand_gbm_motor`, `@champion` set inline. Confirmed live. Wired via
  `resources/motor_models.yml` (in `full_build` motor chain).

### 4c. `src/04_models/model_03_gbm_demand.py` — LEGACY / ORPHAN
- LightGBM classifier of `converted_flag`; computes `quote_to_market_ratio = (gross_premium /
  (sum_insured/1000)) / market_median_rate` (again vs **market**), plus `log_premium`,
  competitor/location features. Displays a demand curve by `price_bucket` but **does not persist a
  table** (`display(demand_df)` only).
- **Registration name:** `{catalog}.{schema}.lgbm_demand_model`. **NOT registered in the live
  workspace, NOT referenced by any `resources/*.yml`.** This is a legacy sequential notebook
  (`model_0X_*.py` in `04_models/` root); the production path is `04_models/production/`.

### Critical reconciliation fact
`price_optimiser.py` fits its **own per-segment `LogisticRegression` on `vs_market_rate`** (L74, L97)
and **does not load `demand_gbm`** (no `models:/…@champion`, no `load_model`). **The governed GBM
demand model and the optimiser are disconnected** — two independent demand representations.

---

## 5. DEEP LINKS

Optimisation deep-links are built in `GET /api/optimisation/assets`
(`src/app/server/routes/optimisation.py` L107–130) from **`get_workspace_host()`**
(`config.py` L127, **env-driven** — `DATABRICKS_HOST` / SDK config, **not hardcoded**):
- Tables → `{host}/explore/data/{catalog}/{schema}/{table}` (Catalog Explorer) for `quotes`,
  `optimisation_summary`, `optimisation_curve`, `optimisation_config`, `optimisation_monitoring`.
- Notebook → `{host}/#workspace{path}` (path with the leading `/Workspace` stripped).
- Job → `{host}/jobs/{job_id}`; `job_id` resolved **by name** via `resolve_job_by_name`
  (`config.py` → `GET /api/2.1/jobs/list`, cached, TTL 300s — same pattern as Genie-by-title).
- Agent → `{host}/ml/endpoints/pwg2_chat_agent`.
- MLflow → `{host}/ml/experiments` — **generic, not run/experiment-specific** (effectively a
  landing link, not a precise deep-link).
- Frontend renders these via `LinkChip` (`PriceOptimisation.tsx` L~368) as `target="_blank"` anchors;
  renders nothing when the href is null (no dead links).

Other deep-link plumbing (not optimisation-specific): `GET /api/config` (`app.py` L83–108) exposes
`genie_url`/`genie_embed_url`, `mart_dashboard_url` (env-var or resolved-by-title),
`notebooks_base`, `bundle_files_base`, `workspace_host` — used by other pages.

**Hardcoded external URL (only one, and uncommitted):** `RatingEngineIntegration.tsx`
`ACTUARIAL_SW_INTEGRATIONS_DOC = 'https://docs.google.com/document/d/…'`. **No lineage-graph links,
no repo-file links, no MLflow run-specific links anywhere.**

---

## 6. DATA

### Primary dataset for the optimisation work = the COMMERCIAL book
`{fqn}.quotes`, generated by `src/00_setup/setup_quote_stream.py` (commercial property/liability
quotes). The Price Optimisation panel and `price_optimiser.py` run **only** on `quotes`.

- **Price variation in the generator: YES.** `market_premium = round(gross_premium *
  random.lognormvariate(0.0, 0.11), 2)`; `vs_market_rate = gross_premium / market_premium`
  (L277–278). Genuine offer-vs-market dispersion.
- **Bound / lost outcomes: YES.** A logistic demand curve drives conversion: `_elasticity = 8.0` if
  `gross_premium < 50_000` else `11.0`; `_z = 0.5 − _elasticity·(vs_market_rate − 1.0)`;
  `quote_status = "BOUND" if random < sigmoid(_z) else "QUOTED"`; a `force_dropout` branch yields
  `"ABANDONED"`; `converted = "Y" iff BOUND` (L281–286). `competitor_quoted` flag (~0.35). So
  `quote_status ∈ {BOUND, QUOTED, ABANDONED}` and `converted ∈ {Y,N}` = bound vs lost.
- **Renewal offers: NO** in the quote stream. `setup_quote_stream.py` has no renewal / prior-premium
  concept — it is **new-business only**.
- **Renewal / retention elsewhere (not in the optimiser path):**
  `src/04_models/model_06_retention.py` (legacy root) predicts `is_churned`, registers
  `lgbm_retention_model`; wired only in `resources/supplementary_models.yml`, which is **not** in
  `full_build`, and the model is **not registered live**. `src/03_gold/build_upt.py` carries a
  `renewal_date` column (metadata). Motor demand uses `current_premium` as positioning but there is
  **no renewal-offer table**.

### Car / motor dataset: EXISTS and is BUILT (parallel to commercial)
`src/00_setup/setup_motor.py` writes `{fqn}.motor_policies`, `{fqn}.motor_telematics_aggregate`,
`{fqn}.motor_claims_history`; `{fqn}.unified_motor_table_live` is the motor UPT. All present live.
Wired into `full_build` **core** (`motor_setup → motor_upt → motor_train → motor_scorer`). Motor
models live: `demand_gbm_motor`, `freq_glm_motor`, `sev_glm_motor`, `fraud_gbm_motor`; endpoints
`pwg2_motor_scorer_direct`, `pwg2_motor_scorer`. **However, the Price Optimisation panel/optimiser
does not touch motor** — it is commercial-`quotes`-only.

### Live registered models (UC, via `/api/2.1/unity-catalog/models`)
`demand_gbm, demand_gbm_motor, fraud_gbm, fraud_gbm_motor, freq_glm, freq_glm_motor, sev_glm,
sev_glm_motor, governance_agent, pwg2_chat_agent, pwg2_motor_scorer, pwg2_motor_scorer_direct,
pwg2_pricing_scorer`. (`lgbm_demand_model`, `lgbm_retention_model` — **absent**, confirming the root
`model_0X_*.py` notebooks are legacy/unrun.)

---

## 7. GAPS VS CONVENTIONS

1. **Optimiser ↔ governed demand model disconnect.** The optimiser uses an ad-hoc per-segment
   `LogisticRegression` inside `price_optimiser.py`; the governed, MLflow-registered `@champion`
   `demand_gbm` GBM is never loaded. Divergence from the "surface the real registered model"
   convention.
2. **Coarse "factors."** Optimiser output is 4 size-band segment multipliers in
   `optimisation_summary`, not a granular rating-factor table. There is no factor/scenario table
   (the old `opt_factor_table`/`opt_scenarios` are gone).
3. **No HITL / approval gate.** The Walkthrough triggers the `price_optimiser` job directly (app SP
   `CAN_MANAGE_RUN`). `optimisation_config` gives a versioned audit trail, but there is **no
   human sign-off / approve-before-apply** workflow — unlike Data Ingestion (dataset approve) or
   Review & Promote. The old module's constraints-YAML gate was removed.
4. **No serving tier for optimisation.** Every other model family has a scorer endpoint; the
   optimiser produces batch tables only.
5. **Demand-model naming/lineage inconsistency.** `demand_gbm` (production, live) vs
   `lgbm_demand_model` (legacy `model_03`, orphan) vs `demand_gbm_motor`. Root `model_0X_*.py`
   notebooks are a legacy path parallel to `production/`.
6. **MLflow deep-link is generic** (`/ml/experiments`), not run-specific — weaker than the
   table/job/agent links beside it.
- **Consistent with conventions:** serverless job (`client: "5"`), single-schema unprefixed tables,
  `full_build` (core) inclusion without spurious `deploy_profile` gating (only the online-store
  live-serving tier is profile-gated, in `live_pricing.yml`), and the **no-PAT automatic-auth
  passthrough** (`/run` and `agentLead` use the app's `WorkspaceClient` / app SP, not a token).

---

## 8. ONE-PARAGRAPH SUMMARY

Against a full loop (data → elasticity → simulation → solver → factors → serving → monitoring →
HITL), roughly **half genuinely exists and runs today**, and it runs as a real worked example rather
than a UI shell: **data ✅** (commercial `quotes` with true price variation and bound/lost
outcomes), **elasticity ✅ but ad-hoc** (per-segment logistic on `vs_market_rate` inside the
optimiser — the governed `demand_gbm` LightGBM exists and trains in `full_build` yet is **not** wired
into the optimiser), **simulation ◑** (a price-grid sweep plus a client-side portfolio roll-up and
efficient frontier — not stochastic/scenario simulation), **solver ✅** (constrained arg-max under a
rate-change cap and a margin floor), **factors ◑** (four size-band segment multipliers in
`optimisation_summary`, not granular rating factors), **serving ✗** (no optimisation endpoint; batch
tables only), **monitoring ✅** (`optimisation_monitoring` actual-vs-model-expected conversion
drift), **HITL ✗** (versioned `optimisation_config` audit only, no approval gate). The app layer is
**real, not mocked** — the Optimiser tab reads live tables, the Walkthrough triggers the actual
`price_optimiser` job and reads live monitoring and calls the live `rate_change` agent — but the
whole thing is a 4-segment, logistic-demand, illustrative-cost "worked example." The missing pieces
to reach the spec's end-to-end loop are: wire the governed GBM demand model into the optimiser,
add renewal/retention data to the (currently new-business-only) quote stream, produce a real
factor/scenario layer, add an optimisation serving path, and add a HITL approval gate.

# Pricing Workbench Gen2 — End-to-End System Overview

**Date:** August 2026  
**Catalog:** `lr_pricing_v2_aws_us_catalog`  
**Schema:** `pricing_workbench_gen2`  
**App:** `pricing-workbench-gen2` (Databricks Apps)  
**DAB:** `pricing-workbench-gen2` (all profiles + targets)

---

## Executive Summary

The Pricing Workbench Gen2 is a **complete commercial P&C pricing demo** for the fictional insurer "Bricksurance SE" that **demonstrates production-shaped patterns** for building governed pricing operations on Databricks — a demo on synthetic data, not a production system and not a product sold or warranted by Databricks. It is **not** a black-box accelerator but a **transparent, governed, auditable system** where every step — from raw data through live scoring to regulator-facing defense — is traceable in Unity Catalog, versioned in git, and decidable by named humans under policy.

**Core flow:**
- **Data ingestion:** External CSVs (market rates, geospatial, credit bureau) → Bronze → Silver (via DLT) → Gold (Unified Pricing Table)
- **Feature engineering:** 50K+ policies with 20+ features (real UK postcode enrichment + internal risk attributes)
- **Model training:** 4 core champions (freq/sev GLMs, demand/fraud GBMs) + 2 motor variants, trained via the GLM/GBM factory
- **Rating engine:** Versioned releases chaining champion model versions + rating config (expense/commission loadings) + constraints
- **Price optimisation:** Motor-line elasticity-driven solver (monotone conversion curves, fairness screens, immutable decision records, 7-tab app interface)
- **Agents:** Governance, explainability, chat — all on the Databricks Agent Framework, self-provisioning their SQL token on deploy
- **Governance:** Unity Catalog lineage, immutable audit log, bias demographics, regulatory export, governance PDFs for every champion

**Scale:** Serverless, scale-to-zero, 50K–500K policies depending on SCALE_FACTOR. Everything is idempotent; the Full Build orchestrator populates a fresh workspace in ~30–40 minutes.

---

## System Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PRICING WORKBENCH GEN2                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [External Data]                [Internal Data]                             │
│  ├─ Market rates CSV      ┐      ├─ Policies                              │
│  ├─ Geospatial hazard     ├──→ [Bronze Layer]  ├─ Claims                 │
│  └─ Credit bureau         │      └─ CSV files  └─ Quotes (3 JSON tables) │
│                           │                                                │
│                           └─→ [Silver Layer] ──┐                         │
│                               (DLT pipeline)   │                         │
│                                                 │                         │
│  [Reference Data]                           ┌──┴───────────────────────┐ │
│  ├─ Postcode enrichment                      │                         │ │
│  │  (ONSPD + IMD + ONS RUC)          [Gold Layer: UPT]              │ │
│  └─ Derived factors (urban score,           │ unified_pricing_table_live│ │
│     neighbourhood claim freq)                │ (50K–500K rows)        │ │
│                                               │                         │ │
│                                               └──┬───────────────────────┘ │
│                                                  │                         │
│  ┌──────────────────────────────────────────────┴─────────────────────┐  │
│  │ [Model Training Layer — 4 Core + 2 Motor Variants]                 │  │
│  ├─ freq_glm         ─────────────────────────────────────────────────┤  │
│  ├─ sev_glm          ─────→ [MLflow UC Registry] @champion            │  │
│  ├─ demand_gbm       ─────────────────────────────────────────────────┤  │
│  ├─ fraud_gbm                                                          │  │
│  ├─ freq_glm_motor   ─ (motor behavioural layer, distinct models)    │  │
│  └─ sev_glm_motor                                                      │  │
│                                                                         │  │
│  [Factory: 50-variant exploration]  ──→  [Governance Packs]           │  │
│  - feature banding                        PDFs per model version       │  │
│  - interaction terms           (elastic frontier)                      │  │
│  - family selection (Poisson/NB/Tweedie)   + sidecars                │  │
│  └─ candidates: factory_freq_glm_*, factory_sev_glm_*, ...           │  │
│                                                                         │  │
│  [Price Optimisation Module — Motor Only]                             │  │
│  ├─ Block 1: Motor data (quote/renewal, price-variant scenarios)     │  │
│  ├─ Block 2: Elasticity (conversion, retention, monotone LightGBM)   │  │
│  ├─ Block 3: Frontier simulation (3000-point grid, efficient set)    │  │
│  ├─ Block 4: Constrained solver (YAML-versioned constraints)         │  │
│  ├─ Block 5: Fairness & fair-value evidence screen                   │  │
│  ├─ Block 6: Immutable decision records                              │  │
│  ├─ Block 7: Monitoring (drift, deviation, corridor/GIPP breaches)  │  │
│  ├─ Block 8: Red-team panels (endogeneity, parameter recovery)       │  │
│  └─ Output: factors + monitor tables + agent decision loop            │  │
│                                                                         │  │
│  [Rating Engine Configuration]                                        │  │
│  ├─ Expense/commission loadings  ─────────────────────────────────────┤  │
│  ├─ Constraints & underwriting rules                                  │  │
│  └─ Regulatory config (caps, floors, fair-value corridors)           │  │
│                                                                         │  │
│  [Pricing Engine Releases]                                            │  │
│  ├─ release_id (monthly snapshots)                                    │  │
│  ├─ status: "champion" | "retired" | "backtest"                      │  │
│  ├─ model versions (freq/sev/demand/fraud GLM/GBM versions)          │  │
│  └─ rating engine version                                             │  │
│                                                                         │  │
│  [Serving Layer]                                                      │  │
│  ├─ pwg2_pricing_scorer (Model Serving endpoint)                      │  │
│  │  └─ rates quotes via 4 champion models in one round-trip          │  │
│  ├─ pwg2_motor_pricing_scorer (Model Serving endpoint)                │  │
│  │  └─ rates motor quotes (freq_glm_motor × sev_glm_motor)           │  │
│  ├─ pwg2_elasticity_scorer (optional, on-demand)                      │  │
│  │  └─ real-time price elasticity for optimisation app tab           │  │
│  ├─ pwg2_chat_agent (Agent Framework endpoint)                        │  │
│  │  └─ factory review + price explainability                          │  │
│  └─ pwg2_governance_agent (Agent Framework endpoint)                  │  │
│     └─ governance, bias, fairness, drift, regulatory narrative       │  │
│                                                                         │  │
│  [Quote Stream & Audit]                                               │  │
│  ├─ quote_payload_request (JSON: what was asked)                      │  │
│  ├─ quote_payload_rating_engine (JSON: what the engine returned)      │  │
│  ├─ quote_payload_response (JSON: what the user saw)                  │  │
│  ├─ audit_log (immutable, every event)                                │  │
│  └─ Served by quote_stream routes (/api/quote_stream/*)              │  │
│                                                                         │  │
│  [HITL Application — React Frontend + FastAPI Backend]                │  │
│  ├─ Frontend: 23 pages (Home, Datasets, Model Development, Pricing    │  │
│  │  Engine, Quote Review, Governance, Optimisation, Broker Chat, etc.)│  │
│  └─ Backend: 20+ route modules (pricing, factory, governance, etc.)   │  │
│                                                                         │  │
│  [MCP Server Surface] (10+ tools for external clients)                │  │
│  ├─ Pricing engine operations (opt_*, price_*, model_*)               │  │
│  ├─ Constraint authoring (opt_constraint_*)                           │  │
│  ├─ Agentic buyer (mcp_buyer_quote, mcp_buyer_bind)                  │  │
│  └─ Governance tools (query_*, log_event)                             │  │
│                                                                         │  │
└─────────────────────────────────────────────────────────────────────────────┘

```

**Data Flow:** External / internal data → Bronze/Silver/Gold UPT → Feature engineering → Model training → Champion selection/aliasing → Rating engine config seeding → Live endpoints + shadow pricing → Audit log & governance → Agents (explain/govern) → App (HITL review/optimize)

**Control Flow:** App routes → SQL queries via warehouse or Model Serving endpoints → MCP tools (external clients via agent framework) → Governance agents (Claude-backed) → Audit log → Regulatory export

---

## Capability Catalog

| **User-Facing Capability** | **What It Does** | **Backend Assets** | **Backing App Pages** |
|---|---|---|---|
| **Data Ingestion Hub** | Upload/approve external datasets (market rates, geospatial, credit bureau); track lineage + audit. | `datasets` routes (HITL approval), `external_landing` volume, `dataset_approvals` table, DLT expectations | `/datasets`, `/datasets/{dataset_id}` |
| **Feature Store** | View offline + online feature status; promote/pause features; browse per-feature provenance catalog. | `feature_store_live` table, `features` routes, feature-level UC lineage | `/feature-store` |
| **Model Development** | Notebook tracker; compare all model runs + hyperparameter variants; Gini lift per real UK factor. | `model_development` routes, MLflow runs, UC lineage, model versioning | `/model-development` |
| **Model Factory** | 50-spec leaderboard explorer; retrain shortlist; review governance PDFs per variant. | `factory_train` notebook, `factory_variants` + `factory_runs` tables, `factory` + `factory_real` routes | `/model-factory` |
| **Model Deployment** | Promote champion models to production; manage serving endpoint access; versioned releases. | `deployment` routes, MLflow aliases (`@champion`), Model Serving endpoints, `pricing_engine_releases` table | `/model-deployment` |
| **Quote Review** | Look up transaction by ID; replay quote JSON payloads; compare historical vs current scoring; AI analyst mode. | `quote_stream` routes, 3 quote-payload tables (`quote_payload_*`), `review` routes, Claude agent | `/quote-review` |
| **Pricing Engine** | See current champion release + all prior releases; compare releases family-by-family; export rate-book. | `pricing` routes, `pricing_engine_releases` table, Model Serving endpoint (`pwg2_pricing_scorer`), legacy batch jobs | `/pricing-engine` |
| **Price Optimisation (Motor)** | 7-tabbed control tower: Optimiser (efficient frontier + waterfall + factor table + approve/deploy HITL), Decisions (immutable records + committee-paper drafting), Demand & red-team (elasticity curves + parameter recovery), Monitoring (drift + corridor breaches + closed-loop), Aggregator squeeze (agentic reactive second act), Heavy mode (ensemble + stochastic), How it works (constraint YAML + MCP tools). | `optimisation` routes (20+ endpoints), 8+ optimisation_* tables, elasticity + solver notebooks, 7 agent personas on Agent Framework | `/pricing-optimisation` (7 tabs) |
| **Governance & Audit** | Immutable event log; data freshness; bias demographics; DQ monitoring; regulatory export; governance packs. | `governance` routes, `audit_log` table, `bias_demographics_live` table, governance PDFs in volume, `regulatory_export` function | `/governance` |
| **Live Serving** (optional) | Realtime quote scoring + 1M QPS load test via Model Serving endpoint + Lakebase online feature store. | `live_pricing` routes, Lakebase online store, `motor_provision`/`teardown` notebooks, load tester | `/pricing-engine` (live tab, if provisioned) |
| **Broker Chat** | Agentic distribution — end user asks pricing questions; MCP tools fetch quotes, bind policies, suggest alternatives. | `broker` routes, `distribution` routes, MCP `mcp_buyer_*` tools, Agent Framework | `/broker-chat` |
| **New Data Impact Study** | Standalone 6-notebook track: build enrichment → train standard vs enriched models → governance PDF → AI agent review. | `src/new_data_impact/` notebooks, `impact_*` derivative tables, governance agent | Entry: `/new-data-impact` (if link exposed) |
| **Genie Q&A** | Conversational natural-language queries over Modelling Mart + quote stream; resolve to SQL. | `genie` routes, Genie Space (workspace asset, must be created + wired), AI/BI Genie runtime | `/modelling-mart` (if Genie space ID set) |
| **Admin Panel** | Manage warehouse grants, pause/resume tables, reset demo state, inspect mcp/agent logs. | `admin` routes, grant jobs, teardown jobs, demo-reset notebook | `/admin` (restricted to workspace admins) |

---

## Layer-by-Layer Walkthrough

### Layer 00: Setup & Data Generation

**Notebooks:**
- `src/00_setup/setup.py` — Create schema, volume, audit_log, reference data (postcodes, SIC codes, regions). Generates synthetic policies (50K–500K per scale factor), claims, quotes.
- `src/00_setup/setup_quote_stream.py` — Build unified quotes table + 3 JSON payload tables (`quote_payload_request`, `quote_payload_rating_engine`, `quote_payload_response`).
- `src/00_setup/apply_metadata.py` — Tag tables with `pii`, `regulatory`, `lineage` tags.
- `src/00_setup/create_ai_assets.py` — Scaffold Genie spaces + Lakeview mart dashboard (workspace assets, created once).
- `src/00_setup/set_champion_aliases.py` — After training, set `@champion` aliases on model versions.
- `src/00_setup/grant_app_sp.py` — Grant app service principal (`CAN_MANAGE_RUN` on jobs, `CAN_USE` on warehouse).

**Generated Tables:**
- `policies` (50K–500K rows) — policy_id, inception_date, customer attributes, risk (turnover, building age, etc.), claims outcomes (5-year count, total_incurred)
- `claims` — policy_id, claim_date, incurred_amount, type
- `quotes` — quote_id, policy_id, quote_date, premium_quoted, converted (0/1)
- `quote_payload_request`, `quote_payload_rating_engine`, `quote_payload_response` — JSON blobs for transaction audit
- `audit_log` — (empty initially, populated by app)
- `postcode_enrichment` — Real UK 1.5M postcodes (ONSPD + IMD + ONS RUC + coastal flags)

**Resources:** `setup_job.yml`, `full_pipeline.yml` (orchestrator)

---

### Layer 01: Ingestion

**Notebooks:**
- `src/01_ingestion/ingest_market_pricing.py` — Load market-rate CSV → `1_bronze_market_pricing`
- `src/01_ingestion/ingest_geospatial_hazard.py` — Load hazard CSV → `1_bronze_geospatial_hazard`
- `src/01_ingestion/ingest_credit_bureau.py` — Load credit-score CSV → `1_bronze_credit_bureau`
- `src/01_ingestion/inject_data_variation.py` — Optional: perturb CSVs to simulate data quality issues

**Generated Tables (Bronze):**
- `1_bronze_market_pricing` — source, postcode, rate_by_risk_band
- `1_bronze_geospatial_hazard` — postcode, flood_zone_rating, subsidence_risk, proximity_to_fire_station_km, etc.
- `1_bronze_credit_bureau` — entity_id, credit_score, ccj_count, director_stability_score

**DLT Pipeline:** `src/02_silver/` (SQL files) applies DLT expectations + cleansing (nulls, casting, deduplication) → Silver tables:
- `2_silver_market_pricing`
- `2_silver_geospatial_hazard`
- `2_silver_credit_bureau`

**Resources:** `ingestion_pipeline.yml` (DLT definition)

---

### Layer 02: Silver Transformations

**SQL Notebooks:** Applied by DLT pipeline
- `silver_credit_bureau.sql` — Casting, null handling, dedup
- `silver_geospatial_hazard.sql` — Casting, null handling, dedup
- `silver_market_pricing.sql` — Casting, null handling, dedup

**Output:** `2_silver_*` tables (clean, typed, expectations-validated)

**Expectations:** DLT quality rules (e.g., nulls, value ranges) — failures logged to DLT expectations table.

**Resources:** `ingestion_pipeline.yml` (DLT job)

---

### Layer 03: Gold — Unified Pricing Table (UPT) & Feature Engineering

**Notebooks:**
- `src/03_gold/derive_factors.py` — Aggregate postcode-level factors (urban_score, neighbourhood_claim_frequency) from claims + postcode enrichment. Output: `postcode_factors`.
- `src/03_gold/build_upt.py` — LEFT JOIN policies + claims → features on postcode enrichment + derived factors + silver external data. Output: `unified_pricing_table` (version-snapshotted).
- `src/03_gold/build_feature_catalog.py` — Generate feature-level metadata (name, source table, transformation, owner, PII/regulatory flags). Output: `feature_catalog`.
- `src/03_gold/build_motor_upt.py` — Subset UPT for motor line (vehicle-specific columns).

**Generated Tables:**
- `postcode_factors` — postcode, urban_score, neighbourhood_claim_frequency, etc.
- `unified_pricing_table_live` — Policy-keyed (50K–500K rows), 20+ features:
  - Policy attributes: annual_turnover, sum_insured, building_age_years, current_premium
  - External (postcode-based): flood_zone_rating, proximity_to_fire_station_km, crime_theft_index, subsidence_risk, composite_location_risk, distance_to_coast_km, population_density_per_km2, elevation_metres, annual_rainfall_mm
  - Credit: credit_score, ccj_count, credit_default_probability, director_stability_score
  - Derived: market_median_rate, business_stability_score, years_trading, employee_count_est
  - Target: claim_count_5y, total_incurred_5y, fraud_flag, retained_next_year
- `feature_catalog` — feature_id, feature_name, source_table, transformation_logic, owner, pii_flag, regulatory_flag
- `motor_unified_pricing_table_live` — Motor subset (driver_age, vehicle_group, vehicle_value, annual_mileage, no_claims_years, etc.)

**Resources:** `upt_pipeline.yml`, `motor_upt.yml`

---

### Layer 04: Models & Model Factory

#### 04a: Core Champion Models

**Training Notebooks** (GLM via `statsmodels`, GBM via `lightgbm`):
- `src/04_models/model_01_glm_frequency.py` — Poisson GLM, target: claim_count_5y
- `src/04_models/model_02_glm_severity.py` — Gamma GLM, target: total_incurred_5y
- `src/04_models/model_03_gbm_demand.py` — LightGBM classifier, target: converted (0/1)
- `src/04_models/model_04_gbm_risk_uplift.py` — GBM regressor, target: risk_score (relative to freq_glm)
- `src/04_models/model_05_fraud_propensity.py` — GBM classifier, target: fraud_flag
- `src/04_models/model_06_retention.py` — GBM classifier, target: retained_next_year

**Registered in MLflow UC as:**
- `{fqn}.freq_glm` @champion
- `{fqn}.sev_glm` @champion
- `{fqn}.demand_gbm` @champion
- `{fqn}.fraud_gbm` @champion
- (+ @retired, @backtest versions)

#### 04b: Motor-Specific Champions

**Training Notebooks** (same algorithms, motor UPT):
- `src/04_models/production/freq_glm_motor.py` — Poisson GLM on motor features
- `src/04_models/production/sev_glm_motor.py` — Gamma GLM on motor features
- `src/04_models/production/demand_gbm_motor.py` — LightGBM conversion on motor + price elasticity features
- `src/04_models/production/fraud_gbm_motor.py` — LightGBM fraud on motor features

**Registered as:**
- `{fqn}.freq_glm_motor` @champion
- `{fqn}.sev_glm_motor` @champion
- `{fqn}.demand_gbm_motor` @champion
- `{fqn}.fraud_gbm_motor` @champion

#### 04c: Model Factory (Variant Exploration)

**Notebook:** `src/04_models/production/factory_train.py`
- Input: JSON plan (50 variant specs, each with: feature subset, interactions, banding strategy, family)
- For each variant:
  1. Apply banding (raw_linear, log_then_linear, quantile_5_bands, quantile_10_bands)
  2. Add pairwise interactions
  3. Fit GLM (Poisson, Quasi-Poisson, Negative Binomial, Tweedie)
  4. 5-fold CV for shortlist stability
  5. Log metrics to MLflow + `factory_variants` table
  6. Register as `factory_freq_glm_{variant_id}` (no @champion alias; demo only)

**Factory Tables:**
- `factory_runs` — run_id, family, plan_json (50 variant specs), status, created_at
- `factory_variants` — run_id, variant_id, config_json, metrics (train_gini, cv_gini_mean, cv_gini_std, etc.), status (shortlist / ranked / backtest)

**Resources:** `factory_train.yml`

#### 04d: Supplementary Models (Explored But Not Live)

- `src/04_models/model_03_gbm_demand.py` — Demand scoring (new business conversion probability)
- `src/04_models/model_04_gbm_risk_uplift.py` — Risk score relative to freq_glm
- (Registered in UC but not chained into pricing engine by default)

#### 04e: Model Lineage & Versioning

**MLflow Registry (UC-backed):**
- Every training run is logged with tags (`story`, `simulated`, `upt_delta_version`, etc.), params (features, train/test split), metrics (Gini, AIC, deviance explained)
- Aliases: `@champion` (live), `@retired` (previous champion), `@backtest` (exploration)
- UC lineage: Every model version links back to `unified_pricing_table_live` + training run metadata
- Delta versioning: Training capture UPT Delta version (enables point-in-time reproducibility)

**Governance Packs:** `src/04_models/production/governance_pack.py`
- Per-model-version PDF covering: what is it / who trained it / performance metrics / feature importance / stability over versions / known risks / regulatory responsibility / sign-off
- Output: uploaded to `{fqn}_packs/governance_packs/` volume, indexed in `governance_packs_index` table
- Triggered by: manual runs or orchestrated by `governance_pack.yml` for all 4 champions post-deploy

**Resources:** `production_training.yml`, `supplementary_models.yml`, `factory_train.yml`, `governance_pack.yml`

---

### Layer 05: Use Cases (Example Workflows)

**Notebooks:**
- `src/05_use_cases/uc1_shadow_pricing.py` — Score all policies with current + prior-month champion releases; compute premium delta and churn risk. Output: `shadow_pricing_results`, `shadow_pricing_churn_risk`.
- `src/05_use_cases/uc2_point_in_time.py` — Historical quote backtesting; rescore past quotes against historical model versions. Output: `uc2_point_in_time_backtest`, `uc2_comparison_metrics`.
- `src/05_use_cases/uc3_new_dataset.py` — Test impact of a new dataset on model performance (standard vs enriched feature sets). Output: `uc3_impact_metrics`.
- `src/05_use_cases/uc4_lineage_governance.py` — UC lineage traversal + governance checks. Output: `uc4_lineage_report`.
- `src/05_use_cases/uc5_enriched_pricing.py` — Compare commercial vs motor+enrichment pricing; measure Gini lift. Output: `uc5_enriched_comparison`.

**Resources:** `use_cases.yml`

---

### Layer 07: Serving & Live Endpoints

#### 07a: Model Serving Endpoints

**Provision Notebooks:**
- `src/07_serving/deploy_model_endpoint.py` — Deploy `pwg2_pricing_scorer` (bakes all 4 commercial champions + direct inlining of endpoint signature). One round-trip returns freq_glm + sev_glm + demand_gbm + fraud_gbm predictions.
- `src/07_serving/promote_model.py` — Promote a model version to @champion alias.
- `src/07_serving/test_endpoint.py` — Load-test the endpoint; measure latency.

**Live Pricing Tier** (optional, on-demand):
- `src/07_serving/live_pricing/motor_provision.py` — Stand up Lakebase online feature store + motor-specific scorer endpoint + QPS load tester.
- `src/07_serving/live_pricing/motor_teardown.py` — Tear down the online store + endpoint (scale-to-zero cost).
- `src/07_serving/live_pricing/04_realtime_feature_refresh.py` — Scheduled refresh of online store (e.g., credit score updates).
- `src/07_serving/live_pricing/03_load_test.py` — 1M QPS performance test.

#### 07b: Optimisation Elasticity Scorer (Optional)

- `src/07_serving/optimisation_elasticity_serve/provision.py` — Arm `pwg2_elasticity_scorer` (Model Serving endpoint wrapping the elasticity LightGBM models).
- `src/07_serving/optimisation_elasticity_serve/teardown.py` — Tear it down.

**Endpoint Names (DAB variables):**
- `pwg2_pricing_scorer` (commercial, live)
- `pwg2_motor_pricing_scorer` (motor, live)
- `pwg2_elasticity_scorer` (motor elasticity, on-demand)
- `pwg2_chat_agent` (Agent Framework, live)
- `pwg2_governance_agent` (Agent Framework, live)

**Resources:** `live_pricing.yml`, `motor_provision.yml`, `pricing_scorer.yml`, `motor_pricing_scorer.yml`, `optimisation.yml` (elasticity_serve_provision/teardown tasks)

---

### Layer 08: Governance, Audit & Compliance

**Notebooks:**
- `src/08_governance/regulatory_export.py` — Export pricing decisions + feature importance + model metadata in regulatory format (e.g., CRD IV Article 173, IFR compliance). Output: CSV/JSON in volume.

**Governance Packs:**
- `src/04_models/production/governance_pack.py` — PDF per model version (8–10 pages: overview, data lineage, performance metrics, stability, feature importance, limitations, regulatory statement, sign-off). Output: `governance_packs_index` table + PDF volume.

**Audit Log:**
- `audit_log` table (created in setup) — event_id, event_type, entity_type, entity_id, entity_version, user_id, timestamp, details (JSON), source (app/notebook/api)
- Populated by: app routes (every approve/reject/upload event logged), agents (governance_pack, explain price calls), batch jobs (model training, shadow pricing runs)
- **Immutable by design:** appends only, no updates/deletes (enforced at UC table level if possible)

**Bias & Demographics:**
- `src/04_models/production/bias_demographics_backfill.py` — Capture sensitive attributes (if proxy-available: postcode IMD quintile, age bands, etc.) per policy. Output: `bias_demographics_live` table.
- App governance routes query this to screen for disparate impact (e.g., Gini by quintile).

**UC Lineage:**
- Every model version links to `unified_pricing_table_live` (training input) + `quote_payload_*` (serving input)
- Every rating-engine release links to model versions + config table
- Feature catalog provides feature-level provenance

**Governance Agents:**
- `src/04_models/production/governance_agent.py` — Agent Framework endpoint (`pwg2_governance_agent`). Tools: query audit log, compute bias metrics, fetch model lineage, draft regulatory statements. Deployed as serving endpoint.

**Resources:** `governance_agent.yml`, `governance_pack.yml`, `bias_demographics_backfill.yml`, `regulatory_export.yml` (future)

---

### Layer 04–08: Price Optimisation Module (Motor, §3–§8)

**Overview:** Motor-specific offline optimization spine (data → elasticity → simulation → solve → monitor). Each block is its own job; all chain into `optimisation_full` orchestrator. British spelling (`optimisation_*`, not `opt_*`). Gated into Full Build by `enable_optimization` flag (DAB var).

#### Block 1: Motor Quote & Renewal Data (§3)

**Notebook:** `src/04_models/production/optimisation_motor_data.py`

**Inputs:**
- Motor UPT (freq_glm_motor technical premium via score, sev_glm_motor severity)
- Rating engine config (expense/commission loadings)
- Base elasticity parameters (base_conv_elasticity, base_ret_elasticity)
- Price variation (SD) + month simulation length

**Outputs:**
- `optimisation_quote_request` — New business request payload (driver age, vehicle group, sum insured, etc.)
- `optimisation_quote_response` — Quote response with vs_technical (price relative to risk), vs_market (vs competing rate), converted (0/1 bind outcome)
- `optimisation_renewal_response` — Renewal response with rate_change (renewal premium / prior premium), retained (0/1)
- `optimisation_portfolio_snapshot` — Monthly policy book snapshot for simulation
- `optimisation_redteam_endogeneity`, `optimisation_redteam_param_recovery` — Synthetic truth for red-teaming

**Gate:** `technical_source=champion` (inner-model load, rung c)

**Resource:** `optimisation.yml` task `optimisation_data`

#### Block 2: Elasticity Models (§4)

**Notebook:** `src/04_models/production/optimisation_elasticity.py`

**Elasticity Models:**
- **Conversion elasticity** (`conversion_elasticity_motor` LightGBM): P(bound) vs price.
  - Features: vs_technical, vs_market, driver_age, no_claims_years, annual_mileage, vehicle_value, vehicle_group, month_idx
  - **Monotone constraints:** [–1, –1, 0, 0, 0, 0, 0, 0] — conversion can only fall as price rises
  - Output: Binary classifier (bound=1, walked=0)
- **Retention elasticity** (`retention_elasticity_motor` LightGBM): P(retained) vs renewal rate change.
  - Features: rate_change, vs_technical, tenure_years, gipp_breach, month_idx
  - **Monotone constraints:** [–1, 0, 0, 0, 0] — retention can only fall as rate change rises
  - Output: Binary classifier (retained=1, lapsed=0)

**Panels (red-team):**
- `optimisation_redteam_endogeneity` — Demonstrates why raw price gives the wrong elasticity (price is endogenous to risk)
- `optimisation_redteam_param_recovery` — Synthetic-data parameter-recovery check; the pipeline recovers known-injected month-by-month elasticity

**Outputs:**
- `conversion_elasticity_motor` (UC model) @champion
- `retention_elasticity_motor` (UC model) @champion
- `optimisation_elasticity_curve` (table) — per-segment price→conversion curve
- Red-team tables (indexed by segment + month)

**Resource:** `optimisation.yml` task `optimisation_elasticity`

#### Block 3: Frontier Simulation (§5)

**Notebook:** `src/04_models/production/optimisation_simulation.py`

**Inputs:**
- Elasticity models (conversion + retention LGBMs)
- Motor portfolio snapshot
- Grid of 3000 candidate price-factor sets (exploring {−20%, −10%, 0%, +5%, +10%, ...} per segment)

**Simulation Logic:**
- For each candidate factor set:
  1. Price each policy: technical_premium × factor_matrix
  2. Load elasticity model; predict conversion prob (new business) + retention prob (renewals)
  3. Aggregate: total GWP, total commission, surrender loss, margin contribution
  4. Mark as **feasible** if within corridor constraint (e.g., GWP ≥ 85% of current)

**Outputs:**
- `optimisation_simulation_results` — 3000 candidate scenarios with {factors, GWP, commission, margin, feasible}
- Efficient frontier extraction (Pareto set: candidates that dominate all others on GWP vs margin)

**Resource:** `optimisation.yml` task `optimisation_simulation`, param: grid_points (default 3000), corridor_pct (default 15%)

#### Block 4: Constrained Solver (§6)

**Notebook:** `src/04_models/production/optimisation_solver.py`

**Inputs:**
- Simulation results (3000 scenarios)
- Versioned constraint YAML (e.g., `constraints_v1.yaml`):
  ```yaml
  objective: "maximize_margin"         # or maximize_gwp / maximize_retention
  portfolio_floor_pct: 0.85            # must keep ≥85% of current GWP
  segment_rules:                       # per-segment caps/floors
    - segment: "U25 · grpHigh"
      min_factor: 0.8
      max_factor: 1.3
  fairness_constraints:
    - dimension: "age_band"
      max_disparity: 0.15              # no segment can change >15%
  ```

**Solver Logic:**
- Cast as constrained arg-max: find the candidate factor set that maximizes the objective (margin, GWP, or retention) subject to portfolio/segment/fairness constraints
- All constraints are **versioned in git** (enables audit trail of policy changes)

**Outputs:**
- `optimisation_solution` — Chosen factor set (one row: {factors, objective_value, segments_affected, compliance_report})
- `optimisation_factor_table` — Per-segment factors extracted from solution
- Constraint compliance report (audit trail: which constraints were binding)

**Resource:** `optimisation.yml` task `optimisation_solver`, params: constraint_version (default v1), objective (blank = use YAML)

#### Block 4b: Renewal Solver (GIPP-Enforced) (§6)

**Notebook:** `src/04_models/production/optimisation_renewal_solver.py`

**Variant:** Solver for renewal line, with solve-time GIPP constraint (Good Insurance Practice — bound premium increase within a % of prior).

**Outputs:**
- `optimisation_renewal_solution` — Factor set for renewals, honoring GIPP ceiling

**Resource:** `optimisation.yml` task `optimisation_renewal_solver`

#### Block 5: Fairness & Fair-Value Evidence (§11)

**Notebook:** `src/04_models/production/optimisation_fairness.py`

**Inputs:**
- Solved factor set
- Portfolio snapshot (segmented by demographics proxy: age, vehicle group, postcode IMD quintile, etc.)

**Checks:**
1. **Disparate impact screening:** per-protected-class segment, compute avg premium change. Flag if any segment diverges >10% from portfolio mean.
2. **Fair-value evidence:** for each segment, show:
   - Prior premium (prior release)
   - Technical premium (risk-only, no optimization)
   - Optimized premium (solved factors applied)
   - Rationale: "optimized premium reflects risk + demand elasticity + portfolio constraints"
3. **Regulatory narrative:** draft GIPP/CRD IV Article 173 compliance statement

**Outputs:**
- `optimisation_fairness_report` (table) — segment, metrics (avg_prior, avg_technical, avg_optimized, disparity_pct, is_outlier)
- Narrative JSON (used by governance agent)

**Resource:** `optimisation.yml` task `optimisation_fairness`

#### Block 6: Immutable Decision Records (§11)

**Notebook:** `src/04_models/production/optimisation_decision_record.py`

**Purpose:** Create immutable, auditable record of every pricing decision.

**Outputs:**
- `optimisation_decision_records` (table, append-only):
  - decision_id (UUID)
  - decision_date (timestamp)
  - decision_type (e.g., "price_optimization_solve_new_business", "price_optimization_renewal_solver", "manual_override")
  - constraint_version
  - objective
  - solved_factors (JSON: segment → factor)
  - fairness_report (JSON: segment → disparity metrics)
  - approved_by (user_id, initially NULL; set by HITL approval route)
  - approval_timestamp
  - narrative (markdown; used for committee papers)

**Resource:** `optimisation.yml` task `optimisation_decision_record`

#### Block 7: Explain-This-Price UC Function (§11)

**Notebook:** `src/04_models/production/optimisation_explain_price.py`

**Purpose:** Create UC function callable from app or SQL to explain any premium.

**Function:** `optimisation_explain_price(quote_id)` → JSON:
```json
{
  "quote_id": "...",
  "technical_premium": 1000,
  "risk_factors": {"frequency": 0.95, "severity": 1.05, ...},
  "elasticity_effects": {"conversion_prob": 0.42, "vs_market_ratio": 1.02, ...},
  "segment": "25-70 · grpMid",
  "solved_factor": 1.08,
  "final_premium": 1080,
  "rationale": "Risk-adjusted premium (technical) scaled by demand elasticity under portfolio constraints; segment 25-70 · grpMid constrained to +8% per fairness guardrails."
}
```

**Resource:** `optimisation.yml` task `optimisation_explain_price`

#### Block 8: Monitoring (§7)

**Notebook:** `src/04_models/production/optimisation_monitoring.py`

**Inputs:**
- Solved factor set (Block 4 output)
- Actual quote stream (from Block 1 simulation + real quotes if deployed)

**Monitoring Checks:**
1. **Elasticity drift:** Are actual conversion/retention rates matching model predictions?
2. **Premium deviation:** Are actual premiums matching the solved factor table + rating engine logic?
3. **Corridor breaches:** Is GWP still within portfolio floor?
4. **GIPP breaches:** Are renewal rate changes exceeding the ceiling?
5. **Fair-value evidence erosion:** Have fairness metrics drifted?

**Outputs:**
- `optimisation_monitoring_results` (table) — per-month, per-segment: {elasticity_actual, elasticity_predicted, deviation_pct, corridor_status, gipp_status, fairness_status}
- Red/amber/green dashboard-ready flags

**Resource:** `optimisation.yml` task `optimisation_monitoring`, param: corridor_pct (default 15%)

#### Block 7b: Advance Month / Closed-Loop (§3 tail)

**Notebook:** `src/04_models/production/optimisation_advance_month.py`

**Purpose:** Simulate one month of business under the deployed prices; feed back into Block 1 for next iteration.

**Logic:**
1. Take the solved factor set + monitoring results from prior month
2. Simulate month N+1 with month N's factors applied + observed elasticity
3. Feed into Block 1 for next run (closed-loop feedback)

**Output:** `optimisation_portfolio_snapshot_month_n+1`

**Resource:** `optimisation.yml` task `optimisation_advance_month`

#### Block 11a: Heavy Mode (Optional, On-Demand)

**Notebook:** `src/04_models/production/optimisation_heavy_mode.py`

**Purpose:** Ensemble disagreement map + exhaustive per-policy stochastic run (big hammer; measures real compute cost).

**Inputs:**
- All elasticity models (conversion, retention, freq, sev)
- Portfolio snapshot

**Process:**
1. For each policy, run Monte-Carlo (N iterations) of: sample elasticity model predictions from their distributions
2. For each sampled realization, apply the solved factors + rating engine logic → generate premium
3. Output: per-policy premium distribution (mean, median, 5th/95th percentiles)
4. Ensemble disagreement: are the elasticity models agreeing? Flag outliers.

**Output:** `optimisation_heavy_mode_results` — per-policy ensemble metrics

**Resource:** `optimisation.yml` task `optimisation_heavy_mode` (defined but dormant; never in full_build)

#### Orchestrator: `optimisation_full`

**DAG:**
```
data
 ├─ elasticity (depends: data)
 ├─ simulation (depends: elasticity)
 ├─ solver (depends: elasticity)
 ├─ monitoring (depends: elasticity)
 ├─ renewal_solver (depends: elasticity)
 ├─ fairness (depends: solver)
 ├─ decision_record (depends: fairness)
 └─ explain_price (depends: decision_record)
 └─ advance_month (optional tail)
```

**Integration with Full Build:**
- If `enable_optimization=true`, `full_build` chains `optimisation_full` after motor_train task
- If `enable_optimization=false` (default), `optimisation_*` jobs remain defined but dormant; run on demand via `databricks bundle run optimisation_full`

**Resource:** `optimisation.yml` (all tasks)

---

### Layer: App — HITL Frontend + FastAPI Backend

#### Frontend Pages (23 in `/src/app/frontend/src/pages/`)

| **Page** | **Route** | **Purpose** | **Key Interactions** |
|---|---|---|---|
| **Home** | `/` | Landing page, overview KPIs, 3 pillars, agent lead | Fetch `/api/overview`, 9Ask-the-Book agent|
| **Learn** | `/learn` | Tutorial / onboarding walkthrough | Static content + interactive examples |
| **Datasets** | `/datasets` | List external datasets with approval status | Fetch `/api/datasets`, approve/reject via HITL modal |
| **DatasetDetail** | `/datasets/:datasetId` | Lineage, quality metrics, approval history | Fetch `/api/datasets/:id`, audit log |
| **FeatureStore** | `/feature-store` | Offline + online feature status, promotion | GET `/api/features`, POST `/api/features/promote` |
| **ModelDevelopment** | `/model-development` | MLflow runs, hyperparameter comparison | Fetch `/api/development/runs`, Gini lift table |
| **ModelFactory** | `/model-factory` | 50-variant leaderboard, shortlist, PDFs | GET `/api/factory/runs`, POST `/api/factory/train` |
| **ModelDeployment** | `/model-deployment` | Champion promotion, versioned releases | GET `/api/deployment/models`, POST `/api/deployment/promote` |
| **QuoteReview** | `/quote-review` | Transaction lookup, JSON payload replay, AI analyst | POST `/api/review/lookup`, call agent |
| **QuoteTester** | `/quote-tester` | Generate test quotes, score in real-time | POST `/api/pricing/score-quote` |
| **CompareTest** | `/compare-test` | Multi-release quote comparison (batch) | POST `/api/compare/compare-release` |
| **PricingEngine** | `/pricing-engine` | Current release, prior releases, export rate-book | GET `/api/pricing/releases`, `/api/pricing/releases/current` |
| **RatingEngineIntegration** | `/rating-engine-integration` | Rating config (expense/commission), underwriting rules | GET `/api/deployment/rating-config` |
| **PriceOptimisation** | `/pricing-optimisation` | 7-tab motor optimiser (Optimiser, Decisions, Demand, Monitoring, Aggregator, Heavy, How-It-Works) | POST `/api/optimisation/*` (20+ endpoints) |
| **Supervisor** | `/supervisor` | Approve/reject decisions from optimizer | GET `/api/supervisor/decisions`, POST `/api/supervisor/approve` |
| **Governance** | `/governance` | Audit log, DQ, bias, regulatory export | GET `/api/governance/audit`, `/api/governance/bias` |
| **BlackBox** | `/black-box` | Model explainability (SHAP, feature importance, simulator) | GET `/api/development/model-explainability` |
| **Addons** | `/addons` | Optional feature toggles (live serving, elasticity scorer) | POST `/api/admin/provision-live-serving` |
| **BrokerChat** | `/broker-chat` | Agentic distribution (end-user quote interaction) | WebSocket `/ws/broker-chat`, MCP tools |
| **AgenticDistribution** | `/agentic-distribution` | Configuration UI for broker-chat personas | GET `/api/distribution/personas` |
| **ReviewPromote** | `/review-promote` | HITL approval panel before releasing factors | GET `/api/optimisation/pending-decisions`, POST `/api/optimisation/approve` |
| **NewDataImpact** | `/new-data-impact` | Link to /src/new_data_impact/ notebooks | Standalone 6-notebook study |
| **Genie (Modelling Mart)** | `/modelling-mart` (if genie_space_id set) | AI/BI Q&A over UPT + quote stream | Genie Space runtime |

#### Backend Routes (20+ modules, ~11K LOC in `/src/app/server/routes/`)

| **Module** | **Routes** | **Purpose** | **Backing Tables/Endpoints** |
|---|---|---|---|
| **`overview.py`** | `GET /api/overview` | Return KPIs (live release, policies, GWP, DQ state, governance event count) | `pricing_engine_releases` (status=champion), policies, `audit_log` |
| **`datasets.py`** (1243 LOC) | `GET /api/datasets`, `POST /api/datasets/approve` | HITL approval flow for external CSVs; DQ expectations | `dataset_approvals` table, ingestion_pipeline job trigger |
| **`features.py`** | `GET /api/features`, `POST /api/features/promote`, `POST /api/features/pause` | Feature store status (offline: Delta, online: Lakebase if provisioned) | Feature Lookup table, Lakebase integration |
| **`development.py`** | `GET /api/development/runs`, `GET /api/development/model-explainability` | MLflow runs, SHAP explainability, feature importance per model | MLflow API, UC lineage |
| **`factory.py`** (730 LOC) | `POST /api/factory/train`, `GET /api/factory/runs/:id`, `GET /api/factory/leaderboard`, `POST /api/factory/chat` | Factory orchestration + variant leaderboard + factory-persona agent | `factory_runs`, `factory_variants`, pricing_chat_agent endpoint |
| **`factory_real.py`** (424 LOC) | `POST /api/factory-real/train-real`, `GET /api/factory-real/leaderboard`, `POST /api/factory-real/chat` | Real (non-simulated) factory training + real-factory-persona agent | Same as factory.py but calls factory_train notebook (real training, not synthetic) |
| **`deployment.py`** | `GET /api/deployment/models`, `POST /api/deployment/promote`, `GET /api/deployment/rating-config` | Model promotion to @champion, versioned rating config | MLflow UC registry, `rating_engine_config` table |
| **`review.py`** | `POST /api/review/lookup`, `POST /api/review/replay`, `POST /api/review/regenerate-score` | Quote transaction lookup, payload replay, simulate new score | `quote_payload_*` tables, Model Serving endpoints |
| **`compare.py`** | `POST /api/compare/compare-release` | Compare two pricing releases family-by-family (batch job via historical_quote_score) | `pricing_engine_releases`, historical scoring job |
| **`pricing.py`** (1066 LOC) | `GET /api/pricing/releases`, `GET /api/pricing/releases/{id}`, `GET /api/pricing/releases/current`, `POST /api/pricing/score-quote` | Versioned rate-book, current champion release, live scoring | `pricing_engine_releases` table, `pwg2_pricing_scorer` endpoint, `pwg2_motor_pricing_scorer` |
| **`quote_stream.py`** | `GET /api/quote_stream/quotes`, `GET /api/quote_stream/aggregates`, `POST /api/quote_stream/patterns` | Quote analytics, per-segment aggregates, pattern discovery | `quote_payload_*` tables, Genie integration |
| **`governance.py`** (1299 LOC) | `GET /api/governance/audit`, `GET /api/governance/bias`, `GET /api/governance/lineage`, `POST /api/governance/export` | Immutable audit log, bias demographics screening, UC lineage, regulatory export | `audit_log`, `bias_demographics_live`, UC Catalog API, `governance_packs_index` |
| **`agent.py`** | `POST /api/agent/explain` | Call pricing_chat_agent with explain persona (explainability for any premium) | `pwg2_chat_agent` endpoint |
| **`broker.py`** (340 LOC) | `POST /api/broker/quote`, `POST /api/broker/bind`, `POST /api/broker/alternatives` | End-user broker chat (agentic distribution) | MCP tools (mcp_buyer_quote, mcp_buyer_bind, etc.) |
| **`distribution.py`** | `GET /api/distribution/personas`, `POST /api/distribution/config` | Broker-chat persona configuration | `distribution_config` table |
| **`optimisation.py`** (581 LOC) | 20+ endpoints: `GET /api/optimisation/frontier`, `POST /api/optimisation/simulate`, `POST /api/optimisation/solve`, `GET /api/optimisation/pending-decisions`, `POST /api/optimisation/approve`, etc. | Full optimizer UI: frontier, waterfall, factor table, decision approval, monitoring, etc. | `optimisation_*` tables, elasticity models, Agent Framework tools |
| **`supervisor.py`** | `GET /api/supervisor/decisions`, `POST /api/supervisor/approve` | HITL approval gate before deploy (decision records) | `optimisation_decision_records` |
| **`genie.py`** | `POST /api/genie/ask` | Forward Q&A to Genie Space (workspace asset) | Genie Space API |
| **`live_pricing.py`** (1087 LOC) | `POST /api/live_pricing/provision`, `POST /api/live_pricing/teardown`, `POST /api/live_pricing/load-test` | Provision/tear down Lakebase online store + QPS tester | Lakebase SDK, online_store_name variable |
| **`admin.py`** | `POST /api/admin/pause-table`, `POST /api/admin/warehouse-grant`, `POST /api/admin/demo-reset` | Admin operations (table pause, warehouse grants, reset) | Workspace API, SQL warehouse |

#### App Service Principal & Authentication

- **App SP:** Created by `databricks apps create pricing-workbench-gen2` → mints `app_service_principal_id` (UUID)
- **Grants:** `grant_app_sp.py` job grants:
  - `CAN_MANAGE_RUN` on all jobs (so app can trigger model training, scoring, etc.)
  - `CAN_USE` on SQL warehouse (for route query execution)
  - `CAN_RUN` on Model Serving endpoints (live scoring)
- **End-user forwarding:** App middleware captures `x-forwarded-email` / `x-forwarded-preferred-username` headers (Databricks Apps passes the signed-in user); audit log attributes events to the real person, not the app SP
- **Agent tokens:** `pricing_chat_agent.py` + `governance_agent.py` self-provision a 90-day PAT on deploy (if PATs enabled; fallback: inject `AGENT_TOKEN` / `AGENT_HOST` env vars)

#### Asset Inventory Within App

| **Asset Type** | **Count** | **Examples** |
|---|---|---|
| **Frontend Pages** | 23 | Home, Datasets, Model Development, Pricing Engine, Price Optimisation, Governance, etc. |
| **Server Routes** | 20+ modules | overview, datasets, features, development, factory, pricing, optimisation, governance, broker, etc. |
| **API Endpoints** | ~100+ | GET/POST across all route modules |
| **Model Serving Endpoints** | 5 | pwg2_pricing_scorer, pwg2_motor_pricing_scorer, pwg2_elasticity_scorer, pwg2_chat_agent, pwg2_governance_agent |
| **UC Functions** | 5+ | optimisation_explain_price, regulatory_export, etc. |
| **Agent Framework Personas** | 7 | factory (chat), factory-real (chat), explain (explain price), governance, fairness, planner, recommender |

**Resources:** `app.yml` (DAB resource), `src/app/` frontend + server code

---

## Asset Inventory

### UC Tables (51 total)

#### Foundation & Reference
- `audit_log` — Immutable event trail (event_id, event_type, entity_type, user_id, timestamp, details JSON)
- `policies` — Core dataset (policy_id, customer, risk attributes, claim outcomes 5-year)
- `claims` — Claim events (policy_id, claim_date, incurred_amount, type)
- `quotes` — Quote stream (quote_id, policy_id, quote_date, premium_quoted, converted)
- `quote_payload_request`, `quote_payload_rating_engine`, `quote_payload_response` — JSON payloads per quote (serving audit)
- `postcode_enrichment` — Real UK 1.5M postcodes (ONSPD + IMD + ONS RUC + coastal flags)
- `postcode_factors` — Derived per-postcode aggregates (urban_score, neighbourhood_claim_frequency)

#### Bronze (External Data)
- `1_bronze_market_pricing` — Market rates CSV
- `1_bronze_geospatial_hazard` — Hazard CSV
- `1_bronze_credit_bureau` — Credit score CSV

#### Silver (Transformed)
- `2_silver_market_pricing` — Validated, typed market rates
- `2_silver_geospatial_hazard` — Validated hazard data
- `2_silver_credit_bureau` — Validated credit data

#### Gold (Feature Layer)
- `unified_pricing_table_live` — Policy-keyed UPT (50K–500K rows, 20+ features, Delta-versioned)
- `motor_unified_pricing_table_live` — Motor subset (vehicle-specific columns)
- `feature_catalog` — Per-feature metadata (name, source, transformation, owner, PII/regulatory)
- `shadow_pricing_results` — Prior-month vs current-month champion premium delta
- `shadow_pricing_churn_risk` — Churn risk per policy if premium increases
- `bias_demographics_live` — Sensitive attributes (postcode IMD quintile, age bands, proxy demographics)

#### Model Registry (UC)
- `freq_glm` (v1, v2, ...) @champion @retired — Poisson GLM, claim frequency
- `sev_glm` (v1, v2, ...) @champion @retired — Gamma GLM, claim severity
- `demand_gbm` (v1, v2, ...) @champion @retired — LightGBM, new-business conversion
- `fraud_gbm` (v1, v2, ...) @champion @retired — LightGBM, fraud propensity
- `freq_glm_motor` (v1, ...) @champion — Poisson GLM, motor-specific
- `sev_glm_motor` (v1, ...) @champion — Gamma GLM, motor-specific
- `demand_gbm_motor` (v1, ...) @champion — LightGBM, motor new-business
- `fraud_gbm_motor` (v1, ...) @champion — LightGBM, motor fraud
- `factory_freq_glm_A01`, `factory_freq_glm_A02`, ... — Factory variant candidates (no @champion)
- (+ retention, risk_uplift models)

#### Factory Tracking
- `factory_runs` — run_id, family, plan_json (50 variant specs), status, created_at
- `factory_variants` — run_id, variant_id, config_json, metrics (train_gini, cv_gini_mean/std), status

#### Rating Engine Config
- `rating_engine_config` — Versioned rating parameters (expense loadings, commission %, underwriting rules, constraints)
- `pricing_engine_releases` — release_id, display_name, effective_date, status (champion/retired/backtest), freq/sev/demand/fraud_glm versions, rating_engine_version, approved_by, narrative

#### Use Cases
- `uc2_point_in_time_backtest` — Historical quote backtest results
- `uc2_comparison_metrics` — Prior vs current model performance
- `uc3_impact_metrics` — Standard vs enriched feature impact
- `uc4_lineage_report` — UC lineage traversal results
- `uc5_enriched_comparison` — Commercial vs motor+enrichment comparison

#### Price Optimisation (Motor) — 15 tables
- `optimisation_quote_request` — New-business pricing requests
- `optimisation_quote_response` — Quote responses (with vs_technical, vs_market, converted)
- `optimisation_renewal_response` — Renewal responses (with rate_change, retained)
- `optimisation_portfolio_snapshot_month_N` — Portfolio snapshot per month
- `optimisation_simulation_results` — 3000 candidate factor scenarios
- `optimisation_solution` — Chosen factor set (Block 4 output)
- `optimisation_factor_table` — Per-segment factors extracted from solution
- `optimisation_renewal_solution` — Renewal-specific factor set (GIPP-enforced)
- `optimisation_fairness_report` — Segment-level fairness metrics
- `optimisation_decision_records` — Immutable decision audit trail
- `optimisation_elasticity_curve` — Per-segment price→conversion curve
- `optimisation_monitoring_results` — Monthly monitoring: drift, deviation, breaches
- `optimisation_redteam_endogeneity` — Red-team: endogeneity check (synthetic truth)
- `optimisation_redteam_param_recovery` — Red-team: parameter recovery validation

#### Governance & Approvals
- `dataset_approvals` — Dataset approval history (dataset_id, status, approved_by, timestamp)
- `governance_packs_index` — Index of governance PDFs (model_family, version, pack_id, pack_url, created_at)
- `supporting_tables` — Internal reference data (e.g., geographic lookups, SIC codes)

#### Supporting
- `inference_backfill` — Historical model scores for all policies (used for shadow pricing, bias analysis)
- `new_data_impact_*` — Derivative tables from 6-notebook study (impact_standard_vs_enriched, etc.)

### UC Models (MLflow Registry) — 12–20 total

**Commercial Line:**
- `freq_glm` — Poisson GLM (claim frequency)
- `sev_glm` — Gamma GLM (claim severity)
- `demand_gbm` — LightGBM (new-business conversion)
- `fraud_gbm` — LightGBM (fraud propensity)
- + retired/backtest versions

**Motor Line:**
- `freq_glm_motor` — Poisson GLM (motor frequency)
- `sev_glm_motor` — Gamma GLM (motor severity)
- `demand_gbm_motor` — LightGBM (motor conversion, elasticity features)
- `fraud_gbm_motor` — LightGBM (motor fraud)

**Elasticity (Motor):**
- `conversion_elasticity_motor` — LightGBM classifier (price elasticity, monotone)
- `retention_elasticity_motor` — LightGBM classifier (renewal elasticity, monotone)

**Factory Variants (Per Run):**
- `factory_freq_glm_A01`, `factory_freq_glm_A02`, ..., `factory_freq_glm_Z50` — One per variant spec in the plan

### UC Functions (SQL/Python)

- `optimisation_explain_price(quote_id)` — Return JSON: technical premium, elasticity effects, segment, solved factor, final premium, rationale

### Model Serving Endpoints

- `pwg2_pricing_scorer` — Commercial rating engine (all 4 champions in one call)
- `pwg2_motor_pricing_scorer` — Motor rating engine (freq_glm_motor × sev_glm_motor)
- `pwg2_elasticity_scorer` — Motor elasticity (optional, on-demand)

### Agent Framework Endpoints

- `pwg2_chat_agent` — Factory review + price explainability (persona selection)
- `pwg2_governance_agent` — Governance, bias, fairness, regulatory narrative

### Jobs (37 total, in DAB)

#### Setup & Foundation
- `setup_demo` — Create schema, volume, audit_log, policies, claims, quotes, reference data
- `setup_quote_stream` — Build unified quotes + payload tables
- `setup_motor` — Create motor-specific policies dataset
- `build_postcode_enrichment` — Generate real 1.5M UK postcode enrichment

#### Ingestion & Silver
- `ingest_external_data` — DLT pipeline: bronze → silver for market, geospatial, credit
- `ingest_market_pricing`, `ingest_geospatial_hazard`, `ingest_credit_bureau` — Individual Bronze jobs

#### Gold & Feature Engineering
- `build_upt` — Join policies + claims + postcode enrichment → UPT
- `build_motor_upt` — Build motor UPT subset
- `build_feature_catalog` — Generate feature-level metadata

#### Model Training
- `production_training` — Train 4 core champions (freq, sev, demand, fraud GLMs/GBMs)
- `train_motor_models` — Train 4 motor champions (freq, sev, demand, fraud)
- `factory_train` — Run factory: 50-variant exploration
- `supplementary_models` — Optional: train retention, uplift models

#### Model Deployment & Configuration
- `set_champion_aliases` — Set @champion aliases on trained models
- `pricing_scorer_deploy` — Deploy pwg2_pricing_scorer endpoint
- `motor_pricing_scorer_deploy` — Deploy pwg2_motor_pricing_scorer endpoint
- `rating_engine_seed` — Seed pricing_engine_config + rating params
- `pricing_engine_releases_seed` — Seed first pricing_engine_releases row
- `inference_backfill` — Score all policies with champion models (for shadow pricing, bias)
- `bias_demographics_backfill` — Capture sensitive attributes per policy

#### Use Cases
- `uc1_shadow_pricing` — Score all policies with prior + current champions
- `uc2_point_in_time` — Historical quote backtesting
- `uc3_new_dataset` — Impact of new dataset on model performance
- `uc4_lineage_governance` — UC lineage traversal
- `uc5_enriched_pricing` — Standard vs enriched feature comparison

#### Governance & Agents
- `governance_pack` — Generate PDF for a single model version (4 tasks, one per champion family)
- `governance_agent_deploy` — Deploy pwg2_governance_agent endpoint
- `pricing_chat_agent_deploy` — Deploy pwg2_chat_agent endpoint
- `generate_governance_packs` — Orchestrator: generate packs for all 4 champions + motor variants

#### Optional Live Serving Tier
- `live_pricing_provision` — Stand up Lakebase online store + scorer
- `live_pricing_teardown` — Tear down online store + scorer
- `motor_provision` — Motor-specific live provisioning
- `motor_teardown` — Motor-specific teardown

#### Price Optimisation (Motor, §3–§8)
- `optimisation_data` — Block 1: motor quote/renewal data
- `optimisation_elasticity` — Block 2: elasticity models
- `optimisation_simulation` — Block 3: frontier simulation
- `optimisation_solver` — Block 4: constrained solver
- `optimisation_renewal_solver` — Block 4b: renewal solver (GIPP)
- `optimisation_fairness` — Block 5: fairness screening
- `optimisation_decision_record` — Block 6: decision records
- `optimisation_explain_price` — Block 7: explain-price function
- `optimisation_monitoring` — Block 8: monitoring
- `optimisation_advance_month` — Closed-loop advance
- `optimisation_heavy_mode` — Heavy mode (ensemble, stochastic)
- `optimisation_elasticity_serve_provision` — Arm elasticity scorer (optional)
- `optimisation_elasticity_serve_teardown` — Tear down elasticity scorer
- `optimisation_full` — Orchestrator: data → elasticity → simulation → solve → monitor

#### Orchestrators
- `full_build` — Master orchestrator: everything from scratch (data → UPT → training → agents → metadata)
- `full_pipeline` — Legacy: runs full_build + full_demo
- `run_full_demo` — Runs full_pipeline

#### Utilities
- `apply_metadata` — Tag tables with PII, regulatory, lineage flags
- `apply_tags` — Tag champion models with governance info
- `grant_app_sp` — Grant app service principal permissions
- `ensure_supporting_tables` — Ensure internal reference tables exist
- `demo_reset` — Reset demo to initial state (idempotent)
- `create_ai_assets` — Create Genie spaces + Lakeview dashboard
- `compare_scoring` — Historical quote comparison (batch)
- `historical_quote_score` — Score any historical release on any quote

### Volumes

- `external_landing` — Landing zone for external CSV files (ingestion stage)
- `governance_packs` — Storage for governance PDFs

### MCP Tools Surface (10+, for external agents/clients)

**Pricing Operations:**
- `opt_get_current_solution` — Fetch current solved factors
- `opt_get_frontier` — Fetch efficient frontier
- `opt_get_monitoring` — Fetch monitoring metrics
- `price_quote(motor_attributes)` — Score a single quote
- `model_get_champion_version` — Fetch current champion version for a family

**Constraint Authoring:**
- `opt_constraint_set_yaml(constraint_version, yaml_content)` — Update constraint YAML
- `opt_constraint_validate(yaml_content)` — Validate constraint YAML without deploying

**Agentic Buyer (If Insurance use case):**
- `mcp_buyer_quote(customer_attrs)` — Get a quote
- `mcp_buyer_bind(quote_id)` — Bind the quote (move quote → policy)
- `mcp_buyer_suggest_alternatives(quote_id)` — Suggest alternative pricing

**Governance:**
- `query_audit_log(event_type, days_back)` — Query audit log
- `log_event(event_type, entity_type, entity_id, details)` — Append audit event
- `query_bias_metrics(segment_dimension)` — Fetch bias screening results

---

## Data & Control Flow / Lineage

### End-to-End Quote-to-Price Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. QUOTE REQUEST (via app /api/pricing/score-quote or MCP tools)   │
│    ├─ Customer attributes (driver age, vehicle, turnover, etc.)   │
│    └─ Captured in audit_log (event_type: "quote_requested")       │
└────────────────────┬──────────────────────────────────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │  Route → quote_stream.py route  │
        │  ┌─────────────────────────────┤
        │  │ 1. Enrich with postcode     │
        │  │    (postcode_enrichment     │
        │  │     + postcode_factors)     │
        │  │ 2. Fetch external features  │
        │  │    (2_silver_market_pricing │
        │  │     2_silver_geospatial     │
        │  │     2_silver_credit_bureau) │
        │  └─────────────────────────────┤
        │     → Prepare feature vector   │
        │        (matches UPT schema)    │
        └────────────┬──────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │   Model Serving Endpoint        │
        │   pwg2_pricing_scorer           │
        │  ┌─────────────────────────────┤
        │  │ Loads 4 champion models:    │
        │  │  - freq_glm @champion       │
        │  │  - sev_glm @champion        │
        │  │  - demand_gbm @champion     │
        │  │  - fraud_gbm @champion      │
        │  │                             │
        │  │ Inference: returns          │
        │  │  {frequency, severity,      │
        │  │   conversion_prob,          │
        │  │   fraud_prob}               │
        │  └─────────────────────────────┤
        │  All in one round-trip         │
        └────────────┬──────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │   pricing.py route              │
        │   (/api/pricing/score-quote)    │
        │  ┌─────────────────────────────┤
        │  │ Apply rating engine logic:  │
        │  │  1. Technical premium:      │
        │  │     annual_turnover × freq  │
        │  │     × sev × base_rate       │
        │  │  2. Demand adjustment:      │
        │  │     technical × (1 +        │
        │  │     demand_adjustment%)     │
        │  │  3. Fraud surcharge:        │
        │  │     + fraud_prob × 500      │
        │  │  4. Rating engine rules:    │
        │  │     apply caps, floors,     │
        │  │     geographic rules, etc.  │
        │  │  5. Final premium           │
        │  └─────────────────────────────┤
        │  Uses: rating_engine_config    │
        │        pricing_engine_releases │
        │        (current @champion)     │
        └────────────┬──────────────────┘
                     │
                     ▼
        ┌─────────────────────────────────┐
        │   QUOTE RESPONSE                │
        │   ┌─────────────────────────────┤
        │   │ premium_offered             │
        │   │ breakdown (frequency,       │
        │   │            severity,        │
        │   │            demand,          │
        │   │            fraud, etc.)     │
        │   │ model_version_ids           │
        │   │ release_id                  │
        │   └─────────────────────────────┤
        │   Stored in:                    │
        │   - quote_payload_response      │
        │   - audit_log                   │
        └─────────────────────────────────┘
```

### Shadow Pricing & Monitoring Flow

```
┌───────────────────────────────────────────────────────┐
│ Use Case: Shadow Pricing (UC1)                        │
│ ├─ Load all policies from unified_pricing_table_live │
│ ├─ Score with CURRENT @champion models               │
│ ├─ Score with PRIOR @retired release                 │
│ ├─ Compute premium delta + churn risk                │
│ └─ Output: shadow_pricing_results,                   │
│            shadow_pricing_churn_risk                 │
└────┬────────────────────────────────────────────────┘
     │
     ▼ (Governance route queries)
┌───────────────────────────────────────────────────────┐
│ /api/governance/bias                                  │
│ ├─ JOIN shadow_pricing_results                       │
│ ├─ + bias_demographics_live (age, postcode IMD, etc.)│
│ ├─ Compute avg premium change per segment            │
│ └─ Flag outliers (e.g., >10% disparity)              │
└───────────────────────────────────────────────────────┘
```

### Price Optimisation Flow (Motor) — Full Closed Loop

```
┌─────────────────────────────────────────────────────────────────────┐
│ MONTH N: DEPLOY SOLVED FACTORS                                      │
│ ├─ previous month's optimisation_factor_table deployed              │
│ ├─ all new quotes/renewals priced with these factors                │
│ └─ recorded in quote stream                                         │
└────────────┬──────────────────────────────────────────────────────┘
             │
             ▼
     ┌─────────────────────────┐
     │  optimisation_data      │ (Block 1)
     │  ┌────────────────────┐ │
     │  │ Load month N quote │ │
     │  │ stream + claims    │ │
     │  │ ├─ vs_technical    │ │
     │  │ │  (risk only,     │ │
     │  │ │   before pricing)│ │
     │  │ ├─ vs_market       │ │
     │  │ │  (competitive    │ │
     │  │ │   rate ratio)    │ │
     │  │ ├─ converted (0/1) │ │
     │  │ └─ rate_change     │ │
     │  │    (renewal)       │ │
     │  └────────────────────┘ │
     └────────────┬────────────┘
                  │
                  ▼
     ┌──────────────────────────┐
     │ optimisation_elasticity  │ (Block 2)
     │ ├─ conversion_elasticity │
     │ │  (monotone LGBM)       │
     │ ├─ retention_elasticity  │
     │ │  (monotone LGBM)       │
     │ ├─ red-team panels       │
     │ │  (endogeneity,         │
     │ │   param recovery)      │
     │ └─ elasticity_curve      │
     │    (per-segment)         │
     └────────────┬─────────────┘
                  │
                  ▼
     ┌──────────────────────────┐
     │ optimisation_simulation  │ (Block 3)
     │ ├─ 3000 price scenarios  │
     │ ├─ apply elasticity      │
     │ ├─ aggregate to          │
     │ │  GWP/commission/margin │
     │ └─ extract efficient     │
     │    frontier              │
     └────────────┬─────────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
    ┌──────────┐      ┌──────────┐
    │ optimise │      │ renew_   │
    │_solver   │      │ solver   │
    │(new biz) │      │(renewals)│
    └────┬─────┘      └────┬─────┘
         │                 │
         └────────┬────────┘
                  ▼
     ┌──────────────────────────┐
     │ optimisation_fairness    │ (Block 5)
     │ ├─ fair-value evidence   │
     │ ├─ disparate impact      │
     │ │  screening             │
     │ └─ regulatory narrative  │
     └────────────┬─────────────┘
                  │
                  ▼
     ┌──────────────────────────┐
     │ optimisation_decision    │ (Block 6)
     │ _record                  │
     │ ├─ create immutable      │
     │ │  decision row          │
     │ ├─ store factors +       │
     │ │  fairness report       │
     │ └─ pending approval      │
     │    (approved_by: NULL)   │
     └────────────┬─────────────┘
                  │
                  ▼ (HITL approval)
    ┌─────────────────────────────┐
    │ /api/supervisor/approve     │
    │ ├─ User reviews and approves│
    │ └─ Set approved_by +        │
    │    approval_timestamp       │
    └─────────────┬───────────────┘
                  │
                  ▼
     ┌──────────────────────────┐
     │ DEPLOY (via MCP or app)  │
     │ ├─ optimisation_factor_  │
     │ │  table activated       │
     │ ├─ all new quotes use    │
     │ │  the factors           │
     │ └─ audit_log event:      │
     │    "factors_deployed"    │
     └────────────┬─────────────┘
                  │
    ┌─────────────┴──────────────┐
    │   (parallel, month N)      │
    ▼                            ▼
 ┌──────────────┐       ┌────────────────┐
 │ optimisation │       │ optimisation_  │
 │_monitoring   │       │ advance_month  │
 │             │       │               │
 │ drift check │       │ simulate      │
 │ (actual vs  │       │ month N+1:    │
 │  predicted) │       │  ├─ apply    │
 │             │       │  │  month N  │
 │ deviation   │       │  │  factors  │
 │ (premium vs │       │  ├─ observe  │
 │  factor     │       │  │  conversion
 │  table)     │       │  │  /retention│
 │             │       │  └─ feed into│
 │ corridor    │       │     next run │
 │ (GWP ≥      │       │ (closed loop)│
 │  portfolio  │       │             │
 │  floor)     │       │ Output:     │
 │             │       │ portfolio   │
 │ GIPP        │       │ snapshot    │
 │ (renewal    │       │ month N+1   │
 │  cap)       │       └────────────────┘
 │             │
 │ Output:     │
 │ monitoring_ │
 │ results     │
 │ (red/amber/ │
 │  green)     │
 └──────────────┘

Next iteration: MONTH N+1 starts with optimisation_data
pulling the updated portfolio_snapshot_month_N+1, quote
stream of month N+1, and repeats the loop.
```

### UC Lineage (Via Catalog Explorer)

```
unified_pricing_table_live (policy-keyed UPT)
 ├─ **trained** freq_glm @champion
 │   └─ **used in** pwg2_pricing_scorer endpoint
 │       └─ **used in** /api/pricing/score-quote
 ├─ **trained** sev_glm @champion
 ├─ **trained** demand_gbm @champion
 ├─ **trained** fraud_gbm @champion
 │
 ├─ **reads from** postcode_enrichment (real 1.5M UK postcodes)
 ├─ **reads from** 2_silver_market_pricing (DLT-cleaned)
 ├─ **reads from** 2_silver_geospatial_hazard (DLT-cleaned)
 ├─ **reads from** 2_silver_credit_bureau (DLT-cleaned)
 │
 └─ **used to build** shadow_pricing_results
     └─ **used to compute** bias_demographics impact
         └─ **queried by** /api/governance/bias

 motor_unified_pricing_table_live (motor subset)
 ├─ **trained** freq_glm_motor @champion
 ├─ **trained** sev_glm_motor @champion
 ├─ **trained** demand_gbm_motor @champion
 │   ├─ **elasticity model** conversion_elasticity_motor (monotone)
 │   └─ **elasticity model** retention_elasticity_motor (monotone)
 │
 ├─ **used in** optimisation_data (Block 1)
 │   ├─ → optimisation_elasticity (Block 2)
 │   │   ├─ → optimisation_simulation (Block 3)
 │   │   │   └─ → optimisation_solver (Block 4)
 │   │   │       └─ → optimisation_fairness (Block 5)
 │   │   │           └─ → optimisation_decision_record (Block 6)
 │   │   │               └─ → optimisation_explain_price (Block 7, UC function)
 │   └─ → optimisation_monitoring (Block 8)
 │       └─ → optimisation_advance_month (closed-loop)
 │
 └─ **used in** pwg2_motor_pricing_scorer endpoint
```

---

## Cross-Cutting Concerns

### 1. Authentication & Authorization

- **Workspace Auth:** All routes use Databricks workspace-authenticated SQL warehouse or Model Serving endpoints (no app-level API key; Databricks platform enforces access)
- **App Service Principal:** App SP granted `CAN_MANAGE_RUN` on jobs, `CAN_USE` on warehouse, `CAN_RUN` on Model Serving endpoints
- **End-User Attribution:** Middleware captures `x-forwarded-email` header (Databricks Apps) → audit log attributes events to the real user, not the app SP
- **Agent Token Self-Provisioning:** `pricing_chat_agent.py` + `governance_agent.py` self-mint 90-day PAT on deploy for their SQL tools (fallback: `AGENT_TOKEN`/`AGENT_HOST` env vars if PATs disabled)

### 2. Catalog Portability

**Design Goal:** One-liner `sed` substitution to move the demo to a different workspace.

**Approach:**
- All UC references via DAB variables: `${var.catalog_name}` and `${var.schema_name}`
- Default: `lr_pricing_v2_aws_us_catalog` / `pricing_workbench_gen2`
- To port:
  1. Create target catalog + schema in new workspace
  2. Edit `databricks.yml`: set `catalog_name` and `schema_name` in targets
  3. Deploy: `databricks bundle deploy --target <new_target>`

**Constraints:**
- External reference data (1.5M UK postcodes) must be present or re-generated
- Workspace-level assets (Genie spaces, Lakeview dashboards) must be created separately + wired via `GENIE_SPACE_ID` / `MART_DASHBOARD_ID` env vars

### 3. Serverless & Scale-to-Zero

**Principle:** Everything runs on Databricks serverless SQL + Model Serving; no always-on clusters.

**Implementation:**
- All jobs use serverless SQL (no `init_scripts`, no `driver_node_type_id`)
- Model Serving endpoints scale to zero (no provisioned throughput; on-demand compute)
- Optional live-serving tier (Lakebase online store) is "defined but dormant" — provision/teardown on demand
- Cost implications:
  - Core (data + models + agents): ~$200–400/month for a 500K-policy dataset at dev scale
  - Full Build: ~30–40 min, ~$10–20 in compute cost
  - Live serving (if armed): +$2–5/day while running; $0/day when torn down

### 4. Governance & Audit Trail

**Immutable Audit Log:**
- `audit_log` table, append-only (UC table enforcement: `InsertOnly` policy if available)
- Every event: event_type (dataset_approved, model_rejected, manual_upload, quote_requested, factors_deployed, etc.), entity_type, user_id, timestamp (UTC), details (JSON)
- Sourced by: app routes, agents, batch jobs
- Ingestion: app middleware captures `x-forwarded-email`; batch jobs log via Databricks API

**Governance Packs:**
- Per-model-version PDF: 8–10 pages, auto-generated by `governance_pack.py`
- Covers: overview, data provenance, performance metrics, feature importance, stability over versions, limitations, regulatory statement, sign-off
- Stored: `/Workspace/Volumes/{catalog}/{schema}/governance_packs/{pack_id}.pdf`
- Indexed: `governance_packs_index` table (model_family, version, pack_id, pack_url, created_at)

**UC Lineage:**
- Every model version links to training input (`unified_pricing_table_live` + Delta version)
- Every rating-engine release links to model versions + config
- Feature catalog provides feature-level provenance (source table, transformation, owner, PII/regulatory flags)
- Visible in: Catalog Explorer (Data Lineage tab)

**Bias Screening:**
- `bias_demographics_live` table: per-policy sensitive attributes (postcode IMD quintile, age band, etc., if proxy-available)
- App governance routes compute Gini/premium change per segment; flag disparate impact (>10% deviation)
- Governance agent can draft regulatory statement explaining impact

### 5. Compliance & Regulatory

**Regulatory Export:**
- `src/08_governance/regulatory_export.py` — Export pricing decisions + model metadata in regulatory format (CRD IV, IFR compliance)
- Output: CSV/JSON in volume

**Fair-Value & GIPP:**
- Optimisation fairness block (Block 5) screens for disparate impact before deploy
- Renewal solver enforces Good Insurance Practice ceiling (rate change cap)
- Decision records store fairness report + regulatory narrative

**Model Governance:**
- Governance packs per model version (PDF + sidecars)
- MLflow tags (`story`, `simulated`, `upt_delta_version`) for traceability
- UC aliases (`@champion`, `@retired`, `@backtest`) for version control

### 6. Demo Reset & Idempotence

**Full Build (as Idempotent State Machine):**
- Every step (ingestion, UPT build, training, seeding, agents) is idempotent
- Running Full Build twice produces the same end state (tables overwritten, not appended)
- Audit log is append-only, so events accumulate (expected)

**Demo Reset:**
- `src/04_models/production/demo_reset.py` — Drop all tables and volumes; reset to initial state
- Useful for resetting a demo environment between customer sessions

### 7. Disclaimers & Branding

**Demo Disclaimer (Every Page):**
- "This is not a Databricks product — an example of commercial pricing built purely on Databricks. Bricksurance SE is synthetic — policies, quotes, claims and demographics are generated; the UK postcode enrichment is real public data (OGL)."

**No WOW Factor Branding:**
- Features speak for themselves; no "WOW Factor" labels
- Design: clean, professional, demo-standard (consistent with bricksurance playbook)

**About This Demo Page:**
- `/docs/about_demo.md` covers deployment guide, feature list, disclaimer, FAQ

### 8. Dependencies & Environment

**Key Libraries:**
- `statsmodels` — GLM training
- `lightgbm` — GBM training
- `mlflow` — Model tracking + registry
- `databricks-feature-engineering` — Feature store integration
- `databricks-sdk` — Workspace API (job triggering, grants)
- `databricks-agents` — Agent Framework for governance + chat agents
- `pyyaml` — Constraint YAML parsing (optimisation)
- `fpdf2`, `matplotlib` — Governance pack PDF generation
- `pydantic` — FastAPI request validation

**Serverless Environment Spec (in DAB):**
- `client: "5"` (latest Databricks Runtime)
- `dependencies` list per job (e.g., mlflow, statsmodels, etc.)
- DLT pipeline uses standard DBR for DLT

---

## Gaps, Redundancies & Open Threads

### Critical Findings

#### 1. **Duplicate Factory Routes: `factory.py` vs `factory_real.py`**
- **Files:**
  - `/src/app/server/routes/factory.py` (730 LOC)
  - `/src/app/server/routes/factory_real.py` (424 LOC)
- **Issue:** Both expose `/api/factory/*` and `/api/factory-real/*` endpoints. `factory.py` seems to simulate variants with synthetic metrics; `factory_real.py` calls the real `factory_train` notebook (actual GLM fitting).
- **Current State:** Both are mounted in `src/app/app.py` line 66–67.
- **Concern:** Likely intended as a demo-vs-real toggle, but the split is implicit (no documentation of when to use which). **Gap:** No clear guidance on when the app should route to factory vs factory_real.
- **Recommendation:** Consolidate or document the distinction clearly. Consider a single route with a `mode` parameter or explicit feature flag in env vars.

#### 2. **Motor Models: Partially Integrated**
- **Files:**
  - `src/04_models/production/freq_glm_motor.py`, `sev_glm_motor.py`, `fraud_gbm_motor.py`, `demand_gbm_motor.py`
  - `resources/motor_models.yml`
  - `resources/motor_provision.yml`, `motor_teardown.yml`, `motor_upt.yml`, `motor_descriptions.yml`
  - `src/07_serving/live_pricing/motor_provision.py`, `motor_teardown.py`
- **Current State:** Motor models are champions + registered in UC. They feed the price optimisation spine + broker chat MCP tools. However:
  - Motor model descriptions are set by a separate job (`set_motor_model_descriptions.py`) — why not part of model training?
  - Motor provisions (online store, QPS test) are defined but marked "on-demand" (not in full_build by default).
  - No live-serving tab in the UI for motor (unlike commercial, which has a `/pricing-engine` live tab).
- **Gap:** Motor line appears to be the secondary line; commercial is the primary demo (more UI polish, live-serving tier integration). Motor is used for optimisation + broker chat but not fully featured in the UI.
- **Recommendation:** Clarify the positioning: Is motor an equal citizen or a secondary demo vehicle? If equal, expand UI coverage and full_build inclusion. If secondary, document that explicitly.

#### 3. **Two Optimisation Naming Conventions (British vs American)**
- **Files:**
  - Most notebooks use British spelling: `optimisation_*` (e.g., `optimisation_elasticity.py`)
  - Some references use American: `optimization_*` (e.g., `docs/optimization_spec.md`, `docs/OPTIMIZATION_INVENTORY.md`)
  - DAB variable name: `enable_optimization` (American)
- **Current State:** Mostly consistent in code (British in notebooks + table names), but docs are mixed.
- **Gap:** Inconsistent across code + docs. British spelling is preferred in the codebase (per comment in `optimisation.yml`), but files like `docs/optimization_spec.md` and routes like `optimisation.py` break this.
- **Recommendation:** (Low priority; mainly cosmetic.) Standardize on British spelling across all files (including DAB variable → `enable_optimisation`). Or accept the mixed convention and document it.

#### 4. **Rating Engine Configuration: Incomplete Integration**
- **Files:**
  - `rating_engine_seed.py` creates `rating_engine_config` table with hardcoded values
  - `pricing.py` routes reference `pricing_engine_releases` but not `rating_engine_config` directly
- **Current State:** Rating engine config exists and is seeded, but the UI (`/rating-engine-integration` page) seems to be a placeholder. No app route (`/api/deployment/rating-config`) actually returns the config; the page likely shows mocked data.
- **Gap:** Rating engine config is a critical table but appears underutilized in the UI. The `/rating-engine-integration` page doesn't seem to let users edit or view the actual config.
- **Recommendation:** Either (a) populate the `rating_engine_config` table with realistic, time-varying data (expense loadings, commission %, underwriting rules) and wire it into the app's `/api/deployment/rating-config` route + UI, or (b) mark the page as "not yet implemented" and remove it from the sidebar.

#### 5. **Live Pricing Tier: Disconnected from Full Build**
- **Files:**
  - `resources/live_pricing.yml` (provision/teardown jobs)
  - `src/07_serving/live_pricing/motor_provision.py`, `motor_teardown.py`, `03_load_test.py`, `04_realtime_feature_refresh.py`
  - App page `/pricing-engine` (if live tier is provisioned)
- **Current State:** Defined but not part of full_build by default (marked "optional, on-demand, scale-to-zero cost while idle"). User must manually provision the online store + QPS tester.
- **Gap:** The UI page `/pricing-engine` references a "live tab" that only appears if the live-serving tier is provisioned. If not provisioned, users see nothing (or an error). No clear UI cue to the user about how to provision it.
- **Recommendation:** Add an "Addons" / "Provisions" UI page that shows the status of optional tiers (live serving, elasticity scorer) and lets the user provision/teardown them with a click. Currently, users must know to run `databricks bundle run live_pricing_provision`.

#### 6. **AI/BI Genie Spaces + Mart Dashboard: Manual Wiring**
- **Files:**
  - `create_ai_assets.py` creates Genie spaces + Lakeview dashboard (workspace assets)
  - `databricks.yml` variables: `genie_space_id`, `genie_quote_space_id`, `mart_dashboard_id` (all empty by default)
  - App config endpoint (`/api/config`) resolves by title if env vars are blank
- **Current State:** Genie spaces + dashboard are created but the app won't find them unless the user manually sets env vars or the app auto-resolves by title. Works, but feels fragile.
- **Gap:** No automatic wiring in the DAB. The app is resilient (auto-resolves by title if IDs not set), but documentation is sparse.
- **Recommendation:** Document the two-phase workflow clearly: (a) first full_build creates assets and prints their IDs; (b) user pastes IDs into `databricks.yml` (or sets env vars); (c) redeploy. Consider automating this with a post-deploy script.

#### 7. **Unused / Underutilized Models**
- **Files:**
  - `model_04_gbm_risk_uplift.py` — Trained but never used in production serving
  - `model_05_fraud_propensity.py` — Trained and loggged to MLflow but only used in bias backfill (not in live scoring)
  - `model_06_retention.py` — Trained but unclear how it's used (shadow pricing? monitoring?)
- **Current State:** These models exist and are trained in full_build, but their role is unclear from the docs. They may be designed for future use cases or reference implementations.
- **Gap:** No documentation of why these models exist and how/when they're used. Lineage in UC only shows "trained" but not "used in".
- **Recommendation:** Either (a) document the intended use case for each supplementary model and wire it into a visible feature (e.g., fraud surcharge in live scoring, retention prediction in quote review), or (b) remove them from full_build and move to `supplementary_models.yml` (marked as optional/exploratory).

#### 8. **Broker Chat / Agentic Distribution: MCP Surface Incomplete**
- **Files:**
  - `src/app/server/routes/broker.py` (340 LOC) — Agentic distribution routes
  - `src/app/server/routes/distribution.py` (108 LOC) — Configuration
  - `src/app/server/mcp_tools.py` — MCP tools (opt_*, price_*, mcp_buyer_*)
- **Current State:** Broker chat page exists; MCP tools are defined. However:
  - **Not in full_build:** No orchestration to set up the broker chat agent or MCP surface
  - **Unclear deployment:** How does the external MCP client connect? Is there a separate MCP server endpoint?
  - **Limited UI:** The app has a `/broker-chat` page, but it's unclear if it's a real integration or a placeholder
- **Gap:** Agentic distribution feels incomplete. The MCP tools are defined but not wired into the Agent Framework endpoint (like `pwg2_governance_agent` is).
- **Recommendation:** Either (a) fully integrate broker chat into the app (deploy an agent endpoint, wire the UI page, add to full_build), or (b) document it as a "future feature" placeholder and remove the UI page for now.

#### 9. **NewDataImpact Study: Disconnected from Main App**
- **Files:**
  - `src/new_data_impact/` (6 notebooks)
  - No explicit app route or page integration
- **Current State:** Standalone notebooks; can be run manually but not discoverable from the app. The Home page mentions it but doesn't link to a page.
- **Gap:** No built-in UI to run the notebooks or view results. Users must know to run them separately.
- **Recommendation:** Create a `/new-data-impact` page that displays the results (if run) and offers a button to trigger the study. Or document it as an optional external workflow.

#### 10. **Feature Store Integration: Online Store Provisioning Is Optional**
- **Files:**
  - `src/07_serving/setup_online_store.py`
  - Feature lookup is referenced in `features.py` but implementation is sparse
- **Current State:** Online feature store (Lakebase) is optional; must be provisioned separately. Offline features (Delta) are the default.
- **Gap:** The feature store page (`/feature-store`) shows offline + online status, but if online store is not provisioned, the page will show placeholder data or errors.
- **Recommendation:** Add a provisioning flow in the `/addons` page or `/feature-store` page to arm/disarm the online store. Or clarify in the UI that online store is optional.

#### 11. **No Data Quality / Freshness Dashboard**
- **Files:**
  - DLT expectations are defined in `src/02_silver/` SQL files
  - `governance.py` routes reference "data freshness" but no explicit route
- **Current State:** Data quality rules exist (DLT expectations) but no visible UI to inspect them. No SLA monitoring.
- **Gap:** Users can't easily see which ingestion steps have failed or are stale.
- **Recommendation:** Add a `/data-health` page that queries DLT expectations + last-refresh timestamps and visualizes data freshness by dataset + expectation.

#### 12. **Missing UC Functions**
- **Files:**
  - Only one UC function is explicitly created: `optimisation_explain_price` (in `optimisation_explain_price.py`)
- **Current State:** Other functions likely exist (e.g., `rating_engine_config` lookup, `regulatory_export`), but they're not explicitly registered.
- **Gap:** UC functions should be explicitly created and versioned, but only the optimisation function is visible.
- **Recommendation:** Create explicit UC functions for: regulatory export (CRD IV formatting), rating config lookup (by release_id), bias metrics (by segment), shadow pricing (by policy_id). Make them discoverable in Catalog Explorer.

#### 13. **Governance Agent: Partially Wired**
- **Files:**
  - `src/04_models/production/governance_agent.py` — Deploys agent endpoint
  - No explicit app route calls it (unlike `pricing_chat_agent`, which is called by `/api/agent/explain`)
- **Current State:** Agent endpoint exists; unclear how the app uses it.
- **Gap:** Governance agent appears to be deployed but not actively used by the UI.
- **Recommendation:** Add UI affordances (buttons, modals) to trigger governance agent queries (e.g., "explain this model's fairness", "draft a regulatory statement", "analyze audit log trends").

#### 14. **Compare & Test (Historical Scoring) is Batch-Only**
- **Files:**
  - `resources/historical_quote_score.yml` — Batch job (not interactive)
  - `src/04_models/production/compare_score.py` — Batch scoring logic
- **Current State:** Users can compare two releases via `/compare-test`, which triggers a batch job. Results appear asynchronously (users must poll).
- **Gap:** No real-time comparison; requires a batch job (~5–10 min). For a 2K-quote comparison, this is acceptable, but the UX could be smoother.
- **Recommendation:** Consider a hybrid approach: (a) for small portfolios (<5K quotes), score in-line (Model Serving call per release); (b) for large portfolios, kick off batch. Or pre-cache comparisons for recent releases.

#### 15. **No A/B Testing Framework**
- **Files:**
  - No A/B testing logic visible
- **Current State:** Shadow pricing lets users see the impact of a new release, but no formal A/B test framework (e.g., holdout groups, significance testing).
- **Gap:** For real pricing decisions, the team would want A/B testing. This demo doesn't cover it.
- **Recommendation:** (Low priority for a demo; nice-to-have for a production system.) Document this as a potential extension.

---

## Summary: Top 5 Gaps & Redundancies

1. **Duplicate Factory Routes (`factory.py` vs `factory_real.py`)** — Both exist; unclear distinction. Consolidate or document.
2. **Motor Models: Half-Integrated** — Champions exist, but UI coverage is thin. Clarify positioning (primary vs secondary line).
3. **Rating Engine Config: Underutilized** — Table exists but UI is placeholder. Wire it or remove it.
4. **Live Serving Tier: Manual Provisioning** — Works but no UI affordance to provision/teardown. Add an Addons page.
5. **Broker Chat / Agentic Distribution: Incomplete** — MCP tools defined but not fully wired into Agent Framework. Finish the integration or mark as future work.

---

## Conclusion

**Pricing Workbench Gen2** is a **comprehensive commercial pricing demo** that **demonstrates production-shaped patterns** for building governed pricing operations on Databricks. Every layer — from raw ingestion through live scoring to regulator-facing defense — is traceable, auditable, and versioned. The system is designed to scale from 50K to 5M policies on serverless compute, with optional extensions (live serving, price optimization, agentic distribution) that can be armed/disarmed on demand.

The core demo flow is clean: ingestion → UPT → models → agents → HITL app. The price optimisation module adds a sophisticated second act (motor-line elasticity-driven solver with fairness guardrails + immutable decision records). The system is ready for exploration and customization; the patterns are production-shaped, but this is a demo on synthetic data — not a production deployment, and not sold or warranted by Databricks.

The gaps identified above are mostly (a) incomplete feature integration (rating engine UI, broker chat wiring) or (b) naming/organizational redundancies (factory.py vs factory_real.py, British vs American spelling). None are blocking; all are straightforward to address based on intended use.


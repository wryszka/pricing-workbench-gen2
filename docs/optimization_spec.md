# Price Optimization Module — Build Spec (pricing-workbench-gen2)

Status: ready to build. Written against `wryszka/pricing-workbench-gen2` @ main. Follows gen2 conventions throughout: one schema, `opt_*` table prefix, `pwg2_` global-asset prefix, deploy-profile gating, Full Build orchestration, HITL patterns from the existing app. **This is the canonical spec — build from this, don't re-derive.**

---

## 0. Pre-work (before any module code)

- [x] **Remove the client name from `databricks.yml`** → "frozen v2 client deployment" (done 2026-08-19; also scrubbed app.pricingv2.yaml, docs/v2_plan.md; removed the AXA hand-off machinery scripts/make_handoff.sh + handoff/).
- [x] Remove/lock the internal Google Doc runbook link in README (public repo) — done. (App sidebar DemoDocCard still links it; make env-driven if the app repo is shared publicly.)
- [ ] Confirm what the existing **Demand GBM** predicts today. It is either promoted into this module as the conversion/elasticity model, or renamed — the demo must not contain two demand-model concepts.

## 1. Purpose and positioning

Demonstrate **how** an insurer builds price optimization on Databricks from scratch, and **what** the open platform enables that appliances cannot: open code end-to-end, elastic compute for exhaustive scenario exploration, first-class lineage over the full decision chain, and agentic automation with autonomy as a policy setting.

Not a competitor product. The client owns demand models, simulation, and governance; the execution layer is swappable. Risk model = the floor (cost); optimization = shaping margin above the floor. The solver run is **always offline**; execution mode (table vs. endpoint) is a config flag.

### The message (three beats)
1. **This is what we need** — quote-response and renewal data. It already flows through the standard pipeline; the question is whether lost quotes are kept.
2. **This is what we do with it** — model demand, simulate the book, decide under versioned constraints, deploy, monitor. One governed loop, open code, in your workspace.
3. **These are the results** — scenario trade-off view, factor table, audit trail from raw quote to deployed rate.

### Show-don't-say competitive moments (never name a vendor)
- Open the constraint YAML + its git history live.
- Open UC lineage end-to-end: quote → model version → constraint version → factor → deployed rate.
- Show the scenario table row count: "N thousand candidate price sets overnight — N is your choice, not a licence tier."
- Flip the serving flag batch ↔ endpoint in one config line.
- Ask Genie a question about the scenarios, live.

## 2. Placement in the repo

- **Same bundle, same schema** (`pricing_workbench_gen2`). Optimization tables prefixed `opt_*` (mirrors the `impact_*` convention).
- Source under `src/09_optimization/` (numbered after `08_governance/`).
- Job/pipeline definitions in `resources/optimization.yml`.
- Workspace-global assets prefixed `pwg2_` (e.g. `pwg2_optimization_run`, `pwg2_elasticity_scorer`).
- **Deploy gating:** extend `deploy_profile` → `core` | `full` | values gain an orthogonal flag `enable_optimization: "true" | "false"` (default `"false"` initially, flip to `"true"` when stable). Optimization jobs are always defined, dormant unless enabled — same pattern as the live-serving tier.
- App: new sidebar page **Price Optimization** in the existing React app; FastAPI router `src/app/.../optimization.py`. No second app, ever.

## 3. Data (block 01) — standard ingestion only

**No separate ingestion.** All inputs derive from the existing quote stream and policy tables.

Changes to the synthetic data generator (`00_setup`) — the one real data-gen work item:
- **Outcome labelling first-class:** every quote row carries `outcome` (bound / lost) and `bound_ts`.
- **Renewal events:** renewal offer rows (prior premium, offered premium, outcome retained/lapsed).
- **Injected price variation:** controlled noise / test-cell price variation in historical quotes, otherwise elasticity is unlearnable from a deterministic engine's output. Variation magnitude a generator parameter.
- **Elasticity drift over the rolling-month timeline:** demand sensitivity drifts subtly month over month so monitoring has real movement and the drift sentinel has something genuine to catch.

Derived objects (views/tables over existing silver + quote stream):
- `opt_quote_response` — one row per quote: features, price offered, channel, outcome.
- `opt_renewal_response` — one row per renewal offer: prior/offered premium, tenure, outcome.
- `opt_portfolio_snapshot` — current book for simulation.

## 4. Elasticity models (block 02)

- **Conversion model** (new business) and **retention model** (renewal), price / price-change as explanatory variables.
- Resolve against the existing **Demand GBM**: preferred path is that model *becomes* the conversion model, trained on `opt_quote_response`, registered through the existing Model Factory pattern (leaderboard + governance PDF per model).
- **Monotonicity in price enforced** (`monotone_constraints`) — the solver exploits any wrinkle; enforcement is a demo beat.
- Key artifact: **elasticity curve per segment** (price vs. conversion probability) — surfaced in the app page and reused in the talk track.
- MLflow + UC registry, `pwg2_` naming, aliases consistent with existing champions.

## 5. Simulation (block 03)

- Score `opt_portfolio_snapshot` across a grid of candidate price adjustments; Spark-parallel.
- Output `opt_scenarios`: profit, volume, retention by segment per candidate price set.
- Grid size is a job parameter — the "N is your choice" demo moment.

## 6. Constrained optimization (block 04)

- Solver: scipy / Pyomo. Deliberately boring, fully open.
- **Constraints as versioned YAML in the repo** (`src/09_optimization/constraints/`): deviation corridor around technical price, GIPP renewal rule (renewal ≤ equivalent new business), segment caps, forbidden-signal exclusions, sanity/monotonicity rules. Jurisdiction togglable ("elasticity may contribute: yes/no").
- Output `opt_factor_table` — same artifact shape the workbench's rating config already consumes; deployment = the factor table joins the existing rating-config/release-rate-book path.

## 7. Serving

- **Pattern A — batch (spine):** `opt_factor_table` promoted to the existing Lakebase online store; the rating engine's scoring path does a FeatureLookup like any other feature. Zero new infrastructure.
- **Pattern B — real-time (addendum):** elasticity model as one additional Model Serving endpoint (`pwg2_elasticity_scorer`), called by the pricing function with candidate prices.
- Adjustment logic lives **inside the existing pricing function** (apply factor, clamp to corridor); factor source switchable table ↔ endpoint via one config value. Demo beat: flip the flag, batch becomes real-time.
- Real-time tier follows the live-serving tier pattern: defined, dormant, armed on demand, torn down after.

## 8. Monitoring / feedback (block 05)

- `opt_conversion_actuals` — actual vs. predicted conversion per cycle; elasticity drift metrics; constraint-breach checks; deviation-from-technical-price distribution.
- Surfaces in the existing Monitoring/Governance pages + one tile on the Modelling Mart dashboard.
- The rolling-month timeline shows these *moving* — not a static snapshot.

## 9. App page (block 06) — HITL

- **Price Optimization** page: scenario comparison (trade-offs by segment), constraint-set version display, elasticity curves, approve → deploy.
- Reuses the existing HITL approval flow (External Data pattern) and app-SP job-trigger grants (`CAN_MANAGE_RUN` pattern already in the bundle).
- Genie demoed live against `opt_scenarios` via the existing Genie-space wiring (`app.v2.yaml` env id, tab hidden until set).

## 10. Agentic loop — MCP-first (build requirement, day one)

Every capability exposed as a callable tool; app, notebook, and agent are all clients of the same surface. Follow the existing agent conventions — **NB gen2 uses passthrough auth, NOT the AGENT_TOKEN fallback** (the spec's token note is superseded by the gen2 no-PAT rework).

Tools (UC functions / Jobs triggers behind MCP endpoints; parameterized, idempotent, structured returns):
- `refresh_elasticity_models`, `run_simulation(grid)`, `run_solver(constraint_version)`, `deploy_factors`
- Read surfaces: elasticity curves, `opt_scenarios`, monitoring metrics, constraint versions, lineage
- `constraint_yaml` read/write with validation
- **Deployment gate as a tool with the corridor policy enforced server-side** — an agent cannot bypass it regardless of prompt.

Agents:
1. **Drift sentinel** — watches monitoring signals; raises a re-optimization request with rationale.
2. **Analysis planner** — designs the run (segments, grid, constraint version); exploits elastic compute for overnight exhaustive exploration.
3. **Execution** — deterministic Jobs DAG (no agents inside the math).
4. **Results interrogator** — Genie over `opt_scenarios`; trade-off narratives.
5. **Fairness reviewer** — deviation distributions, proxy-correlation checks (vulnerability / protected-characteristic proxies), drafts fair-value evidence pack.
6. **Recommender** — decision pack: proposed factors + rationale + fairness evidence + diff vs. current.
7. **Gate** — within pre-approved corridor → auto-deploy with audit trail; outside → human sign-off in the app page.
8. Supporting: **constraint author** — natural language → validated solver YAML.

Deck line: *the machine runs the pricing cycle; the human sets the policy for when the machine may act alone.*

## 11. Governance

- Full UC lineage: quote data → elasticity model version → constraint set version → solver run → factor table → deployed rate.
- Fairness apparatus first-class: outcome monitoring by segment, deviation corridors, vulnerability screen hooks, fair-value evidence generation into the existing regulatory-export path.
- Regulatory framing baked in: GIPP (UK), Consumer Duty fair value, EIOPA differential-pricing statement, GDPR Art. 22 explainability, US cost-based-state configurability.
- Compliance story = engineering story: constraints in the solver, versioned, auditable.

## 12. Orchestration and demo execution

- **One flow, no per-part smoke tests.** Optimization tasks append to the **Full Build** orchestrator in dependency order, gated by `enable_optimization`: data-gen deltas → elasticity training → simulation → solve → factor promotion → monitoring backfill → app grants.
- Demo walks the DAG as a single story: *data → behaviour → what-if → decision under constraints → reality check → human approval.* Notebooks are narrative stops, not standalone tests.
- Internal build order: data-gen changes → elasticity (incl. Demand GBM resolution) → simulation → solver+constraints → app page → monitoring → MCP tools → agents → real-time addendum.

## 13. Forward hook — FiDA (do not build yet)

Open-finance (FiDA) data enters as one more external dataset through the standard External Data HITL flow, feeding the elasticity/underwriting feature set — **through the fairness gate**. One future slide, zero current code.

## 14. Anticipated challenges

| Challenge | Answer |
|---|---|
| "This is only batch; real-time is the hard part" | Optimization is offline everywhere; execution mode is a flag — here's the live endpoint. |
| "Your optimizer is weaker than proprietary" | Correct, and not the question. Most uplift sits in the first ~80% of sophistication; captured uplift vs. retained licence cost is testable via a shadow-mode pilot on one product line. |
| "How is this governed?" | Open the lineage graph and the constraint YAML history — live, in the room. |
| "Is agent-driven pricing safe?" | Agents never set prices; a deterministic solver does, under versioned constraints, behind a server-side gate agents cannot bypass. |

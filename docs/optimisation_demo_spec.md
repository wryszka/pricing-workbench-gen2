# Price Optimisation — specification & gap analysis (consolidated)

> **Consolidated 2026-08-26:** `docs/optimization_spec.md` (US-spelled, the gen2
> canonical build spec) has been merged into this file. This is now the single
> authoritative optimisation spec. The original scoping/gap-analysis content
> (v2, 2026-08-13) is preserved below as Part 1; the gen2 build spec follows as
> Part 2. Build from Part 2; Part 1 is historical context.

---

# Part 1: Original scoping & gap analysis (v2, 2026-08-13)
<!-- Original content unchanged below this line -->

**Status:** specification only — nothing built. 2026-08-13.
**Target:** Pricing Workbench **v2** (`fevm-lr-pricing-v2-aws-us`, catalog
`lr_pricing_v2_aws_us_catalog`, schema `pricing_workbench`, warehouse
`f738fde9a1197aeb`). Dev is explicitly out of scope.
**Trigger:** a GI client wants to move off **Earnix**; price optimisation is
their main concern right now. This spec scopes what it would take to show a
credible optimisation *example* on the workbench — not to deliver a production
optimiser.

---

## 0. Decisions taken (2026-08-13) — scope this to a DEMO

Accepted into v2. Explicit steer from Laurence: **this is a demo OF optimisation,
not an implementation of an optimiser.** The goal is to make an evaluator who is
shopping for optimisation see that the pattern is available on Databricks — open,
governed, their models. So build the *smallest credible* example, not a
framework.

- **Lead with new business** (conversion/profit). Renewal/retention is beneficial
  and comes second — do NOT build `retention_churn` for the first cut.
- **Jurisdiction: not important** — a UKI/EMEA insurer. Keep regulatory framing to
  a **light, one-line nod** (a fair-value / no-price-walking guardrail shown as an
  enforced constraint), NOT the full FCA framework of §6. §6 stays as optional
  depth for a UK-specific conversation.
- **Scope = MVP, trimmed.** One objective (profit), one or two constraints
  (rate-change cap + margin floor), one app page, one segment view + portfolio
  impact. Grid-search solve for transparency. No multi-objective frontier
  machinery beyond a simple volume-vs-profit sweep if it's cheap.
- **Elasticity DGP fix is still required but kept MINIMAL** — a simple calibrated
  price→conversion logit so the demand curve actually slopes and there is a
  visible optimum. Enough to be credible, not an elaborate segment-varying model.
- **Tier: Core.** No live-serving/online-store dependency.

Everything below is the fuller specification; the first build is the trimmed MVP
above. §7 "Full" and §6 UK-specific depth are future, not now.

---

## 1. Positioning (what we are and are not showing)

Databricks does not sell a pricing optimiser and does not deliver models. What
this demo shows is the **platform pattern** for price optimisation:

- the client's **own** cost and demand models, governed side by side in Unity
  Catalog;
- a **reference optimisation routine** (a worked example the client's actuaries
  own and can rewrite) that turns those models into a price recommendation;
- every recommendation **explainable, versioned and audited**, with regulatory
  constraints enforced as first-class inputs.

This is the wedge against Earnix: **open, transparent, your models, no black
box, no per-seat lock-in** — the optimisation logic is readable code and its
config is governed data, not a vendor's closed engine. We win on governance and
transparency, not on "our optimiser is better."

> Keep the standard demo disclaimer: Bricksurance SE is fictional; all data
> synthetic; the optimisation method is illustrative, not a certified pricing
> model.

---

## 2. What price optimisation is (the decision we are demonstrating)

For each risk (or segment), given:

- **expected cost** `c(x)` = frequency × severity (the technical/risk price), and
- **demand** `d(p | x)` = probability of conversion (new business) or renewal
  (retention) as a function of the offered price `p`,

choose the price `p*` that maximises a **business objective** subject to
**constraints**:

| Objective | Maximise |
|---|---|
| Profit | `d(p) · (p − c)` |
| Volume | `d(p)` s.t. margin floor `p − c ≥ m` |
| Lifetime value | multi-year `d`/retention × margin |
| Blended | `α·profit + β·volume` on an efficient frontier |

**Constraints** (all first-class, all audited):
- rate-change caps (e.g. ±15% vs current book);
- minimum margin / maximum loss ratio;
- competitive guardrails (stay within *k* of market/competitor);
- **regulatory** — see §6. For UK GI this is not optional.

Two demand regimes, both relevant to an Earnix displacement:
- **New business** — conversion elasticity (the `demand_gbm` model).
- **Renewal** — retention/churn elasticity (the `retention_churn` model, not yet
  built). Renewal price optimisation is Earnix's core use case.

The showable artefacts are the **demand curve + cost line per segment**, the
**optimal price**, the **efficient frontier** (volume vs profit), and the
**portfolio impact** of moving from the current rate book to the optimised one.

---

## 3. Target-state architecture in v2

How it plugs into the existing flow (additions in **bold**):

```
UPT (gold) ──> Cost model  (freq_glm × sev_glm)              ─┐
           └─> Demand model (demand_gbm: conversion|price)    │
Quote stream ─> Retention model (retention_churn: renewal|price) ─┤
                                                               ▼
                              **Optimisation engine**  (notebook + util)
                         objective + constraints  ──>  p* per segment
                                                               │
                    **Optimisation config** (governed table, versioned)
                                                               ▼
              **App page "Price Optimisation"**  ── efficient frontier,
              demand/cost curves, p* per segment, portfolio impact vs book,
              what-if levers, **guardrail + regulatory panel**
                                                               │
                           Governance packs · audit_log · shadow_pricing_impact
                              (reuse existing governance & A/B rails)
```

Nothing here requires the live-serving tier. It is a batch/interactive
optimisation over governed tables + scale-to-zero model endpoints — fits the
**Core** profile philosophy.

---

## 4. Current v2 state (verified 2026-08-13)

| Building block | v2 state | Verdict |
|---|---|---|
| Cost model | `freq_glm`, `sev_glm` registered; `pricing_scorer` endpoint READY | ✅ present |
| Demand/elasticity model | `demand_gbm` registered (target `converted`; price features `log_premium`, `quote_to_market_ratio`, `competitor_a_min_premium`) | ⚠️ present but see §5.1 |
| Retention model | **absent** (planned in v2_plan WS2 as `retention_churn`, notebook only) | ❌ missing |
| Quote stream w/ conversion | `quotes` (conversion outcomes), 3 payload tables | ✅ present |
| Rate book / rating config | `rating_engine_config`, `pricing_engine_releases` | ✅ present |
| A/B & impact framework | `shadow_pricing_impact` (proxy formula — kept as-is per v2 plan) | ✅ reusable |
| Governance / audit | governance packs, `audit_log`, bias | ✅ reusable |
| App shell, monitoring, agents | `pricing_chat_agent`, `pricing_governance_agent` READY; mature React app | ✅ reusable |
| **Optimisation engine** | **absent** | ❌ core gap |
| **Constraint / guardrail framework** | **absent** | ❌ missing |
| **Optimisation objective/config governance** | **absent** | ❌ missing |
| **"Price Optimisation" app page** | **absent** | ❌ missing |
| **Efficient frontier / portfolio impact view** | **absent** | ❌ missing |

v2 runs the "core" profile (35 tables) — no live-serving/MCP/OTel assets, which
is fine: optimisation does not need them.

---

## 5. Gap analysis — what is missing

### 5.1 The elasticity signal in the data (foundational — the long pole)

**Verified on v2:** conversion rate is *flat* at ~0.62–0.68 across the entire
price range (0.1× to 3.3× of market rate). The synthetic `converted` flag was
generated **independently of price**, so there is **no price→demand
relationship** to optimise against.

Consequence: the demand model can be accurate on risk/location/credit features
yet carry **near-zero real price elasticity**. An optimiser on this data finds no
interior optimum — with demand insensitive to price, "optimal" price runs to the
constraint ceiling, which makes the demo tell the wrong story.

**What's needed (spec, not build):** the quote-generation process must embed a
**calibrated price-elasticity data-generating process** — conversion as a logit
declining in price-relative-to-market and to competitor, with the slope
(elasticity) varying by segment (SIC, size band, region, risk tier). Same
treatment for the renewal/retention series. This is the single most important
missing piece; without it, everything downstream is unconvincing. Best fixed in
the v2 data generator so both commercial and motor lines inherit it.

### 5.2 Demand & retention models (re-spec, not just retrain)

- **Demand model** — after 5.1, re-train and **validate the price response**:
  the modelled demand curve must be monotonically decreasing in price and produce
  sensible per-segment elasticities. Add an elasticity-by-segment diagnostic. The
  current model has no such validation.
- **Retention model** — does not exist as a deployed asset. Needs building and
  registering (`retention_churn`, already flagged in v2_plan WS2) for renewal
  optimisation. Requires a renewal dataset with retention outcomes and price
  variation (tie to 5.1).

### 5.3 Optimisation engine (the core net-new artefact)

Absent entirely. Specification:
- A **worked-example notebook** + a small reusable util that, per segment (and
  optionally per policy), takes `c(x)` and `d(p|x)` and solves for `p*` under a
  chosen objective and constraint set. Start with a **grid search** over a price
  multiplier for transparency; offer a `scipy.optimize` constrained solve as the
  "proper" version. Portfolio-level constraints (e.g. hold overall volume while
  lifting profit) via a Lagrange multiplier / dual sweep.
- Emit an **efficient frontier** (volume vs profit as the objective weight
  sweeps) and a **portfolio impact** table (current book vs optimised: GWP,
  expected profit, conversion, loss ratio).
- MLflow-tracked runs so each optimisation is reproducible and comparable.

### 5.4 Constraint & guardrail framework

Absent. Needs a declarative, **governed constraint config** (a versioned table):
rate-change caps, margin floors, competitive bounds, and the regulatory rules of
§6 — each applied in the engine and surfaced in the app with a pass/fail and the
binding constraint per segment.

### 5.5 Objective/config governance

The optimisation objective + constraints + model versions used should be a
**versioned, audited config** (same pattern as `rating_engine_config` /
`pricing_engine_releases`). This is a headline differentiator vs a black-box
optimiser: the "why" of every price is a governed, diffable artefact.

### 5.6 App page + narrative

Absent. New **"Price Optimisation"** page: objective + constraint selector;
demand curve + cost line + `p*` per segment; efficient frontier; portfolio impact
vs current book; what-if levers; and a **guardrail/regulatory panel** explaining
every constraint that bound. Reuse the existing page-explainer pattern and the
governance/audit chrome. Add a talk-track section.

### 5.7 Monitoring of optimisation outcomes

Partial. `shadow_pricing_impact` (kept as a proxy per v2 plan) can host a
before/after A-B of book vs optimised. A monitoring view of realised vs predicted
conversion/margin after a price move would complete the loop (can be phase 2).

---

## 6. Regulatory framing (must be explicit for a UK GI client)

If the client is **UK GI**, price optimisation is *regulated* and this must be
built into the demo, not bolted on:

- **FCA GI pricing rules (PS21/5, in force Jan 2022):** the renewal price for an
  existing customer must be **no higher** than the equivalent new-business price
  (the ban on "price walking"). A naïve retention-elasticity optimiser will *want*
  to walk prices — so the demo must show the **constraint enforced** and the
  optimiser respecting it.
- **Fair Value (PROD 4 / Consumer Duty):** price must reflect fair value; the
  governed objective/constraint config + audit trail is exactly the evidence a
  fair-value assessment needs.

This is a **strength**, not a caveat: the demo's punchline is that the platform
makes the optimiser *provably compliant* — every price move traceable to a
governed rule — which a closed vendor engine struggles to evidence. Confirm the
client's jurisdiction before committing to the FCA framing; the constraint
pattern generalises to other regulators.

---

## 7. Scope options & indicative effort (no build implied)

Effort is engineering-days for a demo on the v2 base; ranges, not commitments.

### MVP — new-business profit optimisation (~4–6 days)
1. Elasticity DGP in the v2 data generator + regenerate quotes (§5.1) — 1.5–2d.
2. Re-train + validate `demand_gbm` price response; segment elasticity diagnostic
   (§5.2) — 0.5–1d.
3. Optimisation engine notebook: segment-level profit-max, grid solve, one
   constraint (rate-change cap); efficient frontier (§5.3) — 1.5d.
4. One app page: demand/cost curves, `p*`, frontier, portfolio impact (§5.6) — 1.5d.

### Full — multi-objective + renewal + regulatory governance (~9–13 days)
Adds: `retention_churn` model + renewal price×retention optimisation (§5.2);
multi-objective with portfolio constraints (§5.3); the governed constraint/config
framework incl. FCA no-price-walking + fair-value (§5.4–5.5, §6); guardrail panel
+ monitoring A-B (§5.6–5.7); talk-track + docs.

The mature v2 app, governance rails, A/B framework and existing cost/demand
models are what keep this small — the real work is **the elasticity data fix + an
optimisation layer + one app page + the regulatory constraint framing**, not a
ground-up build.

---

## 8. Alignment with v2 conventions

- **Tier:** fits **Core** (batch/interactive, scale-to-zero, no online store).
  Could alternatively be gated behind a new `deploy_profile` value if we want it
  optional — decision for Laurence.
- **Naming:** single schema `pricing_workbench`, generic table names, no prefix;
  any workspace-global asset (a `pw_optimiser` job/endpoint) takes the `pw_`
  prefix per v2 plan §3.
- **Tags:** apply the uniform set (`project=pricing_workbench`, `owner`,
  `environment=demo`, `managed_by=dab`, `tier`, `contains_pii`) to every new
  asset.
- **Adjacency:** overlaps the backlog "drop a new dataset → portfolio what-if"
  item (v2_plan §8) — the raw-vector scorer both need is the same enabler; worth
  sequencing together.

---

## 9. Open decisions for Laurence

1. **Primary objective to lead with** — new-business conversion, or renewal
   retention? (Steers whether we build `retention_churn` first.)
2. **Jurisdiction** — is the client UK GI (→ make FCA no-price-walking + fair
   value a headline), or another market (→ generalise the constraint framing)?
3. **Core vs optional tier** for the optimisation assets.
4. **Fix the elasticity DGP globally?** It currently makes *every* demand-curve
   view flat, so fixing it improves the base demo too — but it touches the shared
   data generator. In-scope for this, or a separate data workstream?
5. **MVP first or straight to full** — do we want a fast, single-objective
   proof to put in front of the client, or the governed multi-objective version?

---

## 10. Risks & dependencies

- **Data realism (highest):** the whole demo lives or dies on a believable,
  segment-varying elasticity. Getting the DGP calibrated (sensible elasticities,
  not degenerate) is the main technical risk.
- **Regulatory correctness:** the FCA framing must be accurate; validate the
  no-price-walking constraint logic with an SME before it goes client-facing.
- **Scope creep into "we deliver models":** hold the line — this is a reference
  pattern the client owns, demonstrated on synthetic data.
- **Depends on** the v2 base being stable post-WS2 (naming/tags) and, for
  renewal, on a renewal/retention dataset that does not yet exist.

---

# Part 2: Gen2 canonical build spec (pricing-workbench-gen2 @ main)

> **Scope (decided 2026-08-25): personal MOTOR is the sole optimisation LOB.** A
> commercial-lines optimiser is explicitly **out of scope** — motor proves the capability
> end to end and a parallel commercial optimiser would duplicate the spine and put two
> demand-model concepts on screen. Where Part 1 was originally commercial-framed, read
> it as motor. `demand_gbm` stays the commercial quote-stream demand model, just not
> fronted by an optimiser. See `docs/DECISIONS.md`. Build status: Phases 1–3 shipped on
> motor; see `docs/optimisation_runbook.md`.

Status: built (Phases 1–3). Written against `wryszka/pricing-workbench-gen2` @ main. Follows gen2 conventions throughout: one schema, `opt_*` table prefix, `pwg2_` global-asset prefix, deploy-profile gating, Full Build orchestration, HITL patterns from the existing app. **This is the canonical spec — build from this, not from Part 1.**

---

## 0. Pre-work (before any module code)

- [x] **Remove the client name from `databricks.yml`** → "frozen v2 client deployment" (done 2026-08-19; also scrubbed app.pricingv2.yaml, docs/v2_plan.md; removed the AXA hand-off machinery scripts/make_handoff.sh + handoff/).
- [x] Remove/lock the internal Google Doc runbook link in README (public repo) — done. (App sidebar DemoDocCard still links it; make env-driven if the app repo is shared publicly.)
- [x] **Demand GBM resolved (2026-08-19):** it already IS the conversion model — a LightGBM binary classifier on `quotes.converted` (bound vs not), and the quote stream already carries the elasticity DGP (`vs_market_rate` → logit `bind_prob` → `converted`, plus `market_premium`). So there is NO two-demand-concept problem: the optimizer **promotes demand_gbm as its conversion model** (no rename). Block 02 only needs to (a) make **price an explicit lever with `monotone_constraints`** — today it uses `vs_market_rate` as a plain feature with no monotonicity — and (b) add a **retention model** once block 01 generates renewal events.

## 1. Purpose and positioning

Demonstrate **how** an insurer builds price optimisation on Databricks from scratch, and **what** the open platform enables that appliances cannot: open code end-to-end, elastic compute for exhaustive scenario exploration, first-class lineage over the full decision chain, and agentic automation with autonomy as a policy setting.

Not a competitor product. The client owns demand models, simulation, and governance; the execution layer is swappable. Risk model = the floor (cost); optimisation = shaping margin above the floor. The solver run is **always offline**; execution mode (table vs. endpoint) is a config flag.

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

- **Same bundle, same schema** (`pricing_workbench_gen2`). Optimisation tables prefixed `opt_*` (mirrors the `impact_*` convention).
- Source under `src/09_optimization/` (numbered after `08_governance/`).
- Job/pipeline definitions in `resources/optimization.yml`.
- Workspace-global assets prefixed `pwg2_` (e.g. `pwg2_optimization_run`, `pwg2_elasticity_scorer`).
- **Deploy gating:** extend `deploy_profile` → `core` | `full` | values gain an orthogonal flag `enable_optimization: "true" | "false"` (default `"false"` initially, flip to `"true"` when stable). Optimisation jobs are always defined, dormant unless enabled — same pattern as the live-serving tier.
- App: new sidebar page **Price Optimisation** in the existing React app; FastAPI router `src/app/.../optimization.py`. No second app, ever.

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

## 6. Constrained optimisation (block 04)

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

- **Price Optimisation** page: scenario comparison (trade-offs by segment), constraint-set version display, elasticity curves, approve → deploy.
- Reuses the existing HITL approval flow (External Data pattern) and app-SP job-trigger grants (`CAN_MANAGE_RUN` pattern already in the bundle).
- Genie demoed live against `opt_scenarios` via the existing Genie-space wiring (`app.pricingv2.yaml` env id, tab hidden until set).

## 10. Agentic loop — MCP-first (build requirement, day one)

Every capability exposed as a callable tool; app, notebook, and agent are all clients of the same surface. Follow the existing agent conventions — **NB gen2 uses passthrough auth, NOT the AGENT_TOKEN fallback** (the spec's token note is superseded by the gen2 no-PAT rework).

Tools (UC functions / Jobs triggers behind MCP endpoints; parameterized, idempotent, structured returns):
- `refresh_elasticity_models`, `run_simulation(grid)`, `run_solver(constraint_version)`, `deploy_factors`
- Read surfaces: elasticity curves, `opt_scenarios`, monitoring metrics, constraint versions, lineage
- `constraint_yaml` read/write with validation
- **Deployment gate as a tool with the corridor policy enforced server-side** — an agent cannot bypass it regardless of prompt.

Agents:
1. **Drift sentinel** — watches monitoring signals; raises a re-optimisation request with rationale.
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

- **One flow, no per-part smoke tests.** Optimisation tasks append to the **Full Build** orchestrator in dependency order, gated by `enable_optimization`: data-gen deltas → elasticity training → simulation → solve → factor promotion → monitoring backfill → app grants.
- Demo walks the DAG as a single story: *data → behaviour → what-if → decision under constraints → reality check → human approval.* Notebooks are narrative stops, not standalone tests.
- Internal build order: data-gen changes → elasticity (incl. Demand GBM resolution) → simulation → solver+constraints → app page → monitoring → MCP tools → agents → real-time addendum.

## 13. Forward hook — FiDA (do not build yet)

Open-finance (FiDA) data enters as one more external dataset through the standard External Data HITL flow, feeding the elasticity/underwriting feature set — **through the fairness gate**. One future slide, zero current code.

## 14. Anticipated challenges

| Challenge | Answer |
|---|---|
| "This is only batch; real-time is the hard part" | Optimisation is offline everywhere; execution mode is a flag — here's the live endpoint. |
| "Your optimiser is weaker than proprietary" | Correct, and not the question. Most uplift sits in the first ~80% of sophistication; captured uplift vs. retained licence cost is testable via a shadow-mode pilot on one product line. |
| "How is this governed?" | Open the lineage graph and the constraint YAML history — live, in the room. |
| "Is agent-driven pricing safe?" | Agents never set prices; a deterministic solver does, under versioned constraints, behind a server-side gate agents cannot bypass. |

# Price Optimisation — runbook (Phase 1: offline spine, motor)

What shipped, how to run it, and how to demo it. This is the **offline spine** on
personal **motor** — the phase-1 scope of `docs/optimization_spec.md`, built with
the naming/placement decisions in `docs/OPTIMIZATION_RECONCILIATION.md`
(British `optimisation_*` evolved in place; MCP/agents, real-time serving, and the
closed-loop generator are deferred to phases 2–3).

## The message (three beats)
1. **This is what we need** — quote-response and renewal data. It flows through the
   standard pipeline; the only question is whether lost quotes are kept.
2. **This is what we do with it** — model demand (monotone, price ÷ technical),
   simulate the book, decide under versioned constraints, deploy behind a gate,
   monitor. One governed loop, open code, in your workspace.
3. **These are the results** — an efficient frontier, a per-segment factor table,
   an audit trail from raw quote to deployed rate.

## What runs (the DAG)

`optimisation_full` chains five serverless jobs (all in `resources/optimisation.yml`):

| Block | Job / notebook | Writes |
|---|---|---|
| §3 data | `optimisation_data` · `optimisation_motor_data.py` | `optimisation_quote_response`, `optimisation_renewal_response`, `optimisation_portfolio_snapshot` |
| §4 elasticity | `optimisation_elasticity` · `optimisation_elasticity.py` | models `conversion_elasticity_motor`, `retention_elasticity_motor` (@champion); `optimisation_elasticity_curve`; red-team `optimisation_redteam_endogeneity`, `optimisation_param_recovery` |
| §5 simulation | `optimisation_simulation` · `optimisation_simulation.py` | `optimisation_scenarios` (+ Pareto flag), `optimisation_scenario_segments` |
| §6 solver | `optimisation_solver` · `optimisation_solver.py` | `optimisation_factor_table` (bound by the constraint YAML) + an `audit_log` row |
| §8 monitoring | `optimisation_monitoring` · `optimisation_monitoring.py` | `optimisation_monitoring`, `optimisation_deviation_dist`, `optimisation_constraint_breaches` |

The HITL deploy (`POST /api/optimisation/deploy`) writes `optimisation_deployment`
and an `audit_log` row after re-checking the corridor **server-side**.

## Key design decisions (defensible on screen)

- **Price never enters raw.** Demand is modelled on **price ÷ technical price**
  (`vs_technical`) and market position (`vs_market`). Raw price is endogenous to
  risk (expensive risks cost more *and* command a higher market benchmark), so a
  raw-price model reports demand as nearly price-insensitive — the "wrong-model"
  red-team panel quantifies exactly this trap.
- **"Technical price" = break-even (loaded) price**, i.e. pure risk cost
  (`freq_glm_motor × sev_glm_motor`) **plus** expense + commission loadings. A real
  charged premium sits ~1.0× this, so the ±15% deviation corridor is coherent. The
  **pure risk cost is the margin floor** for the profit objective.
- **Monotonicity enforced.** The LightGBM conversion/retention models carry
  `monotone_constraints` so conversion can only fall as price rises — the solver
  can't exploit a spurious non-monotone wrinkle.
- **The constraint set IS the pricing policy** — `optimisation_constraints/default.yaml`,
  versioned in the repo. The solver is bound by it; its git history is the audit
  trail. Jurisdiction toggle (`elasticity_may_contribute`) makes the same engine
  legal in a cost-based US state (holds to technical) vs the UK (shapes margin).
- **The deploy gate holds server-side.** `/deploy` re-validates every factor
  against the corridor before stamping — a future agent cannot talk its way past it.

## How to run

**As part of Full Build (§12-gated).** On `pricingv2` the gate is on by default;
elsewhere pass the flag:
```bash
databricks bundle run full_build -t <target> --params enable_optimization=true
```
The `optimisation` task runs only when `enable_optimization=true`; otherwise the
jobs stay defined but dormant (same spirit as the live-serving tier).

**Standalone (re-run the spine any time):**
```bash
databricks bundle run optimisation_full -t pricingv2                 # whole DAG
databricks bundle run optimisation_solver -t pricingv2 \             # just re-solve
   --params objective=expected_gwp
```

**From the app.** The Optimiser tab's *Re-solve (live job)* button triggers
`optimisation_full` with the chosen objective + grid size and polls to completion —
a real governed run, not a client-side illusion.

## App surfaces (`/optimisation`)

- **Optimiser** — objective front door, portfolio roll-up KPIs, efficient frontier,
  per-segment waterfall, the solved factor table, and the **approve → deploy** gate.
- **Demand & red-team** — per-segment elasticity curves; the endogeneity (wrong-model)
  panel; the parameter-recovery panel.
- **Monitoring** — conversion drift over the rolling months, deviation-from-technical
  distribution, and the corridor/GIPP breach tile.
- **How it works** — the governed loop, the live constraint YAML, deep-links to every
  table / model / job / agent, and the data/model/platform explainer.

## Positioning (say this first)

This is a **module of the pricing workbench, not a separate programme.** It inherits the same
governed machinery — the risk champions, the feature store, the audit log, the agent framework, the
Genie/MCP surface — and adds one value chain on top: demand → simulate → decide-under-policy →
deploy → monitor. **It's an increment, not a rebuild.** The message to a buyer: *"you already have
the foundation; this is the pricing department switched on."*

## Talk track — the three acts + the two-gear line

- **Act 1 (BAU loop)** and **Act 2 (aggregator squeeze)** are the ~6-min core (below / Aggregator tab).
- **Act 3 (heavy mode)** is the **third act, and only after the minute-twenty mark** — never lead with it.
  Run it once the room believes the governed loop is real. The line:
  > *"The default optimiser is deliberately light — smart when you can. But when it matters, the same
  > platform runs the whole book per policy, under an ensemble of your candidate models, for the full
  > risk distribution. **Smart when you can, exhaustive when it matters — the appliance has one gear.**"*
  Show the **measured** caption (row count, wall-clock, est. cost — captured from the actual run, never a
  claim) and the uncertainty-banded frontier + disagreement map.
- **Leave-behind question** (hand this to the room as they go): *"Ask your current vendor to show you
  the distribution of outcomes across your candidate demand models — not a point estimate, the
  distribution."*

*(Never say "brute force". The two gears are "light/smart" and "exhaustive".)*

## Talk-track (motor, ~6 min)

1. *"Here's the book."* Optimiser KPIs — GWP, expected profit at today's prices.
2. *"Model demand honestly."* Demand tab: monotone curve; then the wrong-model panel —
   raw price hides the elasticity; that's the appliance's black box.
3. *"Explore N futures."* Set N = 10,000, re-solve — watch the frontier fill; N is a
   choice, not a licence tier.
4. *"Decide under policy."* Open the constraint YAML; note the U25 override and the
   jurisdiction toggle. The waterfall shows the solver raising standard risks to the
   cap and *cutting* price for shop-happy young drivers.
5. *"Reality check."* Monitoring: drift is small and moving; GIPP holds.
6. *"Human sets the policy; the gate enforces it."* Approve → deploy; the corridor is
   re-checked server-side and the deploy is audited.

## Phase 2–3 (now BUILT — 2026-08-25)
- **Closed loop (§3 tail, Principle 6):** `optimisation_advance_month` job + `/advance`
  endpoint + Monitoring "Advance one month" button — rolls the book forward under the
  deployed prices, writes predicted-vs-realized, appends the month to monitoring + the
  quote stream. Verified: predicted £8.79m → realized £8.77m (−0.2%).
- **Real-time serving (§7B):** `pwg2_elasticity_scorer` — defined-but-dormant, arm/teardown
  jobs (`src/07_serving/optimisation_elasticity_serve/`), scale-to-zero.
- **MCP surface (§8/§10):** 10 `opt_*` tools on the JSON-RPC MCP server (stages + reads;
  `opt_deploy_factors` stays server-side gated). App, notebook and agent share one surface.
- **Fairness / fair-value (§11):** `optimisation_fairness` job → proxy-correlation /
  disparate-impact / vulnerability evidence + pack; chained into `optimisation_full`;
  `/fairness` endpoint + Monitoring panel.
- **Agent bench (§10):** four LLM personas on the managed `pwg2_chat_agent` framework over
  the MCP/tables — `constraint_author`, `drift_sentinel`, `planner`, `recommender`. The
  other spec roles are deterministic components already present: execution = the
  `optimisation_full` DAG, gate = the server-side deploy gate, fairness reviewer = the
  fairness job, interrogator = Genie.
- **Reactive second act (§14):** the "Aggregator squeeze" Walkthrough tab drives it end to
  end — detect → plan → re-solve → recommend → gate → deploy → did-it-work.

**Out of scope (decided 2026-08-25):** a commercial-lines optimiser is **not** being
built — personal **motor** is the sole optimisation LOB and is sufficient to prove the
capability. See `docs/DECISIONS.md`.
**Still deferred:** FiDA (§17, one slide, forward hook only).

## Open gate
**GATE-1 lineage edge** — technical premium is champion-*scored* (Block 1 loads the
real `freq_glm_motor × sev_glm_motor` champions), but the inner-artifact load doesn't
emit a UC `model version → table` lineage edge. Champion scoring ✓; lineage edge open.

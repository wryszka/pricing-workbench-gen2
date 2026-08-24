# Optimization Module — Spec ↔ Reality Reconciliation

Reconciles `OPTIMIZATION_MODULE_SPEC.md` (intent) against `OPTIMIZATION_INVENTORY.md`
(reality, verified live 2026-08-24). Purpose: decide what to reuse, recover, rework,
or build new — and surface the decisions that gate the build.

## ⛔ OPEN GATES (pre-work / hygiene — must close before external demo)

- **GATE-1 · technical_premium must be champion-scored.** Status: **PARTIAL —
  champion-scored ✓, lineage-edge OPEN** (2026-08-24). Scoring now uses the real
  `freq_glm_motor × sev_glm_motor` champions (default `technical_source=champion`,
  mean £654) via inner-model load on the driver (rung c). Remaining: UC lineage
  shows no `champion model version → technical_premium` edge (the inner-artifact
  load bypasses mlflow model-load lineage). Full close needs `mlflow.pyfunc`
  model loading to work (it threw the FE-wrapper load error) or a lineage-emitting
  score path. See docs/OPTIMIZATION_INVENTORY.md for the escalation record.

## Verdict up front

The spec is, structurally, **the `09_optimization` module that was built and then deleted**
in commit `a406749`. Its full tree still exists in git at `dcfafcb`:
`01_optimization_data.py, 02_elasticity.py, 03_simulation.py, 04_solver.py, 05_monitoring.py,
constraints/default.yaml` — plus `resources/optimization.yml`, `/api/optimization` router, and the
`opt_*` tables. **But the deleted module was COMMERCIAL, used elasticity vs. MARKET price, and
LightGBM `pwg2_conversion/retention_elasticity` models.** The new spec changes the three things that
matter most: **(a) line of business → personal MOTOR, (b) price enters as ratio/deviation vs.
TECHNICAL price, (c) one consolidated demand model + a closed-loop generator.** So the deleted code
is a reusable *scaffold for blocks 03/04/05*, not a drop-in answer.

**Coverage estimate:** ~20–30% of the spec is covered by reusable-live + recoverable-from-git assets;
the rest is net-new or substantial rework. What runs live today is a **commercial** worked example
(sklearn logistic on vs-market), which the spec supersedes.

## Cross-cutting conflicts (must resolve before building)

1. **LOB conflict — commercial (live) vs motor (spec).** Today `/optimisation` = commercial
   worked-example (`optimisation_*` tables, `price_optimiser.py`, Optimiser + Walkthrough +
   How-it-works). Spec §1/§3 mandate **motor** as optimization's home, commercial as "surrounding
   demo." Decision: does the motor module **replace** the commercial `/optimisation` surface, or
   **coexist** beside it? (The commercial worked-example is genuinely nice — frontier chart, live
   job, monitoring — but the spec doesn't want two demand-model concepts on screen.)
2. **Naming conflict — `opt_*` (spec) vs `optimisation_*` (live).** Spec §2 mandates `opt_*` tables,
   `src/09_optimization/`, `/api/optimization`, `enable_optimization` flag — i.e. re-introduce
   exactly the names removed in `a406749`, now alongside the surviving `optimisation_*`. Either
   rename the live worked-example out of the way or accept both prefixes transiently.
3. **Demand-model conflict — three concepts today, spec wants one.** Live: `demand_gbm` (commercial,
   vs-market), `demand_gbm_motor` (motor, raw `current_premium`), plus the optimiser's own logistic.
   None uses **price-relative-to-technical-price**. Spec §0/§4 require consolidation to a single
   conversion model on the technical-price formulation. This is a **retrain + rewire**, not a rename.
4. **Data conflict — motor has no quote-response/renewal/closed-loop data.** The commercial quote
   stream has price variation + bound/lost but **no renewal, not closed-loop**. Motor
   (`setup_motor.py`) has policies/telematics/claims and a *train-time synthetic* acceptance label —
   **no stored `opt_quote_response`, no renewal events, no injected price variation, no closed loop.**
   Spec §3 is the single biggest build item and it lands on the motor generator.

## Section-by-section

Status: **REUSE** (live, usable) · **RECOVER** (deleted, in git @dcfafcb) · **PARTIAL** (exists,
needs rework) · **NEW** (net-new) · **CONFLICT** (diverges from current) · **MOOT** (already done/NA).

| Spec § | Status | Reality / action |
|---|---|---|
| **0.1** remove AXA from databricks.yml | MOOT | No "AXA" in gen2 `databricks.yml` (already neutral). |
| **0.2** internal Google-Doc link | PARTIAL | Not in README. Lives in **uncommitted** `RatingEngineIntegration.tsx` (`ACTUARIAL_SW_INTEGRATIONS_DOC`). Lock down / drop before it's committed. |
| **0.3** resolve the Demand GBM | CONFLICT | See cross-cutting #3. Three demand concepts live; must consolidate on technical-price formulation. |
| **1** purpose/positioning (motor) | CONFLICT | Live optimiser is commercial. Motor is the target habitat; commercial becomes surrounding demo. |
| **2** placement (`src/09_optimization`, `opt_*`, `resources/optimization.yml`, `enable_optimization`) | RECOVER + CONFLICT | Exact paths/names existed and were deleted (`a406749`). Recoverable from `dcfafcb`; conflicts with live `optimisation_*` naming (cross-cutting #2). |
| **3** data (outcome labelling, renewal, price variation, elasticity drift, **closed loop**, `pwg2_advance_month`) | NEW (mostly) | Commercial stream has price-var + bound/lost only. Motor has none of the quote-response/renewal/closed-loop machinery. `opt_quote_response`/`opt_renewal_response`/`opt_portfolio_snapshot` existed for **commercial** at `dcfafcb` (RECOVER as templates); motor versions + closed-loop + advance-month are NEW. Biggest lift. |
| **4** elasticity models (price vs **technical** price, market-position feats, monotone, Demand-GBM-as-conversion) | RECOVER-scaffold + NEW | `02_elasticity.py` (RECOVER) trained monotone LightGBM but on **vs-market**; must be reworked to **vs-technical-price** and consolidated with `demand_gbm`. Retention analogue NEW for motor. |
| **5** simulation (`opt_scenarios`, grid param) | RECOVER | `03_simulation.py` @dcfafcb is scale-free curve+aggregate; adaptable to motor. |
| **6** solver + **constraints YAML** (corridor, GIPP, caps, forbidden signals, jurisdiction toggle) | RECOVER | `04_solver.py` + `constraints/default.yaml` @dcfafcb (scipy, corridor/GIPP/caps) — directly reusable, retarget to motor factor cells. |
| **7** serving (A: online store; B: `pwg2_elasticity_scorer`) | PARTIAL + NEW | Online store `pwg2-pricing-online-store` is **defined but dormant** (core runs "no online store"); Pattern A needs it armed (spec's "zero new infra" is optimistic). Pattern B endpoint NEW. |
| **8** monitoring (`opt_conversion_actuals`, drift, breaches, deviation dist) | PARTIAL + RECOVER | Live `optimisation_monitoring` = actual-vs-expected drift (commercial). `05_monitoring.py` @dcfafcb had `opt_conversion_actuals`/`opt_deviation_dist`/`opt_constraint_breaches` (RECOVER). Neither is closed-loop-driven yet; no GIPP tile. |
| **9** app page (objective front door, **efficient frontier**, **waterfall**, constraint version, approve→deploy HITL) | PARTIAL | Frontier chart EXISTS (worked-example). Objective-capture form, segment waterfall, constraint-author agent, and **approve→deploy HITL gate** are NEW. Current Walkthrough triggers the job with **no approval gate**. |
| **10** MCP-first + 8 agents (drift sentinel, planner, execution, interrogator, fairness, recommender, gate, constraint-author) | NEW | None exist for optimization. General `mcp.py` router + agent framework + `rate_change` persona exist as patterns to build on. Server-side corridor-enforced deploy gate is NEW. |
| **11** governance (full lineage, fairness apparatus, GIPP/Consumer-Duty/EIOPA/GDPR framing) | PARTIAL | UC lineage exists; constraint YAML history (RECOVER). Fairness/vulnerability screens + fair-value evidence export into the regulatory path are NEW. |
| **12** orchestration (append to Full Build, gated by `enable_optimization`) | RECOVER-pattern | `opt_full` orchestrator + gating existed @dcfafcb (never auto-gated into full_build — was standalone). Re-add, this time actually chained + flag-gated. |
| **13** red-team artifacts (How-it-works **deep-links**, wrong-model panel, parameter-recovery, GIPP tile, grid+wallclock) | PARTIAL | **How-it-works tab + live deep-links already shipped** (commercial). Wrong-model challenger, parameter-recovery overlay, GIPP tile, grid+wallclock counters are NEW. |
| **14** walkthrough (CUO +2pts, 8 beats, aggregator-squeeze act) | PARTIAL | A Walkthrough tab exists but tells a different (commercial competitor-SME) story with no HITL/agents. Rework to the motor CUO script + agentic second act. |
| **15** docs (talk_track, runbook, data_dictionary, README, about_demo) | PARTIAL | `docs/talk_track.md`, `docs/data_dictionary.md`, `docs/about_demo.md` exist (need optimization sections). `docs/optimization_runbook.md` NEW. Also stale: `docs/optimisation_demo_spec.md`, `docs/optimization_spec.md` (older specs — supersede/retire). |
| **16** anticipated challenges | REUSE-into-docs | Feed verbatim into talk_track Q&A. |
| **17** FiDA hook | MOOT | Do not build. One slide. |

## Recoverable-from-git cheat sheet
```
git show dcfafcb:src/09_optimization/01_optimization_data.py   # opt_quote_response / _renewal_response / _portfolio_snapshot (COMMERCIAL)
git show dcfafcb:src/09_optimization/02_elasticity.py          # monotone LightGBM, VS-MARKET (rework → vs-technical)
git show dcfafcb:src/09_optimization/03_simulation.py          # scale-free grid → opt_scenarios
git show dcfafcb:src/09_optimization/04_solver.py              # scipy, corridor/GIPP/caps → opt_factor_table
git show dcfafcb:src/09_optimization/05_monitoring.py          # opt_conversion_actuals / _deviation_dist / _constraint_breaches
git show dcfafcb:src/09_optimization/constraints/default.yaml  # versioned constraint set
git show dcfafcb:resources/optimization.yml                    # opt_data/elasticity/simulate/solve/monitor + opt_full
git show dcfafcb:src/app/server/routes/optimization.py         # /api/optimization surface
```
These are a **commercial, vs-market** scaffold. Value = structure (sim/solver/constraints/monitoring),
not the modelling formulation the new spec requires.

## Decisions that gate the build (user's call)
- **D1 — commercial worked-example disposition:** replace `/optimisation` with the motor module, or
  keep the commercial one as a second surface?
- **D2 — naming:** adopt spec `opt_*` / `src/09_optimization` / `/api/optimization` (re-adding the
  removed names beside live `optimisation_*`), or evolve the live `optimisation_*` naming in place?
- **D3 — scaffold source:** resurrect blocks 03/04/05 + constraints from `dcfafcb` and rework for
  motor+technical-price, or build fresh? (Recommendation: resurrect 03/04/05/constraints as scaffold;
  build 01/02 fresh for motor + technical-price.)
- **D4 — first-PR scope:** the spec is 17 sections. Recommended Phase 1 = the **offline spine on
  motor**: data-gen (§3) → elasticity vs-technical (§4) → simulation (§5) → solver+constraints (§6)
  → app frontier+waterfall+objective front door+**HITL gate** (§9) → monitoring (§8), all gated by
  `enable_optimization`, with the wrong-model + parameter-recovery + GIPP red-team artifacts (§13).
  **Defer to later phases:** MCP tools + 8 agents (§10), real-time `pwg2_elasticity_scorer` (§7B),
  closed-loop `pwg2_advance_month` (§3 tail), agentic aggregator-squeeze act (§14), FiDA (§17).

## Proposed phased build order (follows spec §12 internal order)
1. **Phase 1 — offline spine (motor):** §3 data-gen (outcome labelling + renewal + injected price
   variation; closed-loop deferred) → §4 elasticity (technical-price, monotone, Demand-GBM
   consolidation) → §5 simulation → §6 solver + constraints YAML → §8 monitoring → §9 app
   (objective front door, frontier, waterfall, approve→deploy HITL) → §13 red-team panels → §12
   Full Build gating → §15 docs for shipped surfaces.
2. **Phase 2 — closed loop + real-time:** §3 closed-loop generator + `pwg2_advance_month` → §7B
   `pwg2_elasticity_scorer` + flag flip → §8 monitoring moves over rolling months.
3. **Phase 3 — agentic:** §10 MCP tool surface + the 8 agents + server-side gate → §14 aggregator
   -squeeze second act → §11 fairness/evidence automation.

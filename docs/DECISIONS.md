# Decisions

Dated, reverse-chronological decision log for pricing-workbench-gen2. Self-contained
narratives with a verification note each. Shared **gotchas** at the bottom (once-bitten
failure modes). See also `docs/OPTIMIZATION_RECONCILIATION.md` (spec↔reality) and
`docs/optimisation_runbook.md` (current-state optimiser doc).

---

## 2026-08-25 — Commercial-lines optimiser: NO-GO (motor is the sole LOB)

A commercial-lines optimiser (wiring the governed `demand_gbm` into a second optimisation
surface, mirroring the motor spine) was on the pipeline as a possible Phase-2 expansion. It
is **ruled out**. Personal **motor** is the demo's optimisation habitat and is sufficient to
prove the capability end to end (data → monotone elasticity → simulation → constrained
solver → monitoring → HITL → closed loop → agents → fair value). A parallel commercial
optimiser would be a large net-new surface that largely duplicates the motor spine and
re-introduces a second demand-model concept on screen — which the spec explicitly warns
against. Removed from the specs/roadmap; `demand_gbm` remains the commercial *quote-stream*
demand model (unchanged), just not fronted by an optimiser.

## 2026-08-25 — Price Optimisation: Phase-1 offline spine on motor

- **Replace, don't coexist (D1).** The commercial worked-example optimiser
  (`price_optimiser.py` + `optimisation_summary/curve/config` tables) was removed and
  replaced by the spec-conformant motor spine. Two demand-model concepts on screen was
  a clarity cost the spec explicitly warns against.
- **Evolve `optimisation_*` naming in place (D2)** rather than re-introducing the spec's
  `opt_*` / `src/09_optimization/` / `/api/optimization`. Keeps British spelling + the
  existing app route stable.
- **Offline-spine-first (D4).** Phase 1 = data → elasticity → simulation → solver →
  monitoring → app (frontier/waterfall/objective/HITL) → red-team → §12 gating → docs.
  Deferred to phases 2–3: MCP + the 8 agents (§10), real-time `pwg2_elasticity_scorer`
  (§7B), closed-loop `pwg2_advance_month` (§3 tail / Principle 6 feedback beat), FiDA.
- **"Technical price" = break-even (loaded) price, not pure risk cost.** Price enters the
  demand model as `offered ÷ loaded` (deviation from the technically-correct price); the
  pure `freq_glm_motor × sev_glm_motor` cost is the **margin floor**. Without this a real
  premium reads ~37% above "technical" and the ±15% corridor is incoherent. *Verified:*
  hold £7.95m → opt £8.79m (+£837k, +10.5%), all segments within corridor.
- **`mlflow.lightgbm`, not `mlflow.sklearn`, for the elasticity models.** Newer MLflow
  serialises sklearn models via skops, which rejects LightGBM's Booster as an untrusted
  type. *Verified:* both models register + alias @champion and load on the driver.
- **§12 gating via `condition_task` + `enable_optimization` job parameter.** The spine is
  chained into `full_build` but dormant unless `enable_optimization=true` (="true" on
  pricingv2). *Verified:* `bundle validate` + a gated `full_build` run.
- **HITL deploy writeback is governed, least-privilege.** `/api/optimisation/deploy`
  re-checks the corridor **server-side**, then writes `optimisation_deployment` + an
  `audit_log` row. The app SP was granted `MODIFY` on exactly those two tables (in
  `grant_app_sp.py`); the deployment table is pre-created by the solver so the SP never
  needs `CREATE`. *Verified:* live POST wrote both rows; smoke rows cleaned.
- **GATE-1 (OPEN, roadmapped).** Technical premium is champion-*scored* (inner-artifact
  load on the driver — rung c), but the load bypasses MLflow's model-load lineage, so
  there is no UC `model version → technical_premium` edge. Scoring ✓; lineage edge open.

## 2026-08-25 — 6-agent review panel (Phase-1 promotion)

Ran the playbook's 6-agent fan-out on both the legacy workbench and the optimiser; reports
in `docs/REVIEW/`. Verdict: **SHIP WITH ROADMAPPED GAPS** for both. One blocker found and
fixed: the deploy endpoint's audit `details` JSON was built by string interpolation of the
free-text `note` (a double-quote corrupted the JSON) — now built via `json.dumps` with all
interpolated values SQL-escaped. Re-solve button switched to solver-only (~1 min) for live
rooms. Doc gaps (this file, `STANDARDS.md`, tier declaration) closed; run-sheet/QA in house
format remain roadmapped.

---

## Gotchas (once bitten)

- **Serverless `fe.score_batch` signature typing** — casting int→double clears the
  signature error but the FE-wrapped model then fails to load inside the distributed UDF.
  Batch stamping of technical premium instead loads the inner sklearn flavor on the driver
  (`download_artifacts` → deepest `MLmodel` → `mlflow.sklearn.load_model`). Trade-off:
  no model→table lineage edge (GATE-1).
- **`mlflow.sklearn.log_model` on a LightGBM model** → "untrusted types" (skops). Use
  `mlflow.lightgbm`.
- **Stale `current_premium`** in the synthetic motor book sits ~20% below pure risk cost;
  never use it as the optimisation price basis (use `loaded_premium`). It made the book
  look loss-making and renewals look like 91% corridor breaches until switched.
- **SQL built by f-string** across the app — every interpolated value must be
  single-quote-escaped, and any embedded JSON must be `json.dumps`-built (a raw double
  quote breaks the JSON literal). Parameterised queries are the roadmapped hardening.
- **App SP is SELECT/EXECUTE only by default** — governed writeback (e.g. the deploy
  ledger) needs an explicit `MODIFY` grant on the specific table in `grant_app_sp.py`.

# Review report — Price Optimisation (motor offline spine, Phase 1)

> Standardized output of the 6-agent review panel (bricksurance-playbook `BUILD_AND_REVIEW.md` §7), run fan-out (all six personas in parallel) and collated here.

- **Demo:** pricing-workbench-gen2 · `/optimisation` surface · `wryszka/pricing-workbench-gen2` @ main
- **Reviewed:** 2026-08-25 · live on pricingv2, data as of today
- **Verdict:** **SHIP WITH ROADMAPPED GAPS** — one blocker found and **fixed**; remaining gaps are labelled + roadmapped.
- **Scorecard (§6):** P0 — all pass. P1 — closed-loop feedback beat (§E) + MCP/agents (§D) deferred to phases 2–3 (labelled). GATE-1 lineage edge open (documented).

**Severity:** `blocker` · `major` · `minor` · `nit`. **Status:** `fixed` · `roadmapped` · `wontfix` · `open`.

---

## 1 · Practitioner (pricing actuary)
*Real and right in my world? Value vs Radar/Earnix? Deal-breakers?*

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Monotonicity enforced end-to-end (LightGBM `monotone_constraints`); endogeneity panel shows why raw price would hide it — defensible under drill-down. | — (strength) | — |
| 2 | Price enters as ratio to technical, never raw; `vs_technical` / `vs_market`. Correct answer to the endogeneity kill-shot. | — (strength) | — |
| 3 | Versioned constraint YAML + server-side HITL gate = the wedge against a black-box optimiser. | — (strength) | — |
| 4 | Motor-only in Phase 1 (commercial deferred) — fair, but should be one-line labelled in the talk-track. | minor | roadmapped |
| 5 | GATE-1 lineage edge open — champion *scoring* works; add a one-line "lineage note" on the How-it-works tab. | minor | roadmapped |

**Deal-breakers:** none. **Value story:** enrich/wrap/replace all clearly shown (open code + governed constraints + audit vs a closed optimiser). **Verdict:** SHIP.

## 2 · Decision-maker (CFO / CRO)
*Does the money and the story land?*

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Uplift numbers are model-derived (elasticity × simulated book), not hardcoded; red-team panels validate the DGP. | — (strength) | — |
| 2 | Add an "assumptions & sensitivity" line (base elasticity, "if elasticity halves → £Z") + the explicit Earnix contrast. | major | roadmapped |
| 3 | Regulatory framing (GIPP / Consumer Duty / fair-value evidence) is infra-ready but not *presented* — add a How-it-works bullet; full pack is Phase 2. | major | roadmapped |
| 4 | Open on risk-of-inaction (vendor lock-in, per-seat cost, no audit) rather than the capability — re-messaging, not code. | major | roadmapped |
| 5 | Solver constraints versioned + audited; every solve writes an audit row — the headline CFO story. | — (strength) | — |

**Verdict:** SHIP (Phase 1); narrative coaching + sensitivity line before a CFO room.

## 3 · Databricks SA (demoability)
*Easy and reliable to demo — timings, fallbacks, reset, yellow-button cache?*

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | "Re-solve (live job)" originally triggered the whole DAG (incl. slow data-gen) live — a live-room timing risk. | major | **fixed** — button now runs solver-only (~1 min); full rebuild is the offline `optimisation_full` job. |
| 2 | Closed-loop "did it work" feedback beat (`advance_period`) not implemented. | major | roadmapped (Phase 2) |
| 3 | Page degrades gracefully when tables empty; run-now + poll + spinner all wired; deep-links env-driven. | — (strength) | — |
| 4 | Confirm the rate-change agent's responses sit behind the yellow live/cached toggle; note in run-sheet. | minor | roadmapped |
| 5 | For a fast live run use `grid_points=1000`, and keep a pre-solved frontier screenshot as fallback. | nit | roadmapped (run-sheet) |

**Verdict:** SHIP WITH ROADMAPPED GAPS — all P0 pass; the offline spine is razor-sharp.

## 4 · Senior developer (correctness & robustness)

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | `/deploy` built the audit `details` JSON by string-interpolating the free-text `note` (single-quote escaped only) — a double-quote in `note` corrupts the JSON / audit integrity. | **blocker** | **fixed** — `details` now built with `json.dumps`; all interpolated values (incl. `cver`) SQL-escaped. |
| 2 | `_coerce()` swallows `TypeError/ValueError` silently; downstream arithmetic assumes numerics. | major | roadmapped (log/validate coercion) |
| 3 | `np.interp` could extrapolate outside the elasticity-curve grid → conv <0/>1. In practice solver bounds ⊆ grid domain, so no extrapolation today; clip is cheap insurance. | major→minor | roadmapped (clip conv to [0,1]) |
| 4 | Post-coercion numeric validation before roll-up arithmetic. | major | roadmapped |
| 5 | Divide-by-zero on hold profit in `summary()`. | minor | no_change_needed — already guarded (`if hold else None`). |
| 6 | Client run-poll loop could poll forever if a job hangs. | minor | **fixed** — poll capped at ~80 (≈7 min) then TIMEOUT. |
| 7 | Simulation loss-ratio guards zero but not NaN/negative. | minor | roadmapped |

**Verdict:** SHIP WITH ROADMAPPED GAPS — blocker fixed; remaining items are defensive edge-cases (happy path solid).

## 5 · Security

| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | `/deploy` JSON-in-SQL injection via `note` (corrupts audit JSON; stays within the SQL string so no exfiltration). | major | **fixed** (same fix as Senior-dev #1). |
| 2 | `constraint_version` (from table) interpolated into the deploy INSERTs unescaped. | minor | **fixed** — now SQL-escaped. |
| 3 | No RBAC on `/deploy` beyond the corridor gate (any app user can approve). | minor | roadmapped (gate on ADMIN_USERS / UC grant). |

**Cross-cutting (clean):** no secrets in code/history; app SP least-privilege (SELECT/EXECUTE + MODIFY on exactly two tables); no external data egress; auth delegated to Databricks Apps.

**Verdict:** SHIP WITH ROADMAPPED GAPS — the one exploitable item is fixed.

## 6 · Current-Databricks expert (up to date)

| # | Finding | Severity | Status | Doc checked |
|---|---|---|---|---|
| 1 | `mlflow.lightgbm.log_model` + UC registry + `@champion` alias + `infer_signature` — all current; correct flavor vs skops. | — (strength) | — | MLflow flavors/registry |
| 2 | `monotone_constraints`, scipy solver, pyyaml constraints — current, no deprecated APIs. | — (strength) | — | LightGBM / MLflow |
| 3 | Inner-artifact champion load is an acceptable, documented workaround; revisit `fe.score_batch` if the FE signature reconciles (also closes GATE-1). | minor | roadmapped | Feature Engineering |
| 4 | Confirm serverless env `client: "5"` and Jobs API 2.1 are still current (no deprecation found). | nit | open (verify) | serverless env / Jobs API |

**Docs swept:** MLflow (flavors, registry, aliases), Feature Engineering, serverless env spec, Jobs API 2.1, LightGBM monotone constraints — as of 2026-08-25. **Verdict:** SHIP.

---

## Applied fixes (summary)
- **[blocker] `/deploy` audit JSON** — build `details` via `json.dumps`; SQL-escape `note`, `approver`, `cver`. (`routes/optimisation.py`)
- **[major] Re-solve timing** — solver-only re-solve (~1 min) instead of the full DAG, for live rooms. (`PriceOptimisation.tsx`)
- **[minor] Client poll** — capped at ~80 polls with a TIMEOUT state.
- **Docs** — `STANDARDS.md` (tier 2 declared), `docs/DECISIONS.md` (incl. gotchas) added.

## Open / roadmapped
- **Phase 2 (now BUILT):** closed-loop `advance_month` feedback beat; MCP tool surface + agent bench; real-time `pwg2_elasticity_scorer`; fair-value evidence pack. *(A commercial-lines optimiser was considered and ruled OUT on 2026-08-25 — motor is the sole LOB; see `docs/DECISIONS.md`.)*
- **GATE-1** lineage edge (model→table) — champion scoring works; lineage edge open.
- **Hardening:** parameterised SQL across the app; RBAC on `/deploy`; coercion/interp guards; `DEMO_RUNSHEET.md` + `DEMO_QA.md` in house format; verify serverless client "5".
- **Narrative:** sensitivity line + explicit incumbent contrast + risk-of-inaction opening.

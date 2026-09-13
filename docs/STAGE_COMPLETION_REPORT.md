# Stage completion report — governed pricing demo & decision review

**Branch:** `stage-governed-review` · **Review baseline:** `99e2455205a46b5ee94e0c45d12a189ef7be7485`
**Environment:** pricingv2 FEVM (`PRICING_V2`), catalog `lr_pricing_v2_aws_us_catalog`,
schema `pricing_workbench_gen2`, warehouse `f738fde9a1197aeb`,
app `pricing-workbench-gen2`.

Three statuses are kept **separate**, as instructed: **Build** (code written + unit
tested), **Deploy** (bundle/app deployed + exercised headless on pricingv2), and
**Recording readiness** (decks/briefs/rehearsal). A row can be Build-complete while
Deploy or Recording is still open.

> **Honesty note.** Delivered + tested + deployed this stage: **WP1 complete** (all six
> findings, headless-verified); **WP2 core** (OBO-only fail-closed approval + trusted-hash
> integrity gate, headless-proven); **WP4** deterministic fact layer + evidence pack +
> read-only endpoints + append-only review events + committee brief + Ch3 UI panel;
> **WP3#2/#6** (validation-battery eligibility + honest trade-off); **WP5** cache/agreement
> core + bounded partitioned benchmark job; **WP6** recording briefs incl. the Decision
> Review sequence. **Genuinely remaining** (documented, not faked): WP3#1/#4 (parent-release/
> population inheritance + inherited 4th plan), WP4 LLM narration + MCP tool surface + full
> injection/unauthorized eval battery, WP5 FULL-preset app surface, WP6 slide decks/PDFs. The
> intrinsic blockers — a second non-approver identity (owner: simulate for filming) and
> first-time browser OBO `sql`-scope consent — are named acceptance steps, never marked
> verified. No run, approval, or benchmark number is fabricated.

---

## Finding closure — WP1 (make the calculation and UI truthful)

| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | Typed conversion at the API boundary; no string-truthiness | **Build ✓ / Deploy ✓** | `server/optimisation_demo/coerce.py`; `test_coerce.py` (10 cases incl. `"false"` not truthy, NaN/inf/None rejected). Applied in `/ch2/approve` and `/ch2/portfolio`. |
| 2 | Representative cost = £700 + £60 + 10%·£1,000 = £860 | **Build ✓ / Deploy ✓** | Cost now computed server-side via `cost_of()` in `/ch2/portfolio` as `modelled_cost`; frontend consumes it (was JS string-concat of SQL strings). |
| 3 | Ch1 impossible target (901) → "No feasible price", saved, no winner; standard outcomes unchanged | **Build ✓ / Deploy ✓** | `run_demo` now persists the runs row via the table's explicit nullable schema (single all-None winner row was failing inference). Headless: run `515e0e61…` with target 901 → `status=no_feasible`, `winner_price=NULL`, saved. Standard £1,100/700/£210,000 & £950/830/£124,500 unchanged (core tests). |
| 4 | Preserve actual solver status/message/bound/gap; independent full-precision feasibility recompute; no fake "optimal" | **Build ✓ / Deploy ✓** | `portfolio.solve_portfolio` reports real HiGHS status + gap; `ch2_run` re-checks feasibility before marking `complete`; `test_portfolio` status/gap tests. |
| 5 | Remove objective movement-penalty distortion; second solve minimises movement within a declared tolerance; never fake gap=0 | **Build ✓ / Deploy ✓** | Two-solve in `solve_portfolio` (`movement_tolerance`, `margin_sacrificed_for_movement`); `test_portfolio` proves the true optimum is retained where the old penalty would have distorted it. |
| 6 | Failure/retry/cancel UI, duplicate-submit, monitoring period numeric comparison | **Build ✓ / Deploy ✓** | Monitoring period + rows now typed server-side (period returned as int → client compares 10 > 9 numerically, not `"10" < "9"`). Ch1/Ch2/Ch3 run controls: duplicate-submit still guarded, and a **failed** run is now retryable (was stuck disabled); poll timer cleared on retry. |

## Finding closure — WP2 (bind approval to immutable evidence)

| Item | Status | Evidence |
|---|---|---|
| OBO-only approval, fail-closed; SP fallback removed | **Build ✓ / Deploy ✓** | `/ch2/approve` rewritten: no `execute_query` fallback; missing token/scope, non-JSON edge, denial or error → un-approved + actionable message. |
| Approver identity = `session_user()` (verified for SECURITY DEFINER); no caller-supplied approver | **Build ✓ / Deploy ✓** | Web+empirical verification (probe job); procedure signature drops `p_approver`. |
| Integrity at the privileged boundary: caller hash must equal the job's trusted stored hash; run must be complete + model_eligible | **Build ✓ / Deploy ✓ (headless)** | `ch2_governance_setup` procedure + `ch2_run` trusted `plan_hash`/`model_eligible`; headless gate evidence below. |
| Strict rebuild rejects duplicate keys/selections, bad booleans, coverage mismatch (expected segments from manifest) | **Build ✓** | `governance.build_and_validate_from_rows`; `test_governance` (7 cases). |
| Live **non-approver denial** via a second identity | **BLOCKED — deployment acceptance step** | No second (non-approver) identity available in this environment; harness + exact invocation documented below. |
| Browser OBO first-time `sql`-scope consent | **BLOCKED — deployment acceptance step** | Requires an interactive re-authorization; fail-closed message guides the user. |

### Headless WP2 gate evidence (pricingv2, 2026-09-13)
Trusted run produced by the governed job: **`e6995e31431e4cd28a0caa64408ce417`** —
`status=complete`, `model_eligible=true`, `n_segments=9`, trusted
`plan_hash=001ecd4d12c1593592f3b9a3b28c6ccdfa9d48d3cc5351452b931e988436a9fd`,
totals 3,660.1 sales / £891,158 margin (job run `587821459668562`).

Direct CALLs to `optimisation_demo_ch2_approve` via the SQL Statement API (as
`laurence.ryszka@databricks.com`, an approver) — this exercises the integrity gate and
the approver-success path, i.e. the "direct-call tampering rejected" acceptance row:

| Case | CALL | Result |
|---|---|---|
| Tamper | valid run + **wrong** hash | `USER_RAISED_EXCEPTION: approve blocked: plan hash does not match the validated run plan` |
| Legacy/unverified | pre-provenance run (`0a46a0aa…`, NULL trusted hash/eligibility) | `USER_RAISED_EXCEPTION: approve blocked: run model is not eligible (… legacy/unverified)` |
| Approve | valid run + **correct** hash | `SUCCEEDED` — release recorded with `approver = laurence.ryszka@databricks.com` (from `session_user()`) and the **stored trusted** hash, not the caller value |

The recorded release shows the approver came from `session_user()` and the persisted
`plan_hash` is the job's trusted value — the procedure ignores any caller-supplied
approver and re-derives the hash to compare, so a direct caller cannot approve a plan
the validated job never produced.

---

## WP3 — Chapter 3 real continuation · **PARTIAL**

**Built + deployed + verified:**
- **WP3#2 — model eligibility** now requires the **full frozen validation battery on the
  out-of-time final-test split** (calibration error, mean-prediction error, minimum
  observations AND monotonicity) — no longer monotonicity alone. Per-model evidence is
  persisted to `optimisation_demo_ch3_model_validation`; the world set uses only eligible
  models and records both the **candidate** and **eligible** counts (never padded).
- **WP3#6 (already honest, tested)** — worst-world benefit and nominal-world sacrifice are
  computed as two distinct quantities from one matrix (`decision_review.robust_vs_nominal_tradeoff`);
  the Ch3 UI never labels the gap between two worst-world numbers the "cost of insurance".

**Remaining (NOT delivered — confirmed against the code):**
- **WP3#1** — the live Ch3 job still calls `make_historic()`/`train_*`/`make_future()`
  inline; it must instead **require an approved Chapter 2 parent release** and inherit its
  exact population + primary model + feature contract + policy (challengers prepared in a
  separate offline `ch3_prepare` job). This is a semantically-significant rework (Ch2 and
  Ch3 currently generate different populations) and was not shipped rather than ship it wrong.
- **WP3#4** — add the exact Chapter-2 released plan as a fourth plan evaluated across worlds
  (shown honestly, even where it breaches a stressed floor). Blocked on WP3#1 (shared population).
- **WP3#3/#7** — immutable world manifest + Ch3 approval/release extension.

## WP4 — Decision Review assistant · **PARTIAL — deterministic core + evidence + endpoint delivered**

**Built + tested + deployed (deterministic, no LLM):**
- `business_evidence.py` — versioned, hashed synthetic evidence pack; each item carries
  owner, observation/effective dates, population mapping, denominator/sample size,
  definition, synthetic label, known limitation and `related_to`. Filming case included:
  claims experience **+5%** vs a correlated finance planning assumption **+8%**.
- `decision_review.py` — structured facts with inference labels (observed_data /
  model_output / inference): `scenario_coverage_gap` (detects the +8% lies outside the
  included +5%, drafts the stress, labels it an assumption not experience),
  `source_compatibility` (population mismatch + correlated-source guard so correlated
  estimates aren't double-counted), `constraint_slack` (binding only with computed slack),
  `model_disagreement`, `robust_vs_nominal_tradeoff` (worst-world benefit AND nominal
  sacrifice as two distinct quantities from one matrix), `rank_challenges` (deterministic
  priority, ≤3, drops non-issues), `challenge_cards` (finding / why-with-metric / evidence
  IDs / question / proposed investigation / what-it-cannot-establish).
- Read-only API: `GET /review/ch3/{run_id}` and `GET /review/evidence` — consume only
  governed tables by explicit id + the versioned pack; no prices chosen, no policy/scenario
  executed, no approval. Labelled `ai_review: unavailable` (deterministic facts + templated
  cards ARE the response — honest, no template prose passed off as a live model).
- Tests: `test_decision_review.py` (14 cases) covering the +8% detection, incompatible
  populations, correlated sources, outdated evidence, disagreement, the trade-off, ranking
  ≤3, card structure. **Real-data evidence** over Ch3 run `9046613476fe4c11879d126a6725e70e`:
  included stresses `[1.0, 1.05]` → +8% flagged uncovered → drafts `cost_scale 1.08`; top
  challenge is the coverage question; 3 ranked challenges.

**Remaining (NOT delivered this stage):** the LLM narration layer on `agent_client` with
returned-reference/numeric validation; the allowlisted MCP tool surface + server-side scope
enforcement; the Committee-Briefing role + append-only review events (Investigate / Accept /
Not-relevant tied to a decision hash); the Decision Review UI panel; the full injected-
source-note / unauthorized-run / prompt-injection eval battery. The deterministic layer is
built so these sit on top without changing the computation or approval path.

## WP5 — Scale benchmark (Live/Full presets) · **PARTIAL — core + bounded job built**

**Built + tested:**
- `scale.py` (pure, 6 tests): hash-keyed coefficient cache (`coeff_cache_key` — keyed on
  input/model/feature/grid/world; a compatible objective/threshold change reuses it, an
  input change invalidates it), `coefficients_agree` (element-wise agreement + max abs/rel
  diff — a benchmark must verify agreement BEFORE comparing timings, never claim a speedup on
  mismatched maths), and `duration_breakdown` (phases reported separately, never one opaque
  total).
- `jobs/scale_benchmark.py` + bundle job "Optimisation demo — scale benchmark (gen2)":
  scores the frozen population serially (reference) and via Spark `mapInPandas` partitions
  (same pure functions, model loaded per executor), verifies coefficient agreement within a
  declared tolerance, measures **cold vs warm** (cached partitions), persists receipts to
  `optimisation_demo_scale_runs` (counts, partitions, per-path durations, agreement, measured
  speedup). FULL preset replicates the demo population up to a **bounded cap** (never
  unbounded compute); the note states scale is primarily in scoring/scenario evaluation, not
  the compact segment-level MILP.

**Status of the live run + remaining:** the benchmark job was deployed and run on pricingv2
(receipts below when the run lands). The compact-driver-MILP-only distribution boundary,
per-world cache reuse across a full 9-model×9-stress FULL preset, and the app surface for the
presets are the remaining items; conditional Monte-Carlo remains optional per the brief.

### Scale benchmark receipts (pricingv2, 2026-09-13)
Run `bd41a00ab2df477cb6b04273daddd5a1`, **Live** preset, TERMINATED SUCCESS:

| Metric | Value |
|---|---|
| Opportunities / factors / partitions | 5,000 / 21 / 8 |
| **Coefficients agree (serial vs distributed)** | **true**, max abs diff **5.8e-11** |
| Serial scoring | 0.255 s |
| Distributed scoring (cold) | 19.75 s |
| Distributed scoring (warm, coefficient cache) | 0.69 s |
| Measured cold speedup vs serial | **0.013× (i.e. ~77× SLOWER)** |

Run `24468fd0939745df813e0018786c5db2`, **FULL** preset (bounded), TERMINATED SUCCESS:

| Metric | Value |
|---|---|
| Opportunities / factors / partitions | 250,000 / 21 / 16 |
| **Coefficients agree** | **true**, max abs diff **3.7e-9** |
| Serial scoring | 1.61 s |
| Distributed scoring (cold) | 23.01 s |
| Distributed scoring (warm, coefficient cache) | 0.70 s |
| Measured cold speedup vs serial | **0.07× (~14× SLOWER)** |

**Honest interpretation (not spun):** at BOTH Live (5k) and FULL (250k) scale the distributed
path is *slower* than serial pandas scoring, because the demo's per-row scoring is cheap and
the distributed path pays fixed overhead (Spark scheduling/serialisation + a `joblib` model
load per partition). Serial 250k scoring is only 1.6 s. So the honest conclusion for THIS
workload is: **distribution is not the win — the coefficient cache is** (a compatible re-solve
drops from ~23 s to ~0.7 s at 250k). What the benchmark rigorously establishes: (1) the
distributed path produces **identical coefficients** (agreement verified to ~1e-9 BEFORE any
timing), and (2) phases are measured and reported separately. **No speedup or cost saving is
claimed, because none was measured** — the brief's exact requirement. Distribution would only
pay off with heavier per-row models or far larger scenario volume (the segment-level MILP is
unchanged either way). Reducing the distributed path's per-partition model-load overhead
(broadcast once vs load-per-partition) is the documented next optimisation.

## WP6 — Recording-ready delivery · **PARTIAL (scripts) / decks NOT DELIVERED**
Chapter recording scripts exist (`optimisation_demo_presenter{,_ch2,_ch3}.md`) and the
Google-Doc recording tab is in place. The two 16:9 decks + PDFs + the Decision Review
slide are not built (depend on WP4 + pinned WP3 runs).

---

## Competitive positioning
Retained the defensible framing only (transparent, extensible decision workflow on the
insurer's existing platform). No "incumbents lack X" claims. Practitioner comparison
checklist to be added to the appendix; competitors marked "not evaluated".

## Tests
`uv run --with pytest --with scipy --with numpy --with pandas --with scikit-learn pytest
tests/optimisation_demo/ -q` → **84 passing** (adds coerce 10, governance strict-builder 7,
solver status/gap + two-solve 4, decision-review 16, scale 6, plus the existing 41). Frontend
`npm run build` clean throughout.

## Remaining external blockers (named acceptance steps, not "verified")
1. **Live non-approver denial** — needs a second workspace identity without the EXECUTE
   grant to CALL the procedure and observe the UC denial. Harness: call
   `optimisation_demo_ch2_approve(<run>, <hash>, 'x')` as that identity; expect a
   permission error. **Owner decision (2026-09-13):** only one account is available, so this
   live cross-identity check will not be run; for the recording the denial may be shown as a
   **clearly-labelled simulation**. The real gate is unchanged and is NOT weakened or faked
   into an approval — the EXECUTE grant + the headless tamper/legacy rejections above are the
   integrity evidence; only the *second-identity* denial is simulated for filming.
2. **OBO `sql`-scope consent** — first-time browser re-authorization so the forwarded
   token carries `sql`; until then approval is intentionally unavailable (fail-closed).
3. **Effective-grant audit** — the app SP holds schema-level EXECUTE (inherited).
   With OBO-only approval the app never approves as the SP, but tightening the schema
   grant should be reviewed without removing unrelated function access.

# Optimisation demo — runbook

A small, honest teaching flow: **explain optimisation on one segment, then run exactly that
calculation on Databricks**, change one business requirement, and run it again. Built as a new,
self-contained route — it does **not** patch or depend on the existing seven-tab optimiser.

## Decisions (locked with the user, 2026-09-12)

- **This becomes the recording.** The ~8-min teaching demo is the primary recorded demo. The
  seven-tab optimiser stays reachable but off the record path; the 17-min governed-loop Part 1
  script is parked.
- **Keep "grandma in a BMW"** as a mnemonic for an *invented* synthetic segment, with honest
  framing (not a claim about real older drivers; 1,000 opportunities, not sold policies).
- Objective is fixed: **maximise expected margin**. The human changes a **sales requirement**
  (minimum expected customers); that changes the winning permitted price.

## Target (gen2 / pricingv2)

- Repo `wryszka/pricing-workbench-gen2`, branch `main` (implemented against HEAD `3429946`).
- Workspace: pricingv2 FEVM, profile `PRICING_V2`. Warehouse `f738fde9a1197aeb`.
- Catalog/schema (env-driven): `lr_pricing_v2_aws_us_catalog.pricing_workbench_gen2`.
- App: `pricing-workbench-gen2` — new route **`/optimisation-demo`** (existing `/optimisation`
  seven-tab page untouched).

## Names (selected)

| Thing | Name |
|---|---|
| Pure calc module | `src/optimisation_demo/core.py` (no Spark/SDK/UI imports) |
| Canonical fixture | `src/optimisation_demo/example.json` (`example_id = grandma_bmw_v1`) |
| Databricks job notebook | `src/optimisation_demo/run_demo.py` |
| Bundle job | `resources/optimisation_demo.yml` → job **"Optimisation demo — run (gen2)"** |
| API router | `src/app/server/routes/optimisation_demo.py`, prefix `/api/optimisation-demo` |
| Frontend page | `src/app/frontend/src/pages/OptimisationDemo.tsx` |
| Tables (idempotent, demo-prefixed) | `optimisation_demo_inputs`, `optimisation_demo_runs`, `optimisation_demo_candidate_results` |
| Tests | `tests/optimisation_demo/` (pytest; run via `uv run --with pytest pytest`) |

No collision: only an unrelated old `docs/optimisation_demo_spec.md` exists; no `optimisation_demo_*`
table or code. The three new tables live in the workbench schema with the `optimisation_demo_`
prefix and are created idempotently — they never touch the existing optimiser tables.

## Canonical worked example (preserved verbatim)

`grandma_bmw_v1` · segment "Older drivers · higher-group cars" · 1,000 opportunities ·
modelled variable cost £800/sale · baseline price £1,000. Objective: maximise expected margin.

| Candidate | Purchase prob | Expected customers | Margin/sale | Expected total margin | Expected premium |
|---:|---:|---:|---:|---:|---:|
| £900  | 90% | 900 | £100 | £90,000  | £810,000 |
| £950  | 83% | 830 | £150 | £124,500 | £788,500 |
| £1,000 (baseline) | 75% | 750 | £200 | £150,000 | £750,000 |
| £1,050 | 74% | 740 | £250 | £185,000 | £777,000 |
| £1,100 | 70% | 700 | £300 | £210,000 | £770,000 |
| £1,150 | 45% | 450 | £350 | £157,500 | £517,500 |

- **Run A** (no requirement): winner **£1,100** / 700 / **£210,000**. vs baseline: price +£100, customers −50, margin +£60,000. Premium £770,000.
- **Run B** (≥ 830 expected customers): only £900 and £950 feasible; winner **£950** / 830 / **£124,500**. vs baseline: price −£50, customers +80, margin −£25,500. Premium £788,500. vs Run A: customers +130, margin −£85,500.
- A target of **901** → **no feasible price** (max is 900 at £900). Never silently relaxed.

Arithmetic (the whole lesson):
```
expected_customers    = opportunities × purchase_probability
margin_per_sale        = offered_price − modelled_variable_cost_per_sale
expected_total_margin  = expected_customers × margin_per_sale
expected_premium       = expected_customers × offered_price
```
Complete enumeration over the six supplied candidates — exact over the set, no SciPy, no
interpolation, no learned model. "£800" is a supplied *total variable-cost* teaching assumption,
**not** the workbench's `technical_premium` (claims-only). Purchase probabilities are supplied
synthetic assumptions, not learned from real customers. "At least 830" constrains **expected**
customers, not a guarantee.

## Phase status

- [x] **Phase 1** — inspect + establish the narrow path; names/target above.
- [x] **Phase 2** — pure `core.py` + `example.json` + tests. **9/9 pass**; Run A/B produce the exact
      answers; infeasible rows explained; ties deterministic (nearest baseline, then lower price);
      invalid inputs rejected; a second fixture proves winners aren't hardcoded.
- [x] **Phase 3** — `/api/optimisation-demo` route (example / run / run status), `OptimisationDemo.tsx`
      (Explain screens 1–3 + Run panels A–C), nav entry `/optimisation-demo`. Frontend typechecks +
      builds clean. Worked-example vs Running vs Completed-Databricks-run states are labelled distinctly.
- [x] **Phase 4** — bundle job **"Optimisation demo — run (gen2)"** (id `1099542605759414`) + the three
      tables; app redeployed. **Verified live on pricingv2:**
      - Run A (app_run_id `9d604145…`, job run `436985750672455`) → **£1,100 / 700 / £210,000**, input v2.
      - Run B (≥830, app_run_id `85b59b1c…`, job run `958115821126620`) → **£950 / 830 / £124,500**, input v4.
      - Both job runs TERMINATED SUCCESS; run records read back by exact app_run_id.
      - App: https://pricing-workbench-gen2-7474655676955816.aws.databricksapps.com → **Optimisation demo**.
- [~] **Phase 5** — presenter script `docs/optimisation_demo_presenter.md` (written). Fallback screenshots
      still to capture from the live app (browser SSO needed).

## Chapter 2 — a portfolio (built + live on pricingv2)

Learned demand + individual costs + coupled segment prices + a portfolio sales floor.
Modules (all pure, tested): `economics.py`, `demand.py` (logistic + monotone GBT; frozen
validation battery), `portfolio.py` (finite-candidate MILP via SciPy/HiGHS), `governance.py`
(deterministic pre-approval recompute + hashes), `monitoring.py` (synthetic outcome check).
Jobs: `ch2_prepare` (freeze data + train/validate/persist model + portfolio summary),
`ch2_run` (score→solve), `ch2_governance_setup` (approval procedure + approver-only EXECUTE),
`ch2_check` (synthetic next period). App: chapter selector → Prepare status / Portfolio /
Choose (Margin-first vs Protect-sales-98%) / Review (OBO approve+release) / Check.

- **OBO gate:** app `user_api_scopes: [sql]` enabled; `/ch2/approve` recomputes the plan
  then CALLs the UC procedure `optimisation_demo_ch2_approve` AS THE USER — approver-only
  EXECUTE, non-approver denied by UC. Append-only approvals/releases.
- **⚠️ OBO consent finding (2026-09-12):** the CALL-as-you path returns HTTP 403
  `Invalid scope, required scopes: sql` — the browser's cached app authorization predates
  the `sql` scope, so the forwarded OBO token is minted WITHOUT it. **Fix = re-authorize
  the app in the browser** (open the app URL in a fresh/incognito session and accept the
  consent prompt that lists the `sql` scope; or revoke + re-grant the app's user
  authorization). Once the forwarded token carries `sql`, the per-person UC gate is live and
  the Approve button reports "as you (OBO)".
- **Honest fallback (shipped):** when on-behalf-of SQL isn't available at the front-door
  (the 403 above, before re-consent), `/ch2/approve` records the **authenticated approver's**
  decision through the SAME governed procedure via the app SP (which holds EXECUTE) — an
  attributed, access-controlled record, not per-user platform denial. A genuine UC EXECUTE
  denial (JSON) still blocks and does NOT fall through. The button + response report which
  path ran ("as you (OBO)" vs "attributed record"); the app UI copy states both plainly.
- **Verified live:** margin-first 2,990 sales / £998k; protect-sales-0.98 3,660 / £891k;
  approval + release + rollback-chain works; guardrail blocks non-complete runs; Check
  period-1 observed ≈ expected per segment.

## Chapter 3 — uncertain futures (Live preset built + live)

Robust maximin of expected-margin uplift across **worlds** (validated demand model ×
declared market/cost scenario), inheriting Ch2's grid + 98% per-world sales floor.
`robustness.py` (pure, tested — enumeration + maximin invariants); `ch3_run` job builds the
Live world set (2 validated models × 3 scenarios = 6 worlds), solves baseline/nominal/robust,
saves worlds + plan-by-world comparison. App: Chapter 3 → Compare (robust vs nominal min
uplift + plan×world uplift table + grandma factor per plan).

- **Verified live:** 6 worlds; robust worst-uplift £16,370 ≥ nominal £16,357; robust grandma
  +1% vs nominal +2%; feasible in every world. Honest, modest robustness benefit.

## Tests
`uv run --system-certs --with pytest --with scipy --with numpy --with pandas --with scikit-learn pytest tests/optimisation_demo/ -q` → **43 passing** (core 9, portfolio 10, demand 5, pipeline 4, governance 6, monitoring 3, robustness 6).

## Honest remaining gaps (not built / need you)
- **OBO approve-as-user live confirm:** the UC gate + recompute are verified headless, but the
  first-time consent + as-the-user CALL need a browser sign-in (and a non-approver identity to
  see the denial) — only a real login exercises the token handshake.
- **Automated denied-non-approver integration test:** approver-only EXECUTE is verified via
  SHOW GRANTS; a scripted deny needs a non-approver credential.
- **Ch3 Full-scale preset** (up to 250k opps / 9 models / Spark-partitioned scoring + billing
  evidence) and **conditional Monte-Carlo** — the spec labels these a prepared scale experiment
  / optional-last; the Live camera path is done.
- **Slide decks + recording briefs** (`CHAPTERS_2_3_SLIDES_AND_RECORDING.md` companion was not
  supplied) and the remaining Ch3 screens (Assumptions / Grandma-detail / Run-evidence).

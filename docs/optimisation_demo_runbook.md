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

## How to run the tests
```
uv run --system-certs --with pytest pytest tests/optimisation_demo/ -q
```

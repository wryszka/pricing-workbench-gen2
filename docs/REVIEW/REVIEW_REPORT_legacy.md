# Review report — Pricing Workbench (legacy / pre-optimiser)

> Standardized output of the 6-agent review panel (bricksurance-playbook `BUILD_AND_REVIEW.md` §7), run fan-out and collated here. Scope = the whole gen2 workbench **except** the price-optimisation module (reviewed separately in `REVIEW_REPORT_optimiser.md`).

- **Demo:** pricing-workbench-gen2 (data → models → serving → governance → agents → factory → broker/MCP) · `wryszka/pricing-workbench-gen2` @ main
- **Reviewed:** 2026-08-25 · live on pricingv2, data as of today
- **Verdict:** **SHIP WITH ROADMAPPED GAPS** — no code blockers; the gaps are documentation-format items and defensive hardening.
- **Scorecard (§6):** P0 platform stack passes (real UC objects, MLflow/UC aliases, Genie-via-API, managed agents, serverless, governance/audit). Doc-format P0s (run-sheet/QA) + one security-hardening item are the open list.

**Severity:** `blocker` · `major` · `minor` · `nit`. **Status:** `fixed` · `roadmapped` · `wontfix` · `open`.

---

## 1 · Practitioner (pricing actuary)
| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Opening is capability-first ("pricing accelerator") not pain-led; the canonical question isn't named in README/talk-track. | major | roadmapped |
| 2 | Governance (audit + lineage + time-travel) is excellent but under-narrated — add a "click a row → model version → reproduce" beat. | minor | roadmapped |
| 3 | Value-vs-incumbent (Radar/Earnix) is implied, not shown as an on-screen artifact. | minor | roadmapped |

**Deal-breakers:** none — real models, real serving, real UC lineage; credible under drill-down. **Verdict:** SHIP (positioning polish).

## 2 · Decision-maker (CFO / CRO)
| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | No `STANDARDS.md` pointer / declared compatibility tier. | blocker (playbook P0) | **fixed** — `STANDARDS.md` added (Tier 2). |
| 2 | No `DECISIONS.md` (dated decision log + gotchas). | major | **fixed** — `docs/DECISIONS.md` added. |
| 3 | No `DEMO_RUNSHEET.md` / `DEMO_QA.md` in house GO·DO·SAY·IF-ASKED format. | major | roadmapped |
| 4 | Business case lacks a quantified risk-of-inaction (cost of status quo / time-to-close). | minor | roadmapped |
| 5 | No CFO-persona Q&A (OpEx, ROI vs incumbent, audit). | minor | roadmapped |

**Verdict:** SHIP WITH ROADMAPPED GAPS — doc structure is the gap, not the demo.

## 3 · Databricks SA (demoability)
| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Reset rolls dates to today; AI yellow-button + cache pre-warm wired (~24 cached entries live); deep-links env-driven; scale-to-zero; no always-on clusters. | — (strength) | — |
| 2 | Compatibility tier not stated in README. | minor | **fixed** (in `STANDARDS.md`) |
| 3 | Live-serving tier is defined-but-dormant via `deploy_profile`, but no in-app one-click arm/disarm (DAB-controlled). | minor | roadmapped |

**Verdict:** SHIP WITH ROADMAPPED GAPS — all P0 demoability controls present.

## 4 · Senior developer (correctness & robustness)
| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Workspace-client singleton retries indefinitely on init failure (no failure flag/backoff). | minor | roadmapped |
| 2 | `sql.py` returns `[]` when manifest/schema is None — masks malformed-query errors as empty results. | minor | roadmapped |
| 3 | Asset-ID cache (Genie/dashboard) has a 300s TTL with no invalidation — stale ID → 403 for ≤5 min after a recreate. | minor | roadmapped |
| 4 | Audit middleware sets user None when forwarded headers missing; downstream falls back to SDK `current_user`. | minor | roadmapped |
| 5 | Statement-chunk loop assumes chunks exist / `chunk_index` present. | minor | roadmapped |

**Verdict:** SHIP — no blockers; items are defensive robustness for long-running/edge cases.

## 5 · Security
| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | `factory.py:381-382` interpolates `variant_id` / `category` from `req.plan` into SQL **unescaped** (only `name` is escaped) — injection via variant config. | major | open (recommend fix) |
| 2 | `datasets.py:945` uses `get_current_user()` in an INSERT without escaping. | minor | open |
| 3 | All SQL is f-string interpolated (single-quote escaping only) — error-prone; parameterised queries are the defence-in-depth. | minor | roadmapped |

**Cross-cutting (clean):** no secrets in code/history; app SP least-privilege; no external egress; auth delegated to Databricks Apps. **Mitigation:** app SP MODIFY is table-scoped, so injection blast radius is constrained. **Verdict:** SHIP WITH ROADMAPPED GAPS (fix factory.py escaping before wide sharing).

## 6 · Current-Databricks expert (up to date)
| # | Finding | Severity | Status | Doc checked |
|---|---|---|---|---|
| 1 | MLflow UC registry + aliases + `infer_signature`, FE `fe.log_model`, model-serving SDK, Genie via `/api/2.0/genie/spaces`, managed ChatAgent on the Agent Framework served with auto-auth, Lakeview API — all current, nothing deprecated. | — (strength) | — | MLflow, FE, Agent Framework, Genie, Lakeview |
| 2 | Verify serverless env `client: "5"` and Jobs API 2.1 remain current. | nit | open (verify) | serverless env / Jobs API |

**Docs swept:** MLflow, Feature Engineering, Agent Framework/AI Gateway, Databricks Apps, Jobs API 2.1, Genie API, Lakeview, serverless env — as of 2026-08-25. **Verdict:** SHIP.

---

## Applied fixes (summary)
- **`STANDARDS.md`** added (playbook pointer + Tier 2 declaration) — closes the flagged P0.
- **`docs/DECISIONS.md`** added (dated log + gotchas).

## Open / roadmapped
- **Security (do before wide sharing):** escape `variant_id`/`category` in `factory.py`; escape `reviewer` in `datasets.py`; roadmap parameterised SQL app-wide.
- **Docs (house format):** `DEMO_RUNSHEET.md` (GO·DO·SAY·IF-ASKED, per-beat timings) + `DEMO_QA.md` (~15–20, per persona incl. CFO), cross-linked; surface reader manuals in-app.
- **Positioning:** name the canonical question + pain-led opening; add an on-screen enrich/wrap/replace-vs-incumbent artifact; quantify risk-of-inaction.
- **Robustness:** workspace-client backoff; distinguish empty-result vs query-error in `sql.py`; asset-cache invalidation; chunk-index guards.
- **Verify:** serverless client "5" / Jobs API 2.1 currency at next panel.

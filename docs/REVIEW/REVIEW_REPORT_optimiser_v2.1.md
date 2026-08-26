# Review report — Price Optimisation module (playbook v2.1, SEVEN-agent panel)

> Standardized output of the v2.1 review panel — run fan-out (all seven personas in parallel) and collated here. v2.1 adds the **incumbent champion** and the rule that questions the demo can't answer live go to `DEMO_QA.md`, cross-referenced from the beat.

- **Demo:** pricing-workbench-gen2 · `/optimisation` module · `wryszka/pricing-workbench-gen2` @ main
- **Reviewed:** 2026-08-26 · live on pricingv2 · against the delta build (decision records, explain-price, agent bench, heavy mode, MCP)
- **Verdict:** **SHIP WITH ROADMAPPED GAPS** — after the fixes below. (Security opened at NOT YET on the MCP authz bypass; fixed → ship.)
- **Scorecard (§6):** P0 pass after fixes; P1 gaps labelled + roadmapped. Legacy workbench reviewed at v2.0 (`REVIEW_REPORT_legacy.md`), unchanged.

**Severity:** `blocker`/`critical` · `major` · `minor` · `nit`. **Status:** `fixed` · `roadmapped` · `wontfix` · `open`.

---

## 1 · Practitioner (pricing actuary) — SHIP WITH ROADMAPPED GAPS
Loop credible under drill-down; Grandma-in-a-BMW walkthrough honest; decision records + explain-price ombudsman-grade; monotonicity + endogeneity handled; value story enrich/wrap/replace. **No deal-breakers.** Confirmed the "About this demo" disclaimer is in-app. Open: GATE-1 lineage edge (documented, not demo-blocking); runsheet non-author smoke.

## 2 · Decision-maker (CFO/CRO) — SHIP WITH ROADMAPPED GAPS
Business case honest (uplift model-derived, not hardcoded); governance is the headline (versioned policy + audit + server-side gate). P1 (all roadmapped, narrative not code): risk-of-inaction opening, on-screen sensitivity line, regulatory framing as a headline beat, incumbent-contrast artifact. Q&As added to DEMO_QA (24, 25).

## 3 · Databricks SA (demoability) — SHIP
All 7 tabs distinct + graceful empty states; Grandma walkthrough runs; seam (`constraint_author` no UI button) documented with fallbacks; heavy mode never auto-triggered (pre-computed default; "live" preset explicit); yellow cache covers the personas; reset deterministic; fresh-workspace reproduce verified. Live-room mitigations listed (agent cold-start, solver ~1 min, pre-solved screenshot fallback).

## 4 · Senior developer (correctness) — SHIP WITH ROADMAPPED GAPS
| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | `_write_decision_record` interpolated `fairness_pass` (Python bool) into SQL | **blocker** | **fixed** — bound `:fpass` + `cast(... AS BOOLEAN)` |
| 2 | MCP deploy path skipped the immutable decision record | major | **fixed** — MCP deploy now writes it (parity) |
| 3 | MCP read tools used `.replace("'","''")` not binds | minor | **fixed** — parameterised |
| 5 | React poll stale-closure (`run?.url` on timeout) | minor | **fixed** — track `lastUrl` |
| 4,6 | React poll cleanup-on-unmount; timeout UX copy | minor | roadmapped |
| 7 | spark_udf→inner-artifact fallback logs to notebook only (GATE-1) | minor | roadmapped |
| 8 | heavy-mode Monte-Carlo array not `del`'d | nit | roadmapped |

## 5 · Security — was NOT YET → **SHIP after fixes**
| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | **MCP `opt_deploy_factors` had no RBAC** — corridor-only; any authenticated caller/agent could deploy, bypassing the app's `_require_admin` (privilege escalation vs Principle 8) | **critical** | **fixed** — MCP deploy now calls `_require_admin` first |
| 2,3 | manual SQL escaping in MCP explain / decision-record tools | medium | **fixed** — parameterised |
| 4 | MCP transport has no blanket per-tool RBAC | high (design) | **fixed-for-writes** (deploy gated) + **logged** in DECISIONS.md (reads unrestricted, same as app read endpoints) |
| — | no secrets in code/history; app-SP least-privilege; `/deploy` app route + `/explain` already parameterised; no egress | ✅ | — |

## 6 · Current-Databricks expert — SHIP
No deprecations. UC scalar-fn `max()`-wrapped pattern correct; MLflow `ChatAgent` current; SQL Statement API named-params + Jobs 2.1 current; serverless numpy is the right fit for the per-policy Monte-Carlo; hand-rolled MCP is a **compliant "expected-but-evolving" forward hook** (§8). One verify step: confirm the `databricks-claude-sonnet-4-6` FM endpoint exists in the target workspace (passes here — the agents respond).

## 7 · Incumbent champion (hostile skeptic) — SHIP WITH ROADMAPPED GAPS
The value: it exposed the honesty gap and the real Phase-2 edges.
| # | "You can't really…" | Fair? | Resolution |
|---|---|---|---|
| 1 | GIPP declared in YAML but not enforced in the solver | **fair** | **fixed (honesty):** YAML header + DEMO_QA Q8/Q19 now state GIPP is *monitored*, not solve-time enforced (Phase 1 = new business); renewal optimisation + in-solver GIPP is Phase 2 |
| 2 | Renewals not optimised (new-business only) | fair | roadmapped (Phase 2) — DEMO_QA Q19 |
| 3 | forbidden_signals "just a list" | **not fair** | enforced **by construction** (factor keyed on age×vehicle only) + proxy-tested post-solve — DEMO_QA Q21 |
| 4 | only 9 segments | context | illustrative; solver linear in segment count — DEMO_QA Q20 |
| 5 | portfolio (cross-segment) constraints | fair | roadmapped (Phase 2) — DEMO_QA Q22 |
| 6 | closed loop replays own assumptions | partly | honest calibration check on synthetic data — DEMO_QA Q23 |

**Deal-breakers:** none that survive — the room lands on *"interesting, we'd pilot with renewals"* (a win). **Value story:** enrich/wrap/replace holds.

---

## Applied fixes (this review)
- **[critical] MCP deploy RBAC** — `_require_admin` on `opt_deploy_factors` (+ it now writes the decision record).
- **[blocker] decision-record `fairness_pass`** — bound param + `cast AS BOOLEAN`.
- **[medium] MCP SQL** — parameterised `opt_explain_price` / `opt_get_decision_record`.
- **[minor] React** — poll stale-closure fixed.
- **Honesty** — constraint-YAML enforcement model documented; DEMO_QA Q8/Q19–Q25 added (incl. all incumbent-champion "yes-but"s per the v2.1 rule).
- DECISIONS.md updated (MCP authz design, GIPP enforcement model, this panel).

## Roadmap — CLEARED 2026-08-26 (commit 45cc29f)
- ✅ **Renewal optimisation + solve-time GIPP** — `optimisation_renewal_solver`: renewal priced `min(prior×factor, equiv_new_business)` → GIPP by construction (0 breaches, +£1.35m). Chained into the spine; `/renewal-factors` + Renewals section + MCP tool.
- ✅ **Portfolio (cross-segment) constraint** — solver greedy-repair to hold total volume ≥ `portfolio.min_volume_ratio` (binding='portfolio_volume').
- ✅ **Sensitivity** — real re-solve at 0.5–1.5× elasticity → `optimisation_sensitivity`; `/sensitivity` endpoint + Optimiser panel.
- ✅ **Incumbent-contrast artifact + risk-of-inaction** — How-it-works "vs a black-box appliance" comparison table.
- ✅ **Polish** — heavy-mode array freed; GATE-1 status audited (`optimisation_technical_scored.lineage_edge_emitted`); React poll unmount guard.

## Still open (labelled)
- **Finer segmentation** — the 9-segment grid is illustrative; solver is linear in segment count (config choice on a real book).
- **GATE-1 lineage edge** — champion scoring is correct; whether the `spark_udf` path emits the UC model→table edge (vs inner-artifact fallback) is now recorded per-run in the audit log; closing it fully needs the FE/pyfunc load path.
- **Runsheet non-author smoke; verify FM endpoint per target workspace** (process/deploy checks).

# Review report — FULL WORKBENCH (playbook v2.2, 8-agent panel)

> First **full-workbench** panel since v2.0. The Price Optimisation module keeps its separate v2.2 pass (`REVIEW_REPORT_optimiser_v2.2.md`) — this report deliberately weights the **non-optimiser** surfaces (ingestion → GLMs & model factory → serving → governance → quote/broker → app), which had not been reviewed since v2.0, before the incumbent-champion and UI/UX lenses and the §3 Layout-logic rules existed.

- **Reviewed:** 2026-08-26 · gen2 `main` · live on pricingv2 · against bricksurance-playbook **v2.2** §6 scorecard + §7 8-agent panel.
- **Companion:** `docs/WORKBENCH_OVERVIEW.md` (the end-to-end description this review was run against).
- **Panel verdict:** **DO NOT SHIP YET — one true security P0 blocks a room.** Fix the two P0s below, then the demo ships with the P1 cluster labelled + roadmapped (playbook bar: every P0 passes, every P1 labelled). Six of eight lenses returned SHIP-WITH-GAPS / CURRENT-WITH-GAPS / CONDITIONAL-GO; **Security returned BLOCK.**

## Per-lens verdicts
| # | Lens | Verdict | Headline |
|---|---|---|---|
| 1 | Practitioner | SHIP-WITH-GAPS | Motor track clean; commercial GLMs carry real actuarial errors |
| 2 | Decision-maker | SHIP-WITH-GAPS | Story lands but "cost of doing nothing" + non-optimiser ROI missing from exec open |
| 3 | Databricks SA | SHIP-WITH-GAPS | Deploy/reset sound; DEPLOY.md stale, single-person admin, silent cache-warm fail |
| 4 | Senior developer | SHIP-WITH-GAPS | Core well-engineered; SQL hardening not propagated; duplicate build assets |
| 5 | **Security** | **BLOCK** | **SQL injection on a write path — any viewer can corrupt the whole book** |
| 6 | Current-Databricks | CURRENT-WITH-GAPS | Sound stack; `ChatAgent` deprecated, private `_header_factory()` at 18+ sites |
| 7 | Incumbent champion | CONDITIONAL-GO | Rating engine is thin (answerable via Radar framing); governance maker-checker gap |
| 8 | UI/UX expert | SHIP-WITH-GAPS | Governance page is the star; ~8 pages off the design system; one missing disclaimer |

---

## P0 — blockers (must pass before any room)

**P0-1 · SQL injection on a WRITE path → whole-book corruption** · `src/app/server/routes/live_pricing.py:687, 701` · *(Security)*
The telematics `UPDATE`/`MERGE` interpolates `policy_id` raw; `.strip().upper()` does not neutralise injection. Any authenticated app viewer POSTs `policy_id = "Z' OR 'A'='A"` → `WHERE policy_id = 'Z' OR 'A'='A'` matches **every row**, rewriting `behaviour_score`/telematics for the entire book, then MERGE-propagating the corruption into the modelling mart — running with the app SP's `MODIFY` grant.
**Fix:** bind `:pid` (the `sql.py` helper already supports named params) or apply a strict `^[A-Z0-9-]+$` guard like `quote_stream._validate_tx`. A single shared identifier-sanitiser applied everywhere in P1-1 clears this and all the read sinks at once.

**P0-2 · Full-screen branded page with no "About this demo" disclaimer** · `src/app/frontend/src/pages/QuoteTester.tsx:55–127` · *(UI/UX)*
The standalone dark-theme load-tester renders a branded "Bricksurance Motor" page with no disclaimer anywhere — every other standalone page (`QuoteSystem`, `BrokerChat`) has at least a footer line. Violates a P0 house rule (disclaimer on every screen).
**Fix:** add the one-line `<footer>` disclaimer used by `BrokerChat`.

---

## P1 — real gaps (fix, or label + roadmap before ship)

### Model correctness & compliance — the load-bearing drill-down *(Practitioner, Incumbent)*
These sit under the "razor-sharp under drill-down" P0 scorecard item. Fix the ones marked ⚠ before a practitioner room; the rest must be labelled in `DEMO_QA.md` tab 2.

- **P1-2 ⚠ · Commercial technical premium ~5× overstated — no annualisation** · `pricing_scorer.py:368–403` · `freq` is a Poisson GLM on `claim_count_5y` (5-year count) but `_apply_rules` does `technical = freq * sev` with no `/5`. Motor already fixed this (`motor_pricing_scorer.py:273`); commercial never got the divisor. **Flagged independently by Practitioner and Incumbent.** Fix: add `freq_exposure_years:5` to `rating_engine_config` + divide (or add `offset=log(5)` in the GLM).
- **P1-3 ⚠ · Gender is an active rating coefficient in the motor frequency GLM** · `freq_glm_motor.py:52` lists `gender` in `FEATURES` → fitted coefficient drives premium, while `mcp_tools.py:94` documents it as "must not rate on it." Directly contradicts the compliance narrative that IS the product; a challenger printing relativities catches it. Fix: remove `gender` from `FEATURES`; keep it only in post-hoc fairness monitoring. *(Verify the line before acting — this is the single most reputationally sensitive finding.)*
- **P1-4 · Demand model evaluates conversion at the OLD `current_premium`, not the quoted price** · `pricing_scorer.py:335–343` · `gross_premium_quoted = current_premium` (in-force premium), so the demand signal is one cycle stale and undefined for new business. **Incumbent rated this P0 ("breaks the demand-pricing story").** Fix: pass the computed `technical`/`loaded` back into `_build_demand_input`.
- **P1-5 · Severity GLMs understate ~20–27% — OLS on log without Duan smearing** · `sev_glm.py:191`, `sev_glm_motor.py:157` · `exp(E[log Y])` understates `E[Y]`; no `exp(0.5·σ²)` correction. Fix: apply the smearing constant or use a true Gamma GLM (and correct the "GLM_Gamma" MLflow tag, which currently mislabels an OLS-on-log model — governance-pack accuracy).
- **P1-6 · Retention model target is circular** · `model_06_retention.py:88–102` · `is_churned` is a deterministic formula over the same features then used as the label → learns the generator's weights. Fix: derive churn from the temporal policy structure (renewal gaps).
- **P1-7 · Validation is in-sample 80/20 hash split — no OOT holdout** · `freq_glm.py:109–128` · No out-of-time split, no decile lift, no CI on Gini — SR 11-7 / PRA SS1/23 expect OOT. Fix or label in DEMO_QA tab 2.

### Governance depth *(Incumbent — the maker-checker attack)*
- **P1-8 · Governance-pack generation auto-flips the `champion` alias — no second signer** · `governance_pack.py:1513–1544`, and `review.py`'s docstring claims "never mutates UC aliases." The pack author is also the promoter; only gate is single-person RBAC. Against PRA SS1/23 maker-checker. Fix: decouple pack generation from the alias flip; require `requested_by ≠ approved_by` and log it.
- **P1-9 · No book-level rate-change impact certificate before a `rating_engine_config` flip** · `rating_engine_seed.py:68–117` · Changing loadings has only a free-text `narrative`, no computed cohort-level premium impact. Fix: a `compare_rating_config` endpoint that re-scores the book (candidate vs champion) before any status flip.
- **P1-10 · Monotonicity not enforced on any production model** · fairness sidecar (`governance_pack.py:872`) admits it. Consumer-Duty explainability exposure. Label + roadmap.
- **P1-11 · Fraud target is a credit/behaviour proxy, not confirmed fraud; stability trail is simulated replays** · `governance_pack.py:234–240`, `backdate_versions.py` · Architecture is production-grade; the labels/history are demo-only. Own it explicitly in the pack + talk track (disclosed in DEMO_QA today but buried).

### Security — the rest of the injection surface *(Security P1, corroborated by Senior-dev)*
- **P1-12 · Unescaped identifiers across ~7 route files (read/exfil)** · `live_pricing.py:298,560,666,721`, `governance.py:262,314,383,616,634`, `factory.py:645,706`, `review.py:520`, `compare.py:261`, `deployment.py:235`, `pricing.py:84,443,332,837,921` · `UNION SELECT` reads any table the SP can select. The tell: `factory_real.py:362` escapes but `factory.py:706` (same op) doesn't; `live_pricing.py:441` escapes on INSERT but the SELECTs don't. **Fix = the same shared sanitiser as P0-1.**

### Platform currency *(Current-Databricks)*
- **P1-13 · `mlflow.pyfunc.ChatAgent` deprecated since MLflow 3.0** · `pricing_chat_agent.py:53`, `governance_agent.py:58` · Migrate both to `ResponsesAgent` (signature maps cleanly; tools unchanged).
- **P1-14 · Private SDK `w.config._header_factory()` at 18+ call sites** · agents, `agent_client.py`, `mcp_engine.py`, `genie.py`, `apply_metadata.py`, `motor_pricing_scorer.py`, +11 · No stability contract. Replace with the public `w.config.authenticate()`.

### Demoability *(Databricks SA)*
- **P1-15 · `docs/DEPLOY.md` stale throughout** · wrong target (`v2`→`pricingv2`), app name (→`-gen2`), schema, deploy command, app.yaml name; teardown drops the wrong schema → a fresh SA fails at step 1. Fix: full find/replace + "gen2-only" header.
- **P1-16 · `ADMIN_USERS` hard-set to one email** in both app.yamls · a colleague can't reset or flip to live in the room (SA), and it **fails OPEN if ever unset** (Security P2). Fix: team/SA-group alias; make `_require_admin` fail *closed*.
- **P1-17 · Cache-warm silently skipped if app is cold at reset** · `demo_reset.py:444–480` · green "reset complete" over an empty cache → 30–45s cold hang on first click. Fix: surface `ai_cache_warm.ok=false` in the reset response + show entry count in the admin panel.

### UI/UX *(UI/UX expert)*
- **P1-18 · ~8 pages bypass the shared `Page`/`PageHeader`/`OnThisPage` scaffold** · `ModelFactory`, `QuoteReview`, `Addons`, `AgenticDistribution`, `RatingEngineIntegration`, `NewDataImpact`, `Learn` · width jumps + missing explainers between pages. Wrap them.
- **P1-19 · AI live/cached toggle not reachable from standalone pages that make real AI calls** (`BrokerChat`, `QuoteSystem`) · extract `AiModeBadge` into their headers.
- **P1-20 · Local components duplicate shared primitives** (`QuoteReview` `MetricCard`/`Stat`/`StatusBadge`, `ModelFactory` `SummaryTile`) → visual drift. Replace with `Metric`/`Pill`.
- **P1-21 · Home pipeline-health uses colour-only status dots** (`Home.tsx:159`) + inline hardcoded hex bypassing tokens. Pair dot with icon/label; use token classes.
- **P1-22 · Stale hardcoded governance example dates** (`Governance.tsx:329–331`, Feb–Apr 2026 labelled "current champions"). Derive from `today − {6,3,1}mo`.

### Business framing *(Decision-maker)*
- **P1-23 · No "cost of doing nothing" in the exec opening** · `talk_track.md` opens on capability, not pain. Add a 60s problem frame (weeks-to-shadow-price, no audit trail, Consumer-Duty exposure).
- **P1-24 · Only the optimiser carries a headline ROI number** · model factory / governance / data enrichment have no CFO-level value claim. Add one KPI per stage (esp. the data-enrichment Gini 0.11→0.25, currently notebook-only).
- **P1-25 · Enrich/wrap/replace positioning lives only in DEMO_QA Q24, not the exec open** · say it before the app opens; render a phased "how to start" tier map in-app.

---

## P2 — polish / cleanup (dedup'd)
- **Two Model Factory implementations both wired; `factory.py` fabricates leaderboard/portfolio metrics** (`factory.py` docstring) — retire it or banner the simulated tab. *(Senior-dev, Decision-maker, Overview gap #1)*
- **Orphaned legacy build orchestrator** `resources/full_pipeline.yml` + `run_full_demo.py` — no doc references it; a deployer may fire the stale monolith instead of `full_build`. Delete or mark `[LEGACY]`. *(Senior-dev, SA)*
- **Duplicate optimisation spec docs** — `docs/optimization_spec.md` (US) vs `docs/optimisation_demo_spec.md` (UK). Consolidate to the UK-spelled one (matches code). *(Senior-dev, Overview gap #13)*
- **Unbounded `SELECT *` full-table read** in `datasets.py:1040` download → container OOM on a large book. Add LIMIT + truncated flag or route via volume. *(Senior-dev)*
- **`ai_cache.py:6` docstring says default `live`; code defaults `cached`** (`:38–45`). Correct the docstring. *(Senior-dev)*
- **Unpaginated asset-title resolvers** (`config.py:169,193,215`) miss matches past page 1; `_asset_cache` unlocked. Follow page tokens. *(Senior-dev)*
- **MLflow experiment paths user-scoped** across 14 training notebooks → fall back to default experiment under an SP. Use `/Workspace/Shared/.bundle/...`. *(Current-Databricks)*
- **`agents.deploy()` on Model Serving** — Databricks now recommends Databricks Apps for new agents; consider for gen2.1. Also tighten `pip_requirements` (`mlflow>=2.16` → `>=3.0,<4`), fix SDK enum string-compares, prefer `w.genie.create_space()` over raw `api_client.do()`, verify serverless `client` "5"→"6". *(Current-Databricks)*
- **`deploy_profile` var declared but never consumed**; `make_handoff.sh` referenced but missing; cost-status errors for `pwg2_motor_scorer` in core mode; dev-target SP bootstrap undocumented; runsheet/DEPLOY timing mismatch (30s vs 45s); generate-pack stall missing from runsheet IF-FAILS. *(SA)*
- **MTA repricing is an SI-ratio heuristic** (`pricing.py:948`) — ignores flood-zone/occupation changes; re-score via endpoint. **`at_fault_count_5y` formula subtracts one** (`mcp_tools.py:168`). **`behaviour_score` book-mean fallback not flagged in `explain_price`.** **No Poisson exposure offset.** *(Practitioner)*
- **Prompt-injection surface** into `explain_price`/`/chat`/factory prompts (P2 — those personas hold no write tools; keep it that way). **Audit/factory INSERTs use manual escaping** — migrate to bound params for defence-in-depth. *(Security)*
- **`ModelDeployment.tsx` "live endpoint metrics" are client-side `Math.sin`+random, unlabelled** — label `[demo simulation]` or wire real serving metrics. *(Incumbent P1 / UI/UX)*
- **"WOW MOMENT" labels in `talk_track.md`** violate the no-WOW-branding standard — rename. **Model-Factory demo banner** could read as "synthetic governance pack" — add a one-line clarifier. *(Decision-maker)*
- UI nits: QuoteReview Analytics tab no explainer; two near-identical `ChatPane` implementations (extract `TurnChat`); fixed-px chat/PDF heights clip at ≤820px; `UnderTheHood` labelled "Under the hood" not "How does this work?"; BlackBox/Addons/RatingEngineIntegration missing scaffold/disclaimer; ModelDevelopment AgentLead auto-seeds above the tabs. *(UI/UX)*

---

## Positioning findings — answerable, not code blockers *(Incumbent P0s)*
The incumbent champion's two P0s — **"the GLM emits regression slopes, not a rate-file factor table"** (`freq_glm.py:61`) and **"the rating engine is 6 arithmetic parameters"** (`pricing_scorer.py:368`) — are real, but the honest answer is the **Rating Engine Integration page** (Databricks as Radar's *data/governance layer*, not its replacement — the enrich/wrap/replace story). His own verdict: *"lean into it; call the built-in formula a demonstration arithmetic layer and the objection evaporates."* **Action: reframe in `talk_track.md` + a DEMO_QA tab-2 entry; no code change required.** This also answers Decision-maker P1-25.

## Cross-lens convergence (highest-confidence findings)
1. **SQL injection across non-optimiser routes** — Security (P0 write) + Senior-dev (P1). The optimiser was hardened at v2.2; the fix was never propagated.
2. **Commercial 5-year-freq / no annualisation** — Practitioner + Incumbent, independently.
3. **Demand model at old price** — Incumbent (P0) + Practitioner.
4. **`ADMIN_USERS` single-person** — SA (demoability) + Security (fail-open).
5. **Legacy `full_pipeline` / duplicate specs / duplicate factory** — Senior-dev + SA + Overview.

## What's genuinely strong (keep)
Motor exposure annualisation now correct + documented; full separable rated waterfall; broker agent never invents a price; MTA tied to release-of-record; `sql.py` bound-param helper + self-healing `config.py`; least-privilege grants and **no secrets / no baked serving tokens**; correct UC `@champion` aliases + FE lineage + passthrough auth; production-grade demo-reset (date-shift + self-heal grant); correct AI-cache design; the **Governance page** (bias/adequacy monitors → one-click investigate → grounded agent → real PDF pack) is the fleet's standout and the real moat.

---

## Recommended remediation order
1. **P0-1 SQL-injection write path** (+ P1-12 read sinks) via one shared identifier-sanitiser — *unambiguous, ~1 focused change, clears the BLOCK.*
2. **P0-2 QuoteTester disclaimer** — one line.
3. **Model-correctness cluster** P1-2 (commercial 5×), P1-3 (gender), P1-4 (demand-at-old-price), P1-5 (Duan/label) — fix or label; these are the practitioner/regulator drill-down.
4. **Governance maker-checker** P1-8/9 + label P1-10/11 in DEMO_QA tab 2.
5. **Platform currency** P1-13/14 (ChatAgent → ResponsesAgent; `authenticate()`).
6. **Demoability** P1-15/16/17 (DEPLOY.md, admin, cache-warm signal).
7. **UI/UX + business framing** P1-18..25.
8. **P2 cleanup** — retire `factory.py`/`full_pipeline`, consolidate specs, cap the CSV export.

*Ship bar (playbook §6.J): every P0 passes; every remaining P1 labelled + roadmapped; every "can't-show-live" question in `DEMO_QA.md` tab 2.*

---

## Remediation applied (2026-08-26, post-review pass)

Fixes were fanned out across five tranches (backend security+governance = maintainer; UI, docs/config, model-correctness, platform-currency = parallel agents). Status per finding:

| Finding | Status | Note |
|---|---|---|
| P0-1 injection (write path) | ✅ **FIXED** | `live_pricing.py` UPDATE/MERGE + all reads now use bound `:pid`; BLOCK cleared |
| P0-2 QuoteTester disclaimer | ✅ FIXED | footer added (+ BlackBox) |
| P1-2 commercial 5× annualisation | ✅ FIXED (code) | `/freq_exposure_years` divisor; **effect pending champion retrain + rebake** |
| P1-3 gender rating factor | ✅ FIXED (code) | removed from `freq_glm_motor` FEATURES + motor scorer; kept for fairness only; **pending retrain** |
| P1-4 demand-at-old-price | ✅ FIXED (code) | scores demand at the computed premium; **pending rebake** |
| P1-5 severity Duan smearing + GLM_Gamma mislabel | ✅ FIXED (code) | smearing constant + honest relabel; **pending retrain** |
| P1-6 retention circular target | ◑ PARTIAL | leakage features removed from inputs + tagged `synthetic_proxy_for_demo`; temporal label roadmapped (no renewal fields in the mart) |
| P1-7 no OOT holdout | ⏳ ROADMAPPED | DEMO_QA tab 2 (honesty entry) |
| P1-8 maker-checker | ◑ PARTIAL | promote/rollback now **admin-gated** (`_require_admin`) + audited requester; full dual-identity segregation roadmapped |
| P1-9 rate-change impact certificate | ⏳ ROADMAPPED | DEMO_QA tab 2; endpoint not built |
| P1-10 monotonicity on production models | ⏳ ROADMAPPED | DEMO_QA tab 2 |
| P1-11 fraud label / stability trail honesty | ✅ FIXED | DEMO_QA entries + governance relabels |
| P1-12 injection (reads, ~7 files) | ✅ FIXED | bound params across live_pricing/governance/pricing/factory/factory_real/review/compare/deployment/datasets |
| P1-13 ChatAgent → ResponsesAgent | ⏳ ROADMAPPED | migration would break the app-side response parser (`agent_client`, `routes/mcp`); ChatAgent still works on MLflow 3.0; coordinated migration logged |
| P1-14 private `_header_factory()` | ✅ FIXED | replaced with public `authenticate()` at all 14+ sites |
| P1-15 stale DEPLOY.md | ✅ FIXED | rewritten to gen2 targets/app/schema |
| P1-16 ADMIN_USERS single-person / fail-open | ✅ FIXED | guard now **fails closed**; app.yaml carries presenter slot + comment |
| P1-17 silent cache-warm | ◑ PARTIAL | runsheet IF-FAILS added; surfacing `ai_cache_warm.ok` in the reset response is a small remaining code item |
| P1-18..22 UI (scaffold, toggle, status dots, dup components, stale dates, tokens) | ✅ FIXED | 13 pages migrated to shared scaffold; one minor P2 (ModelDevelopment AgentLead position) deferred |
| P1-23..25 business framing | ✅ FIXED | talk_track "cost of doing nothing" + per-stage KPI + enrich/wrap/replace in the open |
| Positioning P0s (GLM slopes / rating-engine thinness) | ✅ ADDRESSED | reframed as "demonstration arithmetic layer" + Radar-integration story in talk_track + DEMO_QA Q31/32 |
| P2 cluster (full_pipeline legacy, dup specs, CSV cap, ai_cache docstring, pagination, experiment paths, WOW labels, fake-metrics label, at_fault) | ✅ FIXED | see docs/model/platform tranches |
| P2 remaining (retire/banner `factory.py`, MTA re-score, exposure offset) | ⏳ ROADMAPPED | labelled |

**Verification:** all server code compiles; frontend `tsc -b` clean; `_header_factory()` calls = 0; no unescaped user-value SQL sinks remain. **Model-correctness fixes require a champion retrain + scorer rebake + optimiser re-run to take effect — this changes the headline £ figures, which will be re-measured and the docs updated after `full_build`.**

# Standards

This demo is built and reviewed against the **Bricksurance demo standard**, which lives in one canonical place — this repo does **not** copy it.

- **Standard:** https://github.com/wryszka/bricksurance-playbook
  - `BUILD_AND_REVIEW.md` — the build method + the review scorecard (the bar)
  - `DESIGN_LANGUAGE.md` — the house visual style (canonical tokens)
  - `MANIFESTO.md` — the why
- **Reviewed against standard version:** `2.2`
- **This demo's compatibility tier:** `Tier 2 — Serverless-only` (needs a full workspace with a serverless SQL warehouse; runs end-to-end on serverless compute, no always-on clusters). The optional **live-serving tier** (Lakebase online store + route-optimized scorer + QPS tester) is a **Tier 3** module, shipped defined-but-dormant behind `deploy_profile=full`.
- **Last panel review:** 2026-08-26 — v2.2 — UI/UX expert (#8) + sceptical-practitioner re-review (`docs/REVIEW/REVIEW_REPORT_optimiser_v2.2.md`); full 7-lens panel at v2.1; Legacy at v2.0.

New here? Two entry points: **bringing this demo to Bricksurance** → it goes through the standard's review; **extending/building** → start from the standard. Copy only *this* pointer file into a demo repo — never the standard itself.

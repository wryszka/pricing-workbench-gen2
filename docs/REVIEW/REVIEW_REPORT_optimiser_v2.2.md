# Review report — Price Optimisation (playbook v2.2): UI/UX expert + sceptical practitioner

> Targeted v2.2 pass on two lenses: the NEW **UI/UX expert** (#8) and a fresh **incumbent champion / sceptical practitioner** (#7) re-review after the roadmap gaps were closed. (Full 7-lens panel = `REVIEW_REPORT_optimiser_v2.1.md`.)

- **Reviewed:** 2026-08-26 · live on pricingv2 · optimiser module @ commit 315686c
- **Verdict:** **SHIP WITH ROADMAPPED GAPS** — the UX must-fixes and the one real correctness finding are **fixed**; the rest are honest, documented limitations.

## 8 · UI/UX expert (new in v2.2) — SHIP after fixes
| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | Information hierarchy reversed — controls above the KPI headline | blocker | **fixed** — KPI rollup now leads the Optimiser tab |
| 2 | Three equally-loud CTAs (Re-solve / Approve&deploy / Explain) | blocker | **fixed** — Re-solve is the sole primary; the other two are ghost |
| 3 | Colour-only signal on factor direction | blocker | **fixed** — ▲/▼ glyph paired with the colour (factor + renewal tables) |
| 6 | Deploy button had no loading state | minor | **fixed** — disabled + spinner |
| 7 | "What am I seeing?" too jargon-heavy | minor | **fixed** — plain-language rewrite |
| 4,8,11,5,12 | Learn deep-link glyphs; responsive tab bar; row-hover; local `Section` vs canonical; sidebar width | minor/nit | roadmapped |

**Good:** credible governed core, close-the-loop beat, explainer + disclaimer present, no external chart libs, reactive Act 2, fair-value/GIPP visible, immutable decision records.

## 7 · Incumbent champion / sceptical practitioner (re-review) — conditional GO → addressed
Verified the prior fixes **hold**: GIPP solve-time enforcement = **0 breaches** live; renewal solver + main sensitivity sound.
| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | **Sensitivity re-solve ignored the portfolio repair** → scenarios incomparable under a binding floor | HIGH | **fixed** — shared `volume_repair(chosen, conv)` helper now applied in the main solve AND every sensitivity scale |
| 2 | Portfolio constraint invisible (non-binding on this book) | HIGH | **addressed** — floor + `portfolio_volume` binding surfaced in the factor-table caption; honest that it's non-binding here (DEMO_QA Q22/Q26) |
| 3 | GATE-1 lineage conditional (open on `spark_udf` fallback) | MEDIUM | documented — audited per run (`lineage_edge_emitted`); DEMO_QA Q28 |
| 4 | 500-segment scaling claimed, tested at 9 | MEDIUM | honest caveat added — DEMO_QA Q29 (O(segments) by construction; not stress-tested at 500) |
| 5 | Heavy-mode disagreement not wired into the deploy decision | LOW | labelled Phase 3 — DEMO_QA Q30 |

**Deal-breakers:** none — verdict "conditional go → pilot 10% of the book." Value story (enrich/wrap/replace) holds.

## Applied fixes (this pass, commit 315686c)
- UX: hierarchy (KPIs lead), single primary CTA, ▲/▼ dual-signal, Deploy loading state, plain-language help.
- Correctness: `volume_repair` shared by solve + sensitivity (Finding 1).
- Surface: portfolio floor + binding legend in the factor-table caption.
- DEMO_QA Q22/Q27 corrected; Q26–Q30 (drafted in-review, reviewed for accuracy) retained.

## Still open (labelled)
Learn deep-link glyphs + canonical Learn panel; responsive tab bar / row-hover polish; GATE-1 lineage edge (needs the FE/pyfunc load path); 500-segment live stress test; heavy-mode→deploy integration (Phase 3).

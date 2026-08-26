# Demo Q&A — Pricing Workbench (gen2)

~18 anticipated questions, persona-labelled **[P]ractitioner / [E]xecutive / pla[T]form-SA**, cross-linked to run-sheet beats. Answers are factual and sourced from the live schema/output — not hand-waved.

---

### Data & realism
1. **[P] Where do the numbers come from?** (B1) Every screen reads a live Unity Catalog table — `optimisation_factor_table`, `optimisation_scenarios`, `optimisation_monitoring`. Deep-link chips on the How-it-works tab open them in Catalog Explorer.
2. **[P] Is this real data?** Synthetic, illustrative motor data in a sandbox (stated in "About this demo"). The *method* is production-shaped; the magnitudes would differ on a real book.
3. **[P] Where does the technical price come from?** The champion `freq_glm_motor × sev_glm_motor` risk models (pure cost), plus expense + commission loadings = the break-even "technical price." Price enters demand as a ratio to it, never raw.

### Demand & elasticity (the credibility beat)
4. **[P] Why not model demand on price directly?** (B2) Raw price is endogenous to risk — expensive risks carry a high price *and* a high market benchmark, so raw price barely tracks competitiveness. The red-team "endogeneity" panel shows the naive model reads demand as nearly flat (dangerous). We model on price ÷ technical.
5. **[P] Is demand monotone in price?** Yes — enforced via LightGBM `monotone_constraints`. Conversion can only fall as price rises, so the solver can't exploit a spurious wrinkle.
6. **[P] How do you know the elasticity is right?** (B2) The parameter-recovery panel: the generator injected a known month-by-month elasticity and the pipeline recovered it — correlation **0.95**. On a real book you'd cross-check against historical conversion.
7. **[E] Isn't this weaker than a specialist optimiser?** Correct, and not the point. Most uplift sits in the first ~80% of sophistication. We win on breadth, openness and cost — one open platform you own end to end, testable via a shadow-mode pilot.

### Solver, constraints & governance
8. **[P/T] What stops an unsafe price?** (B4/B5) A versioned constraint YAML. The **corridor (±15% of technical) and per-segment caps are hard-enforced** at solve + deploy; **forbidden signals** are excluded by construction; the **renewal/GIPP rule is monitored** (Phase 1 optimises new business — see Q19). The file's git history is the audit trail.
9. **[T] Who can approve a deploy?** (B7) RBAC — the caller must be in `ADMIN_USERS`. On top of that the ±corridor is re-checked **server-side** before any write, so no prompt or agent can bypass it.
10. **[P] Can you make it legal in a US cost-based state?** Flip `elasticity_may_contribute: false` in the YAML — the solver then holds every segment to technical (no demand shaping). One switch, same engine.
11. **[E] What's the audit story?** Every solve and every deploy writes an immutable `audit_log` row; the factor set is stamped to `optimisation_deployment`; constraints are versioned in git. Any number traces to its constraint version + inputs.
12. **[P] What's GIPP compliance look like?** (B6) The monitoring tile tracks renewals offered above equivalent new business; the DGP anchors renewals below break-even so the compliant majority is clear and the breaching minority is flagged.

### Numbers & business case
13. **[E] What's the uplift?** (B1/B4) On this synthetic book: hold £7.95m → optimised £8.79m = **+£837k (+10.5%)**, all segments within corridor. It's model-derived (elasticity × book), not a hardcoded promise.
14. **[E] How sensitive is that to the elasticity assumption?** It scales with the injected elasticity; the base case is a 6.0 price-to-conversion slope. Halve it and the uplift roughly halves — the *pattern* (raise stable, cut price-sensitive) holds.
15. **[E] Why not just keep our current optimiser?** You don't own the decision logic, pay per seat, can't integrate your own models, and get a recommendation with no audit trail of *why*. This is open code, your models, versioned policy, full audit — one platform, no per-seat cost.

### Platform / demoability
16. **[T] Is this all serverless?** Yes — Tier 2 (serverless-only). Jobs are serverless/scale-to-zero; the optional real-time serving tier ships defined-but-dormant. No always-on clusters.
17. **[T] Can I reproduce it on a fresh workspace?** `bundle deploy` + one `full_build` run (with `enable_optimization=true`). Reset rolls the data to today, deterministically.
18. **[T] Will the live re-solve stall the room?** The Re-solve button runs the solver only (~1 min); a pre-solved frontier is the fallback (B3). AI/agent calls sit behind the yellow live/cached toggle and pre-warm.

---

## Incumbent-champion Q&A (v2.1 — the "yes, but…" that can't be shown live)

Per playbook v2.1 §7: questions raised in review that the live demo can't answer on-screen get a straight, sourced answer here, cross-referenced from the beat that provokes them. These come from the hostile incumbent-champion lens (Radar/Earnix veteran).

19. **[Incumbent · G3/B5] "Your YAML says `gipp_renewal_rule: true` — is GIPP actually enforced in the solver, or is it decoration?"** Straight answer: in **Phase 1 it is monitored, not solve-time enforced.** The solver optimises **new-business** factors and does not reprice renewals, so GIPP is tracked by the monitoring + fairness jobs (the breach tile) rather than blocked inside the solve. What **is** hard-enforced at solve + deploy is the deviation corridor and the per-segment caps. The constraint file's enforcement model is documented in `optimisation_constraints/default.yaml`. In-solver GIPP with renewal optimisation is Phase 2. *(Don't claim GIPP is enforced — say it's monitored today, enforced when renewal optimisation lands.)*
20. **[Incumbent · G1] "You only have 9 segments. My book has 500+ and elasticity varies 2–3× across them."** Correct — the 9-segment age×vehicle grid is an **illustrative** granularity, not a limit. The solver is **linear in segment count** (the decision math is O(segments); §heavy-mode is book-size-independent), so 500 segments is the same machinery with more rows — segmentation is a config choice, not a licence tier. On a real book you'd segment to your rating factors.
21. **[Incumbent] "Are forbidden signals really excluded, or is `forbidden_signals` just a list in a file?"** Enforced **by construction**: the optimised factor is keyed only on the age×vehicle segment, so gender / postcode-demographic / occupation-grade are **never optimisation levers** in the first place. The fairness job then **proxy-tests** every rating factor against those signals (`proxy_correlation_max = 0.35`) post-solve — the evidence pack is on the Monitoring tab.
22. **[Incumbent] "Can it hold total portfolio volume while lifting profit — a real portfolio constraint?"** Phase 1 optimises **per-segment** under the corridor; a portfolio-level (cross-segment) constraint like "hold total volume" is **Phase 2**. The efficient frontier already shows the volume↔profit trade-off so you can pick a point by hand; automated portfolio-level Lagrangian constraints are roadmapped.
23. **[Incumbent] "Does the closed loop test real market shift, or just replay your own assumptions?"** The advance-month loop injects a fresh ±3pp demand shock on top of the deployed prices — it's an honest calibration check on synthetic data, **not** a claim of predicting a real market regime change. On a real book, monitoring drift against actuals is the equivalent signal.
24. **[Decision-maker · pre-room] "Why move off Earnix/Radar at all?"** Not "better math" — we concede sophistication. **Cost** (serverless, no per-seat licence), **control** (you own the demand models + the constraint logic + the audit trail), **speed** (a rule change is a pull request, not a vendor roadmap item), **audit** (every price traces to its rule version + inputs + approver — the incumbent gives a recommendation with no "why"), **open** (fork it, extend it, pilot in shadow mode). Enrich / wrap / replace — your choice.
25. **[Decision-maker · B1] "How sensitive is the £837k to the elasticity assumption?"** It **scales** with elasticity (base case a 6.0 price-to-conversion slope, validated at 0.95 parameter-recovery on synthetic data); halve the elasticity and the uplift roughly halves — but the **pattern** (raise the price-insensitive, cut the price-sensitive) holds. A live sensitivity widget is Phase 2.

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
8. **[P/T] What stops an unsafe price?** (B4/B5) A versioned constraint YAML — deviation corridor (±15% of technical), GIPP renewal rule, per-segment caps (tighter for U25), forbidden signals. The solver is bound by it; the file's git history is the audit trail.
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

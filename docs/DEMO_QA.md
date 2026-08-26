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
13. **[E] What's the uplift?** (B1/B4) On this synthetic book: hold £9.38m → optimised £10.39m = **+£1.00m (+10.7%)**, all segments within corridor. It's model-derived (elasticity × book), not a hardcoded promise.
14. **[E] How sensitive is that to the elasticity assumption?** It scales **inversely** with elasticity — the base case is a 6.0 price-to-conversion slope. If demand is only half as elastic as we assume there is more room to move price and the uplift roughly doubles (~£2.1m); at 1.5× as elastic it falls to ~£624k. The *pattern* (raise the price-insensitive, cut the price-sensitive) holds throughout.
15. **[E] Why not just keep our current optimiser?** You don't own the decision logic, pay per seat, can't integrate your own models, and get a recommendation with no audit trail of *why*. This is open code, your models, versioned policy, full audit — one platform, no per-seat cost.

### Platform / demoability
16. **[T] Is this all serverless?** Yes — Tier 2 (serverless-only). Jobs are serverless/scale-to-zero; the optional real-time serving tier ships defined-but-dormant. No always-on clusters.
17. **[T] Can I reproduce it on a fresh workspace?** `bundle deploy` + one `full_build` run (with `enable_optimization=true`). Reset rolls the data to today, deterministically.
18. **[T] Will the live re-solve stall the room?** The Re-solve button runs the solver only (~1 min); a pre-solved frontier is the fallback (B3). AI/agent calls sit behind the yellow live/cached toggle and pre-warm.

---

## Incumbent-champion Q&A (v2.1 — the "yes, but…" that can't be shown live)

Per playbook v2.1 §7: questions raised in review that the live demo can't answer on-screen get a straight, sourced answer here, cross-referenced from the beat that provokes them. These come from the hostile incumbent-champion lens (Radar/Earnix veteran).

19. **[Incumbent · G3/B5] "Your YAML says `gipp_renewal_rule: true` — is GIPP actually enforced in the solver, or is it decoration?"** **Enforced — solve-time, per policy.** The renewal solver (`optimisation_renewal_solver`) prices each renewal as **`min(prior × factor, equivalent_new_business)`**, so no renewal can ever exceed its fresh new-business quote — GIPP holds **by construction** (the solved renewal factor table shows **0 breaches**). The solver picks the retention-weighted-optimal factor under the corridor + anti-shock cap. New-business factors are separately corridor+cap enforced. So: corridor + caps + GIPP are all hard-enforced at solve; only proxy-correlation is a post-solve check. *(This was a Phase-1 gap — monitored-only — closed 2026-08-26.)*
20. **[Incumbent · G1] "You only have 9 segments. My book has 500+ and elasticity varies 2–3× across them."** Correct — the 9-segment age×vehicle grid is an **illustrative** granularity, not a limit. The solver is **linear in segment count** (the decision math is O(segments); §heavy-mode is book-size-independent), so 500 segments is the same machinery with more rows — segmentation is a config choice, not a licence tier. On a real book you'd segment to your rating factors.
21. **[Incumbent] "Are forbidden signals really excluded, or is `forbidden_signals` just a list in a file?"** Enforced **by construction**: the optimised factor is keyed only on the age×vehicle segment, so gender / postcode-demographic / occupation-grade are **never optimisation levers** in the first place. The fairness job then **proxy-tests** every rating factor against those signals (`proxy_correlation_max = 0.35`) post-solve — the evidence pack is on the Monitoring tab.
22. **[Incumbent] "Can it hold total portfolio volume while lifting profit — a real portfolio constraint?"** YES — the solver enforces `total_expected_volume >= min_volume_ratio × hold_volume` (YAML default: 0.90). When a per-segment argmax trades too much volume, a greedy repair walks back the least profit-efficient increases until the floor holds. Segments the repair touched are marked `binding='portfolio_volume'`. On this synthetic book the floor is non-binding (all segments show `binding='interior'`), so to see it in action you'd tighten `min_volume_ratio` to 0.95–0.99 or resample data with more elastic segments. The solver logs repair steps and the constraint is versioned in the YAML. *(Implemented 2026-08-26; code present; not visibly binding on this book.)*
23. **[Incumbent] "Does the closed loop test real market shift, or just replay your own assumptions?"** The advance-month loop injects a fresh ±3pp demand shock on top of the deployed prices — it's an honest calibration check on synthetic data, **not** a claim of predicting a real market regime change. On a real book, monitoring drift against actuals is the equivalent signal.
24. **[Decision-maker · pre-room] "Why move off Earnix/Radar at all?"** Not "better math" — we concede sophistication. **Cost** (serverless, no per-seat licence), **control** (you own the demand models + the constraint logic + the audit trail), **speed** (a rule change is a pull request, not a vendor roadmap item), **audit** (every price traces to its rule version + inputs + approver — the incumbent gives a recommendation with no "why"), **open** (fork it, extend it, pilot in shadow mode). Enrich / wrap / replace — your choice.
25. **[Decision-maker · B1] "How sensitive is the £1.0m to the elasticity assumption?"** It scales **inversely** with elasticity (base case a 6.0 price-to-conversion slope, validated at 0.95 parameter-recovery on synthetic data): if demand is half as elastic as we assume there's more room to move price and the uplift roughly doubles (~£2.1m); at 1.5× as elastic it falls to ~£624k. The **pattern** (raise the price-insensitive, cut the price-sensitive) holds across the range. The sensitivity table (`optimisation_sensitivity`) shows the full 0.5×–1.5× sweep.

---

## Incumbent-champion follow-up Q&A (v2.2 — post-Phase-1 fixes audit)

Per playbook v2.2 §7: second-pass hostile review, probing the depth of the Phase-1 fixes.

26. **[Incumbent · B4] "When does the portfolio constraint actually bind?"** The constraint (min_volume_ratio = 0.90 in the YAML) binds only if the per-segment argmax trades more than 10% of volume for margin. On this synthetic book, the unconstrained solution already holds volume, so the repair never fires — you'll see all segments `binding='interior'`. On a real book with more price-elastic segments, it would bind. To see it on THIS book, raise `min_volume_ratio` to 0.95–0.99 or resample the generator to inject more elasticity variance. The solver will then log "repaired in N steps" and mark touched segments `binding='portfolio_volume'`.

27. **[Incumbent · B2] "If I tighten the volume floor, does the sensitivity table still make sense?"** **Yes — fixed 2026-08-26.** The volume-floor repair was refactored into a shared `volume_repair(chosen, conv)` helper that the main solve **and** each sensitivity elasticity-scale now both call, so every sensitivity scenario respects the same portfolio floor and stays comparable to base. (Previously the sensitivity re-solve was per-segment only — a real inconsistency under a binding floor.)

28. **[Incumbent · G4] "What happens if the spark_udf lineage path fails in production?"** The fallback loads the inner champion models on the driver and scores in pandas — the *numbers* are identical. However, the UC lineage edge (model version → table) is not emitted. The audit log honestly records `lineage_edge_emitted=false`, so you know it happened. For production, we enforce the spark_udf path; the fallback is a safety net, not the norm. **GATE-1 is conditional: lineage is present on the happy path, open on fallback.** Open escalation with FE to harden the spark path.

29. **[Incumbent · Q20] "Can you show me 500-segment segmentation working?"** The solver is O(segments), so 500 is *feasible* — the decision math doesn't scale with count. However, this demo uses 9 segments (3×3 age×vehicle grid) to teach the method. On a real book with 200+ rating factors, you'd segment accordingly, but the algorithm is identical. **We have NOT stress-tested the elasticity curve grid at 500 segments.** On a real deployment, you'd validate grid interpolation accuracy per your factor count and confirm solve time stays <1 min. The code scales; the claim needs live proof.

30. **[Incumbent · Act 3] "The heavy mode shows ensemble disagreement — do you *use* it to change the decision?"** No, not yet. Heavy mode (ensemble re-fits + stochastic frontier) is defined-but-dormant and optional. The disagreement map shows where models disagree, but deployment still uses the base segment-level deterministic solve. **Heavy mode is a confidence band, not a decision lever.** Phase 3 will integrate disagreement into the approval workflow (e.g., "veto a factor move if ensemble agreement <80%"). For now, it's research optionality, not core.

---

## Rating-engine integration Q&A (v2.2 addition)

31. **[Incumbent · Section 3] "Your GLM emits regression slopes — not a rate-file factor table. Radar/Earnix works with factor tables."** Correct, and that is not a conflict. The GLM in this demo is a **demonstration arithmetic layer** — six parameters to make the demo self-contained without a real rate engine. In a production integration, Databricks is the **data and governance layer around Radar or Earnix**: data prep, feature engineering, model training, and a governed REST endpoint that your rating engine can call for enrichment signals. Your rate-file GLM runs unchanged inside Radar; this platform delivers the enriched features it consumes. "Enrich, wrap, replace — in that order, at your pace."

32. **[Incumbent · Section 3] "Your rating engine is just six parameters — no real GLM exposure table, no link function, no offset for exposure."** That is intentional and stated in the demo. The demo formula is **illustrative arithmetic** to show how technical price feeds the pricing loop end-to-end. The point is not to replicate your exposure table; it is to show that (a) any technical-price input can be slotted in via the REST API seam, and (b) governance, lineage, and approval wrap around whatever produces that input — including a real rating engine's output. Bring your own rate-file output; this platform governs it.

---

## Honesty Q&A — what the demo does not show live (v2.2 addition)

Per playbook §7: these items were raised in the Phase-1 and v2.2 reviews as gaps the live demo cannot answer on-screen. Answers are sourced and marked **FIXED / ROADMAP / KNOWN LIMITATION** honestly.

33. **[Practitioner] "You train/test on the same book — where's the out-of-time (OOT) validation?"** **KNOWN LIMITATION (roadmap).** Today the train/test split is a random hash-split in-sample (reproducible, leak-free, but no temporal holdout). OOT split on the rolling-month timeline is Phase 2 — the data generator already produces a realistic month-by-month series, so the split is a config change. The Gini/PSI metrics shown are in-sample. Disclose this in a UK-regulatory conversation; the architecture fully supports OOT.

34. **[Practitioner] "Your fraud model's label is 'fraud_propensity' — what's the actual ground-truth label?"** **HONEST ANSWER.** The label in this demo is a **credit/behaviour proxy** — a synthetic score correlated with risk indicators (claims frequency, credit tier, SIC code), not a confirmed-fraud flag. There is no confirmed-fraud ground truth in a synthetic book. In production you would train on verified-fraud outcomes; this demo shows the *pipeline pattern* (train → govern → serve), not a calibrated fraud model. State this clearly; the pipeline is real, the label is proxy.

35. **[Practitioner] "The governance stability trail — are those replays of real decisions, or were they pre-seeded?"** **HONEST ANSWER (known limitation).** The governance audit log is **simulated replay** — `full_build` populates a realistic sequence of approval events, DQ checks, and model promotions to populate the history views. No real human made those decisions. The *mechanism* (every decision writes an immutable audit row; Delta Time Travel reproduces state at any date) is production-shaped; the *history* is demo data. In a real deployment you'd build the trail organically.

36. **[Practitioner] "Are monotonicity constraints enforced on the production (serving) models, or only on the demand model?"** **ROADMAP.** Monotonicity (`monotone_constraints` in LightGBM) is enforced on the **demand/elasticity model** (conversion must fall as price rises — this is a demo beat). It is **not yet enforced on the core freq/severity GLMs or the risk-uplift GBM** in production serving. GLMs are monotone by construction in well-specified cases, but the uplift GBM is unconstrained. Adding monotonicity constraints to the uplift model is a Phase 2 item.

37. **[Practitioner] "The governance maker-checker — can one person approve their own model?"** **PARTIALLY FIXED.** As of Phase 1, the app's approve-and-deploy button is gated by `ADMIN_USERS` RBAC and a server-side corridor check, but it does **not enforce a four-eyes / maker-checker rule** (the model trainer and the approver could be the same person). A two-principal requirement is on the near-term roadmap (Phase 2 governance hardening). Disclose this in a regulated UK context; the audit trail records *who* approved, so segregation of duties is policy-enforceable even before the code enforces it.

38. **[Practitioner] "The demo mixes commercial and motor — are the premiums annualised consistently?"** **IMPORTANT GOTCHA (known, documented).** Motor frequency in this demo is derived from a **5-year claims count** — annualise by dividing by 5, or the technical price will be ~5× too high. Commercial lines use annual exposure. Both are documented in the codebase (`docs/DECISIONS.md`, `pricing_workbench_motor_freq_exposure` memory note). If you show a side-by-side commercial/motor comparison live, call this out — the magnitudes are not directly comparable without the annualisation step.

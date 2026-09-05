# Price Optimisation demo — SA primer & dictionary

Who this is for: any SA running the optimisation demo (`pricing-workbench-gen2` → Price Optimisation) without a pricing background. It is not a pricing course. It draws the **defensible perimeter**: the ten ideas you must genuinely understand, the exact sentence for what sits beyond them, and the rule for everything past that.

The rule for everything past the perimeter, memorise it:
> "That's a modelling choice your actuaries would own — the platform runs whichever choice they make."

Say it without apology and move on. Nobody expects an SA to be an actuary; they expect you not to bluff.

You do NOT need to understand: GLM/GBM internals, Monte-Carlo mechanics, solver algorithms, reserving, capital, IFRS 17. None of it is load-bearing for this demo.

> **Two live-build facts** (reconciled against the deployed app, Sep 2026): the grandma segment `70+ · grpHigh` is **~316 policies**, and the solver's organic pick for it is **+7.5%**, not +5% — the profit curve is flat across +2.5–7.5% on this small segment, so +7.5% is the genuine optimum. The "5%" used below is the *illustrative principle*; read the actual factor live off the screen.

---

## The ten concepts (the required mental model)

**1. Technical price.**
The break-even cost of insuring one policy: expected claims plus expenses. Every price in the demo is expressed *relative to* this floor. If you remember one thing: technical price answers "what does this risk cost us?", optimisation answers "what should we charge, given that?"

**2. The demand curve (elasticity).**
For each customer segment: as price goes up, what fraction still buys? A steep curve = price-sensitive shoppers; a flat curve = loyal customers who barely react. This is the *one extra model* optimisation adds over traditional pricing — everything else (risk models, rating) an insurer already has.

**3. Why lost quotes matter.**
You cannot learn price sensitivity from customers who said yes. The quotes that walked away carry the price signal — that's why the data foundation includes lost quotes, and why this is a data-platform story before it's a modelling story.

**4. The endogeneity trap (Beat B — learn this one properly).**
Riskier customers get quoted higher prices *and still buy* (they have to insure). So a naive model looking at raw price concludes "price barely affects demand" — a false read that leaves money everywhere. The fix: model demand on price *relative to the technical price*, so the risk-driven part of the price cancels out and only the pricing decision remains. The "wrong-model" panel shows both models side by side; the naive one is the trap.

**5. The corridor.**
A hard bound (±15% here) around the technical price that no optimised price may leave — enforced *at solve time*, meaning the solver cannot produce a violating price at all, and re-checked at deploy. Distinguish this from a guideline someone checks afterwards: the difference is the governance story.

**6. Why the machine raises loyal segments (the grandma logic).**
If a segment's curve is flat on the upside — raise price ~5%, lose almost nobody — a profit maximiser will always raise it. That's not a bug; it's the objective doing its job. Whether it *should* is a policy question, which is the whole twist of Beat D. *(In the current build the solver picks +7.5% for grandma — same logic, larger number.)*

**7. GIPP in one sentence.**
UK FCA rule (2022): a renewing customer's price may not exceed what an equivalent *new* customer would pay through the same channel. It exists because insurers systematically "price-walked" loyal customers upward year after year. In the demo it's checked at solve time and shown as the Conduct column.

**8. Legal floor vs fair-value standard (Beat D's twist — the beat dies if you can't articulate this).**
GIPP is the law — the floor. Consumer Duty asks a broader question: is this customer getting fair value at all? A price can pass GIPP and still fail fair value (loading a loyal, older, non-switching segment). The amber pill flags the second question, and the point of the demo is: the machine can check the floor, only a human can set the standard.

**9. What "Re-solve" actually does.**
It tries thousands of candidate price-factor sets against the fitted demand curves and keeps the best one that satisfies every constraint. It does not retrain any model and it isn't AI magic — it's a governed search job. (That's why it's fast, and why N is a text box.)

**10. Ensemble disagreement = model risk (Part 2 / heavy mode only).**
One demand model is one opinion. Heavy mode refits demand as eight candidate specifications and re-solves each segment's price under all of them. Where they agree, the move is robust; where they split, the move is a model artifact — hold it or widen the corridor. That's "model risk, made visible."

---

## Dictionary

Written to double as **app panel copy** — each entry is one tooltip-length definition (≤2 sentences, no jargon-defined-by-jargon), followed where useful by an italic *demo note* for the presenter only. If enriching the app: attach the tooltip text to the matching panel/column header; leave the demo notes out of the UI.

**Technical price** — The break-even cost of a policy: expected claims plus expenses. All optimised prices are expressed as a factor on this baseline.

**Street price / final premium** — What the customer is actually charged: technical price × the optimised factor, bounded by the corridor.

**Price factor** — The multiplier applied to a segment's technical price (e.g. 1.05 = +5%). The factor table is the solver's output and the thing that would export to a rating engine.

**Segment** — A group of similar customers priced together (e.g. age band × vehicle group). The demo optimises per segment; *demo note: grandma = `70+ · grpHigh`, ~316 policies, solves to +7.5% in the current build.*

**Conversion** — The share of quoted customers who buy. The quantity the demand model predicts and the y-axis of every elasticity curve.

**Demand model** — A model predicting conversion as a function of price (relative to technical). The one extra model optimisation requires.

**Elasticity** — How strongly conversion reacts to a price change. Elastic = shoppers, inelastic = loyal. *Demo note: sensitivity scales inversely — less elastic segments attract more uplift.*

**Monotonic constraint** — A rule built into the demand model forcing conversion to only fall as price rises. Guarantees the model can't produce nonsense like "raise the price, sell more."

**Endogeneity** — The statistical trap where risk drives both price and purchase, making demand look price-insensitive. Removed here by modelling on price relative to technical. *Demo note: the "wrong-model" panel exists solely to show this trap.*

**Lost quote** — A quote that didn't convert. Carries most of the price signal; without lost quotes there is no demand model.

**Objective** — What the solver maximises: expected profit, volume, or a weighted blend. Set by a human; the machine never chooses its own goal.

**Expected profit** — Conversion-weighted margin of street price over technical cost, before fixed overheads. *Demo note: if asked "profit after what?" — say exactly that; don't imply net underwriting result.*

**Constraint** — A rule the solver must respect: the corridor, segment caps, forbidden signals, GIPP, a portfolio volume floor. Lives in a versioned YAML file — the "pricing policy" as an explicit artifact.

**Corridor** — The hard band (±15%) around technical price that no optimised price may leave. Enforced at solve time and re-checked at deploy.

**Forbidden signal** — A variable the model is never allowed to use (protected characteristics and their proxies). Excluded by construction; proxy-tested after solve by the fairness job.

**Solver / Re-solve** — The governed job that searches thousands of candidate factor sets and returns the best one satisfying all constraints. Search, not training.

**Efficient frontier** — The curve of best-available trade-offs between volume and profit. Any point below it is leaving money or customers on the table.

**Waterfall** — The chart decomposing where the profit uplift comes from, segment by segment.

**GIPP** — UK FCA pricing rule: a renewal price may not exceed the equivalent new-business price. Checked at solve time; shown in the Conduct column.

**Consumer Duty / fair value** — UK conduct standard asking whether the customer receives fair value overall — a higher bar than GIPP. The amber "fair-value review" pill flags segments deserving a human call.

**Price walking** — Raising loyal customers' renewal prices year after year because they don't shop around. The practice GIPP banned.

**Fair-value evidence panel** — The pack a fair-value committee would review: proxy correlation, disparate impact, vulnerability screen.

**Constraint author (agent)** — An agent that turns a plain-language instruction into a drafted change to the constraints YAML. Drafts only; a named human reviews the diff and commits.

**Decision record** — The immutable row written when prices deploy: who, when, why, which model version, which constraint version.

**Provenance block** — The chain shown under an explained price: model version → constraint version → approver → decision record. The "from her premium to the audit trail" artifact.

**Deploy gate** — A Unity Catalog stored procedure that re-checks the corridor and writes the audit record. Permission to run it is a per-person database grant, not app logic.

**Predicted vs realised** — The monitoring view comparing what the model expected with what happened after prices went live. *Demo note: on synthetic data this reconciles by construction — say so; the point is the pattern.*

**Advance one month** — The demo control that rolls the synthetic book forward under the deployed prices so predicted-vs-realised has something to compare.

**Heavy mode** — The optional second gear: refit demand as an ensemble and score the whole book across hundreds of candidate plans and demand draws. "Smart when you can, exhaustive when it matters."

**Ensemble** — Several differently-specified demand models fitted to the same data. Agreement between them is evidence a price move is real.

**Disagreement map** — Per-segment spread of the ensemble's recommended prices. Green = models agree (deploy with confidence); amber = they split (hold or widen the corridor).

**Monte-Carlo demand draws** — Simulating "who actually converts" many times per candidate plan, since each customer converts with a probability. Produces the outcome distribution instead of one number.

**P5–P95 band** — The realistic worst-to-best range of a plan's outcome from the draws. A tight band above today's line often beats a higher but wider mean.

**Probability of missing plan** — Per candidate: the chance the outcome lands below today's profit. Computed in the data; *demo note: don't point at a chart element for it — it's a number, not a mark.*

**Scored evaluation** — One policy × one candidate plan × one demand draw, computed as cheap arithmetic on fitted curves — not a model inference. *Demo note: own this distinction out loud before anyone raises it.*

**The receipt** — The caption the heavy run writes about itself: evaluations, wall-clock, estimated cost. Measured by the job, read back by the app — never typed by the presenter.

---

## Operational one-pager (what each control really does)

- **Re-solve (Optimiser)** → runs the live solver job (~1 min; ~90s ceiling). Cold start after idle ≈ 45s extra — warm it before any audience.
- **N (scenarios)** → the candidate count the solver explores. A text box on purpose; set it on camera.
- **Objective selector** → switches what the solver maximises (profit / volume / retention-weighted blend). The retention-weighted tilt is fallback route (a) for Beat D.
- **Fair-value pill (amber, factor table)** → one click to the fair-value evidence panel. Warm it.
- **constraint_author (agent panel)** → drafts a YAML change from plain language → diff view → attributed apply. Fallback route (b): show the pre-edited override in `optimisation_constraints/default.yaml`.
- **Approve & deploy** → calls the UC stored procedure over OBO: corridor re-check + immutable audit row. Requires an EXECUTE grant on the procedure for *your* identity — verify before every session or the beat is denied by UC.
- **Explain this price → demo case button** → loads the grandma quote, renders decomposition + provenance block.
- **Advance one month (Monitoring)** → rolls the synthetic book forward so predicted-vs-realised populates.
- **Heavy tab: "Re-run live (small)" (green)** → the room-safe live proof, ~1–2 min. **"Full heavy run" (black)** → the ~4.5B-eval run. Never click the black one live; the pre-computed default is what you narrate.
- **Warm-up ritual (before any audience):** one throwaway call each to serving, both agents (fresh uncached question), fairness panel, and — if you'll click it — one small heavy re-run. Keep fallback screenshots: solved frontier + factor table with Conduct column, fairness panel, YAML diff, heavy map + frontier + caption.

## The three answers that cover 90% of hard questions

1. **"How does this reach my rating engine (Radar Live / Guidewire)?"** → "The factor table is a governed Delta table — publish it to your rating engine like any rate revision. This replaces the analysis and decision layer, not your execution path."
2. **"Is any of this real data / a real model?"** → Concede first: "Synthetic book, production-shaped patterns. The demo shows the mechanics and the governance; your data and your actuaries' models drop into the same slots."
3. **Anything about modelling choices you can't answer** → the perimeter rule: "That's a modelling choice your actuaries would own — the platform runs whichever choice they make."

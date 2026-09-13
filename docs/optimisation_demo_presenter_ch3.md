# Optimisation demo — presenter script (Chapter 3)

~5 minutes, single presenter. App → **Price Optimisation** tab → chapter selector → **Chapter 3**
(https://pricing-workbench-gen2-7474655676955816.aws.databricksapps.com). Chapter 2 chose one plan
under one demand estimate. Chapter 3 asks: what if demand or market conditions turn out different?
We evaluate plans across several **worlds** and pick the one whose **worst** outcome is best. Read
every number off the screen and name its unit. Everything is **synthetic**; worlds are declared
**stress scenarios**, not forecasts and not probabilities.

Before recording: open Chapter 3 once and do one throwaway **Run robust decision** so the job's
compute is warm (it solves several worlds; first run has cold-start latency).

Live numbers to expect (they reproduce): **6 worlds** (2 validated demand models × 3 market/cost
scenarios), 98% per-world sales floor, **robust worst-uplift ≈£16,370 ≥ nominal worst-uplift ≈£16,357**;
robust grandma **+1%** vs nominal **+2%**. The robustness benefit is honest and modest.

---

## A · Test run — click through, no talking (do this once, silently)

1. **Chapter 3** loads → header + a disclaimer that worlds are declared stress scenarios; a **Run robust decision** button.
2. Click **Run robust decision** → "Solving worlds…" spinner, an **Open run** link appears; when it finishes the **Robust vs nominal** section renders.
3. **Robust vs nominal** shows four metrics: **Robust — min uplift ≈£16,370**, **Nominal — min uplift ≈£16,357**, **Worlds 6** (2 demand models), **Sales floor 98%**.
4. **Plan comparison** table renders: rows **baseline / nominal / robust**; columns Min uplift, Grandma factor, Largest move, then one column per world; green cells = positive uplift, amber = below that world's sales floor. Robust's worst-world cell is its min-uplift.
5. Grandma factor column: robust **+1%**, nominal **+2%**; the run id + Databricks run link show at the foot.

If all green, record.

---

## B · Talk track (click + say)

### The question (0:00–0:45)
**CLICK:** Chapter 3, read the disclaimer.
**SAY:** "Chapter 2 picked the best plan assuming one demand estimate. But the estimate could be wrong, and the market could move. So here we define a handful of worlds — two validated demand models crossed with three market-and-cost scenarios, six worlds in all. These are deliberate stresses we chose, not forecasts and not weighted by probability. The question: is there a plan that holds up across all of them?"

### Run it (0:45–2:00)
**CLICK:** **Run robust decision**; when it finishes, open the run link.
**SAY:** "The job evaluates candidate plans in every world and solves a robust optimisation — maximise the *worst* world's expected-margin uplift, while keeping the 98% sales floor in every world, not just on average. It's the same kind of program as Chapter 2 with an extra variable that tracks the worst case. It ran across all six worlds on Databricks."

### Robust vs nominal (2:00–3:30)
**CLICK:** the two min-uplift metrics, then the comparison table.
**SAY:** "Two plans to compare. The nominal plan maximises one world's margin — its worst-world uplift is about £16,357. The robust plan maximises the worst world directly — about £16,370. Read across the table: each plan in each world. The robust plan's worst column is higher than the nominal plan's worst column — that's the whole point. The gap is small here, and that's an honest finding: on these worlds, insuring against the bad scenarios costs very little."

### Grandma and the moves (3:30–4:30)
**CLICK:** the Grandma factor and Largest move columns.
**SAY:** "You can see how the plans differ in behaviour. The robust plan moves grandma's price about +1%, the nominal plan about +2% — robust is more cautious, because a big move that wins in one world can lose in another. Amber cells, if any, are worlds where a plan breaches the sales floor. And if the robust optimum ever came back equal to baseline, that itself would be the finding: the safe move is to hold."

### The scope (4:30–5:00)
**SAY:** "So — a plan chosen to be resilient across declared scenarios, solved on Databricks, on synthetic data. 'Worst case' means worst of the worlds we included, in expectation. It is not a probabilistic forecast, and it doesn't certify any of these worlds will happen. It shows the decision method, honestly."

---

## Decision Review sequence (new — ~60–90s, film after the plan comparison)

The distinctive beat: a challenge from **outside** the optimiser. All figures are read live;
the assistant is read-only (it cannot choose prices, change policy, run a scenario or approve).

**A · Silent test-run (before recording)**
1. After a six-world result renders, open **Decision Review → Challenge this plan**.
2. Confirm ≤3 cards appear; the top card is the **claims-stress coverage gap** (a finance
   planning assumption of **+8%** sits outside the tested claims stresses, max **+5%**).
3. Confirm the card shows the drafted stress `{"cost_scale": 1.08}`, an inference label, and
   an "Evidence & limits" disclosure with the evidence IDs and what it cannot establish.
4. Click **Investigate** on that card; confirm it records (attributed to you).
5. Click **Prepare committee brief**; confirm the brief shows the trade-off, "no human
   decision recorded / not approved", the unresolved count, and the disclaimer.

**B · Talk track (click + say)**
- **CLICK:** Decision Review → Challenge this plan.
  **SAY:** "This assistant doesn't price anything — it helps me challenge the decision with
  evidence, including evidence from outside the model. It's read-only."
- **CLICK:** the top card (the +8% coverage gap); point at the evidence IDs.
  **SAY:** "It's found something the optimiser couldn't: Finance plans claims inflation at
  eight percent this year, but the scenarios we stress-tested only went to five. So this plan
  has never been evaluated under Finance's own assumption. It even drafts that scenario for me
  — but it's careful to say a planning assumption is not proof claims will actually inflate."
- **CLICK:** Investigate (records the disposition); then, if filming the loop, add the +8%
  world and re-run via the normal control, showing the actual outcome (may be no change or
  infeasible — never tuned to 'win').
  **SAY:** "I decide what to do. I'll investigate it — that's recorded against this decision."
- **CLICK:** Prepare committee brief.
  **SAY:** "And here's the brief for the committee — the trade-off, which challenges are still
  open, who owns it, and the honest approval state. Every number is computed, not narrated, and
  it never calls a feasible plan 'approved' or 'safe'."

> **Honest labelling for the recording:** the panel shows "AI narration unavailable — deterministic
> evidence review". The findings, ranking and cards are computed deterministically (no language
> model in this build); say "evidence review", not "the AI said". The per-person approval *denial*
> for a non-approver is shown as a **labelled simulation** (single demo account).

## What this demo proves / doesn't
- **Proves:** you can evaluate a plan across multiple declared worlds and choose one that maximises the worst-case expected uplift while holding a sales floor in every world; the robust-vs-nominal trade-off is shown explicitly, including when it's small.
- **Does not prove:** that the worlds are likely, that they're probability-weighted, or that "worst case" covers anything outside the included worlds. Synthetic throughout; expected outcomes, not realised.

## Answers to the obvious questions
- **What is a "world"?** A validated demand model paired with a declared market/cost scenario. Six here = 2 models × 3 scenarios.
- **Robust vs nominal — the difference?** Robust maximises the worst world's uplift; nominal maximises one world's margin over the same all-world feasible set. Robust's worst case is by construction no worse than nominal's.
- **Why is the benefit so small?** On these particular worlds the plans barely diverge — an honest result, not a bug. The method surfaces that rather than manufacturing a dramatic gap.
- **Are the worlds weighted by probability?** No. They're declared stresses; no probabilities are applied.
- **What does the 98% floor do here?** It must hold in *every* world, not on average — a plan that breaches it in any world is infeasible (amber in the table).
- **What if robust equals baseline?** That's a valid finding: across the stresses, holding current prices is the resilient move.

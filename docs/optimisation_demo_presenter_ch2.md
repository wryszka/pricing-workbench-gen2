# Optimisation demo — presenter script (Chapter 2)

~9 minutes, single presenter. App → **Price Optimisation** tab → chapter selector → **Chapter 2**
(https://pricing-workbench-gen2-7474655676955816.aws.databricksapps.com). Chapter 1 was one segment,
supplied probabilities, six prices. Chapter 2 is **a whole portfolio**: nine synthetic segments, a
learned demand model, individual costs, and prices chosen for all segments at once under a total
sales floor. Read every number off the screen and name its unit. Everything is **synthetic**; the
demand model is fit on a **synthetic generator**, not real customers.

Before recording: open Chapter 2 once (warm it), confirm the **Prepared model** pill says
"validation passed", the **book today** table shows nine segments, and do one throwaway
**Margin first** run so the MILP job's compute is warm (first run has cold-start latency). If the
approve button matters to your take, either pre-approve once so a release already shows, or read the
"Approve" beat below and know it records via the attributed path unless you've re-consented for OBO.

Live numbers to expect (frozen snapshot, they reproduce): baseline **≈3,735** expected sales /
**≈£865,865** margin across **5,000** opportunities · nine segments; **Margin first → 2,990 / £998,194**;
**Protect sales ≥ 98% → 3,660 / £891,158**. Grandma segment is labelled **70+ · grp≥30**.

---

## A · Test run — click through, no talking (do this once, silently)

1. **Chapter 2** loads → **Prepared model** shows a green "validation passed" pill, a model version, a calibration-error figure (≤0.05), and "monotone ✓".
2. **The book today** renders: four metrics (Opportunities 5,000 · Baseline expected sales ≈3,735 · Baseline premium · Baseline margin ≈£865,865) and a nine-row segment table; the grandma row (**70+ · grp≥30**) is highlighted; the representative-opportunity note reads its claims + expenses + commission breakdown.
3. **Choose the plan** → click **Margin first** → a "Running" pill, then a result card: **Completed Databricks run**, ≈**2,990 / £998,194**, sales floor "none", per-segment factor table, and an **Approve & release (approver)** button.
4. Click **Protect sales ≥ 98%** → a second card appears beside the first: ≈**3,660 / £891,158**, sales floor 98%. The two cards sit side by side; grandma's factor differs between them.
5. On one card click **Approve & release (approver)** → it turns to "Approved & released" with a small note saying which path ran ("as you (OBO)" or "attributed record"); the **Review & release** section now shows an active release (id, run id, approved-by, timestamp).
6. **Check** → click **Advance one synthetic period** → after the job, a table of expected vs observed sales and margin per segment appears; observed sits close to expected.

If all green, record.

---

## B · Talk track (click + say)

### The prepared model (0:00–1:15)
**CLICK:** Chapter 2, point at the Prepared model pill + calibration + monotone.
**SAY:** "Chapter 1 used probabilities I supplied. Here the purchase probability is a model — fit offline on a synthetic generator, then frozen. Before it's allowed anywhere near a plan it has to pass a validation battery: calibration error under five percent, and monotonic — higher price never predicts higher demand. It passed, so it's eligible. If it failed, the Choose buttons would be disabled. That gate is the point: an un-validated model can't drive a price here."

### The book today (1:15–2:45)
**CLICK:** the book-today metrics and the nine-row table; the grandma row; the representative note.
**SAY:** "This is the portfolio at today's prices — nine synthetic segments, five thousand opportunities, about £866,000 of expected margin. Each segment has its own cost and its own demand curve. Take grandma-in-a-BMW: for a representative opportunity you can see the modelled cost broken out — expected claims, per-sale expenses, and commission. There's no median-customer shortcut; we sum probability-weighted margin over individuals."

### Margin first (2:45–4:15)
**CLICK:** **Margin first**; when it finishes, open the Databricks run link.
**SAY:** "Objective: maximise expected margin, no sales requirement. The app submits a job that scores every segment at every candidate price against the frozen model, then solves a portfolio optimisation — a mixed-integer program — to pick one price per segment. Best expected margin is about £998,000, at about 2,990 expected sales. That's up on baseline margin, but notice sales fell — margin-first buys profit by walking away from some customers."

### Protect sales (4:15–5:45)
**CLICK:** **Protect sales ≥ 98%**; let the second card land.
**SAY:** "Same model, same prices, same objective — I add one business rule: keep total expected sales at least 98% of baseline. Now the answer is about 3,660 sales and £891,000 margin. We gave up roughly £107,000 of margin to hold volume. And grandma's factor changes between the two plans — because the constraint is on the whole portfolio, one segment's price moves to protect the total. Same lesson as Chapter 1, at portfolio scale: I changed the requirement, the optimiser changed the plan."

### Approve & release (5:45–7:15)
**CLICK:** **Approve & release (approver)** on the plan you want; then point at the Review & release record.
**SAY:** "Approving isn't a UI flag. First the plan is recomputed deterministically from the saved scores — if the numbers on the card don't reproduce, approval is refused. Then it calls a Unity Catalog stored procedure that writes the approval and the release to an append-only record. The gate is a per-person EXECUTE grant on that procedure: the app tries to call it as me over on-behalf-of auth, so only an approver can release. Where on-behalf-of SQL isn't available it records my authenticated identity through the same governed procedure — the button tells you which path ran, and the record says so too. Either way it's attributed, reproduced, and append-only, and the release is chained to the one before it."

### Check (7:15–8:30)
**CLICK:** **Advance one synthetic period**; read the expected-vs-observed table.
**SAY:** "Last, an honesty check. We roll the released plan forward one synthetic period — but outcomes are drawn from the generator, not from the model's own predictions, so it's a real test, not a mirror. Expected versus observed, per segment; they land close. This checks the arithmetic holds up out of sample on synthetic data — it does not validate real demand or realised claims."

### The scope (8:30–9:00)
**SAY:** "So: a validated demand model, a portfolio optimiser that respects a business constraint, a governed approval that's attributed and reproducible, and a forward check — all on Databricks, all on synthetic data. It proves the workflow and the governance. It does not certify the demand model against real customers or issue a real price."

---

## What this demo proves / doesn't
- **Proves:** a model must pass validation to be eligible; the optimiser trades margin against a portfolio sales floor transparently; approval is deterministic-recompute + append-only + attributed; a forward check draws from the generator, not the model.
- **Does not prove:** that the synthetic demand model reflects real customers, that costs are real, or that any factor is production-ready. "≥ 98% of baseline" is a floor on *expected* sales, not a guarantee.

## Answers to the obvious questions
- **Why do sales fall under Margin first?** With no floor, the optimiser raises some prices past the volume-maximising point — more margin per sale, fewer sales, higher total margin.
- **Why does grandma's factor differ between the two plans?** The floor is on the whole portfolio; holding total sales forces some segments (grandma among them) to a different price than margin-first would pick.
- **What is the "MILP"?** A mixed-integer program over a finite grid of candidate prices per segment — HiGHS via SciPy — picking exactly one price per segment to maximise expected margin subject to the floor.
- **What does "validation passed" gate?** The Choose buttons. A model that fails calibration or monotonicity is not eligible to drive a plan.
- **Is the approval a real per-person gate?** The design is a UC EXECUTE grant enforced over OBO. If your browser session has consented to the `sql` scope it runs as you; otherwise it records your authenticated identity via the app service principal through the same procedure. The button states which.
- **Is the Check validating the model?** No — outcomes are drawn from the frozen generator, independent of the model's predictions; it's an out-of-sample arithmetic check on synthetic data.

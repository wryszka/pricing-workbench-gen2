# Optimisation demo — presenter script (Chapter 1)

~8 minutes, single presenter. App → **Optimisation demo** tab
(https://pricing-workbench-gen2-7474655676955816.aws.databricksapps.com). Two views: **Explain**
(worked example) and **Run on Databricks** (the same example as a real job). Read every number off
the screen and name its unit. Everything is a **synthetic teaching example**.

Before recording: open the tab once (warm it), confirm the six-row table renders, and do one throwaway
**Run on Databricks** so the job's compute is warm (~1st run has cold-start latency).

---

## A · Test run — click through, no talking (do this once, silently)

1. **Explain** view loads → segment card shows **1,000 opportunities · £800 modelled cost/sale · £1,000 current price**; "Synthetic teaching example" banner present.
2. Screen 2 → six-row table; click **Show the margin** → margin/sale + expected total margin columns appear; click a row → its arithmetic line appears; the two charts (demand, expected margin) render with six points.
3. Screen 3 → best price shows **£1,100 / 700 / £210,000**; the £1,150 note is present. Click **Require at least 830 customers** → four rows grey out ("Below the sales target"), winner flips to **£950 / 830 / £124,500**.
4. Click **Run this example on Databricks** → Run view. Panel A shows the same inputs, objective "Maximise expected margin", a minimum-customers box + **Require 830 customers**.
5. Leave the box blank → **Run on Databricks** → Panel B shows **Running** then an **Open Databricks run** link; Panel C shows **£1,100 / 700 / £210,000**, "Completed Databricks run".
6. Set **Require 830 customers** → **Run** again → a second result card appears beside the first: **£950 / 830 / £124,500**. Both visible side by side.

If all green, record.

---

## B · Talk track (click + say)

### The question (0:00–0:45)
**CLICK:** Explain view, screen 1.
**SAY:** "We've got 1,000 potential customers in a synthetic segment — older drivers in higher-group cars; we'll call it our grandma-in-a-BMW example. Each sold policy is expected to cost us £800, and today we charge £1,000. Cost alone doesn't tell us the best price: charge more and we earn more per sale, but fewer people buy. We have to weigh both."

### Demand and margin (0:45–2:00)
**CLICK:** screen 2; **Show the margin**; click the £1,100 row.
**SAY:** "For each candidate price we have a purchase probability — an assumption we've supplied, not something learned from real customers. Expected customers is opportunities times that probability. Margin per sale is price minus the £800 cost. Multiply them for expected total margin. At £1,100 we expect 700 customers, £300 each above cost — 700 times £300 is £210,000."

### The best answer, then the requirement (2:00–3:00)
**CLICK:** screen 3 (best = £1,100); then **Require at least 830 customers**.
**SAY:** "Maximising expected margin, the best of these prices is £1,100 — even though £1,150 earns the most per sale, its conversion falls off a cliff to 45%, so it makes less in total. Now the human adds a requirement: win at least 830 expected customers. That rules out the four higher prices, and the best permitted answer becomes £950. Same calculation, same objective — I changed the business requirement, and the answer changed."

### Move to Databricks (3:00–3:30)
**CLICK:** **Run this example on Databricks**.
**SAY:** "Now the exact same example, run as a real job on Databricks — not arithmetic in the browser."

### Run A (3:30–5:00)
**CLICK:** leave the requirement blank → **Run on Databricks**; when it finishes, open the run link.
**SAY:** "The app submitted a Python job. It reads the input table, evaluates the six prices, applies our requirement — none this time — and writes the results back, keyed to this run. Six candidates evaluated; the best expected margin is £210,000 at £1,100. We can open the job and inspect every step."

### Run B and compare (5:00–6:30)
**CLICK:** **Require 830 customers** → **Run** again.
**SAY:** "Same costs, same model, same prices — now with the 830 requirement. £950 wins: more expected customers, at an explicit margin cost of about £85,000 versus the unconstrained plan. Both runs are here side by side, each read from its own saved result."

### Inspect (6:30–7:30)
**CLICK:** point at the candidate table, run id, input version, run link.
**SAY:** "Every number traces back: the candidate rows, which were feasible, the one we selected, the requirement that produced it, and the input version it ran against — all saved under this run's id, not a shared ‘latest’ value."

### The limit (7:30–8:00)
**SAY:** "So — a transparent optimisation calculation running on Databricks, conditional on our assumptions. It proves the calculation runs and stays inspectable. It does not validate real-world demand or deploy a production price. That's the honest scope."

---

## What this demo proves / doesn't
- **Proves:** you can read governed inputs, run a real calculation on Databricks, and inspect/reproduce the result by run id.
- **Does not prove:** that the demand assumptions are real, that £800 is a real cost, or that any price is production-ready. "At least 830" is a floor on *expected* customers, not a guarantee.

## Answers to the obvious questions
- **Why £1,100 over £1,150 (Run A)?** £1,150 earns most per sale but converts at 45%; 450×£350 < 700×£300.
- **Why £950 in Run B?** Only £900 and £950 give ≥830 expected customers; of those, £950 has the higher margin.
- **What changes between runs?** Only the sales requirement. Objective, costs, prices and probabilities are identical.
- **Where did the probabilities come from?** Supplied synthetic assumptions.
- **Is 830 a guarantee?** No — a floor on expected customers.
- **What's in £800?** A supplied total modelled variable cost per sale (the costs we chose to model), not the workbench's claims-only figure.
- **What ran on Databricks?** A Python job that read the input table, ran the shared calculation, validated it, and saved candidate rows + a run record.

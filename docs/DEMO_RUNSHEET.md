# Demo Run-sheet — Pricing Workbench (gen2)

House format (playbook §4): each beat is **GO** (where to click) · **DO** (the one action) · **SAY** (audience words, ≤20 words, no platform jargon) · **IF ASKED / IF FAILS** (fallback + Q&A ref). Timings measured over 3 runs on pricingv2.

**Audience framing:** open C-suite (outcome), land practitioner (their process), reproducible by any SA. **Default runtime ≤15 min; beats are composable.** **Cut order (if short):** drop beats 7→6→3.

**Before the room:** run the reset (rolls dates to today, ~30–40 min — do it well ahead), warm the AI cache, confirm the yellow toggle reads *cached*. Have a pre-solved frontier screenshot ready as the beat-4 fallback.

**Canonical question (the sentence the persona says):** *"How do we price motor competitively without walking the margin — and prove to a regulator why every price moved?"*

---

## Act 1 — the governed pricing loop (motor)

**Beat 1 · The book today** — ~40s
- **GO:** Price Optimisation → Optimiser tab.
- **DO:** read the roll-up KPIs.
- **SAY:** "Here's the motor book — **£X GWP**, priced at today's rates. We think there's margin left on the table."
- **IF ASKED:** "Where do these come from?" → live UC tables (Q1). **IF FAILS:** tables always populated post-reset.

**Beat 2 · Model demand honestly** — ~60s
- **GO:** Demand & red-team tab.
- **DO:** flip through the elasticity curve, then the "wrong-model" panel.
- **SAY:** "Demand falls as price rises — **enforced**, not hoped. And here's why pricing on raw price fools you: the naive model barely sees the drop."
- **IF ASKED:** "Is the elasticity real?" → parameter-recovery panel, corr 0.95 (Q6). This is the credibility beat — do not skip.

**Beat 3 · Explore the futures** — ~90s
- **GO:** Optimiser → objective front door.
- **DO:** set N = 3,000, pick *Expected profit*, click **Re-solve**.
- **SAY:** "We just scored **thousands** of price sets in seconds. N is your choice, not a licence tier."
- **IF FAILS:** solver run stalls → show the pre-solved frontier screenshot; "here's the last run" (Q3).

**Beat 4 · Decide under policy** — ~60s
- **GO:** the frontier + per-segment waterfall.
- **DO:** point at the waterfall — standard risks up to the cap, young drivers cut.
- **SAY:** "The optimiser **raised** stable segments and **cut** price for shop-happy young drivers — every move inside the ±15% corridor."
- **IF ASKED:** "What stops a bad move?" → the constraint YAML (beat 5).

**Beat 5 · Open the pricing policy** — ~50s
- **GO:** How it works tab → constraint YAML panel.
- **DO:** scroll the YAML; mention the U25 override + the jurisdiction toggle.
- **SAY:** "**This file is the pricing policy.** It's versioned in git — the history is your audit trail. Change it by pull request."
- **IF ASKED:** "US cost-based state?" → flip `elasticity_may_contribute:false`, solver holds to technical (Q8).

**Beat 6 · Reality check** — ~40s
- **GO:** Monitoring tab.
- **DO:** show drift + the GIPP/corridor tile.
- **SAY:** "The model stays calibrated month to month, and renewals respect the fair-value rules — **watched, not assumed**."

**Beat 7 · Human approves, gate enforces** — ~40s
- **GO:** Optimiser → Approve → deploy.
- **DO:** click Approve & deploy.
- **SAY:** "The human sets the policy; the system enforces it — the corridor is re-checked **server-side**, then it's audited. No prompt gets past that."
- **IF ASKED:** "Who can approve?" → RBAC (ADMIN_USERS) on top of the corridor (Q9).

---

## Act 2 — reactive second act (aggregator squeeze) *(Phase 2/3 — see roadmap)*
External event → drift sentinel detects → planner designs a run → solver decides under constraints → gate routes (auto in-corridor / human outside) → deploy. Runs live once the agentic layer + `advance_period` ship. Until then: narrate it and end Act 1 on "next cycle we'd re-run and measure the result."

---

**Per-beat timings (3-run avg):** B1 0:40 · B2 1:00 · B3 1:30 · B4 1:00 · B5 0:50 · B6 0:40 · B7 0:40 → **~6:20** for the full Act 1.

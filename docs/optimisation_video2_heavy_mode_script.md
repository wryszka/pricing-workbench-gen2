# Optimisation — video script & demo run (Part 2: Heavy mode, "the second gear")

The **follow-up** to the Part-1 optimisation video (`docs/optimisation_video_script.md`).
Single presenter, **~9 min**. Same mixed audience: non-experts must leave able to say *why*
you'd ever run "heavy mode" and what it buys you; practitioners get the silent hook that this
is flex their appliance can't match.

**Golden rule (from the runbook):** never lead with heavy mode. It only makes sense once the
viewer already believes the light, governed loop is real — which Part 1 established. So this
video **opens by assuming Part 1**, recaps it in two sentences, then earns the second gear.

Same two standing rules as Part 1: **no "WOW" label, ever**; **no verbalised shot at
Earnix/Radar** — the one competitive line is the polite leave-behind (and it's literally
printed on the app's own caption, so you just read what's on screen).

Every beat is **GO** (what's on screen / click) · **SAY** (the words) · **SEE** (silent
practitioner hook — do not verbalise) · **IF ASKED / FALLBACK**.

---

## What this video demonstrates (read this before anything else)

In the Part-1 loop, we picked each segment's optimal price using **one** demand model and
reported **one** expected-profit number. That's the light gear: fast, smart, segment-collapsed.

**Heavy mode is the optional second gear — two things the same platform can do "because you
can," not because you must:**

1. **Ensemble disagreement map** — *model risk, made visible.* Any single demand model is one
   opinion. Heavy mode refits demand as **8 genuinely different models** (LightGBM variants at
   different depths / feature subsets / seeds, plus a logistic regression), re-solves the
   optimal price factor for **every segment under each model**, and measures how much they
   **disagree**. Where they agree → the price move is robust, deploy with confidence. Where
   they split → that move is a model artifact, not a signal → hold it or widen the corridor.
   → table `optimisation_disagreement`.

2. **Exhaustive stochastic run** — *the full distribution, not a point estimate.* Demand is
   uncertain: each customer converts with a probability, so the real outcome is a spread, not a
   single number. Heavy mode scores the **whole book, policy by policy**, across **hundreds of
   candidate price sets**, and for each one runs **hundreds of Monte-Carlo demand draws** —
   simulating "who actually converts" hundreds of times. Out comes the full picture per
   candidate: **mean profit, the P5–P95 band** (how good or bad it could plausibly get), and the
   **probability of missing plan** (falling below today's profit). → table
   `optimisation_scenarios_stochastic`.

**The scale (measured live, never hardcoded):** the default preset is roughly **the whole book
(~50k policies) × ~300 candidate price sets × ~300 demand draws ≈ ~4.5 billion evaluations**,
plus the ensemble — done in about **90 seconds** for roughly **a dollar** of serverless compute.
The app reads those numbers from a table it wrote during the run, so the caption is a receipt,
not a claim.

**The one line that sums it up (it's on the app banner):**
> *"Smart when you can, exhaustive when it matters — the appliance has one gear."*

---

## Pre-flight — do this before you record (and before your test run)

1. **App:** open **`pricing-workbench-gen2`** (pricingv2 FEVM) → **Price Optimisation** →
   **Heavy mode** tab. (URL: `______`.)
2. **The default artifact MUST already exist.** The tab loads the pre-computed disagreement map
   + stochastic frontier + caption on open. If it shows "Run heavy mode to…" placeholders, the
   heavy job has never run. Run it **well ahead** (it's the genuinely heavy one):
   ```bash
   databricks bundle run "optimisation_heavy_mode" -t pricingv2   # (or click "Full heavy run" once, ahead of time)
   ```
   Job name to look for: *"Price optimisation — heavy mode (ensemble + stochastic) (gen2)"*.
3. **Understand the two buttons — this is the critical operational point:**
   - **"Re-run live (small)"** (green) = preset `live` (~60 candidates × 60 draws × 4 models).
     Room-safe, ~1–2 min. **This is the one you click on camera** to prove it's real.
   - **"Full heavy run"** (black) = preset `default` — the ~4.5B-eval one. **Do NOT click this
     live** unless you deliberately have the time/budget. The pre-computed default view is
     already on screen; that's what you narrate.
4. **Warm-up:** the heavy job is scale-to-zero; the very first trigger after idle has a cold
   start. If you'll click "Re-run live," fire one throwaway `live` run before recording.
5. Have a **screenshot** of the populated disagreement map + frontier + caption as a fallback if
   a live re-run stalls.

**Honesty flags — do NOT overclaim (a practitioner will catch it):**
- The cost figure is a **labelled estimate** (serverless ≈ $0.70/DBU, ~1 DBU/min single node);
  it renders on screen as "(est.)". Say "roughly a dollar, estimated," not "it cost exactly $X."
- This runs on **synthetic data** with the demo's elasticity curves — it demonstrates the
  **pattern and the scale**, it is not a production risk model. "Production-shaped," not
  "production-grade."
- The evaluation count is real and measured; the *dollar* is an estimate. Keep that distinction.
- `prob_below_plan` (probability of missing plan) is computed per candidate and lives in the
  data — the on-screen frontier shows the **mean + P5–P95 band**; describe prob-below-plan as
  "also computed per candidate," don't point at a chart element that isn't there.

---

## PART 1 — Recap & set-up  (~1:00)

**GO:** you on camera, or the Part-1 result still on screen (the +£1m optimised book).

**SAY:**
> "In the last video we ran the governed pricing loop — modelled demand, optimised the motor
> book, found about a million in margin, and deployed it behind a gate. That optimiser was
> deliberately **light**: fast, smart, one demand model, one expected-profit number. That's the
> right default. But sometimes a pricing decision is big enough that you don't just want the
> smart answer — you want to know **how much to trust it**, and **how badly it could go**.
> That's the second gear. Let me show you what running pricing on Databricks lets you do that a
> pricing appliance simply can't."

**SEE (silent hook):** framing it as "because you can" plants the idea that scale here is free
capability, not a licence upgrade. Don't spell it out.

---

## PART 2 — What heavy mode is, and why it matters  (~2:30)

**GO:** the concept can be a slide (build later) or just you talking. If a slide: two panels —
**"Which moves can I trust?" (ensemble disagreement)** and **"How bad could it get?" (the
distribution)**.

**SAY — the first thing it does (model risk):**
> "First problem. When I optimised, I used one demand model. But any one model is one opinion.
> So heavy mode refits demand as **eight genuinely different models** — different algorithms,
> different depths, different features — and it re-solves the best price for every segment
> **under each of them.** Then it asks: where do the models **agree**, and where do they
> **split**? If eight models all say 'raise this segment 8%', that's a robust decision. If they
> range from minus-5 to plus-12, that price move is an artifact of one model's quirk, not a real
> signal — so I hold it, or I widen the guardrail. That's **model risk, made visible, segment by
> segment.**"

**SAY — the second thing it does (the distribution):**
> "Second problem. My optimiser reported **expected** profit — one number. But demand is
> uncertain: each customer only converts with some probability. So the real outcome is a
> **range**, not a number. Heavy mode scores the **whole book, one policy at a time**, across
> hundreds of candidate price plans, and for each plan it rolls the dice on who converts
> **hundreds of times.** That gives me the full distribution: the average, the **P5-to-P95
> band** — the realistic best and worst case — and the **probability I miss plan.** Now I can
> choose a plan on **risk**, not just on the headline number. A slightly lower average with a
> much tighter band is often the better business call."

**SAY — the scale, and why it's honest:**
> "And the scale is the point. The full run is the whole book — around fifty thousand policies —
> times a few hundred price plans, times a few hundred demand draws. That's on the order of
> **four and a half billion evaluations**, and it finishes in about **ninety seconds** for
> roughly **a dollar** of compute. And — this matters — those numbers aren't on my slide. The
> job **measures itself** and writes them to a table, and the app reads them back. It's a
> receipt, not a claim."

**SEE (silent hook):** "eight candidate models," "the whole book per policy," and "measured, not
claimed" are each things a black-box appliance can't offer. Let them sit; don't name the tool.

---

## PART 3 — In the app  (~4:30)

**GO:** Price Optimisation → **Heavy mode** tab. The dark banner at the top reads *"The second
gear… Smart when you can, exhaustive when it matters — the appliance has one gear."* Let it show.

### Beat A · The receipt — "measured, not claimed"  (~0:50)

**GO:** point at the green caption box under the two buttons. It reads, from the live meta table:
**"Measured, not claimed: [N] evaluations ([policies] × [price sets] × [draws], [models] demand
models) in [X]s · ~$[Y] compute (est.)."**

**SAY:**
> "Start here. This caption is generated by the run itself — [read the live numbers]: that many
> evaluations, across the whole book, in that many seconds, for that many dollars, estimated.
> I didn't type these in. The engine measured itself. So when I tell you this is cheap and fast,
> you're reading the receipt, not trusting me."

**SEE (silent hook):** the caption ends with its own polite challenge — *"Now ask an appliance to
show you the distribution across your candidate models."* You can let the viewer read it; you
don't need to say it.

**IF ASKED** "is the cost real?" → the evaluation count and wall-clock are measured; the dollar
is a **labelled estimate** at serverless rates. Be precise about that.

### Beat B · The ensemble disagreement map — which moves can I trust?  (~1:20)

**GO:** the **"Ensemble disagreement map"** section. Each row is a segment with a bar; the label
reads *"spread X.Xpp · agree 0.XX · N models."* Green bars = models agree (agreement ≥ 0.7);
amber = they disagree. Rows are sorted **widest disagreement first.**

**SAY:**
> "Here's the model-risk view. Every row is a segment, and the bar is how much my eight demand
> models **disagree** on its optimal price. Green means they agree — high confidence, I'll deploy
> that move. Amber, up here at the top, means they split — [read a wide one]: the models range
> across several points, so I do **not** treat that as a confident signal. I hold it, or I widen
> the corridor and revisit. This is the conversation a Chief Actuary wants to have: not just
> 'what's the optimal price', but '**which of these moves is real, and which is one model's
> opinion.**'"

**SEE (silent hook):** re-solving the optimum under 8 independent model specs *and* showing the
per-segment spread is model-risk governance you can't get from a single-engine tool. Unspoken.

**IF ASKED** "what are the eight models?" → LightGBM variants at different depths/leaves/seeds
plus a logistic regression — deliberately different specifications so agreement means something.

### Beat C · The uncertainty-banded frontier — how bad could it get?  (~1:20)

**GO:** the **"Uncertainty-banded frontier"** chart. X-axis = expected volume; Y-axis = profit;
each candidate is a dot at its **mean** with a **vertical P5–P95 band**. The **hold baseline**
(today's prices) is the larger black dot/line.

**SAY:**
> "And here's the distribution view. Every point is a candidate price plan. But it's not just a
> point — it's a **band**: the line through it is the P5-to-P95 range from the Monte-Carlo draws,
> the plausible best and worst case. The black marker is where we sit today. Now look at the
> difference between choosing a plan by its **highest mean** versus choosing one whose **band is
> tight and sits comfortably above today's line.** That second plan might make a little less on
> average but is far less likely to disappoint — and the run also computes, for each candidate,
> the **probability it comes in below today's profit.** That's how you price a big decision on
> risk, not on a single hopeful number."

**SEE (silent hook):** a distribution-per-candidate, with tail risk, is exactly the artifact the
leave-behind question asks for. You're showing it; you never have to say who can't.

**FALLBACK:** if the chart is empty, the default artifact didn't load — use your screenshot, or
run "Re-run live (small)" (Beat D) to populate it.

### Beat D · Prove it's live  (~1:00)

**GO:** click **"Re-run live (small)"** (the green button). Watch the run status tick, then the
caption and both visuals refresh with the smaller `live` preset numbers.

**SAY:**
> "And it's not a static picture. I'll run it live now — a smaller pass so we're not waiting —
> [click]. It fires the real job on serverless compute, and in a minute or two the map, the
> frontier, and that receipt all refresh with fresh numbers. Same engine, smaller dials. When it
> really matters, I turn the dials back up and run the full four-and-a-half billion."

**SEE (silent hook):** the number of models / candidates / draws are **dials you set**, not a
plan tier. Demonstrated by clicking, not stated.

**IF FAILS:** first run after idle is a ~45s+ cold start; if it stalls, say "that's the compute
warming — here's the pre-computed full run" and stay on the default artifact. **Never** click
"Full heavy run" to recover in-room — that's the expensive one.

---

## PART 4 — Summary  (~1:00)

**GO:** back on camera, or the frontier on screen.

**SAY (recap — reinforce the two ideas):**
> "So that's the second gear. Two things: it tells me **which of my price moves I can trust**, by
> seeing where eight independent models agree or split — and it tells me **how badly a plan could
> go**, by giving me the whole distribution instead of a single number. And it does it across the
> entire book for about a dollar, with the cost measured, not claimed."

**SAY (the framing line):**
> "The default optimiser is light on purpose — smart, fast, cheap. Heavy mode is there for the
> decisions that deserve it. **Smart when you can, exhaustive when it matters.**"

**SAY (the leave-behind — the only competitive line, and it's already on the app's caption):**
> "So here's the question to take away: ask whoever prices for you today to show you the
> **distribution** of outcomes across a whole ensemble of candidate demand models — not one
> number, the spread — for your whole book, on demand. That's a good thing to be able to do.
> Thanks for watching."

---

## Test-run checklist (walk it once, silently, before recording)

- [ ] Heavy tab opens with the disagreement map, frontier, and caption **already populated**
      (if not, run the default heavy job ahead of time)
- [ ] Caption shows a live evaluation count, wall-clock, and est. cost (~billions / ~90s / ~$1)
- [ ] Disagreement map: green (agree) and amber (disagree) rows both present; widest at top
- [ ] Frontier: candidate dots with P5–P95 bands render; **hold baseline** is the black marker
- [ ] "Re-run live (small)" completes in ~1–2 min and refreshes all three (caption + both viz)
- [ ] You did **not** need to click "Full heavy run" on camera
- [ ] Total run lands **8–10 min** at speaking pace

If a live beat stalls on first hit, that's the cold start — warm it and retry; fall back to the
pre-computed default view, never to "Full heavy run."

---

## Notes for the editor / presenter

- This video assumes Part 1 has been watched. If it will ever stand alone, add ~30s explaining
  the light loop first (money on the table → optimise → deploy behind a gate) before Part 1's recap.
- The strongest 20 seconds are **Beat A (the receipt)** and **Beat C (the bands)**. If you need to
  cut to ~6 min, keep A + B + C and drop the live re-run (Beat D), narrating the pre-computed view.
- Numbers are read **live** off the app — don't memorise them; point and read. The only fixed
  claims are structural (whole book, per policy, ensemble of models, P5–P95, measured-not-claimed).

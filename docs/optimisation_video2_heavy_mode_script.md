# Optimisation — video script & demo run (Part 2: Heavy mode, "the second gear")

> ## ✅ APP BUILT — verify deployed before recording
> WP6 is done: the on-screen **"appliance" copy is removed** — verified, the word appears nowhere in
> the Heavy tab (the banner now ends *"Smart when you can, exhaustive when it matters."*; the
> caption's taunt is gone). The whole competitive weight sits on the single spoken leave-behind.
> Remaining gate: these changes are **committed and deployed on pricingv2** — reconfirm the running
> build matches HEAD before recording. Committed ≠ necessarily the live build.

The **follow-up** to Part 1 (`docs/optimisation_video_script.md`). Single presenter, **~9 min**.
Mixed audience: non-experts must leave able to say *why* you'd run "heavy mode" and what it buys;
practitioners get the silent hook that this is flex a closed, single-formula tool can't match.

**Golden rule (from the runbook):** never lead with heavy mode. It only makes sense once the viewer
believes the light, governed loop is real — which Part 1 established. So this video **assumes Part 1**,
recaps in two sentences, then earns the second gear.

Same two standing rules: **no "WOW" label, ever**; **no verbalised shot at Earnix/Radar** — the one
competitive line is the polite leave-behind (spoken, at the end).

Each beat: **GO** · **SAY** · **SEE** (silent hook — do not verbalise) · **IF ASKED / FALLBACK**.

---

## What this video demonstrates (read before anything else)

In the Part-1 loop we picked each segment's price using **one** demand model and reported **one**
expected-profit number. That's the light gear: fast, smart, segment-collapsed.

**Heavy mode is the optional second gear — two things the same platform can do "because you can":**

1. **Ensemble disagreement map** — *model risk, made visible.* Any one demand model is one opinion.
   Heavy mode refits demand as **8 candidate specifications across two algorithm families** — six
   gradient-boosted (LightGBM) variants at different depths / features / seeds, plus two logistic
   regressions — re-solves the optimal factor for **every segment under each**, and measures how
   much they **disagree**. Agree → robust, deploy with confidence. Split → treat the factor as
   uncertain (hold, or widen the corridor). → `optimisation_disagreement`.
2. **Exhaustive stochastic run** — *the full distribution, not a point estimate.* Demand is
   uncertain: each customer converts with a probability, so the real outcome is a spread. Heavy mode
   scores the **whole book, policy by policy**, across **hundreds of candidate price sets**, each
   with **hundreds of Monte-Carlo demand draws** — simulating "who actually converts" hundreds of
   times. Out comes, per candidate: **mean profit, the P5–P95 band**, and the **probability of
   missing plan**. → `optimisation_scenarios_stochastic`.

**The scale (measured live, never hardcoded):** the default preset is roughly the **whole book
(~50k policies) × ~300 candidate price sets × ~300 draws ≈ ~4.5 billion evaluations**, plus the
ensemble — in about **90 seconds** for roughly **a dollar** of serverless compute. The job measures
itself and writes those numbers to a table; the caption is a receipt, not a claim.

**Own the obvious jab before it's thrown:** those ~4.5 billion are **scored** evaluations — cheap
arithmetic on the fitted demand curves (Bernoulli draws and a dot product), **not** 4.5 billion
model inferences. The expensive part — refitting the ensemble — happens **once**. That factoring is
*why* exhaustive costs a dollar. Say it out loud (Beat A) so no one gets to "that's not real
inference" first.

**The framing line:** *"Smart when you can, exhaustive when it matters."*

---

## Pre-flight — before you record (and before your test run)

1. **App:** `pricing-workbench-gen2` (pricingv2 FEVM) → **Price Optimisation → Heavy mode**.
   (URL: `______`.)
2. **WP6 check (done in code — verify on the deployed app):** confirm the word **"appliance" is gone**
   from the tab's banner and caption. Verified absent in source; confirm it's the deployed build.
3. **The default artifact MUST already exist.** The tab loads the pre-computed disagreement map +
   frontier + caption on open. If it shows "Run heavy mode to…" placeholders, run it well ahead (the
   genuinely heavy one):
   ```bash
   databricks bundle run "optimisation_heavy_mode" -t pricingv2
   ```
   Job name: *"Price optimisation — heavy mode (ensemble + stochastic) (gen2)"*.
4. **The two buttons — the critical operational point:**
   - **"Re-run live (small)"** (green) = preset `live` (~60×60×4). Room-safe, ~1–2 min. **Click this
     on camera** to prove liveness.
   - **"Full heavy run"** (black) = preset `default` — the ~4.5B-eval one. **Do NOT click live.** The
     pre-computed default view is already on screen; that's what you narrate.
5. **Warm-up:** heavy job is scale-to-zero; the first trigger after idle cold-starts. If you'll click
   "Re-run live," fire one throwaway `live` run first.
6. **Fallback screenshot** of the populated map + frontier + caption.

**Honesty flags — do NOT overclaim:**
- Cost is a **labelled estimate** (≈$0.70/DBU, ~1 DBU/min single node); renders as "(est.)". Say
  "roughly a dollar, estimated," not "it cost exactly $X."
- Say **"scored evaluations,"** not "inferences" — see the concession above.
- **Synthetic data**, demo elasticity curves — this shows the **pattern and the scale**, not a
  production risk model. "Production-shaped," not "production-grade."
- `prob_below_plan` is computed per candidate and lives in the data; the on-screen frontier shows the
  **mean + P5–P95 band** — describe prob-below-plan as "also computed," don't point at a chart
  element that isn't there.

---

## PART 1 — Recap & set-up  (~1:00)

**GO:** you on camera, or the Part-1 result still on screen.

**SAY:**
> "In the last video we ran the governed pricing loop — modelled demand, optimised the motor book,
> found about **two percent of premium** in extra margin, and deployed it behind a gate. That
> optimiser was deliberately **light**: fast, smart, one demand model, one expected-profit number.
> That's the right default. But sometimes a pricing decision is big enough that you don't just want
> the smart answer — you want to know **how much to trust it**, and **how badly it could go.** That's
> the second gear."

**SEE (silent hook):** "because you can" frames scale as free capability, not a licence upgrade.

---

## PART 2 — What heavy mode is, and why it matters  (~2:30)

**GO:** a slide (build later) or you talking. Two panels: **"Which moves can I trust?"** (ensemble
disagreement) and **"How bad could it get?"** (the distribution).

**SAY — the first thing it does (model risk):**
> "First problem. When I optimised, I used one demand model — but any one model is one opinion. So
> heavy mode refits demand as **eight different model specifications, across two families** —
> gradient boosting and logistic regression, at different depths and feature sets — and re-solves
> the best price for every segment **under each of them.** Then it asks: where do they **agree**, and
> where do they **split**? If they all say 'raise this segment eight percent', that's a robust
> decision. If they range from minus-five to plus-twelve, that move is an **artifact of one model's
> quirk**, not a signal — so I hold it, or widen the guardrail. **Model risk, made visible, segment
> by segment.**"

**SAY — the second thing it does (the distribution):**
> "Second problem. My optimiser reported **expected** profit — one number. But demand is uncertain:
> each customer only converts with some probability, so the real outcome is a **range.** Heavy mode
> scores the **whole book, one policy at a time**, across hundreds of candidate plans, and for each
> it rolls the dice on who converts **hundreds of times.** That gives the full distribution: the
> average, the **P5-to-P95 band** — the realistic best and worst case — and the **probability I miss
> plan.** Now I can choose on **risk**, not just the headline: a slightly lower average with a much
> tighter band is often the better business call."

**SAY — the scale, and why it's honest (own the jab):**
> "And the scale is the point. The full run is the whole book — around fifty thousand policies —
> times a few hundred plans, times a few hundred draws: on the order of **four and a half billion
> evaluations**, in about **ninety seconds** for roughly **a dollar.** And to be straight with you:
> those are **scored** evaluations — cheap arithmetic on the fitted curves, not four and a half
> billion model re-fits. The expensive part, refitting the ensemble, happens **once.** That's the
> design — exhaustive costs a dollar *because* the loop is factored properly. And I didn't type these
> numbers; the job **measures itself** and the app reads them back. A receipt, not a claim."

**SEE (silent hook):** "eight specs across two families," "the whole book per policy," and "measured,
not claimed" are each things a black box can't offer. Let them sit.

---

## PART 3 — In the app  (~4:30)

**GO:** Price Optimisation → **Heavy mode** tab.

### Beat A · The receipt — "measured, not claimed"  (~0:50)

**GO:** point at the green caption box under the two buttons — generated from the live meta table:
evaluation count, policies × price sets × draws, model count, wall-clock, est. cost.

**SAY:**
> "Start here. This caption is generated by the run itself — [read the live numbers]: that many
> **scored** evaluations, across the whole book, in that many seconds, for that many dollars,
> estimated. I didn't type these in — the engine measured itself. So when I say this is cheap and
> fast, you're reading the receipt."

**IF ASKED** "is the cost real?" → the evaluation count and wall-clock are measured; the dollar is a
**labelled estimate** at serverless rates.

### Beat B · Ensemble disagreement map — which moves can I trust?  (~1:20)

**GO:** the **"Ensemble disagreement map"** — one row per segment, bar = disagreement; label reads
*"spread X.Xpp · agree 0.XX · N models."* Green = agree (≥0.7); amber = split. Sorted widest-first.

**SAY:**
> "The model-risk view. Every row is a segment; the bar is how much my eight demand models
> **disagree** on its optimal price. Green means they agree — high confidence, deploy it. Amber, at
> the top, means they split — [read a wide one]: several points of range, so I do **not** treat that
> as a confident signal. I hold it, or widen the corridor and revisit. This is the conversation a
> Chief Actuary wants: not just 'what's the optimal price', but '**which of these moves is real, and
> which is one model's opinion.**'"

**SEE (silent hook):** re-solving the optimum under 8 independent specs *and* showing the per-segment
spread is model-risk governance a single-engine tool can't give you. Unspoken.

**IF ASKED** "what are the eight?" → six LightGBM variants (different depths / leaves / seeds) plus
two logistic regressions — deliberately different, so agreement means something.

### Beat C · Uncertainty-banded frontier — how bad could it get?  (~1:20)

**GO:** the **"Uncertainty-banded frontier"** — X = expected volume, Y = profit; each candidate a dot
at its **mean** with a **vertical P5–P95 band**; the **hold baseline** (today) the larger black marker.

**SAY:**
> "The distribution view. Every point is a candidate plan — but it's not just a point, it's a
> **band**: the line through it is the P5-to-P95 range from the Monte-Carlo draws, the plausible best
> and worst case. The black marker is where we sit today. Now compare choosing a plan by **highest
> mean** versus one whose **band is tight and sits comfortably above today's line.** That second plan
> might average a little less but is far less likely to disappoint — and the run also computes, per
> candidate, the **probability it comes in below today's profit.** That's pricing a big decision on
> risk, not on a single hopeful number."

**SEE (silent hook):** a distribution-per-candidate with tail risk is exactly what the leave-behind
question asks for. You're showing it; never say who can't.

**FALLBACK:** empty chart → default artifact didn't load; use the screenshot, or run "Re-run live
(small)" (Beat D).

### Beat D · Prove it's live  (~1:00)

**GO:** click **"Re-run live (small)"** (green). Watch the status tick; caption + both visuals refresh
with the smaller `live` numbers.

**SAY:**
> "Not a static picture. I'll run it live — a smaller pass so we're not waiting — [click]. It fires
> the real job on serverless, and in a minute or two the map, the frontier, and that receipt refresh
> with fresh numbers. Same engine, smaller dials. When it matters, I turn the dials up and run the
> full four-and-a-half billion."

**SEE (silent hook):** models / candidates / draws are **dials you set**, not a plan tier —
demonstrated by clicking.

**IF FAILS:** first run after idle is a ~45s+ cold start; if it stalls, "that's compute warming —
here's the pre-computed full run" and stay on the default artifact. **Never** click "Full heavy run"
to recover in-room.

---

## PART 4 — Summary  (~1:00)

**GO:** back on camera, or the frontier on screen.

**SAY (recap — the two ideas):**
> "So that's the second gear. Two things: **which of my price moves I can trust**, by seeing where
> eight independent specs agree or split — and **how badly a plan could go**, by the whole
> distribution instead of a single number. Across the entire book, for about a dollar, with the cost
> measured, not claimed."

**SAY (the framing line):**
> "The default optimiser is light on purpose — smart, fast, cheap. Heavy mode is there for the
> decisions that deserve it. **Smart when you can, exhaustive when it matters.**"

**SAY (the leave-behind — the only competitive line anywhere):**
> "So a question to take away: ask whoever prices for you today to show you the **distribution** of
> outcomes across a whole ensemble of candidate demand models — not one number, the spread — for your
> whole book, on demand. That's a good thing to be able to do. Thanks for watching."

---

## Shared IF ASKED cards (learn cold — add to Part 1 too)

1. **"My rates execute in Radar Live / Guidewire — how do factors get there?"** → "They export — the
   factor table is a governed Delta table; publish it to your rating engine like any other rate
   revision. This replaces the **analysis and decision** layer, not your execution path — integrate
   first, and the seam is a table, not a migration." *(Seam doctrine — never improvise this one.)*
2. **"Where's the competitor price?"** → "Synthetic direct book — price-relative-to-technical stands
   in for market position. In production your aggregator/competitor feed lands as another input to
   the demand model; it's a column, not a feature you wait for."
3. **"Is the elasticity real / where's the price test?"** → Concede first: "Synthetic, so parameter
   recovery is expected — the panel demonstrates the red-team pattern. On real data you'd feed it
   price-test or randomised-corridor experience; relative-to-technical reduces endogeneity, controlled
   variation is what removes it."
4. **"Can I set portfolio-level constraints — total volume, mix, loss-ratio floor?"** → answer with
   the truth as built: **"Yes for volume — there's a `portfolio.min_volume_ratio` floor in the same
   YAML, enforced by the solver (it walks back the least profit-efficient moves until the floor
   holds).** Mix and loss-ratio floors aren't keys yet — but they're the same pattern: a line in the
   file, not a feature tier." *(Verified against `default.yaml` + solver — do not overstate mix/loss-ratio.)*
5. **"This optimises this period's profit — what about lifetime value?"** → "Correct — the objective
   here is period profit. The objective function is code you own; a CLV-weighted objective is a
   modelling choice, not a platform limit."
6. **"Isn't raising loyal customers exactly price-walking?"** → "On renewal, unmanaged, yes — which is
   why GIPP is checked at solve time and why the fair-value flag exists. The demo's whole twist is
   that the machine **proposing** it is not the same as the business **doing** it."

---

## Test-run checklist (walk it once, silently, before recording)

- [ ] **[verify deployed]** The word **"appliance" is absent** from the tab's banner and caption
- [ ] Heavy tab opens with map, frontier, and caption **already populated**
- [ ] Caption says **"scored evaluations… (est.)"** with live count / wall-clock / cost (~billions / ~90s / ~$1)
- [ ] Ensemble label matches reality — **"eight specifications across two families"** (GLM logit + monotone GBM)
- [ ] Disagreement map: green (agree) and amber (split) rows both present; widest at top
- [ ] Frontier: candidate dots with P5–P95 bands; **hold baseline** is the black marker
- [ ] "Re-run live (small)" completes in ~1–2 min and refreshes all three
- [ ] You did **not** click "Full heavy run" on camera
- [ ] Recap uses the **~2%-of-premium** number (not "about a million")
- [ ] Total run lands **8–10 min** at speaking pace

If a live beat stalls on first hit, that's the cold start — warm and retry; fall back to the
pre-computed default view, **never** to "Full heavy run."

---

## Notes for the editor / presenter

- Assumes Part 1 has been watched. If it will ever stand alone, add ~30s explaining the light loop
  first (margin on the table → optimise → deploy behind a gate) before the recap.
- The strongest 20 seconds are **Beat A (the receipt)** and **Beat C (the bands)**. For a ~6-min cut,
  keep A + B + C and drop the live re-run (Beat D), narrating the pre-computed view.
- Numbers are read **live** off the app — point and read. The only fixed claims are structural (whole
  book, per policy, ensemble across two families, P5–P95, measured-not-claimed, scored-not-inferred).

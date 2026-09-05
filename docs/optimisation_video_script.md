# Optimisation — video script & demo run (Part 1: the governed loop)

A **single-presenter video**, ~17 min, target audience **mixed**: SAs and partners who
are *not* pricing experts (they must leave able to say what optimisation is and why it
matters) **and** practitioners who live in Earnix/Radar (they get silent, unspoken hooks
that the same mechanics run in an open, governed system).

**Structure:** (1) intro → (2) concept, one slide → (3) the app, step by step → (4) summary.
**Spine:** the "Grandma-in-a-BMW" story carries the whole app walk.
**Heavy mode** is a *teaser only* here — it gets its own follow-up video (see the end).

Two standing rules this script obeys, on purpose:
- **Never label anything "WOW" on screen or say it out loud.** The impressive moments land
  through the *visible artifact*, not a label.
- **Never verbalise a shot at Earnix/Radar.** The practitioner hooks are *seen, not said* —
  the viewer's own knowledge supplies the punchline. The one competitive line is the polite
  leave-behind question at the end.

Every beat below is: **GO** (what's on screen / click-path) · **SAY** (the words) ·
**SEE** (the silent practitioner hook — do not verbalise) · **IF ASKED / FALLBACK**.

---

## Pre-flight — do this before you hit record (and before your test run)

1. **App:** open the gen2 app **`pricing-workbench-gen2`** on the pricingv2 FEVM → the
   **Price Optimisation** page. (Fill your exact URL here: `______`.)
2. **Reset / data:** the motor book must be populated and dates rolled to "today." If the
   book looks stale, re-run the spine (`databricks bundle run optimisation_full -t pricingv2`).
3. **Warm the endpoints.** Serving + agents are scale-to-zero: the **first** quote/agent call
   after idle takes **~45s** (cold start). Fire one throwaway call to each before recording so
   the live beats are sub-second.
4. **Warm the AI cache** and confirm the mode toggle. **Gotcha:** the AI cache can replay a
   *stale* agent answer — if you changed a persona, ask a fresh question or clear the cache,
   or you'll narrate an answer that doesn't match the screen.
5. **Have a fallback screenshot** of a solved frontier + factor table, in case a live re-solve
   stalls (~1 min normally).
6. **Confirm you're an admin** (deploy is RBAC-gated to `ADMIN_USERS`). Deploy only works if
   you're on that list — you are (`laurence.ryszka@databricks.com`).
7. **Know your demo objects:** grandma segment `70+ · grpHigh` (~340 policies); the
   explain-price demo case is triggered by the "use the grandma-in-a-BMW demo case" button
   (quote ≈ `MQ-00025204`, age 72, group 40).

**Honesty flags — do NOT overclaim these (a practitioner will catch it):**
- The technical price is **champion-scored** by the real risk models, but that scoring step
  does **not** currently emit an automatic model→table lineage edge. Don't claim "automatic
  lineage" on that specific step.
- **Constraints:** the corridor + caps are enforced *at solve time*; forbidden signals are
  excluded *by construction*; GIPP is enforced *at solve time in the renewal solver*. Don't
  say "every constraint is solve-time enforced across the board" — say what's enforced where.
- **Sensitivity scales inversely:** *less* elastic → *more* uplift (not "half the elasticity,
  half the uplift"). If you show the sensitivity panel, describe it that way.
- It's **synthetic data** and a **demonstration arithmetic layer** for the rate formula.
  These are **production-shaped patterns**, not "production-grade."

---

## PART 1 — Intro  (~0:45)

**GO:** you on camera, or a title card. No app yet.

**SAY:**
> "Hi, I'm Laurence — I'm a Solutions Architect at Databricks. Today we're talking about
> **price optimisation**, and I'm going to show it running end to end inside a real pricing
> workbench on Databricks. Two promises: by the end, if you've never done pricing, you'll be
> able to explain what optimisation is and why it matters. And if you *do* pricing for a
> living, you'll recognise every step — just running somewhere you might not expect."

*(That second sentence is the only time you nod to practitioners out loud. After this, the hooks are silent.)*

---

## PART 2 — What optimisation is, and what you need  (~2:30)  · one slide

**GO:** the concept slide (build later). While it's up, talk. The slide carries one diagram:
**Data → (Cost model + Demand model) → Solver, bound by Constraints → Gate → Monitor**, with
an arrow labelled **"human sets the policy"** pointing into *Constraints*.

**SAY — what it is (the four sentences; say them slowly):**
> "Traditional pricing is cost-plus. You work out the **technical price** — the break-even
> cost of the policy, expected claims plus expenses — and you add a margin. Optimisation asks
> a smarter question: customers **respond** to price. Some shop around, some are loyal. So for
> each type of customer, what price best hits my goal — profit, or volume, or a blend — given
> how likely they actually are to buy at that price?
>
> To answer it you need one extra model — a **demand model**, which is just: as I raise the
> price, how many customers still convert? — and a **solver** that picks the best price for
> each segment, **inside rules a human sets.** Same risk, same book — but demand-aware prices
> instead of a flat margin."

**SAY — why it matters (two reasons):**
> "Why care? Two reasons. One is money: you lift profit **without taking on more risk** —
> you're just pricing smarter. Two is regulation: demand-aware pricing is exactly what
> regulators now scrutinise — fair value, no price-walking. So being able to do this
> **transparently, and prove every decision**, isn't overhead. It's the whole point."

**SAY — the hook that makes it click (grandma):**
> "Here's the one idea to hold onto. Imagine I tell the system: *I want to win the most
> grandmas who drive BMWs.* Watch what happens — because a profit-maximising machine will
> actually try to **raise** their price. Grandmas are loyal, they don't shop around, so the
> machine happily charges them more and loses a few. Whether that's OK is **not** a maths
> question — it's a **policy** question, and a human has to answer it. That tension —
> **the machine optimises, the human decides what 'optimal' means** — is the whole demo.
> Let's watch it."

**SEE (silent hook):** the diagram deliberately shows *Constraints* as a first-class box, not
buried config. A practitioner clocks "the policy is an explicit, external artifact" before
you ever open the app.

---

## PART 3 — In the app, step by step  (~12 min)

Grandma is the through-line. The order maps to the loop: **data → models → results → the
twist (control) → governance → did-it-work.**

### Beat A · Data — the book today  (~1:00)

**GO:** Price Optimisation → **Optimiser** tab. Read the roll-up KPIs at the top.

**SAY:**
> "This is our motor book — real, though synthetic, data. Roughly **£9.4m of premium** at
> today's prices. The claim we're going to test is that there's margin left on the table, and
> we can find it without touching how we assess risk."

**SEE (silent hook):** these KPIs come straight off live Unity Catalog tables — the numbers
are queryable, not baked into a slide. A practitioner used to exports notices it's *live*.

**IF ASKED** "where's the data from?" → live UC tables written by the pipeline; quote
responses including **lost** quotes (the lost ones carry the price signal).

---

### Beat B · Models — model demand honestly  (~1:45)

**GO:** **Demand & red-team** tab. Show the **elasticity curve** first, then the
**"wrong-model" (endogeneity) panel**.

**SAY (the curve):**
> "Here's the demand model. As price goes up, conversion comes down — and notice it can *only*
> go down: that monotonic shape is **enforced in the model**, not hoped for. This curve is the
> heart of optimisation: it tells us, segment by segment, how price-sensitive people are."

**SAY (the wrong-model panel — this is the credibility beat):**
> "Now, the trap. If you naively model demand on the **raw price**, the model tells you
> customers barely care about price — because expensive risks cost more *and* command higher
> prices, so the signal cancels out. That's a false 'inelastic' read, and it's how you leave
> money everywhere. We model demand on price **relative to the technical price**, which removes
> that trap — and this panel shows the difference side by side."

**SEE (silent hook):** the model's code and its monotonic constraints are on screen, and there
is a *panel whose only job is to red-team the model's own honesty*. A black-box appliance shows
you a curve; here you see the model, the code, and the self-check. Say none of that.

**IF ASKED** "is the elasticity even real?" → the **parameter-recovery** panel: on data where
we know the true answer, the model recovers it (correlation ≈ 0.95).

---

### Beat C · Results — what optimisation finds  (~1:45)

**GO:** back to **Optimiser**. Set the objective to **Expected profit**, set **N** (scenarios)
to a few thousand, click **Re-solve (live job)**. Let it run (~1 min), then read the
**efficient frontier**, the **per-segment waterfall**, and the **factor table**.

**SAY (while it solves):**
> "I'm going to explore a few **thousand** possible price sets and pick the best one under my
> goal. This is a real governed job running now — not a slider faking it."

**SAY (the result):**
> "There it is. Same book, same risk models — optimised, the profit goes from **£9.4m to about
> £10.4m. That's roughly +£1m, about +11%,** and — this matters — **every single price move
> stayed inside a ±15% corridor** around the technical price. Look at the waterfall: it raised
> stable, loyal segments toward the cap, and it **cut** price for the young drivers who shop
> around hard. That's the machine doing exactly what we asked."

**SEE (silent hook):** **N is a control you set**, and the frontier is generated live. In an
appliance, the number of scenarios you can explore is a licence tier; here it's a text box.
Don't say it — just set N in front of them.

**FALLBACK:** if the live solve stalls, drop to your pre-solved screenshot: "here's the last
run" — the story is identical.

---

### Beat D · The twist — the machine vs the human (control)  (~2:30)  ← the peak

**GO:** **Optimiser → factor table.** Find the grandma segment **`70+ · grpHigh`** (~340
policies). It shows a **+5%** move.

**SAY:**
> "Now watch. Remember the grandmas. Told 'maximise profit', the optimiser **raised** our
> 70-plus, high-value-car segment by **5%** — conversion drops a touch, 73% to 68%, and the
> machine is fine with that, because they're loyal. From a pure profit view, that's correct."

**GO:** flip to **Demand & red-team → elasticity curve**, select `70+ · grpHigh`.

**SAY:**
> "But say my business wants to **win** this segment, not milk it. Look at their curve: if I
> **cut** their price, conversion climbs — 92% at a 15% discount, versus 48% at a 15% loading.
> To win them I have to go the *opposite* way to what the profit machine chose. That's not a
> maths error — the maths is right. It's a **policy decision**, and it's mine to make."

**GO (Option A — agents woven in):** invoke the **`constraint_author`** agent — ask it, in plain
language: *"cap increases and allow a price cut for the 70-plus high-group segment."* It drafts
the constraint-YAML override.

**SAY:**
> "So I tell the system, in plain English, what I want — and an agent drafts the change to the
> **pricing policy** for me. I'm not editing maths; I'm stating intent. Then I re-solve under
> the new policy."

**GO:** **Optimiser → Re-solve** (solver-only, ~1 min). Show `70+ · grpHigh` now moving **down**.

**SAY:**
> "Same governed solver, new policy — the grandmas now move **down**, and conversion goes up.
> The machine ran the optimisation; **I** decided what optimal meant."

**SEE (silent hook):** the policy is a **versioned YAML file changed by an agent + re-solved on
demand** — i.e. your pricing policy is diff-able, reviewable, and reproducible. A practitioner
who changes constraints through a GUI clocks "that's under version control" instantly.

**FALLBACK / SEAM:** `constraint_author` is an **agent persona via the agent panel, not yet a
one-click button**. If it's slow or you want a clean click-path, either (a) tilt the objective
to **retention-weighted** in the front door, or (b) show the pre-edited segment override in
`optimisation_constraints/default.yaml`. All three routes reach the same "human overrules the
machine" point.

---

### Beat E · Governance — approve, prove, explain  (~3:00)

**GO:** **Optimiser → Approve & deploy.** Click it (you're an admin).

**SAY:**
> "The human sets the policy; the system **enforces** it. When I deploy, the corridor is
> re-checked **server-side** — no prompt, no agent, nothing can talk its way past it — and the
> whole decision is written to an **immutable record**: who, when, why, which model, which
> constraint version."

**GO:** open the **decision record** (Decisions tab) for the deploy you just made.

**SAY:**
> "Here's that record. This is what a regulator or an internal auditor asks for — and it exists
> automatically, as a by-product of deciding."

**GO (the standout beat):** **Optimiser → "Explain this price" → "use the grandma-in-a-BMW demo
case."** Show the decomposition, then the plain-language explanation.

**SAY:**
> "And here's the one I love. Pick a single real quote — this is our grandma, age 72, higher
> group car. **Exactly why does she pay what she pays?** The risk price, the factor we chose,
> the corridor that bounds it — every number, traceable, from her premium back to the model and
> the policy. And it drops straight into a decision record."

**SEE (silent hook — the big one):** **this per-quote, fully-decomposed, traceable explanation
is the thing a black-box appliance cannot produce.** You do not say that. You just show the
document on the grandma's own quote and pause. A practitioner's own experience fills the gap.

**GO (optional, if fair value comes up):** the **fairness / fair-value** evidence panel
(Monitoring or the fairness section) — proxy-correlation, disparate impact, vulnerability.

**FALLBACK:** if a governance PDF render hangs (known serverless stall), use the **Pack History**
list — packs were pre-generated at deploy time; click one to show it inline.

---

### Beat F · Did it work?  (~1:00)

**GO:** **Monitoring** tab → **Advance one month**.

**SAY:**
> "Last question: did reality agree? I roll the book forward one month under the prices we just
> deployed, and compare **predicted against realised**. [Read the on-screen numbers.] They line
> up closely — the book behaved the way the model said it would. That closes the loop: decide,
> deploy, monitor, and check yourself honestly."

**SEE (silent hook):** the loop is **closed and self-checking** — predicted-vs-realised is a
first-class screen, not a quarterly reconciliation project.

---

## PART 4 — Summary  (~1:15)

**GO:** back on camera, or the concept slide again.

**SAY (recap the concept — reinforce the teach):**
> "So — that's price optimisation. Cost-plus tells you the floor; optimisation asks what price
> best hits your goal given how customers respond, within rules a human sets. We modelled
> demand honestly, we found about **£1m of margin on the same book without touching risk**, and
> every price was bounded, deployed behind a gate, explained down to a single grandma's quote,
> and checked against reality a month later."

**SAY (the line to leave them with):**
> "The machine runs the cycle. The human decides when it's allowed to act alone. That's the
> product — and it all runs in your own workspace, open, on one platform."

**SAY (heavy-mode teaser → sequel hook):**
> "One more thing, and then I'll let you go. Today the optimiser was deliberately *light* —
> smart, fast, thousands of scenarios. But when a decision really matters, the same platform can
> run the **entire book, policy by policy, across a whole ensemble of candidate demand models,
> for the full distribution of outcomes** — not a single point estimate. **Smart when you can,
> exhaustive when it matters.** That's a video of its own — I'll show you that next."

**SAY (the polite competitive leave-behind — the only shot you take):**
> "And a question to take with you: ask whoever prices for you today to show you the
> **distribution** of outcomes across your candidate demand models — not one number, the spread.
> That's a good conversation to have."

---

## Test-run checklist (run this once, silently, before recording)

Walk the whole path with a stopwatch and tick each:

- [ ] Optimiser KPIs load and show ~£9.4m (Beat A)
- [ ] Demand curve + wrong-model panel + param-recovery all render (Beat B)
- [ ] Live re-solve completes < ~90s; frontier + waterfall + factor table populate (Beat C)
- [ ] `70+ · grpHigh` visible in the factor table at **+5%** (Beat D)
- [ ] Its elasticity curve shows the 92% / 73% / 48% shape (Beat D)
- [ ] `constraint_author` agent returns a YAML override on a fresh (uncached) question (Beat D)
- [ ] Re-solve flips `70+ · grpHigh` to a **cut** (Beat D)
- [ ] Approve & deploy succeeds as admin; a decision record appears (Beat E)
- [ ] "Explain this price" grandma demo case renders the full decomposition (Beat E)
- [ ] Advance-one-month returns predicted-vs-realised numbers (Beat F)
- [ ] Total run lands **15–20 min** at speaking pace

If any agent/serving beat is slow on first hit, that's the ~45s cold start — warm it and retry.

---

## Follow-up video (planned): Heavy mode — "exhaustive when it matters"

Its own ~8–10 min video. Star of the show: the **Heavy mode** tab — the pre-computed
**disagreement map** and **uncertainty-banded frontier**, and the **measured** caption
(evaluation count, wall-clock, estimated cost — captured from a real run, never a claim;
the shipped run measured billions of evaluations in ~90s for ~$1). Rule from the runbook:
**never lead with this** — it only makes sense once a viewer already believes the light,
governed loop is real, which this Part-1 video establishes. The leave-behind question above
is the natural bridge into it.

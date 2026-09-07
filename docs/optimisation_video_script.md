# Optimisation — video script & demo run (Part 1: the governed loop)

> ## ✅ APP BUILT — two gates remain before recording
> The fix-spec work is **committed** (94bb9d1 + follow-ups) **and deployed on pricingv2**: the factor
> table's **Conduct column** (renewal GIPP status + an amber "fair-value review →" pill), the
> **three KPIs** (GWP · expected profit · uplift **as % of GWP**), the **reshaped grandma curve**
> (organic +7.5%), the **provenance block** on explain-price, the **UC stored-procedure deploy
> gate**, and the removal of on-screen "appliance" copy. Two gates remain:
> 1. **Confirm the DEPLOYED build matches HEAD.** These changes are **committed** (94bb9d1 + follow-ups)
>    and the app was redeployed on pricingv2 — before recording, reconfirm the running app matches HEAD
>    and the pipeline was re-run (reshaped data is in the tables). Committed ≠ necessarily the live build.
> 2. **Read every number live and name its unit.** The app now shows **GWP** and **expected profit**
>    as separate KPIs and the **uplift as % of GWP** — read those off the screen; the reshaped data
>    changes the absolutes, so never memorise a £ figure. (The earlier fix brief mislabelled the
>    ~£9.4m *profit* as *premium*; the KPIs now make the distinction explicit — see the reviewer
>    note at the foot.)

A **single-presenter video**, ~17 min, audience **mixed**: SAs/partners who are *not* pricing
experts (they must leave able to say what optimisation is and why it matters) **and**
practitioners who live in Earnix/Radar (silent, unspoken hooks that the same mechanics run in an
open, governed system).

**Structure:** (1) intro → (2) concept, one slide → (3) the app, step by step → (4) summary.
**Spine:** "Grandma-in-a-BMW" carries the whole app walk — and the twist is now a **conduct**
twist (Consumer Duty / fair value), not just a commercial one.
**Heavy mode** is a teaser only here; it has its own follow-up video.

Two standing rules this script obeys:
- **Never label anything "WOW" on screen or out loud.** The impressive moments land through the
  *visible artifact*.
- **Never verbalise a shot at Earnix/Radar.** Practitioner hooks are *seen, not said*. The one
  spoken competitive line is the polite leave-behind at the very end — and it is now the **only**
  competitive line anywhere (the on-app "appliance" copy has been removed).

Each beat is **GO** (screen / click) · **SAY** (the words) · **SEE** (silent practitioner hook —
do not verbalise) · **IF ASKED / FALLBACK**.

---

## Pre-flight — before you record (and before your test run)

1. **App:** open **`pricing-workbench-gen2`** (pricingv2 FEVM) → **Price Optimisation**.
   (URL: `______` ← fill this in.)
2. **Verify the DEPLOYED build (all built in code — confirm it's live):** the factor table's Conduct
   column (GIPP + amber fair-value pill) is present, the grandma curve is reshaped (flat upside /
   steep deep-cut side), the provenance block renders on explain-price, the constraint-edit YAML-diff
   apply flow works, the word "appliance" is absent from all on-screen copy, and the solve uplift
   reads **1–3% of GWP**. If any fail, the build isn't deployed — **do not record.**
3. **Numbers / demo objects:** confirm the Optimiser KPI row shows **GWP and expected profit as
   two separate numbers** (the summary endpoint already returns both — verify the UI renders both;
   if not, that's a fix-spec item). After data regeneration re-check: segment `70+ · grpHigh` is
   still **~316 policies** and still the solver's **organic +7.5%** pick (the profit curve is flat
   across +2.5–7.5% on this small segment, so +7.5% is the genuine optimum — see the reviewer note),
   and the explain-price demo case still resolves via the **"grandma-in-a-BMW" button** (it looks the
   quote up server-side — there is no hardcoded quote id to update).
4. **Warm the endpoints (~45s cold start each):** serving, **both** agents (ask `constraint_author`
   a **fresh, uncached** question), the fairness panel, and the heavy-mode default artifact.
5. **New fallback screenshots needed post-fix:** solved frontier + factor table **with the GIPP
   column**, the fairness panel, the YAML diff, and (for the teaser) the heavy map + frontier +
   caption.
6. **Confirm your deploy privilege** — the gate is now a UC stored procedure; RBAC is a **UC
   `EXECUTE` grant** on it (you or `sa-presenter@databricks.com`), **not** an app `ADMIN_USERS`
   list. Confirm you hold `EXECUTE`, or the Approve & deploy beat is denied by Unity Catalog.

**Honesty flags — do NOT overclaim (a practitioner will catch it):**
- **Name the unit on every number.** GWP (~£53m) and expected profit (~£9.4m) are different
  quantities on screen; point at each once. The uplift (~£1m) is **~2% of premium** *or* **~11% of
  profit** — same money; pick one framing and stay consistent.
- **"Profit" here = conversion-weighted margin of price over the technical (risk) cost** — i.e.
  before fixed overheads. If asked "profit after what?", say that plainly; don't imply it's net
  underwriting result.
- **Constraints bind differently — say which is which.** Corridor + segment caps: solve-time hard.
  Forbidden signals: excluded by construction, proxy-tested post-solve by the fairness job. **GIPP:
  solve-time in the *renewal* solver** (renewal ≤ equivalent new business). Don't say "all
  constraints solve-time enforced across the board."
- The technical-price scoring step does **not** currently emit an automatic model→table lineage
  edge — don't claim automatic lineage on that specific step.
- Synthetic data; a **demonstration arithmetic layer** for the rate formula; **production-shaped
  patterns**, not "production-grade."

---

## PART 1 — Intro  (~0:45)

**GO:** you on camera, or a title card. No app yet.

**SAY:**
> "Hi, I'm Laurence — a Solutions Architect at Databricks. Today we're talking about **price
> optimisation**, and I'll show it running end to end inside a real pricing workbench on
> Databricks. Two promises: if you've never done pricing, you'll leave able to explain what
> optimisation is and why it matters. And if you *do* price for a living, you'll recognise every
> step — just running somewhere you might not expect."

---

## PART 2 — What optimisation is, and what you need  (~2:30)  · one slide

**GO:** the concept slide (build later). One diagram —
**Data → (Cost model + Demand model) → Solver, bound by Constraints → Gate → Monitor**, with an
arrow labelled **"human sets the policy"** pointing into *Constraints*.

**Plus a second build — the "bill of materials"** listed beside the diagram (this is the
"here's the shopping list of what you need" ask, and the frame SAs will screenshot):
> *quote responses incl. lost quotes · technical price · demand model · constraints file
> (versioned) · solver job · decision record · monitor*

**SAY — the bill of materials (one breath):**
> "Seven artifacts. That's the whole shopping list — everything else today is just these, live."

**SAY — what it is (the four sentences; say them slowly):**
> "Traditional pricing is cost-plus. You work out the **technical price** — the break-even cost of
> the policy, expected claims plus expenses — and add a margin. Optimisation asks a smarter
> question: customers **respond** to price. Some shop around, some are loyal. So for each type of
> customer, what price best hits my goal — profit, or volume, or a blend — given how likely they
> actually are to buy at that price? To answer it you need one extra model — a **demand model**,
> which is just: as I raise price, how many still convert? — and a **solver** that picks the best
> price per segment, **inside rules a human sets.** Same risk, same book — but demand-aware prices
> instead of a flat margin."

**SAY — why it matters (two reasons):**
> "Why care? One is money: you lift profit **without taking on more risk** — you're pricing
> smarter, not gambling harder. Two is regulation: demand-aware pricing is exactly what regulators
> now scrutinise — fair value, no price-walking. So being able to do it **transparently, and prove
> every decision**, isn't overhead. It's the point."

**SAY — the hook that makes it click (grandma):**
> "Here's the idea to hold onto. Imagine I tell the system: *I want to win the most grandmas who
> drive BMWs.* Watch what happens — a profit-maximising machine will actually try to **raise** their
> price. Grandmas are loyal, they don't shop, so the machine happily charges them more and loses a
> few. Whether that's OK is **not** a maths question — it's a **policy** question, and a human has
> to answer it. That tension — **the machine optimises, the human decides what 'optimal' means** —
> is the whole demo."

**SEE (silent hook):** the diagram shows *Constraints* as a first-class, external box, not buried
config. A practitioner clocks "the policy is an explicit, versioned artifact" before you open the app.

---

## PART 3 — In the app, step by step  (~12 min)

Grandma is the through-line. Order maps to the loop: **data → models → results → the twist
(conduct) → governance → did-it-work.**

### Beat A · Data — the book today  (~1:00)

**GO:** Price Optimisation → **Optimiser** tab. Read the roll-up KPIs — **GWP and expected profit
are two separate numbers**; point at each.

**SAY:**
> "This is our motor book — synthetic data, real mechanics. About **[read live — ~£53m] of gross
> written premium**, and at today's prices it earns about **[read live — ~£9.4m] of expected
> profit** — that's conversion-weighted margin over the risk cost. The claim we'll test: there's
> margin left on this book **without touching how we assess risk.**"

**SEE (silent hook):** both KPIs come straight off live Unity Catalog tables — queryable, not baked
into a slide.

**IF ASKED** "where's the data from?" → live UC tables; quote responses including **lost** quotes
(the lost ones carry the price signal). **"Profit after what?"** → margin of price over the
technical (risk) cost, before fixed overheads — the quantity the objective maximises.

> **[RESOLVED]** The app took the clean route: keep Beat A as **"the motor book"** (the KPI/factor
> table are new-business segment factors), and the factor table's new **Conduct column** joins each
> segment's **renewal GIPP status** onto the row. There is also a dedicated **"Renewals — GIPP
> enforced"** section. So call it "the motor book" here; grandma's +7.5% is her **new-business segment
> factor**, and the Conduct column shows her **renewal** stays GIPP-clean. Do not call the whole
> thing a "renewal book."

---

### Beat B · Models — model demand honestly  (~1:45)

**GO:** **Demand & red-team** tab. Elasticity curve first, then the **"wrong-model" (endogeneity)
panel**.

**SAY (the curve):**
> "Here's the demand model. As price rises, conversion falls — and it can *only* fall: that
> monotonic shape is **enforced in the model**, not hoped for. This curve is the heart of
> optimisation — it tells us, segment by segment, how price-sensitive people are."

**SAY (the wrong-model panel — the credibility beat):**
> "Now the trap. Model demand on the **raw price** and it tells you customers barely care —
> because expensive risks cost more *and* command higher prices, so the signal cancels out. That's
> a false 'inelastic' read, and it's how you leave money everywhere. We model demand on price
> **relative to the technical price**, which removes the trap — and this panel shows the difference
> side by side."

**SEE (silent hook):** the model's code and monotone constraints are on screen, plus a panel whose
only job is to red-team the model's own honesty. Say none of it.

**IF ASKED** "is the elasticity real?" → concede first: it's synthetic, so parameter recovery is
expected — the panel demonstrates the red-team *pattern* (recovery correlation ≈ 0.95). On real
data you'd feed it price-test or randomised-corridor experience.

---

### Beat C · Results — what optimisation finds  (~1:45)

**GO:** back to **Optimiser**. Objective = **Expected profit**, set **N** (scenarios) to a few
thousand, click **Re-solve (live job)** (~1 min). Read the **frontier**, **waterfall**, **factor
table**.

**SAY (while it solves):**
> "I'll explore a few **thousand** possible price sets and pick the best under my goal — a real
> governed job running now, not a slider faking it."

**SAY (the result — read numbers live, name units):**
> "There it is. Same book, same risk models — optimised, expected profit moves up by [read the
> **Profit uplift** KPI], and the app reads it back as a **percent of GWP** right there — call it
> **about two percent of premium** — with every move inside the ±15% corridor. Two percent doesn't
> sound dramatic — **that's the point.** It's found money on the same book, same risk, and it's the
> honest size of what optimisation finds. Anyone promising you ten times that is selling you *their*
> elasticities, not yours."

**SEE (silent hook):** **N is a control you set** and the frontier is generated live — in an
appliance the number of scenarios is a licence tier; here it's a text box. Don't say it; set N in
front of them.

**FALLBACK:** if the live solve stalls, drop to the pre-solved screenshot — the story is identical.

---

### Beat D · The twist — the machine vs the human (a *conduct* twist)  (~2:30)  ← the peak

**[BUILT — verify deployed. Now live: the factor table's Conduct column (renewal GIPP status + an
amber "fair-value review →" pill), the reshaped grandma curve (organic +7.5%), and the
`/optimisation/constraint-edit` YAML-diff apply endpoint.]**

**GO:** **Optimiser → factor table.** Find `70+ · grpHigh` (~316 policies): **+7.5%**, with a
**Conduct column** showing **GIPP ✓** and an **amber "fair-value review →" pill**.

**SAY (1 — commercial + legal):**
> "Watch. Told 'maximise profit', the machine raised our 70-plus segment **7.5%**. Look at her curve
> — nearly flat on increases; she barely reacts, only deep cuts move her. So the machine milks the
> loyalty. Commercially, that's correct. And notice — it stayed **legal**: her renewal never
> exceeds the equivalent new-business price, checked at solve time. That's the GIPP column."

**GO:** point at the **amber marker**.

**SAY (2 — legal is the floor, not the standard):**
> "But legal is the floor, not the standard. This flag says: a loyal, older, low-switching segment
> is being loaded — that's a **fair-value question under Consumer Duty**, and it isn't the machine's
> to answer. It's mine."

**GO:** click the amber **"fair-value review →"** pill on her row — it jumps to **Monitoring → the
Fair-value evidence panel** (proxy-correlation, disparate impact, vulnerability screen).

**SAY (3 — the evidence, one sentence):**
> "Here's the evidence I'd take to a fair-value committee — and my call is: **we win this segment,
> we don't milk it.**"

**GO:** ask **`constraint_author`** in plain language — *"cap increases and allow a price cut for the
70-plus high-group segment"* — then **pause on the YAML diff**.

**SAY (4 — intent, then attributed commit):**
> "The agent drafted the change — I'm not editing maths, I'm stating intent — but **nothing applies
> until I review this diff and commit it.** The policy is a versioned file; this change now has my
> name on it."

**GO:** **Re-solve** → `70+ · grpHigh` moves **down**, conversion up, consistent with the deep-cut
side of her curve.

**SAY (5):**
> "Same governed solver, new policy — the grandmas now move **down**, and conversion climbs. The
> machine ran the optimisation; **I** decided what optimal meant."

**SEE (silent hook):** the policy is a **versioned YAML changed by an agent, reviewed as a diff,
committed under a name, and re-solved on demand** — pricing policy that's diff-able, attributable,
reproducible.

**FALLBACK / SEAM:** `constraint_author` is an **agent persona, not yet a one-click button**. If
slow, (a) tilt the objective to **retention-weighted**, or (b) show the pre-edited segment override
in `optimisation_constraints/default.yaml`. Both must land on the **same conduct framing** — legal
floor vs fair-value standard, human decides.

> **[NOTE]** The old "92% / 73% / 48%" elasticity recital is **deleted** — the reshaped curve has
> different numbers. Read them live off her curve.

---

### Beat E · Governance — approve, then prove provenance  (~3:00)

**GO:** **Optimiser → Approve & deploy.** The deploy runs a **Unity Catalog stored procedure** (not
app code): it re-checks the corridor, writes the deployment, and stamps an **immutable `audit_log`
row** — called **as you, over OBO**, so UC enforces the gate per person via an **`EXECUTE` grant**,
and your forwarded email is the approver on the record.

**SAY:**
> "The human sets the policy; the platform **enforces** it. Deploy here isn't app code I could edit —
> it's a **Unity Catalog stored procedure**, and permission to run it is a **database grant**, checked
> per person. It re-checks the corridor server-side and stamps an immutable audit record with my name
> on it. No prompt, no agent, no engineer talks past a UC privilege."

**GO (re-aimed standout):** open **Explain this price → "use the grandma-in-a-BMW demo case."** Give
the decomposition **~10 seconds**, then **pause on the provenance block.**

**SAY (the provenance chain — this is the beat):**
> "Every rating engine can show you a factor waterfall. Here's what sits **underneath** this one:
> the exact model version, the exact constraint version — **including the change I just committed
> with my name on it** — who approved deployment, and the decision record it all landed in. One
> chain, from her premium to the audit trail, queryable. Not a report someone assembles for the
> regulator — a **by-product of deciding.**"

**SEE (silent hook):** a queryable premium→model-version→constraint-version→approver→decision-record
chain is the thing a black box can't produce. Show it; never say who can't.

> **[RESOLVED — word choice]** The deploy procedure writes an **immutable `audit_log` row** under
> `SQL SECURITY DEFINER` (owner-privileged; the caller only holds `EXECUTE`). "Immutable" is now
> defensible — be ready to show the audit table (or Delta time-travel) if pressed. Still don't
> improvise beyond what you can show.

**FALLBACK:** if a governance PDF render hangs (known serverless stall), use **Pack History** —
packs are pre-generated at deploy time; click one to show it inline.

---

### Beat F · Did it work? — the honesty flip  (~1:00)

**GO:** **Monitoring** tab → **Advance one month.**

**SAY:**
> "Last screen — and let me be straight about what it proves. This is **synthetic data**, so
> predicted and realised reconcile by construction; I wrote the world. What matters is the
> **pattern**: this screen exists, first-class, and in production it's where your model error
> surfaces in **month one** — not in a year-end reconciliation project. Decide, deploy, monitor, and
> check yourself honestly."

**SEE (silent hook):** predicted-vs-realised is a first-class screen, not a quarterly project.

> **[NOTE]** Never say "the book behaved the way the model said it would" — that's false validation
> on synthetic data.

---

## PART 4 — Summary  (~1:15)

**GO:** back on camera, or the concept slide.

**SAY (recap — honest numbers):**
> "So — that's price optimisation. Cost-plus tells you the floor; optimisation asks what price best
> hits your goal given how customers respond, within rules a human sets. We modelled demand
> honestly, found about **£1m — roughly two percent of premium — on the same book without touching
> risk**, bounded every move, deployed behind a gate, and could trace a single grandma's premium
> all the way to the audit trail."

**SAY (the line to leave them with):**
> "The machine runs the cycle. The human decides when it's allowed to act alone. That's the
> product — and it all runs in your own workspace, open, on one platform."

**SAY (heavy-mode teaser → sequel hook):**
> "One more thing. Today the optimiser was deliberately *light* — smart, fast, thousands of
> scenarios. But when a decision really matters, the same platform can run the **whole book, policy
> by policy, across an ensemble of candidate demand models, for the full distribution of outcomes** —
> not one point estimate. **Smart when you can, exhaustive when it matters.** That's the next video."

**SAY (the only competitive line anywhere — the polite leave-behind):**
> "And a question to take with you: ask whoever prices for you today to show you the **distribution**
> of outcomes across your candidate demand models — not one number, the spread. That's a good
> conversation to have."

---

## Test-run checklist (walk it once, silently, before recording)

- [ ] KPIs show **GWP and profit separately** (~£53m / ~£9.4m) — both rendered
- [ ] Solve **uplift reads 1–3% of GWP** (≈£1m); read live, named by unit
- [ ] **[verify deployed]** Grandma curve: flat upside, steep deep-cut side; solver picks +7.5% **organically**
- [ ] **[verify deployed]** GIPP column + amber fair-value marker on her row
- [ ] **[verify deployed]** One click from her row → fairness panel renders
- [ ] **[verify deployed]** Agent draft → YAML diff → **attributed** apply → re-solve flips her to a cut
- [ ] **[verify deployed]** Provenance block on explain-price with live values; decision-record link opens
- [ ] Monitoring caption carries the **synthetic-reconciliation** honesty line
- [ ] `constraint_author` returns on a **fresh (uncached)** question
- [ ] Total run lands **15–20 min** at speaking pace

If an agent/serving beat is slow on first hit, that's the ~45s cold start — warm it and retry.

---

## Editor guidance (Part 1)

Full cut **~17 min.** If a **10-minute** cut is ever needed, keep: **concept slide (with bill of
materials), Beat A, Beat C, Beat D (the conduct twist, uncut — it *is* the video), Beat E
explain-price + provenance.** Drop first: Beat B's parameter-recovery detail; Beat F (fold its one
honesty line into the summary); the live-solve wait (jump-cut it). **The strongest 30 seconds are
the YAML-diff commit and the provenance chain — protect them in any cut.**

---

## Reviewer note (why the numbers differ from the fix brief)

The fix brief states GWP ≈ £9.4m and profit ≈ £1.3m with a £180k (~2%) uplift. Verified against the
app: the `/summary` endpoint returns `gwp_current` **and** `expected_profit_hold/opt/profit_uplift`
**separately**. The real values are **GWP ≈ £53m** (≈50k policies × ~£1,065 loaded — the same 50k
that makes Part 2's ~4.5B evaluations true) and **expected profit ≈ £9.4m → £10.4m, uplift ≈ £1m.**
The brief's "£9.4m premium" is actually the **profit** figure mislabelled as premium; £1.3m and
£180k are then derived from that mislabel. The brief's *narrative instinct is correct* — the uplift
**is** ~2% of premium (£1m / £53m ≈ 1.9%) — so this script keeps "~2% of premium / found money /
not selling you their elasticities" and only corrects the base numbers. **Re-review update (app
built):** the app now exposes an explicit **`uplift_pct_of_gwp`** KPI alongside separate GWP and
expected-profit KPIs — confirming the correction. The **new-business vs renewal** challenge is
resolved: renewal GIPP status *is* joined onto the factor table (the Conduct column), plus a
dedicated Renewals section. The deploy gate also became a **UC stored procedure** (EXECUTE-grant
RBAC over OBO) — a stronger governance beat than the old app `ADMIN_USERS` check; Beat E reflects it.

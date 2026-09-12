# Gemini image spec — Part 2 concept slide ("What optimisation is, and what you need")

For the optimisation video, Part 2 (~2:30), **one slide, two builds**. Generate two images that
share the same diagram: **Build 1** = the diagram alone; **Build 2** = the same diagram with the
"bill of materials" panel revealed beside it. Paste the prompts below into Gemini image generation
(Nano Banana / Gemini 2.5 Flash Image, which renders text well). Every label is spelled exactly —
tell Gemini to reproduce label text verbatim.

## The one thing the picture must say
`Constraints` is a **first-class, external, versioned artifact that a human controls** — not buried
config. A practitioner should clock "the pricing policy is an explicit, versioned thing" before a
single app screen is opened. The human → Constraints arrow ("sets the policy") is the emotional
centre of the slide; make it draw the eye.

## Style tokens (state these to Gemini)
- **Format:** 16:9 presentation slide, flat-vector infographic, executive-grade, generous
  whitespace. No 3D, no photos, no gradients, no drop shadows, no clutter.
- **Background:** off-white `#F8FAFC`.
- **Pipeline nodes** (Data / models / Solver / Gate / Monitor): pale-blue fill `#E8F1FB`, navy text
  `#0B1F33`, blue accent border `#2D6CDF`, rounded rectangles, thin (2px) connectors, arrowheads
  pointing right.
- **Hero (Constraints):** warm lava accent — border `#FF3621`, fill `#FFF1EC` — visibly larger and
  bolder than the pipeline nodes, set ABOVE and clearly separate from the flow.
- **Gate:** green accent `#12805C` (a shield/tick). **Monitor:** a small line-chart glyph.
- **Human + its arrows:** lava `#FF3621`, the highest-contrast element on the slide.
- **Type:** clean geometric sans-serif (Inter / Helvetica feel), bold node labels, small caption text.
- **No** company logos, product names, or vendor/brand marks of any kind.

## Exact labels (reproduce verbatim, no substitutions)
- Title: **What price optimisation is — and what you need**
- Flow: **Data** → (**Cost model — technical price** + **Demand model — elasticity**) → **Solver** → **Gate** → **Monitor**
- Hero box: **Constraints — the pricing policy**, corner pill: **versioned · v3**
- Constraints→Solver arrow label: **bounds every price**
- Human icon label: **Human — pricing committee**; its arrow label: **sets the policy**
- Bill-of-materials heading: **The bill of materials** / sub: **7 artifacts — the whole shopping list**
- The 7 items: **Quote responses (incl. lost quotes)** · **Technical price** · **Demand model** · **Constraints file (versioned)** · **Solver job** · **Decision record** · **Monitor**
- BoM footer (italic): **Everything else is just these, live.**

---

## BUILD 1 — diagram only (paste into Gemini)

> A clean, modern flat-vector presentation slide, 16:9, for an executive audience. Off-white
> background (#F8FAFC), generous whitespace, professional infographic style — no 3D, no photos, no
> gradients, no drop shadows. Rounded-rectangle nodes with thin 2px borders, thin arrow connectors.
> Crisp geometric sans-serif labels, reproduced exactly as written.
>
> Title, top-left, bold navy (#0B1F33): "What price optimisation is — and what you need".
>
> A left-to-right pipeline across the centre, five stages joined by right-pointing arrows:
> (1) "Data" with a small database-cylinder glyph; (2) a vertically stacked PAIR of boxes
> "Cost model — technical price" and "Demand model — elasticity" — draw an arrow from Data into
> BOTH boxes, and an arrow from BOTH boxes into the next stage; (3) "Solver" with a gear glyph;
> (4) "Gate" with a green shield-and-tick glyph (#12805C); (5) "Monitor" with a small line-chart
> glyph. These pipeline nodes are pale blue (#E8F1FB fill, #2D6CDF border, #0B1F33 text).
>
> ABOVE the Solver, drawn as the largest and most prominent box and clearly SEPARATE from the
> pipeline, a warm lava-accented box (border #FF3621, fill #FFF1EC): "Constraints — the pricing
> policy", with a small corner pill reading "versioned · v3". A thick arrow points DOWN from this
> box into the Solver, labelled "bounds every price".
>
> To the upper-left of the Constraints box, a simple line-art person icon labelled
> "Human — pricing committee", with a bold lava-orange (#FF3621) arrow pointing INTO the
> Constraints box, labelled "sets the policy". This arrow is the highest-contrast element on the
> slide and should draw the eye first.
>
> The composition must make it obvious that Constraints is an explicit, external, versioned
> artifact controlled by a human — not buried configuration. No company logos, no product or vendor
> names, no decorative clutter. Render all text crisply and legibly.

## BUILD 2 — diagram + bill of materials (paste into Gemini)

> [Everything in Build 1, with the diagram occupying the left ~68% of the slide], PLUS a vertical
> panel down the right ~30% of the slide: a rounded card, pale slate fill (#F1F5F9), thin border.
> Card heading, bold navy: "The bill of materials"; sub-heading, smaller grey: "7 artifacts — the
> whole shopping list". Below, a clean numbered checklist, each line with a small lava tick:
> 1. Quote responses (incl. lost quotes)
> 2. Technical price
> 3. Demand model
> 4. Constraints file (versioned)
> 5. Solver job
> 6. Decision record
> 7. Monitor
> A footer line in italic grey: "Everything else is just these, live." Keep the same flat-vector,
> whitespace-generous, logo-free executive style; reproduce all text exactly.

---

## Tips for a clean result
- If Gemini crowds or garbles text, generate at higher resolution and ask it to "prioritise legible
  labels; simplify glyphs before dropping any label text."
- The vertically-stacked "Cost model + Demand model" pair is the one place models tend to merge —
  if so, add: "the two model boxes are clearly separate, stacked one above the other."
- Alternative composition if the right-hand panel feels cramped: put the bill of materials as a
  horizontal strip along the bottom third instead of a right column (say so in the prompt).

## Cross-reference
Slide narration + build cues live in `docs/optimisation_video_script.md` (Part 2 "What optimisation
is, and what you need", ~2:30). The grandma hook there uses the +7.5% behaviour; this slide stays
conceptual (no live numbers), so it doesn't need re-cutting when data is regenerated.

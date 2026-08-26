# Demo Talk Track — P&C Insurance Pricing Accelerator

## Overview

**Company:** Bricksurance SE (fictional commercial property insurer)
**Platform:** Databricks with serverless compute
**Audience:** Heads of Pricing, Chief Actuaries, Pricing Engineers, Big4 Consultants

**Key message:** The full pricing lifecycle — from raw vendor data to live pricing
decisions — runs on one platform. Not just modelling, but ingestion, governance,
serving, and auditability.

---

## EXECUTIVE VERSION (30 minutes, app-focused)

### Before the app opens — The Problem (~1 min)

**What to say (before screen-share starts):**
> "Before I show you the demo, here's what we're solving. Right now, when new
> flood or market data arrives, pricing teams typically spend weeks validating
> the portfolio impact manually — spreadsheets, emails, a sign-off chain with no
> audit trail. When a regulator asks 'why did this customer's premium change last
> April?', the answer is often a best guess.
>
> Consumer Duty and the FCA's fair-value rules have put this squarely on the
> CDO and Chief Actuary's desk — not just 'are our prices right?' but 'can we
> prove they're right, decision by decision, with a traceable audit trail?'
>
> The cost of doing nothing: weeks per vendor data cycle, a governance gap that's
> a regulatory finding waiting to happen, and pricing decisions that can't be
> reproduced. What I'm about to show you replaces that with a governed, automated
> loop — same data, same models, same decisions, in seconds instead of weeks."

**Positioning (say once, up front):**
> "One more framing point: this platform sits *around* your existing rating
> engine — Radar, Earnix, whatever you use. Think enrich, wrap, replace — in that
> order, at your pace. Today we prove the data enrichment and governance layers.
> The rating-engine integration story comes second."

---

### Opening (2 min)

**What to show:** Landing page of the app

**What to say:**
> "This is a pricing data transformation accelerator for commercial P&C insurance.
> What you're looking at is a single platform that handles everything from data
> ingestion to live model serving — with human-in-the-loop governance at every step.
> Let me walk you through what that looks like in practice."

**Talking point:** This isn't a prototype or a PowerPoint — every button works,
every table is real (synthetic) data, every model is trained and serving.

---

### Section 1: Data Ingestion & Impact Analysis (8 min)

**What to show:** Data Ingestion tab → click into Geospatial Hazard → Impact Analysis tab

**What to say:**
> "New flood risk data has arrived from a vendor. Before anyone touches the rating
> engine, the system has already joined this data to our 50,000 active policies
> and re-rated every single one. Watch this..."

**Hero moment — Shadow Pricing:**
> "6,018 policies are affected. The total premium impact is £X. 342 policies
> face a premium increase of more than 10%. And the actuary can see all of this
> before clicking Approve."

**Headline value to land:** Geospatial enrichment lifts the model's Gini from
0.11 to 0.25 — that's the discrimination improvement visible in the Model Factory
leaderboard. Not a prototype claim; it's in the live data.

**Expected questions:**
- "How long does this shadow pricing take?" → "Seconds. It runs automatically
  when new data arrives."
- "Can we override individual values?" → "Yes — the Upload tab lets you amend
  data, and the app tracks who changed what."
- "How does this compare to what we do now?" → "Most insurers spend weeks on
  this manually. This is the same analysis, automated, in seconds."

**Pause for questions.**

---

### Section 2: Model Factory & Approval (8 min)

**What to show:** Model Factory tab → leaderboard → click PDF for a model

**What to say:**
> "The system trained 20+ model configurations — GLMs for regulatory submission,
> gradient boosted machines for demand and fraud, plus an uplift model that
> captures what the GLM missed. They're ranked on insurance-specific metrics:
> Gini, PSI for stability, and a regulatory suitability score."

**Hero moment — PDF Report:**
> "Click this PDF button — you get a regulatory-grade model validation report.
> Model identity, performance metrics, data lineage, approval chain. Ready for
> your regulator."

**Talking point — AI Agent:**
> "There's an optional AI assistant that can analyse the feature table and
> recommend which models to train. It's turned off by default — actuaries
> decide. But it shows what's possible."

**Expected questions:**
- "Can we use our own models?" → "Absolutely. The platform supports any Python
  model — statsmodels, sklearn, LightGBM, PyTorch."
- "How do you handle regulatory requirements?" → "GLMs provide transparent
  relativities. Everything is versioned and auditable."

**Pause for questions.**

---

### Section 3: Feature Store & Serving (5 min)

**What to show:** Feature Store tab → latency numbers → explain online vs offline

**What to say:**
> "The Unified Pricing Table serves two purposes. Offline, it's a Delta Lake
> table for model training. Online, it's a Lakebase store with sub-10ms lookups.
> Same data, different access pattern."

**Hero moment — Auto Feature Lookup:**
> "When we deploy a model, you send just a policy_id and get a price back.
> The endpoint automatically looks up all 90 features from the online store.
> No custom integration code. The model knows which features it needs because
> we captured that lineage at training time."

**Rating-engine positioning (say this here):**
> "Important framing: the rating formula you see here is a **demonstration
> arithmetic layer** — six parameters to make the demo self-contained. On your
> estate, Databricks is the **data and governance layer around Radar or Earnix**,
> not a replacement for your rate-file GLM. The REST endpoint here is the seam
> point: your rating engine calls it, gets back an enriched score, and applies
> its own relativities. Enrich first, integrate later, replace only if you choose."

**Expected questions:**
- "What's the latency?" → "Sub-100ms end-to-end including feature lookup."
- "How does this compare to Radar/Earnix?" → "Those tools own the rate-file
  and the relativities — we sit upstream. Data prep, feature engineering, model
  training, and a governed REST API your rating engine can call. See DEMO_QA Q31
  for the full framing."

**Pause for questions.**

---

### Section 4: Governance (5 min)

**What to show:** Governance tab → audit trail → DQ pass rates

**What to say:**
> "Everything that happened — every data approval, every model decision, every
> LLM call — is recorded with who did it, when, and why. A regulatory auditor
> can reconstruct the exact state of any model, its training data, and the
> human decisions that approved it."

**Hero moment — Full Audit Trail:**
> "This isn't a separate governance tool. It's the same platform. Unity Catalog
> tracks lineage automatically. The audit log adds the human decisions on top.
> Delta Time Travel lets you go back to any point in history."

**Closing:**
> "What you've seen is a complete pricing data transformation pipeline — from
> raw vendor data to live pricing — on one platform. Not six tools with six
> integration projects. One platform, fully governed, fully auditable."

---

### Closing & Future (2 min)

**Future roadmap talking points:**
- Earnix/Radar mock integration (REST API enrichment)
- ABAC/attribute-based access control across business units
- CI/CD with Databricks Asset Bundles
- Agentic data quality monitoring
- Real-time streaming (Delta CDF for continuous online store sync)

---

## TECHNICAL VERSION (60 minutes, notebooks + app)

### Opening (5 min)
Show the architecture diagram notebook (`00_demo_overview.py`). Walk through
the end-to-end flow.

### Section 1: Data Setup & Ingestion (10 min)
- Run `setup.py` — show the SCALE_FACTOR parameter
- Show the Volume with CSV files
- Run the ingestion pipeline — show parallel task execution
- Show the DLT pipeline — walk through expectations in `silver_*.sql`
- Show DQ pass rates in the app

### Section 2: Gold Layer / UPT (10 min)
- Run `build_upt.py` — walk through the joins
- Show the PK constraint, tags, and column comments
- Show the Features UI in Catalog Explorer
- Explain synthetic vs real columns

### Section 3: Model Training (10 min)
- Run `train_pricing_models` — walk through the 4 notebooks
- Show GLM relativities (audience loves this)
- Show GBM feature importance
- Show the model comparison: GLM only vs GLM + uplift
- Show `fe.log_model()` and explain auto feature lookup

### Section 4: Use Cases (10 min)
- UC1: Shadow pricing — show the flood risk v2 simulation
- UC2: Point-in-time — show Delta Time Travel
- UC5: Enriched pricing waterfall (tech × fraud × retention)

### Section 5: Serving (10 min)
- Show online store setup
- Deploy model endpoint
- Send a request with just `policy_id` — show the response
- Feature override demo ("what if flood score = 10?")

### Section 6: Governance & App (5 min)
- Walk through all 4 app tabs
- Generate a regulatory PDF
- Show the Genie Space

---

## Tips for Presenters

1. **Start with the app, not the notebooks.** The app tells the story; the
   notebooks prove it's real.
2. **Don't skip the impact analyser.** It's the strongest "aha" moment.
3. **Have a backup policy_id ready** for the serving demo (e.g. POL-100042).
4. **If Genie Space is configured,** ask one of the sample questions live.
5. **Adapt for your audience:** actuaries care about GLM relativities and
   regulatory compliance; engineers care about the serverless architecture
   and feature lookup; Big4 consultants care about the governance story.
6. **The AI agent is optional.** Only show it if the audience is receptive
   to AI in regulated processes. Always lead with "the human decides."

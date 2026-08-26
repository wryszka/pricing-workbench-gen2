# Pricing Workbench gen2 — deploy runbook

> **This is the gen2 deploy doc.** gen2 lives on the `pricingv2` FEVM workspace
> alongside the frozen v2 client deployment, uses schema `pricing_workbench_gen2`,
> app `pricing-workbench-gen2`, and is deployed from the `wryszka/pricing-workbench-gen2`
> repo (`main` branch). Do not follow the old v2 runbook for this codebase.

End-to-end, copy-pasteable. Everything is serverless / scale-to-zero; no classic
compute. A full deploy is: **bootstrap the app → deploy the bundle → run one
populate job**. ~35–45 min mostly unattended.

The canonical post-deploy populate command is **`full_build`** — see step 4.
(`resources/full_pipeline.yml` / `run_full_demo.py` are a legacy fallback, marked
`[LEGACY]`, and are not the canonical path.)

## 0. Settings (pricingv2 workspace; change for dev)

| | |
|---|---|
| Workspace | `https://fevm-lr-pricing-v2-aws-us.cloud.databricks.com` |
| CLI profile | `PRICING_V2` |
| Catalog | `lr_pricing_v2_aws_us_catalog` |
| Schema | `pricing_workbench_gen2` |
| Warehouse | `f738fde9a1197aeb` |
| App | `pricing-workbench-gen2` |
| Repo / branch | `wryszka/pricing-workbench-gen2` @ `main` |
| Bundle target | `pricingv2` (default) |

Prereqs: Databricks CLI authenticated to the workspace
(`databricks auth login --host <host> --profile PRICING_V2`), the catalog exists,
a serverless SQL warehouse exists, and (for pushes) `gh auth switch --user wryszka`.

---

## 1. (Optional) Tear down for a clean redeploy

Skip this to redeploy in place (`full_build` is idempotent). Do it to prove a
from-nothing deploy.

```bash
cd pricing-workbench-gen2

# a) Serving endpoints (created by jobs, NOT bundle-managed — destroy won't remove them)
for ep in pwg2_pricing_scorer pwg2_pricing_chat_agent pwg2_pricing_governance_agent pwg2_motor_pricing_scorer_direct; do
  databricks --profile PRICING_V2 serving-endpoints delete "$ep" 2>/dev/null || true
done

# b) Genie spaces + dashboard (not bundle-managed). Optional — create_ai_assets
#    reuses by title if left. Delete for a truly fresh run:
#    databricks --profile PRICING_V2 genie trash-space <SPACE_ID>
#    databricks --profile PRICING_V2 api delete /api/2.0/lakeview/dashboards/<DASH_ID>

# c) Bundle resources (jobs, pipeline, app) + synced files
databricks bundle destroy --target pricingv2 --profile PRICING_V2 --auto-approve

# d) Data + models (drops every table, model, volume in the gen2 schema)
databricks --profile PRICING_V2 api post /api/2.0/sql/statements --json \
  '{"warehouse_id":"f738fde9a1197aeb","statement":"DROP SCHEMA IF EXISTS lr_pricing_v2_aws_us_catalog.pricing_workbench_gen2 CASCADE","wait_timeout":"30s"}'
```

---

## 2. Bootstrap the app (mints its service principal)

The app must exist before it has a service principal, and `full_build` grants
that SP. So create it first, then tell the bundle its id.

```bash
# create the app shell (provisions compute + an SP; ~2 min)
databricks apps create pricing-workbench-gen2 --profile PRICING_V2

# read its service principal appId
databricks apps get pricing-workbench-gen2 --profile PRICING_V2 \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['service_principal_client_id'])"
```

Put that value into `databricks.yml` → `targets.pricingv2.variables.app_service_principal_id`
(replacing the old one), then let the bundle adopt the pre-created app:

```bash
databricks bundle deployment bind pricing_workbench_gen2 pricing-workbench-gen2 \
  --target pricingv2 --profile PRICING_V2 --auto-approve
```

> Redeploying in place (app kept)? Skip step 2 entirely — the app + SP already exist.

---

## 3. Deploy the bundle + app

```bash
./deploy.sh pricingv2
```

This builds the frontend, copies `app.pricingv2.yaml` → `app.yaml`, runs
`databricks bundle deploy --target pricingv2` (jobs + pipeline + app + synced files,
incl. the built `frontend/dist`), then deploys the app source. The app comes up
but is empty until step 4.

---

## 4. Populate everything — one job

**This is the canonical populate command (use this, not `run_full_demo`):**

```bash
databricks bundle run full_build --target pricingv2 --profile PRICING_V2
```

Generates, in dependency order (~35–45 min): synthetic data + quote stream (with
price elasticity) → real UK postcode enrichment → bronze/silver ingest → UPT →
4 champions + `@champion` aliases → rating config + release rate-book →
inference/bias backfills → shadow-pricing → supporting tables + packs volume →
commercial rating-engine endpoint → governance + chat agents (self-mint their SQL
token) → motor/agentic core (`pwg2_motor_pricing_scorer_direct`) → price-optimiser
tables → **Genie spaces + mart dashboard** (`create_ai_assets`) → **real
governance packs per champion** (`generate_governance_packs`) → app-SP grants (UC
+ endpoints + READ VOLUME) → metadata → uniform `pw_` tags.

**Populate governance separately (if ever needed):** the real packs are made by
their own reusable job, so you can (re)fill governance any time without a full
rebuild:
```bash
databricks bundle run generate_governance_packs --target pricingv2 --profile PRICING_V2
```
One real multi-section PDF (+ charts + sidecars) per champion, ~10 min.

---

## 5. Verify

```bash
APP=$(databricks apps get pricing-workbench-gen2 --profile PRICING_V2 | python3 -c "import json,sys;print(json.load(sys.stdin)['url'])")
TOK=$(databricks --profile PRICING_V2 auth token | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")
curl -s -H "Authorization: Bearer $TOK" "$APP/" -o /dev/null -w "root: %{http_code}\n"                    # expect 200 (HTML)
curl -s -H "Authorization: Bearer $TOK" "$APP/api/pricing/status" | python3 -m json.tool                  # champions + ready:true
curl -s -H "Authorization: Bearer $TOK" "$APP/api/review/packs" | python3 -c "import json,sys;print('packs:',len(json.load(sys.stdin)['packs']))"
curl -s -H "Authorization: Bearer $TOK" "$APP/api/config" | python3 -c "import json,sys;d=json.load(sys.stdin);print('genie/quote/dash:',bool(d['genie_space_id']),bool(d['genie_quote_space_id']),bool(d['mart_dashboard_id']))"
```

Then open the app URL and click through.

---

## Expected, not failures
- **First quote after a cold deploy takes ~45s** — the endpoints are scale-to-zero
  and warm on first call; subsequent calls are sub-second.
- **Genie/dashboard get fresh ids** on a from-nothing run — the app resolves them
  **by title** at runtime, so no id-wiring is needed.
- The live **"Generate pack" PDF** button hangs on serverless (env stall) — the
  seeded pack *history* is what the script produces; the list/reproduce views work.

## The optional live-serving tier (millisecond pricing / QPS)
Not part of `full_build` (it costs money while up). Arm on demand and tear down:
```bash
databricks bundle run motor_provision --target pricingv2 --profile PRICING_V2   # Lakebase online store + route-optimized scorer
databricks bundle run motor_teardown  --target pricingv2 --profile PRICING_V2   # stop it when done
```

## Deploying to the dev workspace
```bash
./deploy.sh dev
databricks bundle run full_build --target dev --profile DEV
```
Schema, app, and assets are identically gen2-namespaced (`pricing_workbench_gen2`,
`pricing-workbench-gen2`, `pwg2_` prefixes) — they coexist with gen1 during cutover.

## Deploying to a different / customer workspace
Use the public repo `wryszka/pricing-workbench-gen2` directly against a `sandbox`
target you point at the customer workspace (see `databricks.yml` for the target
pattern). The handoff repo is maintained manually — update it from main before
customer sessions.

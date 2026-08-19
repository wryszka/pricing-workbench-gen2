#!/usr/bin/env bash
# Pricing Workbench gen2 deploy helper.
#
#   ./deploy.sh pricingv2   — deploy bundle + app to fevm-lr-pricing-v2-aws-us (PRICING_V2)
#   ./deploy.sh dev         — deploy bundle + app to fevm-lr-dev-aws-us        (DEV)
#
# Copies the right app.<target>.yaml into place before bundle deploy so the app
# picks up the target's catalog / warehouse / Genie ids and bundle path.
#
# NOTE — first deploy to a fresh workspace is two-phase (see README): the app's
# service principal doesn't exist until the app is created, but jobs grant it
# CAN_MANAGE_RUN. Create the app, capture its SP, set app_service_principal_id,
# then run this. On a workspace where the app already exists this is a no-op.
set -euo pipefail

TARGET=${1:-}
case "$TARGET" in
  pricingv2) PROFILE=PRICING_V2 ;;
  dev)       PROFILE=DEV ;;
  *)         echo "Usage: $0 pricingv2|dev" >&2; exit 1 ;;
esac

cd "$(dirname "$0")"
BUNDLE=pricing-workbench-gen2
APP=pricing-workbench-gen2

echo "==> [$TARGET] swapping src/app/app.yaml to app.${TARGET}.yaml"
cp "src/app/app.${TARGET}.yaml" "src/app/app.yaml"

echo "==> [$TARGET] building frontend"
( cd src/app/frontend && npm run build )

echo "==> [$TARGET] deploying bundle"
databricks bundle deploy --target "$TARGET" --profile "$PROFILE"

# Both targets deploy in production mode under /Workspace/Shared.
APP_PATH="/Workspace/Shared/.bundle/${BUNDLE}/${TARGET}/files/src/app"

echo "==> [$TARGET] deploying app source from $APP_PATH"
databricks apps deploy "$APP" \
    --source-code-path "$APP_PATH" --profile "$PROFILE"

echo "==> [$TARGET] done."

#!/usr/bin/env bash
# Deploys the agenda parser (Lambda behind a function URL that calls Claude on Bedrock).
# Run via `make deploy-ai` after deploy-backend, deploy-frontend and deploy-auth.
set -euo pipefail

# Everything runs inside main so bash parses the whole file before starting.
main() {
  cd "$(dirname "$0")/.."
  source infra/common.sh

  for s in "$BACKEND_STACK" "$FRONTEND_STACK" "$AUTH_STACK"; do
    stack_exists "$s" || { echo "Stack $s not found; deploy backend, frontend and auth first." >&2; exit 1; }
  done

  model="${PARSER_MODEL:-}"
  api="${PARSER_API:-runtime}"
  [ -n "$model" ] || { echo "Set PARSER_MODEL in .env first (e.g. us.anthropic.claude-haiku-4-5-20251001-v1:0)." >&2; exit 1; }
  case "$api" in
    runtime|mantle) ;;
    *) echo "PARSER_API must be 'runtime' or 'mantle', got '$api'." >&2; exit 1 ;;
  esac

  image_uri="$(output "$BACKEND_STACK" ImageUri)"
  [ -n "$image_uri" ] || { echo "ImageUri output not found on $BACKEND_STACK; run make deploy-backend first." >&2; exit 1; }
  pool_id="$(output "$AUTH_STACK" UserPoolId)"
  client_id="$(output "$AUTH_STACK" UserPoolClientId)"
  { [ -n "$pool_id" ] && [ -n "$client_id" ]; } || { echo "UserPoolId or UserPoolClientId missing on $AUTH_STACK; run make deploy-auth first." >&2; exit 1; }
  origins="$(ai_origins)"

  echo "==> Deploying '$AI_STACK' in $AWS_REGION"
  echo "    Model:   $model ($api)"
  echo "    Image:   $image_uri"
  echo "    Origins: $origins"

  aws cloudformation deploy \
    --stack-name "$AI_STACK" \
    --template-file infra/ai.yaml \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
      "ProjectName=$PROJECT_NAME" \
      "ImageUri=$image_uri" \
      "ParserModel=$model" \
      "ParserApi=$api" \
      "CognitoUserPoolId=$pool_id" \
      "CognitoClientId=$client_id" \
      "AllowedOrigins=$origins" \
    --tags "${STACK_TAGS[@]}" \
    --no-fail-on-empty-changeset

  echo
  echo "Parser URL: $(output "$AI_STACK" ParserUrl)"
  echo "Logs:       CloudWatch log group /$PROJECT_NAME/ai"
  echo
  echo "Next: make deploy-frontend (bakes the parser URL into the site build)."
}

main "$@"

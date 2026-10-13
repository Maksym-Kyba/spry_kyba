#!/usr/bin/env bash
# Deploys Amazon Cognito User Pool with Google social sign-in and Managed Login v2.
# Run via `make deploy-auth` after `make deploy-frontend`.
set -euo pipefail

# Everything runs inside main so bash parses the whole file before starting. Otherwise
# editing the script (or a git pull) during a long deploy makes bash resume mid-file.
main() {
  cd "$(dirname "$0")/.."
  source infra/common.sh

  stack_exists "$FRONTEND_STACK" || { echo "Stack $FRONTEND_STACK not found; run make deploy-frontend first." >&2; exit 1; }

  cognito_prefix="${COGNITO_DOMAIN_PREFIX:-}"
  google_id="${GOOGLE_CLIENT_ID:-}"
  google_secret="${GOOGLE_CLIENT_SECRET:-}"

  [ -n "$cognito_prefix" ] || { echo "Set COGNITO_DOMAIN_PREFIX in .env first." >&2; exit 1; }
  [ -n "$google_id" ] || { echo "Set GOOGLE_CLIENT_ID in .env first." >&2; exit 1; }
  [ -n "$google_secret" ] || { echo "Set GOOGLE_CLIENT_SECRET in .env first." >&2; exit 1; }

  urls="$(auth_urls)"
  echo "==> [1/2] Cognito User Pool + Managed Login ($AUTH_STACK)"
  echo "    Prefix:               $cognito_prefix"
  echo "    Google Client ID:     $google_id"
  echo "    Callback/Logout URLs: $urls"

  # GoogleClientSecret is passed without being logged or printed.
  aws cloudformation deploy \
    --stack-name "$AUTH_STACK" \
    --template-file infra/auth.yaml \
    --parameter-overrides \
      "ProjectName=$PROJECT_NAME" \
      "CognitoDomainPrefix=$cognito_prefix" \
      "GoogleClientId=$google_id" \
      "GoogleClientSecret=$google_secret" \
      "CallbackUrls=$urls" \
      "LogoutUrls=$urls" \
    --tags "${STACK_TAGS[@]}" \
    --no-fail-on-empty-changeset

  pool_id="$(output "$AUTH_STACK" UserPoolId)"
  client_id="$(output "$AUTH_STACK" UserPoolClientId)"
  cognito_domain="$(output "$AUTH_STACK" CognitoDomain)"
  authority="$(output "$AUTH_STACK" Authority)"

  echo
  echo "Cognito User Pool: $pool_id"
  echo "Client ID:         $client_id"
  echo "Domain:            https://$cognito_domain"
  echo "Authority:         $authority"
  echo

  echo "==> [2/2] Rebuilding and deploying frontend with auth stack outputs..."
  ./infra/deploy-frontend.sh
}

main "$@"

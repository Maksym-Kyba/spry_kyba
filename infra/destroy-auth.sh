#!/usr/bin/env bash
# Deletes the Amazon Cognito auth stack.
set -euo pipefail

# Everything runs inside main so bash parses the whole file before starting. Otherwise
# editing the script (or a git pull) during a long deploy makes bash resume mid-file.
main() {
  cd "$(dirname "$0")/.."
  source infra/common.sh

  stack_exists "$AUTH_STACK" || { echo "Stack $AUTH_STACK not found."; exit 0; }

  read -r -p "Delete stack $AUTH_STACK in $AWS_REGION? Type the app name to confirm: " answer
  [ "$answer" = "$PROJECT_NAME" ] || { echo "Aborted."; exit 1; }

  echo "==> Deleting $AUTH_STACK"
  aws cloudformation delete-stack --stack-name "$AUTH_STACK"
  aws cloudformation wait stack-delete-complete --stack-name "$AUTH_STACK"
  echo "Done."
}

main "$@"

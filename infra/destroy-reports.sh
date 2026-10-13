#!/usr/bin/env bash
# Deletes the weekly reports stack (SQS queue, Scheduler, builder Lambda, S3 bucket,
# SES identities, mailer Lambda).
set -euo pipefail

# Everything runs inside main so bash parses the whole file before starting. Otherwise
# editing the script (or a git pull) during a long deploy makes bash resume mid-file.
main() {
  cd "$(dirname "$0")/.."
  source infra/common.sh

  stack_exists "$REPORTS_STACK" || { echo "Stack $REPORTS_STACK not found."; exit 0; }

  read -r -p "Delete stack $REPORTS_STACK in $AWS_REGION? Type the app name to confirm: " answer
  [ "$answer" = "$PROJECT_NAME" ] || { echo "Aborted."; exit 1; }

  bucket="$(output "$REPORTS_STACK" ReportBucketName)"
  if [ -n "$bucket" ]; then
    echo "==> Emptying s3://$bucket"
    aws s3 rm "s3://$bucket" --recursive >/dev/null 2>&1 || true
  fi

  echo "==> Deleting $REPORTS_STACK"
  aws cloudformation delete-stack --stack-name "$REPORTS_STACK"
  aws cloudformation wait stack-delete-complete --stack-name "$REPORTS_STACK"
  echo "Done."
}

main "$@"

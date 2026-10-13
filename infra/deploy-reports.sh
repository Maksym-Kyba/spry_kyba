#!/usr/bin/env bash
# Deploys the weekly reports stack (SQS, EventBridge Scheduler, VPC builder Lambda,
# S3 gateway endpoint, private S3 bucket, SES email identities, mailer Lambda).
# Run via `make deploy-reports` after `make deploy-backend`.
set -euo pipefail

# Everything runs inside main so bash parses the whole file before starting. Otherwise
# editing the script (or a git pull) during a long deploy makes bash resume mid-file.
main() {
  cd "$(dirname "$0")/.."
  source infra/common.sh

  stack_exists "$BACKEND_STACK" || { echo "Stack $BACKEND_STACK not found; run make deploy-backend first." >&2; exit 1; }

  domain="${REPORT_DOMAIN:-}"
  email="${REPORT_EMAIL:-}"

  [ -n "$domain" ] || { echo "Set REPORT_DOMAIN in .env first." >&2; exit 1; }
  [ -n "$email" ] || { echo "Set REPORT_EMAIL in .env first." >&2; exit 1; }

  # Backend stack outputs must exist (requires deploy-backend with the updated template)
  image_uri="$(output "$BACKEND_STACK" ImageUri)"
  [ -n "$image_uri" ] || { echo "ImageUri output not found on $BACKEND_STACK; run make deploy-backend first." >&2; exit 1; }

  vpc_id="$(output "$BACKEND_STACK" VpcId)"
  [ -n "$vpc_id" ] || { echo "VpcId output not found on $BACKEND_STACK; run make deploy-backend first." >&2; exit 1; }

  subnet_ids="$(output "$BACKEND_STACK" SubnetIds)"
  [ -n "$subnet_ids" ] || { echo "SubnetIds output not found on $BACKEND_STACK; run make deploy-backend first." >&2; exit 1; }

  security_group_id="$(output "$BACKEND_STACK" FunctionSecurityGroup)"
  [ -n "$security_group_id" ] || { echo "FunctionSecurityGroup output not found on $BACKEND_STACK; run make deploy-backend first." >&2; exit 1; }

  route_table_id="$(output "$BACKEND_STACK" RouteTableId)"
  [ -n "$route_table_id" ] || { echo "RouteTableId output not found on $BACKEND_STACK; run make deploy-backend first." >&2; exit 1; }

  db_endpoint="$(output "$BACKEND_STACK" DatabaseEndpoint)"
  [ -n "$db_endpoint" ] || { echo "DatabaseEndpoint output not found on $BACKEND_STACK; run make deploy-backend first." >&2; exit 1; }

  PASSWORD_PARAM="/$PROJECT_NAME/db-password"
  db_password="$(aws ssm get-parameter --name "$PASSWORD_PARAM" --with-decryption --query Parameter.Value --output text)"

  schedule_expr="${SCHEDULE_EXPRESSION:-cron(0 7 ? * MON *)}"

  account="$(aws sts get-caller-identity --query Account --output text)"
  echo "==> Deploying '$REPORTS_STACK' to account $account in $AWS_REGION"
  echo "    Image:            $image_uri"
  echo "    Schedule:         $schedule_expr (Europe/Kyiv)"
  echo "    Report Domain:    $domain"
  echo "    Recipient Email:  $email"

  aws cloudformation deploy \
    --stack-name "$REPORTS_STACK" \
    --template-file infra/reports.yaml \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
      "ProjectName=$PROJECT_NAME" \
      "ImageUri=$image_uri" \
      "VpcId=$vpc_id" \
      "SubnetIds=$subnet_ids" \
      "SecurityGroupId=$security_group_id" \
      "RouteTableId=$route_table_id" \
      "DBEndpoint=$db_endpoint" \
      "DBPassword=$db_password" \
      "ReportDomain=$domain" \
      "RecipientEmail=$email" \
      "ScheduleExpression=$schedule_expr" \
    --tags "${STACK_TAGS[@]}" \
    --no-fail-on-empty-changeset

  queue_url="$(output "$REPORTS_STACK" ReportQueueUrl)"
  bucket_name="$(output "$REPORTS_STACK" ReportBucketName)"

  echo
  echo "Reports Bucket:     s3://$bucket_name"
  echo "Report Queue:       $queue_url"
  echo "Dead-Letter Queue:  $(output "$REPORTS_STACK" ReportDeadLetterQueueUrl)"
  echo
  echo "Amazon SES DKIM CNAME Records for $domain:"
  echo "Add these 3 CNAME records at your DNS provider to enable DKIM signing:"
  echo "  1) $(output "$REPORTS_STACK" DkimDNSTokenName1)  ->  $(output "$REPORTS_STACK" DkimDNSTokenValue1)"
  echo "  2) $(output "$REPORTS_STACK" DkimDNSTokenName2)  ->  $(output "$REPORTS_STACK" DkimDNSTokenValue2)"
  echo "  3) $(output "$REPORTS_STACK" DkimDNSTokenName3)  ->  $(output "$REPORTS_STACK" DkimDNSTokenValue3)"
  echo
  echo "Note: If your AWS account is in SES sandbox, also check $email for a verification link from AWS."
}

main "$@"

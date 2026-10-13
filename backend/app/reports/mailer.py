import logging
import os
import urllib.parse
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import boto3

logger = logging.getLogger("reports.mailer")
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

s3_client = boto3.client("s3")
ses_client = boto3.client("ses")


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """Handle S3 ObjectCreated events for reports/*.csv and send via Amazon SES."""
    records = event.get("Records", [])
    if not records:
        logger.warning("No records found in event")
        return {"status": "no_records"}

    report_domain = os.environ.get("REPORT_DOMAIN")
    recipient_email = os.environ.get("RECIPIENT_EMAIL")

    if not report_domain or not recipient_email:
        raise ValueError("REPORT_DOMAIN and RECIPIENT_EMAIL environment variables must be set")

    sender_email = f"reports@{report_domain}"
    results = []

    for record in records:
        bucket = record["s3"]["bucket"]["name"]
        raw_key = record["s3"]["object"]["key"]
        key = urllib.parse.unquote_plus(raw_key)

        # Extract week from key (e.g. 'reports/2026-W39.csv' -> '2026-W39')
        week = key.split("/")[-1].replace(".csv", "")

        logger.info(
            "Report mailer started: trigger=s3 transport=s3 week=%s key=%s bucket=%s",
            week,
            key,
            bucket,
        )

        # Fetch CSV from S3 (read-only, never write)
        response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_bytes = response["Body"].read()

        # Build MIME email message with CSV attachment
        msg = MIMEMultipart()
        msg["Subject"] = f"Weekly Meetings Report - {week}"
        msg["From"] = sender_email
        msg["To"] = recipient_email

        body_text = (
            f"Hello,\n\n"
            f"Please find attached the weekly meetings report for {week}.\n\n"
            f"Report details:\n"
            f"- Week: {week}\n"
            f"- S3 object: s3://{bucket}/{key}\n\n"
            f"Best regards,\n"
            f"Meetings App"
        )
        msg.attach(MIMEText(body_text, "plain", "utf-8"))

        attachment = MIMEApplication(csv_bytes, _subtype="csv")
        attachment.add_header("Content-Disposition", "attachment", filename=f"{week}.csv")
        msg.attach(attachment)

        # Send via SES
        ses_client.send_raw_email(
            Source=sender_email,
            Destinations=[recipient_email],
            RawMessage={"Data": msg.as_string()},
        )

        logger.info(
            "Report mailer completed: trigger=s3 transport=s3 week=%s email sent from=%s to=%s",
            week,
            sender_email,
            recipient_email,
        )
        results.append({"week": week, "key": key, "sent_to": recipient_email})

    return {"status": "ok", "sent": len(results), "results": results}

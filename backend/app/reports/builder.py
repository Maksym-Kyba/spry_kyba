import asyncio
import json
import logging
import os
from typing import Any

import boto3
from fastapi import FastAPI, HTTPException, Request

from app.reports.weekly import build_weekly_report, get_previous_iso_week

logger = logging.getLogger("reports.builder")
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Meetings Report Builder")
s3_client = boto3.client("s3")


def _resolve_trigger_and_week(payload: dict[str, Any], is_sqs: bool) -> tuple[str, str, str]:
    """Determine trigger, transport, and week from an event payload.

    - "source": "schedule" -> trigger=schedule
    - "source": "manual" -> trigger=sqs
    - direct invocation -> trigger=direct
    Transport is 'sqs' or 'direct'.
    """
    transport = "sqs" if is_sqs else "direct"
    source = payload.get("source")

    if source == "schedule":
        trigger = "schedule"
    elif source == "manual":
        trigger = "sqs"
    elif is_sqs:
        trigger = payload.get("trigger", "sqs")
    else:
        trigger = payload.get("trigger", "direct")

    raw_week = payload.get("week")
    if isinstance(raw_week, str) and raw_week.strip():
        week = raw_week.strip()
    else:
        week = get_previous_iso_week()

    return trigger, transport, week


async def _process_single_request(payload: dict[str, Any], is_sqs: bool) -> dict[str, Any]:
    trigger, transport, week = _resolve_trigger_and_week(payload, is_sqs)
    logger.info(
        "Report builder started: trigger=%s transport=%s week=%s",
        trigger,
        transport,
        week,
    )

    # build_weekly_report raises ValueError if week is malformed, propagating 500 to LWA
    csv_bytes = await build_weekly_report(week)

    bucket = os.environ.get("REPORTS_BUCKET")
    if not bucket:
        raise ValueError("REPORTS_BUCKET environment variable is not set")

    key = f"reports/{week}.csv"
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=csv_bytes,
        ContentType="text/csv",
    )
    logger.info(
        "Report builder completed: trigger=%s transport=%s week=%s s3://%s/%s (%d bytes)",
        trigger,
        transport,
        week,
        bucket,
        key,
        len(csv_bytes),
    )
    return {"status": "ok", "trigger": trigger, "transport": transport, "week": week, "key": key}


async def handle_event(event: dict[str, Any]) -> dict[str, Any]:
    """Process an event from either SQS (Event Source Mapping) or direct invocation."""
    try:
        # Check if this is an SQS Event Source Mapping payload
        records = event.get("Records")
        if (
            isinstance(records, list)
            and len(records) > 0
            and records[0].get("eventSource") == "aws:sqs"
        ):
            results = []
            for record in records:
                raw_body = record.get("body", "{}")
                if isinstance(raw_body, str):
                    try:
                        payload = json.loads(raw_body)
                    except json.JSONDecodeError:
                        payload = {"raw": raw_body}
                elif isinstance(raw_body, dict):
                    payload = raw_body
                else:
                    payload = {}
                res = await _process_single_request(payload, is_sqs=True)
                results.append(res)
            return {"status": "ok", "processed": len(results), "results": results}

        # Otherwise treated as direct invocation payload
        return await _process_single_request(event, is_sqs=False)
    except Exception as exc:
        logger.error("Report builder failed: %s", exc, exc_info=True)
        # Raise HTTPException with 500 so LWA returns HTTP 500 and fails the Lambda invocation
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/events")
@app.post("/")
async def events_endpoint(request: Request) -> dict[str, Any]:
    event_payload = await request.json()
    return await handle_event(event_payload)


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """Standard Lambda handler function for testing or direct Lambda runtime."""
    return asyncio.run(handle_event(event))

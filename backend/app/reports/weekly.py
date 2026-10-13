import csv
import io
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import SessionLocal
from app.models import Meeting

ISO_WEEK_REGEX = re.compile(r"^(\d{4})-W(0[1-9]|[1-4][0-9]|5[0-3])$")


def parse_iso_week(week: str) -> tuple[datetime, datetime, str]:
    """Parse an ISO week string (e.g. '2026-W39') into:

    (start_of_week_utc, end_of_week_utc, prev_week_str).
    """
    match = ISO_WEEK_REGEX.match(week)
    if not match:
        raise ValueError(f"Invalid ISO week format: '{week}'. Expected YYYY-Www (e.g. '2026-W39').")

    year = int(match.group(1))
    week_num = int(match.group(2))

    start = datetime.fromisocalendar(year, week_num, 1).replace(tzinfo=UTC)
    end = start + timedelta(days=7)

    prev_start = start - timedelta(days=7)
    prev_year, prev_week_num, _ = prev_start.isocalendar()
    prev_week = f"{prev_year}-W{prev_week_num:02d}"

    return start, end, prev_week


def get_previous_iso_week() -> str:
    """Return the previous ISO week string based on the current UTC time."""
    now = datetime.now(UTC)
    last_week = now - timedelta(days=7)
    year, week_num, _ = last_week.isocalendar()
    return f"{year}-W{week_num:02d}"


async def _generate_report(week: str, session: AsyncSession) -> bytes:
    start, end, prev_week = parse_iso_week(week)
    prev_start = start - timedelta(days=7)

    # Fetch current week's meetings with participants eagerly loaded
    stmt_current = (
        select(Meeting)
        .options(selectinload(Meeting.participants))
        .where(Meeting.starts_at >= start, Meeting.starts_at < end)
        .order_by(Meeting.starts_at)
    )
    result_current = await session.execute(stmt_current)
    current_meetings = list(result_current.scalars().all())

    # Fetch previous week's meetings
    stmt_prev = select(Meeting).where(Meeting.starts_at >= prev_start, Meeting.starts_at < start)
    result_prev = await session.execute(stmt_prev)
    prev_meetings = list(result_prev.scalars().all())

    # Compute metrics
    current_count = len(current_meetings)
    current_total_seconds = sum((m.ends_at - m.starts_at).total_seconds() for m in current_meetings)
    current_hours = current_total_seconds / 3600.0

    prev_count = len(prev_meetings)
    prev_total_seconds = sum((m.ends_at - m.starts_at).total_seconds() for m in prev_meetings)
    prev_hours = prev_total_seconds / 3600.0

    count_diff = current_count - prev_count
    hours_diff = current_hours - prev_hours

    # Five longest meetings in the target week
    longest_meetings = sorted(
        current_meetings,
        key=lambda m: (m.ends_at - m.starts_at).total_seconds(),
        reverse=True,
    )[:5]

    output = io.StringIO()
    writer = csv.writer(output)

    # Metadata and summary
    writer.writerow(["Report", f"Weekly Meetings Report - {week}"])
    writer.writerow(["Previous Week", prev_week])
    writer.writerow([])
    writer.writerow(["Metric", f"Current Week ({week})", f"Previous Week ({prev_week})", "Change"])
    writer.writerow(["Meetings Count", str(current_count), str(prev_count), f"{count_diff:+d}"])
    writer.writerow(
        ["Total Hours", f"{current_hours:.2f}", f"{prev_hours:.2f}", f"{hours_diff:+.2f}"]
    )
    writer.writerow([])

    # Five longest meetings details
    writer.writerow(["Top 5 Longest Meetings"])
    writer.writerow(["Title", "Start (UTC)", "Duration (Hours)", "Participants"])
    for m in longest_meetings:
        duration_h = (m.ends_at - m.starts_at).total_seconds() / 3600.0
        participants_str = ", ".join(p.name for p in m.participants) if m.participants else "None"
        writer.writerow([m.title, m.starts_at.isoformat(), f"{duration_h:.2f}", participants_str])

    return output.getvalue().encode("utf-8")


async def build_weekly_report(week: str, session: AsyncSession | None = None) -> bytes:
    """Build a weekly meetings report for the specified ISO week (e.g.

    '2026-W39') and return it as CSV bytes.
    """
    if session is not None:
        return await _generate_report(week, session)

    async with SessionLocal() as s:
        return await _generate_report(week, s)

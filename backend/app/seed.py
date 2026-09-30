"""Insert sample participants and meetings.

Safe to run more than once."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import Meeting, Participant

PARTICIPANTS = [
    ("Olena Koval", "olena@example.com"),
    ("Taras Shevchuk", "taras@example.com"),
    ("Iryna Bondar", "iryna@example.com"),
    ("Andrii Melnyk", "andrii@example.com"),
]


def sample_meetings(people: list[Participant]) -> list[Meeting]:
    base = datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0)
    return [
        Meeting(
            title="Sprint planning",
            description="Plan the work for the next sprint.",
            starts_at=base + timedelta(days=1),
            ends_at=base + timedelta(days=1, hours=1),
            place="Room 204",
            participants=people[:3],
        ),
        Meeting(
            title="Design review",
            description="Walk through the new meeting form.",
            starts_at=base + timedelta(days=2, hours=4),
            ends_at=base + timedelta(days=2, hours=5),
            place="https://meet.example.com/design",
            participants=[people[0], people[3]],
        ),
        Meeting(
            title="Retrospective",
            starts_at=base + timedelta(days=5, hours=6),
            ends_at=base + timedelta(days=5, hours=7, minutes=30),
            place="Main hall",
            participants=people,
        ),
    ]


async def seed() -> None:
    async with SessionLocal() as session:
        existing = {p.email: p for p in await session.scalars(select(Participant))}
        for name, email in PARTICIPANTS:
            if email not in existing:
                existing[email] = Participant(name=name, email=email)
                session.add(existing[email])
        await session.flush()
        people = [existing[email] for _, email in PARTICIPANTS]

        existing_meetings = list(await session.scalars(select(Meeting)))
        if not existing_meetings:
            session.add_all(sample_meetings(people))
            await session.commit()
            print("Seed data inserted: sample participants and meetings.")
        else:
            await session.commit()
            print("Sample participants inserted. Meetings already exist.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())

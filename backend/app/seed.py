"""Insert sample participants, and sample meetings for every user who has none yet.

Users appear in the database on their first signed-in request, so sign up in the app first.
Safe to run more than once."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import Meeting, Participant, User

PARTICIPANTS = [
    ("Olena Koval", "olena@example.com"),
    ("Taras Shevchuk", "taras@example.com"),
    ("Iryna Bondar", "iryna@example.com"),
    ("Andrii Melnyk", "andrii@example.com"),
]


def sample_meetings(owner: User, people: list[Participant]) -> list[Meeting]:
    base = datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0)
    return [
        Meeting(
            title="Sprint planning",
            description="Plan the work for the next sprint.",
            starts_at=base + timedelta(days=1),
            ends_at=base + timedelta(days=1, hours=1),
            place="Room 204",
            participants=people[:3],
            owner_id=owner.id,
        ),
        Meeting(
            title="Design review",
            description="Walk through the new meeting form.",
            starts_at=base + timedelta(days=2, hours=4),
            ends_at=base + timedelta(days=2, hours=5),
            place="https://meet.example.com/design",
            participants=[people[0], people[3]],
            owner_id=owner.id,
        ),
        Meeting(
            title="Retrospective",
            starts_at=base + timedelta(days=5, hours=6),
            ends_at=base + timedelta(days=5, hours=7, minutes=30),
            place="Main hall",
            participants=people,
            owner_id=owner.id,
        ),
    ]


async def seed() -> None:
    async with SessionLocal() as session:
        existing = {p.email: p for p in await session.scalars(select(Participant))}
        for name, email in PARTICIPANTS:
            if email not in existing:
                existing[email] = Participant(name=name, email=email)
                session.add(existing[email])
        people = [existing[email] for _, email in PARTICIPANTS]

        owners = set(await session.scalars(select(Meeting.owner_id).distinct()))
        users = [u for u in await session.scalars(select(User)) if u.id not in owners]
        for user in users:
            session.add_all(sample_meetings(user, people))
        await session.commit()
    await engine.dispose()

    if users:
        print(f"Seed data inserted; sample meetings for {', '.join(u.email for u in users)}.")
    else:
        print("Sample participants inserted. Every user already has meetings (or none signed up).")


if __name__ == "__main__":
    asyncio.run(seed())

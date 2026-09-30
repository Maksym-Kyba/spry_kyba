"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "participants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "meetings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("place", sa.String(200), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("ends_at > starts_at", name="ck_meetings_ends_after_starts"),
    )
    op.create_index("ix_meetings_starts_at", "meetings", ["starts_at"])
    op.create_table(
        "meeting_participants",
        sa.Column(
            "meeting_id",
            sa.Uuid(),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "participant_id",
            sa.Uuid(),
            sa.ForeignKey("participants.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("meeting_participants")
    op.drop_index("ix_meetings_starts_at", table_name="meetings")
    op.drop_table("meetings")
    op.drop_table("participants")

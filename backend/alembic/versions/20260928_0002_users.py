"""users, and an owner for every meeting

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-28

Meetings that exist before this migration had no owner. They are kept and assigned to a
placeholder user that nobody can sign in as (its cognito_sub is not a Cognito id); move them
to a real account with `UPDATE meetings SET owner_id = <users.id> WHERE owner_id = <placeholder>`.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLACEHOLDER_SUB = "unowned-before-0002"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cognito_sub", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.add_column("meetings", sa.Column("owner_id", sa.Uuid(), nullable=True))
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM meetings)")).scalar():
        placeholder = uuid.uuid4()
        bind.execute(
            sa.text(
                "INSERT INTO users (id, cognito_sub, email, name) "
                "VALUES (:id, :sub, '', 'Meetings from before sign-in')"
            ),
            {"id": placeholder, "sub": PLACEHOLDER_SUB},
        )
        bind.execute(sa.text("UPDATE meetings SET owner_id = :id"), {"id": placeholder})
    op.alter_column("meetings", "owner_id", nullable=False)
    op.create_foreign_key(
        "meetings_owner_id_fkey", "meetings", "users", ["owner_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_meetings_owner_id", "meetings", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_meetings_owner_id", table_name="meetings")
    op.drop_constraint("meetings_owner_id_fkey", "meetings", type_="foreignkey")
    op.drop_column("meetings", "owner_id")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

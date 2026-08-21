"""Create calendar events table.

Revision ID: 20260828_15
Revises: 20260827_14
Create Date: 2026-08-28
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260828_15"
down_revision: str | None = "20260827_14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

event_type = sa.Enum(
    "opportunity_deadline", "application", "interview", "document_submission", "follow_up",
    name="calendareventtype", native_enum=False,
)
deadline_state = sa.Enum(
    "upcoming", "closing_soon", "today", "passed", "extended", "changed",
    "unconfirmed", "rolling_deadline",
    name="deadlinestate", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("type", event_type, nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("reminder_minutes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("deadline_state", deadline_state, nullable=False),
        sa.Column("related_entity_id", sa.String(255)),
        sa.Column("previous_starts_at", sa.DateTime(timezone=True)),
        sa.Column("recurrence", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("external_calendar_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calendar_events_user_id", "calendar_events", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_calendar_events_user_id", table_name="calendar_events")
    op.drop_table("calendar_events")

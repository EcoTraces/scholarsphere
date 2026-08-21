"""Create application guidance plans table.

Revision ID: 20260829_16
Revises: 20260828_15
Create Date: 2026-08-29
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260829_16"
down_revision: str | None = "20260828_15"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "guidance_plans",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("opportunity_id", sa.String(255), nullable=False),
        sa.Column("items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "recommendation_letters", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("timeline_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "follow_up_reminders", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submission_confirmation", postgresql.JSONB(astext_type=sa.Text())),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guidance_plans_user_id", "guidance_plans", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_guidance_plans_user_id", table_name="guidance_plans")
    op.drop_table("guidance_plans")

"""Create engagement events table.

Revision ID: 20260904_22
Revises: 20260903_21
Create Date: 2026-09-04
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260904_22"
down_revision: str | None = "20260903_21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "engagement_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("country", sa.String(255), nullable=False),
        sa.Column("study_level", sa.String(255), nullable=False),
        sa.Column("field", sa.String(255), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("identifiable_sharing_consent", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_engagement_events_provider_id", "engagement_events", ["provider_id"])


def downgrade() -> None:
    op.drop_index("ix_engagement_events_provider_id", table_name="engagement_events")
    op.drop_table("engagement_events")

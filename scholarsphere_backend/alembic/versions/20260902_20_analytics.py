"""Create opportunity view events table.

Revision ID: 20260902_20
Revises: 20260901_19
Create Date: 2026-09-02
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260902_20"
down_revision: str | None = "20260901_19"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "opportunity_view_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["external_opportunities.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_opportunity_view_events_user_id",
        "opportunity_view_events",
        ["user_id"],
    )
    op.create_index(
        "ix_opportunity_view_events_opportunity_id",
        "opportunity_view_events",
        ["opportunity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_opportunity_view_events_opportunity_id", table_name="opportunity_view_events")
    op.drop_index("ix_opportunity_view_events_user_id", table_name="opportunity_view_events")
    op.drop_table("opportunity_view_events")

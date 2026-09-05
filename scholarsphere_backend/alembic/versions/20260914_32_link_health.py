"""Add link_checked_at for periodic application-link health monitoring.

Revision ID: 20260914_32
Revises: 20260913_31
Create Date: 2026-09-14
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260914_32"
down_revision: str | None = "20260913_31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "external_opportunities",
        sa.Column("link_checked_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_column("external_opportunities", "link_checked_at")

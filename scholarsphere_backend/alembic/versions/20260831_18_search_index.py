"""Create search index and search history tables.

Revision ID: 20260831_18
Revises: 20260830_17
Create Date: 2026-08-31
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260831_18"
down_revision: str | None = "20260830_17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_index_entries",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "search_history_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("query", sa.String(500), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("searched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_search_history_entries_user_id", "search_history_entries", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_search_history_entries_user_id", table_name="search_history_entries")
    op.drop_table("search_history_entries")
    op.drop_table("search_index_entries")

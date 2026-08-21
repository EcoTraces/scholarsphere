"""Create collection ledger entries table.

Revision ID: 20260913_31
Revises: 20260912_30
Create Date: 2026-09-13
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260913_31"
down_revision: str | None = "20260912_30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

collection_source_type = sa.Enum(
    "manualAdministrator",
    "providerSubmission",
    "officialApi",
    "approvedRss",
    "structuredFeed",
    "controlledWebCollection",
    "userSubmission",
    name="collectionsourcetype",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "collection_ledger_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", collection_source_type, nullable=False),
        sa.Column("source_location", sa.Text(), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_by_user_id", sa.String(255), nullable=True),
        sa.Column("automated", sa.Boolean(), nullable=False),
        sa.Column("approved_source", sa.Boolean(), nullable=False),
        sa.Column("verification_status", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["external_opportunities.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_collection_ledger_entries_opportunity_id",
        "collection_ledger_entries",
        ["opportunity_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_collection_ledger_entries_opportunity_id",
        table_name="collection_ledger_entries",
    )
    op.drop_table("collection_ledger_entries")

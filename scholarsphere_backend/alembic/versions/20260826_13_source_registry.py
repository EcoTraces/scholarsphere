"""Create source registry entries table.

Revision ID: 20260826_13
Revises: 20260825_12
Create Date: 2026-08-26
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260826_13"
down_revision: str | None = "20260825_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

source_type = sa.Enum(
    "official_university_website", "official_government_portal", "embassy_website",
    "foundation_website", "international_organization", "official_application_portal",
    "approved_api", "approved_rss_feed", "verified_provider_submission",
    "trusted_secondary_source", "community_submission",
    name="opportunitysourcetype", native_enum=False,
)
reliability_level = sa.Enum("a", "b", "c", "d", "e", "f", name="reliabilitylevel", native_enum=False)
verification_status = sa.Enum(
    "pending", "approved", "blocked", "expired",
    name="sourceverificationstatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "source_registry_entries",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("type", source_type, nullable=False),
        sa.Column("domain", sa.String(500), nullable=False),
        sa.Column("normalized_domain", sa.String(500), nullable=False),
        sa.Column("country", sa.String(255), nullable=False),
        sa.Column("organization_id", sa.String(255), nullable=False),
        sa.Column("trust_level", reliability_level, nullable=False),
        sa.Column("trust_score", sa.Integer(), nullable=False),
        sa.Column("verification_status", verification_status, nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("last_successful_access", sa.DateTime(timezone=True)),
        sa.Column("accuracy_rate", sa.Float(), nullable=False),
        sa.Column("correction_count", sa.Integer(), nullable=False),
        sa.Column("rejection_count", sa.Integer(), nullable=False),
        sa.Column("is_blocked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("parser_configuration", postgresql.JSONB(astext_type=sa.Text())),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_registry_entries_normalized_domain",
        "source_registry_entries",
        ["normalized_domain"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_source_registry_entries_normalized_domain", table_name="source_registry_entries"
    )
    op.drop_table("source_registry_entries")

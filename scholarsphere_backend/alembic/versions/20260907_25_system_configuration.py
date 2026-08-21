"""Create platform configurations table.

Revision ID: 20260907_25
Revises: 20260906_24
Create Date: 2026-09-07
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260907_25"
down_revision: str | None = "20260906_24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_configurations",
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("platform_name", sa.String(255), nullable=False),
        sa.Column("logo_location", sa.String(1000), nullable=False),
        sa.Column("brand_primary_color", sa.String(16), nullable=False),
        sa.Column("email_sender_name", sa.String(255), nullable=False),
        sa.Column("email_sender_address", sa.String(320), nullable=False),
        sa.Column("verification_expiration_days", sa.Integer(), nullable=False),
        sa.Column("supported_countries", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("supported_languages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("opportunity_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("document_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("maximum_file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("applicant_registration_enabled", sa.Boolean(), nullable=False),
        sa.Column("provider_registration_enabled", sa.Boolean(), nullable=False),
        sa.Column("maintenance_mode", sa.Boolean(), nullable=False),
        sa.Column("feature_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("environment", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("security_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommendation_settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fraud_rule_settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("integration_settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("notification_settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.Column("change_reason", sa.String(1000), nullable=False),
        sa.PrimaryKeyConstraint("version"),
    )


def downgrade() -> None:
    op.drop_table("platform_configurations")

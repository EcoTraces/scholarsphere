"""Create privacy consent, request, access, and incident tables.

Revision ID: 20260824_11
Revises: 20260823_10
Create Date: 2026-08-24
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260824_11"
down_revision: str | None = "20260823_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

consent_type = sa.Enum(
    "privacy_policy", "terms_and_conditions", "cookies", "marketing", "notifications",
    "personalized_recommendations", "sensitive_data", "document_storage", "third_party_sharing",
    name="consenttype", native_enum=False,
)
privacy_request_type = sa.Enum(
    "data_export", "account_deletion", "data_correction", "document_deletion",
    name="privacyrequesttype", native_enum=False,
)
privacy_request_status = sa.Enum(
    "submitted", "in_review", "completed", "rejected", "cancelled",
    name="privacyrequeststatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "consent_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("type", consent_type, nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "type", name="uq_consent_user_type"),
    )
    op.create_index("ix_consent_records_user_id", "consent_records", ["user_id"])
    op.create_table(
        "privacy_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("type", privacy_request_type, nullable=False),
        sa.Column("status", privacy_request_status, nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_privacy_requests_user_id", "privacy_requests", ["user_id"])
    op.create_table(
        "organization_access_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("organization_id", sa.String(255), nullable=False),
        sa.Column("organization_name", sa.String(512), nullable=False),
        sa.Column("data_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consent_record_type", consent_type, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organization_access_records_user_id", "organization_access_records", ["user_id"]
    )
    op.create_table(
        "privacy_incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("affected_user_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("privacy_incidents")
    op.drop_index("ix_organization_access_records_user_id", table_name="organization_access_records")
    op.drop_table("organization_access_records")
    op.drop_index("ix_privacy_requests_user_id", table_name="privacy_requests")
    op.drop_table("privacy_requests")
    op.drop_index("ix_consent_records_user_id", table_name="consent_records")
    op.drop_table("consent_records")

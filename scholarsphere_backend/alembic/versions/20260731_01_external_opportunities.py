"""Create external opportunity import and verification tables.

Revision ID: 20260731_01
Revises:
Create Date: 2026-07-31
"""

from typing import Sequence
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260731_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

processing_status = sa.Enum(
    "pending", "normalized", "imported", "skipped", "duplicate", "failed",
    name="processingstatus", native_enum=False,
)
verification_status = sa.Enum(
    "pending", "verified", "reverification_required", "rejected", "suspicious",
    "expired", "archived", name="verificationstatus", native_enum=False,
)
publication_status = sa.Enum(
    "unpublished", "published", "archived",
    name="publicationstatus", native_enum=False,
)
sync_status = sa.Enum(
    "running", "completed", "partially_completed", "failed",
    name="syncstatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "opportunity_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_code", sa.String(64), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("base_url", sa.String(2048), nullable=False),
        sa.Column("authentication_type", sa.String(64), nullable=False),
        sa.Column("trust_level", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_failed_sync_at", sa.DateTime(timezone=True)),
        sa.Column("most_recent_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_code"),
    )
    op.create_table(
        "external_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(512), nullable=False),
        sa.Column("external_reference", sa.String(512)),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("opportunity_type", sa.String(128), nullable=False),
        sa.Column("provider_name", sa.String(512), nullable=False),
        sa.Column("provider_code", sa.String(128)),
        sa.Column("country", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("opening_date", sa.Date()),
        sa.Column("deadline", sa.Date()),
        sa.Column("opportunity_status", sa.String(128), nullable=False),
        sa.Column("funding_type", sa.String(128)),
        sa.Column("award_floor", sa.Float()),
        sa.Column("award_ceiling", sa.Float()),
        sa.Column("currency", sa.String(3)),
        sa.Column("official_source_url", sa.String(2048)),
        sa.Column("official_application_url", sa.String(2048)),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("external_fingerprint", sa.String(64), nullable=False),
        sa.Column("duplicate_review_required", sa.Boolean(), nullable=False),
        sa.Column("verification_status", verification_status, nullable=False),
        sa.Column("publication_status", publication_status, nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_external_update_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["opportunity_sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_external_source_external_id"),
    )
    op.create_index("ix_external_fingerprint", "external_opportunities", ["external_fingerprint"])
    op.create_index(
        "ix_external_verification_publication", "external_opportunities",
        ["verification_status", "publication_status"],
    )
    op.create_table(
        "raw_external_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(512), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processing_status", processing_status, nullable=False),
        sa.Column("processing_error", sa.Text()),
        sa.Column("opportunity_id", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["opportunity_sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["external_opportunities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_raw_source_external_id"),
    )
    op.create_index("ix_raw_external_processing_status", "raw_external_opportunities", ["processing_status"])
    op.create_index("ix_raw_external_opportunities_source_id", "raw_external_opportunities", ["source_id"])
    op.create_table(
        "external_opportunity_verification_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("previous_status", sa.String(64), nullable=False),
        sa.Column("new_status", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("changed_fields", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["external_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_external_opportunity_verification_history_opportunity_id", "external_opportunity_verification_history", ["opportunity_id"])
    op.create_table(
        "external_opportunity_verification_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("verification_officer_id", sa.String(255)),
        sa.Column("source_checked", sa.Boolean(), nullable=False),
        sa.Column("application_link_checked", sa.Boolean(), nullable=False),
        sa.Column("deadline_checked", sa.Boolean(), nullable=False),
        sa.Column("duplicate_checked", sa.Boolean(), nullable=False),
        sa.Column("decision", sa.String(64), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["external_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opportunity_id"),
    )
    op.create_table(
        "opportunity_sync_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.String(255)),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("triggered_by", sa.String(255)),
        sa.Column("correlation_id", sa.String(255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("records_created", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("records_skipped", sa.Integer(), nullable=False),
        sa.Column("records_failed", sa.Integer(), nullable=False),
        sa.Column("final_status", sync_status, nullable=False),
        sa.Column("error_summary", sa.Text()),
        sa.ForeignKeyConstraint(["source_id"], ["opportunity_sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunity_sync_history_task_id", "opportunity_sync_history", ["task_id"])
    op.create_index("ix_opportunity_sync_history_source_id", "opportunity_sync_history", ["source_id"])
    op.create_index("ix_opportunity_sync_history_triggered_by", "opportunity_sync_history", ["triggered_by"])
    op.create_index("ix_opportunity_sync_history_correlation_id", "opportunity_sync_history", ["correlation_id"])
    op.create_table(
        "external_import_audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("previous_value", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("correlation_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["external_opportunities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_external_import_audit_log_opportunity_id", "external_import_audit_log", ["opportunity_id"])
    op.create_index("ix_external_import_audit_log_correlation_id", "external_import_audit_log", ["correlation_id"])

    sources = sa.table(
        "opportunity_sources",
        sa.column("id", sa.Uuid()), sa.column("source_code", sa.String()),
        sa.column("source_name", sa.String()), sa.column("source_type", sa.String()),
        sa.column("base_url", sa.String()), sa.column("authentication_type", sa.String()),
        sa.column("trust_level", sa.String()), sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(sources, [
        {"id": uuid.UUID("11111111-1111-4111-8111-111111111111"), "source_code": "grants_gov", "source_name": "Grants.gov", "source_type": "government", "base_url": "https://api.grants.gov/v1/api", "authentication_type": "none", "trust_level": "official", "is_active": True},
        {"id": uuid.UUID("22222222-2222-4222-8222-222222222222"), "source_code": "simpler_grants", "source_name": "Simpler.Grants.gov", "source_type": "government", "base_url": "https://api.simpler.grants.gov", "authentication_type": "api_key", "trust_level": "official", "is_active": True},
        {"id": uuid.UUID("33333333-3333-4333-8333-333333333333"), "source_code": "eu_funding_tenders", "source_name": "European Commission Funding & Tenders", "source_type": "international_government", "base_url": "https://api.tech.ec.europa.eu/search-api/prod/rest/search", "authentication_type": "api_key", "trust_level": "official", "is_active": True},
    ])


def downgrade() -> None:
    op.drop_index("ix_external_import_audit_log_correlation_id", table_name="external_import_audit_log")
    op.drop_index("ix_external_import_audit_log_opportunity_id", table_name="external_import_audit_log")
    op.drop_table("external_import_audit_log")
    op.drop_index("ix_opportunity_sync_history_correlation_id", table_name="opportunity_sync_history")
    op.drop_index("ix_opportunity_sync_history_triggered_by", table_name="opportunity_sync_history")
    op.drop_index("ix_opportunity_sync_history_source_id", table_name="opportunity_sync_history")
    op.drop_index("ix_opportunity_sync_history_task_id", table_name="opportunity_sync_history")
    op.drop_table("opportunity_sync_history")
    op.drop_table("external_opportunity_verification_reviews")
    op.drop_index("ix_external_opportunity_verification_history_opportunity_id", table_name="external_opportunity_verification_history")
    op.drop_table("external_opportunity_verification_history")
    op.drop_index("ix_raw_external_opportunities_source_id", table_name="raw_external_opportunities")
    op.drop_index("ix_raw_external_processing_status", table_name="raw_external_opportunities")
    op.drop_table("raw_external_opportunities")
    op.drop_index("ix_external_verification_publication", table_name="external_opportunities")
    op.drop_index("ix_external_fingerprint", table_name="external_opportunities")
    op.drop_table("external_opportunities")
    op.drop_table("opportunity_sources")

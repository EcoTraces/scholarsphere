"""Create legal policy, acceptance, request, and compliance tables.

Revision ID: 20260901_19
Revises: 20260831_18
Create Date: 2026-09-01
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260901_19"
down_revision: str | None = "20260831_18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

policy_type = sa.Enum(
    "terms_and_conditions", "privacy_policy", "cookie_policy", "acceptable_use",
    "provider_agreement", "content_publishing", "verification_disclaimer",
    "funding_disclaimer", "copyright_policy", "data_processing_agreement",
    name="legalpolicytype", native_enum=False,
)
request_type = sa.Enum(
    "takedown", "complaint", "regulator", "court_order", "data_protection",
    name="legalrequesttype", native_enum=False,
)
request_status = sa.Enum(
    "submitted", "validated", "in_review", "actioned", "rejected", "closed",
    name="legalrequeststatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "legal_policies",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("type", policy_type, nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requires_acceptance", sa.Boolean(), nullable=False),
        sa.Column("material_change", sa.Boolean(), nullable=False),
        sa.Column("published_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("type", "version", name="uq_legal_policy_type_version"),
    )
    op.create_index("ix_legal_policies_type", "legal_policies", ["type"])
    op.create_table(
        "policy_acceptances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("policy_id", sa.String(255), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["policy_id"], ["legal_policies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "policy_id", name="uq_acceptance_user_policy"),
    )
    op.create_index("ix_policy_acceptances_user_id", "policy_acceptances", ["user_id"])
    op.create_table(
        "legal_requests",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("type", request_type, nullable=False),
        sa.Column("requester", sa.String(500), nullable=False),
        sa.Column("subject_entity_id", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_locations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", request_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("history", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "compliance_records",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("framework", sa.String(255), nullable=False),
        sa.Column("obligation", sa.Text(), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("review_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_locations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("compliance_records")
    op.drop_table("legal_requests")
    op.drop_index("ix_policy_acceptances_user_id", table_name="policy_acceptances")
    op.drop_table("policy_acceptances")
    op.drop_index("ix_legal_policies_type", table_name="legal_policies")
    op.drop_table("legal_policies")

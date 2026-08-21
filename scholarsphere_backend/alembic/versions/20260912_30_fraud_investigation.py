"""Create fraud cases and watchlist entries tables.

Revision ID: 20260912_30
Revises: 20260911_29
Create Date: 2026-09-12
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260912_30"
down_revision: str | None = "20260911_29"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

fraud_subject_type = sa.Enum(
    "opportunity", "provider", "source", "user", "domain", "payment",
    name="fraudsubjecttype", native_enum=False,
)
investigation_risk_level = sa.Enum(
    "low", "medium", "high", "critical",
    name="investigationrisklevel", native_enum=False,
)
fraud_case_status = sa.Enum(
    "opened", "assigned", "investigating", "additionalVerificationRequired",
    "restricted", "resolved", "rejected", "appealed", "closed",
    name="fraudcasestatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "fraud_cases",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("subject_type", fraud_subject_type, nullable=False),
        sa.Column("subject_id", sa.String(255), nullable=False),
        sa.Column("risk_overall", sa.Integer(), nullable=False),
        sa.Column("risk_level", investigation_risk_level, nullable=False),
        sa.Column("risk_provider", sa.Integer(), nullable=False),
        sa.Column("risk_source", sa.Integer(), nullable=False),
        sa.Column("risk_user_behaviour", sa.Integer(), nullable=False),
        sa.Column("risk_domain", sa.Integer(), nullable=False),
        sa.Column("risk_link", sa.Integer(), nullable=False),
        sa.Column("risk_payment", sa.Integer(), nullable=False),
        sa.Column("risk_impersonation", sa.Integer(), nullable=False),
        sa.Column("risk_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", fraud_case_status, nullable=False),
        sa.Column("assigned_investigator_id", sa.String(255), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "investigator_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("history", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("appeal_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fraud_cases_subject_type", "fraud_cases", ["subject_type"])
    op.create_index("ix_fraud_cases_subject_id", "fraud_cases", ["subject_id"])
    op.create_index("ix_fraud_cases_status", "fraud_cases", ["status"])

    op.create_table(
        "fraud_watchlist_entries",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("subject_type", fraud_subject_type, nullable=False),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fraud_watchlist_entries_subject_type", "fraud_watchlist_entries", ["subject_type"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_fraud_watchlist_entries_subject_type", table_name="fraud_watchlist_entries"
    )
    op.drop_table("fraud_watchlist_entries")
    op.drop_index("ix_fraud_cases_status", table_name="fraud_cases")
    op.drop_index("ix_fraud_cases_subject_id", table_name="fraud_cases")
    op.drop_index("ix_fraud_cases_subject_type", table_name="fraud_cases")
    op.drop_table("fraud_cases")

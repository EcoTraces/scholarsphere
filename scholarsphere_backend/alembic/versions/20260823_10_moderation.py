"""Create moderation case, history, and warning tables.

Revision ID: 20260823_10
Revises: 20260822_09
Create Date: 2026-08-23
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260823_10"
down_revision: str | None = "20260822_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

reported_entity_type = sa.Enum(
    "opportunity", "provider", "user",
    name="reportedentitytype", native_enum=False,
)
moderation_report_type = sa.Enum(
    "scam", "incorrect_deadline", "broken_link", "duplicate_listing",
    "misleading_content", "inappropriate_content", "outdated_content", "harmful_content",
    name="moderationreporttype", native_enum=False,
)
moderation_status = sa.Enum(
    "submitted", "under_review", "evidence_required", "escalated", "resolved",
    "rejected", "content_corrected", "content_removed", "provider_suspended", "closed",
    name="moderationstatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "moderation_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_id", sa.String(255), nullable=False),
        sa.Column("entity_type", reported_entity_type, nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column("report_type", moderation_report_type, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", moderation_status, nullable=False),
        sa.Column("assigned_moderator_id", sa.String(255)),
        sa.Column("moderation_notes", sa.Text()),
        sa.Column("temporarily_hidden", sa.Boolean(), nullable=False),
        sa.Column("appeal_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moderation_cases_reporter_id", "moderation_cases", ["reporter_id"])
    op.create_index("ix_moderation_cases_entity_id", "moderation_cases", ["entity_id"])
    op.create_table(
        "moderation_case_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("status", moderation_status, nullable=False),
        sa.Column("actor_id", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["moderation_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moderation_case_history_case_id", "moderation_case_history", ["case_id"])
    op.create_table(
        "moderation_warnings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", reported_entity_type, nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("issued_by", sa.String(255), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["moderation_cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moderation_warnings_entity_id", "moderation_warnings", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_moderation_warnings_entity_id", table_name="moderation_warnings")
    op.drop_table("moderation_warnings")
    op.drop_index("ix_moderation_case_history_case_id", table_name="moderation_case_history")
    op.drop_table("moderation_case_history")
    op.drop_index("ix_moderation_cases_entity_id", table_name="moderation_cases")
    op.drop_index("ix_moderation_cases_reporter_id", table_name="moderation_cases")
    op.drop_table("moderation_cases")

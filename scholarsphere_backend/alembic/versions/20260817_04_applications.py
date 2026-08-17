"""Create applications table.

Revision ID: 20260817_04
Revises: 20260731_03
Create Date: 2026-08-17
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260817_04"
down_revision: str | None = "20260731_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

application_stage = sa.Enum(
    "interested", "saved", "preparing_documents", "application_started",
    "application_submitted", "interview_stage", "waiting_for_decision",
    "accepted", "rejected", "withdrawn",
    name="applicationstage", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_title", sa.String(1000), nullable=False),
        sa.Column("provider_name", sa.String(512), nullable=False),
        sa.Column("deadline", sa.Date()),
        sa.Column("stage", application_stage, nullable=False),
        sa.Column("application_date", sa.Date()),
        sa.Column("application_reference_number", sa.String(255)),
        sa.Column("missing_documents", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("interview_date", sa.Date()),
        sa.Column("personal_notes", sa.Text(), nullable=False),
        sa.Column("result_date", sa.Date()),
        sa.Column("scholarship_value", sa.Float()),
        sa.Column("follow_up_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["external_opportunities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "opportunity_id", name="uq_application_user_opportunity"),
    )
    op.create_index("ix_application_user_id", "applications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_application_user_id", table_name="applications")
    op.drop_table("applications")

"""Create personalization controls, recommendation history, and feedback tables.

Revision ID: 20260903_21
Revises: 20260902_20
Create Date: 2026-09-03
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260903_21"
down_revision: str | None = "20260902_20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

feedback_type = sa.Enum(
    "helpful",
    "notRelevant",
    "inappropriate",
    "dismissed",
    name="recommendationfeedbacktype",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "personalization_controls",
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("behavioural_recommendations_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "preferred_countries", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "opportunity_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "hidden_opportunity_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "recommendation_history_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("opportunity_id", sa.String(255), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("host_country", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recommendation_history_entries_user_id",
        "recommendation_history_entries",
        ["user_id"],
    )
    op.create_table(
        "recommendation_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("opportunity_id", sa.String(255), nullable=False),
        sa.Column("type", feedback_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recommendation_feedback_user_id",
        "recommendation_feedback",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_recommendation_feedback_user_id", table_name="recommendation_feedback")
    op.drop_table("recommendation_feedback")
    op.drop_index(
        "ix_recommendation_history_entries_user_id",
        table_name="recommendation_history_entries",
    )
    op.drop_table("recommendation_history_entries")
    op.drop_table("personalization_controls")

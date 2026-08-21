"""Create quality reports and deployment records tables.

Revision ID: 20260909_27
Revises: 20260908_26
Create Date: 2026-09-09
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260909_27"
down_revision: str | None = "20260908_26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

deployment_environment = sa.Enum(
    "development", "testing", "staging", "production",
    name="deploymentenvironment", native_enum=False,
)
deployment_strategy = sa.Enum(
    "standard", "blueGreen", "canary", name="deploymentstrategy", native_enum=False
)
deployment_status = sa.Enum(
    "draft", "awaitingApproval", "approved", "deploying", "completed", "failed",
    "rolledBack", name="deploymentstatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "quality_reports",
        sa.Column("release_version", sa.String(255), nullable=False),
        sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("coverage_percent", sa.Float(), nullable=False),
        sa.Column(
            "mandatory_eligibility_coverage_percent", sa.Float(), nullable=False
        ),
        sa.Column(
            "security_findings", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("release_version"),
    )
    op.create_table(
        "deployment_records",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("artifact_version", sa.String(255), nullable=False),
        sa.Column("artifact_commit_sha", sa.String(255), nullable=False),
        sa.Column("artifact_image_reference", sa.String(1000), nullable=False),
        sa.Column("artifact_release_notes", sa.Text(), nullable=False),
        sa.Column("artifact_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "artifact_migration_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("environment", deployment_environment, nullable=False),
        sa.Column("strategy", deployment_strategy, nullable=False),
        sa.Column("status", deployment_status, nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_deployment_id", sa.String(255), nullable=True),
        sa.Column("history", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("deployment_records")
    op.drop_table("quality_reports")

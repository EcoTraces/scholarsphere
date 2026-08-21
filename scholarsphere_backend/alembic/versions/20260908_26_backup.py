"""Create backup policy, records, and recovery test tables.

Revision ID: 20260908_26
Revises: 20260907_25
Create Date: 2026-09-08
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260908_26"
down_revision: str | None = "20260907_25"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

backup_type = sa.Enum(
    "fullDatabase",
    "incremental",
    "transactionLog",
    "fileStorage",
    name="backuptype",
    native_enum=False,
)
backup_status = sa.Enum(
    "scheduled",
    "running",
    "completed",
    "failed",
    "verified",
    "expired",
    name="backupstatus",
    native_enum=False,
)
recovery_status = sa.Enum(
    "requested",
    "approved",
    "running",
    "completed",
    "failed",
    name="recoverystatus",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "backup_policies",
        sa.Column("id", sa.String(16), nullable=False),
        sa.Column("full_backup_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("transaction_log_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("retention_seconds", sa.Integer(), nullable=False),
        sa.Column("monthly_restore_test", sa.Boolean(), nullable=False),
        sa.Column("encryption_required", sa.Boolean(), nullable=False),
        sa.Column("separate_region_required", sa.Boolean(), nullable=False),
        sa.Column("recovery_point_objective_seconds", sa.Integer(), nullable=False),
        sa.Column("recovery_time_objective_seconds", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "backup_records",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("type", backup_type, nullable=False),
        sa.Column("status", backup_status, nullable=False),
        sa.Column("storage_location", sa.String(1000), nullable=False),
        sa.Column("region", sa.String(255), nullable=False),
        sa.Column("encrypted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(255), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "recovery_tests",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("backup_id", sa.String(255), nullable=False),
        sa.Column("status", recovery_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("integrity_valid", sa.Boolean(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["backup_id"], ["backup_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("recovery_tests")
    op.drop_table("backup_records")
    op.drop_table("backup_policies")

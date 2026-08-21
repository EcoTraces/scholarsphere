"""Create retention rules, lifecycle records, and legal holds tables.

Revision ID: 20260910_28
Revises: 20260909_27
Create Date: 2026-09-10
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260910_28"
down_revision: str | None = "20260909_27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

retained_entity_type = sa.Enum(
    "opportunity", "userAccount", "document", "notification", "auditLog",
    "supportTicket", "providerRecord", name="retainedentitytype", native_enum=False,
)
lifecycle_status = sa.Enum(
    "active", "softDeleted", "archived", "pendingPermanentDeletion",
    "permanentlyDeleted", "restored", name="lifecyclestatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "retention_rules",
        sa.Column("entity_type", retained_entity_type, nullable=False),
        sa.Column("active_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("archive_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("delete_from_backups_after_seconds", sa.Integer(), nullable=False),
        sa.Column("archive_expired_records", sa.Boolean(), nullable=False),
        sa.Column("retain_rejected_for_fraud_prevention", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("entity_type"),
    )
    op.create_table(
        "lifecycle_records",
        sa.Column("entity_type", retained_entity_type, nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column("owner_id", sa.String(255), nullable=True),
        sa.Column("status", lifecycle_status, nullable=False),
        sa.Column("contains_personal_data", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("backup_deletion_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deletion_verification", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("entity_type", "entity_id"),
    )
    op.create_table(
        "legal_holds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", retained_entity_type, nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("placed_by", sa.String(255), nullable=False),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_legal_holds_entity", "legal_holds", ["entity_type", "entity_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_legal_holds_entity", table_name="legal_holds")
    op.drop_table("legal_holds")
    op.drop_table("lifecycle_records")
    op.drop_table("retention_rules")

"""Extend external audit records for governance and source events.

Revision ID: 20260731_03
Revises: 20260731_02
Create Date: 2026-07-31
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260731_03"
down_revision: str | None = "20260731_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "external_import_audit_log", "opportunity_id", nullable=True
    )
    op.add_column(
        "external_import_audit_log", sa.Column("actor_id", sa.String(255))
    )
    op.create_index(
        "ix_external_import_audit_log_actor_id",
        "external_import_audit_log",
        ["actor_id"],
    )
    op.add_column(
        "external_import_audit_log", sa.Column("actor_role", sa.String(64))
    )
    op.add_column(
        "external_import_audit_log", sa.Column("entity_type", sa.String(128))
    )
    op.add_column(
        "external_import_audit_log", sa.Column("entity_id", sa.String(512))
    )
    op.execute(
        """
        UPDATE external_import_audit_log
        SET entity_type = 'external_opportunity',
            entity_id = opportunity_id::text
        WHERE entity_type IS NULL
        """
    )
    op.alter_column(
        "external_import_audit_log", "entity_type", nullable=False
    )
    op.alter_column(
        "external_import_audit_log", "entity_id", nullable=False
    )
    op.create_index(
        "ix_external_import_audit_log_entity_id",
        "external_import_audit_log",
        ["entity_id"],
    )
    op.add_column(
        "external_import_audit_log",
        sa.Column("result", sa.String(32), server_default="success", nullable=False),
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM external_import_audit_log WHERE opportunity_id IS NULL"
    )
    op.drop_column("external_import_audit_log", "result")
    op.drop_index(
        "ix_external_import_audit_log_entity_id",
        table_name="external_import_audit_log",
    )
    op.drop_column("external_import_audit_log", "entity_id")
    op.drop_column("external_import_audit_log", "entity_type")
    op.drop_column("external_import_audit_log", "actor_role")
    op.drop_index(
        "ix_external_import_audit_log_actor_id",
        table_name="external_import_audit_log",
    )
    op.drop_column("external_import_audit_log", "actor_id")
    op.alter_column(
        "external_import_audit_log", "opportunity_id", nullable=False
    )

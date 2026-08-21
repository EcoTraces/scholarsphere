"""Create audit records, chain state, and retention policy tables.

Revision ID: 20260906_24
Revises: 20260905_23
Create Date: 2026-09-06
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260906_24"
down_revision: str | None = "20260905_23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

audit_action = sa.Enum(
    "login",
    "logout",
    "failedLogin",
    "profileChanged",
    "roleChanged",
    "permissionChanged",
    "opportunityChanged",
    "verificationDecision",
    "documentAccessed",
    "providerAction",
    "administrativeAction",
    "securityEvent",
    "dataExported",
    "accountDeleted",
    "apiRequest",
    name="auditaction",
    native_enum=False,
)

audit_result = sa.Enum(
    "success", "failure", "denied", name="auditresult", native_enum=False
)


def upgrade() -> None:
    op.create_table(
        "audit_records",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("actor_id", sa.String(255), nullable=False),
        sa.Column("actor_role", sa.String(64), nullable=False),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("entity_type", sa.String(255), nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column("previous_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=False),
        sa.Column("device_information", sa.String(500), nullable=False),
        sa.Column("location_information", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", audit_result, nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(255), nullable=False),
        sa.Column("integrity_hash", sa.String(16), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_records_actor_id", "audit_records", ["actor_id"])
    op.create_index("ix_audit_records_action", "audit_records", ["action"])
    op.create_index("ix_audit_records_entity_type", "audit_records", ["entity_type"])
    op.create_index("ix_audit_records_entity_id", "audit_records", ["entity_id"])
    op.create_index("ix_audit_records_timestamp", "audit_records", ["timestamp"])

    op.create_table(
        "audit_chain_state",
        sa.Column("id", sa.String(16), nullable=False),
        sa.Column("anchor", sa.String(16), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_retention_policy",
        sa.Column("id", sa.String(16), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("audit_retention_policy")
    op.drop_table("audit_chain_state")
    op.drop_index("ix_audit_records_timestamp", table_name="audit_records")
    op.drop_index("ix_audit_records_entity_id", table_name="audit_records")
    op.drop_index("ix_audit_records_entity_type", table_name="audit_records")
    op.drop_index("ix_audit_records_action", table_name="audit_records")
    op.drop_index("ix_audit_records_actor_id", table_name="audit_records")
    op.drop_table("audit_records")

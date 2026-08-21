"""Create login history, security sessions, and security alerts tables.

Revision ID: 20260905_23
Revises: 20260904_22
Create Date: 2026-09-05
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260905_23"
down_revision: str | None = "20260904_22"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

login_outcome = sa.Enum(
    "success",
    "invalidCredentials",
    "locked",
    "blockedIp",
    "mfaFailed",
    name="loginoutcome",
    native_enum=False,
)

security_alert_type = sa.Enum(
    "newDevice",
    "suspiciousLogin",
    "repeatedFailures",
    "accountLocked",
    "sessionRevoked",
    "privilegedAction",
    name="securityalerttype",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "login_history_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome", login_outcome, nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("browser", sa.String(255), nullable=False),
        sa.Column("operating_system", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=False),
        sa.Column("suspicious", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_history_entries_email", "login_history_entries", ["email"])
    op.create_index("ix_login_history_entries_user_id", "login_history_entries", ["user_id"])

    op.create_table(
        "security_sessions",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("browser", sa.String(255), nullable=False),
        sa.Column("operating_system", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("strong_authentication", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_sessions_user_id", "security_sessions", ["user_id"])

    op.create_table(
        "security_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("type", security_alert_type, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_alerts_user_id", "security_alerts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_security_alerts_user_id", table_name="security_alerts")
    op.drop_table("security_alerts")
    op.drop_index("ix_security_sessions_user_id", table_name="security_sessions")
    op.drop_table("security_sessions")
    op.drop_index("ix_login_history_entries_user_id", table_name="login_history_entries")
    op.drop_index("ix_login_history_entries_email", table_name="login_history_entries")
    op.drop_table("login_history_entries")

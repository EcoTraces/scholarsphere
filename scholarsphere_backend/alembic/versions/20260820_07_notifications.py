"""Create notification preferences, templates, and instance tables.

Revision ID: 20260820_07
Revises: 20260818_06
Create Date: 2026-08-20
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260820_07"
down_revision: str | None = "20260818_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

notification_frequency = sa.Enum(
    "immediate", "daily_digest", "weekly_digest", "disabled",
    name="notificationfrequency", native_enum=False,
)
notification_event_type = sa.Enum(
    "matching_opportunity", "deadline_reminder", "requirements_changed",
    "deadline_changed", "opportunity_verified", "saved_opportunity_expired",
    "application_progress", "provider_announcement", "emergency_system_message",
    name="notificationeventtype", native_enum=False,
)
notification_delivery_status = sa.Enum(
    "scheduled", "queued", "processing", "sent", "delivered", "read",
    "failed", "retrying", "cancelled", "expired",
    name="notificationdeliverystatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "notification_templates",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("type", notification_event_type, nullable=False),
        sa.Column("title_template", sa.String(500), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("channels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("channels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("frequency", notification_frequency, nullable=False),
        sa.Column("reminder_days", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("matching_opportunities", sa.Boolean(), nullable=False),
        sa.Column("opportunity_changes", sa.Boolean(), nullable=False),
        sa.Column("verification_updates", sa.Boolean(), nullable=False),
        sa.Column("saved_opportunity_expiry", sa.Boolean(), nullable=False),
        sa.Column("quiet_hours_start", sa.Integer()),
        sa.Column("quiet_hours_end", sa.Integer()),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("daily_limit", sa.Integer(), nullable=False),
        sa.Column("group_notifications", sa.Boolean(), nullable=False),
        sa.Column("unsubscribed_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "scholarsphere_notifications",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("type", notification_event_type, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("channels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("template_id", sa.String(255)),
        sa.Column("related_entity_type", sa.String(64)),
        sa.Column("related_entity_id", sa.String(255)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("status", notification_delivery_status, nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("group_key", sa.String(255)),
        sa.ForeignKeyConstraint(["opportunity_id"], ["external_opportunities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["template_id"], ["notification_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "scholarsphere_notifications", ["user_id"])
    op.create_index(
        "ix_notifications_user_status_scheduled", "scholarsphere_notifications",
        ["user_id", "status", "scheduled_for"],
    )
    op.create_index(
        "ix_notifications_status_scheduled", "scholarsphere_notifications",
        ["status", "scheduled_for"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_status_scheduled", table_name="scholarsphere_notifications")
    op.drop_index("ix_notifications_user_status_scheduled", table_name="scholarsphere_notifications")
    op.drop_index("ix_notifications_user_id", table_name="scholarsphere_notifications")
    op.drop_table("scholarsphere_notifications")
    op.drop_table("notification_preferences")
    op.drop_table("notification_templates")

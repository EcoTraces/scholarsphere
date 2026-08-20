import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.external_opportunity import JSONType


class NotificationChannel(str, enum.Enum):
    in_app = "in_app"
    email = "email"
    push = "push"
    sms = "sms"
    whatsapp = "whatsapp"


class NotificationFrequency(str, enum.Enum):
    immediate = "immediate"
    daily_digest = "daily_digest"
    weekly_digest = "weekly_digest"
    disabled = "disabled"


class NotificationEventType(str, enum.Enum):
    matching_opportunity = "matching_opportunity"
    deadline_reminder = "deadline_reminder"
    requirements_changed = "requirements_changed"
    deadline_changed = "deadline_changed"
    opportunity_verified = "opportunity_verified"
    saved_opportunity_expired = "saved_opportunity_expired"
    application_progress = "application_progress"
    provider_announcement = "provider_announcement"
    emergency_system_message = "emergency_system_message"


class NotificationDeliveryStatus(str, enum.Enum):
    scheduled = "scheduled"
    queued = "queued"
    processing = "processing"
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"
    retrying = "retrying"
    cancelled = "cancelled"
    expired = "expired"


class NotificationPreferences(Base):
    """One row per user - a settings table, not an event table, so the

    Firebase uid is the primary key itself rather than a separate uuid.
    """

    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    channels: Mapped[list[str]] = mapped_column(
        JSONType,
        default=lambda: [
            NotificationChannel.in_app.value,
            NotificationChannel.email.value,
            NotificationChannel.push.value,
        ],
        nullable=False,
    )
    frequency: Mapped[NotificationFrequency] = mapped_column(
        Enum(NotificationFrequency, native_enum=False),
        default=NotificationFrequency.immediate,
        nullable=False,
    )
    reminder_days: Mapped[list[int]] = mapped_column(
        JSONType, default=lambda: [30, 14, 7, 3, 1], nullable=False
    )
    matching_opportunities: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    opportunity_changes: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verification_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    saved_opportunity_expiry: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quiet_hours_start: Mapped[int | None] = mapped_column(Integer)
    quiet_hours_end: Mapped[int | None] = mapped_column(Integer)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    daily_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    group_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    unsubscribed_types: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class NotificationTemplate(Base):
    """Admin-managed catalog, upserted by a client-chosen id (not server-generated)."""

    __tablename__ = "notification_templates"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[NotificationEventType] = mapped_column(
        Enum(NotificationEventType, native_enum=False), nullable=False
    )
    title_template: Mapped[str] = mapped_column(String(500), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    channels: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ScholarSphereNotification(Base):
    """A scheduled/sent notification instance.

    ``id`` is a plain string, not a UUID: deadline reminders use a
    deterministic id (``{opportunity_id}-deadline-{days}``) so re-scheduling
    is idempotent by primary-key collision, matching the Dart demo
    repository's id-equality dedup. Event/admin-created records use a random
    hex id instead.
    """

    __tablename__ = "scholarsphere_notifications"
    __table_args__ = (
        Index("ix_notifications_user_status_scheduled", "user_id", "status", "scheduled_for"),
        Index("ix_notifications_status_scheduled", "status", "scheduled_for"),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[NotificationEventType] = mapped_column(
        Enum(NotificationEventType, native_enum=False), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    channels: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    opportunity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("external_opportunities.id", ondelete="RESTRICT")
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    template_id: Mapped[str | None] = mapped_column(
        ForeignKey("notification_templates.id", ondelete="SET NULL")
    )
    related_entity_type: Mapped[str | None] = mapped_column(String(64))
    related_entity_id: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[NotificationDeliveryStatus] = mapped_column(
        Enum(NotificationDeliveryStatus, native_enum=False),
        default=NotificationDeliveryStatus.scheduled,
        nullable=False,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    group_key: Mapped[str | None] = mapped_column(String(255))

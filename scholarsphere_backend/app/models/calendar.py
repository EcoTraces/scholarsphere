import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.external_opportunity import JSONType


class CalendarEventType(str, enum.Enum):
    opportunity_deadline = "opportunity_deadline"
    application = "application"
    interview = "interview"
    document_submission = "document_submission"
    follow_up = "follow_up"


class DeadlineState(str, enum.Enum):
    upcoming = "upcoming"
    closing_soon = "closing_soon"
    today = "today"
    passed = "passed"
    extended = "extended"
    changed = "changed"
    unconfirmed = "unconfirmed"
    rolling_deadline = "rolling_deadline"


class CalendarProvider(str, enum.Enum):
    google = "google"
    outlook = "outlook"
    ics = "ics"


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    type: Mapped[CalendarEventType] = mapped_column(
        Enum(CalendarEventType, native_enum=False), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    reminder_minutes: Mapped[list[int]] = mapped_column(JSONType, default=list, nullable=False)
    deadline_state: Mapped[DeadlineState] = mapped_column(
        Enum(DeadlineState, native_enum=False), nullable=False
    )
    related_entity_id: Mapped[str | None] = mapped_column(String(255))
    previous_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recurrence: Mapped[dict | None] = mapped_column(JSONType)
    external_calendar_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

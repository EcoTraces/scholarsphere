from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.notification import (
    NotificationChannel,
    NotificationDeliveryStatus,
    NotificationEventType,
    NotificationFrequency,
)

_CHANNEL_WIRE_TO_MODEL: dict[str, NotificationChannel] = {
    "inApp": NotificationChannel.in_app,
    "email": NotificationChannel.email,
    "push": NotificationChannel.push,
    "sms": NotificationChannel.sms,
    "whatsapp": NotificationChannel.whatsapp,
}
_CHANNEL_MODEL_TO_WIRE: dict[str, str] = {
    value.value: key for key, value in _CHANNEL_WIRE_TO_MODEL.items()
}

_FREQUENCY_WIRE_TO_MODEL: dict[str, NotificationFrequency] = {
    "immediate": NotificationFrequency.immediate,
    "dailyDigest": NotificationFrequency.daily_digest,
    "weeklyDigest": NotificationFrequency.weekly_digest,
    "disabled": NotificationFrequency.disabled,
}
_FREQUENCY_MODEL_TO_WIRE: dict[NotificationFrequency, str] = {
    value: key for key, value in _FREQUENCY_WIRE_TO_MODEL.items()
}

_EVENT_TYPE_WIRE_TO_MODEL: dict[str, NotificationEventType] = {
    "matchingOpportunity": NotificationEventType.matching_opportunity,
    "deadlineReminder": NotificationEventType.deadline_reminder,
    "requirementsChanged": NotificationEventType.requirements_changed,
    "deadlineChanged": NotificationEventType.deadline_changed,
    "opportunityVerified": NotificationEventType.opportunity_verified,
    "savedOpportunityExpired": NotificationEventType.saved_opportunity_expired,
    "applicationProgress": NotificationEventType.application_progress,
    "providerAnnouncement": NotificationEventType.provider_announcement,
    "emergencySystemMessage": NotificationEventType.emergency_system_message,
}
_EVENT_TYPE_MODEL_TO_WIRE: dict[str, str] = {
    value.value: key for key, value in _EVENT_TYPE_WIRE_TO_MODEL.items()
}

_STATUS_WIRE_TO_MODEL: dict[str, NotificationDeliveryStatus] = {
    "scheduled": NotificationDeliveryStatus.scheduled,
    "queued": NotificationDeliveryStatus.queued,
    "processing": NotificationDeliveryStatus.processing,
    "sent": NotificationDeliveryStatus.sent,
    "delivered": NotificationDeliveryStatus.delivered,
    "read": NotificationDeliveryStatus.read,
    "failed": NotificationDeliveryStatus.failed,
    "retrying": NotificationDeliveryStatus.retrying,
    "cancelled": NotificationDeliveryStatus.cancelled,
    "expired": NotificationDeliveryStatus.expired,
}
_STATUS_MODEL_TO_WIRE: dict[NotificationDeliveryStatus, str] = {
    value: key for key, value in _STATUS_WIRE_TO_MODEL.items()
}


def channel_from_wire(value: str) -> str:
    try:
        return _CHANNEL_WIRE_TO_MODEL[value].value
    except KeyError as error:
        raise ValueError(f"Unknown notification channel: {value!r}") from error


def channels_from_wire(values: list[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        model_value = channel_from_wire(value)
        if model_value not in seen:
            seen.append(model_value)
    return seen


def channels_to_wire(values: list[str]) -> list[str]:
    return [_CHANNEL_MODEL_TO_WIRE.get(value, value) for value in values]


def frequency_from_wire(value: str) -> NotificationFrequency:
    try:
        return _FREQUENCY_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown notification frequency: {value!r}") from error


def event_type_from_wire(value: str) -> str:
    try:
        return _EVENT_TYPE_WIRE_TO_MODEL[value].value
    except KeyError as error:
        raise ValueError(f"Unknown notification event type: {value!r}") from error


def event_types_from_wire(values: list[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        model_value = event_type_from_wire(value)
        if model_value not in seen:
            seen.append(model_value)
    return seen


def event_types_to_wire(values: list[str]) -> list[str]:
    return [_EVENT_TYPE_MODEL_TO_WIRE.get(value, value) for value in values]


class NotificationPreferencesUpdate(BaseModel):
    """Full-replace upsert - matches the Dart settings screen's whole-form save."""

    channels: list[str] = Field(default_factory=lambda: ["inApp", "email", "push"])
    frequency: str = "immediate"
    reminder_days: list[int] = Field(default_factory=lambda: [30, 14, 7, 3, 1])
    matching_opportunities: bool = True
    opportunity_changes: bool = True
    verification_updates: bool = True
    saved_opportunity_expiry: bool = True
    quiet_hours_start: int | None = Field(default=None, ge=0, le=23)
    quiet_hours_end: int | None = Field(default=None, ge=0, le=23)
    timezone: str = Field(default="UTC", max_length=64)
    daily_limit: int = Field(default=10, ge=0, le=1000)
    group_notifications: bool = True
    unsubscribed_types: list[str] = Field(default_factory=list)

    @field_validator("channels")
    @classmethod
    def _validate_channels(cls, value: list[str]) -> list[str]:
        return channels_from_wire(value)

    @field_validator("frequency")
    @classmethod
    def _validate_frequency(cls, value: str) -> str:
        frequency_from_wire(value)
        return value

    @field_validator("unsubscribed_types")
    @classmethod
    def _validate_unsubscribed(cls, value: list[str]) -> list[str]:
        return event_types_from_wire(value)

    @field_validator("reminder_days")
    @classmethod
    def _validate_reminder_days(cls, value: list[int]) -> list[int]:
        for day in value:
            if day < 0 or day > 3650:
                raise ValueError("Reminder days must be between 0 and 3650.")
        return sorted(set(value), reverse=True)


class NotificationPreferencesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    channels: list[str]
    frequency: NotificationFrequency
    reminder_days: list[int]
    matching_opportunities: bool
    opportunity_changes: bool
    verification_updates: bool
    saved_opportunity_expiry: bool
    quiet_hours_start: int | None
    quiet_hours_end: int | None
    timezone: str
    daily_limit: int
    group_notifications: bool
    unsubscribed_types: list[str]

    @field_serializer("channels")
    def _serialize_channels(self, value: list[str], _info: Any) -> list[str]:
        return channels_to_wire(value)

    @field_serializer("unsubscribed_types")
    def _serialize_unsubscribed(self, value: list[str], _info: Any) -> list[str]:
        return event_types_to_wire(value)

    @field_serializer("frequency")
    def _serialize_frequency(self, value: NotificationFrequency, _info: Any) -> str:
        return _FREQUENCY_MODEL_TO_WIRE[value]


class ScheduleDeadlineRemindersRequest(BaseModel):
    opportunity_ids: list[UUID] = Field(max_length=200)


class RecordOpportunityEventRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)
    opportunity_id: UUID
    type: str
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        event_type_from_wire(value)
        return value


class SaveTemplateRequest(BaseModel):
    type: str
    title_template: str = Field(min_length=1, max_length=500)
    body_template: str = Field(min_length=1, max_length=10000)
    channels: list[str] = Field(default_factory=list)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        event_type_from_wire(value)
        return value

    @field_validator("channels")
    @classmethod
    def _validate_channels(cls, value: list[str]) -> list[str]:
        return channels_from_wire(value)


class RetryFailedRequest(BaseModel):
    maximum_retries: int = Field(default=3, ge=0, le=100)


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    type: NotificationEventType
    title: str
    message: str
    channels: list[str]
    scheduled_for: datetime
    created_at: datetime
    opportunity_id: UUID | None
    read_at: datetime | None
    template_id: str | None
    related_entity_type: str | None
    related_entity_id: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    status: NotificationDeliveryStatus
    retry_count: int
    failure_reason: str | None
    timezone: str
    group_key: str | None

    @field_serializer("type")
    def _serialize_type(self, value: NotificationEventType, _info: Any) -> str:
        return _EVENT_TYPE_MODEL_TO_WIRE[value.value]

    @field_serializer("status")
    def _serialize_status(self, value: NotificationDeliveryStatus, _info: Any) -> str:
        return _STATUS_MODEL_TO_WIRE[value]

    @field_serializer("channels")
    def _serialize_channels(self, value: list[str], _info: Any) -> list[str]:
        return channels_to_wire(value)


class NotificationPage(BaseModel):
    items: list[NotificationRead]
    total: int
    page: int
    page_size: int


class NotificationDeliveryAnalytics(BaseModel):
    total: int
    delivered: int
    read: int
    failed: int
    retried: int

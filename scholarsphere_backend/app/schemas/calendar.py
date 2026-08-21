from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.calendar import CalendarEventType, CalendarProvider, DeadlineState

_TYPE_WIRE_TO_MODEL: dict[str, CalendarEventType] = {
    "opportunityDeadline": CalendarEventType.opportunity_deadline,
    "application": CalendarEventType.application,
    "interview": CalendarEventType.interview,
    "documentSubmission": CalendarEventType.document_submission,
    "followUp": CalendarEventType.follow_up,
}
_TYPE_MODEL_TO_WIRE: dict[CalendarEventType, str] = {
    value: key for key, value in _TYPE_WIRE_TO_MODEL.items()
}

_STATE_WIRE_TO_MODEL: dict[str, DeadlineState] = {
    "upcoming": DeadlineState.upcoming,
    "closingSoon": DeadlineState.closing_soon,
    "today": DeadlineState.today,
    "passed": DeadlineState.passed,
    "extended": DeadlineState.extended,
    "changed": DeadlineState.changed,
    "unconfirmed": DeadlineState.unconfirmed,
    "rollingDeadline": DeadlineState.rolling_deadline,
}
_STATE_MODEL_TO_WIRE: dict[DeadlineState, str] = {
    value: key for key, value in _STATE_WIRE_TO_MODEL.items()
}

_PROVIDER_WIRE_TO_MODEL: dict[str, CalendarProvider] = {
    "google": CalendarProvider.google,
    "outlook": CalendarProvider.outlook,
    "ics": CalendarProvider.ics,
}


def event_type_from_wire(value: str) -> CalendarEventType:
    try:
        return _TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown calendar event type: {value!r}") from error


def event_type_to_wire(value: CalendarEventType) -> str:
    return _TYPE_MODEL_TO_WIRE[value]


def deadline_state_from_wire(value: str) -> DeadlineState:
    try:
        return _STATE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown deadline state: {value!r}") from error


def deadline_state_to_wire(value: DeadlineState) -> str:
    return _STATE_MODEL_TO_WIRE[value]


def provider_from_wire(value: str) -> CalendarProvider:
    try:
        return _PROVIDER_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown calendar provider: {value!r}") from error


# "Sticky" states that a save() should preserve instead of recomputing from
# the current date, matching DemoCalendarRepository._currentState.
_STICKY_STATES = frozenset(
    {DeadlineState.extended, DeadlineState.changed, DeadlineState.unconfirmed, DeadlineState.rolling_deadline}
)


def is_sticky_state(value: DeadlineState) -> bool:
    return value in _STICKY_STATES


class RecurrenceRuleInput(BaseModel):
    frequency: str = Field(min_length=1, max_length=32)
    interval: int = Field(ge=1)
    count: int | None = Field(default=None, ge=1)
    until: datetime | None = None


class SaveCalendarEventRequest(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=5000)
    type: str
    starts_at: datetime
    ends_at: datetime
    timezone: str = Field(default="UTC", max_length=64)
    reminder_minutes: list[int] = Field(default_factory=list, max_length=20)
    deadline_state: str = "upcoming"
    related_entity_id: str | None = Field(default=None, max_length=255)
    recurrence: RecurrenceRuleInput | None = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        event_type_from_wire(value)
        return value

    @field_validator("deadline_state")
    @classmethod
    def _validate_state(cls, value: str) -> str:
        deadline_state_from_wire(value)
        return value


class UpdateDeadlineRequest(BaseModel):
    new_deadline: datetime


class MarkSynchronizedRequest(BaseModel):
    provider: str
    external_id: str = Field(min_length=1, max_length=255)

    @field_validator("provider")
    @classmethod
    def _validate_provider(cls, value: str) -> str:
        provider_from_wire(value)
        return value


class IcsExportRead(BaseModel):
    content: str


class CalendarEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    description: str
    type: CalendarEventType
    starts_at: datetime
    ends_at: datetime
    timezone: str
    reminder_minutes: list[int]
    deadline_state: DeadlineState
    related_entity_id: str | None
    previous_starts_at: datetime | None
    recurrence: dict[str, Any] | None
    external_calendar_id: str | None
    created_at: datetime

    @field_serializer("type")
    def _serialize_type(self, value: CalendarEventType, _info: Any) -> str:
        return event_type_to_wire(value)

    @field_serializer("deadline_state")
    def _serialize_state(self, value: DeadlineState, _info: Any) -> str:
        return deadline_state_to_wire(value)


class CalendarConflictRead(BaseModel):
    first_event_id: str
    second_event_id: str
    overlap_seconds: int

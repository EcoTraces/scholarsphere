from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.application import ApplicationStage

_STAGE_WIRE_TO_MODEL: dict[str, ApplicationStage] = {
    "interested": ApplicationStage.interested,
    "saved": ApplicationStage.saved,
    "preparingDocuments": ApplicationStage.preparing_documents,
    "applicationStarted": ApplicationStage.application_started,
    "applicationSubmitted": ApplicationStage.application_submitted,
    "interviewStage": ApplicationStage.interview_stage,
    "waitingForDecision": ApplicationStage.waiting_for_decision,
    "accepted": ApplicationStage.accepted,
    "rejected": ApplicationStage.rejected,
    "withdrawn": ApplicationStage.withdrawn,
}
_STAGE_MODEL_TO_WIRE: dict[ApplicationStage, str] = {
    value: key for key, value in _STAGE_WIRE_TO_MODEL.items()
}


def stage_from_wire(value: str) -> ApplicationStage:
    try:
        return _STAGE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown application stage: {value!r}") from error


class ApplicationCreate(BaseModel):
    opportunity_id: UUID


class ApplicationUpdate(BaseModel):
    """Full replace of every mutable field - matches the Flutter edit screen,

    which always resubmits the entire form (``copyWith`` with every field
    spelled out) rather than sending a sparse patch.
    """

    stage: str
    application_date: date | None = None
    application_reference_number: str | None = Field(default=None, max_length=255)
    missing_documents: list[str] = Field(default_factory=list, max_length=50)
    interview_date: date | None = None
    personal_notes: str = Field(default="", max_length=5000)
    result_date: date | None = None
    scholarship_value: float | None = Field(default=None, ge=0)
    follow_up_actions: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("stage")
    @classmethod
    def _validate_stage(cls, value: str) -> str:
        stage_from_wire(value)
        return value

    @field_validator("missing_documents", "follow_up_actions")
    @classmethod
    def _validate_item_lengths(cls, value: list[str]) -> list[str]:
        for item in value:
            if len(item) > 500:
                raise ValueError("Each item must be 500 characters or fewer.")
        return value


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    opportunity_id: UUID
    opportunity_title: str
    provider_name: str
    deadline: date | None
    stage: ApplicationStage
    created_at: datetime
    updated_at: datetime
    application_date: date | None
    application_reference_number: str | None
    missing_documents: list[str]
    interview_date: date | None
    personal_notes: str
    result_date: date | None
    scholarship_value: float | None
    follow_up_actions: list[str]

    @field_serializer("stage")
    def _serialize_stage(self, stage: ApplicationStage, _info: Any) -> str:
        return _STAGE_MODEL_TO_WIRE[stage]


class ApplicationPage(BaseModel):
    items: list[ApplicationRead]
    total: int
    page: int
    page_size: int

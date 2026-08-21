from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.guidance import GuidanceItemStatus, GuidanceItemType

_ITEM_TYPE_WIRE_TO_MODEL: dict[str, GuidanceItemType] = {
    "applicationStep": GuidanceItemType.application_step,
    "requiredDocument": GuidanceItemType.required_document,
    "profileInformation": GuidanceItemType.profile_information,
    "curriculumVitae": GuidanceItemType.curriculum_vitae,
    "personalStatement": GuidanceItemType.personal_statement,
    "researchProposal": GuidanceItemType.research_proposal,
    "recommendationLetter": GuidanceItemType.recommendation_letter,
    "interviewPreparation": GuidanceItemType.interview_preparation,
    "submission": GuidanceItemType.submission,
    "followUp": GuidanceItemType.follow_up,
}
_ITEM_TYPE_MODEL_TO_WIRE: dict[GuidanceItemType, str] = {
    value: key for key, value in _ITEM_TYPE_WIRE_TO_MODEL.items()
}

_ITEM_STATUS_WIRE_TO_MODEL: dict[str, GuidanceItemStatus] = {
    "notStarted": GuidanceItemStatus.not_started,
    "inProgress": GuidanceItemStatus.in_progress,
    "ready": GuidanceItemStatus.ready,
    "missing": GuidanceItemStatus.missing,
    "confirmed": GuidanceItemStatus.confirmed,
    "notApplicable": GuidanceItemStatus.not_applicable,
}
_ITEM_STATUS_MODEL_TO_WIRE: dict[GuidanceItemStatus, str] = {
    value: key for key, value in _ITEM_STATUS_WIRE_TO_MODEL.items()
}


def item_type_from_wire(value: str) -> GuidanceItemType:
    try:
        return _ITEM_TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown guidance item type: {value!r}") from error


def item_type_to_wire(value: GuidanceItemType) -> str:
    return _ITEM_TYPE_MODEL_TO_WIRE[value]


def item_status_from_wire(value: str) -> GuidanceItemStatus:
    try:
        return _ITEM_STATUS_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown guidance item status: {value!r}") from error


def item_status_to_wire(value: GuidanceItemStatus) -> str:
    return _ITEM_STATUS_MODEL_TO_WIRE[value]


class CreatePlanRequest(BaseModel):
    """`required_documents`/`application_procedure` are accepted as a

    client-supplied snapshot because external_opportunities does not yet
    store structured application requirements (ApiOpportunityRepository
    always returns empty lists for these today - a pre-existing gap in
    the Opportunities feature, not introduced here). The applicant's own
    profile and documents are never trusted from the client: they are
    always looked up server-side from applicant_profiles /
    applicant_documents by the caller's verified uid.
    """

    opportunity_id: str = Field(min_length=1, max_length=255)
    opportunity_title: str = Field(min_length=1, max_length=1000)
    opportunity_deadline: datetime
    required_documents: list[str] = Field(default_factory=list, max_length=100)
    application_procedure: list[str] = Field(default_factory=list, max_length=100)


class UpdateItemRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        item_status_from_wire(value)
        return value


class TrackRecommendationLetterRequest(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    referee_name: str = Field(min_length=1, max_length=255)
    referee_email: str = Field(min_length=1, max_length=255)
    requested_at: datetime
    due_at: datetime
    received: bool = False
    received_at: datetime | None = None


class ConfirmSubmissionRequest(BaseModel):
    confirmed_at: datetime
    application_reference: str = Field(default="", max_length=500)
    confirmed_by_user_id: str = Field(default="", max_length=255)
    official_portal: str = Field(default="", max_length=500)


class GuidanceItemRead(BaseModel):
    id: str
    type: str
    title: str
    guidance: str
    status: str
    required: bool
    order: int
    due_at: datetime | None = None


class RecommendationLetterRead(BaseModel):
    id: str
    referee_name: str
    referee_email: str
    requested_at: datetime
    due_at: datetime
    received: bool
    received_at: datetime | None = None


class SubmissionConfirmationRead(BaseModel):
    confirmed_at: datetime
    application_reference: str
    confirmed_by_user_id: str
    official_portal: str


class ApplicationGuidancePlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    opportunity_id: str
    items: list[GuidanceItemRead]
    recommendation_letters: list[RecommendationLetterRead]
    timeline_start: datetime
    deadline: datetime
    follow_up_reminders: list[str]
    updated_at: datetime
    submission_confirmation: SubmissionConfirmationRead | None

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.moderation import ModerationReportType, ModerationStatus, ReportedEntityType

# ReportedEntityType's members (opportunity/provider/user) are already flat
# lowercase words identical on both sides - no wire map needed, unlike the
# other two enums below.

_REPORT_TYPE_WIRE_TO_MODEL: dict[str, ModerationReportType] = {
    "scam": ModerationReportType.scam,
    "incorrectDeadline": ModerationReportType.incorrect_deadline,
    "brokenLink": ModerationReportType.broken_link,
    "duplicateListing": ModerationReportType.duplicate_listing,
    "misleadingContent": ModerationReportType.misleading_content,
    "inappropriateContent": ModerationReportType.inappropriate_content,
    "outdatedContent": ModerationReportType.outdated_content,
    "harmfulContent": ModerationReportType.harmful_content,
}
_REPORT_TYPE_MODEL_TO_WIRE: dict[ModerationReportType, str] = {
    value: key for key, value in _REPORT_TYPE_WIRE_TO_MODEL.items()
}

_STATUS_WIRE_TO_MODEL: dict[str, ModerationStatus] = {
    "submitted": ModerationStatus.submitted,
    "underReview": ModerationStatus.under_review,
    "evidenceRequired": ModerationStatus.evidence_required,
    "escalated": ModerationStatus.escalated,
    "resolved": ModerationStatus.resolved,
    "rejected": ModerationStatus.rejected,
    "contentCorrected": ModerationStatus.content_corrected,
    "contentRemoved": ModerationStatus.content_removed,
    "providerSuspended": ModerationStatus.provider_suspended,
    "closed": ModerationStatus.closed,
}
_STATUS_MODEL_TO_WIRE: dict[ModerationStatus, str] = {
    value: key for key, value in _STATUS_WIRE_TO_MODEL.items()
}


def entity_type_from_wire(value: str) -> ReportedEntityType:
    try:
        return ReportedEntityType(value)
    except ValueError as error:
        raise ValueError(f"Unknown reported entity type: {value!r}") from error


def report_type_from_wire(value: str) -> ModerationReportType:
    try:
        return _REPORT_TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown moderation report type: {value!r}") from error


def status_from_wire(value: str) -> ModerationStatus:
    try:
        return _STATUS_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown moderation status: {value!r}") from error


class ModerationEvidenceItem(BaseModel):
    location: str = Field(max_length=2048)
    description: str = Field(max_length=1000)


class ModerationCaseSubmit(BaseModel):
    entity_type: str
    entity_id: str = Field(min_length=1, max_length=255)
    report_type: str
    description: str = Field(min_length=1, max_length=5000)
    evidence: list[ModerationEvidenceItem] = Field(default_factory=list, max_length=20)

    @field_validator("entity_type")
    @classmethod
    def _validate_entity_type(cls, value: str) -> str:
        entity_type_from_wire(value)
        return value

    @field_validator("report_type")
    @classmethod
    def _validate_report_type(cls, value: str) -> str:
        report_type_from_wire(value)
        return value


class ModerationTransitionRequest(BaseModel):
    status: str
    notes: str = Field(min_length=1, max_length=5000)
    hide_content: bool = False

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        status_from_wire(value)
        return value


class ModerationAppealRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=5000)


class IssueWarningRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ModerationHistoryEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: ModerationStatus
    actor_id: str
    notes: str
    created_at: datetime

    @field_serializer("status")
    def _serialize_status(self, value: ModerationStatus, _info: Any) -> str:
        return _STATUS_MODEL_TO_WIRE[value]


class ModerationCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reporter_id: str
    entity_type: ReportedEntityType
    entity_id: str
    report_type: ModerationReportType
    description: str
    evidence: list[ModerationEvidenceItem]
    status: ModerationStatus
    assigned_moderator_id: str | None
    moderation_notes: str | None
    temporarily_hidden: bool
    appeal_reason: str | None
    created_at: datetime
    history: list[ModerationHistoryEntryRead] = Field(default_factory=list)

    @field_serializer("entity_type")
    def _serialize_entity_type(self, value: ReportedEntityType, _info: Any) -> str:
        return value.value

    @field_serializer("report_type")
    def _serialize_report_type(self, value: ModerationReportType, _info: Any) -> str:
        return _REPORT_TYPE_MODEL_TO_WIRE[value]

    @field_serializer("status")
    def _serialize_status(self, value: ModerationStatus, _info: Any) -> str:
        return _STATUS_MODEL_TO_WIRE[value]


class ModerationAnalyticsRead(BaseModel):
    total_reports: int
    open_reports: int
    removed_content: int
    suspended_providers: int
    repeat_offenders: dict[str, int]


class ModerationWarningRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: ReportedEntityType
    entity_id: str
    reason: str
    issued_by: str
    issued_at: datetime
    case_id: UUID

    @field_serializer("entity_type")
    def _serialize_entity_type(self, value: ReportedEntityType, _info: Any) -> str:
        return value.value

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.support import (
    KnowledgeContentType,
    SupportTicketCategory,
    SupportTicketPriority,
    SupportTicketStatus,
)

_CATEGORY_WIRE_TO_MODEL: dict[str, SupportTicketCategory] = {
    "accountAccess": SupportTicketCategory.account_access,
    "profileProblem": SupportTicketCategory.profile_problem,
    "opportunityInformation": SupportTicketCategory.opportunity_information,
    "eligibilityResult": SupportTicketCategory.eligibility_result,
    "applicationTracking": SupportTicketCategory.application_tracking,
    "documentUpload": SupportTicketCategory.document_upload,
    "notificationProblem": SupportTicketCategory.notification_problem,
    "providerVerification": SupportTicketCategory.provider_verification,
    "fraudReport": SupportTicketCategory.fraud_report,
    "privacyRequest": SupportTicketCategory.privacy_request,
    "technicalIssue": SupportTicketCategory.technical_issue,
    "billingIssue": SupportTicketCategory.billing_issue,
    "generalInquiry": SupportTicketCategory.general_inquiry,
}
_CATEGORY_MODEL_TO_WIRE: dict[SupportTicketCategory, str] = {
    value: key for key, value in _CATEGORY_WIRE_TO_MODEL.items()
}

_PRIORITY_WIRE_TO_MODEL: dict[str, SupportTicketPriority] = {
    "low": SupportTicketPriority.low,
    "normal": SupportTicketPriority.normal,
    "high": SupportTicketPriority.high,
    "urgent": SupportTicketPriority.urgent,
}
_PRIORITY_MODEL_TO_WIRE: dict[SupportTicketPriority, str] = {
    value: key for key, value in _PRIORITY_WIRE_TO_MODEL.items()
}

_STATUS_WIRE_TO_MODEL: dict[str, SupportTicketStatus] = {
    "open": SupportTicketStatus.open,
    "assigned": SupportTicketStatus.assigned,
    "inProgress": SupportTicketStatus.in_progress,
    "waitingForUser": SupportTicketStatus.waiting_for_user,
    "escalated": SupportTicketStatus.escalated,
    "resolved": SupportTicketStatus.resolved,
    "closed": SupportTicketStatus.closed,
    "reopened": SupportTicketStatus.reopened,
}
_STATUS_MODEL_TO_WIRE: dict[SupportTicketStatus, str] = {
    value: key for key, value in _STATUS_WIRE_TO_MODEL.items()
}

_CONTENT_TYPE_WIRE_TO_MODEL: dict[str, KnowledgeContentType] = {
    "frequentlyAskedQuestion": KnowledgeContentType.frequently_asked_question,
    "article": KnowledgeContentType.article,
    "tutorial": KnowledgeContentType.tutorial,
    "applicationHelp": KnowledgeContentType.application_help,
}
_CONTENT_TYPE_MODEL_TO_WIRE: dict[KnowledgeContentType, str] = {
    value: key for key, value in _CONTENT_TYPE_WIRE_TO_MODEL.items()
}

_CLOSED_TICKET_STATUSES = frozenset({SupportTicketStatus.resolved, SupportTicketStatus.closed})
_EXECUTABLE_CONTENT_TYPES = frozenset({"application/x-msdownload", "application/x-executable"})
_MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024


def category_from_wire(value: str) -> SupportTicketCategory:
    try:
        return _CATEGORY_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown support ticket category: {value!r}") from error


def category_to_wire(value: SupportTicketCategory) -> str:
    return _CATEGORY_MODEL_TO_WIRE[value]


def priority_from_wire(value: str) -> SupportTicketPriority:
    try:
        return _PRIORITY_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown support ticket priority: {value!r}") from error


def status_from_wire(value: str) -> SupportTicketStatus:
    try:
        return _STATUS_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown support ticket status: {value!r}") from error


def status_to_wire(value: SupportTicketStatus) -> str:
    return _STATUS_MODEL_TO_WIRE[value]


def content_type_from_wire(value: str) -> KnowledgeContentType:
    try:
        return _CONTENT_TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown knowledge content type: {value!r}") from error


def is_closed_ticket_status(value: SupportTicketStatus) -> bool:
    return value in _CLOSED_TICKET_STATUSES


class AttachmentInput(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=500)
    storage_location: str = Field(min_length=1, max_length=1024)
    content_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)

    @field_validator("size_bytes")
    @classmethod
    def _validate_size(cls, value: int) -> int:
        if value > _MAX_ATTACHMENT_BYTES:
            raise ValueError("Attachments cannot exceed 10 MB.")
        return value

    @field_validator("content_type")
    @classmethod
    def _validate_content_type(cls, value: str) -> str:
        if value in _EXECUTABLE_CONTENT_TYPES:
            raise ValueError("Executable attachments are not allowed.")
        return value


class SubmitTicketRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    category: str
    priority: str
    message: str = Field(min_length=1, max_length=10000)
    attachments: list[AttachmentInput] = Field(default_factory=list, max_length=10)

    @field_validator("category")
    @classmethod
    def _validate_category(cls, value: str) -> str:
        category_from_wire(value)
        return value

    @field_validator("priority")
    @classmethod
    def _validate_priority(cls, value: str) -> str:
        priority_from_wire(value)
        return value


class AddMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    attachments: list[AttachmentInput] = Field(default_factory=list, max_length=10)


class AddInternalNoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=10000)


class UpdateStatusRequest(BaseModel):
    status: str
    notes: str = Field(default="", max_length=5000)

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        status_from_wire(value)
        return value


class EscalateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=5000)


class SaveArticleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=2000)
    content: str = Field(min_length=1, max_length=20000)
    type: str
    category: str
    language_code: str = Field(default="en", max_length=16)
    published: bool = False
    keywords: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        content_type_from_wire(value)
        return value

    @field_validator("category")
    @classmethod
    def _validate_category(cls, value: str) -> str:
        category_from_wire(value)
        return value


class SaveTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=10000)

    @field_validator("category")
    @classmethod
    def _validate_category(cls, value: str) -> str:
        category_from_wire(value)
        return value


class SubmitSurveyRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    storage_location: str
    content_type: str
    size_bytes: int


class SupportMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sender_id: str
    message: str
    created_at: datetime
    attachments: list[AttachmentRead]
    is_agent: bool


class InternalSupportNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    agent_id: str
    note: str
    created_at: datetime


class SupportTicketEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: SupportTicketStatus
    actor_id: str
    created_at: datetime
    notes: str

    @field_serializer("status")
    def _serialize_status(self, value: SupportTicketStatus, _info: Any) -> str:
        return status_to_wire(value)


class SupportTicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester_id: str
    subject: str
    category: SupportTicketCategory
    priority: SupportTicketPriority
    status: SupportTicketStatus
    assigned_agent_id: str | None
    created_at: datetime
    updated_at: datetime
    first_response_due_at: datetime
    resolution_due_at: datetime
    escalation_reason: str | None
    resolved_at: datetime | None
    closed_at: datetime | None
    messages: list[SupportMessageRead] = Field(default_factory=list)
    internal_notes: list[InternalSupportNoteRead] = Field(default_factory=list)
    history: list[SupportTicketEventRead] = Field(default_factory=list)

    @field_serializer("category")
    def _serialize_category(self, value: SupportTicketCategory, _info: Any) -> str:
        return category_to_wire(value)

    @field_serializer("priority")
    def _serialize_priority(self, value: SupportTicketPriority, _info: Any) -> str:
        return _PRIORITY_MODEL_TO_WIRE[value]

    @field_serializer("status")
    def _serialize_status(self, value: SupportTicketStatus, _info: Any) -> str:
        return status_to_wire(value)


class KnowledgeArticleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    summary: str
    content: str
    type: KnowledgeContentType
    category: SupportTicketCategory
    language_code: str
    published: bool
    updated_at: datetime
    keywords: list[str]

    @field_serializer("type")
    def _serialize_type(self, value: KnowledgeContentType, _info: Any) -> str:
        return _CONTENT_TYPE_MODEL_TO_WIRE[value]

    @field_serializer("category")
    def _serialize_category(self, value: SupportTicketCategory, _info: Any) -> str:
        return category_to_wire(value)


class SupportResponseTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    category: SupportTicketCategory
    subject: str
    body: str

    @field_serializer("category")
    def _serialize_category(self, value: SupportTicketCategory, _info: Any) -> str:
        return category_to_wire(value)


class SupportPerformanceReportRead(BaseModel):
    total_tickets: int
    open_tickets: int
    sla_breaches: int
    average_first_response_minutes: float
    average_resolution_minutes: float
    satisfaction_score: float
    by_category: dict[str, int]

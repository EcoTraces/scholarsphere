from datetime import date, datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.models.external_opportunity import SyncStatus


class SourceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_code: str
    source_name: str
    is_active: bool
    trust_level: str
    authentication_type: str
    last_successful_sync: datetime | None
    last_failed_sync: datetime | None
    most_recent_error: str | None
    next_scheduled_sync: datetime | None


class SyncQueued(BaseModel):
    task_id: str
    source: str
    status: str = "queued"
    correlation_id: str


class SyncHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: str | None
    source_code: str
    started_at: datetime
    finished_at: datetime | None
    records_received: int
    records_created: int
    records_updated: int
    records_skipped: int
    records_failed: int
    duplicate_candidates: int
    status: SyncStatus
    error_summary: str | None
    correlation_id: str
    triggered_by: str | None
    created_at: datetime
    updated_at: datetime


class SyncHistoryPage(BaseModel):
    items: list[SyncHistoryItem]
    total: int
    page: int
    page_size: int


class PendingOpportunityItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    external_id: str
    external_reference: str | None
    title: str
    provider_name: str
    opportunity_type: str
    country: str | None
    description: str | None
    opening_date: date | None = None
    deadline: date | None = None
    opportunity_status: str
    funding_type: str | None
    award_floor: float | None
    award_ceiling: float | None
    currency: str | None
    official_source_url: str | None
    official_application_url: str | None
    duplicate_review_required: bool
    collected_at: datetime


class PendingOpportunityPage(BaseModel):
    items: list[PendingOpportunityItem]
    total: int
    page: int
    page_size: int


class SourceHealth(BaseModel):
    source_code: str
    active_status: bool
    last_successful_sync: datetime | None
    last_failed_sync: datetime | None
    most_recent_error: str | None
    next_scheduled_sync: datetime | None


class VerificationDecisionRequest(BaseModel):
    decision: Literal[
        "approved",
        "rejected",
        "reverification_required",
        "expired",
        "source_unavailable",
        "suspicious",
    ]
    notes: str = Field(min_length=1, max_length=4000)
    source_checked: bool = False
    application_link_checked: bool = False
    deadline_checked: bool = False
    duplicate_checked: bool = False


class PublicationRequest(BaseModel):
    published: bool


class SourceStateRequest(BaseModel):
    is_active: bool


class OpportunityState(BaseModel):
    id: UUID
    verification_status: str
    publication_status: str


class VerificationReviewState(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: UUID
    verification_officer_id: str | None
    source_checked: bool
    application_link_checked: bool
    deadline_checked: bool
    duplicate_checked: bool
    decision: str
    notes: str | None
    verified_at: datetime | None
    updated_at: datetime


class OpportunityNoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=4000)


class OpportunityEditRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    title: str | None = Field(default=None, min_length=1, max_length=1000)
    description: str | None = None
    opening_date: date | None = None
    deadline: date | None = None
    funding_type: str | None = Field(default=None, max_length=128)
    award_floor: float | None = None
    award_ceiling: float | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    official_source_url: HttpUrl | None = None
    official_application_url: HttpUrl | None = None

    @field_validator("official_source_url", "official_application_url")
    @classmethod
    def https_urls_only(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is not None and value.scheme != "https":
            raise ValueError("official URLs must use HTTPS")
        return value


class OpportunityEditResponse(BaseModel):
    id: UUID
    changed_fields: list[str]

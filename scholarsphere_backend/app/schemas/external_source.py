from datetime import date, datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    deadline: date | None = None
    opportunity_status: str
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
    decision: Literal["approved", "rejected"]
    notes: str = Field(min_length=1, max_length=4000)
    source_checked: bool
    application_link_checked: bool
    deadline_checked: bool
    duplicate_checked: bool


class PublicationRequest(BaseModel):
    published: bool


class SourceStateRequest(BaseModel):
    is_active: bool


class OpportunityState(BaseModel):
    id: UUID
    verification_status: str
    publication_status: str

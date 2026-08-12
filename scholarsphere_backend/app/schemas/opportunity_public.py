from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.services.deadline_engine import DeadlinePriority


class PublicOpportunity(BaseModel):
    """A published, human-verified opportunity as shown to applicants.

    Every field here is either a normalized value collected from the
    opportunity's official source, or an explicit ``UNKNOWN``/``None`` when
    the source did not provide it. Nothing is inferred or fabricated.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    opportunity_type: str
    provider_name: str
    country: str | None
    description: str | None
    opening_date: date | None
    deadline: date | None
    opportunity_status: str
    funding_type: str | None
    award_floor: float | None
    award_ceiling: float | None
    currency: str | None
    official_source_url: str | None
    official_application_url: str | None
    verification_status: str
    source_code: str
    source_name: str
    source_trust_level: str
    collected_at: datetime
    last_external_update_at: datetime
    verified_at: datetime | None
    days_remaining: int | None
    deadline_priority: DeadlinePriority


class PublicOpportunityPage(BaseModel):
    items: list[PublicOpportunity]
    total: int
    page: int
    page_size: int


class FieldEvidence(BaseModel):
    field: str
    value: Any
    confidence: str


class OpportunityEvidence(BaseModel):
    """Answers "where did this field come from?" for one opportunity.

    ``raw_payload`` is the exact, unmodified JSON record last collected
    from the official source API - the ground truth every normalized
    field above is derived from.
    """

    opportunity_id: UUID
    source_code: str
    source_name: str
    source_type: str
    source_trust_level: str
    official_source_url: str | None
    collected_at: datetime
    field_evidence: list[FieldEvidence]
    raw_payload: dict[str, Any]


class VerificationHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    previous_status: str
    new_status: str
    reason: str
    changed_fields: dict[str, Any] | None
    changed_at: datetime


class VerificationHistoryPage(BaseModel):
    opportunity_id: UUID
    items: list[VerificationHistoryItem]

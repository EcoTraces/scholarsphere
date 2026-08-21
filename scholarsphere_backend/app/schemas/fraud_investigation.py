from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.fraud_investigation import FraudSubjectType


class RiskScoringInputIn(BaseModel):
    provider_risk: int = Field(default=0, ge=0, le=100)
    source_risk: int = Field(default=0, ge=0, le=100)
    user_behaviour_risk: int = Field(default=0, ge=0, le=100)
    suspicious_domain: bool = False
    duplicate_account: bool = False
    risky_link: bool = False
    payment_request: bool = False
    impersonation: bool = False


class CreateFraudCaseRequest(BaseModel):
    subject_type: FraudSubjectType
    subject_id: str = Field(min_length=1, max_length=255)
    risk_input: RiskScoringInputIn = Field(default_factory=RiskScoringInputIn)


class AssignCaseRequest(BaseModel):
    investigator_id: str = Field(min_length=1, max_length=255)


class AddEvidenceRequest(BaseModel):
    type: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1, max_length=1000)
    summary: str = Field(default="", max_length=5000)


class AddNoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=5000)


class AppealRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class AddWatchlistEntryRequest(BaseModel):
    subject_type: FraudSubjectType
    value: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=2000)
    blocked: bool = True


class RiskScoreRead(BaseModel):
    overall: int
    level: str
    provider_risk: int
    source_risk: int
    user_behaviour_risk: int
    domain_risk: int
    link_risk: int
    payment_risk: int
    impersonation_risk: int
    reasons: list[str]


class FraudCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_type: str
    subject_id: str
    risk: RiskScoreRead
    status: str
    assigned_investigator_id: str | None
    evidence: list[dict[str, Any]]
    investigator_notes: list[str]
    created_at: datetime
    history: list[str]
    appeal_reason: str | None

    @field_validator("subject_type", "status", mode="before")
    @classmethod
    def _unwrap_enum(cls, value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value)

    @classmethod
    def from_model(cls, case: Any) -> "FraudCaseRead":
        return cls(
            id=case.id,
            subject_type=case.subject_type,
            subject_id=case.subject_id,
            risk=RiskScoreRead(
                overall=case.risk_overall,
                level=case.risk_level.value,
                provider_risk=case.risk_provider,
                source_risk=case.risk_source,
                user_behaviour_risk=case.risk_user_behaviour,
                domain_risk=case.risk_domain,
                link_risk=case.risk_link,
                payment_risk=case.risk_payment,
                impersonation_risk=case.risk_impersonation,
                reasons=case.risk_reasons,
            ),
            status=case.status,
            assigned_investigator_id=case.assigned_investigator_id,
            evidence=case.evidence,
            investigator_notes=case.investigator_notes,
            created_at=case.created_at,
            history=case.history,
            appeal_reason=case.appeal_reason,
        )


class WatchlistEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject_type: str
    value: str
    reason: str
    blocked: bool
    created_at: datetime
    created_by: str

    @field_validator("subject_type", mode="before")
    @classmethod
    def _unwrap_enum(cls, value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value)


class FraudAnalyticsRead(BaseModel):
    open_cases: int
    critical_cases: int
    restricted_subjects: int
    watchlist_entries: int
    by_subject_type: dict[str, int]

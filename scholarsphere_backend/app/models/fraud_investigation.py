import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.external_opportunity import JSONType


class FraudSubjectType(str, enum.Enum):
    opportunity = "opportunity"
    provider = "provider"
    source = "source"
    user = "user"
    domain = "domain"
    payment = "payment"


class InvestigationRiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class FraudCaseStatus(str, enum.Enum):
    opened = "opened"
    assigned = "assigned"
    investigating = "investigating"
    additionalVerificationRequired = "additionalVerificationRequired"
    restricted = "restricted"
    resolved = "resolved"
    rejected = "rejected"
    appealed = "appealed"
    closed = "closed"


CLOSED_CASE_STATUSES = frozenset(
    {FraudCaseStatus.resolved, FraudCaseStatus.rejected, FraudCaseStatus.closed}
)


class FraudCase(Base):
    __tablename__ = "fraud_cases"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    subject_type: Mapped[FraudSubjectType] = mapped_column(
        Enum(FraudSubjectType, native_enum=False), nullable=False, index=True
    )
    subject_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    risk_overall: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_level: Mapped[InvestigationRiskLevel] = mapped_column(
        Enum(InvestigationRiskLevel, native_enum=False), nullable=False
    )
    risk_provider: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_source: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_user_behaviour: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_domain: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_link: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_payment: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_impersonation: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_reasons: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    status: Mapped[FraudCaseStatus] = mapped_column(
        Enum(FraudCaseStatus, native_enum=False), nullable=False, index=True
    )
    assigned_investigator_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    investigator_notes: Mapped[list[str]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    history: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    appeal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class WatchlistEntry(Base):
    __tablename__ = "fraud_watchlist_entries"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    subject_type: Mapped[FraudSubjectType] = mapped_column(
        Enum(FraudSubjectType, native_enum=False), nullable=False, index=True
    )
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)

import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType, PublicationStatus


class ProviderOpportunityType(str, enum.Enum):
    scholarship = "scholarship"
    fellowship = "fellowship"
    internship = "internship"
    conference = "conference"
    summit = "summit"
    webinar = "webinar"
    exchange_program = "exchange_program"
    research_grant = "research_grant"
    competition = "competition"
    training = "training"
    volunteering = "volunteering"
    youth_program = "youth_program"
    online_course = "online_course"
    funded_event = "funded_event"
    grant = "grant"
    job = "job"


class ProviderOpportunityFundingType(str, enum.Enum):
    fully_funded = "fully_funded"
    partially_funded = "partially_funded"
    self_funded = "self_funded"


class ProviderOpportunityDeliveryFormat(str, enum.Enum):
    online = "online"
    physical = "physical"
    hybrid = "hybrid"


class ProviderOpportunityVerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    verification_expired = "verification_expired"
    incomplete = "incomplete"
    suspicious = "suspicious"
    rejected = "rejected"
    expired = "expired"
    archived = "archived"


class ProviderOpportunity(Base):
    """A provider-submitted opportunity - its own pipeline, deliberately not

    sharing tables with the Grants.gov-family ExternalOpportunity pipeline
    (see the Provider implementation plan for why). ``provider_id`` is the
    submitting organization; ``submitted_by`` is the individual admin who
    actually submitted, kept for audit only, never the ownership key.
    """

    __tablename__ = "provider_opportunities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    submitted_by: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    host_institution: Mapped[str] = mapped_column(String(512), nullable=False)
    host_country: Mapped[str] = mapped_column(String(255), nullable=False)
    opportunity_type: Mapped[ProviderOpportunityType] = mapped_column(
        Enum(ProviderOpportunityType, native_enum=False), nullable=False
    )
    funding_type: Mapped[ProviderOpportunityFundingType] = mapped_column(
        Enum(ProviderOpportunityFundingType, native_enum=False), nullable=False
    )
    delivery_format: Mapped[ProviderOpportunityDeliveryFormat] = mapped_column(
        Enum(ProviderOpportunityDeliveryFormat, native_enum=False), nullable=False
    )
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    application_open_date: Mapped[date] = mapped_column(Date, nullable=False)
    official_source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    application_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    eligible_nationalities: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    study_levels: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    fields_of_study: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    benefits: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    eligibility_requirements: Mapped[list[str]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    required_documents: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    application_procedure: Mapped[list[str]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    language_requirements: Mapped[list[str]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    minimum_age: Mapped[int | None] = mapped_column(Integer)
    maximum_age: Mapped[int | None] = mapped_column(Integer)
    work_experience_years_required: Mapped[float | None] = mapped_column(Float)
    contact_information: Mapped[str] = mapped_column(Text, nullable=False)
    available_positions: Mapped[int | None] = mapped_column(Integer)
    application_fee: Mapped[float | None] = mapped_column(Float)
    verification_status: Mapped[ProviderOpportunityVerificationStatus] = mapped_column(
        Enum(ProviderOpportunityVerificationStatus, native_enum=False),
        default=ProviderOpportunityVerificationStatus.pending,
        nullable=False,
    )
    publication_status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, native_enum=False),
        default=PublicationStatus.unpublished,
        nullable=False,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ProviderOpportunityVerificationReview(Base):
    __tablename__ = "provider_opportunity_verification_reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider_opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("provider_opportunities.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    verification_officer_id: Mapped[str | None] = mapped_column(String(255))
    source_checked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    application_link_checked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deadline_checked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_checked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    decision: Mapped[str] = mapped_column(String(64), default="pending", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ProviderOpportunityVerificationHistory(Base):
    __tablename__ = "provider_opportunity_verification_history"
    __table_args__ = (
        Index(
            "ix_provider_opp_verif_history_opp_id",
            "provider_opportunity_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider_opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("provider_opportunities.id", ondelete="CASCADE"), nullable=False
    )
    previous_status: Mapped[str] = mapped_column(String(64), nullable=False)
    new_status: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    changed_fields: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

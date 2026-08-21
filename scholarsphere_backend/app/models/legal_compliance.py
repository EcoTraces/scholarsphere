import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class LegalPolicyType(str, enum.Enum):
    terms_and_conditions = "terms_and_conditions"
    privacy_policy = "privacy_policy"
    cookie_policy = "cookie_policy"
    acceptable_use = "acceptable_use"
    provider_agreement = "provider_agreement"
    content_publishing = "content_publishing"
    verification_disclaimer = "verification_disclaimer"
    funding_disclaimer = "funding_disclaimer"
    copyright_policy = "copyright_policy"
    data_processing_agreement = "data_processing_agreement"


class LegalRequestType(str, enum.Enum):
    takedown = "takedown"
    complaint = "complaint"
    regulator = "regulator"
    court_order = "court_order"
    data_protection = "data_protection"


class LegalRequestStatus(str, enum.Enum):
    submitted = "submitted"
    validated = "validated"
    in_review = "in_review"
    actioned = "actioned"
    rejected = "rejected"
    closed = "closed"


class LegalPolicy(Base):
    __tablename__ = "legal_policies"
    __table_args__ = (UniqueConstraint("type", "version", name="uq_legal_policy_type_version"),)

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[LegalPolicyType] = mapped_column(
        Enum(LegalPolicyType, native_enum=False), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requires_acceptance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    material_change: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_by: Mapped[str] = mapped_column(String(255), nullable=False)


class PolicyAcceptance(Base):
    __tablename__ = "policy_acceptances"
    __table_args__ = (UniqueConstraint("user_id", "policy_id", name="uq_acceptance_user_policy"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(
        ForeignKey("legal_policies.id", ondelete="CASCADE"), nullable=False
    )
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)


class LegalRequest(Base):
    __tablename__ = "legal_requests"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[LegalRequestType] = mapped_column(
        Enum(LegalRequestType, native_enum=False), nullable=False
    )
    requester: Mapped[str] = mapped_column(String(500), nullable=False)
    subject_entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_locations: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    status: Mapped[LegalRequestStatus] = mapped_column(
        Enum(LegalRequestStatus, native_enum=False),
        default=LegalRequestStatus.submitted,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    history: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)


class ComplianceRecord(Base):
    __tablename__ = "compliance_records"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    framework: Mapped[str] = mapped_column(String(255), nullable=False)
    obligation: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    review_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_locations: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)

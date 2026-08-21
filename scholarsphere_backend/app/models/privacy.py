import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class ConsentType(str, enum.Enum):
    privacy_policy = "privacy_policy"
    terms_and_conditions = "terms_and_conditions"
    cookies = "cookies"
    marketing = "marketing"
    notifications = "notifications"
    personalized_recommendations = "personalized_recommendations"
    sensitive_data = "sensitive_data"
    document_storage = "document_storage"
    third_party_sharing = "third_party_sharing"


class PrivacyRequestType(str, enum.Enum):
    data_export = "data_export"
    account_deletion = "account_deletion"
    data_correction = "data_correction"
    document_deletion = "document_deletion"


class PrivacyRequestStatus(str, enum.Enum):
    submitted = "submitted"
    in_review = "in_review"
    completed = "completed"
    rejected = "rejected"
    cancelled = "cancelled"


class ConsentRecord(Base):
    """One row per (user, consent type) - re-granting overwrites granted_at

    and clears withdrawn_at, matching DemoPrivacyRepository's
    `_consents[userId][type] = ConsentRecord(...)` overwrite semantics.
    """

    __tablename__ = "consent_records"
    __table_args__ = (UniqueConstraint("user_id", "type", name="uq_consent_user_type"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[ConsentType] = mapped_column(Enum(ConsentType, native_enum=False), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[PrivacyRequestType] = mapped_column(
        Enum(PrivacyRequestType, native_enum=False), nullable=False
    )
    status: Mapped[PrivacyRequestStatus] = mapped_column(
        Enum(PrivacyRequestStatus, native_enum=False),
        default=PrivacyRequestStatus.submitted,
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class OrganizationAccessRecord(Base):
    __tablename__ = "organization_access_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_name: Mapped[str] = mapped_column(String(512), nullable=False)
    data_categories: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consent_record_type: Mapped[ConsentType] = mapped_column(
        Enum(ConsentType, native_enum=False), nullable=False
    )


class PrivacyIncident(Base):
    __tablename__ = "privacy_incidents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    affected_user_ids: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

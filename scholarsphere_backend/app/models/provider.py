import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class ProviderStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    additional_information_required = "additional_information_required"
    verified = "verified"
    rejected = "rejected"
    suspended = "suspended"
    verification_expired = "verification_expired"
    archived = "archived"


class ProviderPermission(str, enum.Enum):
    manage_organization = "manage_organization"
    publish_opportunities = "publish_opportunities"
    manage_admins = "manage_admins"


class Provider(Base):
    """An organization account that may submit opportunities once verified.

    ``user_id`` is the owner's Firebase uid - there is no local users table,
    identity lives in Firebase, matching ``Application.user_id``.
    """

    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    organization_name: Mapped[str] = mapped_column(String(512), nullable=False)
    organization_type: Mapped[str] = mapped_column(String(128), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(255), nullable=False)
    official_website: Mapped[str] = mapped_column(String(2048), nullable=False)
    official_email_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    physical_address: Mapped[str] = mapped_column(Text, nullable=False)
    contact_person: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(64), nullable=False)
    supporting_documents: Mapped[list[str]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    social_media_links: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    status: Mapped[ProviderStatus] = mapped_column(
        Enum(ProviderStatus, native_enum=False), default=ProviderStatus.draft, nullable=False
    )
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    verification_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[str | None] = mapped_column(String(255))
    reverification_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def has_verified_badge(self) -> bool:
        if self.status != ProviderStatus.verified:
            return False
        if self.reverification_date is None:
            return True
        return self.reverification_date > datetime.now(self.reverification_date.tzinfo)


class ProviderAdministrator(Base):
    __tablename__ = "provider_administrators"
    __table_args__ = (UniqueConstraint("provider_id", "user_id", name="uq_provider_admin_user"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProviderActivity(Base):
    __tablename__ = "provider_activity_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProviderAppeal(Base):
    __tablename__ = "provider_appeals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="Pending", nullable=False)

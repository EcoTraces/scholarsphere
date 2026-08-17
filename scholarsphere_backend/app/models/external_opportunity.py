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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


class ProcessingStatus(str, enum.Enum):
    pending = "pending"
    normalized = "normalized"
    imported = "imported"
    skipped = "skipped"
    duplicate = "duplicate"
    failed = "failed"


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    reverification_required = "reverification_required"
    rejected = "rejected"
    suspicious = "suspicious"
    expired = "expired"
    archived = "archived"
    source_unavailable = "source_unavailable"


class PublicationStatus(str, enum.Enum):
    unpublished = "unpublished"
    published = "published"
    archived = "archived"


class SyncStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    partially_completed = "partially_completed"
    failed = "failed"
    cancelled = "cancelled"


class OpportunitySource(Base):
    __tablename__ = "opportunity_sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    authentication_type: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failed_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    most_recent_error: Mapped[str | None] = mapped_column(Text)
    next_scheduled_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RawExternalOpportunity(Base):
    __tablename__ = "raw_external_opportunities"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_raw_source_external_id"),
        Index("ix_raw_external_processing_status", "processing_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, native_enum=False), default=ProcessingStatus.pending, nullable=False
    )
    processing_error: Mapped[str | None] = mapped_column(Text)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("external_opportunities.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ExternalOpportunity(Base):
    __tablename__ = "external_opportunities"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_external_source_external_id"),
        Index("ix_external_verification_publication", "verification_status", "publication_status"),
        Index("ix_external_fingerprint", "external_fingerprint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_sources.id", ondelete="RESTRICT"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(512))
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    opportunity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(512), nullable=False)
    provider_code: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    opening_date: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date)
    opportunity_status: Mapped[str] = mapped_column(String(128), nullable=False)
    funding_type: Mapped[str | None] = mapped_column(String(128))
    award_floor: Mapped[float | None] = mapped_column(Float)
    award_ceiling: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(3))
    official_source_url: Mapped[str | None] = mapped_column(String(2048))
    official_application_url: Mapped[str | None] = mapped_column(String(2048))
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    external_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    duplicate_review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, native_enum=False), default=VerificationStatus.pending, nullable=False
    )
    publication_status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, native_enum=False), default=PublicationStatus.unpublished, nullable=False
    )
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_external_update_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    source: Mapped[OpportunitySource] = relationship()
    verification_history: Mapped[list["VerificationHistory"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )
    verification_review: Mapped["VerificationReview | None"] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )


class VerificationHistory(Base):
    __tablename__ = "external_opportunity_verification_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("external_opportunities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_status: Mapped[str] = mapped_column(String(64), nullable=False)
    new_status: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    changed_fields: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    opportunity: Mapped[ExternalOpportunity] = relationship(back_populates="verification_history")


class VerificationReview(Base):
    """Active verification-queue record; history remains append-only separately."""

    __tablename__ = "external_opportunity_verification_reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("external_opportunities.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
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
    opportunity: Mapped[ExternalOpportunity] = relationship(
        back_populates="verification_review"
    )


class OpportunitySyncHistory(Base):
    __tablename__ = "opportunity_sync_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[str | None] = mapped_column(String(255), index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("opportunity_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    triggered_by: Mapped[str | None] = mapped_column(String(255), index=True)
    correlation_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_candidates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, native_enum=False), default=SyncStatus.queued, nullable=False
    )
    error_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ImportAuditLog(Base):
    """Append-only by application policy; no update/delete service is exposed."""

    __tablename__ = "external_import_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("external_opportunities.id", ondelete="RESTRICT"), index=True
    )
    actor_id: Mapped[str | None] = mapped_column(String(255), index=True)
    actor_role: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(32), default="success", nullable=False)
    previous_value: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    correlation_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base


class RetainedEntityType(str, enum.Enum):
    opportunity = "opportunity"
    userAccount = "userAccount"
    document = "document"
    notification = "notification"
    auditLog = "auditLog"
    supportTicket = "supportTicket"
    providerRecord = "providerRecord"


class LifecycleStatus(str, enum.Enum):
    active = "active"
    softDeleted = "softDeleted"
    archived = "archived"
    pendingPermanentDeletion = "pendingPermanentDeletion"
    permanentlyDeleted = "permanentlyDeleted"
    restored = "restored"


class RetentionRule(Base):
    __tablename__ = "retention_rules"

    entity_type: Mapped[RetainedEntityType] = mapped_column(
        Enum(RetainedEntityType, native_enum=False), primary_key=True
    )
    active_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    archive_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    delete_from_backups_after_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    archive_expired_records: Mapped[bool] = mapped_column(Boolean, nullable=False)
    retain_rejected_for_fraud_prevention: Mapped[bool] = mapped_column(
        Boolean, nullable=False
    )


class LifecycleRecord(Base):
    __tablename__ = "lifecycle_records"

    entity_type: Mapped[RetainedEntityType] = mapped_column(
        Enum(RetainedEntityType, native_enum=False), primary_key=True
    )
    entity_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[LifecycleStatus] = mapped_column(
        Enum(LifecycleStatus, native_enum=False), nullable=False
    )
    contains_personal_data: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    backup_deletion_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deletion_verification: Mapped[str | None] = mapped_column(String(255), nullable=True)


class LegalHold(Base):
    __tablename__ = "legal_holds"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[RetainedEntityType] = mapped_column(
        Enum(RetainedEntityType, native_enum=False), nullable=False
    )
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    placed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

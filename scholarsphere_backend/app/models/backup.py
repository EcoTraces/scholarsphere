import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BackupType(str, enum.Enum):
    fullDatabase = "fullDatabase"
    incremental = "incremental"
    transactionLog = "transactionLog"
    fileStorage = "fileStorage"


class BackupStatus(str, enum.Enum):
    scheduled = "scheduled"
    running = "running"
    completed = "completed"
    failed = "failed"
    verified = "verified"
    expired = "expired"


class RecoveryStatus(str, enum.Enum):
    requested = "requested"
    approved = "approved"
    running = "running"
    completed = "completed"
    failed = "failed"


class BackupPolicy(Base):
    __tablename__ = "backup_policies"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    full_backup_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_log_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    retention_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_restore_test: Mapped[bool] = mapped_column(Boolean, nullable=False)
    encryption_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    separate_region_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recovery_point_objective_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    recovery_time_objective_seconds: Mapped[int] = mapped_column(Integer, nullable=False)


class BackupRecord(Base):
    __tablename__ = "backup_records"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[BackupType] = mapped_column(Enum(BackupType, native_enum=False), nullable=False)
    status: Mapped[BackupStatus] = mapped_column(
        Enum(BackupStatus, native_enum=False), nullable=False
    )
    storage_location: Mapped[str] = mapped_column(String(1000), nullable=False)
    region: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(255), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class RecoveryTest(Base):
    __tablename__ = "recovery_tests"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    backup_id: Mapped[str] = mapped_column(
        ForeignKey("backup_records.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RecoveryStatus] = mapped_column(
        Enum(RecoveryStatus, native_enum=False), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    integrity_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)

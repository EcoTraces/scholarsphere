import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditAction(str, enum.Enum):
    login = "login"
    logout = "logout"
    failedLogin = "failedLogin"
    profileChanged = "profileChanged"
    roleChanged = "roleChanged"
    permissionChanged = "permissionChanged"
    opportunityChanged = "opportunityChanged"
    verificationDecision = "verificationDecision"
    documentAccessed = "documentAccessed"
    providerAction = "providerAction"
    administrativeAction = "administrativeAction"
    securityEvent = "securityEvent"
    dataExported = "dataExported"
    accountDeleted = "accountDeleted"
    apiRequest = "apiRequest"


class AuditResult(str, enum.Enum):
    success = "success"
    failure = "failure"
    denied = "denied"


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, native_enum=False), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False)
    device_information: Mapped[str] = mapped_column(String(500), nullable=False)
    location_information: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    result: Mapped[AuditResult] = mapped_column(
        Enum(AuditResult, native_enum=False), nullable=False
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    integrity_hash: Mapped[str] = mapped_column(String(16), nullable=False)


class AuditChainState(Base):
    """Singleton row: the hash chain's anchor, carried forward across purges."""

    __tablename__ = "audit_chain_state"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    anchor: Mapped[str] = mapped_column(String(16), nullable=False)


class AuditRetentionPolicy(Base):
    __tablename__ = "audit_retention_policy"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=2555)

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base


class LoginOutcome(str, enum.Enum):
    success = "success"
    invalidCredentials = "invalidCredentials"
    locked = "locked"
    blockedIp = "blockedIp"
    mfaFailed = "mfaFailed"


class SecurityAlertType(str, enum.Enum):
    newDevice = "newDevice"
    suspiciousLogin = "suspiciousLogin"
    repeatedFailures = "repeatedFailures"
    accountLocked = "accountLocked"
    sessionRevoked = "sessionRevoked"
    privilegedAction = "privilegedAction"


class LoginHistoryEntry(Base):
    __tablename__ = "login_history_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    outcome: Mapped[LoginOutcome] = mapped_column(
        Enum(LoginOutcome, native_enum=False), nullable=False
    )
    device_id: Mapped[str] = mapped_column(String(255), nullable=False)
    browser: Mapped[str] = mapped_column(String(255), nullable=False)
    operating_system: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False)
    suspicious: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SecuritySession(Base):
    __tablename__ = "security_sessions"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(255), nullable=False)
    browser: Mapped[str] = mapped_column(String(255), nullable=False)
    operating_system: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    strong_authentication: Mapped[bool] = mapped_column(Boolean, nullable=False)


class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    type: Mapped[SecurityAlertType] = mapped_column(
        Enum(SecurityAlertType, native_enum=False), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

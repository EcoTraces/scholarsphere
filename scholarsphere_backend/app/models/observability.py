import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class LogLevel(str, enum.Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class HealthStatus(str, enum.Enum):
    healthy = "healthy"
    degraded = "degraded"
    unavailable = "unavailable"


class IncidentStatus(str, enum.Enum):
    open = "open"
    acknowledged = "acknowledged"
    investigating = "investigating"
    resolved = "resolved"


class ApplicationLog(Base):
    __tablename__ = "application_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    level: Mapped[LogLevel] = mapped_column(Enum(LogLevel, native_enum=False), nullable=False)
    service: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)


class MetricPoint(Base):
    __tablename__ = "metric_points"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    labels: Mapped[dict[str, str]] = mapped_column(JSONType, default=dict, nullable=False)


class TraceSpan(Base):
    __tablename__ = "trace_spans"

    trace_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    span_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    operation: Mapped[str] = mapped_column(String(255), nullable=False)
    service: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    successful: Mapped[bool] = mapped_column(Boolean, nullable=False)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    comparison: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[LogLevel] = mapped_column(Enum(LogLevel, native_enum=False), nullable=False)
    escalation_target: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OperationalIncident(Base):
    __tablename__ = "operational_incidents"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    severity: Mapped[LogLevel] = mapped_column(Enum(LogLevel, native_enum=False), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    escalation_target: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)

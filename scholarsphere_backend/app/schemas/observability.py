from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.observability import HealthStatus, IncidentStatus, LogLevel


class RecordLogRequest(BaseModel):
    level: LogLevel
    service: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    timestamp: datetime
    correlation_id: str = Field(min_length=1, max_length=255)
    context: dict[str, Any] = Field(default_factory=dict)


class ApplicationLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    level: LogLevel
    service: str
    message: str
    timestamp: datetime
    correlation_id: str
    context: dict[str, Any]

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, value: Any) -> str:
        return str(value)


class RecordMetricRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    value: float
    unit: str = Field(min_length=1, max_length=64)
    timestamp: datetime
    labels: dict[str, str] = Field(default_factory=dict)


class RecordTraceRequest(BaseModel):
    trace_id: str = Field(min_length=1, max_length=255)
    span_id: str = Field(min_length=1, max_length=255)
    parent_span_id: str | None = None
    operation: str = Field(min_length=1, max_length=255)
    service: str = Field(min_length=1, max_length=255)
    started_at: datetime
    duration_seconds: float = Field(ge=0)
    successful: bool


class ServiceHealthRead(BaseModel):
    service: str
    status: HealthStatus
    checked_at: datetime
    latency_milliseconds: int
    details: dict[str, Any] = Field(default_factory=dict)


class SaveAlertRuleRequest(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    metric_name: str = Field(min_length=1, max_length=255)
    threshold: float
    comparison: str = Field(min_length=1, max_length=32)
    severity: LogLevel
    escalation_target: str = Field(min_length=1, max_length=255)
    enabled: bool = True


class AlertRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    metric_name: str
    threshold: float
    comparison: str
    severity: LogLevel
    escalation_target: str
    enabled: bool


class OperationalIncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    severity: LogLevel
    status: IncidentStatus
    created_at: datetime
    escalation_target: str
    notes: list[str]


class PerformanceReportRead(BaseModel):
    request_volume: int
    error_rate: float
    average_response_milliseconds: float
    metrics: dict[str, float]
    generated_at: datetime

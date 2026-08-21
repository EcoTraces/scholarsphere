from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuditRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_id: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str
    previous_value: str | None
    new_value: str | None
    ip_address: str
    device_information: str
    location_information: str
    timestamp: datetime
    result: str
    failure_reason: str | None
    correlation_id: str
    integrity_hash: str

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, value: object) -> str:
        return str(value)

    @field_validator("action", "result", mode="before")
    @classmethod
    def _unwrap_enum(cls, value: object) -> str:
        return value.value if hasattr(value, "value") else str(value)


class AuditRetentionPolicyRead(BaseModel):
    retention_days: int


class AuditRetentionPolicySave(BaseModel):
    retention_days: int = Field(ge=365)


class AuditExportRead(BaseModel):
    csv: str


class EnforceRetentionRead(BaseModel):
    removed: int

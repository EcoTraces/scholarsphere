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


class ImportAuditRecordRead(BaseModel):
    """Read shape for ImportAuditLog - the append-only trail covering the

    opportunity import/verification pipeline and provider lifecycle
    actions (app/services/audit.py::append_audit), distinct from
    AuditRecord above (backup/collection/data_lifecycle/release/
    system_configuration, app/services/audit_log.py). Previously had no
    read endpoint at all despite covering the pipeline that protects this
    platform's core "Verified" trust label - see Task.md.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    opportunity_id: str | None
    actor_id: str | None
    actor_role: str | None
    action: str
    entity_type: str
    entity_id: str
    result: str
    previous_value: dict | None
    new_value: dict | None
    correlation_id: str
    created_at: datetime

    @field_validator("id", "opportunity_id", mode="before")
    @classmethod
    def _stringify_opportunity_id(cls, value: object) -> str | None:
        return None if value is None else str(value)


class ImportAuditRecordPage(BaseModel):
    items: list[ImportAuditRecordRead]
    total: int
    page: int
    page_size: int


class AuditRetentionPolicyRead(BaseModel):
    retention_days: int


class AuditRetentionPolicySave(BaseModel):
    retention_days: int = Field(ge=365)


class AuditExportRead(BaseModel):
    csv: str


class EnforceRetentionRead(BaseModel):
    removed: int

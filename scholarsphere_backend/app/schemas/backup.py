from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.backup import BackupType

_BACKUP_TYPE_WIRE_TO_MODEL: dict[str, BackupType] = {
    "fullDatabase": BackupType.fullDatabase,
    "incremental": BackupType.incremental,
    "transactionLog": BackupType.transactionLog,
    "fileStorage": BackupType.fileStorage,
}


def backup_type_from_wire(value: str) -> BackupType:
    try:
        return _BACKUP_TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown backup type: {value!r}") from error


class BackupPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    full_backup_interval_seconds: int
    transaction_log_interval_seconds: int
    retention_seconds: int
    monthly_restore_test: bool
    encryption_required: bool
    separate_region_required: bool
    recovery_point_objective_seconds: int
    recovery_time_objective_seconds: int


class BackupPolicySave(BaseModel):
    full_backup_interval_seconds: int = Field(default=86400, ge=1)
    transaction_log_interval_seconds: int = Field(default=900, ge=1)
    retention_seconds: int = Field(default=35 * 86400, ge=1)
    monthly_restore_test: bool = True
    encryption_required: bool = True
    separate_region_required: bool = True
    recovery_point_objective_seconds: int = Field(default=900, ge=1, le=900)
    recovery_time_objective_seconds: int = Field(default=4 * 3600, ge=1, le=4 * 3600)


class CreateBackupRequest(BaseModel):
    type: str
    region: str = Field(min_length=1, max_length=255)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        backup_type_from_wire(value)
        return value


class BackupRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: BackupType
    status: str
    storage_location: str
    region: str
    encrypted: bool
    created_at: datetime
    completed_at: datetime | None
    expires_at: datetime | None
    size_bytes: int
    checksum: str
    failure_reason: str | None

    @field_validator("type", "status", mode="before")
    @classmethod
    def _unwrap_enum(cls, value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value)


class RecoveryTestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    backup_id: str
    status: str
    started_at: datetime
    completed_at: datetime
    integrity_valid: bool
    duration_seconds: int
    notes: str

    @field_validator("status", mode="before")
    @classmethod
    def _unwrap_enum(cls, value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value)


class DisasterRecoveryPlanRead(BaseModel):
    version: int
    primary_region: str
    recovery_region: str
    restoration_steps: list[str]
    emergency_contacts: list[str]
    business_continuity_steps: list[str]
    last_reviewed_at: datetime


class EnforceRetentionRead(BaseModel):
    removed: int

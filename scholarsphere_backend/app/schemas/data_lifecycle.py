from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.data_lifecycle import LifecycleStatus, RetainedEntityType


class SaveRetentionRuleRequest(BaseModel):
    active_duration_seconds: int = Field(ge=0)
    archive_duration_seconds: int = Field(ge=0)
    delete_from_backups_after_seconds: int = Field(ge=0)
    archive_expired_records: bool = True
    retain_rejected_for_fraud_prevention: bool = True


class RetentionRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_type: RetainedEntityType
    active_duration_seconds: int
    archive_duration_seconds: int
    delete_from_backups_after_seconds: int
    archive_expired_records: bool
    retain_rejected_for_fraud_prevention: bool


class RegisterRecordRequest(BaseModel):
    entity_type: RetainedEntityType
    entity_id: str = Field(min_length=1, max_length=255)
    owner_id: str | None = None
    status: LifecycleStatus = LifecycleStatus.active
    contains_personal_data: bool = False


class LifecycleRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entity_type: RetainedEntityType
    entity_id: str
    owner_id: str | None
    status: LifecycleStatus
    contains_personal_data: bool
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    deleted_at: datetime | None
    backup_deletion_due_at: datetime | None
    deletion_verification: str | None


class LegalHoldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_type: RetainedEntityType
    entity_id: str
    reason: str
    placed_by: str
    placed_at: datetime
    released_at: datetime | None

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_id(cls, value: Any) -> str:
        return str(value)


class PlaceLegalHoldRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class CleanupReportRead(BaseModel):
    archived: int
    permanently_deleted: int
    skipped_legal_holds: int
    completed_at: datetime

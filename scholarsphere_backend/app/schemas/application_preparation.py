from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.application_preparation import (
    ApplicantCategory,
    ChecklistItemStatus,
    RequirementMatchStatus,
)


class WorkspaceCreateRequest(BaseModel):
    application_id: UUID
    category: ApplicantCategory
    target_university: str = Field(default="", max_length=500)
    target_program: str = Field(default="", max_length=500)


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: str
    application_id: UUID
    category: ApplicantCategory
    target_university: str
    target_program: str
    created_at: datetime
    updated_at: datetime


class RequirementMatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requirement_text: str
    status: RequirementMatchStatus
    notes: str


class ChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_key: str
    label: str
    category: str
    status: ChecklistItemStatus
    auto_generated: bool
    sort_order: int


class ChecklistItemUpdateRequest(BaseModel):
    status: ChecklistItemStatus


class ReadinessRead(BaseModel):
    profile_pct: float
    background_pct: float
    documents_pct: float
    requirements_pct: float
    checklist_pct: float
    overall_pct: float
    weights: dict[str, float]

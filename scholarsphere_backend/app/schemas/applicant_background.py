from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.applicant_background import BackgroundEntryCategory


class BackgroundEntryCreateRequest(BaseModel):
    category: BackgroundEntryCategory
    title: str = Field(min_length=1, max_length=500)
    organization: str = Field(default="", max_length=500)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str = Field(default="", max_length=5000)
    details: dict = Field(default_factory=dict)


class BackgroundEntryUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    organization: str | None = Field(default=None, max_length=500)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    description: str | None = Field(default=None, max_length=5000)
    details: dict | None = None


class BackgroundEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: BackgroundEntryCategory
    title: str
    organization: str
    start_date: date | None
    end_date: date | None
    is_current: bool
    description: str
    details: dict
    created_at: datetime
    updated_at: datetime

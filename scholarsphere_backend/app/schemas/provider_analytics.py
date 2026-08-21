from datetime import datetime

from pydantic import BaseModel, Field


class RecordEngagementEventRequest(BaseModel):
    provider_id: str
    opportunity_id: str = Field(min_length=1, max_length=255)
    kind: str = Field(min_length=1, max_length=64)
    country: str = Field(min_length=1, max_length=255)
    study_level: str = Field(min_length=1, max_length=255)
    field: str = Field(min_length=1, max_length=255)
    occurred_at: datetime
    identifiable_sharing_consent: bool = False


class ProviderAnalyticsSnapshotRead(BaseModel):
    views: int
    saves: int
    application_clicks: int
    countries: dict[str, int]
    study_levels: dict[str, int]
    fields: dict[str, int]
    suppressed: bool


class ProviderAnalyticsExportRead(BaseModel):
    csv: str

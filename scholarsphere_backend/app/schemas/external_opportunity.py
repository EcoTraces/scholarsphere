from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.services.parsing import utc_now


class NormalizedExternalOpportunity(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source_code: str = Field(min_length=1, max_length=64)
    external_id: str = Field(min_length=1, max_length=512)
    external_reference: str | None = None
    title: str = Field(min_length=1, max_length=1000)
    opportunity_type: str = Field(min_length=1, max_length=128)
    provider_name: str = Field(min_length=1, max_length=512)
    provider_code: str | None = None
    country: str | None = None
    description: str | None = None
    opening_date: date | None = None
    deadline: date | None = None
    opportunity_status: str = Field(min_length=1, max_length=128)
    funding_type: str | None = None
    award_floor: float | None = None
    award_ceiling: float | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    official_source_url: HttpUrl | None = None
    official_application_url: HttpUrl | None = None
    collected_at: datetime = Field(default_factory=utc_now)
    verification_status: str = "pending"
    publication_status: str = "unpublished"
    raw_payload: dict[str, Any]

    @field_validator("verification_status")
    @classmethod
    def pending_only(cls, value: str) -> str:
        if value != "pending":
            raise ValueError("externally collected opportunities must be pending")
        return value

    @field_validator("publication_status")
    @classmethod
    def unpublished_only(cls, value: str) -> str:
        if value != "unpublished":
            raise ValueError("externally collected opportunities must be unpublished")
        return value

    @field_validator("collected_at")
    @classmethod
    def timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("collected_at must be timezone-aware")
        return value

    @field_validator("official_source_url", "official_application_url")
    @classmethod
    def https_urls_only(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is not None and value.scheme != "https":
            raise ValueError("official URLs must use HTTPS")
        return value


class ImportStatistics(BaseModel):
    records_received: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    duplicate_candidates: int = 0

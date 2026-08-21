from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OpportunitySnapshot(BaseModel):
    """Opaque passthrough of the Flutter client's Opportunity object.

    Only `id` is required here; every other field is read defensively
    (`.get(...)`) by app.services.search_matching, so an opportunity
    missing an optional field degrades gracefully rather than failing
    the whole synchronize/upsert call.
    """

    model_config = {"extra": "allow"}

    id: str = Field(min_length=1, max_length=255)


class SynchronizeRequest(BaseModel):
    opportunities: list[OpportunitySnapshot] = Field(default_factory=list, max_length=5000)


class RebuildRequest(BaseModel):
    opportunities: list[OpportunitySnapshot] = Field(default_factory=list, max_length=5000)


class OpportunityFilterInput(BaseModel):
    type: str | None = None
    country: str | None = None
    region: str | None = None
    provider: str | None = None
    field: str | None = None
    study_level: str | None = None
    funding: str | None = None
    no_application_fee: bool = False
    eligible_nationality: str | None = None
    deadline_window: str = "any"
    delivery_format: str | None = None
    applicant_age: int | None = None
    available_work_experience_years: float | None = None
    language: str | None = None
    verified_only: bool = True
    availability: str = "open"

    def to_matching_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "country": self.country,
            "region": self.region,
            "provider": self.provider,
            "field": self.field,
            "studyLevel": self.study_level,
            "funding": self.funding,
            "noApplicationFee": self.no_application_fee,
            "eligibleNationality": self.eligible_nationality,
            "deadlineWindow": self.deadline_window,
            "deliveryFormat": self.delivery_format,
            "applicantAge": self.applicant_age,
            "availableWorkExperienceYears": self.available_work_experience_years,
            "language": self.language,
            "verifiedOnly": self.verified_only,
            "availability": self.availability,
        }


class DiscoverySearchRequest(BaseModel):
    query: str = ""
    filter: OpportunityFilterInput = Field(default_factory=OpportunityFilterInput)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    eligibility_scores: dict[str, int] = Field(default_factory=dict)
    source_trust_scores: dict[str, int] = Field(default_factory=dict)


class SearchHitRead(BaseModel):
    opportunity: dict[str, Any]
    score: float
    matched_terms: list[str]


class SearchFacetsRead(BaseModel):
    countries: dict[str, int]
    funding: dict[str, int]
    study_levels: dict[str, int]
    institutions: dict[str, int]


class DiscoverySearchResultRead(BaseModel):
    hits: list[SearchHitRead]
    total: int
    facets: SearchFacetsRead
    suggestions: list[str]
    page: int
    page_size: int


class SearchHistoryEntryRead(BaseModel):
    user_id: str
    query: str
    result_count: int
    searched_at: datetime


class PopularSearchRead(BaseModel):
    query: str
    count: int

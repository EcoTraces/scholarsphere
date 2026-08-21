from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.source_registry import (
    OpportunitySourceType,
    ReliabilityLevel,
    SourceVerificationStatus,
)

_SOURCE_TYPE_WIRE_TO_MODEL: dict[str, OpportunitySourceType] = {
    "officialUniversityWebsite": OpportunitySourceType.official_university_website,
    "officialGovernmentPortal": OpportunitySourceType.official_government_portal,
    "embassyWebsite": OpportunitySourceType.embassy_website,
    "foundationWebsite": OpportunitySourceType.foundation_website,
    "internationalOrganization": OpportunitySourceType.international_organization,
    "officialApplicationPortal": OpportunitySourceType.official_application_portal,
    "approvedApi": OpportunitySourceType.approved_api,
    "approvedRssFeed": OpportunitySourceType.approved_rss_feed,
    "verifiedProviderSubmission": OpportunitySourceType.verified_provider_submission,
    "trustedSecondarySource": OpportunitySourceType.trusted_secondary_source,
    "communitySubmission": OpportunitySourceType.community_submission,
}
_SOURCE_TYPE_MODEL_TO_WIRE: dict[OpportunitySourceType, str] = {
    value: key for key, value in _SOURCE_TYPE_WIRE_TO_MODEL.items()
}

# ReliabilityLevel ("a".."f") and SourceVerificationStatus (pending/approved/
# blocked/expired) are spelled identically on both sides - no wire map needed,
# just validated against the enum directly.


def source_type_from_wire(value: str) -> OpportunitySourceType:
    try:
        return _SOURCE_TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown opportunity source type: {value!r}") from error


def source_type_to_wire(value: OpportunitySourceType) -> str:
    return _SOURCE_TYPE_MODEL_TO_WIRE[value]


class RegisterSourceRequest(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=500)
    type: str
    domain: str = Field(min_length=1, max_length=500)
    country: str = Field(default="Global", max_length=255)
    organization_id: str = Field(default="", max_length=255)
    trust_level: ReliabilityLevel = ReliabilityLevel.e
    accuracy_rate: float = Field(default=1.0, ge=0, le=1)
    parser_configuration: dict[str, str] | None = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        source_type_from_wire(value)
        return value


class ReviewSourceRequest(BaseModel):
    trust_level: ReliabilityLevel
    status: SourceVerificationStatus


class RecordAccessRequest(BaseModel):
    successful: bool


class SourceRegistryEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: OpportunitySourceType
    domain: str
    country: str
    organization_id: str
    trust_level: ReliabilityLevel
    trust_score: int
    verification_status: SourceVerificationStatus
    last_checked_at: datetime | None
    last_successful_access: datetime | None
    accuracy_rate: float
    correction_count: int
    rejection_count: int
    is_blocked: bool
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    parser_configuration: dict[str, str] | None

    @field_serializer("type")
    def _serialize_type(self, value: OpportunitySourceType, _info: Any) -> str:
        return source_type_to_wire(value)

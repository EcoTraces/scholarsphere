from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.collection import CollectionSourceType

_SOURCE_TYPE_WIRE_TO_MODEL: dict[str, CollectionSourceType] = {
    "manualAdministrator": CollectionSourceType.manualAdministrator,
    "providerSubmission": CollectionSourceType.providerSubmission,
    "officialApi": CollectionSourceType.officialApi,
    "approvedRss": CollectionSourceType.approvedRss,
    "structuredFeed": CollectionSourceType.structuredFeed,
    "controlledWebCollection": CollectionSourceType.controlledWebCollection,
    "userSubmission": CollectionSourceType.userSubmission,
}


def source_type_from_wire(value: str) -> CollectionSourceType:
    try:
        return _SOURCE_TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown collection source type: {value!r}") from error


class CollectOpportunityRequest(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    provider: str = Field(min_length=1, max_length=512)
    host_country: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=128)
    deadline: date | None = None
    application_open_date: date | None = None
    official_source_url: str = Field(min_length=1, max_length=2048)
    application_url: str = Field(min_length=1, max_length=2048)
    summary: str = ""

    source_type: str
    source_location: str = Field(min_length=1, max_length=2000)
    # Only consulted for non-automated source types, where it is a staff
    # record-keeping label, not a security gate - automated collection's
    # approval is always re-derived server-side from the real source
    # registry, never trusted from the client.
    approved_source: bool = False

    @field_validator("source_type")
    @classmethod
    def _validate_source_type(cls, value: str) -> str:
        source_type_from_wire(value)
        return value


class CollectedOpportunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    opportunity_id: str
    source_type: str
    source_location: str
    discovered_at: datetime
    collected_by_user_id: str | None
    automated: bool
    approved_source: bool
    verification_status: str

    @field_validator("id", "opportunity_id", mode="before")
    @classmethod
    def _stringify(cls, value: object) -> str:
        return str(value)

    @field_validator("source_type", mode="before")
    @classmethod
    def _unwrap_enum(cls, value: object) -> str:
        return value.value if hasattr(value, "value") else str(value)

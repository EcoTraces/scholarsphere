from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.provider_opportunity import (
    ProviderOpportunityDeliveryFormat,
    ProviderOpportunityFundingType,
    ProviderOpportunityType,
    ProviderOpportunityVerificationStatus,
)

_TYPE_WIRE_TO_MODEL: dict[str, ProviderOpportunityType] = {
    "scholarship": ProviderOpportunityType.scholarship,
    "fellowship": ProviderOpportunityType.fellowship,
    "internship": ProviderOpportunityType.internship,
    "conference": ProviderOpportunityType.conference,
    "summit": ProviderOpportunityType.summit,
    "webinar": ProviderOpportunityType.webinar,
    "exchangeProgram": ProviderOpportunityType.exchange_program,
    "researchGrant": ProviderOpportunityType.research_grant,
    "competition": ProviderOpportunityType.competition,
    "training": ProviderOpportunityType.training,
    "volunteering": ProviderOpportunityType.volunteering,
    "youthProgram": ProviderOpportunityType.youth_program,
    "onlineCourse": ProviderOpportunityType.online_course,
    "fundedEvent": ProviderOpportunityType.funded_event,
    "grant": ProviderOpportunityType.grant,
    "job": ProviderOpportunityType.job,
}
_TYPE_MODEL_TO_WIRE: dict[ProviderOpportunityType, str] = {
    value: key for key, value in _TYPE_WIRE_TO_MODEL.items()
}

_FUNDING_WIRE_TO_MODEL: dict[str, ProviderOpportunityFundingType] = {
    "fullyFunded": ProviderOpportunityFundingType.fully_funded,
    "partiallyFunded": ProviderOpportunityFundingType.partially_funded,
    "selfFunded": ProviderOpportunityFundingType.self_funded,
}
_FUNDING_MODEL_TO_WIRE: dict[ProviderOpportunityFundingType, str] = {
    value: key for key, value in _FUNDING_WIRE_TO_MODEL.items()
}

_DELIVERY_WIRE_TO_MODEL: dict[str, ProviderOpportunityDeliveryFormat] = {
    "online": ProviderOpportunityDeliveryFormat.online,
    "physical": ProviderOpportunityDeliveryFormat.physical,
    "hybrid": ProviderOpportunityDeliveryFormat.hybrid,
}
_DELIVERY_MODEL_TO_WIRE: dict[ProviderOpportunityDeliveryFormat, str] = {
    value: key for key, value in _DELIVERY_WIRE_TO_MODEL.items()
}

_VERIFICATION_WIRE_TO_MODEL: dict[str, ProviderOpportunityVerificationStatus] = {
    "pending": ProviderOpportunityVerificationStatus.pending,
    "verified": ProviderOpportunityVerificationStatus.verified,
    "verificationExpired": ProviderOpportunityVerificationStatus.verification_expired,
    "incomplete": ProviderOpportunityVerificationStatus.incomplete,
    "suspicious": ProviderOpportunityVerificationStatus.suspicious,
    "rejected": ProviderOpportunityVerificationStatus.rejected,
    "expired": ProviderOpportunityVerificationStatus.expired,
    "archived": ProviderOpportunityVerificationStatus.archived,
}
_VERIFICATION_MODEL_TO_WIRE: dict[ProviderOpportunityVerificationStatus, str] = {
    value: key for key, value in _VERIFICATION_WIRE_TO_MODEL.items()
}


def type_from_wire(value: str) -> ProviderOpportunityType:
    try:
        return _TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown opportunity type: {value!r}") from error


def funding_from_wire(value: str) -> ProviderOpportunityFundingType:
    try:
        return _FUNDING_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown funding type: {value!r}") from error


def delivery_from_wire(value: str) -> ProviderOpportunityDeliveryFormat:
    try:
        return _DELIVERY_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown delivery format: {value!r}") from error


class ProviderOpportunityCreate(BaseModel):
    provider_id: UUID
    title: str = Field(min_length=1, max_length=1000)
    host_institution: str = Field(min_length=1, max_length=512)
    host_country: str = Field(min_length=1, max_length=255)
    opportunity_type: str
    funding_type: str
    delivery_format: str
    deadline: date
    application_open_date: date
    official_source_url: str = Field(min_length=1, max_length=2048)
    application_url: str = Field(min_length=1, max_length=2048)
    eligible_nationalities: list[str] = Field(default_factory=list, max_length=200)
    study_levels: list[str] = Field(default_factory=list, max_length=50)
    fields_of_study: list[str] = Field(default_factory=list, max_length=50)
    summary: str = Field(min_length=1, max_length=10000)
    benefits: list[str] = Field(default_factory=list, max_length=50)
    eligibility_requirements: list[str] = Field(default_factory=list, max_length=50)
    required_documents: list[str] = Field(default_factory=list, max_length=50)
    application_procedure: list[str] = Field(default_factory=list, max_length=50)
    language_requirements: list[str] = Field(default_factory=list, max_length=50)
    minimum_age: int | None = Field(default=None, ge=0, le=120)
    maximum_age: int | None = Field(default=None, ge=0, le=120)
    work_experience_years_required: float | None = Field(default=None, ge=0)
    contact_information: str = Field(min_length=1, max_length=2000)
    available_positions: int | None = Field(default=None, ge=0)
    application_fee: float | None = Field(default=None, ge=0)

    @field_validator("opportunity_type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        type_from_wire(value)
        return value

    @field_validator("funding_type")
    @classmethod
    def _validate_funding(cls, value: str) -> str:
        funding_from_wire(value)
        return value

    @field_validator("delivery_format")
    @classmethod
    def _validate_delivery(cls, value: str) -> str:
        delivery_from_wire(value)
        return value

    @field_validator("deadline")
    @classmethod
    def _validate_deadline(cls, value: date, info: Any) -> date:
        opening = info.data.get("application_open_date")
        if opening is not None and value <= opening:
            raise ValueError("The deadline must be after the application opening date.")
        return value


class ProviderOpportunityVerificationRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    notes: str | None = Field(default=None, max_length=2000)
    source_checked: bool
    application_link_checked: bool
    deadline_checked: bool
    duplicate_checked: bool


class ProviderOpportunityPublicationRequest(BaseModel):
    published: bool


class ProviderOpportunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_id: UUID
    provider_name: str
    submitted_by: str
    title: str
    host_institution: str
    host_country: str
    opportunity_type: ProviderOpportunityType
    funding_type: ProviderOpportunityFundingType
    delivery_format: ProviderOpportunityDeliveryFormat
    deadline: date
    application_open_date: date
    official_source_url: str
    application_url: str
    eligible_nationalities: list[str]
    study_levels: list[str]
    fields_of_study: list[str]
    summary: str
    benefits: list[str]
    eligibility_requirements: list[str]
    required_documents: list[str]
    application_procedure: list[str]
    language_requirements: list[str]
    minimum_age: int | None
    maximum_age: int | None
    work_experience_years_required: float | None
    contact_information: str
    available_positions: int | None
    application_fee: float | None
    verification_status: ProviderOpportunityVerificationStatus
    publication_status: str
    last_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("opportunity_type")
    def _serialize_type(self, value: ProviderOpportunityType, _info: Any) -> str:
        return _TYPE_MODEL_TO_WIRE[value]

    @field_serializer("funding_type")
    def _serialize_funding(self, value: ProviderOpportunityFundingType, _info: Any) -> str:
        return _FUNDING_MODEL_TO_WIRE[value]

    @field_serializer("delivery_format")
    def _serialize_delivery(self, value: ProviderOpportunityDeliveryFormat, _info: Any) -> str:
        return _DELIVERY_MODEL_TO_WIRE[value]

    @field_serializer("verification_status")
    def _serialize_verification(
        self, value: ProviderOpportunityVerificationStatus, _info: Any
    ) -> str:
        return _VERIFICATION_MODEL_TO_WIRE[value]

    @field_serializer("publication_status")
    def _serialize_publication(self, value: Any, _info: Any) -> str:
        return value.value if hasattr(value, "value") else value


class ProviderOpportunityPage(BaseModel):
    items: list[ProviderOpportunityRead]
    total: int
    page: int
    page_size: int

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.taxonomy import TaxonomyType

_TYPE_WIRE_TO_MODEL: dict[str, TaxonomyType] = {
    "country": TaxonomyType.country,
    "region": TaxonomyType.region,
    "continent": TaxonomyType.continent,
    "nationality": TaxonomyType.nationality,
    "institution": TaxonomyType.institution,
    "organization": TaxonomyType.organization,
    "degreeLevel": TaxonomyType.degree_level,
    "academicField": TaxonomyType.academic_field,
    "opportunityType": TaxonomyType.opportunity_type,
    "fundingType": TaxonomyType.funding_type,
    "language": TaxonomyType.language,
    "currency": TaxonomyType.currency,
    "qualification": TaxonomyType.qualification,
    "industrySector": TaxonomyType.industry_sector,
}
_TYPE_MODEL_TO_WIRE: dict[TaxonomyType, str] = {
    value: key for key, value in _TYPE_WIRE_TO_MODEL.items()
}


def taxonomy_type_from_wire(value: str) -> TaxonomyType:
    try:
        return _TYPE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown taxonomy type: {value!r}") from error


def taxonomy_type_to_wire(value: TaxonomyType) -> str:
    return _TYPE_MODEL_TO_WIRE[value]


class SaveTaxonomyTermRequest(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    type: str
    canonical_name: str = Field(min_length=1, max_length=500)
    code: str | None = Field(default=None, max_length=64)
    synonyms: list[str] = Field(default_factory=list, max_length=200)
    parent_id: str | None = None
    active: bool = True
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        taxonomy_type_from_wire(value)
        return value


class MergeTaxonomyRequest(BaseModel):
    canonical_id: str = Field(min_length=1, max_length=255)
    duplicate_ids: list[str] = Field(min_length=1, max_length=100)


class TaxonomyTermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: TaxonomyType
    canonical_name: str
    code: str | None
    synonyms: list[str]
    parent_id: str | None
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime

    @field_serializer("type")
    def _serialize_type(self, value: TaxonomyType, _info: Any) -> str:
        return taxonomy_type_to_wire(value)


class TaxonomyVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    created_at: datetime
    created_by: str
    reason: str
    term_count: int

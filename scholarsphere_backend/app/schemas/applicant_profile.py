from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.applicant_profile import EmploymentStatus, EnglishTestStatus, PassportStatus

_ENGLISH_TEST_WIRE_TO_MODEL: dict[str, EnglishTestStatus] = {
    "notTaken": EnglishTestStatus.not_taken,
    "planned": EnglishTestStatus.planned,
    "completed": EnglishTestStatus.completed,
    "notRequired": EnglishTestStatus.not_required,
}
_ENGLISH_TEST_MODEL_TO_WIRE: dict[EnglishTestStatus, str] = {
    value: key for key, value in _ENGLISH_TEST_WIRE_TO_MODEL.items()
}

_PASSPORT_WIRE_TO_MODEL: dict[str, PassportStatus] = {
    "unavailable": PassportStatus.unavailable,
    "applied": PassportStatus.applied,
    "valid": PassportStatus.valid,
    "expired": PassportStatus.expired,
}
_PASSPORT_MODEL_TO_WIRE: dict[PassportStatus, str] = {
    value: key for key, value in _PASSPORT_WIRE_TO_MODEL.items()
}

_EMPLOYMENT_WIRE_TO_MODEL: dict[str, EmploymentStatus] = {
    "student": EmploymentStatus.student,
    "employed": EmploymentStatus.employed,
    "selfEmployed": EmploymentStatus.self_employed,
    "unemployed": EmploymentStatus.unemployed,
    "other": EmploymentStatus.other,
}
_EMPLOYMENT_MODEL_TO_WIRE: dict[EmploymentStatus, str] = {
    value: key for key, value in _EMPLOYMENT_WIRE_TO_MODEL.items()
}


def english_test_status_from_wire(value: str) -> EnglishTestStatus:
    try:
        return _ENGLISH_TEST_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown English test status: {value!r}") from error


def passport_status_from_wire(value: str) -> PassportStatus:
    try:
        return _PASSPORT_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown passport status: {value!r}") from error


def employment_status_from_wire(value: str) -> EmploymentStatus:
    try:
        return _EMPLOYMENT_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown employment status: {value!r}") from error


class ApplicantProfileUpdate(BaseModel):
    """Full-replace upsert - matches the Dart profile screen's whole-form save."""

    full_name: str = Field(min_length=1, max_length=255)
    nationality: str = Field(default="", max_length=255)
    country_of_residence: str = Field(default="", max_length=255)
    date_of_birth: date | None = None
    gender: str = Field(default="", max_length=64)
    highest_qualification: str = Field(default="", max_length=255)
    degree_field: str = Field(default="", max_length=255)
    academic_classification: str = Field(default="", max_length=255)
    graduation_year: int | None = Field(default=None, ge=1900, le=2200)
    work_experience_years: float = Field(default=0, ge=0, le=80)
    preferred_study_levels: list[str] = Field(default_factory=list, max_length=50)
    preferred_countries: list[str] = Field(default_factory=list, max_length=250)
    areas_of_interest: list[str] = Field(default_factory=list, max_length=50)
    english_test_status: str = "notTaken"
    passport_status: str = "unavailable"
    employment_status: str = "student"
    funding_preferences: list[str] = Field(default_factory=list, max_length=50)
    special_eligibility_categories: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("english_test_status")
    @classmethod
    def _validate_english_test(cls, value: str) -> str:
        english_test_status_from_wire(value)
        return value

    @field_validator("passport_status")
    @classmethod
    def _validate_passport(cls, value: str) -> str:
        passport_status_from_wire(value)
        return value

    @field_validator("employment_status")
    @classmethod
    def _validate_employment(cls, value: str) -> str:
        employment_status_from_wire(value)
        return value


class ApplicantProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    full_name: str
    nationality: str
    country_of_residence: str
    date_of_birth: date | None
    gender: str
    highest_qualification: str
    degree_field: str
    academic_classification: str
    graduation_year: int | None
    work_experience_years: float
    preferred_study_levels: list[str]
    preferred_countries: list[str]
    areas_of_interest: list[str]
    english_test_status: EnglishTestStatus
    passport_status: PassportStatus
    employment_status: EmploymentStatus
    funding_preferences: list[str]
    special_eligibility_categories: list[str]
    created_at: datetime
    updated_at: datetime

    @field_serializer("english_test_status")
    def _serialize_english_test(self, value: EnglishTestStatus, _info: Any) -> str:
        return _ENGLISH_TEST_MODEL_TO_WIRE[value]

    @field_serializer("passport_status")
    def _serialize_passport(self, value: PassportStatus, _info: Any) -> str:
        return _PASSPORT_MODEL_TO_WIRE[value]

    @field_serializer("employment_status")
    def _serialize_employment(self, value: EmploymentStatus, _info: Any) -> str:
        return _EMPLOYMENT_MODEL_TO_WIRE[value]


class ApplicantProfilePage(BaseModel):
    items: list[ApplicantProfileRead]
    total: int
    page: int
    page_size: int

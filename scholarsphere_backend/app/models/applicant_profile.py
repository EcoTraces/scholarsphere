import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.external_opportunity import JSONType


class EnglishTestStatus(str, enum.Enum):
    not_taken = "not_taken"
    planned = "planned"
    completed = "completed"
    not_required = "not_required"


class PassportStatus(str, enum.Enum):
    unavailable = "unavailable"
    applied = "applied"
    valid = "valid"
    expired = "expired"


class EmploymentStatus(str, enum.Enum):
    student = "student"
    employed = "employed"
    self_employed = "self_employed"
    unemployed = "unemployed"
    other = "other"


class ApplicantProfile(Base):
    """One row per applicant - a settings/profile table, not an event table,

    so the Firebase uid is the primary key itself, matching
    NotificationPreferences' identical shape.

    ``documents`` is deliberately not modeled here: the Dart domain's
    ``ProfileDocument`` is metadata-only (name/type/timestamp, no file
    path or URL), so there is nothing real to persist yet - real file
    storage belongs to a dedicated Documents feature, not bolted onto
    profile fields. The API always returns an empty documents list.
    """

    __tablename__ = "applicant_profiles"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    nationality: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    country_of_residence: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    highest_qualification: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    degree_field: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    academic_classification: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    work_experience_years: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    preferred_study_levels: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    preferred_countries: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    areas_of_interest: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    english_test_status: Mapped[EnglishTestStatus] = mapped_column(
        Enum(EnglishTestStatus, native_enum=False),
        default=EnglishTestStatus.not_taken,
        nullable=False,
    )
    passport_status: Mapped[PassportStatus] = mapped_column(
        Enum(PassportStatus, native_enum=False),
        default=PassportStatus.unavailable,
        nullable=False,
    )
    employment_status: Mapped[EmploymentStatus] = mapped_column(
        Enum(EmploymentStatus, native_enum=False),
        default=EmploymentStatus.student,
        nullable=False,
    )
    funding_preferences: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    special_eligibility_categories: Mapped[list[str]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

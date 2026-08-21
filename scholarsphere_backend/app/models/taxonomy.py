import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.external_opportunity import JSONType


class TaxonomyType(str, enum.Enum):
    country = "country"
    region = "region"
    continent = "continent"
    nationality = "nationality"
    institution = "institution"
    organization = "organization"
    degree_level = "degree_level"
    academic_field = "academic_field"
    opportunity_type = "opportunity_type"
    funding_type = "funding_type"
    language = "language"
    currency = "currency"
    qualification = "qualification"
    industry_sector = "industry_sector"


class TaxonomyTerm(Base):
    __tablename__ = "taxonomy_terms"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[TaxonomyType] = mapped_column(Enum(TaxonomyType, native_enum=False), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64))
    synonyms: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("taxonomy_terms.id", ondelete="SET NULL")
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TaxonomyVersion(Base):
    """One row per save()/merge() call, matching DemoTaxonomyRepository's

    single global `_version` counter shared across every taxonomy type -
    not scoped per-type.
    """

    __tablename__ = "taxonomy_versions"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    term_count: Mapped[int] = mapped_column(Integer, nullable=False)

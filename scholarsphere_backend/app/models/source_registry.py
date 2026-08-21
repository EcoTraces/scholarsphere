import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.external_opportunity import JSONType


class OpportunitySourceType(str, enum.Enum):
    official_university_website = "official_university_website"
    official_government_portal = "official_government_portal"
    embassy_website = "embassy_website"
    foundation_website = "foundation_website"
    international_organization = "international_organization"
    official_application_portal = "official_application_portal"
    approved_api = "approved_api"
    approved_rss_feed = "approved_rss_feed"
    verified_provider_submission = "verified_provider_submission"
    trusted_secondary_source = "trusted_secondary_source"
    community_submission = "community_submission"


class ReliabilityLevel(str, enum.Enum):
    a = "a"
    b = "b"
    c = "c"
    d = "d"
    e = "e"
    f = "f"


class SourceVerificationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    blocked = "blocked"
    expired = "expired"


class SourceRegistryEntry(Base):
    """Admin-curated directory of trusted external sources, reviewed and

    trust-scored by staff (governance concern). Deliberately a separate
    table from `opportunity_sources` (app/models/external_opportunity.py),
    which already powers the live ingestion pipeline (sync bookkeeping,
    auth type, base URL) with a different, leaner shape - the two model
    unrelated capabilities that happen to share the word "source".
    """

    __tablename__ = "source_registry_entries"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[OpportunitySourceType] = mapped_column(
        Enum(OpportunitySourceType, native_enum=False), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_domain: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(255), nullable=False, default="Global")
    organization_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    trust_level: Mapped[ReliabilityLevel] = mapped_column(
        Enum(ReliabilityLevel, native_enum=False), nullable=False
    )
    trust_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_status: Mapped[SourceVerificationStatus] = mapped_column(
        Enum(SourceVerificationStatus, native_enum=False),
        default=SourceVerificationStatus.pending,
        nullable=False,
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_access: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accuracy_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    correction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parser_configuration: Mapped[dict[str, str] | None] = mapped_column(JSONType)

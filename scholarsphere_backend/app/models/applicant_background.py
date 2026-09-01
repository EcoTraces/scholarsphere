import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class BackgroundEntryCategory(str, enum.Enum):
    """The single source of truth every premium document generator reads

    from - never anything an AI provider invents. See
    app/services/document_generation.py's module docstring for the
    grounding rule this table exists to enforce.
    """

    education = "education"
    work_experience = "work_experience"
    project = "project"
    publication = "publication"
    award = "award"
    leadership_community = "leadership_community"
    skill = "skill"
    reference = "reference"


class ApplicantBackgroundEntry(Base):
    """One row per real, user-entered fact (a degree, a job, a project, an

    award, a publication, a leadership/volunteering role, a skill, or a
    referee) that premium document generation is allowed to draw on.
    Consolidated into one table with a ``category`` discriminator and a
    ``details`` JSON payload for category-specific fields (e.g. a
    publication's ``authors``/``venue``/``url``, a skill's
    ``proficiency``, a reference's ``email``/``phone``) rather than eight
    near-identical tables - the same "one flexible JSON payload, always
    read/written as a unit" shape already used by
    ``ApplicationGuidancePlan.items`` (app/models/guidance.py).

    Entry ownership/visibility is identical to ``ApplicantDocument`` and
    ``ApplicantProfile``: the Firebase uid is the only access key, no
    staff read path exists here, and none should be added without the
    same deliberate review that would apply to widening
    ``applicant-documents/`` Storage rules (Coding_Rules.md SS6).
    """

    __tablename__ = "applicant_background_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[BackgroundEntryCategory] = mapped_column(
        Enum(BackgroundEntryCategory, native_enum=False), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    organization: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    details: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base


class ApplicantCategory(str, enum.Enum):
    """Drives which document types/checklist items a workspace gets - see

    app/services/category_workflow.py's ``CATEGORY_WORKFLOWS`` registry.
    Adding a tenth category is a registry entry, not new branching logic
    scattered through routes/services.
    """

    undergraduate = "undergraduate"
    postgraduate = "postgraduate"
    phd = "phd"
    fellowship = "fellowship"
    research_scholarship = "research_scholarship"
    professional_scholarship = "professional_scholarship"
    exchange_mobility = "exchange_mobility"
    short_course_training = "short_course_training"
    internship_graduate_opportunity = "internship_graduate_opportunity"


class PremiumWorkspace(Base):
    """The premium "Application Preparation" workspace for one tracked

    opportunity. Deliberately anchored to the existing free-tier
    ``Application`` row (app/models/application.py) rather than a bare
    ``opportunity_id`` - the workspace *is* the premium layer on top of an
    opportunity the applicant already tracks for free, not a parallel
    concept. One workspace per tracked application
    (``UniqueConstraint(application_id)``).
    """

    __tablename__ = "premium_workspaces"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_premium_workspace_application"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[ApplicantCategory] = mapped_column(
        Enum(ApplicantCategory, native_enum=False), nullable=False
    )
    target_university: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    target_program: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RequirementMatchStatus(str, enum.Enum):
    match = "match"
    partial_match = "partial_match"
    missing = "missing"
    needs_verification = "needs_verification"


class RequirementMatch(Base):
    """One row per real requirement extracted from the target opportunity's

    own eligibility/requirement text, matched against the applicant's
    actual profile/background data - see
    app/services/requirement_matching.py. Never asserts eligibility the
    underlying data can't support: an ambiguous requirement is
    ``needs_verification``, not guessed into ``match``.
    """

    __tablename__ = "requirement_matches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("premium_workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RequirementMatchStatus] = mapped_column(
        Enum(RequirementMatchStatus, native_enum=False), nullable=False
    )
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ChecklistItemStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    done = "done"
    not_applicable = "not_applicable"


class PersonalizedChecklistItem(Base):
    """The premium checklist - generated from the workspace's category

    workflow (app/services/category_workflow.py) plus its requirement
    matches, distinct from the free-tier ``ApplicationGuidancePlan``
    (app/models/guidance.py), which this feature does not replace or
    duplicate.
    """

    __tablename__ = "personalized_checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("premium_workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_key: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ChecklistItemStatus] = mapped_column(
        Enum(ChecklistItemStatus, native_enum=False),
        default=ChecklistItemStatus.not_started,
        nullable=False,
    )
    auto_generated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

import enum
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.external_opportunity import JSONType


class GuidanceItemType(str, enum.Enum):
    application_step = "application_step"
    required_document = "required_document"
    profile_information = "profile_information"
    curriculum_vitae = "curriculum_vitae"
    personal_statement = "personal_statement"
    research_proposal = "research_proposal"
    recommendation_letter = "recommendation_letter"
    interview_preparation = "interview_preparation"
    submission = "submission"
    follow_up = "follow_up"


class GuidanceItemStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    ready = "ready"
    missing = "missing"
    confirmed = "confirmed"
    not_applicable = "not_applicable"


class ApplicationGuidancePlan(Base):
    """Items, recommendation letters, and submission confirmation are

    stored as JSON blobs on the plan row rather than child tables: they
    are always read and written as one unit per screen load (matching
    DemoApplicationGuidanceRepository's whole-plan copyWith semantics),
    and never queried independently of their parent plan.
    """

    __tablename__ = "guidance_plans"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    opportunity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    items: Mapped[list[dict]] = mapped_column(JSONType, default=list, nullable=False)
    recommendation_letters: Mapped[list[dict]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    timeline_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    follow_up_reminders: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submission_confirmation: Mapped[dict | None] = mapped_column(JSONType)

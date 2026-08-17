import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class ApplicationStage(str, enum.Enum):
    interested = "interested"
    saved = "saved"
    preparing_documents = "preparing_documents"
    application_started = "application_started"
    application_submitted = "application_submitted"
    interview_stage = "interview_stage"
    waiting_for_decision = "waiting_for_decision"
    accepted = "accepted"
    rejected = "rejected"
    withdrawn = "withdrawn"


class Application(Base):
    """An applicant's tracked opportunity: saved, applied to, or further along.

    ``opportunity_title``/``provider_name``/``deadline`` are snapshotted from
    the ``ExternalOpportunity`` at save time and never resynced - the applicant
    is tracking the opportunity as it was when they saved it, matching the
    Flutter client's ``ApplicationRecord.saved`` factory.
    """

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "opportunity_id", name="uq_application_user_opportunity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("external_opportunities.id", ondelete="RESTRICT"), nullable=False
    )
    opportunity_title: Mapped[str] = mapped_column(String(1000), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(512), nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date)
    stage: Mapped[ApplicationStage] = mapped_column(
        Enum(ApplicationStage, native_enum=False), default=ApplicationStage.saved, nullable=False
    )
    application_date: Mapped[date | None] = mapped_column(Date)
    application_reference_number: Mapped[str | None] = mapped_column(String(255))
    missing_documents: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    interview_date: Mapped[date | None] = mapped_column(Date)
    personal_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    result_date: Mapped[date | None] = mapped_column(Date)
    scholarship_value: Mapped[float | None] = mapped_column(Float)
    follow_up_actions: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

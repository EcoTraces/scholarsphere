import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class ReportedEntityType(str, enum.Enum):
    opportunity = "opportunity"
    provider = "provider"
    user = "user"


class ModerationReportType(str, enum.Enum):
    scam = "scam"
    incorrect_deadline = "incorrect_deadline"
    broken_link = "broken_link"
    duplicate_listing = "duplicate_listing"
    misleading_content = "misleading_content"
    inappropriate_content = "inappropriate_content"
    outdated_content = "outdated_content"
    harmful_content = "harmful_content"


class ModerationStatus(str, enum.Enum):
    submitted = "submitted"
    under_review = "under_review"
    evidence_required = "evidence_required"
    escalated = "escalated"
    resolved = "resolved"
    rejected = "rejected"
    content_corrected = "content_corrected"
    content_removed = "content_removed"
    provider_suspended = "provider_suspended"
    closed = "closed"


CLOSED_STATUSES = frozenset(
    {
        ModerationStatus.resolved,
        ModerationStatus.rejected,
        ModerationStatus.content_corrected,
        ModerationStatus.content_removed,
        ModerationStatus.provider_suspended,
        ModerationStatus.closed,
    }
)


class ModerationCase(Base):
    """A content/entity report and its lifecycle.

    ``entity_id`` is deliberately a plain string, not a FK: it may be a real
    opportunity UUID, a real provider UUID, or a Firebase uid (for
    ``entity_type == user``, which has no local table - identity lives in
    Firebase). Existence is checked in the route for opportunity/provider,
    not enforced by the schema.
    """

    __tablename__ = "moderation_cases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reporter_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[ReportedEntityType] = mapped_column(
        Enum(ReportedEntityType, native_enum=False), nullable=False
    )
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    report_type: Mapped[ModerationReportType] = mapped_column(
        Enum(ModerationReportType, native_enum=False), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list, nullable=False)
    status: Mapped[ModerationStatus] = mapped_column(
        Enum(ModerationStatus, native_enum=False),
        default=ModerationStatus.submitted,
        nullable=False,
    )
    assigned_moderator_id: Mapped[str | None] = mapped_column(String(255))
    moderation_notes: Mapped[str | None] = mapped_column(Text)
    temporarily_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    appeal_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ModerationHistoryEntry(Base):
    __tablename__ = "moderation_case_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("moderation_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ModerationStatus] = mapped_column(
        Enum(ModerationStatus, native_enum=False), nullable=False
    )
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ModerationWarning(Base):
    __tablename__ = "moderation_warnings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[ReportedEntityType] = mapped_column(
        Enum(ReportedEntityType, native_enum=False), nullable=False
    )
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    issued_by: Mapped[str] = mapped_column(String(255), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("moderation_cases.id", ondelete="RESTRICT"), nullable=False
    )

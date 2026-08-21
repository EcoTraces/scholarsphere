import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.external_opportunity import JSONType


class SupportTicketCategory(str, enum.Enum):
    account_access = "account_access"
    profile_problem = "profile_problem"
    opportunity_information = "opportunity_information"
    eligibility_result = "eligibility_result"
    application_tracking = "application_tracking"
    document_upload = "document_upload"
    notification_problem = "notification_problem"
    provider_verification = "provider_verification"
    fraud_report = "fraud_report"
    privacy_request = "privacy_request"
    technical_issue = "technical_issue"
    billing_issue = "billing_issue"
    general_inquiry = "general_inquiry"


class SupportTicketPriority(str, enum.Enum):
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"


class SupportTicketStatus(str, enum.Enum):
    open = "open"
    assigned = "assigned"
    in_progress = "in_progress"
    waiting_for_user = "waiting_for_user"
    escalated = "escalated"
    resolved = "resolved"
    closed = "closed"
    reopened = "reopened"


class KnowledgeContentType(str, enum.Enum):
    frequently_asked_question = "frequently_asked_question"
    article = "article"
    tutorial = "tutorial"
    application_help = "application_help"


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    requester_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[SupportTicketCategory] = mapped_column(
        Enum(SupportTicketCategory, native_enum=False), nullable=False
    )
    priority: Mapped[SupportTicketPriority] = mapped_column(
        Enum(SupportTicketPriority, native_enum=False), nullable=False
    )
    status: Mapped[SupportTicketStatus] = mapped_column(
        Enum(SupportTicketStatus, native_enum=False),
        default=SupportTicketStatus.open,
        nullable=False,
    )
    assigned_agent_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    first_response_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolution_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    escalation_reason: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    attachments: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list, nullable=False)
    is_agent: Mapped[bool] = mapped_column(Boolean, nullable=False)


class SupportInternalNote(Base):
    __tablename__ = "support_internal_notes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SupportTicketEvent(Base):
    __tablename__ = "support_ticket_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[SupportTicketStatus] = mapped_column(
        Enum(SupportTicketStatus, native_enum=False), nullable=False
    )
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)


class KnowledgeArticle(Base):
    """Client-chosen id (upsert), matching NotificationTemplate's precedent."""

    __tablename__ = "knowledge_articles"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[KnowledgeContentType] = mapped_column(
        Enum(KnowledgeContentType, native_enum=False), nullable=False
    )
    category: Mapped[SupportTicketCategory] = mapped_column(
        Enum(SupportTicketCategory, native_enum=False), nullable=False
    )
    language_code: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    keywords: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)


class SupportResponseTemplate(Base):
    __tablename__ = "support_response_templates"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[SupportTicketCategory] = mapped_column(
        Enum(SupportTicketCategory, native_enum=False), nullable=False
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class SatisfactionSurvey(Base):
    """PK is ticket_id: only the ticket's own requester may ever survey it

    (enforced in the route), so (ticket_id, user_id) collapses to a single
    natural key in practice - one survey per ticket.
    """

    __tablename__ = "satisfaction_surveys"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(Text)

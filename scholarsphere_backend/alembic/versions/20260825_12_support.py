"""Create support ticketing, knowledge base, and survey tables.

Revision ID: 20260825_12
Revises: 20260824_11
Create Date: 2026-08-25
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260825_12"
down_revision: str | None = "20260824_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

support_ticket_category = sa.Enum(
    "account_access", "profile_problem", "opportunity_information", "eligibility_result",
    "application_tracking", "document_upload", "notification_problem", "provider_verification",
    "fraud_report", "privacy_request", "technical_issue", "billing_issue", "general_inquiry",
    name="supportticketcategory", native_enum=False,
)
support_ticket_priority = sa.Enum(
    "low", "normal", "high", "urgent",
    name="supportticketpriority", native_enum=False,
)
support_ticket_status = sa.Enum(
    "open", "assigned", "in_progress", "waiting_for_user", "escalated",
    "resolved", "closed", "reopened",
    name="supportticketstatus", native_enum=False,
)
knowledge_content_type = sa.Enum(
    "frequently_asked_question", "article", "tutorial", "application_help",
    name="knowledgecontenttype", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requester_id", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("category", support_ticket_category, nullable=False),
        sa.Column("priority", support_ticket_priority, nullable=False),
        sa.Column("status", support_ticket_status, nullable=False),
        sa.Column("assigned_agent_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("first_response_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("escalation_reason", sa.Text()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_tickets_requester_id", "support_tickets", ["requester_id"])
    op.create_table(
        "support_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("attachments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_agent", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_messages_ticket_id", "support_messages", ["ticket_id"])
    op.create_table(
        "support_internal_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.String(255), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_internal_notes_ticket_id", "support_internal_notes", ["ticket_id"])
    op.create_table(
        "support_ticket_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("status", support_ticket_status, nullable=False),
        sa.Column("actor_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_ticket_history_ticket_id", "support_ticket_history", ["ticket_id"])
    op.create_table(
        "knowledge_articles",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("type", knowledge_content_type, nullable=False),
        sa.Column("category", support_ticket_category, nullable=False),
        sa.Column("language_code", sa.String(16), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "support_response_templates",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", support_ticket_category, nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "satisfaction_surveys",
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ticket_id"),
    )


def downgrade() -> None:
    op.drop_table("satisfaction_surveys")
    op.drop_table("support_response_templates")
    op.drop_table("knowledge_articles")
    op.drop_index("ix_support_ticket_history_ticket_id", table_name="support_ticket_history")
    op.drop_table("support_ticket_history")
    op.drop_index("ix_support_internal_notes_ticket_id", table_name="support_internal_notes")
    op.drop_table("support_internal_notes")
    op.drop_index("ix_support_messages_ticket_id", table_name="support_messages")
    op.drop_table("support_messages")
    op.drop_index("ix_support_tickets_requester_id", table_name="support_tickets")
    op.drop_table("support_tickets")

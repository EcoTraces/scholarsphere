"""Create Premium Application-Preparation Platform tables: plans, payments,

payment events, subscriptions, refunds, entitlements, AI usage tracking,
applicant background entries, application-preparation workspaces,
requirement matches, personalized checklist items, and premium documents
with append-only version history.

Revision ID: 20260901_33
Revises: 20260914_32
Create Date: 2026-09-01
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260901_33"
down_revision: str | None = "20260914_32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

billing_interval = sa.Enum(
    "one_time", "monthly", "yearly", name="billinginterval", native_enum=False
)
payment_status = sa.Enum(
    "pending",
    "processing",
    "success",
    "failed",
    "cancelled",
    "refunded",
    "expired",
    "disputed",
    name="paymentstatus",
    native_enum=False,
)
subscription_status = sa.Enum(
    "active",
    "trialing",
    "past_due",
    "canceled",
    "incomplete",
    name="subscriptionstatus",
    native_enum=False,
)
refund_status = sa.Enum(
    "pending", "succeeded", "failed", name="refundstatus", native_enum=False
)
entitlement_status = sa.Enum(
    "active", "expired", "revoked", name="entitlementstatus", native_enum=False
)
ai_usage_status = sa.Enum(
    "success",
    "failed",
    "rate_limited",
    "quota_exceeded",
    name="aiusagestatus",
    native_enum=False,
)
background_entry_category = sa.Enum(
    "education",
    "work_experience",
    "project",
    "publication",
    "award",
    "leadership_community",
    "skill",
    "reference",
    name="backgroundentrycategory",
    native_enum=False,
)
applicant_category = sa.Enum(
    "undergraduate",
    "postgraduate",
    "phd",
    "fellowship",
    "research_scholarship",
    "professional_scholarship",
    "exchange_mobility",
    "short_course_training",
    "internship_graduate_opportunity",
    name="applicantcategory",
    native_enum=False,
)
requirement_match_status = sa.Enum(
    "match",
    "partial_match",
    "missing",
    "needs_verification",
    name="requirementmatchstatus",
    native_enum=False,
)
checklist_item_status = sa.Enum(
    "not_started",
    "in_progress",
    "done",
    "not_applicable",
    name="checklistitemstatus",
    native_enum=False,
)
document_kind = sa.Enum(
    "cv_academic",
    "cv_professional",
    "cv_scholarship",
    "sop",
    "personal_statement",
    "motivation_letter",
    "study_plan",
    "research_proposal",
    "fellowship_leadership_statement",
    "fellowship_personal_statement",
    "fellowship_impact_statement",
    "fellowship_essay",
    name="documentkind",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "premium_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("billing_interval", billing_interval, nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_premium_plans_code", "premium_plans", ["code"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("provider_transaction_id", sa.String(255), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("payment_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["premium_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])
    op.create_index("ix_payments_plan_id", "payments", ["plan_id"])
    op.create_index(
        "ix_payments_provider_transaction_id", "payments", ["provider_transaction_id"]
    )

    op.create_table(
        "payment_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("provider_event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_result", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "provider_event_id", name="uq_payment_event_provider_event"
        ),
    )
    op.create_index("ix_payment_events_payment_id", "payment_events", ["payment_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("status", subscription_status, nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("provider_subscription_id", sa.String(255), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["premium_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])

    op.create_table(
        "refunds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", refund_status, nullable=False),
        sa.Column("provider_refund_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refunds_payment_id", "refunds", ["payment_id"])

    op.create_table(
        "entitlements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("feature_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_payment_id", sa.Uuid(), nullable=True),
        sa.Column("status", entitlement_status, nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["premium_plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_payment_id", name="uq_entitlement_source_payment"),
    )
    op.create_index("ix_entitlements_user_id", "entitlements", ["user_id"])
    op.create_index("ix_entitlements_plan_id", "entitlements", ["plan_id"])
    op.create_index("ix_entitlements_status", "entitlements", ["status"])

    op.create_table(
        "ai_usage_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("feature", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("status", ai_usage_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_usage_records_user_id", "ai_usage_records", ["user_id"])
    op.create_index("ix_ai_usage_records_feature", "ai_usage_records", ["feature"])
    op.create_index("ix_ai_usage_records_created_at", "ai_usage_records", ["created_at"])

    op.create_table(
        "usage_limits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feature", sa.String(64), nullable=False),
        sa.Column("plan_code", sa.String(64), nullable=True),
        sa.Column("limit_per_day", sa.Integer(), nullable=True),
        sa.Column("limit_per_month", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feature", "plan_code", name="uq_usage_limit_feature_plan"),
    )

    op.create_table(
        "applicant_background_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("category", background_entry_category, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("organization", sa.String(500), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_applicant_background_entries_user_id", "applicant_background_entries", ["user_id"]
    )
    op.create_index(
        "ix_applicant_background_entries_category", "applicant_background_entries", ["category"]
    )

    op.create_table(
        "premium_workspaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("category", applicant_category, nullable=False),
        sa.Column("target_university", sa.String(500), nullable=False),
        sa.Column("target_program", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="uq_premium_workspace_application"),
    )
    op.create_index("ix_premium_workspaces_user_id", "premium_workspaces", ["user_id"])

    op.create_table(
        "requirement_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("status", requirement_match_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["premium_workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_requirement_matches_workspace_id", "requirement_matches", ["workspace_id"])

    op.create_table(
        "personalized_checklist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("item_key", sa.String(128), nullable=False),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("status", checklist_item_status, nullable=False),
        sa.Column("auto_generated", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["premium_workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_personalized_checklist_items_workspace_id",
        "personalized_checklist_items",
        ["workspace_id"],
    )

    op.create_table(
        "premium_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
        sa.Column("kind", document_kind, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("latest_version_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["premium_workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_premium_documents_user_id", "premium_documents", ["user_id"])
    op.create_index("ix_premium_documents_workspace_id", "premium_documents", ["workspace_id"])

    op.create_table(
        "premium_document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_ai_generated", sa.Boolean(), nullable=False),
        sa.Column("ats_score", sa.Float(), nullable=True),
        sa.Column("ats_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("quality_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["premium_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "version_number", name="uq_premium_document_version_number"
        ),
    )
    op.create_index(
        "ix_premium_document_versions_document_id", "premium_document_versions", ["document_id"]
    )


def downgrade() -> None:
    op.drop_table("premium_document_versions")
    op.drop_table("premium_documents")
    op.drop_table("personalized_checklist_items")
    op.drop_table("requirement_matches")
    op.drop_table("premium_workspaces")
    op.drop_table("applicant_background_entries")
    op.drop_table("usage_limits")
    op.drop_table("ai_usage_records")
    op.drop_table("entitlements")
    op.drop_table("refunds")
    op.drop_table("subscriptions")
    op.drop_table("payment_events")
    op.drop_table("payments")
    op.drop_table("premium_plans")

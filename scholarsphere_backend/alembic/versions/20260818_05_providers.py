"""Create provider organization tables.

Revision ID: 20260818_05
Revises: 20260817_04
Create Date: 2026-08-18
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260818_05"
down_revision: str | None = "20260817_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

provider_status = sa.Enum(
    "draft", "pending_review", "additional_information_required", "verified",
    "rejected", "suspended", "verification_expired", "archived",
    name="providerstatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("organization_name", sa.String(512), nullable=False),
        sa.Column("organization_type", sa.String(128), nullable=False),
        sa.Column("registration_number", sa.String(255), nullable=False),
        sa.Column("country", sa.String(255), nullable=False),
        sa.Column("official_website", sa.String(2048), nullable=False),
        sa.Column("official_email_domain", sa.String(255), nullable=False),
        sa.Column("physical_address", sa.Text(), nullable=False),
        sa.Column("contact_person", sa.String(255), nullable=False),
        sa.Column("contact_phone", sa.String(64), nullable=False),
        sa.Column("supporting_documents", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("social_media_links", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", provider_status, nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verification_date", sa.DateTime(timezone=True)),
        sa.Column("verified_by", sa.String(255)),
        sa.Column("reverification_date", sa.DateTime(timezone=True)),
        sa.Column("review_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_providers_user_id", "providers", ["user_id"])
    op.create_index(
        "uq_provider_email_domain_lower", "providers",
        [sa.text("lower(official_email_domain)")], unique=True,
    )
    op.create_table(
        "provider_administrators",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("permissions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "user_id", name="uq_provider_admin_user"),
    )
    op.create_index("ix_provider_administrators_provider_id", "provider_administrators", ["provider_id"])
    op.create_index("ix_provider_administrators_user_id", "provider_administrators", ["user_id"])
    op.create_table(
        "provider_activity_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("actor_id", sa.String(255), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_provider_activity_history_provider_id", "provider_activity_history", ["provider_id"])
    op.create_table(
        "provider_appeals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_provider_appeals_provider_id", "provider_appeals", ["provider_id"])


def downgrade() -> None:
    op.drop_index("ix_provider_appeals_provider_id", table_name="provider_appeals")
    op.drop_table("provider_appeals")
    op.drop_index("ix_provider_activity_history_provider_id", table_name="provider_activity_history")
    op.drop_table("provider_activity_history")
    op.drop_index("ix_provider_administrators_user_id", table_name="provider_administrators")
    op.drop_index("ix_provider_administrators_provider_id", table_name="provider_administrators")
    op.drop_table("provider_administrators")
    op.drop_index("uq_provider_email_domain_lower", table_name="providers")
    op.drop_index("ix_providers_user_id", table_name="providers")
    op.drop_table("providers")

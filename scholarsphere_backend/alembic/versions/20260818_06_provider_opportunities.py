"""Create provider opportunity submission tables.

Revision ID: 20260818_06
Revises: 20260818_05
Create Date: 2026-08-18
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260818_06"
down_revision: str | None = "20260818_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

opportunity_type = sa.Enum(
    "scholarship", "fellowship", "internship", "conference", "summit", "webinar",
    "exchange_program", "research_grant", "competition", "training", "volunteering",
    "youth_program", "online_course", "funded_event", "grant", "job",
    name="provideropportunitytype", native_enum=False,
)
funding_type = sa.Enum(
    "fully_funded", "partially_funded", "self_funded",
    name="provideropportunityfundingtype", native_enum=False,
)
delivery_format = sa.Enum(
    "online", "physical", "hybrid",
    name="provideropportunitydeliveryformat", native_enum=False,
)
verification_status = sa.Enum(
    "pending", "verified", "verification_expired", "incomplete", "suspicious",
    "rejected", "expired", "archived",
    name="provideropportunityverificationstatus", native_enum=False,
)
publication_status = sa.Enum(
    "unpublished", "published", "archived",
    name="publicationstatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "provider_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by", sa.String(255), nullable=False),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("host_institution", sa.String(512), nullable=False),
        sa.Column("host_country", sa.String(255), nullable=False),
        sa.Column("opportunity_type", opportunity_type, nullable=False),
        sa.Column("funding_type", funding_type, nullable=False),
        sa.Column("delivery_format", delivery_format, nullable=False),
        sa.Column("deadline", sa.Date(), nullable=False),
        sa.Column("application_open_date", sa.Date(), nullable=False),
        sa.Column("official_source_url", sa.String(2048), nullable=False),
        sa.Column("application_url", sa.String(2048), nullable=False),
        sa.Column("eligible_nationalities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("study_levels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fields_of_study", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("benefits", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("eligibility_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required_documents", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("application_procedure", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("language_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("minimum_age", sa.Integer()),
        sa.Column("maximum_age", sa.Integer()),
        sa.Column("work_experience_years_required", sa.Float()),
        sa.Column("contact_information", sa.Text(), nullable=False),
        sa.Column("available_positions", sa.Integer()),
        sa.Column("application_fee", sa.Float()),
        sa.Column("verification_status", verification_status, nullable=False),
        sa.Column("publication_status", publication_status, nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_provider_opportunities_provider_id", "provider_opportunities", ["provider_id"])
    op.create_table(
        "provider_opportunity_verification_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("verification_officer_id", sa.String(255)),
        sa.Column("source_checked", sa.Boolean(), nullable=False),
        sa.Column("application_link_checked", sa.Boolean(), nullable=False),
        sa.Column("deadline_checked", sa.Boolean(), nullable=False),
        sa.Column("duplicate_checked", sa.Boolean(), nullable=False),
        sa.Column("decision", sa.String(64), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_opportunity_id"], ["provider_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_opportunity_id"),
    )
    op.create_table(
        "provider_opportunity_verification_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("previous_status", sa.String(64), nullable=False),
        sa.Column("new_status", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("changed_fields", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["provider_opportunity_id"], ["provider_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_provider_opp_verif_history_opp_id",
        "provider_opportunity_verification_history", ["provider_opportunity_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_opp_verif_history_opp_id",
        table_name="provider_opportunity_verification_history",
    )
    op.drop_table("provider_opportunity_verification_history")
    op.drop_table("provider_opportunity_verification_reviews")
    op.drop_index("ix_provider_opportunities_provider_id", table_name="provider_opportunities")
    op.drop_table("provider_opportunities")

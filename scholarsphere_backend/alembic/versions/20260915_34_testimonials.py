"""Create testimonials, testimonial_moderation_history and
testimonial_reactions tables for the Success Stories feature.

Revision ID: 20260915_33
Revises: 20260914_32
Create Date: 2026-09-15
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260915_34"
down_revision: str | None = "20260901_33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

testimonial_status = sa.Enum(
    "draft",
    "submitted",
    "under_review",
    "changes_requested",
    "approved",
    "rejected",
    "withdrawn",
    name="testimonialstatus",
    native_enum=False,
)
testimonial_verification_status = sa.Enum(
    "unverified",
    "verified",
    name="testimonialverificationstatus",
    native_enum=False,
)
testimonial_display_mode = sa.Enum(
    "full_name",
    "first_name_last_initial",
    "anonymous",
    name="testimonialdisplaymode",
    native_enum=False,
)
testimonial_outcome = sa.Enum(
    "applied",
    "shortlisted",
    "interviewed",
    "selected",
    "awarded",
    "admitted",
    "funded",
    "other",
    name="testimonialoutcome",
    native_enum=False,
)
testimonial_reaction_type = sa.Enum(
    "helpful",
    "inspiring",
    "useful",
    name="testimonialreactiontype",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "testimonials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("opportunity_name", sa.String(500), nullable=False),
        sa.Column("opportunity_provider", sa.String(512), nullable=False),
        sa.Column("opportunity_type", sa.String(128), nullable=False),
        sa.Column("country", sa.String(255), nullable=True),
        sa.Column("degree_level", sa.String(128), nullable=True),
        sa.Column("field_of_study", sa.String(255), nullable=True),
        sa.Column("success_year", sa.Integer(), nullable=True),
        sa.Column("outcome", testimonial_outcome, nullable=False),
        sa.Column("challenge", sa.Text(), nullable=True),
        sa.Column("discovery_story", sa.Text(), nullable=True),
        sa.Column("preparation_story", sa.Text(), nullable=True),
        sa.Column("scholarsphere_help", sa.Text(), nullable=True),
        sa.Column("outcome_narrative", sa.Text(), nullable=True),
        sa.Column("impact", sa.Text(), nullable=True),
        sa.Column("advice", sa.Text(), nullable=True),
        sa.Column("features_used", sa.JSON(), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("university", sa.String(255), nullable=True),
        sa.Column("program", sa.String(255), nullable=True),
        sa.Column("photo_storage_path", sa.String(1024), nullable=True),
        sa.Column("display_mode", testimonial_display_mode, nullable=False),
        sa.Column("show_university", sa.Boolean(), nullable=False),
        sa.Column("show_country", sa.Boolean(), nullable=False),
        sa.Column("show_program", sa.Boolean(), nullable=False),
        sa.Column("show_photo", sa.Boolean(), nullable=False),
        sa.Column("evidence_storage_paths", sa.JSON(), nullable=False),
        sa.Column("consent_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", testimonial_status, nullable=False),
        sa.Column("verification_status", testimonial_verification_status, nullable=False),
        sa.Column("featured", sa.Boolean(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("verified_by", sa.String(255), nullable=True),
        sa.Column("verification_method", sa.String(255), nullable=True),
        sa.Column("last_moderator_id", sa.String(255), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("helpful_count", sa.Integer(), nullable=False),
        sa.Column("inspiring_count", sa.Integer(), nullable=False),
        sa.Column("useful_count", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["external_opportunities.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_testimonials_slug"),
    )
    op.create_index("ix_testimonials_status", "testimonials", ["status"])
    op.create_index(
        "ix_testimonials_verification_status", "testimonials", ["verification_status"]
    )
    op.create_index("ix_testimonials_featured", "testimonials", ["featured"])
    op.create_index("ix_testimonials_opportunity_id", "testimonials", ["opportunity_id"])
    op.create_index("ix_testimonials_user_id", "testimonials", ["user_id"])
    op.create_index("ix_testimonials_country", "testimonials", ["country"])
    op.create_index("ix_testimonials_success_year", "testimonials", ["success_year"])
    op.create_index("ix_testimonials_created_at", "testimonials", ["created_at"])

    op.create_table(
        "testimonial_moderation_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("testimonial_id", sa.Uuid(), nullable=False),
        sa.Column("previous_status", sa.String(64), nullable=False),
        sa.Column("new_status", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["testimonial_id"], ["testimonials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_testimonial_moderation_history_testimonial_id",
        "testimonial_moderation_history",
        ["testimonial_id"],
    )

    op.create_table(
        "testimonial_reactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("testimonial_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("reaction_type", testimonial_reaction_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["testimonial_id"], ["testimonials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "testimonial_id", "user_id", name="uq_testimonial_reaction_user"
        ),
    )
    op.create_index(
        "ix_testimonial_reactions_testimonial_id",
        "testimonial_reactions",
        ["testimonial_id"],
    )
    op.create_index(
        "ix_testimonial_reactions_user_id", "testimonial_reactions", ["user_id"]
    )


def downgrade() -> None:
    op.drop_table("testimonial_reactions")
    op.drop_table("testimonial_moderation_history")
    op.drop_index("ix_testimonials_created_at", table_name="testimonials")
    op.drop_index("ix_testimonials_success_year", table_name="testimonials")
    op.drop_index("ix_testimonials_country", table_name="testimonials")
    op.drop_index("ix_testimonials_user_id", table_name="testimonials")
    op.drop_index("ix_testimonials_opportunity_id", table_name="testimonials")
    op.drop_index("ix_testimonials_featured", table_name="testimonials")
    op.drop_index("ix_testimonials_verification_status", table_name="testimonials")
    op.drop_index("ix_testimonials_status", table_name="testimonials")
    op.drop_table("testimonials")

"""Create applicant_profiles table.

Revision ID: 20260821_08
Revises: 20260820_07
Create Date: 2026-08-21
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260821_08"
down_revision: str | None = "20260820_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

english_test_status = sa.Enum(
    "not_taken", "planned", "completed", "not_required",
    name="englishteststatus", native_enum=False,
)
passport_status = sa.Enum(
    "unavailable", "applied", "valid", "expired",
    name="passportstatus", native_enum=False,
)
employment_status = sa.Enum(
    "student", "employed", "self_employed", "unemployed", "other",
    name="employmentstatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "applicant_profiles",
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("nationality", sa.String(255), nullable=False),
        sa.Column("country_of_residence", sa.String(255), nullable=False),
        sa.Column("date_of_birth", sa.Date()),
        sa.Column("gender", sa.String(64), nullable=False),
        sa.Column("highest_qualification", sa.String(255), nullable=False),
        sa.Column("degree_field", sa.String(255), nullable=False),
        sa.Column("academic_classification", sa.String(255), nullable=False),
        sa.Column("graduation_year", sa.Integer()),
        sa.Column("work_experience_years", sa.Float(), nullable=False),
        sa.Column("preferred_study_levels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("preferred_countries", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("areas_of_interest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("english_test_status", english_test_status, nullable=False),
        sa.Column("passport_status", passport_status, nullable=False),
        sa.Column("employment_status", employment_status, nullable=False),
        sa.Column("funding_preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("special_eligibility_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("applicant_profiles")

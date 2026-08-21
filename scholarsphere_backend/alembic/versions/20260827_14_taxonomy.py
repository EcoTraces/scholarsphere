"""Create taxonomy term and version tables.

Revision ID: 20260827_14
Revises: 20260826_13
Create Date: 2026-08-27
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260827_14"
down_revision: str | None = "20260826_13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

taxonomy_type = sa.Enum(
    "country", "region", "continent", "nationality", "institution", "organization",
    "degree_level", "academic_field", "opportunity_type", "funding_type", "language",
    "currency", "qualification", "industry_sector",
    name="taxonomytype", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "taxonomy_terms",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("type", taxonomy_type, nullable=False),
        sa.Column("canonical_name", sa.String(500), nullable=False),
        sa.Column("code", sa.String(64)),
        sa.Column("synonyms", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("parent_id", sa.String(255)),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["parent_id"], ["taxonomy_terms.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "taxonomy_versions",
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("term_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("version"),
    )


def downgrade() -> None:
    op.drop_table("taxonomy_versions")
    op.drop_table("taxonomy_terms")

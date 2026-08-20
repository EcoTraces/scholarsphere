"""Create applicant_documents table.

Revision ID: 20260822_09
Revises: 20260821_08
Create Date: 2026-08-22
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260822_09"
down_revision: str | None = "20260821_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

document_type = sa.Enum(
    "passport", "curriculum_vitae", "academic_transcript", "degree_certificate",
    "recommendation_letters", "motivation_letter", "personal_statement",
    "research_proposal", "english_language_certificate", "work_experience_letter",
    "birth_certificate", "portfolio", "financial_documents",
    name="documenttype", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "applicant_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("type", document_type, nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("shared_with_provider_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "type", name="uq_applicant_document_user_type"),
    )
    op.create_index("ix_applicant_documents_user_id", "applicant_documents", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_applicant_documents_user_id", table_name="applicant_documents")
    op.drop_table("applicant_documents")

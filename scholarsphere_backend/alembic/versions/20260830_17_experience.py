"""Create experience preferences and translation entries tables.

Revision ID: 20260830_17
Revises: 20260829_16
Create Date: 2026-08-30
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260830_17"
down_revision: str | None = "20260829_16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

supported_language = sa.Enum(
    "english", "french", "spanish", "arabic", name="supportedlanguage", native_enum=False
)


def upgrade() -> None:
    op.create_table(
        "experience_preferences",
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("language", supported_language, nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("currency_code", sa.String(8), nullable=False),
        sa.Column("country_code", sa.String(8), nullable=False),
        sa.Column("text_scale", sa.Float(), nullable=False),
        sa.Column("high_contrast", sa.Boolean(), nullable=False),
        sa.Column("screen_reader_optimized", sa.Boolean(), nullable=False),
        sa.Column("keyboard_navigation", sa.Boolean(), nullable=False),
        sa.Column("low_bandwidth_mode", sa.Boolean(), nullable=False),
        sa.Column("compress_images", sa.Boolean(), nullable=False),
        sa.Column("data_saving", sa.Boolean(), nullable=False),
        sa.Column("cache_saved_opportunities", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "translation_entries",
        sa.Column("language", supported_language, nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("language", "key"),
    )


def downgrade() -> None:
    op.drop_table("translation_entries")
    op.drop_table("experience_preferences")

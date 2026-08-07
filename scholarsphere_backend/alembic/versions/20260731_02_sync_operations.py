"""Extend source health and synchronization history.

Revision ID: 20260731_02
Revises: 20260731_01
Create Date: 2026-07-31
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260731_02"
down_revision: str | None = "20260731_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "opportunity_sources",
        sa.Column("next_scheduled_sync", sa.DateTime(timezone=True)),
    )
    op.execute(
        """
        UPDATE opportunity_sources
        SET next_scheduled_sync = CURRENT_TIMESTAMP + INTERVAL '12 hours'
        WHERE source_code = 'eu_funding_tenders'
        """
    )
    op.execute(
        """
        UPDATE opportunity_sources
        SET next_scheduled_sync = CURRENT_TIMESTAMP + INTERVAL '6 hours'
        WHERE source_code IN ('grants_gov', 'simpler_grants')
        """
    )
    op.add_column(
        "opportunity_sync_history",
        sa.Column("source_code", sa.String(64)),
    )
    op.execute(
        """
        UPDATE opportunity_sync_history AS history
        SET source_code = sources.source_code
        FROM opportunity_sources AS sources
        WHERE history.source_id = sources.id
        """
    )
    op.alter_column(
        "opportunity_sync_history", "source_code", nullable=False
    )
    op.create_index(
        "ix_opportunity_sync_history_source_code",
        "opportunity_sync_history",
        ["source_code"],
    )
    op.add_column(
        "opportunity_sync_history",
        sa.Column(
            "duplicate_candidates", sa.Integer(), server_default="0", nullable=False
        ),
    )
    op.alter_column(
        "opportunity_sync_history",
        "final_status",
        new_column_name="status",
        existing_type=sa.String(19),
        nullable=False,
    )
    op.add_column(
        "opportunity_sync_history",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "opportunity_sync_history",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("opportunity_sync_history", "updated_at")
    op.drop_column("opportunity_sync_history", "created_at")
    op.execute(
        "UPDATE opportunity_sync_history SET status = 'running' WHERE status = 'queued'"
    )
    op.execute(
        "UPDATE opportunity_sync_history SET status = 'failed' WHERE status = 'cancelled'"
    )
    op.alter_column(
        "opportunity_sync_history",
        "status",
        new_column_name="final_status",
        existing_type=sa.String(19),
        nullable=False,
    )
    op.drop_column("opportunity_sync_history", "duplicate_candidates")
    op.drop_index(
        "ix_opportunity_sync_history_source_code",
        table_name="opportunity_sync_history",
    )
    op.drop_column("opportunity_sync_history", "source_code")
    op.drop_column("opportunity_sources", "next_scheduled_sync")

"""Create observability logs, metrics, traces, alert rules, and incidents tables.

Revision ID: 20260911_29
Revises: 20260910_28
Create Date: 2026-09-11
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260911_29"
down_revision: str | None = "20260910_28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

log_level = sa.Enum(
    "debug", "info", "warning", "error", "critical", name="loglevel", native_enum=False
)
incident_status = sa.Enum(
    "open", "acknowledged", "investigating", "resolved",
    name="incidentstatus", native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "application_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("level", log_level, nullable=False),
        sa.Column("service", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(255), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_application_logs_timestamp", "application_logs", ["timestamp"])
    op.create_index("ix_application_logs_service", "application_logs", ["service"])

    op.create_table(
        "metric_points",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metric_points_name", "metric_points", ["name"])

    op.create_table(
        "trace_spans",
        sa.Column("trace_id", sa.String(255), nullable=False),
        sa.Column("span_id", sa.String(255), nullable=False),
        sa.Column("parent_span_id", sa.String(255), nullable=True),
        sa.Column("operation", sa.String(255), nullable=False),
        sa.Column("service", sa.String(255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("successful", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("trace_id", "span_id"),
    )

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("metric_name", sa.String(255), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("comparison", sa.String(32), nullable=False),
        sa.Column("severity", log_level, nullable=False),
        sa.Column("escalation_target", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "operational_incidents",
        sa.Column("id", sa.String(255), nullable=False),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("severity", log_level, nullable=False),
        sa.Column("status", incident_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("escalation_target", sa.String(255), nullable=False),
        sa.Column("notes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("operational_incidents")
    op.drop_table("alert_rules")
    op.drop_table("trace_spans")
    op.drop_index("ix_metric_points_name", table_name="metric_points")
    op.drop_table("metric_points")
    op.drop_index("ix_application_logs_service", table_name="application_logs")
    op.drop_index("ix_application_logs_timestamp", table_name="application_logs")
    op.drop_table("application_logs")

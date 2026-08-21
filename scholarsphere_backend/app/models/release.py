import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.external_opportunity import JSONType


class DeploymentEnvironment(str, enum.Enum):
    development = "development"
    testing = "testing"
    staging = "staging"
    production = "production"


class DeploymentStrategy(str, enum.Enum):
    standard = "standard"
    blueGreen = "blueGreen"
    canary = "canary"


class DeploymentStatus(str, enum.Enum):
    draft = "draft"
    awaitingApproval = "awaitingApproval"
    approved = "approved"
    deploying = "deploying"
    completed = "completed"
    failed = "failed"
    rolledBack = "rolledBack"


class QualityReport(Base):
    __tablename__ = "quality_reports"

    release_version: Mapped[str] = mapped_column(String(255), primary_key=True)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False)
    coverage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    mandatory_eligibility_coverage_percent: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    security_findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @property
    def production_ready(self) -> bool:
        if self.coverage_percent < 80:
            return False
        if self.mandatory_eligibility_coverage_percent != 100:
            return False
        if any(
            check.get("critical") and check.get("outcome") != "passed"
            for check in self.checks
        ):
            return False
        if any(
            finding.get("severity") == "critical" and not finding.get("resolved")
            for finding in self.security_findings
        ):
            return False
        return True


class DeploymentRecord(Base):
    __tablename__ = "deployment_records"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    artifact_version: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_commit_sha: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_image_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    artifact_release_notes: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    artifact_migration_ids: Mapped[list[str]] = mapped_column(JSONType, nullable=False)
    environment: Mapped[DeploymentEnvironment] = mapped_column(
        Enum(DeploymentEnvironment, native_enum=False), nullable=False
    )
    strategy: Mapped[DeploymentStrategy] = mapped_column(
        Enum(DeploymentStrategy, native_enum=False), nullable=False
    )
    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus, native_enum=False), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_deployment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    history: Mapped[list[str]] = mapped_column(JSONType, nullable=False)

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.release import DeploymentEnvironment, DeploymentStrategy

_TEST_CATEGORIES = {
    "unit", "integration", "api", "endToEnd", "userInterface", "mobile",
    "browserCompatibility", "database", "eligibilityRules", "recommendations",
    "notifications", "security", "penetration", "performance", "load", "stress",
    "accessibility", "localization", "backupRestoration", "userAcceptance",
    "regression", "dataMigration",
}
_TEST_OUTCOMES = {"passed", "failed", "skipped"}
_SEVERITIES = {"low", "medium", "high", "critical"}


class QualityCheckIn(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    category: str
    outcome: str
    critical: bool
    executed_at: datetime
    details: str = ""

    @field_validator("category")
    @classmethod
    def _validate_category(cls, value: str) -> str:
        if value not in _TEST_CATEGORIES:
            raise ValueError(f"Unknown test category: {value!r}")
        return value

    @field_validator("outcome")
    @classmethod
    def _validate_outcome(cls, value: str) -> str:
        if value not in _TEST_OUTCOMES:
            raise ValueError(f"Unknown test outcome: {value!r}")
        return value


class SecurityFindingIn(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    severity: str
    resolved: bool
    summary: str = ""

    @field_validator("severity")
    @classmethod
    def _validate_severity(cls, value: str) -> str:
        if value not in _SEVERITIES:
            raise ValueError(f"Unknown severity: {value!r}")
        return value


class SaveQualityReportRequest(BaseModel):
    checks: list[QualityCheckIn] = Field(default_factory=list)
    coverage_percent: float = Field(ge=0, le=100)
    mandatory_eligibility_coverage_percent: float = Field(ge=0, le=100)
    security_findings: list[SecurityFindingIn] = Field(default_factory=list)


class QualityReportRead(BaseModel):
    release_version: str
    checks: list[dict[str, Any]]
    coverage_percent: float
    mandatory_eligibility_coverage_percent: float
    security_findings: list[dict[str, Any]]
    generated_at: datetime
    production_ready: bool


class ReleaseArtifactIn(BaseModel):
    version: str = Field(min_length=1, max_length=255)
    commit_sha: str = Field(min_length=1, max_length=255)
    image_reference: str = Field(min_length=1, max_length=1000)
    release_notes: str = ""
    created_at: datetime
    migration_ids: list[str] = Field(default_factory=list)


class CreateDeploymentRequest(BaseModel):
    artifact: ReleaseArtifactIn
    environment: str
    strategy: str

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        DeploymentEnvironment(value)
        return value

    @field_validator("strategy")
    @classmethod
    def _validate_strategy(cls, value: str) -> str:
        DeploymentStrategy(value)
        return value


class DeploymentRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    environment: str
    strategy: str
    status: str
    created_by: str
    approved_by: str | None
    created_at: datetime
    previous_deployment_id: str | None
    history: list[str]
    artifact: dict[str, Any]

    @field_validator("environment", "strategy", "status", mode="before")
    @classmethod
    def _unwrap_enum(cls, value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value)

    @classmethod
    def from_model(cls, record: Any) -> "DeploymentRecordRead":
        return cls(
            id=record.id,
            environment=record.environment,
            strategy=record.strategy,
            status=record.status,
            created_by=record.created_by,
            approved_by=record.approved_by,
            created_at=record.created_at,
            previous_deployment_id=record.previous_deployment_id,
            history=record.history,
            artifact={
                "version": record.artifact_version,
                "commit_sha": record.artifact_commit_sha,
                "image_reference": record.artifact_image_reference,
                "release_notes": record.artifact_release_notes,
                "created_at": record.artifact_created_at.isoformat(),
                "migration_ids": record.artifact_migration_ids,
            },
        )

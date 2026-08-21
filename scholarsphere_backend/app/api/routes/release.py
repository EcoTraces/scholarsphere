import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import require_roles
from app.models.audit_log import AuditAction, AuditResult
from app.db.session import get_db
from app.models.release import (
    DeploymentEnvironment,
    DeploymentRecord,
    DeploymentStatus,
    DeploymentStrategy,
    QualityReport,
)
from app.schemas.release import (
    CreateDeploymentRequest,
    DeploymentRecordRead,
    QualityReportRead,
    SaveQualityReportRequest,
)
from app.services.audit_log import append_audit_record
from app.services.parsing import utc_now

router = APIRouter(prefix="/release", tags=["release"])

# Matches DemoReleaseRepository._authorize exactly.
release_access = Depends(require_roles("administrator", "superAdministrator"))


def _report_read(report: QualityReport) -> QualityReportRead:
    return QualityReportRead(
        release_version=report.release_version,
        checks=report.checks,
        coverage_percent=report.coverage_percent,
        mandatory_eligibility_coverage_percent=report.mandatory_eligibility_coverage_percent,
        security_findings=report.security_findings,
        generated_at=report.generated_at,
        production_ready=report.production_ready,
    )


@router.put("/quality-reports/{version}", response_model=QualityReportRead)
async def save_quality_report(
    version: str,
    payload: SaveQualityReportRequest,
    _: Annotated[AuthenticatedUser, release_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> QualityReportRead:
    async with session.begin():
        report = await session.get(QualityReport, version)
        checks = [check.model_dump(mode="json") for check in payload.checks]
        findings = [finding.model_dump(mode="json") for finding in payload.security_findings]
        if report is None:
            report = QualityReport(
                release_version=version,
                checks=checks,
                coverage_percent=payload.coverage_percent,
                mandatory_eligibility_coverage_percent=(
                    payload.mandatory_eligibility_coverage_percent
                ),
                security_findings=findings,
                generated_at=utc_now(),
            )
            session.add(report)
        else:
            report.checks = checks
            report.coverage_percent = payload.coverage_percent
            report.mandatory_eligibility_coverage_percent = (
                payload.mandatory_eligibility_coverage_percent
            )
            report.security_findings = findings
            report.generated_at = utc_now()
        await session.flush()
        return _report_read(report)


@router.get("/quality-reports/{version}", response_model=QualityReportRead | None)
async def get_quality_report(
    version: str,
    _: Annotated[AuthenticatedUser, release_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> QualityReportRead | None:
    report = await session.get(QualityReport, version)
    return _report_read(report) if report is not None else None


@router.post("/deployments", response_model=DeploymentRecordRead)
async def create_deployment(
    payload: CreateDeploymentRequest,
    user: Annotated[AuthenticatedUser, release_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DeploymentRecordRead:
    environment = DeploymentEnvironment(payload.environment)
    strategy = DeploymentStrategy(payload.strategy)
    async with session.begin():
        report = await session.get(QualityReport, payload.artifact.version)
        if report is None or not report.production_ready:
            raise HTTPException(
                status_code=409,
                detail="Deployment is blocked until all quality gates pass.",
            )
        latest = await session.scalar(
            select(DeploymentRecord)
            .where(
                DeploymentRecord.environment == environment,
                DeploymentRecord.status == DeploymentStatus.completed,
            )
            .order_by(DeploymentRecord.created_at.desc())
            .limit(1)
        )
        now = utc_now()
        record = DeploymentRecord(
            id=uuid.uuid4().hex,
            artifact_version=payload.artifact.version,
            artifact_commit_sha=payload.artifact.commit_sha,
            artifact_image_reference=payload.artifact.image_reference,
            artifact_release_notes=payload.artifact.release_notes,
            artifact_created_at=payload.artifact.created_at,
            artifact_migration_ids=payload.artifact.migration_ids,
            environment=environment,
            strategy=strategy,
            status=(
                DeploymentStatus.awaitingApproval
                if environment == DeploymentEnvironment.production
                else DeploymentStatus.approved
            ),
            created_by=user.uid,
            approved_by=None,
            created_at=now,
            previous_deployment_id=latest.id if latest is not None else None,
            history=[f"Deployment created by {user.uid}."],
        )
        session.add(record)
        await session.flush()
        return DeploymentRecordRead.from_model(record)


async def _require_deployment(session: AsyncSession, deployment_id: str) -> DeploymentRecord:
    record = await session.get(DeploymentRecord, deployment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Deployment was not found.")
    return record


async def _save_transition(
    session: AsyncSession, record: DeploymentRecord, user: AuthenticatedUser, action: str
) -> DeploymentRecordRead:
    await append_audit_record(
        session,
        actor_id=user.uid,
        actor_role=user.role,
        action=AuditAction.administrativeAction,
        entity_type="deployment",
        entity_id=record.id,
        new_value=action,
        result=AuditResult.success,
        correlation_id=f"{action}-{record.id}",
    )
    await session.flush()
    return DeploymentRecordRead.from_model(record)


@router.post("/deployments/{deployment_id}/approve", response_model=DeploymentRecordRead)
async def approve_deployment(
    deployment_id: str,
    user: Annotated[AuthenticatedUser, release_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DeploymentRecordRead:
    async with session.begin():
        record = await _require_deployment(session, deployment_id)
        if record.created_by == user.uid and record.environment == DeploymentEnvironment.production:
            raise HTTPException(
                status_code=409,
                detail="Production approval requires a second administrator.",
            )
        record.status = DeploymentStatus.approved
        record.approved_by = user.uid
        record.history = [*record.history, f"Approved by {user.uid}."]
        return await _save_transition(session, record, user, "deployment_approved")


@router.post("/deployments/{deployment_id}/deploy", response_model=DeploymentRecordRead)
async def deploy_deployment(
    deployment_id: str,
    user: Annotated[AuthenticatedUser, release_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DeploymentRecordRead:
    async with session.begin():
        record = await _require_deployment(session, deployment_id)
        if record.status != DeploymentStatus.approved:
            raise HTTPException(status_code=409, detail="Deployment is not approved.")
        record.status = DeploymentStatus.completed
        record.history = [
            *record.history,
            f"{record.strategy.value} deployment completed.",
        ]
        return await _save_transition(session, record, user, "deployment_completed")


@router.post("/deployments/{deployment_id}/rollback", response_model=DeploymentRecordRead)
async def rollback_deployment(
    deployment_id: str,
    user: Annotated[AuthenticatedUser, release_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DeploymentRecordRead:
    async with session.begin():
        record = await _require_deployment(session, deployment_id)
        if record.status != DeploymentStatus.completed:
            raise HTTPException(
                status_code=409, detail="Only completed deployments can roll back."
            )
        record.status = DeploymentStatus.rolledBack
        record.history = [*record.history, f"Rolled back by {user.uid}."]
        return await _save_transition(session, record, user, "deployment_rolled_back")


@router.get("/deployments", response_model=list[DeploymentRecordRead])
async def deployment_history(
    _: Annotated[AuthenticatedUser, release_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[DeploymentRecordRead]:
    rows = await session.scalars(
        select(DeploymentRecord).order_by(DeploymentRecord.created_at.desc())
    )
    return [DeploymentRecordRead.from_model(row) for row in rows.all()]

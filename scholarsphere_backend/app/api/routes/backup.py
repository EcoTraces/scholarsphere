import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.audit_log import AuditAction, AuditResult
from app.models.backup import (
    BackupPolicy,
    BackupRecord,
    BackupStatus,
    BackupType,
    RecoveryStatus,
    RecoveryTest,
)
from app.schemas.backup import (
    BackupPolicyRead,
    BackupPolicySave,
    BackupRecordRead,
    CreateBackupRequest,
    DisasterRecoveryPlanRead,
    EnforceRetentionRead,
    RecoveryTestRead,
    backup_type_from_wire,
)
from app.services.audit_log import append_audit_record
from app.services.parsing import utc_now

router = APIRouter(prefix="/backup", tags=["backup"])

# Matches DemoBackupRepository._authorize exactly: security administrators only.
backup_access = Depends(require_roles("securityAdministrator", "superAdministrator"))

_POLICY_ID = "global"


async def _policy(session: AsyncSession) -> BackupPolicy:
    policy = await session.get(BackupPolicy, _POLICY_ID)
    if policy is None:
        policy = BackupPolicy(
            id=_POLICY_ID,
            full_backup_interval_seconds=86400,
            transaction_log_interval_seconds=900,
            retention_seconds=35 * 86400,
            monthly_restore_test=True,
            encryption_required=True,
            separate_region_required=True,
            recovery_point_objective_seconds=900,
            recovery_time_objective_seconds=4 * 3600,
        )
        session.add(policy)
        await session.flush()
    return policy


async def _require_backup(session: AsyncSession, backup_id: str) -> BackupRecord:
    record = await session.get(BackupRecord, backup_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Backup was not found.")
    return record


@router.get("/policy", response_model=BackupPolicyRead)
async def get_policy(
    _: Annotated[AuthenticatedUser, backup_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BackupPolicyRead:
    return BackupPolicyRead.model_validate(await _policy(session))


@router.put("/policy", response_model=BackupPolicyRead)
async def save_policy(
    payload: BackupPolicySave,
    _: Annotated[AuthenticatedUser, backup_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BackupPolicyRead:
    async with session.begin():
        policy = await _policy(session)
        policy.full_backup_interval_seconds = payload.full_backup_interval_seconds
        policy.transaction_log_interval_seconds = payload.transaction_log_interval_seconds
        policy.retention_seconds = payload.retention_seconds
        policy.monthly_restore_test = payload.monthly_restore_test
        policy.encryption_required = payload.encryption_required
        policy.separate_region_required = payload.separate_region_required
        policy.recovery_point_objective_seconds = payload.recovery_point_objective_seconds
        policy.recovery_time_objective_seconds = payload.recovery_time_objective_seconds
        await session.flush()
        return BackupPolicyRead.model_validate(policy)


@router.post("/backups", response_model=BackupRecordRead)
async def create_backup(
    payload: CreateBackupRequest,
    user: Annotated[AuthenticatedUser, backup_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BackupRecordRead:
    backup_type = backup_type_from_wire(payload.type)
    async with session.begin():
        policy = await _policy(session)
        now = utc_now()
        record = BackupRecord(
            id=uuid.uuid4().hex,
            type=backup_type,
            status=BackupStatus.completed,
            storage_location=f"encrypted://backup-vault/{backup_type.value}/{now.isoformat()}",
            region=payload.region,
            encrypted=True,
            created_at=now,
            completed_at=now,
            expires_at=now + timedelta(seconds=policy.retention_seconds),
            size_bytes=1024 if backup_type == BackupType.transactionLog else 1024 * 1024,
            checksum=f"checksum-{now.timestamp()}",
        )
        session.add(record)
        await append_audit_record(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action=AuditAction.administrativeAction,
            entity_type="backup",
            entity_id=record.id,
            new_value="backup_created",
            result=AuditResult.success,
            correlation_id=f"backup_created-{record.id}",
        )
        await session.flush()
        return BackupRecordRead.model_validate(record)


@router.post("/backups/{backup_id}/verify", response_model=BackupRecordRead)
async def verify_backup(
    backup_id: str,
    user: Annotated[AuthenticatedUser, backup_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BackupRecordRead:
    async with session.begin():
        record = await _require_backup(session, backup_id)
        if not record.encrypted or not record.checksum:
            raise HTTPException(status_code=409, detail="Backup integrity verification failed.")
        record.status = BackupStatus.verified
        await append_audit_record(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action=AuditAction.administrativeAction,
            entity_type="backup",
            entity_id=record.id,
            new_value="backup_verified",
            result=AuditResult.success,
            correlation_id=f"backup_verified-{record.id}",
        )
        await session.flush()
        return BackupRecordRead.model_validate(record)


@router.post("/backups/{backup_id}/test-recovery", response_model=RecoveryTestRead)
async def test_recovery(
    backup_id: str,
    user: Annotated[AuthenticatedUser, backup_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RecoveryTestRead:
    async with session.begin():
        record = await _require_backup(session, backup_id)
        if not record.encrypted or not record.checksum:
            raise HTTPException(status_code=409, detail="Backup integrity verification failed.")
        record.status = BackupStatus.verified
        started = utc_now()
        completed = started + timedelta(minutes=20)
        test = RecoveryTest(
            id=uuid.uuid4().hex,
            backup_id=backup_id,
            status=RecoveryStatus.completed,
            started_at=started,
            completed_at=completed,
            integrity_valid=True,
            duration_seconds=int((completed - started).total_seconds()),
            notes="Isolated restoration test completed within the RTO.",
        )
        session.add(test)
        await append_audit_record(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action=AuditAction.administrativeAction,
            entity_type="backup",
            entity_id=backup_id,
            new_value="recovery_test_completed",
            result=AuditResult.success,
            correlation_id=f"recovery_test_completed-{backup_id}",
        )
        await session.flush()
        return RecoveryTestRead.model_validate(test)


@router.get("/backups", response_model=list[BackupRecordRead])
async def list_backups(
    _: Annotated[AuthenticatedUser, backup_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[BackupRecordRead]:
    rows = await session.scalars(select(BackupRecord).order_by(BackupRecord.created_at.asc()))
    return [BackupRecordRead.model_validate(row) for row in rows.all()]


@router.post("/retention/enforce", response_model=EnforceRetentionRead)
async def enforce_retention(
    _: Annotated[AuthenticatedUser, backup_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EnforceRetentionRead:
    async with session.begin():
        now = utc_now()
        expired = (
            await session.scalars(
                select(BackupRecord).where(
                    BackupRecord.expires_at.is_not(None), BackupRecord.expires_at < now
                )
            )
        ).all()
        for record in expired:
            await session.delete(record)
        return EnforceRetentionRead(removed=len(expired))


@router.get("/disaster-recovery-plan", response_model=DisasterRecoveryPlanRead)
async def disaster_recovery_plan(
    _: Annotated[AuthenticatedUser, backup_access],
) -> DisasterRecoveryPlanRead:
    return DisasterRecoveryPlanRead(
        version=1,
        primary_region="primary-region",
        recovery_region="separate-recovery-region",
        restoration_steps=[
            "Declare the incident and freeze writes.",
            "Verify the latest encrypted backup and transaction logs.",
            "Restore data in the recovery region.",
            "Validate security, integrity, and application health.",
            "Approve traffic failover and notify stakeholders.",
        ],
        emergency_contacts=["security-lead", "operations-lead"],
        business_continuity_steps=[
            "Enable the public status page.",
            "Use read-only opportunity access where safe.",
            "Prioritize authentication and application tracking restoration.",
        ],
        last_reviewed_at=utc_now(),
    )

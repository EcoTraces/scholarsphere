from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.audit_log import AuditAction, AuditResult
from app.models.data_lifecycle import (
    LegalHold,
    LifecycleRecord,
    LifecycleStatus,
    RetainedEntityType,
    RetentionRule,
)
from app.schemas.data_lifecycle import (
    CleanupReportRead,
    LegalHoldRead,
    LifecycleRecordRead,
    PlaceLegalHoldRequest,
    RegisterRecordRequest,
    RetentionRuleRead,
    SaveRetentionRuleRequest,
)
from app.services.audit_log import append_audit_record
from app.services.parsing import utc_now

router = APIRouter(prefix="/data-lifecycle", tags=["data lifecycle"])

# Matches DemoDataLifecycleRepository._authorize exactly.
lifecycle_access = Depends(
    require_roles("administrator", "securityAdministrator", "superAdministrator")
)

_DEFAULT_BACKUP_DELETION_SECONDS = 35 * 86400


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


@router.put("/rules/{entity_type}", response_model=RetentionRuleRead)
async def save_rule(
    entity_type: RetainedEntityType,
    payload: SaveRetentionRuleRequest,
    _: Annotated[AuthenticatedUser, lifecycle_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RetentionRuleRead:
    if entity_type == RetainedEntityType.auditLog and payload.active_duration_seconds < 365 * 86400:
        raise HTTPException(status_code=422, detail="Retention policy is invalid.")
    async with session.begin():
        rule = await session.get(RetentionRule, entity_type)
        if rule is None:
            rule = RetentionRule(entity_type=entity_type)
            session.add(rule)
        rule.active_duration_seconds = payload.active_duration_seconds
        rule.archive_duration_seconds = payload.archive_duration_seconds
        rule.delete_from_backups_after_seconds = payload.delete_from_backups_after_seconds
        rule.archive_expired_records = payload.archive_expired_records
        rule.retain_rejected_for_fraud_prevention = (
            payload.retain_rejected_for_fraud_prevention
        )
        await session.flush()
        return RetentionRuleRead.model_validate(rule)


@router.get("/rules", response_model=list[RetentionRuleRead])
async def list_rules(
    _: Annotated[AuthenticatedUser, lifecycle_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[RetentionRuleRead]:
    rows = await session.scalars(select(RetentionRule))
    return [RetentionRuleRead.model_validate(row) for row in rows.all()]


@router.post("/records", response_model=LifecycleRecordRead)
async def register_record(
    payload: RegisterRecordRequest,
    _: Annotated[AuthenticatedUser, lifecycle_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LifecycleRecordRead:
    async with session.begin():
        now = utc_now()
        record = await session.get(
            LifecycleRecord, (payload.entity_type, payload.entity_id)
        )
        if record is None:
            record = LifecycleRecord(
                entity_type=payload.entity_type,
                entity_id=payload.entity_id,
                created_at=now,
            )
            session.add(record)
        record.owner_id = payload.owner_id
        record.status = payload.status
        record.contains_personal_data = payload.contains_personal_data
        record.updated_at = now
        await session.flush()
        return LifecycleRecordRead.model_validate(record)


async def _require_record(
    session: AsyncSession, entity_type: RetainedEntityType, entity_id: str
) -> LifecycleRecord:
    record = await session.get(LifecycleRecord, (entity_type, entity_id))
    if record is None:
        raise HTTPException(status_code=404, detail="Lifecycle record was not found.")
    return record


async def _has_hold(
    session: AsyncSession, entity_type: RetainedEntityType, entity_id: str
) -> bool:
    hold = await session.scalar(
        select(LegalHold).where(
            LegalHold.entity_type == entity_type,
            LegalHold.entity_id == entity_id,
            LegalHold.released_at.is_(None),
        )
    )
    return hold is not None


async def _permanently_delete(
    session: AsyncSession,
    user: AuthenticatedUser,
    record: LifecycleRecord,
) -> None:
    rule = await session.get(RetentionRule, record.entity_type)
    now = utc_now()
    record.status = LifecycleStatus.permanentlyDeleted
    record.updated_at = now
    record.deleted_at = now
    record.backup_deletion_due_at = now + timedelta(
        seconds=(
            rule.delete_from_backups_after_seconds
            if rule is not None
            else _DEFAULT_BACKUP_DELETION_SECONDS
        )
    )
    record.deletion_verification = f"active-storage-absent:{now.timestamp()}"
    await append_audit_record(
        session,
        actor_id=user.uid,
        actor_role=user.role,
        action=AuditAction.accountDeleted,
        entity_type=record.entity_type.value,
        entity_id=record.entity_id,
        new_value="permanently_deleted",
        result=AuditResult.success,
        correlation_id=f"permanently_deleted-{record.entity_type.value}-{record.entity_id}",
    )


@router.post(
    "/records/{entity_type}/{entity_id}/soft-delete", response_model=LifecycleRecordRead
)
async def soft_delete(
    entity_type: RetainedEntityType,
    entity_id: str,
    user: Annotated[AuthenticatedUser, lifecycle_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LifecycleRecordRead:
    async with session.begin():
        record = await _require_record(session, entity_type, entity_id)
        if await _has_hold(session, entity_type, entity_id):
            raise HTTPException(
                status_code=409, detail="This record is protected by a legal hold."
            )
        record.status = LifecycleStatus.softDeleted
        record.updated_at = utc_now()
        await append_audit_record(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action=AuditAction.accountDeleted,
            entity_type=entity_type.value,
            entity_id=entity_id,
            new_value="soft_deleted",
            result=AuditResult.success,
            correlation_id=f"soft_deleted-{entity_type.value}-{entity_id}",
        )
        await session.flush()
        return LifecycleRecordRead.model_validate(record)


@router.post(
    "/records/{entity_type}/{entity_id}/permanently-delete",
    response_model=LifecycleRecordRead,
)
async def permanently_delete(
    entity_type: RetainedEntityType,
    entity_id: str,
    user: Annotated[AuthenticatedUser, lifecycle_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LifecycleRecordRead:
    async with session.begin():
        record = await _require_record(session, entity_type, entity_id)
        if await _has_hold(session, entity_type, entity_id):
            raise HTTPException(
                status_code=409, detail="This record is protected by a legal hold."
            )
        await _permanently_delete(session, user, record)
        await session.flush()
        return LifecycleRecordRead.model_validate(record)


@router.post("/records/{entity_type}/{entity_id}/restore", response_model=LifecycleRecordRead)
async def restore(
    entity_type: RetainedEntityType,
    entity_id: str,
    user: Annotated[AuthenticatedUser, lifecycle_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LifecycleRecordRead:
    async with session.begin():
        record = await _require_record(session, entity_type, entity_id)
        if record.status == LifecycleStatus.permanentlyDeleted:
            raise HTTPException(
                status_code=409, detail="Permanently deleted data cannot be restored."
            )
        record.status = LifecycleStatus.restored
        record.updated_at = utc_now()
        await append_audit_record(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action=AuditAction.accountDeleted,
            entity_type=entity_type.value,
            entity_id=entity_id,
            new_value="archive_restored",
            result=AuditResult.success,
            correlation_id=f"archive_restored-{entity_type.value}-{entity_id}",
        )
        await session.flush()
        return LifecycleRecordRead.model_validate(record)


@router.get(
    "/records/{entity_type}/{entity_id}/verify-deletion", response_model=bool
)
async def verify_deletion(
    entity_type: RetainedEntityType,
    entity_id: str,
    _: Annotated[AuthenticatedUser, lifecycle_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> bool:
    record = await _require_record(session, entity_type, entity_id)
    return (
        record.status == LifecycleStatus.permanentlyDeleted
        and record.deletion_verification is not None
    )


@router.post("/legal-holds/{entity_type}/{entity_id}", response_model=LegalHoldRead)
async def place_legal_hold(
    entity_type: RetainedEntityType,
    entity_id: str,
    payload: PlaceLegalHoldRequest,
    user: Annotated[AuthenticatedUser, lifecycle_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LegalHoldRead:
    async with session.begin():
        await _require_record(session, entity_type, entity_id)
        now = utc_now()
        hold = LegalHold(
            entity_type=entity_type,
            entity_id=entity_id,
            reason=payload.reason,
            placed_by=user.uid,
            placed_at=now,
        )
        session.add(hold)
        await append_audit_record(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action=AuditAction.accountDeleted,
            entity_type=entity_type.value,
            entity_id=entity_id,
            new_value="legal_hold_placed",
            result=AuditResult.success,
            correlation_id=f"legal_hold_placed-{entity_type.value}-{entity_id}",
        )
        await session.flush()
        return LegalHoldRead.model_validate(hold)


@router.post("/cleanup", response_model=CleanupReportRead)
async def run_cleanup(
    user: Annotated[AuthenticatedUser, lifecycle_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CleanupReportRead:
    async with session.begin():
        now = utc_now()
        archived = 0
        deleted = 0
        held = 0
        records = (await session.scalars(select(LifecycleRecord))).all()
        rules = {
            rule.entity_type: rule for rule in (await session.scalars(select(RetentionRule))).all()
        }
        for record in records:
            rule = rules.get(record.entity_type)
            if rule is None or record.status == LifecycleStatus.permanentlyDeleted:
                continue
            if await _has_hold(session, record.entity_type, record.entity_id):
                held += 1
                continue
            age = now - _aware(record.created_at)
            if (
                record.status == LifecycleStatus.active
                and age.total_seconds() >= rule.active_duration_seconds
            ):
                record.status = LifecycleStatus.archived
                record.archived_at = now
                record.updated_at = now
                archived += 1
            elif (
                record.status == LifecycleStatus.archived
                and record.archived_at is not None
                and (now - _aware(record.archived_at)).total_seconds()
                >= rule.archive_duration_seconds
            ):
                await _permanently_delete(session, user, record)
                deleted += 1
        return CleanupReportRead(
            archived=archived,
            permanently_deleted=deleted,
            skipped_legal_holds=held,
            completed_at=now,
        )

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.audit_log import AuditAction, AuditRecord, AuditResult, AuditRetentionPolicy
from app.schemas.audit_log import (
    AuditExportRead,
    AuditRecordRead,
    AuditRetentionPolicyRead,
    AuditRetentionPolicySave,
    EnforceRetentionRead,
)
from app.services.audit_log import enforce_retention, verify_integrity

router = APIRouter(prefix="/audit", tags=["audit"])

# Audit access is restricted to administrators, matching
# DemoAuditRepository._authorize exactly.
audit_access = Depends(require_roles("administrator", "securityAdministrator", "superAdministrator"))

_POLICY_ID = "global"
_DEFAULT_RETENTION_DAYS = 2555


async def _policy(session: AsyncSession) -> AuditRetentionPolicy:
    policy = await session.get(AuditRetentionPolicy, _POLICY_ID)
    if policy is None:
        policy = AuditRetentionPolicy(id=_POLICY_ID, retention_days=_DEFAULT_RETENTION_DAYS)
        session.add(policy)
        await session.flush()
    return policy


async def _search(
    session: AsyncSession,
    *,
    actor_id: str | None,
    action: str | None,
    entity_type: str | None,
    entity_id: str | None,
    result: str | None,
    from_: datetime | None,
    to: datetime | None,
) -> list[AuditRecord]:
    query = select(AuditRecord)
    if actor_id is not None:
        query = query.where(AuditRecord.actor_id == actor_id)
    if action is not None:
        query = query.where(AuditRecord.action == AuditAction(action))
    if entity_type is not None:
        query = query.where(AuditRecord.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(AuditRecord.entity_id == entity_id)
    if result is not None:
        query = query.where(AuditRecord.result == AuditResult(result))
    if from_ is not None:
        query = query.where(AuditRecord.timestamp >= from_)
    if to is not None:
        query = query.where(AuditRecord.timestamp <= to)
    rows = await session.scalars(query.order_by(AuditRecord.id.asc()))
    return list(rows.all())


@router.get("/records", response_model=list[AuditRecordRead])
async def search_records(
    _: Annotated[AuthenticatedUser, audit_access],
    session: Annotated[AsyncSession, Depends(get_db)],
    actor_id: Annotated[str | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    entity_type: Annotated[str | None, Query()] = None,
    entity_id: Annotated[str | None, Query()] = None,
    result: Annotated[str | None, Query()] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
) -> list[AuditRecordRead]:
    records = await _search(
        session,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        result=result,
        from_=from_,
        to=to,
    )
    return [AuditRecordRead.model_validate(record) for record in records]


@router.get("/records/export", response_model=AuditExportRead)
async def export_records(
    _: Annotated[AuthenticatedUser, audit_access],
    session: Annotated[AsyncSession, Depends(get_db)],
    actor_id: Annotated[str | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    entity_type: Annotated[str | None, Query()] = None,
    entity_id: Annotated[str | None, Query()] = None,
    result: Annotated[str | None, Query()] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
) -> AuditExportRead:
    records = await _search(
        session,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        result=result,
        from_=from_,
        to=to,
    )

    def csv_field(value: str) -> str:
        return '"' + value.replace('"', '""') + '"'

    lines = [
        "audit_id,actor_id,actor_role,action,entity_type,entity_id,timestamp,result,correlation_id",
        *(
            ",".join(
                csv_field(field)
                for field in (
                    str(record.id),
                    record.actor_id,
                    record.actor_role,
                    record.action.value,
                    record.entity_type,
                    record.entity_id,
                    record.timestamp.isoformat(),
                    record.result.value,
                    record.correlation_id,
                )
            )
            for record in records
        ),
    ]
    return AuditExportRead(csv="\n".join(lines))


@router.get("/integrity", response_model=bool)
async def integrity(
    _: Annotated[AuthenticatedUser, audit_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> bool:
    return await verify_integrity(session)


@router.get("/retention-policy", response_model=AuditRetentionPolicyRead)
async def get_retention_policy(
    _: Annotated[AuthenticatedUser, audit_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuditRetentionPolicyRead:
    policy = await _policy(session)
    return AuditRetentionPolicyRead(retention_days=policy.retention_days)


@router.put("/retention-policy", response_model=AuditRetentionPolicyRead)
async def save_retention_policy(
    payload: AuditRetentionPolicySave,
    _: Annotated[AuthenticatedUser, audit_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AuditRetentionPolicyRead:
    async with session.begin():
        policy = await _policy(session)
        policy.retention_days = payload.retention_days
        await session.flush()
        return AuditRetentionPolicyRead(retention_days=policy.retention_days)


@router.post("/retention/enforce", response_model=EnforceRetentionRead)
async def enforce_retention_route(
    _: Annotated[AuthenticatedUser, audit_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EnforceRetentionRead:
    async with session.begin():
        policy = await _policy(session)
        removed = await enforce_retention(session, policy.retention_days)
        return EnforceRetentionRead(removed=removed)

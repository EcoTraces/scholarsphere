from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import STAFF_ROLES, require_roles
from app.db.session import get_db
from app.models.legal_compliance import (
    ComplianceRecord,
    LegalPolicy,
    LegalPolicyType,
    LegalRequest,
    LegalRequestStatus,
    PolicyAcceptance,
)
from app.schemas.legal_compliance import (
    AcceptPolicyRequest,
    ComplianceRecordRead,
    LegalPolicyRead,
    LegalRequestRead,
    PublishPolicyRequest,
    SaveComplianceRecordRequest,
    SubmitLegalRequestRequest,
    policy_type_from_wire,
    request_type_from_wire,
)
from app.services.parsing import utc_now

router = APIRouter(prefix="/legal", tags=["legal"])

any_authenticated = Depends(get_current_user)
# submitLegalRequest/legalRequests/saveComplianceRecord/complianceRecords
# have no current self-service UI caller - the only consumer today is the
# staff-only Data Governance screen (lib/features/governance/presentation/
# data_governance_screen.dart), reached through the administration
# dashboard.
staff_access = Depends(require_roles(*STAFF_ROLES))


async def _current_policy(session: AsyncSession, policy_type) -> LegalPolicy | None:
    return await session.scalar(
        select(LegalPolicy)
        .where(LegalPolicy.type == policy_type)
        .order_by(LegalPolicy.published_at.desc())
        .limit(1)
    )


async def _has_accepted_current(session: AsyncSession, user_id: str, policy_type) -> bool:
    policy = await _current_policy(session, policy_type)
    if policy is None or not policy.requires_acceptance:
        return True
    acceptance = await session.scalar(
        select(PolicyAcceptance).where(
            PolicyAcceptance.user_id == user_id,
            PolicyAcceptance.policy_id == policy.id,
            PolicyAcceptance.policy_version == policy.version,
        )
    )
    return acceptance is not None


@router.post("/policies", response_model=LegalPolicyRead)
async def publish_policy(
    payload: PublishPolicyRequest,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LegalPolicyRead:
    policy_type = policy_type_from_wire(payload.type)
    async with session.begin():
        collision = await session.scalar(
            select(LegalPolicy).where(
                LegalPolicy.type == policy_type, LegalPolicy.version == payload.version
            )
        )
        if collision is not None:
            raise HTTPException(status_code=409, detail="This policy version already exists.")
        policy = LegalPolicy(
            id=payload.id,
            type=policy_type,
            version=payload.version,
            title=payload.title,
            content=payload.content,
            effective_at=payload.effective_at,
            published_at=utc_now(),
            requires_acceptance=payload.requires_acceptance,
            material_change=payload.material_change,
            published_by=user.uid,
        )
        session.add(policy)
        await session.flush()
        await session.refresh(policy)
        return LegalPolicyRead.model_validate(policy)


@router.get("/policies/{policy_type}/current", response_model=LegalPolicyRead | None)
async def get_current_policy(
    policy_type: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LegalPolicyRead | None:
    # Deliberately public, unlike every other route in this file: a
    # visitor must be able to read Terms & Conditions / Privacy Policy
    # before creating an account (the registration form's own consent
    # checkboxes link here), not only after signing in.
    policy = await _current_policy(session, policy_type_from_wire(policy_type))
    return None if policy is None else LegalPolicyRead.model_validate(policy)


@router.get("/policies/{policy_type}/versions", response_model=list[LegalPolicyRead])
async def get_policy_versions(
    policy_type: str,
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[LegalPolicyRead]:
    rows = (
        await session.scalars(
            select(LegalPolicy)
            .where(LegalPolicy.type == policy_type_from_wire(policy_type))
            .order_by(LegalPolicy.published_at)
        )
    ).all()
    return [LegalPolicyRead.model_validate(row) for row in rows]


@router.post("/acceptances", status_code=204)
async def accept_policy(
    payload: AcceptPolicyRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        policy = await session.get(LegalPolicy, payload.policy_id)
        if policy is None:
            raise HTTPException(status_code=404, detail="Policy was not found.")
        current = await _current_policy(session, policy.type)
        if current is None or current.version != payload.policy_version:
            raise HTTPException(
                status_code=409, detail="Only the current policy version can be accepted."
            )
        existing = await session.scalar(
            select(PolicyAcceptance).where(
                PolicyAcceptance.user_id == user.uid,
                PolicyAcceptance.policy_id == payload.policy_id,
            )
        )
        now = utc_now()
        if existing is None:
            session.add(
                PolicyAcceptance(
                    user_id=user.uid,
                    policy_id=payload.policy_id,
                    policy_version=payload.policy_version,
                    accepted_at=now,
                    ip_address=payload.ip_address,
                )
            )
        else:
            existing.policy_version = payload.policy_version
            existing.accepted_at = now
            existing.ip_address = payload.ip_address


@router.get("/policies/{policy_type}/accepted", response_model=bool)
async def has_accepted_current(
    policy_type: str,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> bool:
    return await _has_accepted_current(session, user.uid, policy_type_from_wire(policy_type))


@router.get("/pending-notifications", response_model=list[str])
async def pending_policy_notifications(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[str]:
    pending: list[str] = []
    for policy_type in LegalPolicyType:
        policy = await _current_policy(session, policy_type)
        if policy is not None and policy.material_change and not await _has_accepted_current(
            session, user.uid, policy_type
        ):
            pending.append(f"{policy.title} {policy.version} requires review.")
    return pending


@router.post("/requests", response_model=LegalRequestRead)
async def submit_legal_request(
    payload: SubmitLegalRequestRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LegalRequestRead:
    async with session.begin():
        request = LegalRequest(
            id=payload.id,
            type=request_type_from_wire(payload.type),
            requester=payload.requester,
            subject_entity_id=payload.subject_entity_id,
            description=payload.description,
            evidence_locations=payload.evidence_locations,
            status=LegalRequestStatus.submitted,
            created_at=utc_now(),
            history=[],
        )
        session.add(request)
        await session.flush()
        await session.refresh(request)
        return LegalRequestRead.model_validate(request)


@router.get("/requests", response_model=list[LegalRequestRead])
async def get_legal_requests(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[LegalRequestRead]:
    rows = (await session.scalars(select(LegalRequest))).all()
    return [LegalRequestRead.model_validate(row) for row in rows]


@router.put("/compliance/{record_id}", response_model=ComplianceRecordRead)
async def save_compliance_record(
    record_id: str,
    payload: SaveComplianceRecordRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ComplianceRecordRead:
    async with session.begin():
        record = await session.get(ComplianceRecord, record_id)
        if record is None:
            record = ComplianceRecord(
                id=record_id,
                framework=payload.framework,
                obligation=payload.obligation,
                status=payload.status,
                owner=payload.owner,
                review_due_at=payload.review_due_at,
                evidence_locations=payload.evidence_locations,
            )
            session.add(record)
            await session.flush()
            await session.refresh(record)
            return ComplianceRecordRead.model_validate(record)
        record.framework = payload.framework
        record.obligation = payload.obligation
        record.status = payload.status
        record.owner = payload.owner
        record.review_due_at = payload.review_due_at
        record.evidence_locations = payload.evidence_locations
        await session.flush()
        await session.refresh(record)
        return ComplianceRecordRead.model_validate(record)


@router.get("/compliance", response_model=list[ComplianceRecordRead])
async def get_compliance_records(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ComplianceRecordRead]:
    rows = (await session.scalars(select(ComplianceRecord))).all()
    return [ComplianceRecordRead.model_validate(row) for row in rows]

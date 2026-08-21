import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import STAFF_ROLES, require_roles
from app.db.session import get_db
from app.models.external_opportunity import ExternalOpportunity, VerificationStatus
from app.models.fraud_investigation import (
    CLOSED_CASE_STATUSES,
    FraudCase,
    FraudCaseStatus,
    FraudSubjectType,
    InvestigationRiskLevel,
    WatchlistEntry,
)
from app.models.provider import Provider, ProviderAdministrator, ProviderStatus
from app.schemas.fraud_investigation import (
    AddEvidenceRequest,
    AddNoteRequest,
    AddWatchlistEntryRequest,
    AppealRequest,
    AssignCaseRequest,
    CreateFraudCaseRequest,
    FraudAnalyticsRead,
    FraudCaseRead,
    WatchlistEntryRead,
)
from app.services.parsing import utc_now
from app.services.risk_scoring import RiskScoringInput, evaluate

router = APIRouter(prefix="/fraud-investigation", tags=["fraud investigation"])

any_authenticated = Depends(get_current_user)
# No current UI caller drives this feature yet - gated broadly to staff,
# matching the pattern used for other no-current-caller investigative
# surfaces, since it spans verification, security, and administration
# duties and no narrower "fraud investigator" role exists in this RBAC set.
staff_access = Depends(require_roles(*STAFF_ROLES))


async def _require_case(session: AsyncSession, case_id: str) -> FraudCase:
    case = await session.get(FraudCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Fraud case was not found.")
    return case


async def _automated_restriction(session: AsyncSession, case: FraudCase) -> None:
    if case.subject_type == FraudSubjectType.opportunity:
        try:
            opportunity_id = uuid.UUID(case.subject_id)
        except ValueError:
            return
        opportunity = await session.get(ExternalOpportunity, opportunity_id)
        if opportunity is not None:
            opportunity.verification_status = VerificationStatus.suspicious
    elif case.subject_type == FraudSubjectType.provider:
        try:
            provider_id = uuid.UUID(case.subject_id)
        except ValueError:
            return
        provider = await session.get(Provider, provider_id)
        if provider is not None:
            provider.status = ProviderStatus.suspended


@router.post("/cases", response_model=FraudCaseRead)
async def create_case(
    payload: CreateFraudCaseRequest,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> FraudCaseRead:
    async with session.begin():
        existing = await session.scalar(
            select(FraudCase).where(
                FraudCase.subject_type == payload.subject_type,
                FraudCase.subject_id == payload.subject_id,
                FraudCase.status.not_in(CLOSED_CASE_STATUSES),
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="An open fraud case already exists for this subject.",
            )
        risk = evaluate(
            RiskScoringInput(
                provider_risk=payload.risk_input.provider_risk,
                source_risk=payload.risk_input.source_risk,
                user_behaviour_risk=payload.risk_input.user_behaviour_risk,
                suspicious_domain=payload.risk_input.suspicious_domain,
                duplicate_account=payload.risk_input.duplicate_account,
                risky_link=payload.risk_input.risky_link,
                payment_request=payload.risk_input.payment_request,
                impersonation=payload.risk_input.impersonation,
            )
        )
        now = utc_now()
        case = FraudCase(
            id=uuid.uuid4().hex,
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            risk_overall=risk.overall,
            risk_level=risk.level,
            risk_provider=risk.provider_risk,
            risk_source=risk.source_risk,
            risk_user_behaviour=risk.user_behaviour_risk,
            risk_domain=risk.domain_risk,
            risk_link=risk.link_risk,
            risk_payment=risk.payment_risk,
            risk_impersonation=risk.impersonation_risk,
            risk_reasons=risk.reasons,
            status=FraudCaseStatus.opened,
            created_at=now,
            history=[f"Risk assessed at {now.isoformat()}."],
        )
        if risk.level == InvestigationRiskLevel.critical:
            await _automated_restriction(session, case)
            case.status = FraudCaseStatus.restricted
            case.history = [
                *case.history,
                "Critical automated control applied; security review required.",
            ]
        session.add(case)
        await session.flush()
        return FraudCaseRead.from_model(case)


@router.post("/cases/{case_id}/assign", response_model=FraudCaseRead)
async def assign_case(
    case_id: str,
    payload: AssignCaseRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> FraudCaseRead:
    async with session.begin():
        case = await _require_case(session, case_id)
        case.status = FraudCaseStatus.assigned
        case.assigned_investigator_id = payload.investigator_id
        case.history = [*case.history, f"Assigned to {payload.investigator_id}."]
        await session.flush()
        return FraudCaseRead.from_model(case)


@router.post("/cases/{case_id}/evidence", response_model=FraudCaseRead)
async def add_evidence(
    case_id: str,
    payload: AddEvidenceRequest,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> FraudCaseRead:
    async with session.begin():
        case = await _require_case(session, case_id)
        evidence_id = uuid.uuid4().hex
        case.evidence = [
            *case.evidence,
            {
                "id": evidence_id,
                "type": payload.type,
                "location": payload.location,
                "summary": payload.summary,
                "collected_at": utc_now().isoformat(),
                "collected_by": user.uid,
            },
        ]
        case.history = [*case.history, f"Evidence {evidence_id} collected."]
        await session.flush()
        return FraudCaseRead.from_model(case)


@router.post("/cases/{case_id}/notes", response_model=FraudCaseRead)
async def add_note(
    case_id: str,
    payload: AddNoteRequest,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> FraudCaseRead:
    async with session.begin():
        case = await _require_case(session, case_id)
        if case.assigned_investigator_id != user.uid:
            raise HTTPException(
                status_code=403,
                detail="Only the assigned investigator can add notes.",
            )
        case.status = FraudCaseStatus.investigating
        case.investigator_notes = [*case.investigator_notes, payload.note]
        await session.flush()
        return FraudCaseRead.from_model(case)


@router.post("/cases/{case_id}/restrict", response_model=FraudCaseRead)
async def restrict_case(
    case_id: str,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> FraudCaseRead:
    async with session.begin():
        case = await _require_case(session, case_id)
        if not case.evidence:
            raise HTTPException(
                status_code=409, detail="A restriction requires supporting evidence."
            )
        await _automated_restriction(session, case)
        case.status = FraudCaseStatus.restricted
        case.history = [*case.history, f"Restricted by {user.uid}."]
        await session.flush()
        return FraudCaseRead.from_model(case)


async def _can_appeal(session: AsyncSession, case: FraudCase, user: AuthenticatedUser) -> bool:
    if user.role in STAFF_ROLES:
        return True
    if case.subject_type == FraudSubjectType.user and case.subject_id == user.uid:
        return True
    if case.subject_type == FraudSubjectType.provider:
        try:
            provider_id = uuid.UUID(case.subject_id)
        except ValueError:
            return False
        provider = await session.get(Provider, provider_id)
        if provider is None:
            return False
        if provider.user_id == user.uid:
            return True
        admin = await session.scalar(
            select(ProviderAdministrator).where(
                ProviderAdministrator.provider_id == provider_id,
                ProviderAdministrator.user_id == user.uid,
            )
        )
        return admin is not None
    return False


@router.post("/cases/{case_id}/appeal", response_model=FraudCaseRead)
async def appeal_case(
    case_id: str,
    payload: AppealRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> FraudCaseRead:
    async with session.begin():
        case = await _require_case(session, case_id)
        if case.status != FraudCaseStatus.restricted:
            raise HTTPException(
                status_code=409, detail="Only a restricted subject can appeal."
            )
        if not await _can_appeal(session, case, user):
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to appeal this case.",
            )
        case.status = FraudCaseStatus.appealed
        case.appeal_reason = payload.reason
        case.history = [*case.history, "Appeal submitted."]
        await session.flush()
        return FraudCaseRead.from_model(case)


@router.post("/watchlist", status_code=204)
async def add_watchlist_entry(
    payload: AddWatchlistEntryRequest,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    normalized = payload.value.strip().lower()
    async with session.begin():
        rows = await session.scalars(
            select(WatchlistEntry).where(WatchlistEntry.subject_type == payload.subject_type)
        )
        if any(row.value.strip().lower() == normalized for row in rows.all()):
            raise HTTPException(status_code=409, detail="Watchlist entry already exists.")
        session.add(
            WatchlistEntry(
                id=uuid.uuid4().hex,
                subject_type=payload.subject_type,
                value=payload.value.strip(),
                reason=payload.reason,
                blocked=payload.blocked,
                created_at=utc_now(),
                created_by=user.uid,
            )
        )


@router.get("/watchlist/{subject_type}/blocked", response_model=bool)
async def is_blocked(
    subject_type: FraudSubjectType,
    value: str,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> bool:
    normalized = value.strip().lower()
    rows = await session.scalars(
        select(WatchlistEntry).where(
            WatchlistEntry.subject_type == subject_type, WatchlistEntry.blocked.is_(True)
        )
    )
    return any(row.value.strip().lower() == normalized for row in rows.all())


@router.get("/queue", response_model=list[FraudCaseRead])
async def queue(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[FraudCaseRead]:
    rows = await session.scalars(
        select(FraudCase).where(FraudCase.status.not_in(CLOSED_CASE_STATUSES))
    )
    return [FraudCaseRead.from_model(row) for row in rows.all()]


@router.get("/analytics", response_model=FraudAnalyticsRead)
async def analytics(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> FraudAnalyticsRead:
    cases = (await session.scalars(select(FraudCase))).all()
    watchlist = (await session.scalars(select(WatchlistEntry))).all()
    by_subject_type: dict[str, int] = {}
    for case in cases:
        key = case.subject_type.value
        by_subject_type[key] = by_subject_type.get(key, 0) + 1
    return FraudAnalyticsRead(
        open_cases=len([c for c in cases if c.status not in CLOSED_CASE_STATUSES]),
        critical_cases=len(
            [c for c in cases if c.risk_level == InvestigationRiskLevel.critical]
        ),
        restricted_subjects=len(
            [c for c in cases if c.status == FraudCaseStatus.restricted]
        ),
        watchlist_entries=len(watchlist),
        by_subject_type=by_subject_type,
    )

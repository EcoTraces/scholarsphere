from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.external_opportunity import ExternalOpportunity
from app.models.moderation import (
    CLOSED_STATUSES,
    ModerationCase,
    ModerationHistoryEntry,
    ModerationStatus,
    ModerationWarning,
    ReportedEntityType,
)
from app.models.provider import Provider
from app.schemas.moderation import (
    IssueWarningRequest,
    ModerationAnalyticsRead,
    ModerationAppealRequest,
    ModerationCaseRead,
    ModerationCaseSubmit,
    ModerationHistoryEntryRead,
    ModerationTransitionRequest,
    ModerationWarningRead,
    entity_type_from_wire,
    report_type_from_wire,
    status_from_wire,
)
from app.services.moderation_actions import apply_transition, is_closed
from app.services.parsing import utc_now

router = APIRouter(prefix="/moderation-cases", tags=["moderation"])
warnings_router = APIRouter(prefix="/moderation-warnings", tags=["moderation"])

any_authenticated = Depends(get_current_user)
moderation_access = Depends(require_roles("moderator", "administrator", "superAdministrator"))


async def _to_read(session: AsyncSession, case: ModerationCase) -> ModerationCaseRead:
    history = (
        await session.scalars(
            select(ModerationHistoryEntry)
            .where(ModerationHistoryEntry.case_id == case.id)
            .order_by(ModerationHistoryEntry.created_at.asc())
        )
    ).all()
    read = ModerationCaseRead.model_validate(case)
    read.history = [ModerationHistoryEntryRead.model_validate(entry) for entry in history]
    return read


@router.post("", response_model=ModerationCaseRead)
async def submit_report(
    payload: ModerationCaseSubmit,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationCaseRead:
    entity_type = entity_type_from_wire(payload.entity_type)
    report_type = report_type_from_wire(payload.report_type)
    async with session.begin():
        if entity_type in (ReportedEntityType.opportunity, ReportedEntityType.provider):
            try:
                entity_uuid = UUID(payload.entity_id)
            except ValueError as error:
                raise HTTPException(
                    status_code=404, detail="Reported entity not found."
                ) from error
            model = ExternalOpportunity if entity_type == ReportedEntityType.opportunity else Provider
            if await session.get(model, entity_uuid) is None:
                raise HTTPException(status_code=404, detail="Reported entity not found.")

        duplicate = await session.scalar(
            select(ModerationCase).where(
                ModerationCase.reporter_id == user.uid,
                ModerationCase.entity_type == entity_type,
                ModerationCase.entity_id == payload.entity_id,
                ModerationCase.report_type == report_type,
                ModerationCase.status.not_in(CLOSED_STATUSES),
            )
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=409, detail="An equivalent open report already exists."
            )

        case = ModerationCase(
            reporter_id=user.uid,
            entity_type=entity_type,
            entity_id=payload.entity_id,
            report_type=report_type,
            description=payload.description,
            evidence=[item.model_dump() for item in payload.evidence],
        )
        session.add(case)
        await session.flush()
        await session.refresh(case)
        return await _to_read(session, case)


@router.get("/queue", response_model=list[ModerationCaseRead])
async def get_queue(
    _: Annotated[AuthenticatedUser, moderation_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ModerationCaseRead]:
    rows = (
        await session.scalars(
            select(ModerationCase)
            .where(ModerationCase.status.not_in(CLOSED_STATUSES))
            .order_by(ModerationCase.created_at.asc())
        )
    ).all()
    return [await _to_read(session, row) for row in rows]


@router.get("/mine", response_model=list[ModerationCaseRead])
async def get_my_reports(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ModerationCaseRead]:
    rows = (
        await session.scalars(
            select(ModerationCase)
            .where(ModerationCase.reporter_id == user.uid)
            .order_by(ModerationCase.created_at.desc())
        )
    ).all()
    return [await _to_read(session, row) for row in rows]


@router.get("/analytics", response_model=ModerationAnalyticsRead)
async def get_analytics(
    _: Annotated[AuthenticatedUser, moderation_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationAnalyticsRead:
    cases = (await session.scalars(select(ModerationCase))).all()
    counts: dict[str, int] = {}
    for case in cases:
        counts[case.entity_id] = counts.get(case.entity_id, 0) + 1
    repeat_offenders = {entity_id: count for entity_id, count in counts.items() if count >= 2}
    return ModerationAnalyticsRead(
        total_reports=len(cases),
        open_reports=sum(1 for case in cases if not is_closed(case.status)),
        removed_content=sum(
            1 for case in cases if case.status == ModerationStatus.content_removed
        ),
        suspended_providers=sum(
            1 for case in cases if case.status == ModerationStatus.provider_suspended
        ),
        repeat_offenders=repeat_offenders,
    )


@router.post("/{case_id}/assign", response_model=ModerationCaseRead)
async def assign_case(
    case_id: UUID,
    user: Annotated[AuthenticatedUser, moderation_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationCaseRead:
    async with session.begin():
        case = await session.get(ModerationCase, case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="Report was not found.")
        await apply_transition(
            session,
            case,
            actor_id=user.uid,
            status=ModerationStatus.under_review,
            notes="Assigned to moderator.",
        )
        await session.flush()
        await session.refresh(case)
        return await _to_read(session, case)


@router.post("/{case_id}/transition", response_model=ModerationCaseRead)
async def transition_case(
    case_id: UUID,
    payload: ModerationTransitionRequest,
    user: Annotated[AuthenticatedUser, moderation_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationCaseRead:
    async with session.begin():
        case = await session.get(ModerationCase, case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="Report was not found.")
        await apply_transition(
            session,
            case,
            actor_id=user.uid,
            status=status_from_wire(payload.status),
            notes=payload.notes,
            hide_content=payload.hide_content,
        )
        await session.flush()
        await session.refresh(case)
        return await _to_read(session, case)


@router.post("/{case_id}/appeal", response_model=ModerationCaseRead)
async def appeal_case(
    case_id: UUID,
    payload: ModerationAppealRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationCaseRead:
    async with session.begin():
        case = await session.get(ModerationCase, case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="Report was not found.")
        if not is_closed(case.status):
            raise HTTPException(
                status_code=409, detail="Only decided cases can be appealed."
            )
        case.status = ModerationStatus.escalated
        case.appeal_reason = payload.reason
        session.add(
            ModerationHistoryEntry(
                case_id=case.id,
                status=ModerationStatus.escalated,
                actor_id=user.uid,
                notes=f"Appeal: {payload.reason}",
            )
        )
        await session.flush()
        await session.refresh(case)
        return await _to_read(session, case)


@router.post("/{case_id}/warning", response_model=ModerationWarningRead)
async def issue_warning(
    case_id: UUID,
    payload: IssueWarningRequest,
    user: Annotated[AuthenticatedUser, moderation_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ModerationWarningRead:
    async with session.begin():
        case = await session.get(ModerationCase, case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="Report was not found.")
        if case.entity_type == ReportedEntityType.opportunity:
            raise HTTPException(
                status_code=409, detail="Warnings can only be issued to providers or users."
            )
        warning = ModerationWarning(
            entity_type=case.entity_type,
            entity_id=case.entity_id,
            reason=payload.reason,
            issued_by=user.uid,
            issued_at=utc_now(),
            case_id=case.id,
        )
        session.add(warning)
        await apply_transition(
            session,
            case,
            actor_id=user.uid,
            status=ModerationStatus.resolved,
            notes=f"{case.entity_type.value} warning issued: {payload.reason}",
        )
        await session.flush()
        await session.refresh(warning)
        return ModerationWarningRead.model_validate(warning)


@warnings_router.get("", response_model=list[ModerationWarningRead])
async def get_warnings_for_entity(
    _: Annotated[AuthenticatedUser, moderation_access],
    session: Annotated[AsyncSession, Depends(get_db)],
    entity_type: str = Query(...),
    entity_id: str = Query(...),
) -> list[ModerationWarningRead]:
    rows = (
        await session.scalars(
            select(ModerationWarning).where(
                ModerationWarning.entity_type == entity_type_from_wire(entity_type),
                ModerationWarning.entity_id == entity_id,
            )
        )
    ).all()
    return [ModerationWarningRead.model_validate(row) for row in rows]

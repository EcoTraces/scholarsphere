from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.public_opportunities import _is_public
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import STAFF_ROLES, require_roles
from app.db.session import get_db
from app.models import Application, ExternalOpportunity
from app.schemas.application import (
    ApplicationCreate,
    ApplicationPage,
    ApplicationRead,
    ApplicationUpdate,
    stage_from_wire,
)

router = APIRouter(prefix="/applications", tags=["applications"])

any_authenticated = Depends(get_current_user)
staff_access = Depends(require_roles(*STAFF_ROLES))


@router.post("", response_model=ApplicationRead)
async def save_opportunity(
    payload: ApplicationCreate,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationRead:
    """Track an opportunity for the current user, snapshotting its current data.

    Idempotent: saving an already-saved opportunity returns the existing
    record unchanged rather than erroring or creating a duplicate.
    """
    async with session.begin():
        opportunity = await session.get(ExternalOpportunity, payload.opportunity_id)
        if opportunity is None or not _is_public(opportunity):
            raise HTTPException(status_code=404, detail="Opportunity not found.")
        existing = await session.scalar(
            select(Application).where(
                Application.user_id == user.uid,
                Application.opportunity_id == payload.opportunity_id,
            )
        )
        if existing is not None:
            return ApplicationRead.model_validate(existing)
        application = Application(
            user_id=user.uid,
            opportunity_id=opportunity.id,
            opportunity_title=opportunity.title,
            provider_name=opportunity.provider_name,
            deadline=opportunity.deadline,
        )
        session.add(application)
        await session.flush()
        await session.refresh(application)
        return ApplicationRead.model_validate(application)


@router.get("", response_model=list[ApplicationRead])
async def list_my_applications(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ApplicationRead]:
    rows = (
        await session.scalars(
            select(Application)
            .where(Application.user_id == user.uid)
            .order_by(Application.updated_at.desc())
        )
    ).all()
    return [ApplicationRead.model_validate(row) for row in rows]


@router.get("/admin", response_model=ApplicationPage)
async def list_all_applications(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
    user_id: str | None = None,
    stage: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ApplicationPage:
    filters = []
    if user_id:
        filters.append(Application.user_id == user_id)
    if stage:
        filters.append(Application.stage == stage_from_wire(stage))
    total = await session.scalar(select(func.count(Application.id)).where(*filters))
    rows = (
        await session.scalars(
            select(Application)
            .where(*filters)
            .order_by(Application.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ApplicationPage(
        items=[ApplicationRead.model_validate(row) for row in rows],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/by-opportunity/{opportunity_id}", response_model=ApplicationRead)
async def get_my_application_for_opportunity(
    opportunity_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationRead:
    application = await session.scalar(
        select(Application).where(
            Application.user_id == user.uid,
            Application.opportunity_id == opportunity_id,
        )
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application record not found.")
    return ApplicationRead.model_validate(application)


@router.patch("/{application_id}", response_model=ApplicationRead)
async def update_application(
    application_id: UUID,
    payload: ApplicationUpdate,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationRead:
    async with session.begin():
        application = await session.get(Application, application_id)
        if application is None or application.user_id != user.uid:
            raise HTTPException(status_code=404, detail="Application record not found.")
        application.stage = stage_from_wire(payload.stage)
        application.application_date = payload.application_date
        application.application_reference_number = payload.application_reference_number
        application.missing_documents = payload.missing_documents
        application.interview_date = payload.interview_date
        application.personal_notes = payload.personal_notes
        application.result_date = payload.result_date
        application.scholarship_value = payload.scholarship_value
        application.follow_up_actions = payload.follow_up_actions
        await session.flush()
        await session.refresh(application)
        return ApplicationRead.model_validate(application)

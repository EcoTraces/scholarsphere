from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.entitlements import require_entitlement
from app.db.session import get_db
from app.models.application import Application
from app.models.application_preparation import (
    PersonalizedChecklistItem,
    PremiumWorkspace,
    RequirementMatch,
)
from app.models.external_opportunity import ExternalOpportunity
from app.models.premium_billing import PremiumFeature
from app.schemas.application_preparation import (
    ChecklistItemRead,
    ChecklistItemUpdateRequest,
    ReadinessRead,
    RequirementMatchRead,
    WorkspaceCreateRequest,
    WorkspaceRead,
)
from app.services import application_preparation as prep_service
from app.services.readiness_score import compute_readiness

router = APIRouter(prefix="/application-preparation", tags=["application-preparation"])

any_authenticated = Depends(get_current_user)


async def _require_owned_workspace(
    session: AsyncSession, workspace_id: UUID, uid: str
) -> PremiumWorkspace:
    workspace = await session.get(PremiumWorkspace, workspace_id)
    if workspace is None or workspace.user_id != uid:
        raise HTTPException(status_code=404, detail="Workspace was not found.")
    return workspace


@router.post(
    "/workspaces",
    response_model=WorkspaceRead,
    status_code=201,
    dependencies=[Depends(require_entitlement(PremiumFeature.application_strategy))],
)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceRead:
    async with session.begin():
        application = await session.get(Application, payload.application_id)
        if application is None or application.user_id != user.uid:
            raise HTTPException(status_code=404, detail="Tracked application was not found.")
        existing = await session.scalar(
            select(PremiumWorkspace).where(PremiumWorkspace.application_id == payload.application_id)
        )
        if existing is not None:
            raise HTTPException(
                status_code=409, detail="A premium workspace already exists for this application."
            )

        workspace = await prep_service.create_workspace(
            session,
            user_id=user.uid,
            application_id=payload.application_id,
            category=payload.category,
            target_university=payload.target_university,
            target_program=payload.target_program,
        )
        await prep_service.generate_checklist(session, workspace)
        opportunity = await session.get(ExternalOpportunity, application.opportunity_id)
        if opportunity is not None:
            await prep_service.run_requirement_matching(session, workspace, opportunity)
        await session.refresh(workspace)
        return WorkspaceRead.model_validate(workspace)


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    workspace_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> WorkspaceRead:
    workspace = await _require_owned_workspace(session, workspace_id, user.uid)
    return WorkspaceRead.model_validate(workspace)


@router.post(
    "/workspaces/{workspace_id}/requirement-matching",
    response_model=list[RequirementMatchRead],
    dependencies=[Depends(require_entitlement(PremiumFeature.requirement_matching))],
)
async def refresh_requirement_matching(
    workspace_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[RequirementMatchRead]:
    async with session.begin():
        workspace = await _require_owned_workspace(session, workspace_id, user.uid)
        application = await session.get(Application, workspace.application_id)
        opportunity = (
            await session.get(ExternalOpportunity, application.opportunity_id)
            if application
            else None
        )
        if opportunity is None:
            raise HTTPException(
                status_code=409, detail="The tracked opportunity could not be found."
            )
        matches = await prep_service.run_requirement_matching(session, workspace, opportunity)
        return [RequirementMatchRead.model_validate(match) for match in matches]


@router.get(
    "/workspaces/{workspace_id}/requirement-matches",
    response_model=list[RequirementMatchRead],
    dependencies=[Depends(require_entitlement(PremiumFeature.requirement_matching))],
)
async def list_requirement_matches(
    workspace_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[RequirementMatchRead]:
    workspace = await _require_owned_workspace(session, workspace_id, user.uid)
    matches = (
        await session.scalars(
            select(RequirementMatch).where(RequirementMatch.workspace_id == workspace.id)
        )
    ).all()
    return [RequirementMatchRead.model_validate(match) for match in matches]


@router.get(
    "/workspaces/{workspace_id}/readiness",
    response_model=ReadinessRead,
    dependencies=[Depends(require_entitlement(PremiumFeature.readiness_score))],
)
async def get_readiness(
    workspace_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReadinessRead:
    workspace = await _require_owned_workspace(session, workspace_id, user.uid)
    breakdown = await compute_readiness(session, workspace)
    return ReadinessRead(
        profile_pct=breakdown.profile_pct,
        background_pct=breakdown.background_pct,
        documents_pct=breakdown.documents_pct,
        requirements_pct=breakdown.requirements_pct,
        checklist_pct=breakdown.checklist_pct,
        overall_pct=breakdown.overall_pct,
        weights=breakdown.weights,
    )


@router.get(
    "/workspaces/{workspace_id}/checklist",
    response_model=list[ChecklistItemRead],
    dependencies=[Depends(require_entitlement(PremiumFeature.personalized_checklist))],
)
async def list_checklist(
    workspace_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ChecklistItemRead]:
    workspace = await _require_owned_workspace(session, workspace_id, user.uid)
    items = (
        await session.scalars(
            select(PersonalizedChecklistItem)
            .where(PersonalizedChecklistItem.workspace_id == workspace.id)
            .order_by(PersonalizedChecklistItem.sort_order)
        )
    ).all()
    return [ChecklistItemRead.model_validate(item) for item in items]


@router.patch(
    "/workspaces/{workspace_id}/checklist/{item_id}",
    response_model=ChecklistItemRead,
    dependencies=[Depends(require_entitlement(PremiumFeature.personalized_checklist))],
)
async def update_checklist_item(
    workspace_id: UUID,
    item_id: UUID,
    payload: ChecklistItemUpdateRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ChecklistItemRead:
    async with session.begin():
        workspace = await _require_owned_workspace(session, workspace_id, user.uid)
        item = await session.get(PersonalizedChecklistItem, item_id)
        if item is None or item.workspace_id != workspace.id:
            raise HTTPException(status_code=404, detail="Checklist item was not found.")
        item.status = payload.status
        await session.flush()
        await session.refresh(item)
        return ChecklistItemRead.model_validate(item)

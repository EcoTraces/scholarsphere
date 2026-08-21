import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import STAFF_ROLES, require_roles
from app.db.session import get_db
from app.models.analytics import OpportunityViewEvent
from app.models.external_opportunity import ExternalOpportunity
from app.schemas.analytics import RecordOpportunityViewRequest
from app.services.parsing import utc_now

router = APIRouter(prefix="/analytics", tags=["analytics"])

any_authenticated = Depends(get_current_user)
staff_access = Depends(require_roles(*STAFF_ROLES))


@router.post("/opportunity-views", status_code=204)
async def record_opportunity_view(
    payload: RecordOpportunityViewRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    try:
        opportunity_id = uuid.UUID(payload.opportunity_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    async with session.begin():
        opportunity = await session.get(ExternalOpportunity, opportunity_id)
        if opportunity is None:
            raise HTTPException(status_code=404, detail="Opportunity not found.")
        session.add(
            OpportunityViewEvent(
                user_id=user.uid,
                opportunity_id=opportunity_id,
                viewed_at=utc_now(),
            )
        )
    return Response(status_code=204)


@router.get("/opportunity-views", response_model=dict[str, int])
async def opportunity_view_counts(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    rows = await session.execute(
        select(OpportunityViewEvent.opportunity_id, func.count())
        .group_by(OpportunityViewEvent.opportunity_id)
    )
    return {str(opportunity_id): count for opportunity_id, count in rows.all()}

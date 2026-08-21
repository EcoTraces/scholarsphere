import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import STAFF_ROLES
from app.db.session import get_db
from app.models.provider import Provider, ProviderAdministrator
from app.models.provider_analytics import EngagementEvent
from app.schemas.provider_analytics import (
    ProviderAnalyticsExportRead,
    ProviderAnalyticsSnapshotRead,
    RecordEngagementEventRequest,
)

router = APIRouter(prefix="/provider-analytics", tags=["provider analytics"])

any_authenticated = Depends(get_current_user)

_MINIMUM_COHORT_SIZE = 3


async def _can_view(session: AsyncSession, provider_id: uuid.UUID, user: AuthenticatedUser) -> bool:
    if user.role in STAFF_ROLES:
        return True
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


async def _snapshot(session: AsyncSession, provider_id: uuid.UUID) -> ProviderAnalyticsSnapshotRead:
    events = (
        await session.scalars(
            select(EngagementEvent).where(EngagementEvent.provider_id == provider_id)
        )
    ).all()
    distinct_users = {event.user_id for event in events if event.user_id is not None}
    suppressed = len(distinct_users) < _MINIMUM_COHORT_SIZE

    def group(select_key) -> dict[str, int]:
        if suppressed:
            return {}
        result: dict[str, int] = {}
        for event in events:
            key = select_key(event)
            result[key] = result.get(key, 0) + 1
        return result

    def count(kind: str) -> int:
        return len([event for event in events if event.kind == kind])

    return ProviderAnalyticsSnapshotRead(
        views=count("view"),
        saves=count("save"),
        application_clicks=count("application_click"),
        countries=group(lambda event: event.country),
        study_levels=group(lambda event: event.study_level),
        fields=group(lambda event: event.field),
        suppressed=suppressed,
    )


@router.post("/events", status_code=204)
async def record_event(
    payload: RecordEngagementEventRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    try:
        provider_id = uuid.UUID(payload.provider_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Provider not found.")
    async with session.begin():
        provider = await session.get(Provider, provider_id)
        if provider is None:
            raise HTTPException(status_code=404, detail="Provider not found.")
        session.add(
            EngagementEvent(
                provider_id=provider_id,
                opportunity_id=payload.opportunity_id,
                kind=payload.kind,
                country=payload.country,
                study_level=payload.study_level,
                field=payload.field,
                occurred_at=payload.occurred_at,
                user_id=user.uid if payload.identifiable_sharing_consent else None,
                identifiable_sharing_consent=payload.identifiable_sharing_consent,
            )
        )
    return Response(status_code=204)


@router.get("/{provider_id}/snapshot", response_model=ProviderAnalyticsSnapshotRead)
async def snapshot(
    provider_id: uuid.UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderAnalyticsSnapshotRead:
    if not await _can_view(session, provider_id, user):
        raise HTTPException(
            status_code=403, detail="You are not an administrator of this provider."
        )
    return await _snapshot(session, provider_id)


@router.get("/{provider_id}/export", response_model=ProviderAnalyticsExportRead)
async def export_csv(
    provider_id: uuid.UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderAnalyticsExportRead:
    if not await _can_view(session, provider_id, user):
        raise HTTPException(
            status_code=403, detail="You are not an administrator of this provider."
        )
    data = await _snapshot(session, provider_id)
    csv = (
        "metric,value\n"
        f"views,{data.views}\n"
        f"saves,{data.saves}\n"
        f"application_clicks,{data.application_clicks}\n"
    )
    return ProviderAnalyticsExportRead(csv=csv)

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import STAFF_ROLES, require_roles
from app.db.session import get_db
from app.models.recommendation_governance import (
    PersonalizationControls,
    RecommendationFeedback,
    RecommendationHistoryEntry,
)
from app.schemas.recommendation_governance import (
    PersonalizationControlsRead,
    PersonalizationControlsSave,
    RecommendationFeedbackRead,
    RecommendationHistoryRead,
    RecommendationQualityReportRead,
    RecordFeedbackRequest,
    RecordHistoryRequest,
    feedback_type_from_wire,
)
from app.services.parsing import utc_now

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

any_authenticated = Depends(get_current_user)
# qualityReport() aggregates across every user's history/feedback and has no
# current UI caller (no admin screen consumes it yet) - gated to staff,
# matching the pattern used for other no-current-caller aggregate endpoints.
staff_access = Depends(require_roles(*STAFF_ROLES))

_DEFAULT_CONTROLS = PersonalizationControlsRead(
    behavioural_recommendations_enabled=True,
    preferred_countries=[],
    opportunity_categories=[],
    hidden_opportunity_ids=[],
)


@router.get("/controls", response_model=PersonalizationControlsRead)
async def get_controls(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PersonalizationControlsRead:
    controls = await session.get(PersonalizationControls, user.uid)
    if controls is None:
        return _DEFAULT_CONTROLS
    return PersonalizationControlsRead.model_validate(controls)


@router.put("/controls", response_model=PersonalizationControlsRead)
async def save_controls(
    payload: PersonalizationControlsSave,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PersonalizationControlsRead:
    async with session.begin():
        controls = await session.get(PersonalizationControls, user.uid)
        if controls is None:
            controls = PersonalizationControls(user_id=user.uid)
            session.add(controls)
        controls.behavioural_recommendations_enabled = (
            payload.behavioural_recommendations_enabled
        )
        controls.preferred_countries = payload.preferred_countries
        controls.opportunity_categories = payload.opportunity_categories
        controls.hidden_opportunity_ids = payload.hidden_opportunity_ids
        controls.updated_at = utc_now()
        await session.flush()
        await session.refresh(controls)
        return PersonalizationControlsRead.model_validate(controls)


@router.post("/history", status_code=204)
async def record_history(
    payload: RecordHistoryRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    async with session.begin():
        session.add(
            RecommendationHistoryEntry(
                user_id=user.uid,
                opportunity_id=payload.opportunity_id,
                score=payload.score,
                labels=payload.labels,
                generated_at=payload.generated_at,
                host_country=payload.host_country,
            )
        )
    return Response(status_code=204)


@router.get("/history", response_model=list[RecommendationHistoryRead])
async def get_history(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[RecommendationHistoryRead]:
    rows = await session.scalars(
        select(RecommendationHistoryEntry)
        .where(RecommendationHistoryEntry.user_id == user.uid)
        .order_by(RecommendationHistoryEntry.generated_at.desc())
    )
    return [RecommendationHistoryRead.model_validate(row) for row in rows.all()]


@router.delete("/history", status_code=204)
async def reset_history(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    async with session.begin():
        rows = await session.scalars(
            select(RecommendationHistoryEntry).where(
                RecommendationHistoryEntry.user_id == user.uid
            )
        )
        for row in rows.all():
            await session.delete(row)
    return Response(status_code=204)


@router.post("/feedback", status_code=204)
async def record_feedback(
    payload: RecordFeedbackRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    feedback_type = feedback_type_from_wire(payload.type)
    async with session.begin():
        session.add(
            RecommendationFeedback(
                user_id=user.uid,
                opportunity_id=payload.opportunity_id,
                type=feedback_type,
                created_at=utc_now(),
                comment=payload.comment,
            )
        )
        if feedback_type.value in ("dismissed", "notRelevant"):
            controls = await session.get(PersonalizationControls, user.uid)
            if controls is None:
                # Column defaults only apply at flush, not on direct
                # construction, so set every non-nullable field explicitly
                # rather than relying on `default=` before the read below.
                controls = PersonalizationControls(
                    user_id=user.uid,
                    behavioural_recommendations_enabled=True,
                    preferred_countries=[],
                    opportunity_categories=[],
                    hidden_opportunity_ids=[],
                    updated_at=utc_now(),
                )
                session.add(controls)
            hidden = set(controls.hidden_opportunity_ids)
            hidden.add(payload.opportunity_id)
            controls.hidden_opportunity_ids = sorted(hidden)
            controls.updated_at = utc_now()
    return Response(status_code=204)


@router.get("/feedback", response_model=list[RecommendationFeedbackRead])
async def get_feedback(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[RecommendationFeedbackRead]:
    rows = await session.scalars(
        select(RecommendationFeedback).where(RecommendationFeedback.user_id == user.uid)
    )
    return [RecommendationFeedbackRead.model_validate(row) for row in rows.all()]


@router.get("/quality-report", response_model=RecommendationQualityReportRead)
async def quality_report(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RecommendationQualityReportRead:
    history = (await session.scalars(select(RecommendationHistoryEntry))).all()
    feedback = (await session.scalars(select(RecommendationFeedback))).all()
    total = len(history)
    dismissed = [
        item
        for item in feedback
        if item.type.value in ("dismissed", "notRelevant")
    ]
    helpful = [item for item in feedback if item.type.value == "helpful"]
    sponsored = [item for item in history if "sponsoredOpportunity" in item.labels]
    inappropriate = [item for item in feedback if item.type.value == "inappropriate"]
    return RecommendationQualityReportRead(
        generated_count=total,
        dismissal_rate=0 if total == 0 else len(dismissed) / total,
        helpful_rate=0 if not feedback else len(helpful) / len(feedback),
        country_diversity=len({item.host_country for item in history}),
        sponsored_share=0 if total == 0 else len(sponsored) / total,
        inappropriate_reports=len(inappropriate),
    )

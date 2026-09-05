from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import require_permissions
from app.db.session import get_db
from app.models.testimonial import (
    PUBLIC_STATUSES,
    Testimonial,
    TestimonialModerationHistory,
    TestimonialStatus,
    TestimonialVerificationStatus,
)
from app.schemas.testimonial import (
    TestimonialAdminPage,
    TestimonialAdminRead,
    TestimonialDetailRead,
    TestimonialDraftRequest,
    TestimonialInternalNotesRequest,
    TestimonialModerationDecisionRequest,
    TestimonialModerationHistoryItem,
    TestimonialOwnRead,
    TestimonialPage,
    TestimonialReactionRequest,
    TestimonialStatsRead,
    TestimonialSubmitRequest,
    TestimonialSummaryRead,
    TestimonialVerifyRequest,
)
import app.services.document_storage as document_storage
import app.services.testimonial_service as testimonial_service

any_authenticated = Depends(get_current_user)
moderate_content = Depends(require_permissions("moderateContent"))

router = APIRouter(prefix="/success-stories", tags=["success stories"])
own_router = APIRouter(prefix="/testimonials/me", tags=["my testimonials"])
admin_router = APIRouter(prefix="/admin/testimonials", tags=["admin testimonials"])


_SORTS = {
    "featured": (Testimonial.featured.desc(), Testimonial.created_at.desc()),
    "recent": (Testimonial.created_at.desc(),),
    "most_viewed": (Testimonial.view_count.desc(),),
    "verified_first": (
        (Testimonial.verification_status == TestimonialVerificationStatus.verified).desc(),
        Testimonial.created_at.desc(),
    ),
}


# --------------------------------------------------------------------------
# Public (any signed-in user - matches this backend's existing
# "public_opportunities" convention of requiring authentication but no
# special role for browsing, see app/api/routes/public_opportunities.py)
# --------------------------------------------------------------------------


@router.get("", response_model=TestimonialPage)
async def list_success_stories(
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    opportunity_type: Annotated[str | None, Query(max_length=128)] = None,
    country: Annotated[str | None, Query(max_length=255)] = None,
    field_of_study: Annotated[str | None, Query(max_length=255)] = None,
    degree_level: Annotated[str | None, Query(max_length=128)] = None,
    success_year: Annotated[int | None, Query(ge=1990, le=2100)] = None,
    verified_only: bool = False,
    featured_only: bool = False,
    sort: Annotated[str, Query()] = "recent",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> TestimonialPage:
    """Never returns a story whose status isn't in `PUBLIC_STATUSES` -
    draft/submitted/under_review/changes_requested/rejected/withdrawn
    stories are invisible here regardless of any other filter (Phase
    16's "avoid exposing internal moderation states publicly").
    """
    filters = [Testimonial.status.in_(PUBLIC_STATUSES)]
    if keyword:
        like = f"%{keyword}%"
        filters.append(
            Testimonial.opportunity_name.ilike(like)
            | Testimonial.university.ilike(like)
            | Testimonial.outcome_narrative.ilike(like)
            | Testimonial.impact.ilike(like)
        )
    if opportunity_type:
        filters.append(Testimonial.opportunity_type == opportunity_type)
    if country:
        filters.append(Testimonial.country == country)
    if field_of_study:
        filters.append(Testimonial.field_of_study == field_of_study)
    if degree_level:
        filters.append(Testimonial.degree_level == degree_level)
    if success_year is not None:
        filters.append(Testimonial.success_year == success_year)
    if verified_only:
        filters.append(Testimonial.verification_status == TestimonialVerificationStatus.verified)
    if featured_only:
        filters.append(Testimonial.featured.is_(True))

    order_by = _SORTS.get(sort, _SORTS["recent"])
    total = await session.scalar(select(func.count(Testimonial.id)).where(*filters)) or 0
    rows = (
        await session.scalars(
            select(Testimonial)
            .where(*filters)
            .order_by(*order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return TestimonialPage(
        items=[TestimonialSummaryRead.from_model(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=TestimonialStatsRead)
async def get_success_story_stats(
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialStatsRead:
    return TestimonialStatsRead(**await testimonial_service.public_stats(session))


async def _get_public_row(session: AsyncSession, slug: str) -> Testimonial:
    row = await session.scalar(select(Testimonial).where(Testimonial.slug == slug))
    if row is None or row.status not in PUBLIC_STATUSES:
        raise HTTPException(status_code=404, detail="Success story not found.")
    return row


@router.get("/{slug}", response_model=TestimonialDetailRead)
async def get_success_story(
    slug: str,
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialDetailRead:
    async with session.begin():
        row = await _get_public_row(session, slug)
        await testimonial_service.record_view(session, row=row)
        return TestimonialDetailRead.from_model(row)


@router.get("/{slug}/related", response_model=list[TestimonialSummaryRead])
async def get_related_success_stories(
    slug: str,
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=12)] = 4,
) -> list[TestimonialSummaryRead]:
    row = await _get_public_row(session, slug)
    rows = (
        await session.scalars(
            select(Testimonial)
            .where(
                Testimonial.status.in_(PUBLIC_STATUSES),
                Testimonial.id != row.id,
                (Testimonial.opportunity_type == row.opportunity_type)
                | (Testimonial.country == row.country),
            )
            .order_by(Testimonial.featured.desc(), Testimonial.created_at.desc())
            .limit(limit)
        )
    ).all()
    return [TestimonialSummaryRead.from_model(item) for item in rows]


@router.post("/{slug}/react", response_model=TestimonialDetailRead)
async def react_to_success_story(
    slug: str,
    payload: TestimonialReactionRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialDetailRead:
    async with session.begin():
        row = await _get_public_row(session, slug)
        try:
            row = await testimonial_service.set_reaction(
                session, user_id=user.uid, row=row, reaction_type=payload.reaction_type
            )
        except testimonial_service.TestimonialError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return TestimonialDetailRead.from_model(row)


@router.delete("/{slug}/react", response_model=TestimonialDetailRead)
async def remove_success_story_reaction(
    slug: str,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialDetailRead:
    async with session.begin():
        row = await _get_public_row(session, slug)
        row = await testimonial_service.remove_reaction(session, user_id=user.uid, row=row)
        return TestimonialDetailRead.from_model(row)


# --------------------------------------------------------------------------
# Own (the caller's own submissions, any status)
# --------------------------------------------------------------------------


async def _get_own_row(session: AsyncSession, user_id: str, testimonial_id: UUID) -> Testimonial:
    row = await session.get(Testimonial, testimonial_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=404, detail="Testimonial not found.")
    return row


@own_router.get("", response_model=list[TestimonialOwnRead])
async def list_my_testimonials(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[TestimonialOwnRead]:
    rows = (
        await session.scalars(
            select(Testimonial)
            .where(Testimonial.user_id == user.uid)
            .order_by(Testimonial.created_at.desc())
        )
    ).all()
    return [TestimonialOwnRead.model_validate(row) for row in rows]


@own_router.get("/{testimonial_id}", response_model=TestimonialOwnRead)
async def get_my_testimonial(
    testimonial_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialOwnRead:
    row = await _get_own_row(session, user.uid, testimonial_id)
    return TestimonialOwnRead.model_validate(row)


@own_router.post("/draft", response_model=TestimonialOwnRead)
async def create_draft(
    payload: TestimonialDraftRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialOwnRead:
    async with session.begin():
        row = await testimonial_service.save_draft(
            session, user_id=user.uid, testimonial_id=None, payload=payload
        )
        return TestimonialOwnRead.model_validate(row)


@own_router.put("/{testimonial_id}/draft", response_model=TestimonialOwnRead)
async def update_draft(
    testimonial_id: UUID,
    payload: TestimonialDraftRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialOwnRead:
    async with session.begin():
        try:
            row = await testimonial_service.save_draft(
                session, user_id=user.uid, testimonial_id=testimonial_id, payload=payload
            )
        except testimonial_service.TestimonialError as error:
            status_code = 404 if str(error) == "not_found" else 409
            raise HTTPException(status_code=status_code, detail=str(error)) from error
        return TestimonialOwnRead.model_validate(row)


@own_router.post("/{testimonial_id}/submit", response_model=TestimonialOwnRead)
async def submit_testimonial(
    testimonial_id: UUID,
    payload: TestimonialSubmitRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialOwnRead:
    async with session.begin():
        try:
            row = await testimonial_service.submit(
                session,
                user_id=user.uid,
                testimonial_id=testimonial_id,
                consent_confirmed=payload.consent_confirmed,
            )
        except testimonial_service.TestimonialError as error:
            detail = str(error)
            status_code = 404 if detail == "not_found" else 422
            raise HTTPException(status_code=status_code, detail=detail) from error
        return TestimonialOwnRead.model_validate(row)


@own_router.post("/{testimonial_id}/withdraw", response_model=TestimonialOwnRead)
async def withdraw_testimonial(
    testimonial_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialOwnRead:
    async with session.begin():
        try:
            row = await testimonial_service.withdraw(
                session, user_id=user.uid, testimonial_id=testimonial_id
            )
        except testimonial_service.TestimonialError as error:
            detail = str(error)
            status_code = 404 if detail == "not_found" else 409
            raise HTTPException(status_code=status_code, detail=detail) from error
        return TestimonialOwnRead.model_validate(row)


@own_router.get("/{testimonial_id}/evidence-url")
async def get_my_evidence_url(
    testimonial_id: UUID,
    path: Annotated[str, Query()],
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    row = await _get_own_row(session, user.uid, testimonial_id)
    if path not in row.evidence_storage_paths:
        raise HTTPException(status_code=404, detail="Evidence file not found.")
    try:
        url = document_storage.generate_download_url(path)
    except document_storage.DocumentDownloadUrlError as error:
        raise HTTPException(status_code=503, detail="Evidence download is temporarily unavailable.") from error
    return {"url": url, "expires_in_minutes": document_storage.DEFAULT_EXPIRES_IN_MINUTES}


# --------------------------------------------------------------------------
# Admin moderation (moderateContent permission)
# --------------------------------------------------------------------------


@admin_router.get("", response_model=TestimonialAdminPage)
async def list_testimonials_for_moderation(
    _: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    opportunity_type: Annotated[str | None, Query(max_length=128)] = None,
    country: Annotated[str | None, Query(max_length=255)] = None,
    verification_status: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> TestimonialAdminPage:
    filters = []
    if status_filter:
        try:
            filters.append(Testimonial.status == TestimonialStatus(status_filter))
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Unknown status filter.") from error
    if opportunity_type:
        filters.append(Testimonial.opportunity_type == opportunity_type)
    if country:
        filters.append(Testimonial.country == country)
    if verification_status:
        try:
            filters.append(
                Testimonial.verification_status == TestimonialVerificationStatus(verification_status)
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Unknown verification_status filter.") from error

    total = await session.scalar(select(func.count(Testimonial.id)).where(*filters)) or 0
    rows = (
        await session.scalars(
            select(Testimonial)
            .where(*filters)
            .order_by(Testimonial.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return TestimonialAdminPage(
        items=[TestimonialAdminRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def _get_admin_row(session: AsyncSession, testimonial_id: UUID) -> Testimonial:
    row = await session.get(Testimonial, testimonial_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Testimonial not found.")
    return row


@admin_router.get("/{testimonial_id}", response_model=TestimonialAdminRead)
async def get_testimonial_for_moderation(
    testimonial_id: UUID,
    _: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialAdminRead:
    row = await _get_admin_row(session, testimonial_id)
    return TestimonialAdminRead.model_validate(row)


@admin_router.get("/{testimonial_id}/history", response_model=list[TestimonialModerationHistoryItem])
async def get_testimonial_moderation_history(
    testimonial_id: UUID,
    _: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[TestimonialModerationHistoryItem]:
    await _get_admin_row(session, testimonial_id)
    rows = (
        await session.scalars(
            select(TestimonialModerationHistory)
            .where(TestimonialModerationHistory.testimonial_id == testimonial_id)
            .order_by(TestimonialModerationHistory.created_at)
        )
    ).all()
    return [TestimonialModerationHistoryItem.model_validate(item) for item in rows]


@admin_router.get("/{testimonial_id}/evidence-url")
async def get_admin_evidence_url(
    testimonial_id: UUID,
    path: Annotated[str, Query()],
    _: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    row = await _get_admin_row(session, testimonial_id)
    if path not in row.evidence_storage_paths:
        raise HTTPException(status_code=404, detail="Evidence file not found.")
    try:
        url = document_storage.generate_download_url(path)
    except document_storage.DocumentDownloadUrlError as error:
        raise HTTPException(status_code=503, detail="Evidence download is temporarily unavailable.") from error
    return {"url": url, "expires_in_minutes": document_storage.DEFAULT_EXPIRES_IN_MINUTES}


@admin_router.post("/{testimonial_id}/review", response_model=TestimonialAdminRead)
async def mark_under_review(
    testimonial_id: UUID,
    user: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialAdminRead:
    async with session.begin():
        row = await _get_admin_row(session, testimonial_id)
        try:
            row = await testimonial_service.mark_under_review(session, actor_id=user.uid, row=row)
        except testimonial_service.TestimonialError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return TestimonialAdminRead.model_validate(row)


@admin_router.post("/{testimonial_id}/approve", response_model=TestimonialAdminRead)
async def approve_testimonial(
    testimonial_id: UUID,
    payload: TestimonialModerationDecisionRequest,
    user: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialAdminRead:
    async with session.begin():
        row = await _get_admin_row(session, testimonial_id)
        try:
            row = await testimonial_service.approve(
                session, actor_id=user.uid, row=row, notes=payload.reason
            )
        except testimonial_service.TestimonialError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return TestimonialAdminRead.model_validate(row)


@admin_router.post("/{testimonial_id}/reject", response_model=TestimonialAdminRead)
async def reject_testimonial(
    testimonial_id: UUID,
    payload: TestimonialModerationDecisionRequest,
    user: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialAdminRead:
    async with session.begin():
        row = await _get_admin_row(session, testimonial_id)
        try:
            row = await testimonial_service.reject(
                session, actor_id=user.uid, row=row, reason=payload.reason
            )
        except testimonial_service.TestimonialError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return TestimonialAdminRead.model_validate(row)


@admin_router.post("/{testimonial_id}/request-changes", response_model=TestimonialAdminRead)
async def request_testimonial_changes(
    testimonial_id: UUID,
    payload: TestimonialModerationDecisionRequest,
    user: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialAdminRead:
    async with session.begin():
        row = await _get_admin_row(session, testimonial_id)
        try:
            row = await testimonial_service.request_changes(
                session, actor_id=user.uid, row=row, reason=payload.reason
            )
        except testimonial_service.TestimonialError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return TestimonialAdminRead.model_validate(row)


@admin_router.post("/{testimonial_id}/verify", response_model=TestimonialAdminRead)
async def verify_testimonial(
    testimonial_id: UUID,
    payload: TestimonialVerifyRequest,
    user: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialAdminRead:
    async with session.begin():
        row = await _get_admin_row(session, testimonial_id)
        try:
            row = await testimonial_service.verify(
                session,
                actor_id=user.uid,
                row=row,
                verification_method=payload.verification_method,
                notes=payload.notes,
            )
        except testimonial_service.TestimonialError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return TestimonialAdminRead.model_validate(row)


@admin_router.post("/{testimonial_id}/feature", response_model=TestimonialAdminRead)
async def feature_testimonial(
    testimonial_id: UUID,
    user: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialAdminRead:
    async with session.begin():
        row = await _get_admin_row(session, testimonial_id)
        try:
            row = await testimonial_service.set_featured(session, actor_id=user.uid, row=row, featured=True)
        except testimonial_service.TestimonialError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return TestimonialAdminRead.model_validate(row)


@admin_router.post("/{testimonial_id}/unfeature", response_model=TestimonialAdminRead)
async def unfeature_testimonial(
    testimonial_id: UUID,
    user: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialAdminRead:
    async with session.begin():
        row = await _get_admin_row(session, testimonial_id)
        row = await testimonial_service.set_featured(session, actor_id=user.uid, row=row, featured=False)
        return TestimonialAdminRead.model_validate(row)


@admin_router.put("/{testimonial_id}/notes", response_model=TestimonialAdminRead)
async def update_internal_notes(
    testimonial_id: UUID,
    payload: TestimonialInternalNotesRequest,
    user: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialAdminRead:
    async with session.begin():
        row = await _get_admin_row(session, testimonial_id)
        row = await testimonial_service.set_internal_notes(
            session, actor_id=user.uid, row=row, notes=payload.notes
        )
        return TestimonialAdminRead.model_validate(row)


@admin_router.post("/{testimonial_id}/archive", response_model=TestimonialAdminRead)
async def archive_testimonial(
    testimonial_id: UUID,
    payload: TestimonialModerationDecisionRequest,
    user: Annotated[AuthenticatedUser, moderate_content],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TestimonialAdminRead:
    async with session.begin():
        row = await _get_admin_row(session, testimonial_id)
        try:
            row = await testimonial_service.archive(
                session, actor_id=user.uid, row=row, reason=payload.reason
            )
        except testimonial_service.TestimonialError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return TestimonialAdminRead.model_validate(row)

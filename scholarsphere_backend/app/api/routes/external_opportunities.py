from collections import Counter
from datetime import date, datetime, timedelta
import logging
from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.auth import AuthenticatedUser
from app.core.http_client import ExternalAPIError
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models import (
    ExternalOpportunity,
    ImportAuditLog,
    OpportunitySource,
    OpportunitySyncHistory,
    VerificationHistory,
    VerificationReview,
)
from app.models.external_opportunity import PublicationStatus, SyncStatus, VerificationStatus
from app.schemas.external_opportunity import ImportStatistics, NormalizedExternalOpportunity
from app.schemas.external_source import (
    AdminOpportunityPage,
    DiscoverySummary,
    OpportunityEditRequest,
    OpportunityEditResponse,
    OpportunityNoteRequest,
    PendingOpportunityItem,
    PendingOpportunityPage,
    OpportunityState,
    PublicationRequest,
    SourceStateRequest,
    SourceHealth,
    SourceSummary,
    SyncHistoryPage,
    SyncQueued,
    VerificationActivityDay,
    VerificationDecisionRequest,
    VerificationReviewState,
    VerificationSummary,
)
from app.schemas.opportunity_public import (
    OpportunityEvidence,
    VerificationHistoryItem,
    VerificationHistoryPage,
)
from app.services.eu_funding import EUFundingSource
from app.services.audit import append_audit
from app.services.verification_confidence import ConfidenceAssessment, assess_confidence
from app.services.evidence import build_opportunity_evidence
from app.services.parsing import sanitize_html
from app.services.grants_gov import GrantsGovSource
from app.services.opportunity_import import ImportConflict, import_opportunities
from app.services.parsing import utc_now
from app.services.reliefweb import ReliefWebJobsSource, ReliefWebTrainingSource
from app.services.simpler_grants import SimplerGrantsSource
from app.services.source_registry import seed_opportunity_sources
from app.services.usajobs import UsaJobsSource
from app.tasks.opportunity_sync import queue_source_sync

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/external-opportunities",
    tags=["external opportunities"],
)

preview_access = require_roles(
    "verificationOfficer",
    "administrator",
    "superAdministrator",
)
import_access = require_roles(
    "verificationOfficer",
    "administrator",
    "superAdministrator",
)
admin_access = require_roles("administrator", "superAdministrator")

_DECISION_STATUS: dict[str, VerificationStatus] = {
    "approved": VerificationStatus.verified,
    "rejected": VerificationStatus.rejected,
    "reverification_required": VerificationStatus.reverification_required,
    "expired": VerificationStatus.expired,
    "source_unavailable": VerificationStatus.source_unavailable,
    "suspicious": VerificationStatus.suspicious,
}

_EDITABLE_FIELDS = (
    "title",
    "description",
    "opening_date",
    "deadline",
    "funding_type",
    "award_floor",
    "award_ceiling",
    "currency",
    "official_source_url",
    "official_application_url",
)


@router.get(
    "/grants-gov/preview",
    response_model=list[NormalizedExternalOpportunity],
)
async def preview_grants_gov(
    _: Annotated[AuthenticatedUser, Depends(preview_access)],
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> list[NormalizedExternalOpportunity]:
    """Normalize a Grants.gov page without persisting any records."""
    try:
        return await GrantsGovSource().collect(
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
    except ExternalAPIError as error:
        raise _external_error(error) from error


@router.get(
    "/simpler-grants/preview",
    response_model=list[NormalizedExternalOpportunity],
)
async def preview_simpler_grants(
    _: Annotated[AuthenticatedUser, Depends(preview_access)],
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    statuses: Annotated[list[str] | None, Query()] = None,
    sort_field: Literal["post_date", "close_date"] = "post_date",
    sort_direction: Literal["ascending", "descending"] = "descending",
) -> list[NormalizedExternalOpportunity]:
    """Normalize a Simpler.Grants.gov page without persistence."""
    try:
        return await SimplerGrantsSource().collect(
            keyword=keyword,
            page=page,
            page_size=page_size,
            statuses=statuses,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )
    except ExternalAPIError as error:
        raise _external_error(error) from error


@router.get(
    "/eu-funding/preview",
    response_model=list[NormalizedExternalOpportunity],
)
async def preview_eu_funding(
    _: Annotated[AuthenticatedUser, Depends(preview_access)],
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    type_codes: Annotated[list[str] | None, Query()] = None,
    status_codes: Annotated[list[str] | None, Query()] = None,
    programme_period: Annotated[str | None, Query(max_length=32)] = None,
    language: Annotated[str | None, Query(min_length=2, max_length=10)] = None,
    sort_field: Literal["startDate", "deadlineDate"] = "startDate",
    sort_direction: Literal["ASC", "DESC"] = "DESC",
) -> list[NormalizedExternalOpportunity]:
    """Normalize an EU Funding & Tenders page without persistence."""
    try:
        return await EUFundingSource().collect(
            keyword=keyword,
            page=page,
            page_size=page_size,
            type_codes=type_codes,
            status_codes=status_codes,
            programme_period=programme_period,
            language=language,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )
    except ExternalAPIError as error:
        raise _external_error(error) from error


@router.post("/grants-gov/import", response_model=ImportStatistics)
async def import_grants_gov(
    user: Annotated[AuthenticatedUser, Depends(import_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ImportStatistics:
    try:
        records = await GrantsGovSource().collect_for_import(
            keyword=keyword, page=page, page_size=page_size
        )
        return await import_opportunities(
            session, records, source_code="grants_gov", actor_id=user.uid
        )
    except ImportConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ExternalAPIError as error:
        raise _external_error(error) from error


@router.post("/simpler-grants/import", response_model=ImportStatistics)
async def import_simpler_grants(
    user: Annotated[AuthenticatedUser, Depends(import_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    statuses: Annotated[list[str] | None, Query()] = None,
    sort_field: Literal["post_date", "close_date"] = "post_date",
    sort_direction: Literal["ascending", "descending"] = "descending",
) -> ImportStatistics:
    try:
        records = await SimplerGrantsSource().collect_for_import(
            keyword=keyword,
            page=page,
            page_size=page_size,
            statuses=statuses,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )
        return await import_opportunities(
            session, records, source_code="simpler_grants", actor_id=user.uid
        )
    except ImportConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ExternalAPIError as error:
        raise _external_error(error) from error


@router.post("/eu-funding/import", response_model=ImportStatistics)
async def import_eu_funding(
    user: Annotated[AuthenticatedUser, Depends(import_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    type_codes: Annotated[list[str] | None, Query()] = None,
    status_codes: Annotated[list[str] | None, Query()] = None,
    programme_period: Annotated[str | None, Query(max_length=32)] = None,
    language: Annotated[str | None, Query(min_length=2, max_length=10)] = None,
    sort_field: Literal["startDate", "deadlineDate"] = "startDate",
    sort_direction: Literal["ASC", "DESC"] = "DESC",
) -> ImportStatistics:
    try:
        records = await EUFundingSource().collect_for_import(
            keyword=keyword,
            page=page,
            page_size=page_size,
            type_codes=type_codes,
            status_codes=status_codes,
            programme_period=programme_period,
            language=language,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )
        return await import_opportunities(
            session,
            records,
            source_code="eu_funding_tenders",
            actor_id=user.uid,
        )
    except ImportConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ExternalAPIError as error:
        raise _external_error(error) from error


@router.get("/sources", response_model=list[SourceSummary])
async def list_sources(
    _: Annotated[AuthenticatedUser, Depends(preview_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[SourceSummary]:
    sources = (
        await session.scalars(
            select(OpportunitySource).order_by(OpportunitySource.source_code)
        )
    ).all()
    return [
        SourceSummary(
            source_code=source.source_code,
            source_name=source.source_name,
            is_active=source.is_active,
            trust_level=source.trust_level,
            authentication_type=source.authentication_type,
            last_successful_sync=source.last_successful_sync_at,
            last_failed_sync=source.last_failed_sync_at,
            most_recent_error=source.most_recent_error,
            next_scheduled_sync=source.next_scheduled_sync,
        )
        for source in sources
    ]


@router.get("/sync-history", response_model=SyncHistoryPage)
async def list_sync_history(
    _: Annotated[AuthenticatedUser, Depends(preview_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
    source: str | None = None,
    sync_status: SyncStatus | None = Query(default=None, alias="status"),
    started_from: datetime | None = None,
    started_to: datetime | None = None,
    triggered_by: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    sort_by: Literal["started_at", "finished_at", "created_at"] = "started_at",
    sort_direction: Literal["asc", "desc"] = "desc",
) -> SyncHistoryPage:
    filters = []
    if source:
        filters.append(OpportunitySyncHistory.source_code == _source_code(source))
    if sync_status:
        filters.append(OpportunitySyncHistory.status == sync_status)
    if started_from:
        filters.append(OpportunitySyncHistory.started_at >= started_from)
    if started_to:
        filters.append(OpportunitySyncHistory.started_at <= started_to)
    if triggered_by:
        filters.append(OpportunitySyncHistory.triggered_by == triggered_by)
    total = await session.scalar(
        select(func.count(OpportunitySyncHistory.id)).where(*filters)
    )
    sort_column = getattr(OpportunitySyncHistory, sort_by)
    ordering = asc(sort_column) if sort_direction == "asc" else desc(sort_column)
    items = (
        await session.scalars(
            select(OpportunitySyncHistory)
            .where(*filters)
            .order_by(ordering)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return SyncHistoryPage(
        items=list(items), total=total or 0, page=page, page_size=page_size
    )


def _pending_item(
    opportunity: ExternalOpportunity, assessment: ConfidenceAssessment
) -> PendingOpportunityItem:
    item = PendingOpportunityItem.model_validate(opportunity)
    item.confidence_level = assessment.level
    item.confidence_reasons = assessment.reasons
    return item


@router.get("/pending-verification", response_model=PendingOpportunityPage)
async def list_pending_verification(
    _: Annotated[AuthenticatedUser, Depends(preview_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
    source: str | None = None,
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    duplicate_only: bool = False,
    sort: Literal["collected_at", "confidence"] = "collected_at",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PendingOpportunityPage:
    """`sort=confidence` surfaces the most trustworthy-looking pending
    records first (see app/services/verification_confidence.py) so an
    officer working through a growing queue can triage - this is a
    priority hint only. It never changes what requires approval: every
    record here, regardless of confidence, still needs an officer's
    explicit `approved` decision before it can be published.
    """
    filters = [
        ExternalOpportunity.verification_status == VerificationStatus.pending,
        ExternalOpportunity.publication_status == PublicationStatus.unpublished,
    ]
    if source:
        filters.append(
            ExternalOpportunity.source_id
            == select(OpportunitySource.id)
            .where(OpportunitySource.source_code == _source_code(source))
            .scalar_subquery()
        )
    if keyword:
        filters.append(ExternalOpportunity.title.ilike(f"%{keyword}%"))
    if duplicate_only:
        filters.append(ExternalOpportunity.duplicate_review_required.is_(True))
    total = await session.scalar(
        select(func.count(ExternalOpportunity.id)).where(*filters)
    )

    if sort == "confidence":
        # Confidence has no SQL column to order by - assess a bounded
        # window of the queue (an officer's realistic daily workload, not
        # an unbounded scan) and sort/paginate in Python.
        candidates = (
            await session.scalars(
                select(ExternalOpportunity)
                .options(joinedload(ExternalOpportunity.source))
                .where(*filters)
                .order_by(ExternalOpportunity.collected_at.desc())
                .limit(1000)
            )
        ).all()
        assessed = [
            (opportunity, assess_confidence(opportunity, opportunity.source))
            for opportunity in candidates
        ]
        assessed.sort(key=lambda pair: pair[1].score, reverse=True)
        start = (page - 1) * page_size
        items = [
            _pending_item(opportunity, assessment)
            for opportunity, assessment in assessed[start : start + page_size]
        ]
    else:
        rows = (
            await session.scalars(
                select(ExternalOpportunity)
                .options(joinedload(ExternalOpportunity.source))
                .where(*filters)
                .order_by(ExternalOpportunity.collected_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        items = [
            _pending_item(opportunity, assess_confidence(opportunity, opportunity.source))
            for opportunity in rows
        ]

    return PendingOpportunityPage(
        items=items, total=total or 0, page=page, page_size=page_size
    )


@router.get("/opportunities", response_model=AdminOpportunityPage)
async def list_all_opportunities(
    _: Annotated[AuthenticatedUser, Depends(admin_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 100,
) -> AdminOpportunityPage:
    """Admin-wide listing across every verification/publication status,

    for administration reporting - distinct from `/pending-verification`
    (pending queue only) and `/opportunities` on the public router
    (published+verified only).
    """
    total = await session.scalar(select(func.count(ExternalOpportunity.id)))
    items = (
        await session.scalars(
            select(ExternalOpportunity)
            .order_by(ExternalOpportunity.collected_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return AdminOpportunityPage(
        items=list(items), total=total or 0, page=page, page_size=page_size
    )


@router.get("/verification-summary", response_model=VerificationSummary)
async def verification_summary(
    user: Annotated[AuthenticatedUser, Depends(preview_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> VerificationSummary:
    """Real, aggregate counts for the Verification Officer dashboard.

    Every number here is computed from the actual external_opportunities /
    verification_review / verification_history / import_audit_log tables -
    there is no per-officer assignment or richer workflow-status concept in
    this backend (unlike the demo verification repository), so this
    deliberately reports what the live schema actually tracks rather than
    fabricating the demo's two-person-workflow fields. See
    docs/OPPORTUNITY_VERIFICATION_SYSTEM.md SS4.
    """
    now = utc_now()
    today_start = datetime(now.year, now.month, now.day, tzinfo=now.tzinfo)

    pending = await session.scalar(
        select(func.count(ExternalOpportunity.id)).where(
            ExternalOpportunity.verification_status == VerificationStatus.pending
        )
    )

    verified_today = await session.scalar(
        select(func.count(VerificationReview.id)).where(
            VerificationReview.decision == VerificationStatus.verified.value,
            VerificationReview.verified_at >= today_start,
        )
    )

    # Mirrors app.tasks.opportunity_sync._schedule_reverification's own
    # 90-day cutoff: a review is "due soon" once it's within 7 days of that
    # cutoff and the opportunity is still verified (hasn't already been
    # flipped to reverification_required by an earlier run of that task).
    due_soon_start = now - timedelta(days=90)
    due_soon_end = now - timedelta(days=83)
    reverification_due_soon = await session.scalar(
        select(func.count(VerificationReview.id))
        .join(
            ExternalOpportunity,
            ExternalOpportunity.id == VerificationReview.opportunity_id,
        )
        .where(
            ExternalOpportunity.verification_status == VerificationStatus.verified,
            VerificationReview.verified_at.is_not(None),
            VerificationReview.verified_at <= due_soon_end,
            VerificationReview.verified_at > due_soon_start,
        )
    )

    status_rows = (
        await session.execute(
            select(
                ExternalOpportunity.verification_status, func.count(ExternalOpportunity.id)
            ).group_by(ExternalOpportunity.verification_status)
        )
    ).all()
    by_status = {status_value.value: count for status_value, count in status_rows}

    total_opportunities = await session.scalar(select(func.count(ExternalOpportunity.id)))
    official_count = await session.scalar(
        select(func.count(ExternalOpportunity.id))
        .join(OpportunitySource, OpportunitySource.id == ExternalOpportunity.source_id)
        .where(OpportunitySource.trust_level == "official")
    )
    official_source_ratio = (
        (official_count or 0) / total_opportunities if total_opportunities else 1.0
    )

    # Decision-producing history rows carry a "verification_checks" key
    # (see decide_verification above); notes and field edits don't, so this
    # naturally excludes them without a dialect-specific JSON query.
    recent_history = (
        await session.scalars(
            select(VerificationHistory).where(
                VerificationHistory.changed_at >= now - timedelta(days=7)
            )
        )
    ).all()
    decision_counts: Counter[date] = Counter()
    for entry in recent_history:
        if entry.changed_fields and "verification_checks" in entry.changed_fields:
            decision_counts[entry.changed_at.date()] += 1
    decisions_last_7_days = [
        VerificationActivityDay(date=day, decisions=decision_counts.get(day, 0))
        for day in (now.date() - timedelta(days=offset) for offset in range(6, -1, -1))
    ]

    approved_by_you = await session.scalar(
        select(func.count(ImportAuditLog.id)).where(
            ImportAuditLog.actor_id == user.uid,
            ImportAuditLog.action == "verification_approved",
        )
    )

    return VerificationSummary(
        pending=pending or 0,
        verified_today=verified_today or 0,
        reverification_due_soon=reverification_due_soon or 0,
        by_status=by_status,
        official_source_ratio=official_source_ratio,
        decisions_last_7_days=decisions_last_7_days,
        approved_by_you=approved_by_you or 0,
    )


@router.get("/discovery-summary", response_model=DiscoverySummary)
async def discovery_summary(
    _: Annotated[AuthenticatedUser, Depends(preview_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DiscoverySummary:
    """Source- and country-level aggregates for the admin discovery dashboard.

    See DiscoverySummary's docstring for how this differs from
    verification_summary above.
    """
    sources_total = await session.scalar(select(func.count(OpportunitySource.id)))
    sources_active = await session.scalar(
        select(func.count(OpportunitySource.id)).where(OpportunitySource.is_active.is_(True))
    )
    sources_with_recent_errors = await session.scalar(
        select(func.count(OpportunitySource.id)).where(
            OpportunitySource.most_recent_error.is_not(None)
        )
    )

    opportunities_total = await session.scalar(select(func.count(ExternalOpportunity.id)))
    published_total = await session.scalar(
        select(func.count(ExternalOpportunity.id)).where(
            ExternalOpportunity.publication_status == PublicationStatus.published
        )
    )
    duplicate_review_required = await session.scalar(
        select(func.count(ExternalOpportunity.id)).where(
            ExternalOpportunity.duplicate_review_required.is_(True)
        )
    )

    country_rows = (
        await session.execute(
            select(ExternalOpportunity.country, func.count(ExternalOpportunity.id))
            .where(ExternalOpportunity.country.is_not(None))
            .group_by(ExternalOpportunity.country)
        )
    ).all()
    opportunities_by_country = {country: count for country, count in country_rows}

    never_link_checked = await session.scalar(
        select(func.count(ExternalOpportunity.id)).where(
            ExternalOpportunity.verification_status == VerificationStatus.verified,
            ExternalOpportunity.publication_status == PublicationStatus.published,
            ExternalOpportunity.link_checked_at.is_(None),
        )
    )
    # "Currently believed broken" - still reverification_required, and the
    # reason it was last demoted names a failed link health check (not,
    # say, the unrelated 90-day scheduled-reverification cutoff). Not a
    # perfectly point-in-time signal (a later, unrelated demotion after a
    # link-health one would still count here), but a real, honest
    # aggregate rather than a fabricated one - matches this route's
    # existing pragmatic style (see verified_today's decision-history scan
    # above).
    broken_links = await session.scalar(
        select(func.count(func.distinct(ExternalOpportunity.id)))
        .join(VerificationHistory, VerificationHistory.opportunity_id == ExternalOpportunity.id)
        .where(
            ExternalOpportunity.verification_status == VerificationStatus.reverification_required,
            VerificationHistory.new_status == VerificationStatus.reverification_required.value,
            VerificationHistory.reason.like("%link health check%"),
        )
    )

    return DiscoverySummary(
        sources_total=sources_total or 0,
        sources_active=sources_active or 0,
        sources_with_recent_errors=sources_with_recent_errors or 0,
        opportunities_total=opportunities_total or 0,
        published_total=published_total or 0,
        duplicate_review_required=duplicate_review_required or 0,
        opportunities_by_country=opportunities_by_country,
        never_link_checked=never_link_checked or 0,
        broken_links=broken_links or 0,
    )


@router.get(
    "/opportunities/{opportunity_id}/verification-history",
    response_model=VerificationHistoryPage,
)
async def get_verification_history(
    opportunity_id: UUID,
    _: Annotated[AuthenticatedUser, Depends(preview_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> VerificationHistoryPage:
    opportunity = await session.get(ExternalOpportunity, opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    rows = (
        await session.scalars(
            select(VerificationHistory)
            .where(VerificationHistory.opportunity_id == opportunity_id)
            .order_by(VerificationHistory.changed_at.asc())
        )
    ).all()
    return VerificationHistoryPage(
        opportunity_id=opportunity_id,
        items=[VerificationHistoryItem.model_validate(row) for row in rows],
    )


@router.get(
    "/opportunities/{opportunity_id}/evidence",
    response_model=OpportunityEvidence,
)
async def get_verification_evidence(
    opportunity_id: UUID,
    _: Annotated[AuthenticatedUser, Depends(preview_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OpportunityEvidence:
    """Same evidence view as the applicant-facing endpoint, but available to
    verification staff for any status - not just verified+published records.
    A verification officer must be able to see where a fact came from
    *before* deciding whether to publish it.
    """
    opportunity = await session.scalar(
        select(ExternalOpportunity)
        .options(joinedload(ExternalOpportunity.source))
        .where(ExternalOpportunity.id == opportunity_id)
    )
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    return await build_opportunity_evidence(session, opportunity)


@router.get("/health", response_model=list[SourceHealth])
async def source_health(
    _: Annotated[AuthenticatedUser, Depends(preview_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[SourceHealth]:
    sources = (
        await session.scalars(
            select(OpportunitySource).order_by(OpportunitySource.source_code)
        )
    ).all()
    return [
        SourceHealth(
            source_code=source.source_code,
            active_status=source.is_active,
            last_successful_sync=source.last_successful_sync_at,
            last_failed_sync=source.last_failed_sync_at,
            most_recent_error=source.most_recent_error,
            next_scheduled_sync=source.next_scheduled_sync,
        )
        for source in sources
    ]


@router.patch("/sources/{source}", response_model=SourceSummary)
async def update_source_state(
    source: str,
    payload: SourceStateRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(admin_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SourceSummary:
    source_code = _source_code(source)
    async with session.begin():
        source_model = await session.scalar(
            select(OpportunitySource).where(
                OpportunitySource.source_code == source_code
            )
        )
        if source_model is None:
            raise HTTPException(status_code=404, detail="External source not found.")
        previous = source_model.is_active
        source_model.is_active = payload.is_active
        append_audit(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action=("source_activated" if payload.is_active else "source_deactivated"),
            entity_type="opportunity_source",
            entity_id=source_model.id,
            previous_value={"is_active": previous},
            new_value={"is_active": payload.is_active},
            correlation_id=request.state.correlation_id,
        )
    return SourceSummary(
        source_code=source_model.source_code,
        source_name=source_model.source_name,
        is_active=source_model.is_active,
        trust_level=source_model.trust_level,
        authentication_type=source_model.authentication_type,
        last_successful_sync=source_model.last_successful_sync_at,
        last_failed_sync=source_model.last_failed_sync_at,
        most_recent_error=source_model.most_recent_error,
        next_scheduled_sync=source_model.next_scheduled_sync,
    )


@router.post(
    "/opportunities/{opportunity_id}/verification",
    response_model=OpportunityState,
)
async def decide_verification(
    opportunity_id: UUID,
    payload: VerificationDecisionRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(import_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OpportunityState:
    async with session.begin():
        opportunity = await session.get(ExternalOpportunity, opportunity_id)
        if opportunity is None:
            raise HTTPException(status_code=404, detail="Opportunity not found.")
        review = await session.scalar(
            select(VerificationReview).where(
                VerificationReview.opportunity_id == opportunity_id
            )
        )
        if review is None:
            raise HTTPException(
                status_code=409,
                detail="Opportunity has no pending verification review.",
            )
        checks = {
            "source_checked": payload.source_checked,
            "application_link_checked": payload.application_link_checked,
            "deadline_checked": payload.deadline_checked,
            "duplicate_checked": payload.duplicate_checked,
        }
        if payload.decision == "approved" and not all(checks.values()):
            raise HTTPException(
                status_code=409,
                detail="All verification checks must pass before approval.",
            )
        previous = opportunity.verification_status.value
        new_status = _DECISION_STATUS[payload.decision]
        opportunity.verification_status = new_status
        opportunity.publication_status = PublicationStatus.unpublished
        review.verification_officer_id = user.uid
        review.source_checked = payload.source_checked
        review.application_link_checked = payload.application_link_checked
        review.deadline_checked = payload.deadline_checked
        review.duplicate_checked = payload.duplicate_checked
        review.decision = new_status.value
        review.notes = payload.notes
        review.verified_at = utc_now()
        session.add(
            VerificationHistory(
                opportunity_id=opportunity.id,
                previous_status=previous,
                new_status=new_status.value,
                reason=payload.notes,
                changed_fields={"verification_checks": checks},
            )
        )
        append_audit(
            session,
            opportunity_id=opportunity.id,
            actor_id=user.uid,
            actor_role=user.role,
            action=f"verification_{payload.decision}",
            entity_type="external_opportunity",
            entity_id=opportunity.id,
            previous_value={"verification_status": previous},
            new_value={"verification_status": new_status.value, **checks},
            correlation_id=request.state.correlation_id,
        )
    return OpportunityState(
        id=opportunity.id,
        verification_status=opportunity.verification_status.value,
        publication_status=opportunity.publication_status.value,
    )


@router.get(
    "/opportunities/{opportunity_id}/review",
    response_model=VerificationReviewState,
)
async def get_verification_review(
    opportunity_id: UUID,
    _: Annotated[AuthenticatedUser, Depends(preview_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> VerificationReviewState:
    review = await session.scalar(
        select(VerificationReview).where(
            VerificationReview.opportunity_id == opportunity_id
        )
    )
    if review is None:
        raise HTTPException(
            status_code=404, detail="No verification review exists for this opportunity."
        )
    return VerificationReviewState.model_validate(review)


@router.post(
    "/opportunities/{opportunity_id}/notes",
    response_model=OpportunityState,
)
async def add_verification_note(
    opportunity_id: UUID,
    payload: OpportunityNoteRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(import_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OpportunityState:
    """Attach a timestamped officer note as evidence without changing status."""
    async with session.begin():
        opportunity = await session.get(ExternalOpportunity, opportunity_id)
        if opportunity is None:
            raise HTTPException(status_code=404, detail="Opportunity not found.")
        current_status = opportunity.verification_status.value
        session.add(
            VerificationHistory(
                opportunity_id=opportunity.id,
                previous_status=current_status,
                new_status=current_status,
                reason=payload.note,
                changed_fields={"note_added": True},
            )
        )
        append_audit(
            session,
            opportunity_id=opportunity.id,
            actor_id=user.uid,
            actor_role=user.role,
            action="verification_note_added",
            entity_type="external_opportunity",
            entity_id=opportunity.id,
            new_value={"note": payload.note},
            correlation_id=request.state.correlation_id,
        )
    return OpportunityState(
        id=opportunity.id,
        verification_status=opportunity.verification_status.value,
        publication_status=opportunity.publication_status.value,
    )


@router.patch(
    "/opportunities/{opportunity_id}",
    response_model=OpportunityEditResponse,
)
async def edit_opportunity(
    opportunity_id: UUID,
    payload: OpportunityEditRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(import_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OpportunityEditResponse:
    """Let a verification officer correct specific fields, with a mandatory,
    fully audited reason. Every change is diffed and recorded in both the
    append-only verification history and the import audit log - nothing is
    overwritten silently.
    """
    updates = payload.model_dump(exclude={"reason"}, exclude_unset=True)
    async with session.begin():
        opportunity = await session.get(ExternalOpportunity, opportunity_id)
        if opportunity is None:
            raise HTTPException(status_code=404, detail="Opportunity not found.")
        changed: dict[str, dict[str, Any]] = {}
        for field in _EDITABLE_FIELDS:
            if field not in updates or updates[field] is None:
                continue
            new_value = updates[field]
            if field == "description":
                # Officer-supplied text goes through the same HTML
                # sanitization as source-collected descriptions
                # (app/services/eu_funding.py etc.) before it can ever be
                # served to applicants - an edit reason is not an exemption
                # from that rule.
                new_value = sanitize_html(new_value)
                if new_value is None:
                    continue
            if field in ("official_source_url", "official_application_url"):
                new_value = str(new_value)
            current_value = getattr(opportunity, field)
            current_comparable = (
                str(current_value)
                if field in ("official_source_url", "official_application_url")
                else current_value
            )
            if current_comparable == new_value:
                continue
            changed[field] = {
                "previous": _jsonable(current_value),
                "new": _jsonable(new_value),
            }
            setattr(opportunity, field, new_value)
        if not changed:
            raise HTTPException(
                status_code=400, detail="No editable fields were changed."
            )
        current_status = opportunity.verification_status.value
        session.add(
            VerificationHistory(
                opportunity_id=opportunity.id,
                previous_status=current_status,
                new_status=current_status,
                reason=payload.reason,
                changed_fields=changed,
            )
        )
        append_audit(
            session,
            opportunity_id=opportunity.id,
            actor_id=user.uid,
            actor_role=user.role,
            action="opportunity_edited",
            entity_type="external_opportunity",
            entity_id=opportunity.id,
            previous_value={k: v["previous"] for k, v in changed.items()},
            new_value={k: v["new"] for k, v in changed.items()},
            correlation_id=request.state.correlation_id,
        )
    return OpportunityEditResponse(id=opportunity.id, changed_fields=list(changed.keys()))


def _jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


@router.post(
    "/opportunities/{opportunity_id}/publication",
    response_model=OpportunityState,
)
async def change_publication(
    opportunity_id: UUID,
    payload: PublicationRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(admin_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OpportunityState:
    async with session.begin():
        opportunity = await session.get(ExternalOpportunity, opportunity_id)
        if opportunity is None:
            raise HTTPException(status_code=404, detail="Opportunity not found.")
        if payload.published and opportunity.verification_status != VerificationStatus.verified:
            raise HTTPException(
                status_code=409,
                detail="Only verified opportunities can be published.",
            )
        previous = opportunity.publication_status.value
        opportunity.publication_status = (
            PublicationStatus.published
            if payload.published
            else PublicationStatus.unpublished
        )
        append_audit(
            session,
            opportunity_id=opportunity.id,
            actor_id=user.uid,
            actor_role=user.role,
            action="opportunity_published" if payload.published else "opportunity_unpublished",
            entity_type="external_opportunity",
            entity_id=opportunity.id,
            previous_value={"publication_status": previous},
            new_value={"publication_status": opportunity.publication_status.value},
            correlation_id=request.state.correlation_id,
        )
    return OpportunityState(
        id=opportunity.id,
        verification_status=opportunity.verification_status.value,
        publication_status=opportunity.publication_status.value,
    )


@router.post("/{source}/sync", response_model=SyncQueued, status_code=202)
async def queue_sync(
    source: str,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(import_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SyncQueued:
    source_code = _source_code(source)
    task_id = str(uuid4())
    correlation_id = str(uuid4())
    async with session.begin():
        sources = await seed_opportunity_sources(session)
        source_model = sources[source_code]
        if not source_model.is_active:
            raise HTTPException(status_code=409, detail="The external source is inactive.")
        session.add(
            OpportunitySyncHistory(
                task_id=task_id,
                source_id=source_model.id,
                source_code=source_code,
                started_at=utc_now(),
                status=SyncStatus.queued,
                correlation_id=correlation_id,
                triggered_by=user.uid,
            )
        )
        append_audit(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action="manual_synchronization_queued",
            entity_type="opportunity_source",
            entity_id=source_model.id,
            new_value={"task_id": task_id, "source_code": source_code},
            correlation_id=request.state.correlation_id,
        )
    try:
        queue_source_sync(
            source_code,
            task_id=task_id,
            correlation_id=correlation_id,
            triggered_by=user.uid,
        )
    except Exception as error:
        async with session.begin():
            history = await session.scalar(
                select(OpportunitySyncHistory).where(
                    OpportunitySyncHistory.task_id == task_id
                )
            )
            history.status = SyncStatus.failed
            history.finished_at = utc_now()
            history.error_summary = "The synchronization task could not be queued."
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The synchronization queue is unavailable.",
        ) from error
    logger.info(
        "sync_queued source_code=%s task_id=%s correlation_id=%s "
        "record_count=0 final_status=queued",
        source_code,
        task_id,
        correlation_id,
    )
    return SyncQueued(
        task_id=task_id,
        source=source,
        correlation_id=correlation_id,
    )


@router.get("/{source}/preview", response_model=list[NormalizedExternalOpportunity])
async def preview_source(
    source: str,
    _: Annotated[AuthenticatedUser, Depends(preview_access)],
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> list[NormalizedExternalOpportunity]:
    try:
        return await _collector_for(source).collect(
            keyword=keyword, page=page, page_size=page_size
        )
    except ExternalAPIError as error:
        raise _external_error(error) from error


@router.post("/{source}/import", response_model=ImportStatistics)
async def import_source(
    source: str,
    user: Annotated[AuthenticatedUser, Depends(import_access)],
    session: Annotated[AsyncSession, Depends(get_db)],
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ImportStatistics:
    source_code = _source_code(source)
    try:
        records = await _collector_for(source).collect_for_import(
            keyword=keyword, page=page, page_size=page_size
        )
        return await import_opportunities(
            session, records, source_code=source_code, actor_id=user.uid
        )
    except ImportConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ExternalAPIError as error:
        raise _external_error(error) from error


def _source_code(source: str) -> str:
    try:
        return {
            "grants-gov": "grants_gov",
            "simpler-grants": "simpler_grants",
            "eu-funding": "eu_funding_tenders",
            "usajobs": "usajobs",
            "reliefweb-jobs": "reliefweb_jobs",
            "reliefweb-training": "reliefweb_training",
        }[source]
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Unknown external source.") from error


def _collector_for(source: str):
    return {
        "grants-gov": GrantsGovSource,
        "simpler-grants": SimplerGrantsSource,
        "eu-funding": EUFundingSource,
        "usajobs": UsaJobsSource,
        "reliefweb-jobs": ReliefWebJobsSource,
        "reliefweb-training": ReliefWebTrainingSource,
    }.get(source, _unknown_source)()


def _unknown_source():
    raise HTTPException(status_code=404, detail="Unknown external source.")


def _external_error(error: ExternalAPIError) -> HTTPException:
    if error.status_code == 429:
        response_status = status.HTTP_429_TOO_MANY_REQUESTS
    elif error.status_code in {500, 502, 503, 504} or error.status_code is None:
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        response_status = status.HTTP_502_BAD_GATEWAY
    return HTTPException(
        status_code=response_status,
        detail=str(error),
    )

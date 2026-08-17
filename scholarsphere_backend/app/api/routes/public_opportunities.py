from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models import ExternalOpportunity
from app.models.external_opportunity import PublicationStatus, VerificationStatus
from app.schemas.opportunity_public import (
    OpportunityEvidence,
    PublicOpportunity,
    PublicOpportunityPage,
)
from app.services.deadline_engine import assess_deadline
from app.services.evidence import build_opportunity_evidence
from app.services.parsing import utc_now

router = APIRouter(prefix="/opportunities", tags=["public opportunities"])

any_authenticated = Depends(get_current_user)


@router.get("", response_model=PublicOpportunityPage)
async def list_opportunities(
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    country: Annotated[str | None, Query(max_length=255)] = None,
    opportunity_type: Annotated[str | None, Query(max_length=128)] = None,
    funding_type: Annotated[str | None, Query(max_length=128)] = None,
    closing_within_days: Annotated[int | None, Query(ge=0, le=3650)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PublicOpportunityPage:
    """List published, human-verified opportunities.

    Only records with ``verification_status=verified`` and
    ``publication_status=published`` are ever returned here - see
    Section 33 (production safety) of the platform specification.
    """
    today = utc_now().date()
    filters = [
        ExternalOpportunity.verification_status == VerificationStatus.verified,
        ExternalOpportunity.publication_status == PublicationStatus.published,
    ]
    if keyword:
        filters.append(ExternalOpportunity.title.ilike(f"%{keyword}%"))
    if country:
        filters.append(ExternalOpportunity.country == country)
    if opportunity_type:
        filters.append(ExternalOpportunity.opportunity_type == opportunity_type)
    if funding_type:
        filters.append(ExternalOpportunity.funding_type == funding_type)
    if closing_within_days is not None:
        filters.append(ExternalOpportunity.deadline.is_not(None))
        filters.append(
            ExternalOpportunity.deadline <= today.fromordinal(today.toordinal() + closing_within_days)
        )

    total = await session.scalar(select(func.count(ExternalOpportunity.id)).where(*filters))
    rows = (
        await session.scalars(
            select(ExternalOpportunity)
            .options(
                joinedload(ExternalOpportunity.source),
                joinedload(ExternalOpportunity.verification_review),
            )
            .where(*filters)
            .order_by(ExternalOpportunity.deadline.asc().nulls_last())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return PublicOpportunityPage(
        items=[_to_public(opportunity, today) for opportunity in rows],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{opportunity_id}", response_model=PublicOpportunity)
async def get_opportunity(
    opportunity_id: UUID,
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PublicOpportunity:
    opportunity = await session.scalar(
        select(ExternalOpportunity)
        .options(
            joinedload(ExternalOpportunity.source),
            joinedload(ExternalOpportunity.verification_review),
        )
        .where(ExternalOpportunity.id == opportunity_id)
    )
    if opportunity is None or not _is_public(opportunity):
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    return _to_public(opportunity, utc_now().date())


@router.get("/{opportunity_id}/evidence", response_model=OpportunityEvidence)
async def get_opportunity_evidence(
    opportunity_id: UUID,
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OpportunityEvidence:
    """Answer "where did this field come from?" with the exact raw source record."""
    opportunity = await session.scalar(
        select(ExternalOpportunity)
        .options(joinedload(ExternalOpportunity.source))
        .where(ExternalOpportunity.id == opportunity_id)
    )
    if opportunity is None or not _is_public(opportunity):
        raise HTTPException(status_code=404, detail="Opportunity not found.")
    return await build_opportunity_evidence(session, opportunity)


def _is_public(opportunity: ExternalOpportunity) -> bool:
    return (
        opportunity.verification_status == VerificationStatus.verified
        and opportunity.publication_status == PublicationStatus.published
    )


def _to_public(opportunity: ExternalOpportunity, today: date) -> PublicOpportunity:
    assessment = assess_deadline(opportunity.deadline, today=today)
    return PublicOpportunity(
        id=opportunity.id,
        title=opportunity.title,
        opportunity_type=opportunity.opportunity_type,
        provider_name=opportunity.provider_name,
        country=opportunity.country,
        description=opportunity.description,
        opening_date=opportunity.opening_date,
        deadline=opportunity.deadline,
        opportunity_status=opportunity.opportunity_status,
        funding_type=opportunity.funding_type,
        award_floor=opportunity.award_floor,
        award_ceiling=opportunity.award_ceiling,
        currency=opportunity.currency,
        official_source_url=opportunity.official_source_url,
        official_application_url=opportunity.official_application_url,
        verification_status=opportunity.verification_status.value,
        source_code=opportunity.source.source_code,
        source_name=opportunity.source.source_name,
        source_trust_level=opportunity.source.trust_level,
        collected_at=opportunity.collected_at,
        last_external_update_at=opportunity.last_external_update_at,
        verified_at=(
            opportunity.verification_review.verified_at
            if opportunity.verification_review is not None
            else None
        ),
        days_remaining=assessment.days_remaining,
        deadline_priority=assessment.priority,
    )

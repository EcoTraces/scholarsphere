from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.external_opportunity import PublicationStatus
from app.models.provider import Provider, ProviderAdministrator, ProviderPermission, ProviderStatus
from app.models.provider_opportunity import (
    ProviderOpportunity,
    ProviderOpportunityVerificationHistory,
    ProviderOpportunityVerificationReview,
    ProviderOpportunityVerificationStatus,
)
from app.schemas.provider_opportunity import (
    ProviderOpportunityCreate,
    ProviderOpportunityPage,
    ProviderOpportunityPublicationRequest,
    ProviderOpportunityRead,
    ProviderOpportunityVerificationRequest,
    delivery_from_wire,
    funding_from_wire,
    type_from_wire,
)

router = APIRouter(prefix="/provider-opportunities", tags=["provider opportunities"])

any_authenticated = Depends(get_current_user)
review_access = Depends(require_roles("verificationOfficer", "administrator", "superAdministrator"))
admin_access = Depends(require_roles("administrator", "superAdministrator"))


async def _relationship(
    session: AsyncSession, provider_id: UUID, uid: str
) -> Provider | None:
    provider = await session.get(Provider, provider_id)
    if provider is None:
        return None
    if provider.user_id == uid:
        return provider
    admin = await session.scalar(
        select(ProviderAdministrator).where(
            ProviderAdministrator.provider_id == provider_id,
            ProviderAdministrator.user_id == uid,
        )
    )
    return provider if admin is not None else None


async def _submitter_permission_check(
    session: AsyncSession, provider: Provider, uid: str
) -> None:
    """Enforce the *specific* administrator's own granted permissions, not

    just the organization's aggregate ones. The owner (provider.user_id)
    always has full control of their own organization; a delegate
    ProviderAdministrator only gets publish_opportunities capability if
    that permission was actually granted to them individually via
    POST /providers/{id}/administrators - previously this was stored but
    never checked, so any linked administrator of a verified provider
    could submit opportunities regardless of the permission subset they
    were assigned.
    """
    if provider.user_id == uid:
        return
    admin = await session.scalar(
        select(ProviderAdministrator).where(
            ProviderAdministrator.provider_id == provider.id,
            ProviderAdministrator.user_id == uid,
        )
    )
    if admin is None or ProviderPermission.publish_opportunities.value not in admin.permissions:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to submit opportunities for this organization.",
        )


@router.post("", response_model=ProviderOpportunityRead)
async def submit_opportunity(
    payload: ProviderOpportunityCreate,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderOpportunityRead:
    async with session.begin():
        provider = await session.get(Provider, payload.provider_id)
        if provider is None:
            raise HTTPException(status_code=404, detail="Provider not found.")
        related = await _relationship(session, payload.provider_id, user.uid)
        if related is None:
            raise HTTPException(
                status_code=403,
                detail="You are not an administrator of this provider.",
            )
        if provider.status != ProviderStatus.verified or (
            ProviderPermission.publish_opportunities.value not in provider.permissions
        ):
            raise HTTPException(
                status_code=409,
                detail="Only verified providers with publish permission can submit opportunities.",
            )
        await _submitter_permission_check(session, provider, user.uid)
        opportunity = ProviderOpportunity(
            provider_id=provider.id,
            submitted_by=user.uid,
            title=payload.title,
            host_institution=payload.host_institution,
            host_country=payload.host_country,
            opportunity_type=type_from_wire(payload.opportunity_type),
            funding_type=funding_from_wire(payload.funding_type),
            delivery_format=delivery_from_wire(payload.delivery_format),
            deadline=payload.deadline,
            application_open_date=payload.application_open_date,
            official_source_url=payload.official_source_url,
            application_url=payload.application_url,
            eligible_nationalities=payload.eligible_nationalities,
            study_levels=payload.study_levels,
            fields_of_study=payload.fields_of_study,
            summary=payload.summary,
            benefits=payload.benefits,
            eligibility_requirements=payload.eligibility_requirements,
            required_documents=payload.required_documents,
            application_procedure=payload.application_procedure,
            language_requirements=payload.language_requirements,
            minimum_age=payload.minimum_age,
            maximum_age=payload.maximum_age,
            work_experience_years_required=payload.work_experience_years_required,
            contact_information=payload.contact_information,
            available_positions=payload.available_positions,
            application_fee=payload.application_fee,
        )
        session.add(opportunity)
        await session.flush()
        session.add(ProviderOpportunityVerificationReview(provider_opportunity_id=opportunity.id))
        await session.flush()
        await session.refresh(opportunity)
        return _to_read(opportunity, provider.organization_name)


@router.get("/mine/{provider_id}", response_model=list[ProviderOpportunityRead])
async def list_for_provider(
    provider_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProviderOpportunityRead]:
    related = await _relationship(session, provider_id, user.uid)
    if related is None:
        raise HTTPException(status_code=404, detail="Provider not found.")
    rows = (
        await session.scalars(
            select(ProviderOpportunity)
            .where(ProviderOpportunity.provider_id == provider_id)
            .order_by(ProviderOpportunity.updated_at.desc())
        )
    ).all()
    return [_to_read(row, related.organization_name) for row in rows]


@router.get("/admin", response_model=ProviderOpportunityPage)
async def list_all_provider_opportunities(
    _: Annotated[AuthenticatedUser, review_access],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ProviderOpportunityPage:
    total = await session.scalar(select(func.count(ProviderOpportunity.id)))
    rows = (
        await session.execute(
            select(ProviderOpportunity, Provider.organization_name)
            .join(Provider, Provider.id == ProviderOpportunity.provider_id)
            .order_by(ProviderOpportunity.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ProviderOpportunityPage(
        items=[_to_read(opportunity, provider_name) for opportunity, provider_name in rows],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("/{provider_opportunity_id}/verification", response_model=ProviderOpportunityRead)
async def decide_verification(
    provider_opportunity_id: UUID,
    payload: ProviderOpportunityVerificationRequest,
    user: Annotated[AuthenticatedUser, review_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderOpportunityRead:
    async with session.begin():
        opportunity = await session.get(ProviderOpportunity, provider_opportunity_id)
        if opportunity is None:
            raise HTTPException(status_code=404, detail="Opportunity not found.")
        review = await session.scalar(
            select(ProviderOpportunityVerificationReview).where(
                ProviderOpportunityVerificationReview.provider_opportunity_id
                == provider_opportunity_id
            )
        )
        if review is None:
            raise HTTPException(
                status_code=409, detail="Opportunity has no pending verification review."
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
        new_status = (
            ProviderOpportunityVerificationStatus.verified
            if payload.decision == "approved"
            else ProviderOpportunityVerificationStatus.rejected
        )
        now = datetime.now(timezone.utc)
        opportunity.verification_status = new_status
        opportunity.publication_status = PublicationStatus.unpublished
        opportunity.last_verified_at = now if new_status == ProviderOpportunityVerificationStatus.verified else None
        review.verification_officer_id = user.uid
        review.source_checked = payload.source_checked
        review.application_link_checked = payload.application_link_checked
        review.deadline_checked = payload.deadline_checked
        review.duplicate_checked = payload.duplicate_checked
        review.decision = new_status.value
        review.notes = payload.notes
        review.verified_at = now
        session.add(
            ProviderOpportunityVerificationHistory(
                provider_opportunity_id=opportunity.id,
                previous_status=previous,
                new_status=new_status.value,
                reason=payload.notes or "",
                changed_fields={"verification_checks": checks},
            )
        )
        await session.flush()
        await session.refresh(opportunity)
        provider = await session.get(Provider, opportunity.provider_id)
        return _to_read(opportunity, provider.organization_name)


@router.post("/{provider_opportunity_id}/publication", response_model=ProviderOpportunityRead)
async def change_publication(
    provider_opportunity_id: UUID,
    payload: ProviderOpportunityPublicationRequest,
    _: Annotated[AuthenticatedUser, admin_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderOpportunityRead:
    async with session.begin():
        opportunity = await session.get(ProviderOpportunity, provider_opportunity_id)
        if opportunity is None:
            raise HTTPException(status_code=404, detail="Opportunity not found.")
        if (
            payload.published
            and opportunity.verification_status != ProviderOpportunityVerificationStatus.verified
        ):
            raise HTTPException(
                status_code=409, detail="Only verified opportunities can be published."
            )
        opportunity.publication_status = (
            PublicationStatus.published if payload.published else PublicationStatus.unpublished
        )
        await session.flush()
        await session.refresh(opportunity)
        provider = await session.get(Provider, opportunity.provider_id)
        return _to_read(opportunity, provider.organization_name)


def _to_read(opportunity: ProviderOpportunity, provider_name: str) -> ProviderOpportunityRead:
    data = {
        column.name: getattr(opportunity, column.name)
        for column in ProviderOpportunity.__table__.columns
    }
    data["provider_name"] = provider_name
    return ProviderOpportunityRead.model_validate(data)

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.errors import correlation_id
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.provider import (
    Provider,
    ProviderActivity,
    ProviderAdministrator,
    ProviderAppeal,
    ProviderPermission,
    ProviderStatus,
)
from app.schemas.provider import (
    CanPublishResponse,
    ProviderAdministratorCreate,
    ProviderAdministratorRead,
    ProviderActivityRead,
    ProviderAppealRead,
    ProviderAppealRequest,
    ProviderCreate,
    ProviderRead,
    ProviderReviewRequest,
    ProviderSuspendRequest,
    document_owner_uid,
    permission_from_wire,
    status_from_wire,
)
from app.services.audit import append_audit
from app.services.provider_risk import compute_risk_score

router = APIRouter(prefix="/providers", tags=["providers"])

any_authenticated = Depends(get_current_user)
review_access = Depends(require_roles("verificationOfficer", "administrator", "superAdministrator"))

_REVIEW_QUEUE_STATUSES = {
    ProviderStatus.pending_review,
    ProviderStatus.additional_information_required,
    ProviderStatus.verification_expired,
}


@router.post("", response_model=ProviderRead)
async def register_provider(
    payload: ProviderCreate,
    request: Request,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderRead:
    for path in payload.supporting_documents:
        if document_owner_uid(path) != user.uid:
            raise HTTPException(
                status_code=400,
                detail="Supporting documents must be under your own uploaded folder.",
            )
    async with session.begin():
        domain = payload.official_email_domain.lower().strip()
        existing = await session.scalar(
            select(Provider.id).where(func.lower(Provider.official_email_domain) == domain)
        )
        if existing is not None:
            raise HTTPException(
                status_code=409, detail="This organization domain is already registered."
            )
        risk_score = compute_risk_score(
            official_email_domain=payload.official_email_domain,
            official_website=payload.official_website,
            registration_number=payload.registration_number,
            supporting_documents=payload.supporting_documents,
        )
        provider = Provider(
            user_id=user.uid,
            organization_name=payload.organization_name,
            organization_type=payload.organization_type,
            registration_number=payload.registration_number,
            country=payload.country,
            official_website=payload.official_website,
            official_email_domain=payload.official_email_domain,
            physical_address=payload.physical_address,
            contact_person=payload.contact_person,
            contact_phone=payload.contact_phone,
            supporting_documents=payload.supporting_documents,
            social_media_links=payload.social_media_links,
            status=ProviderStatus.pending_review,
            risk_score=risk_score,
            permissions=[ProviderPermission.manage_organization.value],
        )
        session.add(provider)
        await session.flush()
        append_audit(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action="provider_registered",
            entity_type="provider",
            entity_id=provider.id,
            new_value={"organization_name": provider.organization_name, "risk_score": risk_score},
            correlation_id=correlation_id(request),
        )
        await session.refresh(provider)
        return await _to_read(session, provider)


@router.get("/me", response_model=ProviderRead)
async def get_my_provider(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderRead:
    provider = await session.scalar(select(Provider).where(Provider.user_id == user.uid))
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found.")
    return await _to_read(session, provider)


@router.get("/me/can-publish", response_model=CanPublishResponse)
async def can_publish(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CanPublishResponse:
    provider = await session.scalar(select(Provider).where(Provider.user_id == user.uid))
    if provider is None:
        return CanPublishResponse(can_publish=False)
    allowed = provider.has_verified_badge and (
        ProviderPermission.publish_opportunities.value in provider.permissions
    )
    return CanPublishResponse(can_publish=allowed)


@router.get("/review-queue", response_model=list[ProviderRead])
async def get_review_queue(
    _: Annotated[AuthenticatedUser, review_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ProviderRead]:
    rows = (
        await session.scalars(
            select(Provider).where(Provider.status.in_(_REVIEW_QUEUE_STATUSES))
        )
    ).all()
    return [await _to_read(session, row) for row in rows]


@router.post("/{provider_id}/review", response_model=ProviderRead)
async def review_provider(
    provider_id: UUID,
    payload: ProviderReviewRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, review_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderRead:
    async with session.begin():
        provider = await session.get(Provider, provider_id)
        if provider is None:
            raise HTTPException(status_code=404, detail="Provider not found.")
        decision = status_from_wire(payload.decision)
        if decision == ProviderStatus.verified and not payload.checklist_complete:
            raise HTTPException(
                status_code=409,
                detail="Every verification check must pass before approval.",
            )
        previous_status = provider.status.value
        provider.status = decision
        if decision == ProviderStatus.verified:
            now = datetime.now(timezone.utc)
            provider.permissions = [permission.value for permission in ProviderPermission]
            provider.verification_date = now
            provider.verified_by = user.uid
            provider.reverification_date = now + timedelta(days=365)
            session.add(
                ProviderActivity(
                    provider_id=provider.id,
                    action="Provider verified",
                    actor_id=user.uid,
                )
            )
        else:
            provider.permissions = [ProviderPermission.manage_organization.value]
            provider.verification_date = None
            provider.verified_by = None
            provider.reverification_date = None
        provider.review_note = payload.note
        await session.flush()
        append_audit(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action=f"provider_review_{payload.decision}",
            entity_type="provider",
            entity_id=provider.id,
            previous_value={"status": previous_status},
            new_value={"status": provider.status.value, "note": payload.note},
            correlation_id=correlation_id(request),
        )
        await session.refresh(provider)
        return await _to_read(session, provider)


@router.post("/{provider_id}/suspend", response_model=ProviderRead)
async def suspend_provider(
    provider_id: UUID,
    payload: ProviderSuspendRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, review_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderRead:
    async with session.begin():
        provider = await session.get(Provider, provider_id)
        if provider is None:
            raise HTTPException(status_code=404, detail="Provider not found.")
        previous_status = provider.status.value
        provider.status = ProviderStatus.suspended
        provider.permissions = []
        provider.review_note = payload.reason
        await session.flush()
        append_audit(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action="provider_suspended",
            entity_type="provider",
            entity_id=provider.id,
            previous_value={"status": previous_status},
            new_value={"status": provider.status.value, "reason": payload.reason},
            correlation_id=correlation_id(request),
        )
        await session.refresh(provider)
        return await _to_read(session, provider)


@router.post("/{provider_id}/appeal", response_model=ProviderRead)
async def appeal_provider(
    provider_id: UUID,
    payload: ProviderAppealRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderRead:
    async with session.begin():
        provider = await session.get(Provider, provider_id)
        if provider is None or provider.user_id != user.uid:
            raise HTTPException(status_code=404, detail="Provider not found.")
        if provider.status not in {ProviderStatus.rejected, ProviderStatus.suspended}:
            raise HTTPException(
                status_code=409,
                detail="Only rejected or suspended providers can appeal.",
            )
        previous_status = provider.status.value
        provider.status = ProviderStatus.pending_review
        provider.review_note = f"Appeal: {payload.reason}"
        session.add(
            ProviderAppeal(provider_id=provider.id, reason=payload.reason, status="Pending")
        )
        await session.flush()
        append_audit(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action="provider_appealed",
            entity_type="provider",
            entity_id=provider.id,
            previous_value={"status": previous_status},
            new_value={"status": provider.status.value, "reason": payload.reason},
            correlation_id=correlation_id(request),
        )
        await session.refresh(provider)
        return await _to_read(session, provider)


@router.post("/{provider_id}/administrators", response_model=ProviderRead)
async def add_administrator(
    provider_id: UUID,
    payload: ProviderAdministratorCreate,
    request: Request,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderRead:
    async with session.begin():
        provider = await session.get(Provider, provider_id)
        if provider is None or provider.user_id != user.uid:
            raise HTTPException(status_code=404, detail="Provider not found.")
        if not provider.has_verified_badge:
            raise HTTPException(
                status_code=409,
                detail="Only verified providers can add administrators.",
            )
        # Stored as model values (snake_case), matching Provider.permissions
        # and every other permission field in this codebase - the payload
        # itself is wire-format (camelCase) and was previously stored
        # unconverted, which silently broke any attempt to check a
        # ProviderAdministrator's own permissions against ProviderPermission
        # (see provider_opportunities.py::_relationship).
        model_permissions = [
            permission_from_wire(item).value for item in payload.permissions
        ]
        session.add(
            ProviderAdministrator(
                provider_id=provider.id,
                user_id=payload.user_id,
                email=payload.email,
                permissions=model_permissions,
            )
        )
        session.add(
            ProviderActivity(
                provider_id=provider.id,
                action="Administrator added",
                actor_id=provider.user_id,
            )
        )
        await session.flush()
        append_audit(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action="provider_administrator_added",
            entity_type="provider",
            entity_id=provider.id,
            new_value={"administrator_user_id": payload.user_id, "permissions": model_permissions},
            correlation_id=correlation_id(request),
        )
        await session.refresh(provider)
        return await _to_read(session, provider)


async def _to_read(session: AsyncSession, provider: Provider) -> ProviderRead:
    administrators = (
        await session.scalars(
            select(ProviderAdministrator).where(
                ProviderAdministrator.provider_id == provider.id
            )
        )
    ).all()
    activity = (
        await session.scalars(
            select(ProviderActivity)
            .where(ProviderActivity.provider_id == provider.id)
            .order_by(ProviderActivity.occurred_at.asc())
        )
    ).all()
    appeals = (
        await session.scalars(
            select(ProviderAppeal)
            .where(ProviderAppeal.provider_id == provider.id)
            .order_by(ProviderAppeal.submitted_at.asc())
        )
    ).all()
    read = ProviderRead.model_validate(provider)
    read.administrators = [
        ProviderAdministratorRead.model_validate(row) for row in administrators
    ]
    read.activity_history = [ProviderActivityRead.model_validate(row) for row in activity]
    read.appeals = [ProviderAppealRead.model_validate(row) for row in appeals]
    return read

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.audit_log import AuditAction, AuditResult
from app.models.collection import CollectionLedgerEntry, CollectionSourceType
from app.models.external_opportunity import (
    ExternalOpportunity,
    PublicationStatus,
    VerificationReview,
    VerificationStatus,
)
from app.schemas.collection import (
    CollectOpportunityRequest,
    CollectedOpportunityRead,
    source_type_from_wire,
)
from app.services.audit_log import append_audit_record
from app.services.parsing import duplicate_fingerprint, payload_hash, utc_now
from app.services.source_registry import seed_opportunity_sources
from app.services.source_scoring import find_approved_source

router = APIRouter(prefix="/collection", tags=["collection"])

# Matches the roles that can reach the administration dashboard's
# Collection Queue screen on the frontend (Permission.viewAdministration in
# lib/features/security/domain/access_control.dart).
collection_access = Depends(
    require_roles("administrator", "securityAdministrator", "superAdministrator")
)

_AUTOMATED_SOURCE_TYPES = frozenset(
    {
        CollectionSourceType.officialApi,
        CollectionSourceType.approvedRss,
        CollectionSourceType.structuredFeed,
        CollectionSourceType.controlledWebCollection,
    }
)


@router.get("/ledger", response_model=list[CollectedOpportunityRead])
async def get_intake_ledger(
    _: Annotated[AuthenticatedUser, collection_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[CollectedOpportunityRead]:
    rows = await session.scalars(
        select(CollectionLedgerEntry).order_by(CollectionLedgerEntry.discovered_at.desc())
    )
    return [CollectedOpportunityRead.model_validate(row) for row in rows.all()]


@router.post("/collect", response_model=CollectedOpportunityRead)
async def collect(
    payload: CollectOpportunityRequest,
    user: Annotated[AuthenticatedUser, collection_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CollectedOpportunityRead:
    source_type = source_type_from_wire(payload.source_type)
    automated = source_type in _AUTOMATED_SOURCE_TYPES
    location = payload.source_location.strip()

    async with session.begin():
        approved_source = payload.approved_source
        if automated:
            registered = await find_approved_source(session, location)
            if registered is None:
                raise HTTPException(
                    status_code=409,
                    detail="Automated collection is restricted to approved registry sources.",
                )
            approved_source = True

        sources = await seed_opportunity_sources(session)
        manual_source = sources["manual_collection"]

        now = utc_now()
        raw_payload = {
            "title": payload.title,
            "provider": payload.provider,
            "hostCountry": payload.host_country,
            "type": payload.type,
            "deadline": payload.deadline.isoformat() if payload.deadline else None,
            "officialSourceUrl": payload.official_source_url,
            "applicationUrl": payload.application_url,
        }
        opportunity = ExternalOpportunity(
            source_id=manual_source.id,
            external_id=uuid.uuid4().hex,
            title=payload.title,
            opportunity_type=payload.type,
            provider_name=payload.provider,
            country=payload.host_country,
            description=payload.summary or None,
            opening_date=payload.application_open_date,
            deadline=payload.deadline,
            opportunity_status="posted",
            official_source_url=payload.official_source_url,
            official_application_url=payload.application_url,
            payload_hash=payload_hash(raw_payload),
            external_fingerprint=duplicate_fingerprint(
                payload.title, payload.provider, payload.deadline
            ),
            duplicate_review_required=False,
            verification_status=VerificationStatus.pending,
            publication_status=PublicationStatus.unpublished,
            collected_at=now,
            last_external_update_at=now,
        )
        session.add(opportunity)
        await session.flush()
        session.add(VerificationReview(opportunity_id=opportunity.id))

        entry = CollectionLedgerEntry(
            id=uuid.uuid4(),
            opportunity_id=opportunity.id,
            source_type=source_type,
            source_location=location,
            discovered_at=now,
            collected_by_user_id=user.uid,
            automated=automated,
            approved_source=approved_source,
            verification_status=VerificationStatus.pending.value,
        )
        session.add(entry)
        await append_audit_record(
            session,
            actor_id=user.uid,
            actor_role=user.role,
            action=AuditAction.opportunityChanged,
            entity_type="collected_opportunity",
            entity_id=str(opportunity.id),
            new_value=f"source_type={source_type.value}",
            result=AuditResult.success,
            correlation_id=f"collect-{opportunity.id}",
        )
        await session.flush()
        return CollectedOpportunityRead.model_validate(entry)

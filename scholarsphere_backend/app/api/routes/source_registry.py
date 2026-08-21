from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.source_registry import SourceRegistryEntry, SourceVerificationStatus
from app.schemas.source_registry import (
    RecordAccessRequest,
    RegisterSourceRequest,
    ReviewSourceRequest,
    SourceRegistryEntryRead,
    source_type_from_wire,
)
from app.services.parsing import utc_now
from app.services.source_scoring import compute_trust_score, normalize_domain, score_for_entry

router = APIRouter(prefix="/source-registry", tags=["source-registry"])

# Matches the roles that can reach the administration dashboard's Source
# Registry screen on the frontend (Permission.viewAdministration in
# lib/features/security/domain/access_control.dart).
staff_access = Depends(require_roles("administrator", "securityAdministrator", "superAdministrator"))


def _require(entry: SourceRegistryEntry | None) -> SourceRegistryEntry:
    if entry is None:
        raise HTTPException(status_code=404, detail="Source was not found.")
    return entry


@router.get("", response_model=list[SourceRegistryEntryRead])
async def get_all(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[SourceRegistryEntryRead]:
    rows = (
        await session.scalars(select(SourceRegistryEntry).order_by(SourceRegistryEntry.name))
    ).all()
    return [SourceRegistryEntryRead.model_validate(row) for row in rows]


@router.post("", response_model=SourceRegistryEntryRead)
async def register(
    payload: RegisterSourceRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SourceRegistryEntryRead:
    domain = normalize_domain(payload.domain)
    if not domain:
        raise HTTPException(status_code=422, detail="A valid source domain is required.")
    async with session.begin():
        collision = await session.scalar(
            select(SourceRegistryEntry).where(SourceRegistryEntry.normalized_domain == domain)
        )
        if collision is not None:
            raise HTTPException(
                status_code=409, detail="This source domain is already registered."
            )
        now = utc_now()
        entry = SourceRegistryEntry(
            id=payload.id,
            name=payload.name,
            type=source_type_from_wire(payload.type),
            domain=payload.domain,
            normalized_domain=domain,
            country=payload.country,
            organization_id=payload.organization_id,
            trust_level=payload.trust_level,
            trust_score=compute_trust_score(
                trust_level=payload.trust_level,
                correction_count=0,
                rejection_count=0,
                accuracy_rate=payload.accuracy_rate,
            ),
            verification_status=SourceVerificationStatus.pending,
            accuracy_rate=payload.accuracy_rate,
            correction_count=0,
            rejection_count=0,
            is_blocked=False,
            created_at=now,
            updated_at=now,
            parser_configuration=payload.parser_configuration,
        )
        session.add(entry)
        await session.flush()
        await session.refresh(entry)
        return SourceRegistryEntryRead.model_validate(entry)


@router.post("/{source_id}/review", response_model=SourceRegistryEntryRead)
async def review(
    source_id: str,
    payload: ReviewSourceRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SourceRegistryEntryRead:
    async with session.begin():
        entry = _require(await session.get(SourceRegistryEntry, source_id))
        entry.trust_score = score_for_entry(entry, trust_level=payload.trust_level)
        entry.trust_level = payload.trust_level
        entry.verification_status = payload.status
        entry.is_blocked = payload.status == SourceVerificationStatus.blocked
        entry.updated_at = utc_now()
        await session.flush()
        await session.refresh(entry)
        return SourceRegistryEntryRead.model_validate(entry)


@router.get("/approved", response_model=SourceRegistryEntryRead | None)
async def approved_source_for(
    location: Annotated[str, Query(min_length=1)],
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SourceRegistryEntryRead | None:
    host = normalize_domain(location)
    now = utc_now()
    rows = (await session.scalars(select(SourceRegistryEntry))).all()
    for entry in rows:
        domain = entry.normalized_domain
        matches_host = host == domain or host.endswith(f".{domain}")
        is_approved = (
            entry.verification_status == SourceVerificationStatus.approved
            and not entry.is_blocked
            and (entry.expires_at is None or entry.expires_at > now)
        )
        if matches_host and is_approved:
            return SourceRegistryEntryRead.model_validate(entry)
    return None


@router.post("/{source_id}/access", response_model=SourceRegistryEntryRead)
async def record_access(
    source_id: str,
    payload: RecordAccessRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SourceRegistryEntryRead:
    async with session.begin():
        entry = _require(await session.get(SourceRegistryEntry, source_id))
        # Score is recomputed from pre-update counters, mirroring
        # DemoSourceRegistryRepository.recordAccess (which builds its
        # `trustScore` from the pre-mutation `current`, not the value
        # being written in the same copyWith call).
        entry.trust_score = score_for_entry(entry)
        now = utc_now()
        entry.last_checked_at = now
        if payload.successful:
            entry.last_successful_access = now
        else:
            entry.rejection_count += 1
        entry.updated_at = now
        await session.flush()
        await session.refresh(entry)
        return SourceRegistryEntryRead.model_validate(entry)


@router.post("/{source_id}/correction", response_model=SourceRegistryEntryRead)
async def record_correction(
    source_id: str,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SourceRegistryEntryRead:
    async with session.begin():
        entry = _require(await session.get(SourceRegistryEntry, source_id))
        # Same pre-mutation scoring quirk as recordAccess above, port of
        # DemoSourceRegistryRepository.recordCorrection.
        entry.trust_score = score_for_entry(entry) - 3
        entry.correction_count += 1
        entry.updated_at = utc_now()
        await session.flush()
        await session.refresh(entry)
        return SourceRegistryEntryRead.model_validate(entry)

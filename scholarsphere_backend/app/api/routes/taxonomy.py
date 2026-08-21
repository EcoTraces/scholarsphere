from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.taxonomy import TaxonomyTerm, TaxonomyVersion
from app.schemas.taxonomy import (
    MergeTaxonomyRequest,
    SaveTaxonomyTermRequest,
    TaxonomyTermRead,
    TaxonomyVersionRead,
    taxonomy_type_from_wire,
)
from app.services.parsing import utc_now
from app.services.taxonomy_matching import duplicate_candidate_groups, normalize

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])

# Matches the roles that can reach the administration dashboard's Data
# Governance screen on the frontend (Permission.viewAdministration in
# lib/features/security/domain/access_control.dart).
staff_access = Depends(require_roles("administrator", "securityAdministrator", "superAdministrator"))


async def _next_version(session: AsyncSession) -> int:
    current_max = await session.scalar(select(func.max(TaxonomyVersion.version)))
    return (current_max or 0) + 1


async def _term_count(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(TaxonomyTerm)) or 0


async def _record_version(
    session: AsyncSession, *, version: int, actor_id: str, reason: str
) -> None:
    session.add(
        TaxonomyVersion(
            version=version,
            created_at=utc_now(),
            created_by=actor_id,
            reason=reason,
            term_count=await _term_count(session),
        )
    )


@router.post("/terms", response_model=TaxonomyTermRead)
async def save_term(
    payload: SaveTaxonomyTermRequest,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaxonomyTermRead:
    term_type = taxonomy_type_from_wire(payload.type)
    normalized = normalize(payload.canonical_name)
    async with session.begin():
        others = (
            await session.scalars(
                select(TaxonomyTerm).where(
                    TaxonomyTerm.id != payload.id, TaxonomyTerm.type == term_type
                )
            )
        ).all()
        collision = any(
            normalize(other.canonical_name) == normalized
            or normalized in {normalize(item) for item in other.synonyms}
            for other in others
        )
        if collision:
            raise HTTPException(
                status_code=409, detail="A canonical or synonymous taxonomy term exists."
            )

        now = utc_now()
        version = await _next_version(session)
        existing = await session.get(TaxonomyTerm, payload.id)
        if existing is None:
            term = TaxonomyTerm(
                id=payload.id,
                type=term_type,
                canonical_name=payload.canonical_name,
                code=payload.code,
                synonyms=payload.synonyms,
                parent_id=payload.parent_id,
                active=payload.active,
                version=version,
                created_at=now,
                updated_at=now,
            )
            session.add(term)
        else:
            existing.type = term_type
            existing.canonical_name = payload.canonical_name
            existing.code = payload.code
            existing.synonyms = payload.synonyms
            existing.parent_id = payload.parent_id
            existing.active = payload.active
            existing.version = version
            existing.updated_at = now
            term = existing
        await session.flush()
        await _record_version(session, version=version, actor_id=user.uid, reason=payload.reason)
        await session.flush()
        await session.refresh(term)
        return TaxonomyTermRead.model_validate(term)


@router.get("/terms/resolve", response_model=TaxonomyTermRead | None)
async def resolve_term(
    type: Annotated[str, Query()],
    value: Annotated[str, Query(min_length=1)],
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaxonomyTermRead | None:
    term_type = taxonomy_type_from_wire(type)
    normalized = normalize(value)
    rows = (
        await session.scalars(
            select(TaxonomyTerm).where(
                TaxonomyTerm.type == term_type, TaxonomyTerm.active.is_(True)
            )
        )
    ).all()
    for term in rows:
        if (
            normalize(term.canonical_name) == normalized
            or (term.code is not None and normalize(term.code) == normalized)
            or normalized in {normalize(item) for item in term.synonyms}
        ):
            return TaxonomyTermRead.model_validate(term)
    return None


@router.get("/terms", response_model=list[TaxonomyTermRead])
async def list_terms(
    type: Annotated[str, Query()],
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
    active_only: bool = True,
) -> list[TaxonomyTermRead]:
    term_type = taxonomy_type_from_wire(type)
    query = select(TaxonomyTerm).where(TaxonomyTerm.type == term_type)
    if active_only:
        query = query.where(TaxonomyTerm.active.is_(True))
    rows = (await session.scalars(query)).all()
    return [TaxonomyTermRead.model_validate(row) for row in rows]


@router.get("/terms/duplicates", response_model=list[list[TaxonomyTermRead]])
async def duplicate_candidates(
    type: Annotated[str, Query()],
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[list[TaxonomyTermRead]]:
    term_type = taxonomy_type_from_wire(type)
    rows = list((await session.scalars(select(TaxonomyTerm).where(TaxonomyTerm.type == term_type))).all())
    groups = duplicate_candidate_groups(rows)
    return [[TaxonomyTermRead.model_validate(term) for term in group] for group in groups]


@router.post("/terms/merge", response_model=TaxonomyTermRead)
async def merge_terms(
    payload: MergeTaxonomyRequest,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TaxonomyTermRead:
    async with session.begin():
        canonical = await session.get(TaxonomyTerm, payload.canonical_id)
        if canonical is None:
            raise HTTPException(status_code=404, detail="Canonical term not found.")
        duplicates = [
            term
            for term_id in set(payload.duplicate_ids)
            if (term := await session.get(TaxonomyTerm, term_id)) is not None
            and term.type == canonical.type
        ]
        version = await _next_version(session)
        now = utc_now()
        merged_synonyms = set(canonical.synonyms)
        for duplicate in duplicates:
            merged_synonyms.add(duplicate.canonical_name)
            merged_synonyms.update(duplicate.synonyms)
        canonical.synonyms = sorted(merged_synonyms)
        canonical.version = version
        canonical.updated_at = now
        for duplicate in duplicates:
            duplicate.active = False
            duplicate.version = version
            duplicate.updated_at = now
        await session.flush()
        await _record_version(
            session,
            version=version,
            actor_id=user.uid,
            reason="Merged duplicate taxonomy terms.",
        )
        await session.flush()
        await session.refresh(canonical)
        return TaxonomyTermRead.model_validate(canonical)


@router.get("/versions", response_model=list[TaxonomyVersionRead])
async def get_versions(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[TaxonomyVersionRead]:
    rows = (
        await session.scalars(
            select(TaxonomyVersion).order_by(TaxonomyVersion.version.desc())
        )
    ).all()
    return [TaxonomyVersionRead.model_validate(row) for row in rows]

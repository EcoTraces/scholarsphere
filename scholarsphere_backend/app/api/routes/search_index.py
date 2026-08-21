from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.public_opportunities import _is_public
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import STAFF_ROLES, require_roles
from app.db.session import get_db
from app.models.external_opportunity import ExternalOpportunity
from app.models.search_index import SearchHistoryEntry, SearchIndexEntry
from app.schemas.search_index import (
    DiscoverySearchRequest,
    DiscoverySearchResultRead,
    OpportunitySnapshot,
    PopularSearchRead,
    RebuildRequest,
    SearchFacetsRead,
    SearchHistoryEntryRead,
    SearchHitRead,
    SynchronizeRequest,
)
from app.services import search_matching
from app.services.parsing import utc_now

router = APIRouter(prefix="/search-index", tags=["search-index"])

any_authenticated = Depends(get_current_user)
# remove()/rebuild() mutate or clear the entire shared index rather than a
# single caller's own data, so - unlike synchronize()/upsert(), which are
# scoped by the real-opportunity existence check below - they are
# staff-only. No current UI caller invokes them outside the admin
# background job that already runs as an authenticated staff action.
staff_access = Depends(require_roles(*STAFF_ROLES))


async def _is_real_public_opportunity(session: AsyncSession, opportunity_id: str) -> bool:
    try:
        parsed_id = UUID(opportunity_id)
    except ValueError:
        return False
    opportunity = await session.get(ExternalOpportunity, parsed_id)
    return opportunity is not None and _is_public(opportunity)


async def _upsert(session: AsyncSession, snapshot: OpportunitySnapshot) -> None:
    """Store or drop one snapshot, always re-verified against the real

    external_opportunities table rather than trusting the client's own
    verificationStatus field - this is what stops a malicious caller from
    poisoning the shared search index with fabricated or already-hidden
    listings. Never removes existing unrelated entries (see synchronize).
    """
    if not await _is_real_public_opportunity(session, snapshot.id):
        await session.execute(delete(SearchIndexEntry).where(SearchIndexEntry.id == snapshot.id))
        return
    entry = await session.get(SearchIndexEntry, snapshot.id)
    data = snapshot.model_dump()
    if entry is None:
        session.add(SearchIndexEntry(id=snapshot.id, data=data))
    else:
        entry.data = data


@router.post("/synchronize", status_code=204)
async def synchronize(
    payload: SynchronizeRequest,
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Upserts every incoming, real, public opportunity into the shared

    index. Unlike DemoSearchIndexRepository.synchronize(), this never
    prunes entries absent from the incoming batch: a self-service caller
    controls only what they add, not what disappears for everyone else.
    Full prune-and-rebuild is reserved for the staff-only rebuild().
    """
    async with session.begin():
        for snapshot in payload.opportunities:
            await _upsert(session, snapshot)


@router.post("/opportunities", status_code=204)
async def upsert_opportunity(
    snapshot: OpportunitySnapshot,
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        await _upsert(session, snapshot)


@router.delete("/opportunities/{opportunity_id}", status_code=204)
async def remove_opportunity(
    opportunity_id: str,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        await session.execute(
            delete(SearchIndexEntry).where(SearchIndexEntry.id == opportunity_id)
        )


@router.post("/rebuild", response_model=int)
async def rebuild(
    payload: RebuildRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> int:
    async with session.begin():
        await session.execute(delete(SearchIndexEntry))
        for snapshot in payload.opportunities:
            await _upsert(session, snapshot)
        count = (await session.scalars(select(SearchIndexEntry))).all()
        return len(count)


@router.post("/search", response_model=DiscoverySearchResultRead)
async def search(
    payload: DiscoverySearchRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DiscoverySearchResultRead:
    now = utc_now()
    rows = (await session.scalars(select(SearchIndexEntry))).all()
    opportunity_filter = payload.filter.to_matching_dict()
    candidates = [
        row.data for row in rows if search_matching.matches(row.data, opportunity_filter, now)
    ]
    terms = search_matching.expand(search_matching.tokenize(payload.query))
    hits: list[SearchHitRead] = []
    for data in candidates:
        relevance, matched_terms = search_matching.score(
            data,
            terms,
            payload.eligibility_scores.get(data.get("id", ""), 0),
            payload.source_trust_scores.get(data.get("id", ""), 0),
            now,
        )
        if not terms or relevance > 0:
            hits.append(SearchHitRead(opportunity=data, score=relevance, matched_terms=matched_terms))
    hits.sort(key=lambda hit: hit.score, reverse=True)
    total = len(hits)
    start = (payload.page - 1) * payload.page_size
    paged = [] if start >= total else hits[start : min(start + payload.page_size, total)]

    query_text = payload.query.strip()
    if query_text:
        # The read above already autobegan a transaction; close it out
        # before opening the explicit one below (session.begin() raises
        # if a transaction is already open on the session).
        await session.commit()
        async with session.begin():
            session.add(
                SearchHistoryEntry(
                    user_id=user.uid,
                    query=query_text,
                    result_count=total,
                    searched_at=now,
                )
            )

    facets_data = search_matching.facets([hit.opportunity for hit in hits])
    suggestions = (
        search_matching.no_result_suggestions([row.data for row in rows], payload.query)
        if total == 0
        else []
    )
    return DiscoverySearchResultRead(
        hits=paged,
        total=total,
        facets=SearchFacetsRead(
            countries=facets_data["countries"],
            funding=facets_data["funding"],
            study_levels=facets_data["studyLevels"],
            institutions=facets_data["institutions"],
        ),
        suggestions=suggestions,
        page=payload.page,
        page_size=payload.page_size,
    )


@router.get("/autocomplete", response_model=list[str])
async def autocomplete(
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
    prefix: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=50)] = 8,
) -> list[str]:
    rows = (await session.scalars(select(SearchIndexEntry))).all()
    return search_matching.autocomplete([row.data for row in rows], prefix, limit)


@router.get("/history", response_model=list[SearchHistoryEntryRead])
async def get_history(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[SearchHistoryEntryRead]:
    rows = (
        await session.scalars(
            select(SearchHistoryEntry)
            .where(SearchHistoryEntry.user_id == user.uid)
            .order_by(SearchHistoryEntry.searched_at.desc())
        )
    ).all()
    return [SearchHistoryEntryRead.model_validate(row, from_attributes=True) for row in rows]


@router.delete("/history", status_code=204)
async def clear_history(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        await session.execute(
            delete(SearchHistoryEntry).where(SearchHistoryEntry.user_id == user.uid)
        )


@router.get("/popular-searches", response_model=list[PopularSearchRead])
async def popular_searches(
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[PopularSearchRead]:
    rows = (await session.scalars(select(SearchHistoryEntry))).all()
    counts: dict[str, int] = {}
    for row in rows:
        key = row.query.lower()
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return [PopularSearchRead(query=query, count=count) for query, count in ranked[:limit]]

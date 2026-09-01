from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.applicant_background import ApplicantBackgroundEntry
from app.schemas.applicant_background import (
    BackgroundEntryCreateRequest,
    BackgroundEntryRead,
    BackgroundEntryUpdateRequest,
)

router = APIRouter(prefix="/applicant-background", tags=["applicant-background"])

any_authenticated = Depends(get_current_user)


async def _require_owned(
    session: AsyncSession, entry_id: UUID, uid: str
) -> ApplicantBackgroundEntry:
    entry = await session.get(ApplicantBackgroundEntry, entry_id)
    if entry is None or entry.user_id != uid:
        raise HTTPException(status_code=404, detail="Background entry was not found.")
    return entry


@router.get("", response_model=list[BackgroundEntryRead])
async def list_entries(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[BackgroundEntryRead]:
    entries = (
        await session.scalars(
            select(ApplicantBackgroundEntry)
            .where(ApplicantBackgroundEntry.user_id == user.uid)
            .order_by(ApplicantBackgroundEntry.category, ApplicantBackgroundEntry.start_date.desc())
        )
    ).all()
    return [BackgroundEntryRead.model_validate(entry) for entry in entries]


@router.post("", response_model=BackgroundEntryRead, status_code=201)
async def create_entry(
    payload: BackgroundEntryCreateRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BackgroundEntryRead:
    async with session.begin():
        entry = ApplicantBackgroundEntry(user_id=user.uid, **payload.model_dump())
        session.add(entry)
        await session.flush()
        await session.refresh(entry)
        return BackgroundEntryRead.model_validate(entry)


@router.patch("/{entry_id}", response_model=BackgroundEntryRead)
async def update_entry(
    entry_id: UUID,
    payload: BackgroundEntryUpdateRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> BackgroundEntryRead:
    async with session.begin():
        entry = await _require_owned(session, entry_id, user.uid)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(entry, field, value)
        await session.flush()
        await session.refresh(entry)
        return BackgroundEntryRead.model_validate(entry)


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        entry = await _require_owned(session, entry_id, user.uid)
        await session.delete(entry)

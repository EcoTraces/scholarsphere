"""Append-only-by-convention version history for premium documents.

"Never silently overwrite user content" (platform spec) is enforced here
structurally: editing a document always inserts a new
``PremiumDocumentVersion`` row rather than mutating an existing one, and
"restoring" an old version copies its content into a brand new version
rather than rewinding in place - the full history is always still there
afterward.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.premium_documents import PremiumDocument, PremiumDocumentVersion
from app.services.parsing import utc_now


class VersionNotFoundError(Exception):
    pass


class CannotDeleteLatestVersionError(Exception):
    pass


async def create_version(
    session: AsyncSession,
    document: PremiumDocument,
    *,
    content: dict,
    created_by: str,
    label: str = "",
    is_ai_generated: bool = False,
    ats_score: float | None = None,
    ats_analysis: dict | None = None,
    quality_score: float | None = None,
    quality_analysis: dict | None = None,
) -> PremiumDocumentVersion:
    next_version = document.latest_version_number + 1
    version = PremiumDocumentVersion(
        id=uuid.uuid4(),
        document_id=document.id,
        version_number=next_version,
        label=label,
        content=content,
        is_ai_generated=is_ai_generated,
        ats_score=ats_score,
        ats_analysis=ats_analysis,
        quality_score=quality_score,
        quality_analysis=quality_analysis,
        created_by=created_by,
    )
    session.add(version)
    document.latest_version_number = next_version
    document.updated_at = utc_now()
    await session.flush()
    return version


async def get_version(
    session: AsyncSession, document_id: uuid.UUID, version_number: int
) -> PremiumDocumentVersion | None:
    return await session.scalar(
        select(PremiumDocumentVersion).where(
            PremiumDocumentVersion.document_id == document_id,
            PremiumDocumentVersion.version_number == version_number,
        )
    )


async def restore_version(
    session: AsyncSession, document: PremiumDocument, *, version_number: int, created_by: str
) -> PremiumDocumentVersion:
    source = await get_version(session, document.id, version_number)
    if source is None:
        raise VersionNotFoundError(f"Version {version_number} does not exist for this document.")
    return await create_version(
        session,
        document,
        content=source.content,
        created_by=created_by,
        label=f"Restored from version {version_number}",
        is_ai_generated=source.is_ai_generated,
        ats_score=source.ats_score,
        ats_analysis=source.ats_analysis,
        quality_score=source.quality_score,
        quality_analysis=source.quality_analysis,
    )


async def delete_version(
    session: AsyncSession, document: PremiumDocument, *, version_number: int
) -> None:
    if version_number == document.latest_version_number:
        raise CannotDeleteLatestVersionError(
            "The current (latest) version cannot be deleted - restore or create a newer "
            "version first."
        )
    version = await get_version(session, document.id, version_number)
    if version is None:
        raise VersionNotFoundError(f"Version {version_number} does not exist for this document.")
    await session.delete(version)
    await session.flush()

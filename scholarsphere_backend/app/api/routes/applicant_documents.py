from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.applicant_document import ApplicantDocument
from app.schemas.applicant_document import (
    ApplicantDocumentCreate,
    ApplicantDocumentRead,
    GrantProviderAccessRequest,
    document_owner_uid,
    type_from_wire,
)
from app.services.parsing import utc_now

router = APIRouter(prefix="/applicant-documents", tags=["applicant documents"])

any_authenticated = Depends(get_current_user)


@router.get("/me", response_model=list[ApplicantDocumentRead])
async def list_my_documents(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ApplicantDocumentRead]:
    rows = (
        await session.scalars(
            select(ApplicantDocument)
            .where(ApplicantDocument.user_id == user.uid)
            .order_by(ApplicantDocument.uploaded_at.desc())
        )
    ).all()
    return [ApplicantDocumentRead.model_validate(row) for row in rows]


@router.post("", response_model=ApplicantDocumentRead)
async def add_document(
    payload: ApplicantDocumentCreate,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicantDocumentRead:
    if document_owner_uid(payload.storage_path) != user.uid:
        raise HTTPException(
            status_code=400,
            detail="Document must be uploaded under your own Storage folder.",
        )
    document_type = type_from_wire(payload.type)
    async with session.begin():
        existing = await session.scalar(
            select(ApplicantDocument).where(
                ApplicantDocument.user_id == user.uid,
                ApplicantDocument.type == document_type,
            )
        )
        if existing is not None:
            existing.file_name = payload.file_name
            existing.storage_path = payload.storage_path
            existing.uploaded_at = utc_now()
            document = existing
        else:
            document = ApplicantDocument(
                user_id=user.uid,
                type=document_type,
                file_name=payload.file_name,
                storage_path=payload.storage_path,
                uploaded_at=utc_now(),
            )
            session.add(document)
        await session.flush()
        await session.refresh(document)
        return ApplicantDocumentRead.model_validate(document)


@router.delete("/{document_id}", status_code=204)
async def remove_document(
    document_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        document = await session.get(ApplicantDocument, document_id)
        if document is None or document.user_id != user.uid:
            raise HTTPException(status_code=404, detail="Document not found.")
        await session.delete(document)


@router.post("/{document_id}/share", response_model=ApplicantDocumentRead)
async def grant_provider_access(
    document_id: UUID,
    payload: GrantProviderAccessRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicantDocumentRead:
    """Owner-only self-service sharing - no active-consent precondition yet.

    See app/models/applicant_document.py and storage.rules for why: Privacy
    has no real consent backend to gate against, and requiring one that can
    never exist would make this endpoint permanently unusable. Recorded
    here for future use; actual differential Storage access for providers
    is a separate, not-yet-built follow-up.
    """
    async with session.begin():
        document = await session.get(ApplicantDocument, document_id)
        if document is None or document.user_id != user.uid:
            raise HTTPException(status_code=404, detail="Document not found.")
        if payload.provider_id not in document.shared_with_provider_ids:
            document.shared_with_provider_ids = [
                *document.shared_with_provider_ids,
                payload.provider_id,
            ]
        await session.flush()
        await session.refresh(document)
        return ApplicantDocumentRead.model_validate(document)

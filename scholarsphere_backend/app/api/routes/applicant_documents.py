from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.applicant_document import ApplicantDocument
from app.models.privacy import ConsentRecord, ConsentType, OrganizationAccessRecord
from app.models.provider import Provider
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
    """Owner-only self-service sharing, gated on an active consent record.

    Mirrors the same precondition app/api/routes/privacy.py's
    record_organization_access already enforces for third-party access:
    sharing is refused (409) unless the caller has a
    ConsentType.third_party_sharing ConsentRecord that is granted and not
    withdrawn. This closes the gap noted in a previous revision of this
    docstring ("Privacy has no real consent backend to gate against") -
    that backend now exists (app/models/privacy.py), so this endpoint no
    longer has an excuse to skip the check. Differential Storage access for
    providers (as opposed to this Postgres-level grant) remains a separate,
    not-yet-built follow-up - see storage.rules.
    """
    async with session.begin():
        document = await session.get(ApplicantDocument, document_id)
        if document is None or document.user_id != user.uid:
            raise HTTPException(status_code=404, detail="Document not found.")
        try:
            provider_uuid = UUID(payload.provider_id)
        except ValueError as error:
            raise HTTPException(
                status_code=404, detail="Provider not found."
            ) from error
        provider = await session.get(Provider, provider_uuid)
        if provider is None:
            raise HTTPException(status_code=404, detail="Provider not found.")
        consent = await session.scalar(
            select(ConsentRecord).where(
                ConsentRecord.user_id == user.uid,
                ConsentRecord.type == ConsentType.third_party_sharing,
            )
        )
        if consent is None or consent.withdrawn_at is not None:
            raise HTTPException(
                status_code=409,
                detail="Third-party access requires explicit active user consent.",
            )
        if payload.provider_id not in document.shared_with_provider_ids:
            document.shared_with_provider_ids = [
                *document.shared_with_provider_ids,
                payload.provider_id,
            ]
            session.add(
                OrganizationAccessRecord(
                    user_id=user.uid,
                    organization_id=payload.provider_id,
                    organization_name=provider.organization_name,
                    data_categories=[document.type.value],
                    accessed_at=utc_now(),
                    consent_record_type=ConsentType.third_party_sharing,
                )
            )
        await session.flush()
        await session.refresh(document)
        return ApplicantDocumentRead.model_validate(document)

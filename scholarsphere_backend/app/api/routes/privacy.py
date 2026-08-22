from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import STAFF_ROLES, require_roles
from app.db.session import get_db
from app.models.applicant_document import ApplicantDocument
from app.models.applicant_profile import ApplicantProfile
from app.models.privacy import (
    ConsentRecord,
    ConsentType,
    OrganizationAccessRecord,
    PrivacyIncident,
    PrivacyRequest,
)
from app.schemas.privacy import (
    ConsentRecordRead,
    GrantConsentRequest,
    OrganizationAccessRecordRead,
    PrivacyIncidentRead,
    PrivacyRequestRead,
    RecordIncidentRequest,
    RecordOrganizationAccessRequest,
    SubmitPrivacyRequest,
    consent_type_from_wire,
    is_required_legal_consent,
    request_type_from_wire,
)
from app.services.parsing import utc_now
from app.services.privacy_rules import is_minor, minor_can_grant

router = APIRouter(prefix="/privacy", tags=["privacy"])

any_authenticated = Depends(get_current_user)
staff_access = Depends(require_roles(*STAFF_ROLES))


@router.get("/consents", response_model=list[ConsentRecordRead])
async def get_consents(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ConsentRecordRead]:
    rows = (
        await session.scalars(
            select(ConsentRecord).where(ConsentRecord.user_id == user.uid)
        )
    ).all()
    return [ConsentRecordRead.model_validate(row) for row in rows]


@router.post("/consents", response_model=ConsentRecordRead)
async def grant_consent(
    payload: GrantConsentRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ConsentRecordRead:
    consent_type = consent_type_from_wire(payload.type)
    async with session.begin():
        profile = await session.get(ApplicantProfile, user.uid)
        date_of_birth = profile.date_of_birth if profile is not None else None
        if is_minor(date_of_birth, utc_now().date()) and not minor_can_grant(consent_type):
            raise HTTPException(
                status_code=409, detail="This consent is restricted for minor accounts."
            )
        record = await session.scalar(
            select(ConsentRecord).where(
                ConsentRecord.user_id == user.uid, ConsentRecord.type == consent_type
            )
        )
        now = utc_now()
        if record is None:
            record = ConsentRecord(
                user_id=user.uid,
                type=consent_type,
                policy_version=payload.policy_version,
                granted_at=now,
                withdrawn_at=None,
            )
            session.add(record)
        else:
            record.policy_version = payload.policy_version
            record.granted_at = now
            record.withdrawn_at = None
        await session.flush()
        await session.refresh(record)
        return ConsentRecordRead.model_validate(record)


@router.post("/consents/{consent_type}/withdraw", status_code=204)
async def withdraw_consent(
    consent_type: str,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    parsed_type = consent_type_from_wire(consent_type)
    if is_required_legal_consent(parsed_type):
        raise HTTPException(
            status_code=409,
            detail=(
                "Required legal acceptance cannot be withdrawn while the account "
                "remains active. Submit an account-deletion request instead."
            ),
        )
    async with session.begin():
        record = await session.scalar(
            select(ConsentRecord).where(
                ConsentRecord.user_id == user.uid, ConsentRecord.type == parsed_type
            )
        )
        if record is not None:
            record.withdrawn_at = utc_now()
        if parsed_type == ConsentType.third_party_sharing:
            # Withdrawing sharing consent must revoke every existing
            # provider grant, not just block new ones - otherwise a
            # provider a user shared a document with before withdrawing
            # would keep whatever access applicant_documents.py's
            # grant_provider_access already recorded for them.
            documents = (
                await session.scalars(
                    select(ApplicantDocument).where(
                        ApplicantDocument.user_id == user.uid
                    )
                )
            ).all()
            for document in documents:
                if document.shared_with_provider_ids:
                    document.shared_with_provider_ids = []


@router.post("/requests", response_model=PrivacyRequestRead)
async def submit_privacy_request(
    payload: SubmitPrivacyRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PrivacyRequestRead:
    async with session.begin():
        request = PrivacyRequest(
            user_id=user.uid,
            type=request_type_from_wire(payload.type),
            submitted_at=utc_now(),
            notes=payload.notes,
        )
        session.add(request)
        await session.flush()
        await session.refresh(request)
        return PrivacyRequestRead.model_validate(request)


@router.get("/requests", response_model=list[PrivacyRequestRead])
async def get_privacy_requests(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[PrivacyRequestRead]:
    rows = (
        await session.scalars(
            select(PrivacyRequest).where(PrivacyRequest.user_id == user.uid)
        )
    ).all()
    return [PrivacyRequestRead.model_validate(row) for row in rows]


@router.get("/access-history", response_model=list[OrganizationAccessRecordRead])
async def get_access_history(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[OrganizationAccessRecordRead]:
    rows = (
        await session.scalars(
            select(OrganizationAccessRecord).where(
                OrganizationAccessRecord.user_id == user.uid
            )
        )
    ).all()
    return [OrganizationAccessRecordRead.model_validate(row) for row in rows]


@router.post("/access-history", response_model=OrganizationAccessRecordRead)
async def record_organization_access(
    payload: RecordOrganizationAccessRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationAccessRecordRead:
    """Staff/ops-recorded audit entry - no self-service caller today.

    Mirrors the demo's precondition: recording is refused unless the
    subject user has an active third-party-sharing consent on file.
    """
    async with session.begin():
        consent = await session.scalar(
            select(ConsentRecord).where(
                ConsentRecord.user_id == payload.user_id,
                ConsentRecord.type == ConsentType.third_party_sharing,
            )
        )
        if consent is None or consent.withdrawn_at is not None:
            raise HTTPException(
                status_code=409,
                detail="Third-party access requires explicit active user consent.",
            )
        record = OrganizationAccessRecord(
            user_id=payload.user_id,
            organization_id=payload.organization_id,
            organization_name=payload.organization_name,
            data_categories=payload.data_categories,
            accessed_at=utc_now(),
            consent_record_type=ConsentType.third_party_sharing,
        )
        session.add(record)
        await session.flush()
        await session.refresh(record)
        return OrganizationAccessRecordRead.model_validate(record)


@router.post("/incidents", response_model=PrivacyIncidentRead)
async def record_incident(
    payload: RecordIncidentRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PrivacyIncidentRead:
    async with session.begin():
        incident = PrivacyIncident(
            recorded_at=utc_now(),
            summary=payload.summary,
            affected_user_ids=payload.affected_user_ids,
        )
        session.add(incident)
        await session.flush()
        await session.refresh(incident)
        return PrivacyIncidentRead.model_validate(incident)


@router.get("/incidents", response_model=list[PrivacyIncidentRead])
async def get_incidents(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[PrivacyIncidentRead]:
    rows = (await session.scalars(select(PrivacyIncident))).all()
    return [PrivacyIncidentRead.model_validate(row) for row in rows]

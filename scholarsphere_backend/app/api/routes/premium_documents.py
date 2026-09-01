from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.entitlements import PREMIUM_FEATURE_REQUIRED_DETAIL, get_active_entitlement, has_feature
from app.db.session import get_db
from app.models.applicant_background import ApplicantBackgroundEntry
from app.models.applicant_profile import ApplicantProfile
from app.models.application_preparation import PremiumWorkspace
from app.models.external_opportunity import ExternalOpportunity
from app.models.premium_billing import AIUsageStatus, PremiumFeature
from app.models.premium_documents import PremiumDocument, PremiumDocumentVersion
from app.schemas.premium_documents import (
    AtsAnalyzeResponse,
    DocumentCreateRequest,
    DocumentRead,
    GenerateCvRequest,
    GenerateNarrativeRequest,
    VersionCreateRequest,
    VersionRead,
)
from app.services.ai_provider import AIProviderError, get_ai_provider
from app.services.ats_analysis import analyze_ats
from app.services.document_generation import (
    CV_KINDS,
    KIND_FEATURE_MAP,
    ai_polish_text,
    build_cv_content,
    generate_narrative_document,
)
from app.services.document_export import export_document
from app.services.document_versioning import (
    CannotDeleteLatestVersionError,
    VersionNotFoundError,
    create_version,
    delete_version,
    get_version,
    restore_version,
)
from app.services.parsing import utc_now
from app.services.usage_limits import UsageLimitExceededError, check_usage_allowed, record_usage

router = APIRouter(prefix="/premium-documents", tags=["premium-documents"])

any_authenticated = Depends(get_current_user)


async def _require_owned_document(
    session: AsyncSession, document_id: UUID, uid: str
) -> PremiumDocument:
    document = await session.get(PremiumDocument, document_id)
    if document is None or document.user_id != uid:
        raise HTTPException(status_code=404, detail="Document was not found.")
    return document


async def _require_feature(
    session: AsyncSession, user: AuthenticatedUser, feature: PremiumFeature
) -> None:
    entitlement = await get_active_entitlement(session, user.uid)
    if not has_feature(entitlement, feature):
        raise HTTPException(status_code=402, detail=PREMIUM_FEATURE_REQUIRED_DETAIL)


@router.get("", response_model=list[DocumentRead])
async def list_documents(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_id: UUID | None = None,
) -> list[DocumentRead]:
    query = select(PremiumDocument).where(PremiumDocument.user_id == user.uid)
    if workspace_id is not None:
        query = query.where(PremiumDocument.workspace_id == workspace_id)
    documents = (await session.scalars(query)).all()
    return [DocumentRead.model_validate(document) for document in documents]


@router.post("", response_model=DocumentRead, status_code=201)
async def create_document(
    payload: DocumentCreateRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentRead:
    async with session.begin():
        await _require_feature(session, user, KIND_FEATURE_MAP[payload.kind])
        if payload.workspace_id is not None:
            workspace = await session.get(PremiumWorkspace, payload.workspace_id)
            if workspace is None or workspace.user_id != user.uid:
                raise HTTPException(status_code=404, detail="Workspace was not found.")
        document = PremiumDocument(
            user_id=user.uid, workspace_id=payload.workspace_id, kind=payload.kind, title=payload.title
        )
        session.add(document)
        await session.flush()
        await session.refresh(document)
        return DocumentRead.model_validate(document)


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentRead:
    document = await _require_owned_document(session, document_id, user.uid)
    return DocumentRead.model_validate(document)


@router.get("/{document_id}/versions", response_model=list[VersionRead])
async def list_versions(
    document_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[VersionRead]:
    document = await _require_owned_document(session, document_id, user.uid)
    versions = (
        await session.scalars(
            select(PremiumDocumentVersion)
            .where(PremiumDocumentVersion.document_id == document.id)
            .order_by(PremiumDocumentVersion.version_number.desc())
        )
    ).all()
    return [VersionRead.model_validate(version) for version in versions]


@router.post("/{document_id}/versions", response_model=VersionRead, status_code=201)
async def save_version(
    document_id: UUID,
    payload: VersionCreateRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> VersionRead:
    """Manual save - the applicant's own edits, never AI-generated content."""
    async with session.begin():
        document = await _require_owned_document(session, document_id, user.uid)
        await _require_feature(session, user, KIND_FEATURE_MAP[document.kind])
        version = await create_version(
            session,
            document,
            content=payload.content,
            created_by=user.uid,
            label=payload.label,
            is_ai_generated=False,
        )
        return VersionRead.model_validate(version)


@router.post("/{document_id}/versions/{version_number}/restore", response_model=VersionRead)
async def restore_document_version(
    document_id: UUID,
    version_number: int,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> VersionRead:
    async with session.begin():
        document = await _require_owned_document(session, document_id, user.uid)
        await _require_feature(session, user, PremiumFeature.document_versioning)
        try:
            version = await restore_version(
                session, document, version_number=version_number, created_by=user.uid
            )
        except VersionNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return VersionRead.model_validate(version)


@router.delete("/{document_id}/versions/{version_number}", status_code=204)
async def delete_document_version(
    document_id: UUID,
    version_number: int,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        document = await _require_owned_document(session, document_id, user.uid)
        await _require_feature(session, user, PremiumFeature.document_versioning)
        try:
            await delete_version(session, document, version_number=version_number)
        except CannotDeleteLatestVersionError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except VersionNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{document_id}/generate/cv", response_model=VersionRead)
async def generate_cv(
    document_id: UUID,
    payload: GenerateCvRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> VersionRead:
    """Deterministic assembly from the applicant's own background data;

    ``polish`` opts into an additional AI wording pass (never adds new
    facts - see document_generation.py's module docstring) and requires
    the separate ``ai_document_improvement`` feature.
    """
    async with session.begin():
        document = await _require_owned_document(session, document_id, user.uid)
        if document.kind not in CV_KINDS:
            raise HTTPException(status_code=409, detail="This document is not a CV.")
        await _require_feature(session, user, KIND_FEATURE_MAP[document.kind])

        profile = await session.get(ApplicantProfile, user.uid)
        entries = list(
            (
                await session.scalars(
                    select(ApplicantBackgroundEntry).where(
                        ApplicantBackgroundEntry.user_id == user.uid
                    )
                )
            ).all()
        )
        content = build_cv_content(entries, profile, summary=payload.summary)

        is_ai_generated = False
        if payload.polish:
            await _require_feature(session, user, PremiumFeature.ai_document_improvement)
            settings_provider = get_ai_provider()
            try:
                await check_usage_allowed(session, user_id=user.uid, feature="cv_polish")
                if content["summary"]:
                    content["summary"] = await ai_polish_text(
                        content["summary"], section_label="Summary", ai_provider=settings_provider
                    )
                for section in ("education", "experience", "projects"):
                    for entry in content[section]:
                        if entry.get("description"):
                            entry["description"] = await ai_polish_text(
                                entry["description"],
                                section_label=section,
                                ai_provider=settings_provider,
                            )
                is_ai_generated = True
                await record_usage(
                    session,
                    user_id=user.uid,
                    feature="cv_polish",
                    provider=type(settings_provider).__name__,
                    model=getattr(settings_provider, "_model", ""),
                    tokens_used=None,
                    status=AIUsageStatus.success,
                )
            except UsageLimitExceededError as error:
                raise HTTPException(status_code=429, detail=str(error)) from error
            except AIProviderError as error:
                await record_usage(
                    session,
                    user_id=user.uid,
                    feature="cv_polish",
                    provider="unknown",
                    model="",
                    tokens_used=None,
                    status=AIUsageStatus.failed,
                )
                raise HTTPException(status_code=503, detail=str(error)) from error

        version = await create_version(
            session, document, content=content, created_by=user.uid, is_ai_generated=is_ai_generated
        )
        return VersionRead.model_validate(version)


@router.post("/{document_id}/generate/narrative", response_model=VersionRead)
async def generate_narrative(
    document_id: UUID,
    payload: GenerateNarrativeRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> VersionRead:
    async with session.begin():
        document = await _require_owned_document(session, document_id, user.uid)
        if document.kind in CV_KINDS:
            raise HTTPException(
                status_code=409, detail="Use /generate/cv for CV documents."
            )
        await _require_feature(session, user, KIND_FEATURE_MAP[document.kind])

        try:
            await check_usage_allowed(session, user_id=user.uid, feature=document.kind.value)
        except UsageLimitExceededError as error:
            raise HTTPException(status_code=429, detail=str(error)) from error

        profile = await session.get(ApplicantProfile, user.uid)
        entries = list(
            (
                await session.scalars(
                    select(ApplicantBackgroundEntry).where(
                        ApplicantBackgroundEntry.user_id == user.uid
                    )
                )
            ).all()
        )
        workspace = (
            await session.get(PremiumWorkspace, document.workspace_id)
            if document.workspace_id
            else None
        )
        opportunity = (
            await session.get(ExternalOpportunity, payload.opportunity_id)
            if payload.opportunity_id
            else None
        )

        ai_provider = get_ai_provider()
        try:
            body = await generate_narrative_document(
                document.kind,
                entries=entries,
                profile=profile,
                workspace=workspace,
                opportunity=opportunity,
                user_answers=payload.user_answers,
                ai_provider=ai_provider,
            )
        except AIProviderError as error:
            await record_usage(
                session,
                user_id=user.uid,
                feature=document.kind.value,
                provider="unknown",
                model="",
                tokens_used=None,
                status=AIUsageStatus.failed,
            )
            raise HTTPException(status_code=503, detail=str(error)) from error

        await record_usage(
            session,
            user_id=user.uid,
            feature=document.kind.value,
            provider=type(ai_provider).__name__,
            model=getattr(ai_provider, "_model", ""),
            tokens_used=None,
            status=AIUsageStatus.success,
        )
        version = await create_version(
            session,
            document,
            content={"body": body},
            created_by=user.uid,
            is_ai_generated=True,
        )
        return VersionRead.model_validate(version)


@router.post(
    "/{document_id}/versions/{version_number}/ats-analysis", response_model=AtsAnalyzeResponse
)
async def analyze_document_ats(
    document_id: UUID,
    version_number: int,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AtsAnalyzeResponse:
    async with session.begin():
        document = await _require_owned_document(session, document_id, user.uid)
        if document.kind not in CV_KINDS:
            raise HTTPException(status_code=409, detail="ATS analysis only applies to CVs.")
        await _require_feature(session, user, PremiumFeature.ats_optimization)
        version = await get_version(session, document.id, version_number)
        if version is None:
            raise HTTPException(status_code=404, detail="Version was not found.")

        target_keywords: list[str] = []
        analysis = analyze_ats(version.content, target_keywords=target_keywords or None)
        version.ats_score = analysis.score
        version.ats_analysis = {
            "structure_score": analysis.structure_score,
            "formatting_score": analysis.formatting_score,
            "readability_score": analysis.readability_score,
            "keyword_score": analysis.keyword_score,
            "missing_sections": analysis.missing_sections,
            "issues": analysis.issues,
            "strengths": analysis.strengths,
        }
        await session.flush()
        return AtsAnalyzeResponse(
            score=analysis.score,
            structure_score=analysis.structure_score,
            formatting_score=analysis.formatting_score,
            readability_score=analysis.readability_score,
            keyword_score=analysis.keyword_score,
            missing_sections=analysis.missing_sections,
            issues=analysis.issues,
            strengths=analysis.strengths,
            disclaimer=analysis.disclaimer,
        )


@router.get("/{document_id}/versions/{version_number}/export")
async def export_document_version(
    document_id: UUID,
    version_number: int,
    fmt: str,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    if fmt not in {"pdf", "docx"}:
        raise HTTPException(status_code=422, detail="fmt must be 'pdf' or 'docx'.")
    document = await _require_owned_document(session, document_id, user.uid)
    feature = PremiumFeature.pdf_export if fmt == "pdf" else PremiumFeature.docx_export
    await _require_feature(session, user, feature)
    version = await get_version(session, document.id, version_number)
    if version is None:
        raise HTTPException(status_code=404, detail="Version was not found.")

    data, content_type = export_document(document.kind, document.title, version.content, fmt)
    filename = f"{document.title.replace(' ', '_')}_v{version_number}.{fmt}"
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Generated-At": utc_now().isoformat(),
        },
    )

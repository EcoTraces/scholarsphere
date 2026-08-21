from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.applicant_document import ApplicantDocument, DocumentType
from app.models.applicant_profile import ApplicantProfile
from app.models.guidance import ApplicationGuidancePlan
from app.schemas.guidance import (
    ApplicationGuidancePlanRead,
    ConfirmSubmissionRequest,
    CreatePlanRequest,
    TrackRecommendationLetterRequest,
    UpdateItemRequest,
    item_status_from_wire,
)
from app.services.guidance_matching import document_type_from_requirement
from app.services.parsing import utc_now

router = APIRouter(prefix="/guidance", tags=["guidance"])

any_authenticated = Depends(get_current_user)


async def _require_owned(
    session: AsyncSession, plan_id: str, uid: str
) -> ApplicationGuidancePlan:
    plan = await session.get(ApplicationGuidancePlan, plan_id)
    if plan is None or plan.user_id != uid:
        raise HTTPException(status_code=404, detail="Guidance plan was not found.")
    return plan


@router.post("/plans", response_model=ApplicationGuidancePlanRead)
async def create_plan(
    payload: CreatePlanRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationGuidancePlanRead:
    async with session.begin():
        profile = await session.get(ApplicantProfile, user.uid)
        documents = (
            await session.scalars(
                select(ApplicantDocument).where(ApplicantDocument.user_id == user.uid)
            )
        ).all()
        available_types = {document.type for document in documents}

        items: list[dict] = []
        order = 0
        for requirement in payload.required_documents:
            order += 1
            doc_type = document_type_from_requirement(requirement)
            items.append(
                {
                    "id": f"document-{order - 1}",
                    "type": "requiredDocument",
                    "title": requirement,
                    "guidance": "Prepare the requested document and verify its format.",
                    "status": "ready"
                    if doc_type is not None and doc_type in available_types
                    else "missing",
                    "required": True,
                    "order": order,
                    "due_at": (payload.opportunity_deadline - timedelta(days=7)).isoformat(),
                }
            )
        for step in payload.application_procedure:
            order += 1
            items.append(
                {
                    "id": f"step-{order - 1}",
                    "type": "applicationStep",
                    "title": step,
                    "guidance": "Complete this step on the official application portal.",
                    "status": "notStarted",
                    "required": True,
                    "order": order,
                    "due_at": payload.opportunity_deadline.isoformat(),
                }
            )

        missing_profile: list[str] = []
        if profile is None or not profile.nationality:
            missing_profile.append("Nationality")
        if profile is None or not profile.highest_qualification:
            missing_profile.append("Highest qualification")
        if profile is None or not profile.degree_field:
            missing_profile.append("Academic field")
        for field in missing_profile:
            order += 1
            items.append(
                {
                    "id": f"profile-{order - 1}",
                    "type": "profileInformation",
                    "title": field,
                    "guidance": "Complete this information in your private profile.",
                    "status": "missing",
                    "required": True,
                    "order": order,
                    "due_at": None,
                }
            )

        cv_required = any(
            document_type_from_requirement(requirement) == DocumentType.curriculum_vitae
            for requirement in payload.required_documents
        )
        items.append(
            {
                "id": "cv",
                "type": "curriculumVitae",
                "title": "CV readiness review",
                "guidance": "Check accuracy, dates, relevance, and consistent formatting.",
                "status": "inProgress"
                if DocumentType.curriculum_vitae in available_types
                else "missing",
                "required": cv_required,
                "order": order + 1,
                "due_at": None,
            }
        )
        items.append(
            {
                "id": "interview",
                "type": "interviewPreparation",
                "title": "Interview preparation",
                "guidance": (
                    "Review the program, prepare evidence-based examples, and test "
                    "your setup."
                ),
                "status": "notStarted",
                "required": False,
                "order": order + 2,
                "due_at": None,
            }
        )

        now = utc_now()
        plan_id = f"{user.uid}-{payload.opportunity_id}"
        existing = await session.get(ApplicationGuidancePlan, plan_id)
        if existing is None:
            plan = ApplicationGuidancePlan(
                id=plan_id,
                user_id=user.uid,
                opportunity_id=payload.opportunity_id,
                items=items,
                recommendation_letters=[],
                timeline_start=now,
                deadline=payload.opportunity_deadline,
                follow_up_reminders=[
                    (payload.opportunity_deadline + timedelta(days=7)).isoformat(),
                    (payload.opportunity_deadline + timedelta(days=30)).isoformat(),
                ],
                updated_at=now,
            )
            session.add(plan)
        else:
            existing.items = items
            existing.deadline = payload.opportunity_deadline
            existing.follow_up_reminders = [
                (payload.opportunity_deadline + timedelta(days=7)).isoformat(),
                (payload.opportunity_deadline + timedelta(days=30)).isoformat(),
            ]
            existing.updated_at = now
            plan = existing
        await session.flush()
        await session.refresh(plan)
        return ApplicationGuidancePlanRead.model_validate(plan)


@router.get("/plans/{opportunity_id}", response_model=ApplicationGuidancePlanRead | None)
async def get_plan(
    opportunity_id: str,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationGuidancePlanRead | None:
    plan = await session.get(ApplicationGuidancePlan, f"{user.uid}-{opportunity_id}")
    if plan is None:
        return None
    return ApplicationGuidancePlanRead.model_validate(plan)


@router.post("/plans/{plan_id}/items/{item_id}", response_model=ApplicationGuidancePlanRead)
async def update_item(
    plan_id: str,
    item_id: str,
    payload: UpdateItemRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationGuidancePlanRead:
    async with session.begin():
        plan = await _require_owned(session, plan_id, user.uid)
        item_status_from_wire(payload.status)
        plan.items = [
            {**item, "status": payload.status} if item["id"] == item_id else item
            for item in plan.items
        ]
        plan.updated_at = utc_now()
        await session.flush()
        await session.refresh(plan)
        return ApplicationGuidancePlanRead.model_validate(plan)


@router.post(
    "/plans/{plan_id}/recommendation-letters", response_model=ApplicationGuidancePlanRead
)
async def track_recommendation_letter(
    plan_id: str,
    payload: TrackRecommendationLetterRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationGuidancePlanRead:
    async with session.begin():
        plan = await _require_owned(session, plan_id, user.uid)
        plan.recommendation_letters = [
            *plan.recommendation_letters,
            {
                "id": payload.id,
                "referee_name": payload.referee_name,
                "referee_email": payload.referee_email,
                "requested_at": payload.requested_at.isoformat(),
                "due_at": payload.due_at.isoformat(),
                "received": payload.received,
                "received_at": payload.received_at.isoformat()
                if payload.received_at
                else None,
            },
        ]
        plan.updated_at = utc_now()
        await session.flush()
        await session.refresh(plan)
        return ApplicationGuidancePlanRead.model_validate(plan)


@router.post("/plans/{plan_id}/submission", response_model=ApplicationGuidancePlanRead)
async def confirm_submission(
    plan_id: str,
    payload: ConfirmSubmissionRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationGuidancePlanRead:
    if not payload.application_reference.strip() or not payload.official_portal.strip():
        raise HTTPException(
            status_code=422,
            detail="Submission confirmation requires an official portal and reference.",
        )
    async with session.begin():
        plan = await _require_owned(session, plan_id, user.uid)
        plan.submission_confirmation = {
            "confirmed_at": payload.confirmed_at.isoformat(),
            "application_reference": payload.application_reference,
            "confirmed_by_user_id": payload.confirmed_by_user_id,
            "official_portal": payload.official_portal,
        }
        plan.updated_at = utc_now()
        await session.flush()
        await session.refresh(plan)
        return ApplicationGuidancePlanRead.model_validate(plan)

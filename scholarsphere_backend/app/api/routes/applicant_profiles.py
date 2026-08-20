from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import STAFF_ROLES, require_roles
from app.db.session import get_db
from app.models.applicant_profile import ApplicantProfile
from app.schemas.applicant_profile import (
    ApplicantProfilePage,
    ApplicantProfileRead,
    ApplicantProfileUpdate,
    employment_status_from_wire,
    english_test_status_from_wire,
    passport_status_from_wire,
)

router = APIRouter(prefix="/applicant-profiles", tags=["applicant profiles"])

any_authenticated = Depends(get_current_user)
staff_access = Depends(require_roles(*STAFF_ROLES))


@router.get("/me", response_model=ApplicantProfileRead)
async def get_my_profile(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicantProfileRead:
    profile = await session.get(ApplicantProfile, user.uid)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return ApplicantProfileRead.model_validate(profile)


@router.put("/me", response_model=ApplicantProfileRead)
async def save_my_profile(
    payload: ApplicantProfileUpdate,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicantProfileRead:
    async with session.begin():
        profile = await session.get(ApplicantProfile, user.uid)
        if profile is None:
            profile = ApplicantProfile(user_id=user.uid)
            session.add(profile)
        profile.full_name = payload.full_name
        profile.nationality = payload.nationality
        profile.country_of_residence = payload.country_of_residence
        profile.date_of_birth = payload.date_of_birth
        profile.gender = payload.gender
        profile.highest_qualification = payload.highest_qualification
        profile.degree_field = payload.degree_field
        profile.academic_classification = payload.academic_classification
        profile.graduation_year = payload.graduation_year
        profile.work_experience_years = payload.work_experience_years
        profile.preferred_study_levels = payload.preferred_study_levels
        profile.preferred_countries = payload.preferred_countries
        profile.areas_of_interest = payload.areas_of_interest
        profile.english_test_status = english_test_status_from_wire(
            payload.english_test_status
        )
        profile.passport_status = passport_status_from_wire(payload.passport_status)
        profile.employment_status = employment_status_from_wire(payload.employment_status)
        profile.funding_preferences = payload.funding_preferences
        profile.special_eligibility_categories = payload.special_eligibility_categories
        await session.flush()
        await session.refresh(profile)
        return ApplicantProfileRead.model_validate(profile)


@router.get("/admin", response_model=ApplicantProfilePage)
async def list_all_profiles(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ApplicantProfilePage:
    total = await session.scalar(select(func.count(ApplicantProfile.user_id)))
    rows = (
        await session.scalars(
            select(ApplicantProfile)
            .order_by(ApplicantProfile.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return ApplicantProfilePage(
        items=[ApplicantProfileRead.model_validate(row) for row in rows],
        total=total or 0,
        page=page,
        page_size=page_size,
    )

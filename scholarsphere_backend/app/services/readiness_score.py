"""Application Readiness Score - computed live from real, current data on

every request, never a stored guess that can drift stale. The weights and
sub-scores below are the entire scoring model; there is nothing hidden
elsewhere, and the API response echoes these same weights so the number
is always explainable to the applicant who sees it.

    Profile completeness    15%
    Background completeness 10%
    Documents               40%
    Requirement matches     20%
    Checklist               15%
                            ----
                            100%
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applicant_background import ApplicantBackgroundEntry
from app.models.applicant_profile import ApplicantProfile
from app.models.application_preparation import (
    ChecklistItemStatus,
    PersonalizedChecklistItem,
    PremiumWorkspace,
    RequirementMatch,
    RequirementMatchStatus,
)
from app.models.premium_documents import PremiumDocument
from app.services.category_workflow import workflow_for

WEIGHTS = {
    "profile": 0.15,
    "background": 0.10,
    "documents": 0.40,
    "requirements": 0.20,
    "checklist": 0.15,
}

_PROFILE_FIELDS = (
    "full_name",
    "nationality",
    "country_of_residence",
    "highest_qualification",
    "degree_field",
    "academic_classification",
)

_REQUIREMENT_CREDIT = {
    RequirementMatchStatus.match: 1.0,
    RequirementMatchStatus.partial_match: 0.5,
    RequirementMatchStatus.needs_verification: 0.25,
    RequirementMatchStatus.missing: 0.0,
}


@dataclass(frozen=True)
class ReadinessBreakdown:
    profile_pct: float
    background_pct: float
    documents_pct: float
    requirements_pct: float
    checklist_pct: float
    overall_pct: float
    weights: dict[str, float] = field(default_factory=lambda: dict(WEIGHTS))


def _profile_pct(profile: ApplicantProfile | None) -> float:
    if profile is None:
        return 0.0
    filled = sum(1 for name in _PROFILE_FIELDS if getattr(profile, name))
    filled += 1 if profile.english_test_status.value != "not_taken" else 0
    filled += 1 if profile.passport_status.value != "unavailable" else 0
    return round(100 * filled / (len(_PROFILE_FIELDS) + 2), 1)


def _background_pct(entries: list[ApplicantBackgroundEntry]) -> float:
    # Five or more real background entries (education, experience,
    # projects, ...) reach 100% - a simple, documented saturation rule
    # rather than a category-specific requirement count, since the exact
    # right number of entries genuinely varies by applicant.
    return round(min(100.0, len(entries) * 20.0), 1)


def _documents_pct(workspace: PremiumWorkspace, documents: list[PremiumDocument]) -> float:
    required_kinds = workflow_for(workspace.category).document_kinds
    if not required_kinds:
        return 100.0
    completed = {
        document.kind
        for document in documents
        if document.latest_version_number >= 1
    }
    matched = sum(1 for kind in required_kinds if kind in completed)
    return round(100 * matched / len(required_kinds), 1)


def _requirements_pct(matches: list[RequirementMatch]) -> float:
    if not matches:
        return 0.0
    total_credit = sum(_REQUIREMENT_CREDIT[match.status] for match in matches)
    return round(100 * total_credit / len(matches), 1)


def _checklist_pct(items: list[PersonalizedChecklistItem]) -> float:
    applicable = [item for item in items if item.status != ChecklistItemStatus.not_applicable]
    if not applicable:
        return 0.0
    done = sum(1 for item in applicable if item.status == ChecklistItemStatus.done)
    return round(100 * done / len(applicable), 1)


async def compute_readiness(session: AsyncSession, workspace: PremiumWorkspace) -> ReadinessBreakdown:
    profile = await session.get(ApplicantProfile, workspace.user_id)
    background_entries = (
        await session.scalars(
            select(ApplicantBackgroundEntry).where(
                ApplicantBackgroundEntry.user_id == workspace.user_id
            )
        )
    ).all()
    documents = (
        await session.scalars(
            select(PremiumDocument).where(
                (PremiumDocument.workspace_id == workspace.id)
                | (
                    (PremiumDocument.user_id == workspace.user_id)
                    & (PremiumDocument.workspace_id.is_(None))
                )
            )
        )
    ).all()
    requirement_matches = (
        await session.scalars(
            select(RequirementMatch).where(RequirementMatch.workspace_id == workspace.id)
        )
    ).all()
    checklist_items = (
        await session.scalars(
            select(PersonalizedChecklistItem).where(
                PersonalizedChecklistItem.workspace_id == workspace.id
            )
        )
    ).all()

    profile_pct = _profile_pct(profile)
    background_pct = _background_pct(list(background_entries))
    documents_pct = _documents_pct(workspace, list(documents))
    requirements_pct = _requirements_pct(list(requirement_matches))
    checklist_pct = _checklist_pct(list(checklist_items))

    overall = (
        profile_pct * WEIGHTS["profile"]
        + background_pct * WEIGHTS["background"]
        + documents_pct * WEIGHTS["documents"]
        + requirements_pct * WEIGHTS["requirements"]
        + checklist_pct * WEIGHTS["checklist"]
    )

    return ReadinessBreakdown(
        profile_pct=profile_pct,
        background_pct=background_pct,
        documents_pct=documents_pct,
        requirements_pct=requirements_pct,
        checklist_pct=checklist_pct,
        overall_pct=round(overall, 1),
    )

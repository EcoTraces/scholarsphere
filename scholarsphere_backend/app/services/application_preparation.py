"""Orchestration for the premium Application Preparation workspace:

creating a workspace, running requirement matching against the real
target opportunity's own text, and generating the category-driven
checklist (app/services/category_workflow.py).
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applicant_background import ApplicantBackgroundEntry
from app.models.applicant_profile import ApplicantProfile
from app.models.application_preparation import (
    ApplicantCategory,
    PersonalizedChecklistItem,
    PremiumWorkspace,
    RequirementMatch,
)
from app.models.external_opportunity import ExternalOpportunity
from app.services.category_workflow import workflow_for
from app.services.parsing import utc_now
from app.services.requirement_matching import classify_requirement, extract_requirement_candidates


async def create_workspace(
    session: AsyncSession,
    *,
    user_id: str,
    application_id: uuid.UUID,
    category: ApplicantCategory,
    target_university: str,
    target_program: str,
) -> PremiumWorkspace:
    workspace = PremiumWorkspace(
        id=uuid.uuid4(),
        user_id=user_id,
        application_id=application_id,
        category=category,
        target_university=target_university,
        target_program=target_program,
    )
    session.add(workspace)
    await session.flush()
    return workspace


async def generate_checklist(
    session: AsyncSession, workspace: PremiumWorkspace
) -> list[PersonalizedChecklistItem]:
    """Idempotent: only creates items for ``item_key``s not already present

    on this workspace, so re-running (e.g. after a category change) never
    duplicates or silently resets an item the applicant already marked
    done.
    """
    existing_keys = set(
        (
            await session.scalars(
                select(PersonalizedChecklistItem.item_key).where(
                    PersonalizedChecklistItem.workspace_id == workspace.id
                )
            )
        ).all()
    )
    workflow = workflow_for(workspace.category)
    created: list[PersonalizedChecklistItem] = []
    for order, spec in enumerate(workflow.checklist_items):
        if spec.item_key in existing_keys:
            continue
        item = PersonalizedChecklistItem(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            item_key=spec.item_key,
            label=spec.label,
            category=spec.category,
            auto_generated=True,
            sort_order=order,
        )
        session.add(item)
        created.append(item)
    if created:
        await session.flush()
    return created


async def run_requirement_matching(
    session: AsyncSession, workspace: PremiumWorkspace, opportunity: ExternalOpportunity
) -> list[RequirementMatch]:
    """Regenerates this workspace's requirement matches from the target

    opportunity's *current* real description text - replaces the prior
    set (an opportunity's own published requirements can change) rather
    than appending duplicates.
    """
    await session.execute(
        delete(RequirementMatch).where(RequirementMatch.workspace_id == workspace.id)
    )

    profile = await session.get(ApplicantProfile, workspace.user_id)
    background_entries = list(
        (
            await session.scalars(
                select(ApplicantBackgroundEntry).where(
                    ApplicantBackgroundEntry.user_id == workspace.user_id
                )
            )
        ).all()
    )

    candidates = extract_requirement_candidates(opportunity.description or "")
    matches: list[RequirementMatch] = []
    now = utc_now()
    for requirement_text in candidates:
        status, notes = classify_requirement(
            requirement_text, profile=profile, background_entries=background_entries
        )
        match = RequirementMatch(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            requirement_text=requirement_text,
            status=status,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        session.add(match)
        matches.append(match)
    await session.flush()
    return matches

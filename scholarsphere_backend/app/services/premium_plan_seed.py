"""Seeds the premium plan catalog once, if a given plan's code doesn't
exist yet. This is a seed, not a sync: once a plan row exists, admins own
it entirely via the plans-admin routes (app/api/routes/premium_admin.py)
- re-running this never overwrites an admin's price/feature-list edits,
and never removes a plan an admin has deactivated.

Two kinds of plan are seeded:

- The flagship "Complete Premium Application Package" (``seed_default_plan``,
  code ``settings.premium_plan_id``) - every ``PremiumFeature``, priced as
  a bundle discount against buying every individual plan below separately.
- Six individual, per-service plans (``seed_individual_plans``) - so an
  applicant who only wants one or two services (e.g. just a CV/resume, or
  just an SOP) can buy exactly that instead of the whole bundle. Each
  plan's ``features`` list always includes the cross-cutting utility
  features (AI-assisted improvement, document versioning, PDF/DOCX
  export) alongside its core builder feature, since without those a buyer
  of, say, the CV Builder plan alone couldn't even export the CV they
  built - see app/services/document_generation.py's
  ``DOCUMENT_KIND_FEATURE`` map and app/api/routes/premium_documents.py
  for exactly which routes each feature key gates.

Every price here is a starting point, not a fixed business decision -
admins can edit any plan's price, name, description, or feature list at
any time via PATCH /premium/admin/plans/{id}, same as the bundle always
could.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.premium_billing import BillingInterval, PremiumFeature, PremiumPlan

# Every builder plan includes these alongside its own core feature(s), so a
# standalone buyer can still improve, version, and export what they build.
_DOCUMENT_UTILITY_FEATURES = [
    PremiumFeature.ai_document_improvement.value,
    PremiumFeature.document_versioning.value,
    PremiumFeature.pdf_export.value,
    PremiumFeature.docx_export.value,
]

_INDIVIDUAL_PLANS: list[dict] = [
    {
        "code": "cv_resume_builder",
        "name": "CV & Resume Builder",
        "description": (
            "Build and refine a CV or resume: CV builder with ATS "
            "optimization, AI-assisted improvement, versioning, and "
            "PDF/DOCX export."
        ),
        "price_cents": 2_500,
        "features": [
            PremiumFeature.cv_builder.value,
            PremiumFeature.ats_optimization.value,
            *_DOCUMENT_UTILITY_FEATURES,
        ],
        "sort_order": 1,
    },
    {
        "code": "sop_builder",
        "name": "SOP & Personal Statement Builder",
        "description": (
            "Build a statement of purpose, personal statement, or "
            "motivation letter, with AI-assisted improvement, versioning, "
            "and PDF/DOCX export."
        ),
        "price_cents": 2_500,
        "features": [PremiumFeature.sop_builder.value, *_DOCUMENT_UTILITY_FEATURES],
        "sort_order": 2,
    },
    {
        "code": "study_plan_builder",
        "name": "Study Plan Builder",
        "description": (
            "Build a study plan for your target programme, with "
            "AI-assisted improvement, versioning, and PDF/DOCX export."
        ),
        "price_cents": 2_000,
        "features": [PremiumFeature.study_plan_builder.value, *_DOCUMENT_UTILITY_FEATURES],
        "sort_order": 3,
    },
    {
        "code": "research_proposal_builder",
        "name": "Research Proposal Builder",
        "description": (
            "Build a research proposal for graduate or fellowship "
            "applications, with AI-assisted improvement, versioning, and "
            "PDF/DOCX export."
        ),
        "price_cents": 3_000,
        "features": [
            PremiumFeature.research_proposal_builder.value,
            *_DOCUMENT_UTILITY_FEATURES,
        ],
        "sort_order": 4,
    },
    {
        "code": "fellowship_preparation",
        "name": "Fellowship Preparation",
        "description": (
            "Build leadership, personal, and impact statements and essays "
            "for fellowship applications, with AI-assisted improvement, "
            "versioning, and PDF/DOCX export."
        ),
        "price_cents": 3_000,
        "features": [
            PremiumFeature.fellowship_preparation.value,
            *_DOCUMENT_UTILITY_FEATURES,
        ],
        "sort_order": 5,
    },
    {
        "code": "strategy_readiness_toolkit",
        "name": "Application Strategy & Readiness Toolkit",
        "description": (
            "Application strategy guidance, requirement matching against "
            "real opportunity listings, an honest readiness score, and a "
            "personalized checklist - no document builder included."
        ),
        "price_cents": 1_500,
        "features": [
            PremiumFeature.application_strategy.value,
            PremiumFeature.requirement_matching.value,
            PremiumFeature.readiness_score.value,
            PremiumFeature.personalized_checklist.value,
        ],
        "sort_order": 6,
    },
]


async def seed_default_plan(session: AsyncSession, settings: Settings | None = None) -> PremiumPlan:
    settings = settings or get_settings()
    existing = await session.scalar(
        select(PremiumPlan).where(PremiumPlan.code == settings.premium_plan_id)
    )
    if existing is not None:
        return existing

    plan = PremiumPlan(
        id=uuid.uuid4(),
        code=settings.premium_plan_id,
        name="Complete Premium Application Package",
        description=(
            "Every individual plan combined, at a discount: application "
            "strategy, requirement matching, readiness scoring, "
            "personalized checklist, CV builder with ATS optimization, SOP "
            "builder, study plan builder, research proposal builder, "
            "fellowship preparation, AI-assisted document improvement, "
            "document versioning, and PDF/DOCX export."
        ),
        price_cents=settings.premium_price_cents,
        currency=settings.payment_currency,
        billing_interval=BillingInterval.one_time,
        features=[feature.value for feature in PremiumFeature],
        is_active=True,
        sort_order=0,
        updated_by="system-seed",
    )
    session.add(plan)
    await session.flush()
    return plan


async def seed_individual_plans(
    session: AsyncSession, settings: Settings | None = None
) -> list[PremiumPlan]:
    settings = settings or get_settings()
    created: list[PremiumPlan] = []
    for spec in _INDIVIDUAL_PLANS:
        existing = await session.scalar(
            select(PremiumPlan).where(PremiumPlan.code == spec["code"])
        )
        if existing is not None:
            continue
        plan = PremiumPlan(
            id=uuid.uuid4(),
            code=spec["code"],
            name=spec["name"],
            description=spec["description"],
            price_cents=spec["price_cents"],
            currency=settings.payment_currency,
            billing_interval=BillingInterval.one_time,
            features=spec["features"],
            is_active=True,
            sort_order=spec["sort_order"],
            updated_by="system-seed",
        )
        session.add(plan)
        created.append(plan)
    if created:
        await session.flush()
    return created

"""Seeds the flagship "Complete Premium Application Package" plan row once,

if no plan with ``settings.premium_plan_id`` exists yet. This is a seed,
not a sync: once the row exists, admins own it entirely via the
plans-admin routes (app/api/routes/premium_admin.py) - re-running this
never overwrites an admin's price/feature-list edits.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.premium_billing import BillingInterval, PremiumFeature, PremiumPlan


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
            "Application strategy, requirement matching, readiness scoring, "
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

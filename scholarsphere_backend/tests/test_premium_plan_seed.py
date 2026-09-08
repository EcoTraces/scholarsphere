"""Unit tests for the premium plan catalog seed - not just the flagship
bundle, but the individual per-service plans that let an applicant buy
exactly one service (e.g. only a CV/resume) instead of the whole bundle.
"""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.models.premium_billing import PremiumFeature, PremiumPlan
from app.services.premium_plan_seed import seed_default_plan, seed_individual_plans


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_individual_plans_are_seeded_alongside_the_bundle(session: AsyncSession) -> None:
    settings = Settings(_env_file=None)
    await seed_default_plan(session, settings)
    await seed_individual_plans(session, settings)
    await session.commit()

    plans = (await session.scalars(select(PremiumPlan).order_by(PremiumPlan.sort_order))).all()
    codes = [plan.code for plan in plans]
    assert codes == [
        settings.premium_plan_id,
        "cv_resume_builder",
        "sop_builder",
        "study_plan_builder",
        "research_proposal_builder",
        "fellowship_preparation",
        "strategy_readiness_toolkit",
    ]


@pytest.mark.asyncio
async def test_each_individual_plan_can_be_bought_alone_and_use_its_own_features(
    session: AsyncSession,
) -> None:
    """Every individual plan must include the document utility features
    (AI improvement, versioning, PDF/DOCX export) alongside its core
    builder feature - otherwise a standalone buyer couldn't export what
    they built. Only the strategy/readiness toolkit is exempt: it has no
    document builder at all.
    """
    settings = Settings(_env_file=None)
    await seed_individual_plans(session, settings)
    await session.commit()

    plans = {
        plan.code: plan
        for plan in (await session.scalars(select(PremiumPlan))).all()
    }

    utility_features = {
        PremiumFeature.ai_document_improvement.value,
        PremiumFeature.document_versioning.value,
        PremiumFeature.pdf_export.value,
        PremiumFeature.docx_export.value,
    }
    builder_plans_and_core_feature = {
        "cv_resume_builder": PremiumFeature.cv_builder.value,
        "sop_builder": PremiumFeature.sop_builder.value,
        "study_plan_builder": PremiumFeature.study_plan_builder.value,
        "research_proposal_builder": PremiumFeature.research_proposal_builder.value,
        "fellowship_preparation": PremiumFeature.fellowship_preparation.value,
    }
    for code, core_feature in builder_plans_and_core_feature.items():
        plan = plans[code]
        assert core_feature in plan.features
        assert utility_features.issubset(set(plan.features))

    toolkit = plans["strategy_readiness_toolkit"]
    assert set(toolkit.features) == {
        PremiumFeature.application_strategy.value,
        PremiumFeature.requirement_matching.value,
        PremiumFeature.readiness_score.value,
        PremiumFeature.personalized_checklist.value,
    }


@pytest.mark.asyncio
async def test_individual_plans_sum_to_more_than_the_bundle_price(session: AsyncSession) -> None:
    """The whole point of a bundle is to be a discount - if buying every
    individual plan separately were ever cheaper than (or equal to) the
    bundle, nobody would rationally buy the bundle."""
    settings = Settings(_env_file=None)
    bundle = await seed_default_plan(session, settings)
    individual = await seed_individual_plans(session, settings)
    await session.commit()

    assert sum(plan.price_cents for plan in individual) > bundle.price_cents


@pytest.mark.asyncio
async def test_seed_individual_plans_is_idempotent(session: AsyncSession) -> None:
    settings = Settings(_env_file=None)
    first_run = await seed_individual_plans(session, settings)
    await session.commit()
    assert len(first_run) == 6

    second_run = await seed_individual_plans(session, settings)
    await session.commit()
    assert second_run == []

    all_plans = (await session.scalars(select(PremiumPlan))).all()
    assert len(all_plans) == 6


@pytest.mark.asyncio
async def test_seed_never_overwrites_an_admin_edited_plan(session: AsyncSession) -> None:
    """Re-running the seed (e.g. on every app restart) must never clobber
    a price an admin has since changed - the same seed-not-sync contract
    the bundle plan already had."""
    settings = Settings(_env_file=None)
    await seed_individual_plans(session, settings)
    await session.commit()

    edited = await session.scalar(
        select(PremiumPlan).where(PremiumPlan.code == "cv_resume_builder")
    )
    edited.price_cents = 999
    edited.updated_by = "admin-1"
    await session.commit()

    await seed_individual_plans(session, settings)
    await session.commit()

    reloaded = await session.scalar(
        select(PremiumPlan).where(PremiumPlan.code == "cv_resume_builder")
    )
    assert reloaded.price_cents == 999

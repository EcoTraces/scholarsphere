import uuid
from collections.abc import AsyncIterator
from datetime import timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from sqlalchemy import select

from app.models.applicant_background import ApplicantBackgroundEntry, BackgroundEntryCategory
from app.models.application import Application, ApplicationStage
from app.models.application_preparation import ApplicantCategory, PremiumWorkspace
from app.models.external_opportunity import ExternalOpportunity, OpportunitySource
from app.models.premium_billing import (
    AIUsageRecord,
    AIUsageStatus,
    BillingInterval,
    Entitlement,
    EntitlementStatus,
    PremiumFeature,
    PremiumPlan,
)
from app.services.ai_provider import AIGenerationResult
from app.services.parsing import utc_now


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


def user(uid: str = "applicant-1") -> AuthenticatedUser:
    return AuthenticatedUser(
        uid=uid, email=f"{uid}@example.test", email_verified=True, role="applicant", permissions=frozenset()
    )


def overrides(session: AsyncSession, *, uid: str = "applicant-1") -> None:
    async def current_user() -> AuthenticatedUser:
        return user(uid)

    async def database() -> AsyncIterator[AsyncSession]:
        try:
            yield session
        finally:
            await session.rollback()

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database


class StubAIProvider:
    async def generate_text(self, *, system_prompt: str, user_prompt: str, max_tokens: int) -> AIGenerationResult:
        return AIGenerationResult(
            text="A concise, polished rewrite grounded in the same facts.",
            provider="stub",
            model="stub-model",
            tokens_used=42,
        )


async def _seed_entitlement(session: AsyncSession, *, uid: str = "applicant-1") -> Entitlement:
    plan = PremiumPlan(
        id=uuid.uuid4(),
        code="complete_premium",
        name="Complete Premium",
        price_cents=10000,
        currency="USD",
        billing_interval=BillingInterval.one_time,
        features=[f.value for f in PremiumFeature],
    )
    session.add(plan)
    await session.flush()
    entitlement = Entitlement(
        id=uuid.uuid4(),
        user_id=uid,
        plan_id=plan.id,
        feature_keys=[f.value for f in PremiumFeature],
        status=EntitlementStatus.active,
    )
    session.add(entitlement)
    await session.commit()
    return entitlement


async def _seed_background(session: AsyncSession, *, uid: str = "applicant-1") -> None:
    session.add(
        ApplicantBackgroundEntry(
            id=uuid.uuid4(),
            user_id=uid,
            category=BackgroundEntryCategory.education,
            title="BSc Computer Science",
            organization="Fourah Bay College",
            description="First class honours.",
        )
    )
    await session.commit()


async def _seed_workspace(session: AsyncSession, *, uid: str = "applicant-1") -> PremiumWorkspace:
    source = OpportunitySource(
        id=uuid.uuid4(),
        source_code="test_source_docs",
        source_name="Test Source",
        source_type="government",
        base_url="https://example.org",
        authentication_type="none",
        trust_level="web_scraped",
    )
    session.add(source)
    await session.flush()
    opportunity = ExternalOpportunity(
        id=uuid.uuid4(),
        source_id=source.id,
        external_id="ext-docs-1",
        title="MSc Astrophysics Scholarship",
        opportunity_type="scholarship",
        provider_name="Example Provider",
        opportunity_status="posted",
        payload_hash="hash-docs-1",
        external_fingerprint="fp-docs-1",
        collected_at=utc_now(),
        last_external_update_at=utc_now(),
    )
    session.add(opportunity)
    await session.flush()
    application = Application(
        id=uuid.uuid4(),
        user_id=uid,
        opportunity_id=opportunity.id,
        opportunity_title=opportunity.title,
        provider_name=opportunity.provider_name,
        stage=ApplicationStage.saved,
    )
    session.add(application)
    await session.flush()
    workspace = PremiumWorkspace(
        id=uuid.uuid4(),
        user_id=uid,
        application_id=application.id,
        category=ApplicantCategory.postgraduate,
        target_university="Example University",
        target_program="Astrophysics",
    )
    session.add(workspace)
    await session.commit()
    return workspace


@pytest.mark.asyncio
async def test_free_user_cannot_create_cv_document(session: AsyncSession) -> None:
    """CRITICAL: FREE USER -> protected feature denied."""
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/premium-documents", json={"kind": "cv_professional", "title": "My CV"}
        )
        assert response.status_code == 402


@pytest.mark.asyncio
async def test_cv_builder_is_grounded_in_real_background_data(session: AsyncSession) -> None:
    await _seed_entitlement(session)
    await _seed_background(session)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/premium-documents", json={"kind": "cv_professional", "title": "My CV"}
        )
        assert create.status_code == 201
        document_id = create.json()["id"]

        generate = await client.post(
            f"/api/v1/premium-documents/{document_id}/generate/cv",
            json={"summary": "Aspiring data scientist.", "polish": False},
        )
        assert generate.status_code == 200
        content = generate.json()["content"]
        assert generate.json()["is_ai_generated"] is False
        assert content["education"][0]["institution"] == "Fourah Bay College"
        assert content["education"][0]["description"] == "First class honours."
        # Never fabricated: no education/experience the applicant didn't enter.
        assert len(content["education"]) == 1
        assert content["experience"] == []

        versions = await client.get(f"/api/v1/premium-documents/{document_id}/versions")
        assert len(versions.json()) == 1


@pytest.mark.asyncio
async def test_ats_analysis_never_claims_guarantee(session: AsyncSession) -> None:
    await _seed_entitlement(session)
    await _seed_background(session)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/premium-documents", json={"kind": "cv_professional", "title": "My CV"}
        )
        document_id = create.json()["id"]
        generate = await client.post(
            f"/api/v1/premium-documents/{document_id}/generate/cv",
            json={"summary": "Aspiring data scientist.", "polish": False},
        )
        version_number = generate.json()["version_number"]

        analysis = await client.post(
            f"/api/v1/premium-documents/{document_id}/versions/{version_number}/ats-analysis"
        )
        assert analysis.status_code == 200
        body = analysis.json()
        assert 0 <= body["score"] <= 100
        assert "does not guarantee" in body["disclaimer"].lower()


@pytest.mark.asyncio
async def test_cv_export_pdf_and_docx(session: AsyncSession) -> None:
    await _seed_entitlement(session)
    await _seed_background(session)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/premium-documents", json={"kind": "cv_professional", "title": "My CV"}
        )
        document_id = create.json()["id"]
        generate = await client.post(
            f"/api/v1/premium-documents/{document_id}/generate/cv",
            json={"summary": "", "polish": False},
        )
        version_number = generate.json()["version_number"]

        pdf = await client.get(
            f"/api/v1/premium-documents/{document_id}/versions/{version_number}/export?fmt=pdf"
        )
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"

        docx = await client.get(
            f"/api/v1/premium-documents/{document_id}/versions/{version_number}/export?fmt=docx"
        )
        assert docx.status_code == 200
        assert docx.headers["content-type"].startswith("application/vnd.openxmlformats")


@pytest.mark.asyncio
async def test_narrative_generation_without_ai_provider_returns_503(session: AsyncSession) -> None:
    await _seed_entitlement(session)
    await _seed_background(session)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/premium-documents", json={"kind": "sop", "title": "My SOP"}
        )
        document_id = create.json()["id"]
        response = await client.post(
            f"/api/v1/premium-documents/{document_id}/generate/narrative", json={"user_answers": {}}
        )
        assert response.status_code == 503
        assert "not configured" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_narrative_generation_with_stub_ai_provider(session: AsyncSession, monkeypatch) -> None:
    await _seed_entitlement(session)
    await _seed_background(session)
    monkeypatch.setattr(
        "app.api.routes.premium_documents.get_ai_provider", lambda: StubAIProvider()
    )
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/premium-documents", json={"kind": "sop", "title": "My SOP"}
        )
        document_id = create.json()["id"]
        response = await client.post(
            f"/api/v1/premium-documents/{document_id}/generate/narrative",
            json={"user_answers": {"Why this program?": "It matches my career goals."}},
        )
        assert response.status_code == 200
        assert response.json()["is_ai_generated"] is True
        assert response.json()["content"]["body"] == (
            "A concise, polished rewrite grounded in the same facts."
        )


@pytest.mark.asyncio
async def test_version_restore_never_overwrites_history(session: AsyncSession) -> None:
    await _seed_entitlement(session)
    await _seed_background(session)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/premium-documents", json={"kind": "cv_professional", "title": "My CV"}
        )
        document_id = create.json()["id"]
        v1 = await client.post(
            f"/api/v1/premium-documents/{document_id}/generate/cv",
            json={"summary": "Draft one.", "polish": False},
        )
        v2 = await client.post(
            f"/api/v1/premium-documents/{document_id}/generate/cv",
            json={"summary": "Draft two.", "polish": False},
        )
        assert v1.json()["version_number"] == 1
        assert v2.json()["version_number"] == 2

        restore = await client.post(
            f"/api/v1/premium-documents/{document_id}/versions/1/restore"
        )
        assert restore.status_code == 200
        assert restore.json()["version_number"] == 3
        assert restore.json()["content"]["summary"] == "Draft one."

        versions = await client.get(f"/api/v1/premium-documents/{document_id}/versions")
        assert len(versions.json()) == 3

        cannot_delete_latest = await client.delete(
            f"/api/v1/premium-documents/{document_id}/versions/3"
        )
        assert cannot_delete_latest.status_code == 409

        can_delete_old = await client.delete(
            f"/api/v1/premium-documents/{document_id}/versions/2"
        )
        assert can_delete_old.status_code == 204


@pytest.mark.asyncio
async def test_failed_narrative_generation_still_records_ai_usage(session: AsyncSession) -> None:
    """Regression test: raising the HTTPException from *inside*

    `async with session.begin()` was silently rolling back the
    deliberately-persisted "failed" AIUsageRecord (the same class of bug
    already fixed once in payment_service.py::initiate_checkout) - a
    failed AI attempt must still be visible to the admin usage dashboard
    and to usage-limit accounting, not just report a 503 with nothing
    saved behind it.
    """
    await _seed_entitlement(session)
    await _seed_background(session)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/premium-documents", json={"kind": "sop", "title": "My SOP"}
        )
        document_id = create.json()["id"]
        response = await client.post(
            f"/api/v1/premium-documents/{document_id}/generate/narrative", json={"user_answers": {}}
        )
        assert response.status_code == 503

    records = (await session.scalars(select(AIUsageRecord))).all()
    assert len(records) == 1
    assert records[0].status == AIUsageStatus.failed
    assert records[0].feature == "sop"


@pytest.mark.asyncio
async def test_failed_cv_polish_still_records_ai_usage(session: AsyncSession) -> None:
    """Same regression as above, for the CV-polish AI path."""
    await _seed_entitlement(session)
    await _seed_background(session)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/premium-documents", json={"kind": "cv_professional", "title": "My CV"}
        )
        document_id = create.json()["id"]
        response = await client.post(
            f"/api/v1/premium-documents/{document_id}/generate/cv",
            json={"summary": "Aspiring scientist.", "polish": True},
        )
        assert response.status_code == 503

        # No half-generated version should exist either - the whole
        # attempt rolled back cleanly, not left in a partially-committed
        # state.
        versions = await client.get(f"/api/v1/premium-documents/{document_id}/versions")
        assert versions.json() == []

    records = (await session.scalars(select(AIUsageRecord))).all()
    assert len(records) == 1
    assert records[0].status == AIUsageStatus.failed
    assert records[0].feature == "cv_polish"


@pytest.mark.asyncio
async def test_export_filename_is_sanitized_against_malicious_title(session: AsyncSession) -> None:
    """Regression test: a document title is applicant-chosen free text with

    no character restriction at the schema layer and was previously
    interpolated directly into the Content-Disposition header - a title
    containing a quote or CR/LF could corrupt the header or attempt
    response splitting.
    """
    await _seed_entitlement(session)
    await _seed_background(session)
    overrides(session)
    malicious_title = 'My"CV\r\nX-Injected: evil'
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/premium-documents", json={"kind": "cv_professional", "title": malicious_title}
        )
        document_id = create.json()["id"]
        await client.post(
            f"/api/v1/premium-documents/{document_id}/generate/cv",
            json={"summary": "", "polish": False},
        )
        export = await client.get(
            f"/api/v1/premium-documents/{document_id}/versions/1/export?fmt=pdf"
        )
        assert export.status_code == 200
        disposition = export.headers["content-disposition"]
        assert "\r" not in disposition and "\n" not in disposition
        assert "X-Injected" not in export.headers
        assert disposition == 'attachment; filename="My_CV_X-Injected_evil_v1.pdf"'


@pytest.mark.asyncio
async def test_ats_analysis_uses_real_target_keywords_from_workspace(session: AsyncSession) -> None:
    """Regression test: ATS keyword-coverage analysis previously always

    received a hardcoded empty keyword list, so `keyword_score` silently
    stayed `None` for every real request - the "relevance to keywords"
    requirement was implemented but never actually wired to a target.
    """
    await _seed_entitlement(session)
    await _seed_background(session)
    workspace = await _seed_workspace(session)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/premium-documents",
            json={"kind": "cv_professional", "title": "My CV", "workspace_id": str(workspace.id)},
        )
        document_id = create.json()["id"]
        # A CV with no mention of "Astrophysics" (the real target program).
        await client.post(
            f"/api/v1/premium-documents/{document_id}/generate/cv",
            json={"summary": "Aspiring researcher.", "polish": False},
        )
        analysis = await client.post(
            f"/api/v1/premium-documents/{document_id}/versions/1/ats-analysis"
        )
        assert analysis.status_code == 200
        body = analysis.json()
        assert body["keyword_score"] is not None
        assert body["keyword_score"] < 100.0
        assert any("Astrophysics" in issue for issue in body["issues"])


@pytest.mark.asyncio
async def test_pdf_export_does_not_crash_on_ordinary_text_with_angle_brackets(
    session: AsyncSession,
) -> None:
    """Regression test: ReportLab's ``Paragraph`` parses its text as a

    small XML dialect - passed through unescaped, completely ordinary
    prose containing a bare ``<``, ``>``, or ``&`` (a GPA comparison, an
    ampersand in an institution name, ...) crashed every PDF export of
    that document with an unhandled `ValueError`.
    """
    await _seed_entitlement(session)
    session.add(
        ApplicantBackgroundEntry(
            id=uuid.uuid4(),
            user_id="applicant-1",
            category=BackgroundEntryCategory.education,
            title="BSc <Physics & Maths>",
            organization="A & B University",
            description="GPA > 3.5 & < 4.0, x < y comparisons",
        )
    )
    await session.commit()
    overrides(session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/premium-documents",
            json={"kind": "cv_professional", "title": "CV <draft> & notes"},
        )
        document_id = create.json()["id"]
        generate = await client.post(
            f"/api/v1/premium-documents/{document_id}/generate/cv",
            json={"summary": "Worked on x<y & z>w problems.", "polish": False},
        )
        assert generate.status_code == 200

        pdf = await client.get(
            f"/api/v1/premium-documents/{document_id}/versions/1/export?fmt=pdf"
        )
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"

        docx = await client.get(
            f"/api/v1/premium-documents/{document_id}/versions/1/export?fmt=docx"
        )
        assert docx.status_code == 200


@pytest.mark.asyncio
async def test_older_entitlement_features_are_not_lost_when_a_newer_one_is_granted(
    session: AsyncSession,
) -> None:
    """Regression test: entitlement checks previously only ever looked at

    the single most-recently-granted entitlement
    (get_active_entitlement/has_feature) - a user who bought a narrower
    package (e.g. "CV/ATS only") and later bought a different narrower
    package (e.g. "SOP only") would silently lose access to the CV
    features they already paid for, because only the newer entitlement's
    feature list was ever checked. Real premium access must be the union
    of every active entitlement, not just the latest one.
    """
    cv_plan = PremiumPlan(
        id=uuid.uuid4(),
        code="cv_ats_only",
        name="CV/ATS",
        price_cents=3500,
        currency="USD",
        billing_interval=BillingInterval.one_time,
        features=[PremiumFeature.cv_builder.value, PremiumFeature.ats_optimization.value],
    )
    sop_plan = PremiumPlan(
        id=uuid.uuid4(),
        code="sop_only",
        name="SOP",
        price_cents=2500,
        currency="USD",
        billing_interval=BillingInterval.one_time,
        features=[PremiumFeature.sop_builder.value],
    )
    session.add_all([cv_plan, sop_plan])
    await session.flush()
    older = Entitlement(
        id=uuid.uuid4(),
        user_id="applicant-1",
        plan_id=cv_plan.id,
        feature_keys=cv_plan.features,
        status=EntitlementStatus.active,
        granted_at=utc_now() - timedelta(days=10),
    )
    newer = Entitlement(
        id=uuid.uuid4(),
        user_id="applicant-1",
        plan_id=sop_plan.id,
        feature_keys=sop_plan.features,
        status=EntitlementStatus.active,
        granted_at=utc_now(),
    )
    session.add_all([older, newer])
    await session.commit()
    await _seed_background(session)
    overrides(session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        status = await client.get("/api/v1/premium/me")
        assert status.status_code == 200
        unlocked = set(status.json()["unlocked_features"])
        assert PremiumFeature.cv_builder.value in unlocked
        assert PremiumFeature.sop_builder.value in unlocked
        assert len(status.json()["entitlements"]) == 2

        # The older (CV/ATS) entitlement's own feature must still gate a
        # real request successfully, even though it is not the
        # most-recently-granted entitlement.
        create_cv = await client.post(
            "/api/v1/premium-documents", json={"kind": "cv_professional", "title": "My CV"}
        )
        assert create_cv.status_code == 201

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.applicant_background import ApplicantBackgroundEntry, BackgroundEntryCategory
from app.models.premium_billing import BillingInterval, Entitlement, EntitlementStatus, PremiumFeature, PremiumPlan
from app.services.ai_provider import AIGenerationResult


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

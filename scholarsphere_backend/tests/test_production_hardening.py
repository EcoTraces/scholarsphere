from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import ExternalOpportunity, ImportAuditLog
from app.models.external_opportunity import PublicationStatus, VerificationStatus
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.opportunity_import import import_opportunities
from app.services.parsing import sanitize_html


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


def user(role: str) -> AuthenticatedUser:
    return AuthenticatedUser(
        uid=f"{role}-user",
        email=f"{role}@example.test",
        email_verified=True,
        role=role,
        permissions=frozenset(),
    )


def override_dependencies(session: AsyncSession, role: str) -> None:
    async def current_user() -> AuthenticatedUser:
        return user(role)

    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database


def opportunity() -> NormalizedExternalOpportunity:
    return NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id="secure-1",
        title="Secure Grant",
        opportunity_type="grant",
        provider_name="Official Agency",
        opportunity_status="posted",
        description="<p>Safe</p>",
        raw_payload={"id": "secure-1"},
    )


def test_external_endpoints_must_use_https_and_secrets_are_masked() -> None:
    with pytest.raises(ValidationError):
        Settings(grants_gov_base_url="http://insecure.example.test")
    settings = Settings(simpler_grants_api_key="private-provider-key")
    assert "private-provider-key" not in repr(settings)
    assert settings.simpler_grants_api_key.get_secret_value() == "private-provider-key"


def test_production_always_checks_token_revocation_even_if_disabled() -> None:
    settings = Settings(app_env="production", firebase_check_revoked=False)
    assert settings.firebase_check_revoked is True


def test_non_production_can_still_disable_revocation_checking() -> None:
    settings = Settings(app_env="development", firebase_check_revoked=False)
    assert settings.firebase_check_revoked is False


def test_html_sanitization_removes_all_executable_content() -> None:
    cleaned = sanitize_html(
        '<p onclick="steal()" style="color:red">Hello</p>'
        '<a href="javascript:steal()" onmouseover="steal()">bad</a>'
        '<a href="https://example.test">safe</a>'
        '<script>steal()</script><style>body{display:none}</style>'
        '<iframe src="https://evil.test"></iframe>'
        '<object data="https://evil.test"></object>'
        '<form action="https://evil.test"><input></form>'
    )
    assert cleaned is not None
    for unsafe in (
        "onclick",
        "onmouseover",
        "javascript:",
        "script",
        "style",
        "iframe",
        "object",
        "form",
        "steal",
    ):
        assert unsafe not in cleaned.lower()
    assert 'href="https://example.test"' in cleaned
    assert "nofollow" in cleaned
    assert "noopener" in cleaned
    assert "noreferrer" in cleaned


def test_error_envelope_and_correlation_header_are_consistent() -> None:
    response = TestClient(app).get(
        "/route-that-does-not-exist",
        headers={"X-Correlation-ID": "hardening-test-1"},
    )
    assert response.status_code == 404
    assert response.headers["X-Correlation-ID"] == "hardening-test-1"
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Not Found",
            "correlation_id": "hardening-test-1",
        }
    }


def test_invalid_correlation_id_is_replaced() -> None:
    response = TestClient(app).get(
        "/route-that-does-not-exist",
        headers={"X-Correlation-ID": "bad correlation/id"},
    )
    assert response.status_code == 404
    assert response.headers["X-Correlation-ID"] != "bad correlation/id"


def test_oversized_request_is_rejected_before_body_processing() -> None:
    response = TestClient(app).post(
        "/api/v1/external-opportunities/grants-gov/import",
        headers={"Content-Length": "1048577"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


@pytest.mark.asyncio
async def test_import_requires_approval_then_explicit_publication_and_audits(
    session: AsyncSession,
) -> None:
    await import_opportunities(
        session,
        [opportunity()],
        source_code="grants_gov",
        actor_id="verificationOfficer-user",
    )
    imported = await session.scalar(select(ExternalOpportunity))
    assert imported.verification_status == VerificationStatus.pending
    assert imported.publication_status == PublicationStatus.unpublished
    imported_id = imported.id
    await session.commit()

    override_dependencies(session, "administrator")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            early_publish = await client.post(
                f"/api/v1/external-opportunities/opportunities/{imported_id}/publication",
                json={"published": True},
            )
            approval = await client.post(
                f"/api/v1/external-opportunities/opportunities/{imported_id}/verification",
                json={
                    "decision": "approved",
                    "notes": "Official source and application confirmed.",
                    "source_checked": True,
                    "application_link_checked": True,
                    "deadline_checked": True,
                    "duplicate_checked": True,
                },
            )
            publication = await client.post(
                f"/api/v1/external-opportunities/opportunities/{imported_id}/publication",
                json={"published": True},
            )
    finally:
        app.dependency_overrides.clear()

    assert early_publish.status_code == 409
    assert early_publish.json()["error"]["code"] == "conflict"
    assert approval.status_code == 200
    assert approval.json()["verification_status"] == "verified"
    assert approval.json()["publication_status"] == "unpublished"
    assert publication.status_code == 200
    assert publication.json()["publication_status"] == "published"
    actions = set((await session.scalars(select(ImportAuditLog.action))).all())
    assert "verification_approved" in actions
    assert "opportunity_published" in actions


@pytest.mark.asyncio
async def test_rejection_never_publishes_and_source_state_is_audited(
    session: AsyncSession,
) -> None:
    await import_opportunities(
        session,
        [opportunity()],
        source_code="grants_gov",
        actor_id="verificationOfficer-user",
    )
    imported = await session.scalar(select(ExternalOpportunity))
    await session.commit()
    override_dependencies(session, "administrator")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            rejection = await client.post(
                f"/api/v1/external-opportunities/opportunities/{imported.id}/verification",
                json={
                    "decision": "rejected",
                    "notes": "Official source could not be confirmed.",
                    "source_checked": False,
                    "application_link_checked": False,
                    "deadline_checked": False,
                    "duplicate_checked": True,
                },
            )
            source_state = await client.patch(
                "/api/v1/external-opportunities/sources/grants-gov",
                json={"is_active": False},
            )
    finally:
        app.dependency_overrides.clear()
    assert rejection.status_code == 200
    assert rejection.json()["verification_status"] == "rejected"
    assert rejection.json()["publication_status"] == "unpublished"
    assert source_state.status_code == 200
    assert source_state.json()["is_active"] is False
    actions = set((await session.scalars(select(ImportAuditLog.action))).all())
    assert "verification_rejected" in actions
    assert "source_deactivated" in actions

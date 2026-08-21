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
    app.dependency_overrides.clear()


def user(role: str, uid: str | None = None) -> AuthenticatedUser:
    return AuthenticatedUser(
        uid=uid or f"{role}-user",
        email=f"{uid or role}@example.test",
        email_verified=True,
        role=role,
        permissions=frozenset(),
    )


def overrides(session: AsyncSession, role: str, uid: str | None = None) -> None:
    async def current_user() -> AuthenticatedUser:
        return user(role, uid)

    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database


def _payload(**overrides_kwargs: object) -> dict:
    payload = {
        "platform_name": "ScholarSphere",
        "logo_location": "assets/branding/logo.png",
        "brand_primary_color": "#007C72",
        "email_sender_name": "ScholarSphere",
        "email_sender_address": "no-reply@scholarsphere.example",
        "verification_expiration_days": 90,
        "supported_countries": ["Global"],
        "supported_languages": ["en"],
        "opportunity_categories": ["scholarship"],
        "document_types": ["passport"],
        "maximum_file_size_bytes": 1024 * 1024,
        "applicant_registration_enabled": True,
        "provider_registration_enabled": True,
        "maintenance_mode": False,
        "feature_flags": {"providerSelfPublication": False},
        "environment": {"name": "test"},
        "security_policy": {"mfaForAdministrators": True},
        "recommendation_settings": {},
        "fraud_rule_settings": {},
        "integration_settings": {},
        "notification_settings": {},
        "reason": "Test update",
    }
    payload.update(overrides_kwargs)
    return payload


@pytest.mark.asyncio
async def test_current_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/system-configuration/current")
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_current_requires_administrator_role(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/system-configuration/current")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_current_returns_seeded_defaults(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/system-configuration/current")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["version"] == 1
        assert body["platform_name"] == "ScholarSphere"
        assert body["updated_by"] == "system"


@pytest.mark.asyncio
async def test_update_creates_new_version_and_history(session: AsyncSession) -> None:
    overrides(session, "administrator", uid="config-admin")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        updated = await client.put(
            "/api/v1/system-configuration", json=_payload(platform_name="NewName")
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["version"] == 2
        assert updated.json()["updated_by"] == "config-admin"
        await session.commit()

        history = await client.get("/api/v1/system-configuration/history")
        versions = [item["version"] for item in history.json()]
        assert versions == [2, 1]


@pytest.mark.asyncio
async def test_update_rejects_provider_publication_without_mfa(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.put(
            "/api/v1/system-configuration",
            json=_payload(
                feature_flags={"providerSelfPublication": True},
                security_policy={"mfaForAdministrators": False},
            ),
        )
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_rejects_unknown_feature_flag(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.put(
            "/api/v1/system-configuration",
            json=_payload(feature_flags={"notARealFlag": True}),
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_rollback_creates_new_version_from_target(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.put("/api/v1/system-configuration", json=_payload(platform_name="V2"))
        await session.commit()

        missing = await client.post(
            "/api/v1/system-configuration/rollback",
            json={"target_version": 99, "reason": "test"},
        )
        assert missing.status_code == 404
        await session.commit()

        rolled_back = await client.post(
            "/api/v1/system-configuration/rollback",
            json={"target_version": 1, "reason": "revert"},
        )
        assert rolled_back.status_code == 200, rolled_back.text
        assert rolled_back.json()["version"] == 3
        assert rolled_back.json()["platform_name"] == "ScholarSphere"
        assert "Rollback: revert" in rolled_back.json()["change_reason"]

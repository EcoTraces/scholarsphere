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


@pytest.mark.asyncio
async def test_experience_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/experience/preferences")
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_get_preferences_returns_defaults_before_save(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="exp-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/experience/preferences")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["language"] == "english"
        assert body["text_scale"] == 1.0
        assert body["cache_saved_opportunities"] is True


@pytest.mark.asyncio
async def test_save_preferences_round_trips(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="exp-b")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.put(
            "/api/v1/experience/preferences",
            json={
                "language": "arabic",
                "timezone": "Africa/Cairo",
                "currency_code": "EGP",
                "country_code": "EG",
                "text_scale": 1.5,
                "high_contrast": True,
                "screen_reader_optimized": True,
                "keyboard_navigation": True,
                "low_bandwidth_mode": True,
                "compress_images": True,
                "data_saving": True,
                "cache_saved_opportunities": False,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["language"] == "arabic"
        await session.commit()

        fetched = await client.get("/api/v1/experience/preferences")
        assert fetched.json()["timezone"] == "Africa/Cairo"
        assert fetched.json()["cache_saved_opportunities"] is False


@pytest.mark.asyncio
async def test_save_preferences_rejects_out_of_range_text_scale(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="exp-c")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.put(
            "/api/v1/experience/preferences",
            json={"text_scale": 3.0},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_preferences_are_scoped_to_caller(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="exp-owner")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.put(
            "/api/v1/experience/preferences", json={"currency_code": "GBP"}
        )
        await session.commit()

    overrides(session, "applicant", uid="exp-other")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        other = await client.get("/api/v1/experience/preferences")
        assert other.json()["currency_code"] == "USD"


@pytest.mark.asyncio
async def test_save_translation_requires_staff(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        forbidden = await client.put(
            "/api/v1/experience/translations/french/welcome",
            json={"value": "Bienvenue"},
        )
        assert forbidden.status_code == 403

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        allowed = await client.put(
            "/api/v1/experience/translations/french/welcome",
            json={"value": "Bienvenue"},
        )
        assert allowed.status_code == 200
        assert allowed.json()["value"] == "Bienvenue"


@pytest.mark.asyncio
async def test_translate_falls_back_to_key_or_provided_fallback(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.put(
            "/api/v1/experience/translations/spanish/hello", json={"value": "Hola"}
        )
        await session.commit()

        found = await client.get("/api/v1/experience/translations/spanish/hello")
        assert found.json()["value"] == "Hola"

        missing_no_fallback = await client.get(
            "/api/v1/experience/translations/spanish/missing-key"
        )
        assert missing_no_fallback.json()["value"] == "missing-key"

        missing_with_fallback = await client.get(
            "/api/v1/experience/translations/spanish/missing-key",
            params={"fallback": "Default text"},
        )
        assert missing_with_fallback.json()["value"] == "Default text"

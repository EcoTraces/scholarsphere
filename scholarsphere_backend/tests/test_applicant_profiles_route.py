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
async def test_get_before_save_is_404(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="profile-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/applicant-profiles/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_save_and_round_trip(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="profile-b")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            saved = await client.put(
                "/api/v1/applicant-profiles/me",
                json={
                    "full_name": "Ada Lovelace",
                    "nationality": "British",
                    "country_of_residence": "United Kingdom",
                    "date_of_birth": "1990-01-01",
                    "gender": "female",
                    "highest_qualification": "Master's",
                    "degree_field": "Computer Science",
                    "academic_classification": "Distinction",
                    "graduation_year": 2020,
                    "work_experience_years": 4.5,
                    "preferred_study_levels": ["PhD"],
                    "preferred_countries": ["Canada", "Germany"],
                    "areas_of_interest": ["AI"],
                    "english_test_status": "completed",
                    "passport_status": "valid",
                    "employment_status": "employed",
                    "funding_preferences": ["fullyFunded"],
                    "special_eligibility_categories": [],
                },
            )
            fetched = await client.get("/api/v1/applicant-profiles/me")
    finally:
        app.dependency_overrides.clear()

    assert saved.status_code == 200
    for body in (saved.json(), fetched.json()):
        assert body["full_name"] == "Ada Lovelace"
        assert body["preferred_countries"] == ["Canada", "Germany"]
        assert body["english_test_status"] == "completed"
        assert body["passport_status"] == "valid"
        assert body["employment_status"] == "employed"
        assert body["work_experience_years"] == 4.5
        assert body["user_id"] == "profile-b"


@pytest.mark.asyncio
async def test_save_is_scoped_to_caller_not_client_supplied_user(
    session: AsyncSession,
) -> None:
    """A client can't overwrite another user's profile even by trying to."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="profile-c")
        await client.put(
            "/api/v1/applicant-profiles/me",
            json={"full_name": "User C"},
        )

        overrides(session, "applicant", uid="profile-d")
        await client.put(
            "/api/v1/applicant-profiles/me",
            json={"full_name": "User D"},
        )

        overrides(session, "applicant", uid="profile-c")
        c_profile = await client.get("/api/v1/applicant-profiles/me")
    app.dependency_overrides.clear()

    assert c_profile.json()["full_name"] == "User C"


@pytest.mark.asyncio
async def test_admin_listing_requires_staff_role(session: AsyncSession) -> None:
    overrides(session, "applicant")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/applicant-profiles/admin")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_listing_returns_all_profiles_paginated(session: AsyncSession) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="profile-e")
        await client.put("/api/v1/applicant-profiles/me", json={"full_name": "User E"})
        overrides(session, "applicant", uid="profile-f")
        await client.put("/api/v1/applicant-profiles/me", json={"full_name": "User F"})

        overrides(session, "administrator")
        full = await client.get("/api/v1/applicant-profiles/admin")
        paged = await client.get(
            "/api/v1/applicant-profiles/admin", params={"page_size": 1}
        )
    app.dependency_overrides.clear()

    assert full.json()["total"] == 2
    assert len(full.json()["items"]) == 2
    assert paged.json()["total"] == 2
    assert len(paged.json()["items"]) == 1


@pytest.mark.asyncio
async def test_invalid_enum_value_is_rejected(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="profile-g")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.put(
                "/api/v1/applicant-profiles/me",
                json={"full_name": "X", "passport_status": "not-a-real-status"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_applicant_profiles_require_authentication(session: AsyncSession) -> None:
    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = database
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/applicant-profiles/me")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401

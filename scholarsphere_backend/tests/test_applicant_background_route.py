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


@pytest.mark.asyncio
async def test_create_list_update_delete_entry(session: AsyncSession) -> None:
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/applicant-background",
            json={
                "category": "education",
                "title": "BSc Computer Science",
                "organization": "Fourah Bay College",
                "start_date": "2020-09-01",
                "end_date": "2024-06-01",
                "is_current": False,
                "description": "First class honours.",
                "details": {},
            },
        )
        assert create.status_code == 201
        entry_id = create.json()["id"]
        assert create.json()["title"] == "BSc Computer Science"

        listing = await client.get("/api/v1/applicant-background")
        assert listing.status_code == 200
        assert len(listing.json()) == 1

        update = await client.patch(
            f"/api/v1/applicant-background/{entry_id}", json={"title": "BSc Computer Science (Hons)"}
        )
        assert update.status_code == 200
        assert update.json()["title"] == "BSc Computer Science (Hons)"

        delete = await client.delete(f"/api/v1/applicant-background/{entry_id}")
        assert delete.status_code == 204

        listing_after = await client.get("/api/v1/applicant-background")
        assert listing_after.json() == []


@pytest.mark.asyncio
async def test_cannot_access_another_users_entry(session: AsyncSession) -> None:
    overrides(session, uid="applicant-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/api/v1/applicant-background",
            json={"category": "skill", "title": "Python", "organization": "", "description": "", "details": {}},
        )
        entry_id = create.json()["id"]

    overrides(session, uid="applicant-2")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/applicant-background/{entry_id}", json={"title": "Not yours"}
        )
        assert response.status_code == 404

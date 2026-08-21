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


async def _save(
    client: AsyncClient,
    *,
    term_id: str,
    canonical_name: str,
    synonyms: list[str] | None = None,
    taxonomy_type: str = "academicField",
    code: str | None = None,
) -> dict:
    response = await client.post(
        "/api/v1/taxonomy/terms",
        json={
            "id": term_id,
            "type": taxonomy_type,
            "canonical_name": canonical_name,
            "code": code,
            "synonyms": synonyms or [],
            "parent_id": None,
            "active": True,
            "reason": "Initial entry.",
        },
    )
    return response


@pytest.mark.asyncio
async def test_taxonomy_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/taxonomy/terms", params={"type": "country"})
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_save_creates_term_and_records_version(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await _save(
            client,
            term_id="field-cs",
            canonical_name="Computer Science",
            synonyms=["Computing"],
            code="CS",
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["version"] == 1

        versions = await client.get("/api/v1/taxonomy/versions")
        assert len(versions.json()) == 1
        assert versions.json()[0]["term_count"] == 1


@pytest.mark.asyncio
async def test_save_rejects_synonym_collision(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _save(
            client, term_id="field-cs", canonical_name="Computer Science", synonyms=["Computing"]
        )
        collision = await _save(client, term_id="field-computing", canonical_name="Computing")
        assert collision.status_code == 409


@pytest.mark.asyncio
async def test_resolve_matches_synonym_and_code_case_insensitively(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _save(
            client,
            term_id="field-cs",
            canonical_name="Computer Science",
            synonyms=["Computing"],
            code="CS",
        )
        by_synonym = await client.get(
            "/api/v1/taxonomy/terms/resolve",
            params={"type": "academicField", "value": "COMPUTING"},
        )
        assert by_synonym.json()["id"] == "field-cs"

        by_code = await client.get(
            "/api/v1/taxonomy/terms/resolve",
            params={"type": "academicField", "value": "cs"},
        )
        assert by_code.json()["id"] == "field-cs"

        no_match = await client.get(
            "/api/v1/taxonomy/terms/resolve",
            params={"type": "academicField", "value": "Physics"},
        )
        assert no_match.json() is None


@pytest.mark.asyncio
async def test_list_filters_by_type_and_active_only(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _save(client, term_id="field-cs", canonical_name="Computer Science")
        await _save(client, term_id="country-ca", canonical_name="Canada", taxonomy_type="country")

        fields = await client.get("/api/v1/taxonomy/terms", params={"type": "academicField"})
        assert [item["id"] for item in fields.json()] == ["field-cs"]


@pytest.mark.asyncio
async def test_duplicate_candidates_groups_overlapping_terms(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # A synonym-only overlap ("CompSci" on both) passes save()'s
        # collision check (which only compares the *new* term's canonical
        # name against others), but the grouping algorithm compares full
        # token sets, so it still surfaces as a duplicate candidate pair.
        await _save(
            client, term_id="field-cs", canonical_name="Computer Science", synonyms=["CompSci"]
        )
        await _save(
            client, term_id="field-cs-2", canonical_name="Informatics", synonyms=["CompSci"]
        )
        await _save(client, term_id="field-physics", canonical_name="Physics")

        response = await client.get(
            "/api/v1/taxonomy/terms/duplicates", params={"type": "academicField"}
        )
        groups = response.json()
        assert len(groups) == 1
        assert {item["id"] for item in groups[0]} == {"field-cs", "field-cs-2"}


@pytest.mark.asyncio
async def test_merge_combines_synonyms_and_deactivates_duplicates(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _save(client, term_id="field-cs", canonical_name="Computer Science")
        await _save(client, term_id="field-cs-2", canonical_name="Computer Sciences")
        await session.commit()

        response = await client.post(
            "/api/v1/taxonomy/terms/merge",
            json={"canonical_id": "field-cs", "duplicate_ids": ["field-cs-2"]},
        )
        assert response.status_code == 200, response.text
        merged = response.json()
        assert "Computer Sciences" in merged["synonyms"]
        await session.commit()

        duplicate = await client.get(
            "/api/v1/taxonomy/terms", params={"type": "academicField", "active_only": False}
        )
        by_id = {item["id"]: item for item in duplicate.json()}
        assert by_id["field-cs-2"]["active"] is False


@pytest.mark.asyncio
async def test_merge_404_for_missing_canonical(session: AsyncSession) -> None:
    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/taxonomy/terms/merge",
            json={"canonical_id": "missing", "duplicate_ids": ["also-missing"]},
        )
        assert response.status_code == 404

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone

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


async def _create_plan(
    client: AsyncClient,
    *,
    opportunity_id: str = "opp-1",
    required_documents: list[str] | None = None,
    application_procedure: list[str] | None = None,
) -> dict:
    deadline = datetime.now(timezone.utc) + timedelta(days=60)
    response = await client.post(
        "/api/v1/guidance/plans",
        json={
            "opportunity_id": opportunity_id,
            "opportunity_title": "PhD Scholarship",
            "opportunity_deadline": deadline.isoformat(),
            "required_documents": required_documents
            if required_documents is not None
            else ["Passport", "Academic transcript"],
            "application_procedure": application_procedure
            if application_procedure is not None
            else ["Submit online form"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_guidance_requires_authentication(session: AsyncSession) -> None:
    overrides(session, "applicant")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        app.dependency_overrides.pop(get_current_user, None)
        response = await client.get("/api/v1/guidance/plans/opp-1")
        assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_create_plan_marks_missing_documents_and_profile(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="g-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        plan = await _create_plan(client)
        assert plan["id"] == "g-a-opp-1"
        doc_items = [item for item in plan["items"] if item["type"] == "requiredDocument"]
        assert all(item["status"] == "missing" for item in doc_items)
        profile_items = [
            item for item in plan["items"] if item["type"] == "profileInformation"
        ]
        assert {item["title"] for item in profile_items} == {
            "Nationality",
            "Highest qualification",
            "Academic field",
        }
        cv_item = next(item for item in plan["items"] if item["id"] == "cv")
        assert cv_item["required"] is False


@pytest.mark.asyncio
async def test_create_plan_uses_real_profile_and_documents(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="g-b")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        profile_response = await client.put(
            "/api/v1/applicant-profiles/me",
            json={
                "full_name": "Jordan Smith",
                "nationality": "Kenyan",
                "country_of_residence": "Kenya",
                "date_of_birth": None,
                "gender": "",
                "highest_qualification": "Bachelor's",
                "degree_field": "Computer Science",
                "academic_classification": "",
                "graduation_year": None,
                "work_experience_years": 0,
                "preferred_study_levels": [],
                "preferred_countries": [],
                "areas_of_interest": [],
                "english_test_status": "notTaken",
                "passport_status": "unavailable",
                "employment_status": "student",
                "funding_preferences": [],
                "special_eligibility_categories": [],
            },
        )
        assert profile_response.status_code == 200, profile_response.text
        await session.commit()

        plan = await _create_plan(client, required_documents=["Passport"])
        profile_items = [
            item for item in plan["items"] if item["type"] == "profileInformation"
        ]
        assert profile_items == []


@pytest.mark.asyncio
async def test_get_plan_scoped_to_caller(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="g-c")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _create_plan(client)
        await session.commit()

    overrides(session, "applicant", uid="g-other")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        missing = await client.get("/api/v1/guidance/plans/opp-1")
        assert missing.json() is None
        await session.commit()

        update = await client.post(
            "/api/v1/guidance/plans/g-c-opp-1/items/cv",
            json={"status": "ready"},
        )
        assert update.status_code == 404


@pytest.mark.asyncio
async def test_update_item_status(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="g-d")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        plan = await _create_plan(client)
        response = await client.post(
            f"/api/v1/guidance/plans/{plan['id']}/items/cv",
            json={"status": "ready"},
        )
        assert response.status_code == 200
        cv_item = next(item for item in response.json()["items"] if item["id"] == "cv")
        assert cv_item["status"] == "ready"


@pytest.mark.asyncio
async def test_track_recommendation_letter(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="g-e")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        plan = await _create_plan(client)
        now = datetime.now(timezone.utc)
        response = await client.post(
            f"/api/v1/guidance/plans/{plan['id']}/recommendation-letters",
            json={
                "id": "letter-1",
                "referee_name": "Dr. Lee",
                "referee_email": "lee@example.test",
                "requested_at": now.isoformat(),
                "due_at": (now + timedelta(days=14)).isoformat(),
                "received": False,
                "received_at": None,
            },
        )
        assert response.status_code == 200
        assert len(response.json()["recommendation_letters"]) == 1


@pytest.mark.asyncio
async def test_confirm_submission_requires_reference_and_portal(
    session: AsyncSession,
) -> None:
    overrides(session, "applicant", uid="g-f")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        plan = await _create_plan(client)
        now = datetime.now(timezone.utc)
        rejected = await client.post(
            f"/api/v1/guidance/plans/{plan['id']}/submission",
            json={
                "confirmed_at": now.isoformat(),
                "application_reference": "",
                "confirmed_by_user_id": "g-f",
                "official_portal": "",
            },
        )
        assert rejected.status_code == 422

        confirmed = await client.post(
            f"/api/v1/guidance/plans/{plan['id']}/submission",
            json={
                "confirmed_at": now.isoformat(),
                "application_reference": "REF-123",
                "confirmed_by_user_id": "g-f",
                "official_portal": "https://apply.example.edu",
            },
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["submission_confirmation"]["application_reference"] == "REF-123"


@pytest.mark.asyncio
async def test_create_plan_is_idempotent_upsert(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="g-g")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await _create_plan(client)
        await session.commit()
        second = await _create_plan(client)
        assert second["id"] == "g-g-opp-1"

        listed = await client.get("/api/v1/guidance/plans/opp-1")
        assert listed.status_code == 200

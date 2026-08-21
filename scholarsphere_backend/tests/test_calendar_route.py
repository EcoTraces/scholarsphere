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
    # Every test in this file ends by leaving app.dependency_overrides
    # pointing at this fixture's session; without clearing it here, the
    # last test's override survives into whichever test file pytest
    # collects next and points get_db at an already-disposed engine.
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


def _iso(value: datetime) -> str:
    return value.isoformat()


async def _save(
    client: AsyncClient,
    *,
    event_id: str,
    starts_at: datetime,
    hours: int = 1,
    event_type: str = "opportunityDeadline",
) -> dict:
    ends_at = starts_at + timedelta(hours=hours)
    response = await client.post(
        "/api/v1/calendar/events",
        json={
            "id": event_id,
            "title": "Deadline",
            "description": "Official opportunity deadline",
            "type": event_type,
            "starts_at": _iso(starts_at),
            "ends_at": _iso(ends_at),
            "timezone": "UTC",
            "reminder_minutes": [1440, 60],
            "deadline_state": "upcoming",
            "related_entity_id": "opp-1",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_calendar_requires_authentication() -> None:
    # Deliberately does not call overrides(): leaving app.dependency_overrides
    # untouched (and clearing it afterwards) lets the real get_current_user
    # dependency run and reject before get_db is ever reached, so no stale
    # database override leaks into later test files.
    app.dependency_overrides.clear()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/calendar/events")
            assert response.status_code in (401, 403, 422)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_save_computes_closing_soon_and_is_idempotent(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="cal-a")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        soon = datetime.now(timezone.utc) + timedelta(days=5)
        body = await _save(client, event_id="cal-a-deadline-opp-1", starts_at=soon)
        assert body["deadline_state"] == "closingSoon"

        events = await client.get("/api/v1/calendar/events")
        assert len(events.json()) == 1
        await session.commit()

        # Re-saving the same id (as the screen does on every load) upserts
        # rather than duplicating.
        await _save(client, event_id="cal-a-deadline-opp-1", starts_at=soon)
        events_again = await client.get("/api/v1/calendar/events")
        assert len(events_again.json()) == 1


@pytest.mark.asyncio
async def test_save_rejects_end_before_start(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="cal-b")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        now = datetime.now(timezone.utc)
        response = await client.post(
            "/api/v1/calendar/events",
            json={
                "id": "bad-event",
                "title": "Bad",
                "description": "",
                "type": "application",
                "starts_at": _iso(now),
                "ends_at": _iso(now - timedelta(hours=1)),
                "timezone": "UTC",
                "reminder_minutes": [],
                "deadline_state": "upcoming",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_events_are_scoped_to_caller(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="cal-owner")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        far_future = datetime.now(timezone.utc) + timedelta(days=100)
        await _save(client, event_id="owner-event", starts_at=far_future)

    overrides(session, "applicant", uid="cal-other")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        events = await client.get("/api/v1/calendar/events")
        assert events.json() == []
        await session.commit()

        update = await client.post(
            "/api/v1/calendar/events/owner-event/deadline",
            json={"new_deadline": _iso(far_future + timedelta(days=1))},
        )
        assert update.status_code == 404


@pytest.mark.asyncio
async def test_update_deadline_marks_extended_or_changed(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="cal-c")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        far_future = datetime.now(timezone.utc) + timedelta(days=100)
        await _save(client, event_id="cal-c-event", starts_at=far_future)

        extended = await client.post(
            "/api/v1/calendar/events/cal-c-event/deadline",
            json={"new_deadline": _iso(far_future + timedelta(days=10))},
        )
        assert extended.json()["deadline_state"] == "extended"
        assert extended.json()["previous_starts_at"] is not None

        earlier = await client.post(
            "/api/v1/calendar/events/cal-c-event/deadline",
            json={"new_deadline": _iso(far_future - timedelta(days=1))},
        )
        assert earlier.json()["deadline_state"] == "changed"


@pytest.mark.asyncio
async def test_conflicts_detects_overlap(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="cal-d")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        base = datetime.now(timezone.utc) + timedelta(days=30)
        await _save(client, event_id="cal-d-1", starts_at=base, hours=3)
        await _save(client, event_id="cal-d-2", starts_at=base + timedelta(hours=1), hours=1)

        conflicts = await client.get("/api/v1/calendar/conflicts")
        assert len(conflicts.json()) == 1
        assert conflicts.json()[0]["overlap_seconds"] == 3600


@pytest.mark.asyncio
async def test_export_ics_contains_events(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="cal-e")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        base = datetime.now(timezone.utc) + timedelta(days=30)
        await _save(client, event_id="cal-e-1", starts_at=base)

        export = await client.get("/api/v1/calendar/export.ics")
        assert export.status_code == 200
        content = export.json()["content"]
        assert content.startswith("BEGIN:VCALENDAR")
        assert "SUMMARY:Deadline" in content
        assert content.count("BEGIN:VEVENT") == 1


@pytest.mark.asyncio
async def test_mark_synchronized_sets_external_id(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="cal-f")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        base = datetime.now(timezone.utc) + timedelta(days=30)
        await _save(client, event_id="cal-f-1", starts_at=base)

        response = await client.post(
            "/api/v1/calendar/events/cal-f-1/sync",
            json={"provider": "google", "external_id": "abc123"},
        )
        assert response.json()["external_calendar_id"] == "google:abc123"


@pytest.mark.asyncio
async def test_administrative_deadlines_requires_staff(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="cal-g")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        base = datetime.now(timezone.utc) + timedelta(days=30)
        await _save(client, event_id="cal-g-1", starts_at=base)

        forbidden = await client.get("/api/v1/calendar/administrative-deadlines")
        assert forbidden.status_code == 403

    overrides(session, "administrator")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        allowed = await client.get("/api/v1/calendar/administrative-deadlines")
        assert allowed.status_code == 200
        assert len(allowed.json()) == 1

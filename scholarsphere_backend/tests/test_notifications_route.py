from collections.abc import AsyncIterator
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import ExternalOpportunity
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.opportunity_import import import_opportunities
from app.services.source_registry import seed_opportunity_sources


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
        async with database_session.begin():
            await seed_opportunity_sources(database_session)
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


async def _publish_opportunity(
    session: AsyncSession, *, deadline: date, external_id: str
) -> str:
    record = NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id=external_id,
        title="Education Innovation Grant",
        opportunity_type="grant",
        provider_name="Department of Education",
        country="United States",
        deadline=deadline,
        opportunity_status="posted",
        official_source_url=f"https://example.test/{external_id}",
        official_application_url=f"https://example.test/{external_id}/apply",
        raw_payload={
            "id": external_id,
            "title": "Education Innovation Grant",
            "agencyName": "Department of Education",
            "openDate": "07/01/2026",
            "closeDate": deadline.isoformat(),
            "oppStatus": "posted",
        },
    )
    statistics = await import_opportunities(
        session, [record], source_code="grants_gov", actor_id="officer-1"
    )
    assert statistics.records_created == 1
    from sqlalchemy import select

    opportunity = await session.scalar(
        select(ExternalOpportunity).where(ExternalOpportunity.external_id == external_id)
    )
    opportunity_id = str(opportunity.id)
    await session.commit()

    overrides(session, "administrator")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        verify = await client.post(
            f"/api/v1/external-opportunities/opportunities/{opportunity_id}/verification",
            json={
                "decision": "approved",
                "notes": "Official source confirmed.",
                "source_checked": True,
                "application_link_checked": True,
                "deadline_checked": True,
                "duplicate_checked": True,
            },
        )
        assert verify.status_code == 200
        publish = await client.post(
            f"/api/v1/external-opportunities/opportunities/{opportunity_id}/publication",
            json={"published": True},
        )
        assert publish.status_code == 200
    app.dependency_overrides.clear()
    return opportunity_id


@pytest.mark.asyncio
async def test_preferences_default_before_save(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="user-a")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/notifications/preferences")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["channels"] == ["inApp", "email", "push"]
    assert body["frequency"] == "immediate"
    assert body["reminder_days"] == [30, 14, 7, 3, 1]
    assert body["daily_limit"] == 10


@pytest.mark.asyncio
async def test_preferences_full_replace_round_trip(session: AsyncSession) -> None:
    overrides(session, "applicant", uid="user-b")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            saved = await client.put(
                "/api/v1/notifications/preferences",
                json={
                    "channels": ["email"],
                    "frequency": "dailyDigest",
                    "reminder_days": [7, 1],
                    "matching_opportunities": False,
                    "opportunity_changes": False,
                    "verification_updates": False,
                    "saved_opportunity_expiry": False,
                    "quiet_hours_start": 22,
                    "quiet_hours_end": 6,
                    "timezone": "America/New_York",
                    "daily_limit": 3,
                    "group_notifications": False,
                    "unsubscribed_types": ["providerAnnouncement"],
                },
            )
            fetched = await client.get("/api/v1/notifications/preferences")
    finally:
        app.dependency_overrides.clear()

    assert saved.status_code == 200
    for body in (saved.json(), fetched.json()):
        assert body["channels"] == ["email"]
        assert body["frequency"] == "dailyDigest"
        assert body["reminder_days"] == [7, 1]
        assert body["quiet_hours_start"] == 22
        assert body["daily_limit"] == 3
        assert body["unsubscribed_types"] == ["providerAnnouncement"]


@pytest.mark.asyncio
async def test_schedule_deadline_reminders_is_idempotent(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=10), external_id="notif-1"
    )
    overrides(session, "applicant", uid="user-c")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await client.post(
                "/api/v1/notifications/deadline-reminders",
                json={"opportunity_ids": [opportunity_id]},
            )
            second = await client.post(
                "/api/v1/notifications/deadline-reminders",
                json={"opportunity_ids": [opportunity_id]},
            )
            listing = await client.get("/api/v1/notifications")
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 204
    assert second.status_code == 204
    reminders = [n for n in listing.json() if n["type"] == "deadlineReminder"]
    # Default reminder_days = {30,14,7,3,1}; only offsets before the 10-day
    # deadline are meaningful, but the demo schedules all configured days
    # regardless (the reminder simply lands in the past) - assert exactly
    # one row per configured day, not duplicated by the second POST.
    assert len(reminders) == 5


@pytest.mark.asyncio
async def test_schedule_deadline_reminders_respects_disabled_frequency(
    session: AsyncSession,
) -> None:
    opportunity_id = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=10), external_id="notif-2"
    )
    overrides(session, "applicant", uid="user-d")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.put(
                "/api/v1/notifications/preferences",
                json={"frequency": "disabled"},
            )
            await client.post(
                "/api/v1/notifications/deadline-reminders",
                json={"opportunity_ids": [opportunity_id]},
            )
            listing = await client.get("/api/v1/notifications")
    finally:
        app.dependency_overrides.clear()

    assert listing.json() == []


@pytest.mark.asyncio
async def test_schedule_deadline_reminders_skips_unpublished_and_past_deadline(
    session: AsyncSession,
) -> None:
    unpublished_id = await _import_only(session, external_id="notif-3")
    past_id = await _publish_opportunity(
        session, deadline=date.today() - timedelta(days=1), external_id="notif-4"
    )
    overrides(session, "applicant", uid="user-e")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/notifications/deadline-reminders",
                json={"opportunity_ids": [unpublished_id, past_id, "00000000-0000-4000-8000-000000000000"]},
            )
            listing = await client.get("/api/v1/notifications")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert listing.json() == []


async def _import_only(session: AsyncSession, *, external_id: str) -> str:
    from sqlalchemy import select

    record = NormalizedExternalOpportunity(
        source_code="grants_gov",
        external_id=external_id,
        title="Unpublished Grant",
        opportunity_type="grant",
        provider_name="Department of Education",
        country="United States",
        deadline=date.today() + timedelta(days=10),
        opportunity_status="posted",
        official_source_url=f"https://example.test/{external_id}",
        official_application_url=f"https://example.test/{external_id}/apply",
        raw_payload={
            "id": external_id,
            "title": "Unpublished Grant",
            "agencyName": "Department of Education",
            "openDate": "07/01/2026",
            "closeDate": (date.today() + timedelta(days=10)).isoformat(),
            "oppStatus": "posted",
        },
    )
    await import_opportunities(session, [record], source_code="grants_gov", actor_id="officer-1")
    opportunity = await session.scalar(
        select(ExternalOpportunity).where(ExternalOpportunity.external_id == external_id)
    )
    opportunity_id = str(opportunity.id)
    await session.commit()
    return opportunity_id


@pytest.mark.asyncio
async def test_cross_user_read_and_cancel_are_404(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=10), external_id="notif-5"
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant", uid="user-f")
        await client.post(
            "/api/v1/notifications/deadline-reminders",
            json={"opportunity_ids": [opportunity_id]},
        )
        own_listing = await client.get("/api/v1/notifications")
        notification_id = own_listing.json()[0]["id"]

        overrides(session, "applicant", uid="user-g")
        read_response = await client.post(f"/api/v1/notifications/{notification_id}/read")
        cancel_response = await client.post(f"/api/v1/notifications/{notification_id}/cancel")
    app.dependency_overrides.clear()

    assert read_response.status_code == 404
    assert cancel_response.status_code == 404


@pytest.mark.asyncio
async def test_mark_read_updates_status(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=10), external_id="notif-6"
    )
    overrides(session, "applicant", uid="user-h")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post(
                "/api/v1/notifications/deadline-reminders",
                json={"opportunity_ids": [opportunity_id]},
            )
            listing = await client.get("/api/v1/notifications")
            notification_id = listing.json()[0]["id"]
            marked = await client.post(f"/api/v1/notifications/{notification_id}/read")
    finally:
        app.dependency_overrides.clear()

    assert marked.status_code == 200
    body = marked.json()
    assert body["status"] == "read"
    assert body["read_at"] is not None


@pytest.mark.asyncio
async def test_record_opportunity_event_requires_staff(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=10), external_id="notif-7"
    )
    overrides(session, "applicant", uid="user-i")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/notifications/events",
                json={
                    "user_id": "user-i",
                    "opportunity_id": opportunity_id,
                    "type": "opportunityVerified",
                    "message": "Your saved opportunity was verified.",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_record_opportunity_event_works_against_non_public_opportunity(
    session: AsyncSession,
) -> None:
    unpublished_id = await _import_only(session, external_id="notif-8")
    overrides(session, "administrator")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            created = await client.post(
                "/api/v1/notifications/events",
                json={
                    "user_id": "user-j",
                    "opportunity_id": unpublished_id,
                    "type": "requirementsChanged",
                    "message": "Eligibility requirements were updated.",
                },
            )
    finally:
        app.dependency_overrides.clear()
    assert created.status_code == 204

    overrides(session, "applicant", uid="user-j")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            listing = await client.get("/api/v1/notifications")
    finally:
        app.dependency_overrides.clear()
    events = [n for n in listing.json() if n["type"] == "requirementsChanged"]
    assert len(events) == 1


@pytest.mark.asyncio
async def test_record_opportunity_event_nonexistent_opportunity_is_404(
    session: AsyncSession,
) -> None:
    overrides(session, "administrator")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/notifications/events",
                json={
                    "user_id": "user-k",
                    "opportunity_id": "00000000-0000-4000-8000-000000000000",
                    "type": "requirementsChanged",
                    "message": "test",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_record_opportunity_event_respects_daily_limit(session: AsyncSession) -> None:
    opportunity_id = await _publish_opportunity(
        session, deadline=date.today() + timedelta(days=10), external_id="notif-9"
    )
    overrides(session, "applicant", uid="user-l")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.put(
                "/api/v1/notifications/preferences", json={"daily_limit": 1}
            )
    finally:
        app.dependency_overrides.clear()

    overrides(session, "administrator")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            for _ in range(3):
                await client.post(
                    "/api/v1/notifications/events",
                    json={
                        "user_id": "user-l",
                        "opportunity_id": opportunity_id,
                        "type": "requirementsChanged",
                        "message": "Update.",
                    },
                )
    finally:
        app.dependency_overrides.clear()

    overrides(session, "applicant", uid="user-l")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            listing = await client.get("/api/v1/notifications")
    finally:
        app.dependency_overrides.clear()

    events = [n for n in listing.json() if n["type"] == "requirementsChanged"]
    assert len(events) == 1


@pytest.mark.asyncio
async def test_retry_failed_requires_staff(session: AsyncSession) -> None:
    overrides(session, "applicant")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/notifications/admin/retry-failed", json={}
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_retry_failed_service_function_bumps_or_expires(session: AsyncSession) -> None:
    from app.models.notification import NotificationDeliveryStatus, ScholarSphereNotification
    from app.services.notification_dispatch import retry_failed_notifications

    async with session.begin():
        session.add_all(
            [
                ScholarSphereNotification(
                    id="fail-1",
                    user_id="user-m",
                    type="deadline_reminder",
                    title="t",
                    message="m",
                    channels=["sms"],
                    scheduled_for=date.today(),
                    status=NotificationDeliveryStatus.failed,
                    retry_count=0,
                    timezone="UTC",
                ),
                ScholarSphereNotification(
                    id="fail-2",
                    user_id="user-m",
                    type="deadline_reminder",
                    title="t",
                    message="m",
                    channels=["sms"],
                    scheduled_for=date.today(),
                    status=NotificationDeliveryStatus.failed,
                    retry_count=3,
                    timezone="UTC",
                ),
            ]
        )
    await session.commit()

    result = await retry_failed_notifications(session, maximum_retries=3)
    await session.commit()

    assert result == {"retried": 1, "expired": 1}
    bumped = await session.get(ScholarSphereNotification, "fail-1")
    expired = await session.get(ScholarSphereNotification, "fail-2")
    assert bumped.status == NotificationDeliveryStatus.retrying
    assert bumped.retry_count == 1
    assert expired.status == NotificationDeliveryStatus.expired


@pytest.mark.asyncio
async def test_delivery_analytics_and_admin_listing_require_staff(
    session: AsyncSession,
) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        overrides(session, "applicant")
        analytics_denied = await client.get("/api/v1/notifications/admin/analytics")
        listing_denied = await client.get("/api/v1/notifications/admin")

        overrides(session, "administrator")
        analytics_ok = await client.get("/api/v1/notifications/admin/analytics")
        listing_ok = await client.get("/api/v1/notifications/admin")
    app.dependency_overrides.clear()

    assert analytics_denied.status_code == 403
    assert listing_denied.status_code == 403
    assert analytics_ok.status_code == 200
    assert listing_ok.status_code == 200
    assert "total" in analytics_ok.json()


@pytest.mark.asyncio
async def test_getforuser_flips_own_due_notifications_and_is_scoped(
    session: AsyncSession,
) -> None:
    from app.models.notification import NotificationDeliveryStatus, ScholarSphereNotification

    async with session.begin():
        session.add_all(
            [
                ScholarSphereNotification(
                    id="due-inapp",
                    user_id="user-n",
                    type="deadline_reminder",
                    title="t",
                    message="m",
                    channels=["in_app"],
                    scheduled_for=date.today() - timedelta(days=1),
                    status=NotificationDeliveryStatus.scheduled,
                    retry_count=0,
                    timezone="UTC",
                ),
                ScholarSphereNotification(
                    id="due-sms",
                    user_id="user-n",
                    type="deadline_reminder",
                    title="t",
                    message="m",
                    channels=["sms"],
                    scheduled_for=date.today() - timedelta(days=1),
                    status=NotificationDeliveryStatus.scheduled,
                    retry_count=0,
                    timezone="UTC",
                ),
                ScholarSphereNotification(
                    id="due-other-user",
                    user_id="user-o",
                    type="deadline_reminder",
                    title="t",
                    message="m",
                    channels=["in_app"],
                    scheduled_for=date.today() - timedelta(days=1),
                    status=NotificationDeliveryStatus.scheduled,
                    retry_count=0,
                    timezone="UTC",
                ),
            ]
        )
    await session.commit()

    overrides(session, "applicant", uid="user-n")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            listing = await client.get("/api/v1/notifications")
    finally:
        app.dependency_overrides.clear()

    by_id = {item["id"]: item for item in listing.json()}
    assert by_id["due-inapp"]["status"] == "delivered"
    assert by_id["due-sms"]["status"] == "failed"
    assert by_id["due-sms"]["failure_reason"] == "Delivery provider is not configured."

    other_user = await session.get(ScholarSphereNotification, "due-other-user")
    assert other_user.status == NotificationDeliveryStatus.scheduled


@pytest.mark.asyncio
async def test_notifications_require_authentication(session: AsyncSession) -> None:
    async def database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = database
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/notifications")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401

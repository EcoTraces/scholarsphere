from collections.abc import AsyncIterator
from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.notification import NotificationDeliveryStatus, ScholarSphereNotification
from app.services import notification_dispatch
from app.tasks.notifications import process_due_notifications, retry_failed_notifications


@pytest_asyncio.fixture
async def task_database(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(notification_dispatch, "AsyncSessionFactory", factory)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_process_due_notifications_task_is_global(
    task_database: async_sessionmaker[AsyncSession],
) -> None:
    async with task_database() as session:
        async with session.begin():
            session.add_all(
                [
                    ScholarSphereNotification(
                        id="global-a",
                        user_id="user-x",
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
                        id="global-b",
                        user_id="user-y",
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

    result = process_due_notifications.run()
    assert result == {"processed": 2, "delivered": 2, "failed": 0}

    async with task_database() as session:
        row_a = await session.get(ScholarSphereNotification, "global-a")
        row_b = await session.get(ScholarSphereNotification, "global-b")
    assert row_a.status == NotificationDeliveryStatus.delivered
    assert row_b.status == NotificationDeliveryStatus.delivered


@pytest.mark.asyncio
async def test_retry_failed_notifications_task(
    task_database: async_sessionmaker[AsyncSession],
) -> None:
    async with task_database() as session:
        async with session.begin():
            session.add(
                ScholarSphereNotification(
                    id="retry-a",
                    user_id="user-z",
                    type="deadline_reminder",
                    title="t",
                    message="m",
                    channels=["sms"],
                    scheduled_for=date.today(),
                    status=NotificationDeliveryStatus.failed,
                    retry_count=0,
                    timezone="UTC",
                )
            )

    result = retry_failed_notifications.run()
    assert result == {"retried": 1, "expired": 0}

    async with task_database() as session:
        row = await session.get(ScholarSphereNotification, "retry-a")
    assert row.status == NotificationDeliveryStatus.retrying
    assert row.retry_count == 1

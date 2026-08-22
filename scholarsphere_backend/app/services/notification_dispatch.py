from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionFactory
from app.models.notification import (
    NotificationChannel,
    NotificationDeliveryStatus,
    NotificationEventType,
    NotificationFrequency,
    NotificationPreferences,
    ScholarSphereNotification,
)
from app.services.parsing import utc_now

_CONFIGURED_CHANNELS = frozenset({"in_app", "email", "push"})
_DUE_STATUSES = (
    NotificationDeliveryStatus.scheduled,
    NotificationDeliveryStatus.queued,
    NotificationDeliveryStatus.retrying,
)

_EVENT_TITLES: dict[NotificationEventType, str] = {
    NotificationEventType.matching_opportunity: "New matching opportunity",
    NotificationEventType.deadline_reminder: "Deadline reminder",
    NotificationEventType.requirements_changed: "Requirements changed",
    NotificationEventType.deadline_changed: "Deadline changed",
    NotificationEventType.opportunity_verified: "Opportunity verified",
    NotificationEventType.saved_opportunity_expired: "Saved opportunity expired",
    NotificationEventType.application_progress: "Application status updated",
    NotificationEventType.provider_announcement: "Provider announcement",
    NotificationEventType.emergency_system_message: "Important system message",
    NotificationEventType.reverification_due: "Reverification due",
}


def event_title(event_type: NotificationEventType) -> str:
    return _EVENT_TITLES[event_type]


def wants_in_app_notification(
    preferences: NotificationPreferences, event_type: NotificationEventType
) -> bool:
    """Whether a notification should actually be created for this recipient,

    given their real saved preferences - a global opt-out
    (frequency=disabled), removing the in_app channel, or unsubscribing
    from this specific type all suppress creation, exactly like an
    applicant's preferences would for any other notification type.
    """
    if preferences.frequency == NotificationFrequency.disabled:
        return False
    if NotificationChannel.in_app.value not in preferences.channels:
        return False
    if event_type.value in preferences.unsubscribed_types:
        return False
    return True


def event_enabled(preferences: NotificationPreferences, event_type: NotificationEventType) -> bool:
    """Port of DemoNotificationRepository._eventEnabled()."""
    if event_type == NotificationEventType.matching_opportunity:
        return preferences.matching_opportunities
    if event_type == NotificationEventType.deadline_reminder:
        return True
    if event_type in (
        NotificationEventType.requirements_changed,
        NotificationEventType.deadline_changed,
    ):
        return preferences.opportunity_changes
    if event_type == NotificationEventType.opportunity_verified:
        return preferences.verification_updates
    if event_type == NotificationEventType.saved_opportunity_expired:
        return preferences.saved_opportunity_expiry
    return True  # application_progress, provider_announcement, emergency_system_message


def outside_quiet_hours(
    scheduled: datetime, *, start: int | None, end: int | None
) -> datetime:
    """Port of DemoNotificationRepository._outsideQuietHours()."""
    if start is None or end is None:
        return scheduled
    hour = scheduled.hour
    in_quiet_hours = (
        (hour >= start or hour < end) if start > end else (start <= hour < end)
    )
    if not in_quiet_hours:
        return scheduled
    next_time = scheduled.replace(hour=end, minute=0, second=0, microsecond=0)
    return next_time if next_time > scheduled else next_time + timedelta(days=1)


def default_preferences(user_id: str) -> NotificationPreferences:
    """An unsaved, in-memory-only default row - never inserted on a bare GET.

    SQLAlchemy's Python-side ``default=`` on ``mapped_column`` only applies
    at flush/insert time, not on direct construction - so every field must
    be spelled out explicitly here to match ``NotificationPreferences()``'s
    Dart defaults for a transient (never-flushed) instance.
    """
    return NotificationPreferences(
        user_id=user_id,
        channels=[
            NotificationChannel.in_app.value,
            NotificationChannel.email.value,
            NotificationChannel.push.value,
        ],
        frequency=NotificationFrequency.immediate,
        reminder_days=[30, 14, 7, 3, 1],
        matching_opportunities=True,
        opportunity_changes=True,
        verification_updates=True,
        saved_opportunity_expiry=True,
        quiet_hours_start=None,
        quiet_hours_end=None,
        timezone="UTC",
        daily_limit=10,
        group_notifications=True,
        unsubscribed_types=[],
    )


async def process_due_notifications(
    session: AsyncSession, *, user_id: str | None = None
) -> dict[str, int]:
    """Flip due notifications to delivered/failed.

    Scoped to one user (the eager-GET path) or global (admin trigger /
    Celery beat) depending on whether ``user_id`` is given - single source
    of truth for both callers.
    """
    now = utc_now()
    filters = [
        ScholarSphereNotification.status.in_(_DUE_STATUSES),
        ScholarSphereNotification.scheduled_for <= now,
    ]
    if user_id is not None:
        filters.append(ScholarSphereNotification.user_id == user_id)
    rows = (await session.scalars(select(ScholarSphereNotification).where(*filters))).all()
    delivered = 0
    failed = 0
    for row in rows:
        has_configured_channel = any(channel in _CONFIGURED_CHANNELS for channel in row.channels)
        if has_configured_channel:
            row.status = NotificationDeliveryStatus.delivered
            row.sent_at = now
            row.delivered_at = now
            row.failure_reason = None
            delivered += 1
        else:
            row.status = NotificationDeliveryStatus.failed
            row.failure_reason = "Delivery provider is not configured."
            failed += 1
    return {"processed": len(rows), "delivered": delivered, "failed": failed}


async def retry_failed_notifications(
    session: AsyncSession, *, maximum_retries: int = 3
) -> dict[str, int]:
    """Port of DemoNotificationRepository.retryFailed()."""
    rows = (
        await session.scalars(
            select(ScholarSphereNotification).where(
                ScholarSphereNotification.status == NotificationDeliveryStatus.failed
            )
        )
    ).all()
    retried = 0
    expired = 0
    for row in rows:
        if row.retry_count >= maximum_retries:
            row.status = NotificationDeliveryStatus.expired
            expired += 1
        else:
            row.status = NotificationDeliveryStatus.retrying
            row.retry_count += 1
            retried += 1
    return {"retried": retried, "expired": expired}


async def process_due_notifications_task() -> dict[str, int]:
    """Celery-facing wrapper: owns its own session/transaction, global scope."""
    async with AsyncSessionFactory() as session:
        async with session.begin():
            return await process_due_notifications(session)


async def retry_failed_notifications_task() -> dict[str, int]:
    async with AsyncSessionFactory() as session:
        async with session.begin():
            return await retry_failed_notifications(session)

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.public_opportunities import _is_public
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import STAFF_ROLES, require_roles
from app.db.session import get_db
from app.models.external_opportunity import ExternalOpportunity
from app.models.notification import (
    NotificationDeliveryStatus,
    NotificationEventType,
    NotificationPreferences,
    NotificationTemplate,
    ScholarSphereNotification,
)
from app.schemas.notification import (
    NotificationDeliveryAnalytics,
    NotificationPage,
    NotificationPreferencesRead,
    NotificationPreferencesUpdate,
    NotificationRead,
    RecordOpportunityEventRequest,
    RetryFailedRequest,
    SaveTemplateRequest,
    ScheduleDeadlineRemindersRequest,
    event_type_from_wire,
    frequency_from_wire,
)
from app.services.notification_dispatch import (
    default_preferences,
    event_enabled,
    event_title,
    outside_quiet_hours,
    process_due_notifications,
    retry_failed_notifications,
)
from app.services.parsing import utc_now

router = APIRouter(prefix="/notifications", tags=["notifications"])

any_authenticated = Depends(get_current_user)
staff_access = Depends(require_roles(*STAFF_ROLES))


@router.get("/preferences", response_model=NotificationPreferencesRead)
async def get_preferences(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationPreferencesRead:
    preferences = await session.get(NotificationPreferences, user.uid)
    return NotificationPreferencesRead.model_validate(
        preferences or default_preferences(user.uid)
    )


@router.put("/preferences", response_model=NotificationPreferencesRead)
async def save_preferences(
    payload: NotificationPreferencesUpdate,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationPreferencesRead:
    async with session.begin():
        preferences = await session.get(NotificationPreferences, user.uid)
        if preferences is None:
            preferences = NotificationPreferences(user_id=user.uid)
            session.add(preferences)
        preferences.channels = payload.channels
        preferences.frequency = frequency_from_wire(payload.frequency)
        preferences.reminder_days = payload.reminder_days
        preferences.matching_opportunities = payload.matching_opportunities
        preferences.opportunity_changes = payload.opportunity_changes
        preferences.verification_updates = payload.verification_updates
        preferences.saved_opportunity_expiry = payload.saved_opportunity_expiry
        preferences.quiet_hours_start = payload.quiet_hours_start
        preferences.quiet_hours_end = payload.quiet_hours_end
        preferences.timezone = payload.timezone
        preferences.daily_limit = payload.daily_limit
        preferences.group_notifications = payload.group_notifications
        preferences.unsubscribed_types = payload.unsubscribed_types
        await session.flush()
        await session.refresh(preferences)
        return NotificationPreferencesRead.model_validate(preferences)


@router.get("", response_model=list[NotificationRead])
async def list_my_notifications(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[NotificationRead]:
    async with session.begin():
        await process_due_notifications(session, user_id=user.uid)
        rows = (
            await session.scalars(
                select(ScholarSphereNotification)
                .where(ScholarSphereNotification.user_id == user.uid)
                .order_by(ScholarSphereNotification.scheduled_for.asc())
            )
        ).all()
        return [NotificationRead.model_validate(row) for row in rows]


@router.post("/deadline-reminders", status_code=204)
async def schedule_deadline_reminders(
    payload: ScheduleDeadlineRemindersRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        preferences = await session.get(NotificationPreferences, user.uid)
        preferences = preferences or default_preferences(user.uid)
        if (
            preferences.frequency.value == "disabled"
            or "deadline_reminder" in preferences.unsubscribed_types
        ):
            return
        today = utc_now().date()
        opportunities = (
            await session.scalars(
                select(ExternalOpportunity).where(
                    ExternalOpportunity.id.in_(payload.opportunity_ids)
                )
            )
        ).all()
        for opportunity in opportunities:
            if not _is_public(opportunity):
                continue
            if opportunity.deadline is None or opportunity.deadline <= today:
                continue
            for days in preferences.reminder_days:
                notification_id = f"{opportunity.id}-deadline-{days}"
                existing = await session.get(ScholarSphereNotification, notification_id)
                if existing is not None:
                    continue
                deadline_dt = utc_now().replace(
                    year=opportunity.deadline.year,
                    month=opportunity.deadline.month,
                    day=opportunity.deadline.day,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
                scheduled_for = outside_quiet_hours(
                    deadline_dt - timedelta(days=days),
                    start=preferences.quiet_hours_start,
                    end=preferences.quiet_hours_end,
                )
                session.add(
                    ScholarSphereNotification(
                        id=notification_id,
                        user_id=user.uid,
                        type=NotificationEventType.deadline_reminder,
                        title=f"{days}-day deadline reminder",
                        message=(
                            f"{opportunity.title} closes in {days} "
                            f"{'day' if days == 1 else 'days'}."
                        ),
                        channels=preferences.channels,
                        scheduled_for=scheduled_for,
                        opportunity_id=opportunity.id,
                        related_entity_type="opportunity",
                        related_entity_id=str(opportunity.id),
                        timezone=preferences.timezone,
                        group_key=(
                            f"deadline-{opportunity.id}"
                            if preferences.group_notifications
                            else None
                        ),
                    )
                )


@router.post("/events", status_code=204)
async def record_opportunity_event(
    payload: RecordOpportunityEventRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        opportunity = await session.get(ExternalOpportunity, payload.opportunity_id)
        if opportunity is None:
            raise HTTPException(status_code=404, detail="Opportunity not found.")
        preferences = await session.get(NotificationPreferences, payload.user_id)
        preferences = preferences or default_preferences(payload.user_id)
        event_type = NotificationEventType(event_type_from_wire(payload.type))
        if (
            preferences.frequency.value == "disabled"
            or event_type.value in preferences.unsubscribed_types
            or not event_enabled(preferences, event_type)
        ):
            return
        if event_type != NotificationEventType.emergency_system_message:
            now = utc_now()
            start_of_today = datetime(
                now.year, now.month, now.day, tzinfo=timezone.utc
            )
            end_of_today = start_of_today + timedelta(days=1)
            todays_count = await session.scalar(
                select(func.count(ScholarSphereNotification.id)).where(
                    ScholarSphereNotification.user_id == payload.user_id,
                    ScholarSphereNotification.created_at >= start_of_today,
                    ScholarSphereNotification.created_at < end_of_today,
                )
            )
            if (todays_count or 0) >= preferences.daily_limit:
                return
        session.add(
            ScholarSphereNotification(
                id=uuid4().hex,
                user_id=payload.user_id,
                type=event_type,
                title=event_title(event_type),
                message=payload.message,
                channels=preferences.channels,
                scheduled_for=outside_quiet_hours(
                    utc_now(),
                    start=preferences.quiet_hours_start,
                    end=preferences.quiet_hours_end,
                ),
                opportunity_id=opportunity.id,
                related_entity_type="opportunity",
                related_entity_id=str(opportunity.id),
                timezone=preferences.timezone,
                group_key=(
                    f"{event_type.value}-{opportunity.id}"
                    if preferences.group_notifications
                    else None
                ),
            )
        )


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: str,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationRead:
    async with session.begin():
        notification = await session.get(ScholarSphereNotification, notification_id)
        if notification is None or notification.user_id != user.uid:
            raise HTTPException(status_code=404, detail="Notification not found.")
        notification.status = NotificationDeliveryStatus.read
        notification.read_at = utc_now()
        await session.flush()
        await session.refresh(notification)
        return NotificationRead.model_validate(notification)


@router.post("/{notification_id}/cancel", response_model=NotificationRead)
async def cancel_notification(
    notification_id: str,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationRead:
    async with session.begin():
        notification = await session.get(ScholarSphereNotification, notification_id)
        if notification is None or notification.user_id != user.uid:
            raise HTTPException(status_code=404, detail="Notification not found.")
        notification.status = NotificationDeliveryStatus.cancelled
        await session.flush()
        await session.refresh(notification)
        return NotificationRead.model_validate(notification)


@router.get("/admin", response_model=NotificationPage)
async def list_all_notifications(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
    user_id: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> NotificationPage:
    filters = []
    if user_id:
        filters.append(ScholarSphereNotification.user_id == user_id)
    total = await session.scalar(
        select(func.count(ScholarSphereNotification.id)).where(*filters)
    )
    rows = (
        await session.scalars(
            select(ScholarSphereNotification)
            .where(*filters)
            .order_by(ScholarSphereNotification.scheduled_for.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return NotificationPage(
        items=[NotificationRead.model_validate(row) for row in rows],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.put("/admin/templates/{template_id}", status_code=204)
async def save_template(
    template_id: str,
    payload: SaveTemplateRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    async with session.begin():
        template = await session.get(NotificationTemplate, template_id)
        event_type = NotificationEventType(event_type_from_wire(payload.type))
        if template is None:
            template = NotificationTemplate(id=template_id, type=event_type)
            session.add(template)
        template.type = event_type
        template.title_template = payload.title_template
        template.body_template = payload.body_template
        template.channels = payload.channels


@router.post("/admin/process-due")
async def trigger_process_due(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    async with session.begin():
        return await process_due_notifications(session)


@router.post("/admin/retry-failed")
async def trigger_retry_failed(
    payload: RetryFailedRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    async with session.begin():
        return await retry_failed_notifications(session, maximum_retries=payload.maximum_retries)


@router.get("/admin/analytics", response_model=NotificationDeliveryAnalytics)
async def get_delivery_analytics(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationDeliveryAnalytics:
    total = await session.scalar(select(func.count(ScholarSphereNotification.id)))
    delivered = await session.scalar(
        select(func.count(ScholarSphereNotification.id)).where(
            ScholarSphereNotification.status == NotificationDeliveryStatus.delivered
        )
    )
    read = await session.scalar(
        select(func.count(ScholarSphereNotification.id)).where(
            ScholarSphereNotification.status == NotificationDeliveryStatus.read
        )
    )
    failed = await session.scalar(
        select(func.count(ScholarSphereNotification.id)).where(
            ScholarSphereNotification.status == NotificationDeliveryStatus.failed
        )
    )
    retried = await session.scalar(
        select(func.count(ScholarSphereNotification.id)).where(
            ScholarSphereNotification.retry_count > 0
        )
    )
    return NotificationDeliveryAnalytics(
        total=total or 0,
        delivered=delivered or 0,
        read=read or 0,
        failed=failed or 0,
        retried=retried or 0,
    )

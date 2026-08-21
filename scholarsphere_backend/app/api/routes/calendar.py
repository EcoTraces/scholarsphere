from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import STAFF_ROLES, require_roles
from app.db.session import get_db
from app.models.calendar import CalendarEvent, CalendarEventType, DeadlineState
from app.schemas.calendar import (
    CalendarConflictRead,
    CalendarEventRead,
    IcsExportRead,
    MarkSynchronizedRequest,
    SaveCalendarEventRequest,
    UpdateDeadlineRequest,
    deadline_state_from_wire,
    deadline_state_to_wire,
    event_type_from_wire,
    is_sticky_state,
    provider_from_wire,
)
from app.services.parsing import utc_now

router = APIRouter(prefix="/calendar", tags=["calendar"])

any_authenticated = Depends(get_current_user)
# administrativeDeadlines() has no current UI caller (a cross-user view of
# opportunity deadlines is an ops/reporting concern, not applicant
# self-service) - gated to staff, matching the pattern used for other
# no-current-caller interface methods elsewhere in this backend.
staff_access = Depends(require_roles(*STAFF_ROLES))


def _aware(value: datetime) -> datetime:
    """Normalize a DB-read datetime to timezone-aware (assume UTC if naive).

    SQLite (used in tests) doesn't round-trip tzinfo on DateTime(timezone=
    True) columns the way Postgres does.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _current_state(starts_at: datetime, configured: DeadlineState) -> DeadlineState:
    if is_sticky_state(configured):
        return configured
    today = date.today()
    deadline_date = starts_at.date()
    if deadline_date == today:
        return DeadlineState.today
    if deadline_date < today:
        return DeadlineState.passed
    if (deadline_date - today).days <= 14:
        return DeadlineState.closing_soon
    return DeadlineState.upcoming


async def _require_owned(
    session: AsyncSession, event_id: str, uid: str
) -> CalendarEvent:
    event = await session.get(CalendarEvent, event_id)
    if event is None or event.user_id != uid:
        raise HTTPException(status_code=404, detail="Calendar event was not found.")
    return event


def _recurrence_to_dict(recurrence) -> dict | None:
    if recurrence is None:
        return None
    return {
        "frequency": recurrence.frequency,
        "interval": recurrence.interval,
        "count": recurrence.count,
        "until": recurrence.until.isoformat() if recurrence.until else None,
    }


@router.post("/events", response_model=CalendarEventRead)
async def save_event(
    payload: SaveCalendarEventRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CalendarEventRead:
    if not payload.ends_at > payload.starts_at:
        raise HTTPException(
            status_code=422, detail="Calendar event end must follow its start."
        )
    async with session.begin():
        existing = await session.get(CalendarEvent, payload.id)
        if existing is not None and existing.user_id != user.uid:
            raise HTTPException(status_code=404, detail="Calendar event was not found.")
        state = _current_state(payload.starts_at, deadline_state_from_wire(payload.deadline_state))
        recurrence = _recurrence_to_dict(payload.recurrence)
        if existing is None:
            event = CalendarEvent(
                id=payload.id,
                user_id=user.uid,
                title=payload.title,
                description=payload.description,
                type=event_type_from_wire(payload.type),
                starts_at=payload.starts_at,
                ends_at=payload.ends_at,
                timezone=payload.timezone,
                reminder_minutes=payload.reminder_minutes,
                deadline_state=state,
                related_entity_id=payload.related_entity_id,
                recurrence=recurrence,
                created_at=utc_now(),
            )
            session.add(event)
        else:
            existing.title = payload.title
            existing.description = payload.description
            existing.type = event_type_from_wire(payload.type)
            existing.starts_at = payload.starts_at
            existing.ends_at = payload.ends_at
            existing.timezone = payload.timezone
            existing.reminder_minutes = payload.reminder_minutes
            existing.deadline_state = state
            existing.related_entity_id = payload.related_entity_id
            existing.recurrence = recurrence
            event = existing
        await session.flush()
        await session.refresh(event)
        return CalendarEventRead.model_validate(event)


@router.post("/events/{event_id}/deadline", response_model=CalendarEventRead)
async def update_deadline(
    event_id: str,
    payload: UpdateDeadlineRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CalendarEventRead:
    async with session.begin():
        event = await _require_owned(session, event_id, user.uid)
        starts_at = _aware(event.starts_at)
        duration = _aware(event.ends_at) - starts_at
        extended = payload.new_deadline > starts_at
        event.previous_starts_at = event.starts_at
        event.starts_at = payload.new_deadline
        event.ends_at = payload.new_deadline + duration
        event.deadline_state = (
            DeadlineState.extended if extended else DeadlineState.changed
        )
        await session.flush()
        await session.refresh(event)
        return CalendarEventRead.model_validate(event)


@router.get("/events", response_model=list[CalendarEventRead])
async def get_events(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
) -> list[CalendarEventRead]:
    query = select(CalendarEvent).where(CalendarEvent.user_id == user.uid)
    if from_ is not None:
        query = query.where(CalendarEvent.ends_at >= from_)
    if to is not None:
        query = query.where(CalendarEvent.starts_at <= to)
    rows = (await session.scalars(query.order_by(CalendarEvent.starts_at))).all()
    return [CalendarEventRead.model_validate(row) for row in rows]


@router.get("/conflicts", response_model=list[CalendarConflictRead])
async def get_conflicts(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[CalendarConflictRead]:
    rows = list(
        (
            await session.scalars(
                select(CalendarEvent)
                .where(CalendarEvent.user_id == user.uid)
                .order_by(CalendarEvent.starts_at)
            )
        ).all()
    )
    conflicts: list[CalendarConflictRead] = []
    for left in range(len(rows)):
        for right in range(left + 1, len(rows)):
            start = max(rows[left].starts_at, rows[right].starts_at)
            end = min(rows[left].ends_at, rows[right].ends_at)
            if end > start:
                conflicts.append(
                    CalendarConflictRead(
                        first_event_id=rows[left].id,
                        second_event_id=rows[right].id,
                        overlap_seconds=int((end - start).total_seconds()),
                    )
                )
    return conflicts


def _escape_ics(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _ics_timestamp(value: datetime) -> str:
    # SQLite (used in tests) doesn't round-trip tzinfo on DateTime(timezone=
    # True) columns the way Postgres does, so a naive read is assumed UTC.
    aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@router.get("/export.ics", response_model=IcsExportRead)
async def export_ics(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> IcsExportRead:
    rows = (
        await session.scalars(
            select(CalendarEvent)
            .where(CalendarEvent.user_id == user.uid)
            .order_by(CalendarEvent.starts_at)
        )
    ).all()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ScholarSphere//Deadline Calendar//EN", "CALSCALE:GREGORIAN"]
    for event in rows:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{_escape_ics(event.id)}@scholarsphere",
            f"DTSTAMP:{_ics_timestamp(event.created_at)}",
            f"DTSTART:{_ics_timestamp(event.starts_at)}",
            f"DTEND:{_ics_timestamp(event.ends_at)}",
            f"SUMMARY:{_escape_ics(event.title)}",
            f"DESCRIPTION:{_escape_ics(event.description)}",
        ]
        if event.recurrence is not None:
            rule = f"RRULE:FREQ={event.recurrence['frequency'].upper()};INTERVAL={event.recurrence['interval']}"
            if event.recurrence.get("count") is not None:
                rule += f";COUNT={event.recurrence['count']}"
            lines.append(rule)
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return IcsExportRead(content="\r\n".join(lines))


@router.post("/events/{event_id}/sync", response_model=CalendarEventRead)
async def mark_synchronized(
    event_id: str,
    payload: MarkSynchronizedRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CalendarEventRead:
    async with session.begin():
        event = await _require_owned(session, event_id, user.uid)
        provider = provider_from_wire(payload.provider)
        event.external_calendar_id = f"{provider.value}:{payload.external_id}"
        await session.flush()
        await session.refresh(event)
        return CalendarEventRead.model_validate(event)


@router.get("/administrative-deadlines", response_model=list[CalendarEventRead])
async def administrative_deadlines(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[CalendarEventRead]:
    rows = (
        await session.scalars(
            select(CalendarEvent)
            .where(CalendarEvent.type == CalendarEventType.opportunity_deadline)
            .order_by(CalendarEvent.starts_at)
        )
    ).all()
    return [CalendarEventRead.model_validate(row) for row in rows]

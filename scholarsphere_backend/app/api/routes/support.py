from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.support import (
    KnowledgeArticle,
    SatisfactionSurvey,
    SupportInternalNote,
    SupportMessage,
    SupportResponseTemplate,
    SupportTicket,
    SupportTicketEvent,
    SupportTicketStatus,
)
from app.schemas.support import (
    AddInternalNoteRequest,
    AddMessageRequest,
    EscalateRequest,
    InternalSupportNoteRead,
    KnowledgeArticleRead,
    SaveArticleRequest,
    SaveTemplateRequest,
    SubmitSurveyRequest,
    SubmitTicketRequest,
    SupportMessageRead,
    SupportPerformanceReportRead,
    SupportResponseTemplateRead,
    SupportTicketEventRead,
    SupportTicketRead,
    UpdateStatusRequest,
    category_from_wire,
    category_to_wire,
    content_type_from_wire,
    is_closed_ticket_status,
    priority_from_wire,
    status_from_wire,
)
from app.services.parsing import utc_now

router = APIRouter(prefix="/support", tags=["support"])

any_authenticated = Depends(get_current_user)
staff_access = Depends(require_roles("supportOfficer", "administrator", "superAdministrator"))

_STAFF_ROLES = frozenset({"supportOfficer", "administrator", "superAdministrator"})

_SLA_BY_PRIORITY = {
    "urgent": (timedelta(minutes=30), timedelta(hours=4)),
    "high": (timedelta(hours=2), timedelta(hours=12)),
    "normal": (timedelta(hours=8), timedelta(days=2)),
    "low": (timedelta(days=1), timedelta(days=5)),
}


async def _to_read(session: AsyncSession, ticket: SupportTicket) -> SupportTicketRead:
    messages = (
        await session.scalars(
            select(SupportMessage)
            .where(SupportMessage.ticket_id == ticket.id)
            .order_by(SupportMessage.created_at.asc())
        )
    ).all()
    notes = (
        await session.scalars(
            select(SupportInternalNote)
            .where(SupportInternalNote.ticket_id == ticket.id)
            .order_by(SupportInternalNote.created_at.asc())
        )
    ).all()
    history = (
        await session.scalars(
            select(SupportTicketEvent)
            .where(SupportTicketEvent.ticket_id == ticket.id)
            .order_by(SupportTicketEvent.created_at.asc())
        )
    ).all()
    read = SupportTicketRead.model_validate(ticket)
    read.messages = [SupportMessageRead.model_validate(m) for m in messages]
    read.internal_notes = [InternalSupportNoteRead.model_validate(n) for n in notes]
    read.history = [SupportTicketEventRead.model_validate(h) for h in history]
    return read


def _can_view(ticket: SupportTicket, user: AuthenticatedUser) -> bool:
    return user.role in _STAFF_ROLES or ticket.requester_id == user.uid


@router.post("/tickets", response_model=SupportTicketRead)
async def submit_ticket(
    payload: SubmitTicketRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SupportTicketRead:
    async with session.begin():
        now = utc_now()
        first_response_delta, resolution_delta = _SLA_BY_PRIORITY[payload.priority]
        ticket = SupportTicket(
            requester_id=user.uid,
            subject=payload.subject.strip(),
            category=category_from_wire(payload.category),
            priority=priority_from_wire(payload.priority),
            status=SupportTicketStatus.open,
            first_response_due_at=now + first_response_delta,
            resolution_due_at=now + resolution_delta,
        )
        session.add(ticket)
        await session.flush()
        session.add(
            SupportMessage(
                ticket_id=ticket.id,
                sender_id=user.uid,
                message=payload.message.strip(),
                attachments=[item.model_dump() for item in payload.attachments],
                is_agent=False,
            )
        )
        session.add(
            SupportTicketEvent(
                ticket_id=ticket.id,
                status=SupportTicketStatus.open,
                actor_id=user.uid,
                notes="Ticket submitted.",
            )
        )
        await session.flush()
        await session.refresh(ticket)
        return await _to_read(session, ticket)


@router.get("/tickets/mine", response_model=list[SupportTicketRead])
async def get_my_tickets(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[SupportTicketRead]:
    rows = (
        await session.scalars(
            select(SupportTicket)
            .where(SupportTicket.requester_id == user.uid)
            .order_by(SupportTicket.updated_at.desc())
        )
    ).all()
    return [await _to_read(session, row) for row in rows]


@router.get("/tickets/queue", response_model=list[SupportTicketRead])
async def get_agent_queue(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[SupportTicketRead]:
    closed = {SupportTicketStatus.closed, SupportTicketStatus.resolved}
    rows = (
        await session.scalars(
            select(SupportTicket)
            .where(SupportTicket.status.not_in(closed))
            .order_by(SupportTicket.priority.desc(), SupportTicket.created_at.asc())
        )
    ).all()
    return [await _to_read(session, row) for row in rows]


@router.get("/tickets/{ticket_id}", response_model=SupportTicketRead)
async def get_ticket(
    ticket_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SupportTicketRead:
    ticket = await session.get(SupportTicket, ticket_id)
    if ticket is None or not _can_view(ticket, user):
        raise HTTPException(status_code=404, detail="Support ticket not found.")
    return await _to_read(session, ticket)


@router.post("/tickets/{ticket_id}/assign", response_model=SupportTicketRead)
async def assign_ticket(
    ticket_id: UUID,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SupportTicketRead:
    async with session.begin():
        ticket = await session.get(SupportTicket, ticket_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Support ticket not found.")
        ticket.status = SupportTicketStatus.assigned
        ticket.assigned_agent_id = user.uid
        session.add(
            SupportTicketEvent(
                ticket_id=ticket.id,
                status=SupportTicketStatus.assigned,
                actor_id=user.uid,
                notes="Assigned to support agent.",
            )
        )
        await session.flush()
        await session.refresh(ticket)
        return await _to_read(session, ticket)


@router.post("/tickets/{ticket_id}/messages", response_model=SupportTicketRead)
async def add_message(
    ticket_id: UUID,
    payload: AddMessageRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SupportTicketRead:
    is_agent = user.role in _STAFF_ROLES
    async with session.begin():
        ticket = await session.get(SupportTicket, ticket_id)
        if ticket is None or (not is_agent and ticket.requester_id != user.uid):
            raise HTTPException(status_code=404, detail="Support ticket not found.")
        if ticket.status == SupportTicketStatus.closed:
            raise HTTPException(
                status_code=409, detail="Closed tickets must be reopened first."
            )
        ticket.status = (
            SupportTicketStatus.waiting_for_user if is_agent else SupportTicketStatus.in_progress
        )
        session.add(
            SupportMessage(
                ticket_id=ticket.id,
                sender_id=user.uid,
                message=payload.message.strip(),
                attachments=[item.model_dump() for item in payload.attachments],
                is_agent=is_agent,
            )
        )
        await session.flush()
        await session.refresh(ticket)
        return await _to_read(session, ticket)


@router.post("/tickets/{ticket_id}/notes", response_model=SupportTicketRead)
async def add_internal_note(
    ticket_id: UUID,
    payload: AddInternalNoteRequest,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SupportTicketRead:
    async with session.begin():
        ticket = await session.get(SupportTicket, ticket_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Support ticket not found.")
        session.add(
            SupportInternalNote(ticket_id=ticket.id, agent_id=user.uid, note=payload.note.strip())
        )
        await session.flush()
        await session.refresh(ticket)
        return await _to_read(session, ticket)


@router.post("/tickets/{ticket_id}/status", response_model=SupportTicketRead)
async def update_status(
    ticket_id: UUID,
    payload: UpdateStatusRequest,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SupportTicketRead:
    new_status = status_from_wire(payload.status)
    async with session.begin():
        ticket = await session.get(SupportTicket, ticket_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Support ticket not found.")
        if new_status == SupportTicketStatus.reopened and not is_closed_ticket_status(
            ticket.status
        ):
            raise HTTPException(
                status_code=409, detail="Only resolved or closed tickets can reopen."
            )
        now = utc_now()
        ticket.status = new_status
        ticket.resolved_at = now if new_status == SupportTicketStatus.resolved else None
        ticket.closed_at = now if new_status == SupportTicketStatus.closed else None
        session.add(
            SupportTicketEvent(
                ticket_id=ticket.id, status=new_status, actor_id=user.uid, notes=payload.notes
            )
        )
        await session.flush()
        await session.refresh(ticket)
        return await _to_read(session, ticket)


@router.post("/tickets/{ticket_id}/escalate", response_model=SupportTicketRead)
async def escalate_ticket(
    ticket_id: UUID,
    payload: EscalateRequest,
    user: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SupportTicketRead:
    async with session.begin():
        ticket = await session.get(SupportTicket, ticket_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Support ticket not found.")
        ticket.status = SupportTicketStatus.escalated
        ticket.escalation_reason = payload.reason
        session.add(
            SupportTicketEvent(
                ticket_id=ticket.id,
                status=SupportTicketStatus.escalated,
                actor_id=user.uid,
                notes=payload.reason,
            )
        )
        await session.flush()
        await session.refresh(ticket)
        return await _to_read(session, ticket)


@router.post("/tickets/{ticket_id}/survey", response_model=SupportTicketRead)
async def submit_survey(
    ticket_id: UUID,
    payload: SubmitSurveyRequest,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SupportTicketRead:
    async with session.begin():
        ticket = await session.get(SupportTicket, ticket_id)
        if (
            ticket is None
            or ticket.requester_id != user.uid
            or not is_closed_ticket_status(ticket.status)
        ):
            raise HTTPException(
                status_code=409,
                detail="Surveys are available to the requester after resolution.",
            )
        existing = await session.get(SatisfactionSurvey, ticket_id)
        if existing is not None:
            existing.rating = payload.rating
            existing.comment = payload.comment
            existing.created_at = utc_now()
        else:
            session.add(
                SatisfactionSurvey(
                    ticket_id=ticket_id,
                    user_id=user.uid,
                    rating=payload.rating,
                    comment=payload.comment,
                )
            )
        return await _to_read(session, ticket)


@router.get("/knowledge", response_model=list[KnowledgeArticleRead])
async def search_knowledge(
    _: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
    query: str = "",
    category: str | None = None,
) -> list[KnowledgeArticleRead]:
    filters = [KnowledgeArticle.published.is_(True)]
    if category:
        filters.append(KnowledgeArticle.category == category_from_wire(category))
    rows = (await session.scalars(select(KnowledgeArticle).where(*filters))).all()
    normalized = query.strip().lower()
    if normalized:
        rows = [
            row
            for row in rows
            if normalized in row.title.lower()
            or normalized in row.summary.lower()
            or any(normalized in keyword.lower() for keyword in row.keywords)
        ]
    return [KnowledgeArticleRead.model_validate(row) for row in rows]


@router.put("/knowledge/{article_id}", response_model=KnowledgeArticleRead)
async def save_article(
    article_id: str,
    payload: SaveArticleRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeArticleRead:
    async with session.begin():
        article = await session.get(KnowledgeArticle, article_id)
        if article is None:
            article = KnowledgeArticle(id=article_id)
            session.add(article)
        article.title = payload.title
        article.summary = payload.summary
        article.content = payload.content
        article.type = content_type_from_wire(payload.type)
        article.category = category_from_wire(payload.category)
        article.language_code = payload.language_code
        article.published = payload.published
        article.keywords = payload.keywords
        await session.flush()
        await session.refresh(article)
        return KnowledgeArticleRead.model_validate(article)


@router.get("/templates", response_model=list[SupportResponseTemplateRead])
async def get_templates(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
    category: str = Query(...),
) -> list[SupportResponseTemplateRead]:
    rows = (
        await session.scalars(
            select(SupportResponseTemplate).where(
                SupportResponseTemplate.category == category_from_wire(category)
            )
        )
    ).all()
    return [SupportResponseTemplateRead.model_validate(row) for row in rows]


@router.put("/templates/{template_id}", response_model=SupportResponseTemplateRead)
async def save_template(
    template_id: str,
    payload: SaveTemplateRequest,
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SupportResponseTemplateRead:
    async with session.begin():
        template = await session.get(SupportResponseTemplate, template_id)
        if template is None:
            template = SupportResponseTemplate(id=template_id)
            session.add(template)
        template.name = payload.name
        template.category = category_from_wire(payload.category)
        template.subject = payload.subject
        template.body = payload.body
        await session.flush()
        await session.refresh(template)
        return SupportResponseTemplateRead.model_validate(template)


def _aware(value: datetime) -> datetime:
    """Normalize a DB-read datetime to timezone-aware (assume UTC if naive).

    SQLite (used in tests) doesn't round-trip tzinfo on ``DateTime(timezone=
    True)`` columns the way Postgres does - values read back can come back
    naive even though they were written as UTC-aware. Comparing/subtracting
    against ``utc_now()`` (always aware) would otherwise raise TypeError.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


@router.get("/performance-report", response_model=SupportPerformanceReportRead)
async def performance_report(
    _: Annotated[AuthenticatedUser, staff_access],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SupportPerformanceReportRead:
    tickets = (await session.scalars(select(SupportTicket))).all()
    now = utc_now()
    first_responses: list[float] = []
    resolutions: list[float] = []
    by_category: dict[str, int] = {}
    breaches = 0
    closed = {SupportTicketStatus.resolved, SupportTicketStatus.closed}
    for ticket in tickets:
        wire_category = category_to_wire(ticket.category)
        by_category[wire_category] = by_category.get(wire_category, 0) + 1
        created_at = _aware(ticket.created_at)
        agent_messages = (
            await session.scalars(
                select(SupportMessage)
                .where(SupportMessage.ticket_id == ticket.id, SupportMessage.is_agent.is_(True))
                .order_by(SupportMessage.created_at.asc())
                .limit(1)
            )
        ).first()
        if agent_messages is not None:
            first_responses.append(
                (_aware(agent_messages.created_at) - created_at).total_seconds() / 60
            )
        elif now > _aware(ticket.first_response_due_at):
            breaches += 1
        if ticket.resolved_at is not None:
            resolutions.append((_aware(ticket.resolved_at) - created_at).total_seconds() / 60)
        elif now > _aware(ticket.resolution_due_at):
            breaches += 1
    surveys = (await session.scalars(select(SatisfactionSurvey))).all()
    return SupportPerformanceReportRead(
        total_tickets=len(tickets),
        open_tickets=sum(1 for t in tickets if t.status not in closed),
        sla_breaches=breaches,
        average_first_response_minutes=_average(first_responses),
        average_resolution_minutes=_average(resolutions),
        satisfaction_score=_average([float(s.rating) for s in surveys]),
        by_category=by_category,
    )


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0

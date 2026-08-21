import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.rbac import require_permissions
from app.db.session import get_db
from app.models.security import (
    LoginHistoryEntry,
    LoginOutcome,
    SecurityAlert,
    SecurityAlertType,
    SecuritySession,
)
from app.schemas.security import (
    AlertRead,
    CreateSessionRequest,
    LoginHistoryRead,
    RateLimitCheckRequest,
    RecordLoginRequest,
    SessionRead,
    login_outcome_from_wire,
)
from app.services.parsing import utc_now

router = APIRouter(prefix="/security", tags=["security"])

any_authenticated = Depends(get_current_user)
# Only the account owner or a caller with the `suspendAccounts` permission
# (the same permission gating `AuthRepository.suspendAccount` client-side)
# may revoke another user's sessions - matches the one real cross-user
# caller in this codebase (suspending an account also revokes its
# sessions).
suspend_access = Depends(require_permissions("suspendAccounts"))


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/sessions", response_model=SessionRead)
async def create_session(
    payload: CreateSessionRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SessionRead:
    if payload.privileged and not payload.strong_authentication:
        raise HTTPException(
            status_code=409,
            detail="Privileged sessions require multi-factor authentication.",
        )
    async with session.begin():
        now = utc_now()
        record = SecuritySession(
            id=uuid.uuid4().hex,
            user_id=user.uid,
            device_id=payload.device.id,
            browser=payload.device.browser,
            operating_system=payload.device.operating_system,
            ip_address=_client_ip(request),
            created_at=now,
            expires_at=now
            + (timedelta(minutes=15) if payload.privileged else timedelta(hours=8)),
            last_activity_at=now,
            revoked_at=None,
            strong_authentication=payload.strong_authentication,
        )
        session.add(record)
        await session.flush()
        return SessionRead.from_model(record)


@router.get("/sessions", response_model=list[SessionRead])
async def get_sessions(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[SessionRead]:
    rows = await session.scalars(
        select(SecuritySession).where(SecuritySession.user_id == user.uid)
    )
    return [SessionRead.from_model(row) for row in rows.all()]


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: str,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    async with session.begin():
        record = await session.get(SecuritySession, session_id)
        if record is None or record.user_id != user.uid:
            raise HTTPException(status_code=404, detail="Session not found.")
        record.revoked_at = utc_now()
    return Response(status_code=204)


@router.post("/users/{user_id}/sessions/revoke-all", status_code=204)
async def revoke_all_sessions(
    user_id: str,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    if user_id != user.uid and "suspendAccounts" not in user.permissions:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to revoke another user's sessions.",
        )
    async with session.begin():
        rows = await session.scalars(
            select(SecuritySession).where(
                SecuritySession.user_id == user_id,
                SecuritySession.revoked_at.is_(None),
            )
        )
        now = utc_now()
        for record in rows.all():
            record.revoked_at = now
    return Response(status_code=204)


@router.post("/login-history", status_code=204)
async def record_login(
    payload: RecordLoginRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    outcome = login_outcome_from_wire(payload.outcome)
    email = (user.email or "").lower()
    async with session.begin():
        now = utc_now()
        previous_devices = set(
            (
                await session.scalars(
                    select(LoginHistoryEntry.device_id).where(
                        LoginHistoryEntry.email == email,
                        LoginHistoryEntry.outcome == LoginOutcome.success,
                    )
                )
            ).all()
        )
        new_device = outcome.value == "success" and payload.device.id not in previous_devices
        suspicious = new_device and len(previous_devices) > 0
        session.add(
            LoginHistoryEntry(
                email=email,
                user_id=user.uid,
                occurred_at=now,
                outcome=outcome,
                device_id=payload.device.id,
                browser=payload.device.browser,
                operating_system=payload.device.operating_system,
                ip_address=_client_ip(request),
                suspicious=suspicious,
            )
        )
        if new_device:
            session.add(
                SecurityAlert(
                    user_id=user.uid,
                    type=(
                        SecurityAlertType.suspiciousLogin
                        if suspicious
                        else SecurityAlertType.newDevice
                    ),
                    message=(
                        "A login from a new device requires review."
                        if suspicious
                        else "Your account was accessed from a new device."
                    ),
                    created_at=now,
                    acknowledged_at=None,
                )
            )
    return Response(status_code=204)


@router.get("/login-history", response_model=list[LoginHistoryRead])
async def get_login_history(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[LoginHistoryRead]:
    email = (user.email or "").lower()
    rows = await session.scalars(
        select(LoginHistoryEntry)
        .where(LoginHistoryEntry.email == email)
        .order_by(LoginHistoryEntry.occurred_at.desc())
    )
    return [LoginHistoryRead.from_model(row) for row in rows.all()]


@router.get("/alerts", response_model=list[AlertRead])
async def get_alerts(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AlertRead]:
    rows = await session.scalars(
        select(SecurityAlert).where(SecurityAlert.user_id == user.uid)
    )
    return [AlertRead.model_validate(row) for row in rows.all()]


@router.post("/rate-limit-check", status_code=204)
async def rate_limit_check(
    payload: RateLimitCheckRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, any_authenticated],
) -> Response:
    limiter = request.app.state.rate_limiter
    allowed = await limiter.is_allowed(f"security:{user.uid}:{payload.key}")
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.")
    return Response(status_code=204)

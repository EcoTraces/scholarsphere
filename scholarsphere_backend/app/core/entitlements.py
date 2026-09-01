from datetime import datetime, timezone
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.session import get_db
from app.models.premium_billing import Entitlement, EntitlementStatus, PremiumFeature
from app.services.parsing import utc_now

PREMIUM_FEATURE_REQUIRED_DETAIL = "This is a Premium feature. Upgrade to unlock it."


def _aware(value: datetime) -> datetime:
    # SQLite (used in tests) round-trips DateTime(timezone=True) columns
    # as naive - normalize back to UTC-aware before comparing against
    # utc_now(), same pattern as app/services/audit_log.py::_aware.
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


async def get_active_entitlement(session: AsyncSession, user_id: str) -> Entitlement | None:
    """The caller's current active, unexpired entitlement, or None.

    Server-side and database-backed only - this is the entire point of
    the entitlement system described in the platform spec's "Payment
    Security" section: premium access is never derived from a JWT claim,
    a query parameter, or any client-supplied flag. The only writer of an
    ``active`` ``Entitlement`` row is
    app/services/payment_service.py::grant_entitlement_for_payment, which
    only runs after a payment provider has server-side-verified a real
    transaction (see that module's docstring).
    """
    entitlement = await session.scalar(
        select(Entitlement)
        .where(Entitlement.user_id == user_id)
        .where(Entitlement.status == EntitlementStatus.active)
        .order_by(Entitlement.granted_at.desc())
        .limit(1)
    )
    if entitlement is None:
        return None
    if entitlement.expires_at is not None and _aware(entitlement.expires_at) <= utc_now():
        return None
    return entitlement


def has_feature(entitlement: Entitlement | None, feature: PremiumFeature) -> bool:
    return entitlement is not None and feature.value in entitlement.feature_keys


def require_entitlement(
    feature: PremiumFeature,
) -> Callable[..., "AuthenticatedUser"]:
    """A route dependency mirroring require_roles/require_permissions

    (app/core/rbac.py) but backed by a live database check instead of a
    JWT claim - entitlements are dynamic (a payment can complete, expire,
    or be revoked at any time) and must never be cached into a token the
    way role/permission claims are. Free users can still call every
    *read* endpoint that shows them a feature is locked; only a mutating
    or generation endpoint depends on this.
    """

    async def dependency(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_db)],
    ) -> AuthenticatedUser:
        entitlement = await get_active_entitlement(session, user.uid)
        # Checked before the rollback below, deliberately: rollback()
        # expires every attribute already loaded on this Session (SQLAlchemy
        # has no "expire on rollback = False" option, unlike commit), so
        # reading entitlement.feature_keys afterward - from this plain,
        # non-async helper - would trigger an implicit, illegal lazy-reload.
        allowed = has_feature(entitlement, feature)
        # This dependency runs (and reads) before the route body, on the
        # same request-scoped session - a plain read still opens
        # SQLAlchemy's "autobegin" transaction, which would otherwise
        # collide with a route body that opens its own explicit
        # `async with session.begin()`. Closing it out here (a rollback is
        # always safe: nothing was written) leaves the session clean for
        # whatever the route does next.
        await session.rollback()
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=PREMIUM_FEATURE_REQUIRED_DETAIL,
            )
        return user

    return dependency

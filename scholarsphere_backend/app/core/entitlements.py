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


async def get_active_entitlements(session: AsyncSession, user_id: str) -> list[Entitlement]:
    """Every one of the caller's currently active, unexpired entitlements -

    not just the most recent. A user can legitimately hold more than one
    at a time once individual feature packages exist alongside the
    flagship plan (the platform spec's own "Possible future packages: CV/
    ATS, SOP, Study Plan, ..." section) - buying a second package must
    never silently take away access already paid for in a first one.
    Server-side and database-backed only - the entire point of the
    entitlement system described in the platform spec's "Payment
    Security" section: premium access is never derived from a JWT claim,
    a query parameter, or any client-supplied flag. The only writer of an
    ``active`` ``Entitlement`` row is
    app/services/payment_service.py::grant_entitlement_for_payment, which
    only runs after a payment provider has server-side-verified a real
    transaction (see that module's docstring).
    """
    entitlements = (
        await session.scalars(
            select(Entitlement)
            .where(Entitlement.user_id == user_id)
            .where(Entitlement.status == EntitlementStatus.active)
            .order_by(Entitlement.granted_at.desc())
        )
    ).all()
    now = utc_now()
    return [
        entitlement
        for entitlement in entitlements
        if entitlement.expires_at is None or _aware(entitlement.expires_at) > now
    ]


async def get_active_entitlement(session: AsyncSession, user_id: str) -> Entitlement | None:
    """The single most-recently-granted active entitlement, or None -

    intended for simple "am I premium at all" / status-display purposes
    only (e.g. the billing page's headline banner). Never use this for an
    authorization decision about a *specific* feature: use
    ``get_active_entitlements`` (plural) plus ``has_any_feature`` instead,
    since a user can hold more than one active entitlement at once (see
    that function's docstring) and this single-row view would silently
    hide features a genuinely paying user still has.
    """
    entitlements = await get_active_entitlements(session, user_id)
    return entitlements[0] if entitlements else None


def has_feature(entitlement: Entitlement | None, feature: PremiumFeature) -> bool:
    """Checks a single entitlement only - see ``get_active_entitlement``'s

    docstring for why this must never be used as the real authorization
    check for a specific feature. Kept for status-display call sites.
    """
    return entitlement is not None and feature.value in entitlement.feature_keys


def has_any_feature(entitlements: list[Entitlement], feature: PremiumFeature) -> bool:
    """The real authorization check: true if *any* of the caller's active

    entitlements grants this feature, regardless of which plan or how
    recently it was purchased.
    """
    return any(feature.value in entitlement.feature_keys for entitlement in entitlements)


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
        entitlements = await get_active_entitlements(session, user.uid)
        # Checked before the rollback below, deliberately: rollback()
        # expires every attribute already loaded on this Session (SQLAlchemy
        # has no "expire on rollback = False" option, unlike commit), so
        # reading entitlement.feature_keys afterward - from this plain,
        # non-async helper - would trigger an implicit, illegal lazy-reload.
        allowed = has_any_feature(entitlements, feature)
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

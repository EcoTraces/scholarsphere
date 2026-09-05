"""Configurable AI usage limits - prevents uncontrolled API consumption per

the platform spec's "Usage Management" section. A ``UsageLimit`` database
row (admin-editable) overrides the environment-variable defaults per
feature; both are enforced together (daily and monthly), and every AI
request attempted - not just successful ones - is recorded via
``record_usage`` for the admin "AI usage" dashboard.

Limits can be global (``plan_code`` null) or scoped to a specific plan -
the admin route (``PUT /premium/admin/usage-limits``) accepts a
``plan_code`` and previously had no effect at all once saved (a real,
silently-dead admin control): ``check_usage_allowed`` now looks up the
caller's own active entitlements' plan codes and applies the *most
restrictive* applicable limit (any matching plan-specific row, or the
global row, or the environment-variable default, in that order per
bound) rather than only ever reading the global row.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.premium_billing import AIUsageRecord, AIUsageStatus, Entitlement, EntitlementStatus, PremiumPlan, UsageLimit
from app.services.parsing import utc_now


class UsageLimitExceededError(Exception):
    def __init__(self, message: str, *, period: str, limit: int) -> None:
        super().__init__(message)
        self.period = period
        self.limit = limit


async def _active_plan_codes(session: AsyncSession, user_id: str) -> set[str]:
    rows = await session.execute(
        select(PremiumPlan.code)
        .join(Entitlement, Entitlement.plan_id == PremiumPlan.id)
        .where(Entitlement.user_id == user_id, Entitlement.status == EntitlementStatus.active)
    )
    return {code for (code,) in rows.all()}


async def _effective_limits(
    session: AsyncSession, feature: str, settings: Settings, user_id: str
) -> tuple[int, int]:
    plan_codes = await _active_plan_codes(session, user_id)
    rows = (
        await session.scalars(
            select(UsageLimit).where(
                UsageLimit.feature == feature,
                UsageLimit.plan_code.is_(None) | UsageLimit.plan_code.in_(plan_codes)
                if plan_codes
                else UsageLimit.plan_code.is_(None),
            )
        )
    ).all()

    daily_candidates = [row.limit_per_day for row in rows if row.limit_per_day is not None]
    monthly_candidates = [row.limit_per_month for row in rows if row.limit_per_month is not None]
    daily = min(daily_candidates) if daily_candidates else settings.ai_usage_daily_limit_default
    monthly = min(monthly_candidates) if monthly_candidates else settings.ai_usage_monthly_limit_default
    return daily, monthly


async def _count_since(session: AsyncSession, user_id: str, feature: str, since) -> int:
    return (
        await session.scalar(
            select(func.count(AIUsageRecord.id)).where(
                AIUsageRecord.user_id == user_id,
                AIUsageRecord.feature == feature,
                AIUsageRecord.created_at >= since,
            )
        )
    ) or 0


async def check_usage_allowed(
    session: AsyncSession, *, user_id: str, feature: str, settings: Settings | None = None
) -> None:
    """Raises ``UsageLimitExceededError`` if the caller has hit either the

    daily or monthly ceiling for this feature; otherwise returns silently.
    Called *before* an AI request is attempted, never after.
    """
    settings = settings or get_settings()
    daily_limit, monthly_limit = await _effective_limits(session, feature, settings, user_id)
    now = utc_now()
    daily_count = await _count_since(session, user_id, feature, now - timedelta(days=1))
    if daily_count >= daily_limit:
        raise UsageLimitExceededError(
            f"Daily AI usage limit reached for {feature} ({daily_limit} requests/24h).",
            period="day",
            limit=daily_limit,
        )
    monthly_count = await _count_since(session, user_id, feature, now - timedelta(days=30))
    if monthly_count >= monthly_limit:
        raise UsageLimitExceededError(
            f"Monthly AI usage limit reached for {feature} ({monthly_limit} requests/30d).",
            period="month",
            limit=monthly_limit,
        )


async def record_usage(
    session: AsyncSession,
    *,
    user_id: str,
    feature: str,
    provider: str,
    model: str,
    tokens_used: int | None,
    status: AIUsageStatus,
) -> AIUsageRecord:
    record = AIUsageRecord(
        id=uuid.uuid4(),
        user_id=user_id,
        feature=feature,
        provider=provider,
        model=model,
        tokens_used=tokens_used,
        status=status,
    )
    session.add(record)
    await session.flush()
    return record

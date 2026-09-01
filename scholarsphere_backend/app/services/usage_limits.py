"""Configurable AI usage limits - prevents uncontrolled API consumption per

the platform spec's "Usage Management" section. A ``UsageLimit`` database
row (admin-editable) overrides the environment-variable defaults per
feature; both are enforced together (daily and monthly), and every AI
request attempted - not just successful ones - is recorded via
``record_usage`` for the admin "AI usage" dashboard.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.premium_billing import AIUsageRecord, AIUsageStatus, UsageLimit
from app.services.parsing import utc_now


class UsageLimitExceededError(Exception):
    def __init__(self, message: str, *, period: str, limit: int) -> None:
        super().__init__(message)
        self.period = period
        self.limit = limit


async def _effective_limits(
    session: AsyncSession, feature: str, settings: Settings
) -> tuple[int, int]:
    row = await session.scalar(
        select(UsageLimit).where(UsageLimit.feature == feature, UsageLimit.plan_code.is_(None))
    )
    daily = row.limit_per_day if row and row.limit_per_day is not None else settings.ai_usage_daily_limit_default
    monthly = (
        row.limit_per_month if row and row.limit_per_month is not None else settings.ai_usage_monthly_limit_default
    )
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
    daily_limit, monthly_limit = await _effective_limits(session, feature, settings)
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

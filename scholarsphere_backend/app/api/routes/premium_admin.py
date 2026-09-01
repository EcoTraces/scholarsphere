from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser
from app.core.rbac import require_roles
from app.db.session import get_db
from app.models.premium_billing import (
    AIUsageRecord,
    Entitlement,
    EntitlementStatus,
    Payment,
    PaymentStatus,
    PremiumPlan,
    Refund,
    UsageLimit,
)
from app.schemas.premium_billing import (
    AdminRevenueSummary,
    PaymentRead,
    PremiumPlanCreateRequest,
    PremiumPlanRead,
    PremiumPlanUpdateRequest,
    RefundRead,
    RefundRequest,
    UsageLimitRead,
    UsageLimitUpsertRequest,
)
from app.services import payment_service
from app.services.parsing import utc_now
from app.services.payment_provider import PaymentProviderError

router = APIRouter(prefix="/premium/admin", tags=["premium-admin"])

require_admin = require_roles("administrator", "superAdministrator")


@router.get("/plans", response_model=list[PremiumPlanRead])
async def list_all_plans(
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[PremiumPlanRead]:
    plans = (await session.scalars(select(PremiumPlan).order_by(PremiumPlan.sort_order))).all()
    return [PremiumPlanRead.model_validate(plan) for plan in plans]


@router.post("/plans", response_model=PremiumPlanRead, status_code=201)
async def create_plan(
    payload: PremiumPlanCreateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PremiumPlanRead:
    async with session.begin():
        existing = await session.scalar(select(PremiumPlan).where(PremiumPlan.code == payload.code))
        if existing is not None:
            raise HTTPException(status_code=409, detail="A plan with this code already exists.")
        plan = PremiumPlan(**payload.model_dump(), updated_by=user.uid)
        session.add(plan)
        await session.flush()
        await session.refresh(plan)
        return PremiumPlanRead.model_validate(plan)


@router.patch("/plans/{plan_id}", response_model=PremiumPlanRead)
async def update_plan(
    plan_id: UUID,
    payload: PremiumPlanUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PremiumPlanRead:
    async with session.begin():
        plan = await session.get(PremiumPlan, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Plan was not found.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(plan, field, value)
        plan.updated_by = user.uid
        plan.updated_at = utc_now()
        await session.flush()
        await session.refresh(plan)
        return PremiumPlanRead.model_validate(plan)


@router.get("/payments", response_model=list[PaymentRead])
async def list_payments(
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_filter: PaymentStatus | None = None,
    limit: int = 100,
) -> list[PaymentRead]:
    query = select(Payment).order_by(Payment.created_at.desc()).limit(min(limit, 500))
    if status_filter is not None:
        query = query.where(Payment.status == status_filter)
    payments = (await session.scalars(query)).all()
    return [PaymentRead.model_validate(payment) for payment in payments]


@router.post("/payments/{payment_id}/refund", response_model=RefundRead)
async def refund(
    payment_id: UUID,
    payload: RefundRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RefundRead:
    correlation_id = getattr(request.state, "correlation_id", "admin-refund")
    async with session.begin():
        payment = await session.get(Payment, payment_id)
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment was not found.")
        try:
            refund_record = await payment_service.refund_payment(
                session,
                payment=payment,
                amount_cents=payload.amount_cents,
                reason=payload.reason,
                actor_id=user.uid,
                correlation_id=correlation_id,
            )
        except payment_service.InvalidRefundError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except PaymentProviderError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return RefundRead.model_validate(refund_record)


@router.get("/revenue", response_model=AdminRevenueSummary)
async def revenue_summary(
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminRevenueSummary:
    total_successful = (
        await session.scalar(
            select(func.count(Payment.id)).where(Payment.status == PaymentStatus.success)
        )
    ) or 0
    total_revenue = (
        await session.scalar(
            select(func.coalesce(func.sum(Payment.amount_cents), 0)).where(
                Payment.status == PaymentStatus.success
            )
        )
    ) or 0
    total_refunded = (
        await session.scalar(select(func.coalesce(func.sum(Refund.amount_cents), 0)))
    ) or 0
    active_entitlements = (
        await session.scalar(
            select(func.count(Entitlement.id)).where(Entitlement.status == EntitlementStatus.active)
        )
    ) or 0
    failed_payments = (
        await session.scalar(
            select(func.count(Payment.id)).where(Payment.status == PaymentStatus.failed)
        )
    ) or 0

    return AdminRevenueSummary(
        total_successful_payments=total_successful,
        total_revenue_cents=total_revenue,
        total_refunded_cents=total_refunded,
        currency="USD",
        active_entitlements=active_entitlements,
        failed_payments=failed_payments,
    )


@router.get("/ai-usage")
async def ai_usage_summary(
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    rows = (
        await session.execute(
            select(
                AIUsageRecord.feature,
                AIUsageRecord.status,
                func.count(AIUsageRecord.id).label("count"),
            ).group_by(AIUsageRecord.feature, AIUsageRecord.status)
        )
    ).all()
    return [{"feature": row.feature, "status": row.status.value, "count": row.count} for row in rows]


@router.get("/usage-limits", response_model=list[UsageLimitRead])
async def list_usage_limits(
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[UsageLimitRead]:
    limits = (await session.scalars(select(UsageLimit))).all()
    return [UsageLimitRead.model_validate(limit) for limit in limits]


@router.put("/usage-limits", response_model=UsageLimitRead)
async def upsert_usage_limit(
    payload: UsageLimitUpsertRequest,
    user: Annotated[AuthenticatedUser, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UsageLimitRead:
    async with session.begin():
        existing = await session.scalar(
            select(UsageLimit).where(
                UsageLimit.feature == payload.feature, UsageLimit.plan_code == payload.plan_code
            )
        )
        if existing is None:
            existing = UsageLimit(feature=payload.feature, plan_code=payload.plan_code)
            session.add(existing)
        existing.limit_per_day = payload.limit_per_day
        existing.limit_per_month = payload.limit_per_month
        existing.updated_by = user.uid
        existing.updated_at = utc_now()
        await session.flush()
        await session.refresh(existing)
        return UsageLimitRead.model_validate(existing)

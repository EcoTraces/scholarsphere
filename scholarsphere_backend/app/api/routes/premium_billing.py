from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import get_settings
from app.core.entitlements import get_active_entitlement
from app.db.session import get_db
from app.models.premium_billing import Payment, PremiumPlan
from app.schemas.premium_billing import (
    CheckoutRequest,
    CheckoutResponse,
    EntitlementRead,
    MyPremiumStatusRead,
    PaymentRead,
    PremiumPlanRead,
)
from app.services import payment_service
from app.services.payment_provider import PaymentProviderError

router = APIRouter(prefix="/premium", tags=["premium-billing"])

any_authenticated = Depends(get_current_user)


@router.get("/plans", response_model=list[PremiumPlanRead])
async def list_plans(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[PremiumPlanRead]:
    plans = (
        await session.scalars(
            select(PremiumPlan)
            .where(PremiumPlan.is_active.is_(True))
            .order_by(PremiumPlan.sort_order)
        )
    ).all()
    return [PremiumPlanRead.model_validate(plan) for plan in plans]


@router.get("/me", response_model=MyPremiumStatusRead)
async def my_premium_status(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MyPremiumStatusRead:
    entitlement = await get_active_entitlement(session, user.uid)
    plans = (
        await session.scalars(
            select(PremiumPlan)
            .where(PremiumPlan.is_active.is_(True))
            .order_by(PremiumPlan.sort_order)
        )
    ).all()
    return MyPremiumStatusRead(
        is_premium=entitlement is not None,
        entitlement=EntitlementRead.model_validate(entitlement) if entitlement else None,
        available_plans=[PremiumPlanRead.model_validate(plan) for plan in plans],
    )


@router.post("/checkout", response_model=CheckoutResponse, status_code=201)
async def checkout(
    payload: CheckoutRequest,
    request: Request,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> CheckoutResponse:
    correlation_id = getattr(request.state, "correlation_id", "checkout")
    # A PaymentProviderError deliberately leaves a `failed` Payment row (and
    # its audit record) behind for the admin dashboard - raising the
    # HTTPException *inside* `async with session.begin()` would roll that
    # back along with everything else (an unhandled exception exiting the
    # block always rolls back), so the error is captured here and only
    # raised after the block commits normally.
    pending_error: HTTPException | None = None
    payment = None
    result = None
    async with session.begin():
        try:
            payment, result = await payment_service.initiate_checkout(
                session, user_id=user.uid, plan_code=payload.plan_code, correlation_id=correlation_id
            )
        except payment_service.PlanNotFoundError as error:
            pending_error = HTTPException(status_code=404, detail=str(error))
        except PaymentProviderError as error:
            pending_error = HTTPException(status_code=503, detail=str(error))

    if pending_error is not None:
        raise pending_error

    settings = get_settings()
    return CheckoutResponse(
        payment=PaymentRead.model_validate(payment),
        client_secret=result.client_secret,
        checkout_url=result.checkout_url,
        payment_public_key=settings.payment_public_key,
    )


@router.get("/payments/{payment_id}", response_model=PaymentRead)
async def get_payment(
    payment_id: UUID,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentRead:
    payment = await session.get(Payment, payment_id)
    if payment is None or payment.user_id != user.uid:
        raise HTTPException(status_code=404, detail="Payment was not found.")
    return PaymentRead.model_validate(payment)


@router.post("/payments/{payment_id}/verify", response_model=PaymentRead)
async def verify_payment(
    payment_id: UUID,
    request: Request,
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentRead:
    """Explicit server-side re-verification, e.g. after the applicant's

    browser returns from the payment provider's own checkout page. This
    endpoint never trusts anything the client sends about the outcome -
    it re-asks the provider directly (app/services/payment_service.py).
    """
    correlation_id = getattr(request.state, "correlation_id", "verify")
    async with session.begin():
        payment = await session.get(Payment, payment_id)
        if payment is None or payment.user_id != user.uid:
            raise HTTPException(status_code=404, detail="Payment was not found.")
        try:
            payment = await payment_service.verify_payment(
                session, payment=payment, correlation_id=correlation_id
            )
        except PaymentProviderError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return PaymentRead.model_validate(payment)


@router.get("/payments", response_model=list[PaymentRead])
async def list_my_payments(
    user: Annotated[AuthenticatedUser, any_authenticated],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[PaymentRead]:
    payments = (
        await session.scalars(
            select(Payment).where(Payment.user_id == user.uid).order_by(Payment.created_at.desc())
        )
    ).all()
    return [PaymentRead.model_validate(payment) for payment in payments]

"""Payment orchestration: checkout, server-side verification, idempotent

webhook processing, refunds, and entitlement granting/revocation. This is
the only place in the codebase allowed to create an ``Entitlement`` row -
see app/core/entitlements.py's docstring for why that matters.

The flow this module implements, matching the platform spec exactly:

    User selects package
    -> initiate_checkout() creates a Payment row (status=pending) *before*
       the applicant ever reaches the payment provider
    -> User pays through the provider
    -> Provider webhook/callback -> process_webhook_event()
    -> Server verifies the transaction (signature + a live status read,
       never trusting the webhook body's claimed status alone for a
       success transition without also being able to re-verify)
    -> Payment recorded, Entitlement created - only from here does premium
       actually unlock

Nothing in this module ever grants an entitlement because a frontend
request claims success, a URL contains ``success=true``, or a webhook
delivery is unsigned/wrongly signed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditResult
from app.models.premium_billing import (
    BillingInterval,
    Entitlement,
    EntitlementStatus,
    Payment,
    PaymentEvent,
    PaymentStatus,
    PremiumPlan,
    Refund,
    RefundStatus,
    TERMINAL_PAYMENT_STATUSES,
)
from app.services.audit_log import append_audit_record
from app.services.parsing import utc_now
from app.services.payment_provider import (
    PaymentIntentResult,
    PaymentProvider,
    PaymentProviderError,
    WebhookEvent,
    get_payment_provider,
)


class PlanNotFoundError(Exception):
    pass


class PaymentNotFoundError(Exception):
    pass


class InvalidRefundError(Exception):
    pass


async def initiate_checkout(
    session: AsyncSession,
    *,
    user_id: str,
    plan_code: str,
    correlation_id: str,
    provider: PaymentProvider | None = None,
) -> tuple[Payment, PaymentIntentResult]:
    plan = await session.scalar(
        select(PremiumPlan).where(PremiumPlan.code == plan_code, PremiumPlan.is_active.is_(True))
    )
    if plan is None:
        raise PlanNotFoundError(f"No active plan with code '{plan_code}'.")

    payment = Payment(
        id=uuid.uuid4(),
        user_id=user_id,
        plan_id=plan.id,
        amount_cents=plan.price_cents,
        currency=plan.currency,
        status=PaymentStatus.pending,
        provider="",
        idempotency_key=str(uuid.uuid4()),
        payment_metadata={"plan_code": plan.code},
    )
    session.add(payment)
    await session.flush()

    active_provider = provider or get_payment_provider()
    payment.provider = type(active_provider).__name__
    try:
        result = await active_provider.initialize_payment(
            amount_cents=plan.price_cents,
            currency=plan.currency,
            idempotency_key=payment.idempotency_key,
            customer_id=user_id,
            description=f"ScholarSphere Premium: {plan.name}",
            metadata={"plan_code": plan.code, "payment_id": str(payment.id)},
        )
    except PaymentProviderError as error:
        payment.status = PaymentStatus.failed
        payment.failure_reason = str(error)
        await session.flush()
        await append_audit_record(
            session,
            actor_id=user_id,
            actor_role="applicant",
            action=AuditAction.paymentProcessed,
            entity_type="payment",
            entity_id=str(payment.id),
            result=AuditResult.failure,
            correlation_id=correlation_id,
            failure_reason=str(error),
        )
        raise

    payment.provider_transaction_id = result.provider_transaction_id
    payment.status = result.status
    await session.flush()
    await session.refresh(payment)
    await append_audit_record(
        session,
        actor_id=user_id,
        actor_role="applicant",
        action=AuditAction.paymentProcessed,
        entity_type="payment",
        entity_id=str(payment.id),
        result=AuditResult.success,
        correlation_id=correlation_id,
        new_value=f"status={payment.status.value}",
    )
    return payment, result


async def grant_entitlement_for_payment(
    session: AsyncSession, payment: Payment, *, correlation_id: str
) -> Entitlement:
    """Idempotent: a second call for the same payment (e.g. a duplicate

    webhook delivery that somehow got past PaymentEvent's own unique
    constraint, or a race between two concurrent verify calls) returns the
    already-granted entitlement rather than creating a second one -
    Entitlement.source_payment_id's own unique constraint is the final
    backstop.
    """
    existing = await session.scalar(
        select(Entitlement).where(Entitlement.source_payment_id == payment.id)
    )
    if existing is not None:
        return existing

    plan = await session.get(PremiumPlan, payment.plan_id)
    if plan is None:
        raise PlanNotFoundError(f"Plan {payment.plan_id} referenced by payment no longer exists.")

    expires_at: datetime | None = None
    if plan.billing_interval == BillingInterval.monthly:
        expires_at = utc_now() + timedelta(days=31)
    elif plan.billing_interval == BillingInterval.yearly:
        expires_at = utc_now() + timedelta(days=366)

    entitlement = Entitlement(
        id=uuid.uuid4(),
        user_id=payment.user_id,
        plan_id=plan.id,
        feature_keys=list(plan.features),
        source_payment_id=payment.id,
        status=EntitlementStatus.active,
        expires_at=expires_at,
    )
    session.add(entitlement)
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError:
        existing = await session.scalar(
            select(Entitlement).where(Entitlement.source_payment_id == payment.id)
        )
        if existing is not None:
            return existing
        raise
    await session.refresh(entitlement)

    await append_audit_record(
        session,
        actor_id=payment.user_id,
        actor_role="system",
        action=AuditAction.entitlementChanged,
        entity_type="entitlement",
        entity_id=str(entitlement.id),
        result=AuditResult.success,
        correlation_id=correlation_id,
        new_value=f"granted plan={plan.code} source_payment={payment.id}",
    )
    return entitlement


async def _apply_terminal_status(
    session: AsyncSession, payment: Payment, new_status: PaymentStatus, *, correlation_id: str
) -> None:
    if payment.status in TERMINAL_PAYMENT_STATUSES:
        return
    payment.status = new_status
    await session.flush()
    if new_status == PaymentStatus.success:
        await grant_entitlement_for_payment(session, payment, correlation_id=correlation_id)
    await append_audit_record(
        session,
        actor_id=payment.user_id,
        actor_role="system",
        action=AuditAction.paymentProcessed,
        entity_type="payment",
        entity_id=str(payment.id),
        result=AuditResult.success if new_status == PaymentStatus.success else AuditResult.failure,
        correlation_id=correlation_id,
        new_value=f"status={new_status.value}",
    )


async def verify_payment(
    session: AsyncSession,
    *,
    payment: Payment,
    correlation_id: str,
    provider: PaymentProvider | None = None,
) -> Payment:
    """Explicit server-side re-verification (e.g. the applicant's browser

    returns to a "payment complete" page - that page's own claim is never
    trusted; this function re-asks the provider directly).
    """
    if payment.status in TERMINAL_PAYMENT_STATUSES or not payment.provider_transaction_id:
        return payment
    active_provider = provider or get_payment_provider()
    result = await active_provider.verify_payment(
        provider_transaction_id=payment.provider_transaction_id
    )
    await _apply_terminal_status(session, payment, result.status, correlation_id=correlation_id)
    return payment


async def process_webhook_event(
    session: AsyncSession,
    *,
    provider_name: str,
    raw_body: bytes,
    signature_header: str,
    parsed_body: dict,
    correlation_id: str,
    provider: PaymentProvider | None = None,
) -> str:
    """Returns a short, safe processing-result string for logging/response

    purposes. Never raises for a duplicate delivery - that is the
    successful, idempotent case, not an error.
    """
    active_provider = provider or get_payment_provider()
    if not active_provider.verify_webhook_signature(
        payload=raw_body, signature_header=signature_header
    ):
        raise PaymentProviderError("Webhook signature verification failed.")

    event: WebhookEvent = active_provider.parse_webhook_event(
        payload=raw_body, parsed_body=parsed_body
    )

    payment_event = PaymentEvent(
        id=uuid.uuid4(),
        provider=provider_name,
        provider_event_id=event.provider_event_id,
        event_type=event.event_type,
        raw_payload=parsed_body,
    )
    session.add(payment_event)
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError:
        # A second delivery of an event already recorded - this is
        # PaymentEvent's own unique constraint doing its job. Idempotent
        # no-op: no entitlement is created twice from here.
        return "duplicate_event_ignored"

    payment = None
    if event.provider_transaction_id:
        payment = await session.scalar(
            select(Payment).where(Payment.provider_transaction_id == event.provider_transaction_id)
        )

    if payment is None:
        payment_event.processing_result = "payment_not_found"
        payment_event.processed_at = utc_now()
        await session.flush()
        return "payment_not_found"

    payment_event.payment_id = payment.id
    if event.status is not None:
        await _apply_terminal_status(session, payment, event.status, correlation_id=correlation_id)
    payment_event.processing_result = "applied"
    payment_event.processed_at = utc_now()
    await session.flush()
    return "applied"


async def refund_payment(
    session: AsyncSession,
    *,
    payment: Payment,
    amount_cents: int,
    reason: str,
    actor_id: str,
    correlation_id: str,
    provider: PaymentProvider | None = None,
) -> Refund:
    if payment.status != PaymentStatus.success:
        raise InvalidRefundError("Only a successfully completed payment can be refunded.")
    if amount_cents <= 0 or amount_cents > payment.amount_cents:
        raise InvalidRefundError("Refund amount must be between 1 and the original payment amount.")

    active_provider = provider or get_payment_provider()
    result = await active_provider.refund_payment(
        provider_transaction_id=payment.provider_transaction_id or "",
        amount_cents=amount_cents,
        reason=reason,
    )
    status = (
        RefundStatus.succeeded
        if result.status == "succeeded"
        else RefundStatus.pending
        if result.status in {"pending", "requires_action"}
        else RefundStatus.failed
    )
    refund = Refund(
        id=uuid.uuid4(),
        payment_id=payment.id,
        amount_cents=amount_cents,
        reason=reason,
        status=status,
        provider_refund_id=result.provider_refund_id,
        created_by=actor_id,
    )
    session.add(refund)

    if status == RefundStatus.succeeded:
        payment.status = PaymentStatus.refunded
        entitlements = (
            await session.scalars(
                select(Entitlement)
                .where(Entitlement.source_payment_id == payment.id)
                .where(Entitlement.status == EntitlementStatus.active)
            )
        ).all()
        for entitlement in entitlements:
            entitlement.status = EntitlementStatus.revoked
            entitlement.revoked_at = utc_now()
            entitlement.revoked_reason = "Payment refunded."

    await session.flush()
    await session.refresh(refund)
    await append_audit_record(
        session,
        actor_id=actor_id,
        actor_role="administrator",
        action=AuditAction.paymentProcessed,
        entity_type="refund",
        entity_id=str(refund.id),
        result=AuditResult.success if status == RefundStatus.succeeded else AuditResult.failure,
        correlation_id=correlation_id,
        new_value=f"refund status={status.value} payment={payment.id}",
    )
    return refund

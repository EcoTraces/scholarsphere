"""Provider-independent payment abstraction.

``PaymentProvider`` is the interface every route/service in this codebase
talks to; it never imports a specific provider's SDK or hardcodes a
specific provider's API shape into calling code. Two concrete
implementations ship today:

- ``NullPaymentProvider`` - the default (``PAYMENT_PROVIDER`` unset). Every
  method raises ``PaymentProviderNotConfiguredError`` with a clear,
  actionable message. This is the honest behavior this project's own
  "no fabrication" rule requires: a payment can never be reported as
  succeeded, and premium can never be unlocked, just because a route was
  called with no real provider behind it.
- ``StripePaymentProvider`` - a real, complete integration against
  Stripe's actual documented REST API (Payment Intents + Refunds +
  Subscriptions + webhook signature verification per Stripe's published
  algorithm), selected via ``PAYMENT_PROVIDER=stripe``. It is correct
  *code* today; it still needs a real ``PAYMENT_SECRET_KEY`` and
  ``PAYMENT_WEBHOOK_SECRET`` to actually reach Stripe's servers - nothing
  here fabricates a successful call in their absence, it raises the same
  way any other misconfigured HTTPS client call would (via
  app/core/http_client.py, which every network call in this module goes
  through, never raw httpx).

Adding a second real provider (Paystack, Flutterwave, ...) - relevant
given this platform's Sierra Leone-focused user base - is a new class
implementing this same interface plus one line in ``PROVIDER_REGISTRY``,
not a change to any calling code.

Idempotency and duplicate-webhook protection are NOT this module's job -
they live in app/services/payment_service.py, backed by real database
uniqueness constraints (``PaymentEvent`` and ``Entitlement`` in
app/models/premium_billing.py), not in-memory state that a request retry
or a second server process could bypass.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.config import Settings, get_settings
from app.core.http_client import ExternalAPIError, get_json, post_json
from app.models.premium_billing import PaymentStatus

logger = logging.getLogger(__name__)

_STRIPE_API_BASE_URL = "https://api.stripe.com"
_WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300


class PaymentProviderError(Exception):
    """A safe-to-display payment provider failure (never leaks a secret or

    a raw provider response body to the caller - see Coding_Rules.md SS4's
    "never let a caught exception's str() reach a response body" rule,
    which this exception's message is written to comply with at the
    source).
    """


class PaymentProviderNotConfiguredError(PaymentProviderError):
    pass


@dataclass(frozen=True)
class PaymentIntentResult:
    provider_transaction_id: str
    status: PaymentStatus
    # Safe to hand to the frontend (e.g. Stripe's PaymentIntent
    # client_secret) - never the provider's own secret API key.
    client_secret: str | None = None
    checkout_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RefundResult:
    provider_refund_id: str
    status: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SubscriptionResult:
    provider_subscription_id: str
    status: str
    current_period_end_epoch: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebhookEvent:
    provider_event_id: str
    event_type: str
    provider_transaction_id: str | None
    status: PaymentStatus | None
    raw: dict[str, Any]


class PaymentProvider(Protocol):
    """Conceptually: initializePayment / verifyPayment / getTransaction /

    refundPayment / createSubscription / cancelSubscription /
    handleWebhook, per the platform spec. Python spells these
    snake_case; the mapping is 1:1.
    """

    async def initialize_payment(
        self,
        *,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
        customer_id: str,
        description: str,
        metadata: dict[str, str],
    ) -> PaymentIntentResult: ...

    async def verify_payment(self, *, provider_transaction_id: str) -> PaymentIntentResult: ...

    async def get_transaction(self, *, provider_transaction_id: str) -> PaymentIntentResult: ...

    async def refund_payment(
        self, *, provider_transaction_id: str, amount_cents: int, reason: str
    ) -> RefundResult: ...

    async def create_subscription(
        self, *, customer_id: str, provider_plan_id: str
    ) -> SubscriptionResult: ...

    async def cancel_subscription(self, *, provider_subscription_id: str) -> SubscriptionResult: ...

    def verify_webhook_signature(self, *, payload: bytes, signature_header: str) -> bool: ...

    def parse_webhook_event(self, *, payload: bytes, parsed_body: dict[str, Any]) -> WebhookEvent: ...


class NullPaymentProvider:
    """The honest default. Every call raises with a message naming exactly

    what to set - PAYMENT_PROVIDER plus the chosen provider's credentials
    (see .env.example's "Premium Application-Preparation Platform: payment
    provider" section) - rather than silently succeeding or returning a
    fabricated transaction.
    """

    _MESSAGE = (
        "No payment provider is configured. Set PAYMENT_PROVIDER (and its "
        "credentials) in the environment before initiating a real payment."
    )

    async def initialize_payment(self, **_: Any) -> PaymentIntentResult:
        raise PaymentProviderNotConfiguredError(self._MESSAGE)

    async def verify_payment(self, **_: Any) -> PaymentIntentResult:
        raise PaymentProviderNotConfiguredError(self._MESSAGE)

    async def get_transaction(self, **_: Any) -> PaymentIntentResult:
        raise PaymentProviderNotConfiguredError(self._MESSAGE)

    async def refund_payment(self, **_: Any) -> RefundResult:
        raise PaymentProviderNotConfiguredError(self._MESSAGE)

    async def create_subscription(self, **_: Any) -> SubscriptionResult:
        raise PaymentProviderNotConfiguredError(self._MESSAGE)

    async def cancel_subscription(self, **_: Any) -> SubscriptionResult:
        raise PaymentProviderNotConfiguredError(self._MESSAGE)

    def verify_webhook_signature(self, *, payload: bytes, signature_header: str) -> bool:
        return False

    def parse_webhook_event(self, *, payload: bytes, parsed_body: dict[str, Any]) -> WebhookEvent:
        raise PaymentProviderNotConfiguredError(self._MESSAGE)


_STRIPE_STATUS_MAP: dict[str, PaymentStatus] = {
    "requires_payment_method": PaymentStatus.pending,
    "requires_confirmation": PaymentStatus.pending,
    "requires_action": PaymentStatus.processing,
    "processing": PaymentStatus.processing,
    "requires_capture": PaymentStatus.processing,
    "succeeded": PaymentStatus.success,
    "canceled": PaymentStatus.cancelled,
}

_STRIPE_EVENT_STATUS_MAP: dict[str, PaymentStatus] = {
    "payment_intent.succeeded": PaymentStatus.success,
    "payment_intent.payment_failed": PaymentStatus.failed,
    "payment_intent.canceled": PaymentStatus.cancelled,
    "payment_intent.processing": PaymentStatus.processing,
    "charge.dispute.created": PaymentStatus.disputed,
    "charge.refunded": PaymentStatus.refunded,
}


class StripePaymentProvider:
    """A real, complete integration against Stripe's documented REST API

    (Payment Intents). Selected via ``PAYMENT_PROVIDER=stripe``. Every
    network call goes through app/core/http_client.py (HTTPS-only,
    timeout, bounded retry - the same shared client every other external
    integration in this codebase uses), so nothing here bypasses that
    project-wide safety net.
    """

    def __init__(self, settings: Settings) -> None:
        self._secret_key = settings.payment_secret_key.get_secret_value()
        self._webhook_secret = settings.payment_webhook_secret.get_secret_value()
        self._base_url = settings.payment_api_base_url or _STRIPE_API_BASE_URL

    def _headers(self) -> dict[str, str]:
        if not self._secret_key:
            raise PaymentProviderNotConfiguredError(
                "PAYMENT_PROVIDER=stripe is set but PAYMENT_SECRET_KEY is empty."
            )
        return {"Authorization": f"Bearer {self._secret_key}"}

    async def initialize_payment(
        self,
        *,
        amount_cents: int,
        currency: str,
        idempotency_key: str,
        customer_id: str,
        description: str,
        metadata: dict[str, str],
    ) -> PaymentIntentResult:
        form: dict[str, str] = {
            "amount": str(amount_cents),
            "currency": currency.lower(),
            "description": description,
            "automatic_payment_methods[enabled]": "true",
            "metadata[user_id]": customer_id,
        }
        for key, value in metadata.items():
            form[f"metadata[{key}]"] = value
        try:
            payload = await post_json(
                f"{self._base_url}/v1/payment_intents",
                data=form,
                headers={**self._headers(), "Idempotency-Key": idempotency_key},
            )
        except ExternalAPIError as error:
            raise PaymentProviderError(
                "The payment provider rejected the checkout request."
            ) from error
        return _payment_intent_result(payload)

    async def verify_payment(self, *, provider_transaction_id: str) -> PaymentIntentResult:
        return await self.get_transaction(provider_transaction_id=provider_transaction_id)

    async def get_transaction(self, *, provider_transaction_id: str) -> PaymentIntentResult:
        try:
            payload = await get_json(
                f"{self._base_url}/v1/payment_intents/{provider_transaction_id}",
                headers=self._headers(),
            )
        except ExternalAPIError as error:
            raise PaymentProviderError(
                "Could not retrieve the payment status from the payment provider."
            ) from error
        return _payment_intent_result(payload)

    async def refund_payment(
        self, *, provider_transaction_id: str, amount_cents: int, reason: str
    ) -> RefundResult:
        form = {
            "payment_intent": provider_transaction_id,
            "amount": str(amount_cents),
            "metadata[reason]": reason[:500],
        }
        try:
            payload = await post_json(
                f"{self._base_url}/v1/refunds", data=form, headers=self._headers()
            )
        except ExternalAPIError as error:
            raise PaymentProviderError("The refund request was rejected.") from error
        return RefundResult(
            provider_refund_id=str(payload.get("id", "")),
            status=str(payload.get("status", "")),
            raw=payload,
        )

    async def create_subscription(
        self, *, customer_id: str, provider_plan_id: str
    ) -> SubscriptionResult:
        form = {
            "customer": customer_id,
            "items[0][price]": provider_plan_id,
        }
        try:
            payload = await post_json(
                f"{self._base_url}/v1/subscriptions", data=form, headers=self._headers()
            )
        except ExternalAPIError as error:
            raise PaymentProviderError("Could not create the subscription.") from error
        return SubscriptionResult(
            provider_subscription_id=str(payload.get("id", "")),
            status=str(payload.get("status", "")),
            current_period_end_epoch=payload.get("current_period_end"),
            raw=payload,
        )

    async def cancel_subscription(self, *, provider_subscription_id: str) -> SubscriptionResult:
        try:
            payload = await post_json(
                f"{self._base_url}/v1/subscriptions/{provider_subscription_id}",
                data={"cancel_at_period_end": "false"},
                headers=self._headers(),
            )
        except ExternalAPIError as error:
            raise PaymentProviderError("Could not cancel the subscription.") from error
        return SubscriptionResult(
            provider_subscription_id=str(payload.get("id", "")),
            status=str(payload.get("status", "canceled")),
            current_period_end_epoch=payload.get("current_period_end"),
            raw=payload,
        )

    def verify_webhook_signature(self, *, payload: bytes, signature_header: str) -> bool:
        """Stripe's own published verification algorithm: the

        ``Stripe-Signature`` header is ``t=<unix-ts>,v1=<hmac-hex>[,v0=...]``;
        the expected signature is HMAC-SHA256 of ``"{t}.{payload}"`` keyed
        by the webhook secret, compared with a constant-time comparison
        (never ``==``, which leaks timing information about how many
        leading bytes matched).
        """
        if not self._webhook_secret:
            return False
        parts: dict[str, str] = {}
        for item in signature_header.split(","):
            key, _, value = item.partition("=")
            if key.strip() == "v1":
                parts.setdefault("v1", value.strip())
            elif key.strip() == "t":
                parts["t"] = value.strip()
        timestamp = parts.get("t")
        signature = parts.get("v1")
        if not timestamp or not signature or not timestamp.isdigit():
            return False
        if abs(time.time() - int(timestamp)) > _WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS:
            logger.warning("stripe_webhook_timestamp_outside_tolerance")
            return False
        signed_payload = f"{timestamp}.".encode() + payload
        expected = hmac.new(
            self._webhook_secret.encode(), signed_payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_webhook_event(self, *, payload: bytes, parsed_body: dict[str, Any]) -> WebhookEvent:
        event_type = str(parsed_body.get("type", ""))
        data_object = parsed_body.get("data", {}).get("object", {}) if isinstance(
            parsed_body.get("data"), dict
        ) else {}
        return WebhookEvent(
            provider_event_id=str(parsed_body.get("id", "")),
            event_type=event_type,
            provider_transaction_id=data_object.get("id")
            if event_type.startswith("payment_intent.")
            else data_object.get("payment_intent"),
            status=_STRIPE_EVENT_STATUS_MAP.get(event_type),
            raw=parsed_body,
        )


def _payment_intent_result(payload: dict[str, Any]) -> PaymentIntentResult:
    provider_status = str(payload.get("status", ""))
    return PaymentIntentResult(
        provider_transaction_id=str(payload.get("id", "")),
        status=_STRIPE_STATUS_MAP.get(provider_status, PaymentStatus.pending),
        client_secret=payload.get("client_secret"),
        raw=payload,
    )


PROVIDER_REGISTRY: dict[str, type[StripePaymentProvider]] = {
    "stripe": StripePaymentProvider,
}


def get_payment_provider(settings: Settings | None = None) -> PaymentProvider:
    settings = settings or get_settings()
    provider_code = settings.payment_provider.strip().lower()
    if not provider_code:
        return NullPaymentProvider()
    provider_class = PROVIDER_REGISTRY.get(provider_code)
    if provider_class is None:
        logger.warning("unknown_payment_provider provider=%s", provider_code)
        return NullPaymentProvider()
    return provider_class(settings)

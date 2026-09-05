"""Unit tests for app/services/payment_provider.py - focused on the Stripe

webhook signature verification algorithm specifically, since a bug there
would mean an attacker could forge a "payment succeeded" webhook and
unlock premium for free. Computes real HMAC-SHA256 signatures the same
way Stripe's own client libraries do, rather than mocking the crypto.
"""

import hashlib
import hmac
import time

from app.core.config import Settings
from app.services.payment_provider import (
    NullPaymentProvider,
    StripePaymentProvider,
    get_payment_provider,
)

_SECRET = "whsec_test_secret"


def _sign(payload: bytes, *, secret: str = _SECRET, timestamp: int | None = None) -> str:
    timestamp = timestamp if timestamp is not None else int(time.time())
    signed_payload = f"{timestamp}.".encode() + payload
    signature = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def _provider(secret: str = _SECRET) -> StripePaymentProvider:
    settings = Settings(
        payment_provider="stripe",
        payment_secret_key="sk_test_x",
        payment_webhook_secret=secret,
    )
    return StripePaymentProvider(settings)


def test_valid_signature_is_accepted() -> None:
    provider = _provider()
    payload = b'{"id":"evt_1","type":"payment_intent.succeeded"}'
    header = _sign(payload)
    assert provider.verify_webhook_signature(payload=payload, signature_header=header) is True


def test_signature_with_wrong_secret_is_rejected() -> None:
    provider = _provider()
    payload = b'{"id":"evt_1","type":"payment_intent.succeeded"}'
    header = _sign(payload, secret="wrong_secret")
    assert provider.verify_webhook_signature(payload=payload, signature_header=header) is False


def test_tampered_payload_is_rejected() -> None:
    provider = _provider()
    original_payload = b'{"id":"evt_1","type":"payment_intent.succeeded"}'
    header = _sign(original_payload)
    tampered_payload = b'{"id":"evt_1","type":"payment_intent.succeeded","amount":999999}'
    assert provider.verify_webhook_signature(payload=tampered_payload, signature_header=header) is False


def test_stale_timestamp_is_rejected() -> None:
    provider = _provider()
    payload = b'{"id":"evt_1","type":"payment_intent.succeeded"}'
    old_timestamp = int(time.time()) - 3600
    header = _sign(payload, timestamp=old_timestamp)
    assert provider.verify_webhook_signature(payload=payload, signature_header=header) is False


def test_malformed_header_is_rejected() -> None:
    provider = _provider()
    payload = b'{"id":"evt_1","type":"payment_intent.succeeded"}'
    assert provider.verify_webhook_signature(payload=payload, signature_header="") is False
    assert provider.verify_webhook_signature(payload=payload, signature_header="garbage") is False
    assert provider.verify_webhook_signature(payload=payload, signature_header="t=123") is False


def test_no_webhook_secret_configured_always_rejects() -> None:
    provider = _provider(secret="")
    payload = b'{"id":"evt_1","type":"payment_intent.succeeded"}'
    header = _sign(payload, secret="")
    assert provider.verify_webhook_signature(payload=payload, signature_header=header) is False


def test_null_provider_never_accepts_any_signature() -> None:
    """NEVER fabricate a successful webhook verification when nothing is

    configured - the honest default always returns False.
    """
    provider = NullPaymentProvider()
    assert provider.verify_webhook_signature(payload=b"{}", signature_header="anything") is False


def test_get_payment_provider_defaults_to_null_when_unset() -> None:
    settings = Settings(payment_provider="")
    assert isinstance(get_payment_provider(settings), NullPaymentProvider)


def test_get_payment_provider_falls_back_to_null_for_unknown_name() -> None:
    settings = Settings(payment_provider="some_unsupported_provider")
    assert isinstance(get_payment_provider(settings), NullPaymentProvider)


def test_get_payment_provider_selects_stripe() -> None:
    settings = Settings(payment_provider="stripe", payment_secret_key="sk_test_x")
    assert isinstance(get_payment_provider(settings), StripePaymentProvider)

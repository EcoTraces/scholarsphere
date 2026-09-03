"""Route-level tests for the premium billing/checkout/webhook flow -

covers the platform spec's explicitly required critical tests: a failed
payment never creates an entitlement, and a duplicate webhook delivery
never creates a duplicate entitlement. app/services/payment_service.py's
own idempotency/entitlement-granting logic is exercised end-to-end
through the real HTTP routes here, not mocked out.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.audit_log import AuditRecord, AuditResult
from app.models.premium_billing import (
    BillingInterval,
    Entitlement,
    EntitlementStatus,
    Payment,
    PaymentEvent,
    PaymentStatus,
    PremiumFeature,
    PremiumPlan,
    Refund,
    RefundStatus,
)
from app.services import payment_service
from app.services.payment_provider import PaymentIntentResult, PaymentProviderError, RefundResult, WebhookEvent


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


def user(role: str = "applicant", uid: str = "applicant-1") -> AuthenticatedUser:
    return AuthenticatedUser(
        uid=uid, email=f"{uid}@example.test", email_verified=True, role=role, permissions=frozenset()
    )


def overrides(session: AsyncSession, *, uid: str = "applicant-1", role: str = "applicant") -> None:
    async def current_user() -> AuthenticatedUser:
        return user(role, uid)

    async def database() -> AsyncIterator[AsyncSession]:
        # Mirrors app/db/session.py::get_db's own try/finally - a request
        # that raises must still close out its transaction (a route that
        # never explicitly opens/commits one still leaves SQLAlchemy's
        # "autobegin" transaction open) before this shared,
        # reused-across-requests test session serves the next request
        # (production never hits this: every real request gets its own
        # fresh AsyncSessionFactory() session).
        try:
            yield session
        finally:
            await session.rollback()

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db] = database


class StubProvider:
    def __init__(self, *, checkout_status: PaymentStatus = PaymentStatus.pending) -> None:
        self.checkout_status = checkout_status
        self.transaction_id = f"pi_{uuid.uuid4().hex[:12]}"

    async def initialize_payment(self, **kwargs):
        return PaymentIntentResult(
            provider_transaction_id=self.transaction_id,
            status=self.checkout_status,
            client_secret="secret_stub",
        )

    async def verify_payment(self, **kwargs):
        return PaymentIntentResult(
            provider_transaction_id=self.transaction_id, status=PaymentStatus.success
        )

    async def get_transaction(self, **kwargs):
        return await self.verify_payment(**kwargs)

    async def refund_payment(self, **kwargs):
        return RefundResult(provider_refund_id="re_stub", status="succeeded")

    def verify_webhook_signature(self, *, payload, signature_header) -> bool:
        return signature_header == "valid-signature"

    def parse_webhook_event(self, *, payload, parsed_body):
        return WebhookEvent(
            provider_event_id=parsed_body["id"],
            event_type=parsed_body["type"],
            provider_transaction_id=self.transaction_id,
            status=PaymentStatus.success
            if parsed_body["type"] == "payment_intent.succeeded"
            else PaymentStatus.failed,
            raw=parsed_body,
        )


class FailingInitProvider(StubProvider):
    async def initialize_payment(self, **kwargs):
        from app.services.payment_provider import PaymentProviderError

        raise PaymentProviderError("The payment provider rejected the checkout request.")


class FailingRefundProvider(StubProvider):
    async def refund_payment(self, **kwargs):
        raise PaymentProviderError("The refund request was rejected.")


async def _seed_plan(session: AsyncSession) -> PremiumPlan:
    plan = PremiumPlan(
        id=uuid.uuid4(),
        code="complete_premium",
        name="Complete Premium",
        description="",
        price_cents=10000,
        currency="USD",
        billing_interval=BillingInterval.one_time,
        features=[f.value for f in PremiumFeature],
        is_active=True,
    )
    session.add(plan)
    await session.commit()
    return plan


@pytest.mark.asyncio
async def test_list_plans_and_my_status_free_user(session: AsyncSession) -> None:
    await _seed_plan(session)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        plans = await client.get("/api/v1/premium/plans")
        assert plans.status_code == 200
        assert len(plans.json()) == 1
        assert plans.json()[0]["price_cents"] == 10000

        status = await client.get("/api/v1/premium/me")
        assert status.status_code == 200
        assert status.json()["is_premium"] is False
        assert status.json()["entitlement"] is None


@pytest.mark.asyncio
async def test_checkout_without_configured_provider_returns_503(session: AsyncSession) -> None:
    await _seed_plan(session)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/premium/checkout", json={"plan_code": "complete_premium"})
        assert response.status_code == 503
        assert "no payment provider is configured" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_checkout_unknown_plan_returns_404(session: AsyncSession, monkeypatch) -> None:
    await _seed_plan(session)
    monkeypatch.setattr(payment_service, "get_payment_provider", lambda: StubProvider())
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/premium/checkout", json={"plan_code": "does-not-exist"})
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_failed_payment_never_creates_entitlement(session: AsyncSession, monkeypatch) -> None:
    """CRITICAL: FAILED PAYMENT -> entitlement NOT created."""
    await _seed_plan(session)
    provider = FailingInitProvider()
    monkeypatch.setattr(payment_service, "get_payment_provider", lambda: provider)
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/premium/checkout", json={"plan_code": "complete_premium"})
        assert response.status_code == 503

    entitlements = (await session.execute(Entitlement.__table__.select())).fetchall()
    assert entitlements == []
    payments = (await session.execute(Payment.__table__.select())).fetchall()
    assert len(payments) == 1
    assert payments[0].status == "failed"


@pytest.mark.asyncio
async def test_checkout_then_webhook_success_grants_entitlement(
    session: AsyncSession, monkeypatch
) -> None:
    await _seed_plan(session)
    provider = StubProvider()
    monkeypatch.setattr(payment_service, "get_payment_provider", lambda: provider)
    overrides(session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        checkout = await client.post("/api/v1/premium/checkout", json={"plan_code": "complete_premium"})
        assert checkout.status_code == 201
        payment_id = checkout.json()["payment"]["id"]
        assert checkout.json()["client_secret"] == "secret_stub"

        status_before = await client.get("/api/v1/premium/me")
        assert status_before.json()["is_premium"] is False

        webhook = await client.post(
            "/api/v1/premium/webhooks/stripe",
            json={"id": "evt_1", "type": "payment_intent.succeeded"},
            headers={"Stripe-Signature": "valid-signature"},
        )
        assert webhook.status_code == 200
        assert webhook.json()["result"] == "applied"

        status_after = await client.get("/api/v1/premium/me")
        assert status_after.json()["is_premium"] is True
        assert PremiumFeature.cv_builder.value in status_after.json()["entitlement"]["feature_keys"]

        payment = await client.get(f"/api/v1/premium/payments/{payment_id}")
        assert payment.json()["status"] == "success"


@pytest.mark.asyncio
async def test_duplicate_webhook_never_creates_duplicate_entitlement(
    session: AsyncSession, monkeypatch
) -> None:
    """CRITICAL: DUPLICATE WEBHOOK -> duplicate entitlement NOT created."""
    await _seed_plan(session)
    provider = StubProvider()
    monkeypatch.setattr(payment_service, "get_payment_provider", lambda: provider)
    overrides(session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/premium/checkout", json={"plan_code": "complete_premium"})
        webhook_body = {"id": "evt_dup", "type": "payment_intent.succeeded"}
        first = await client.post(
            "/api/v1/premium/webhooks/stripe", json=webhook_body, headers={"Stripe-Signature": "valid-signature"}
        )
        assert first.status_code == 200
        assert first.json()["result"] == "applied"

        second = await client.post(
            "/api/v1/premium/webhooks/stripe", json=webhook_body, headers={"Stripe-Signature": "valid-signature"}
        )
        assert second.status_code == 200
        assert second.json()["result"] == "duplicate_event_ignored"

    entitlements = (await session.execute(Entitlement.__table__.select())).fetchall()
    assert len(entitlements) == 1
    events = (await session.execute(PaymentEvent.__table__.select())).fetchall()
    assert len(events) == 1


@pytest.mark.asyncio
async def test_webhook_bad_signature_is_rejected(session: AsyncSession, monkeypatch) -> None:
    await _seed_plan(session)
    provider = StubProvider()
    monkeypatch.setattr(payment_service, "get_payment_provider", lambda: provider)
    overrides(session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/premium/webhooks/stripe",
            json={"id": "evt_bad", "type": "payment_intent.succeeded"},
            headers={"Stripe-Signature": "wrong"},
        )
        assert response.status_code == 400

    events = (await session.execute(PaymentEvent.__table__.select())).fetchall()
    assert events == []


@pytest.mark.asyncio
async def test_expired_entitlement_is_not_premium(session: AsyncSession) -> None:
    plan = await _seed_plan(session)
    entitlement = Entitlement(
        id=uuid.uuid4(),
        user_id="applicant-1",
        plan_id=plan.id,
        feature_keys=[f.value for f in PremiumFeature],
        status=EntitlementStatus.active,
        expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    session.add(entitlement)
    await session.commit()
    overrides(session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/premium/me")
        assert response.json()["is_premium"] is False


@pytest.mark.asyncio
async def test_refund_revokes_entitlement(session: AsyncSession, monkeypatch) -> None:
    plan = await _seed_plan(session)
    payment = Payment(
        id=uuid.uuid4(),
        user_id="applicant-1",
        plan_id=plan.id,
        amount_cents=10000,
        currency="USD",
        status=PaymentStatus.success,
        provider="StubProvider",
        provider_transaction_id="pi_refund_test",
        idempotency_key=str(uuid.uuid4()),
    )
    session.add(payment)
    await session.flush()
    entitlement = Entitlement(
        id=uuid.uuid4(),
        user_id="applicant-1",
        plan_id=plan.id,
        feature_keys=[f.value for f in PremiumFeature],
        source_payment_id=payment.id,
        status=EntitlementStatus.active,
    )
    session.add(entitlement)
    await session.commit()

    provider = StubProvider()
    monkeypatch.setattr(payment_service, "get_payment_provider", lambda: provider)
    overrides(session, uid="admin-1", role="administrator")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/premium/admin/payments/{payment.id}/refund",
            json={"amount_cents": 10000, "reason": "Applicant requested a refund."},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "succeeded"

    await session.refresh(entitlement)
    assert entitlement.status == "revoked"


@pytest.mark.asyncio
async def test_failed_refund_attempt_still_leaves_an_audit_trail(
    session: AsyncSession, monkeypatch
) -> None:
    """Regression test: a `PaymentProviderError` raised by the payment

    provider's own `refund_payment` call used to propagate with no trace
    left behind at all - no `Refund` row, no audit record - unlike every
    other failure path in this module (e.g. `initiate_checkout`'s own
    failure handling), so an admin's failed refund attempt was invisible
    to any later audit. The entitlement/payment must also be left
    untouched, since the refund never actually succeeded.
    """
    plan = await _seed_plan(session)
    payment = Payment(
        id=uuid.uuid4(),
        user_id="applicant-1",
        plan_id=plan.id,
        amount_cents=10000,
        currency="USD",
        status=PaymentStatus.success,
        provider="StubProvider",
        provider_transaction_id="pi_refund_fail_test",
        idempotency_key=str(uuid.uuid4()),
    )
    session.add(payment)
    await session.flush()
    entitlement = Entitlement(
        id=uuid.uuid4(),
        user_id="applicant-1",
        plan_id=plan.id,
        feature_keys=[f.value for f in PremiumFeature],
        source_payment_id=payment.id,
        status=EntitlementStatus.active,
    )
    session.add(entitlement)
    await session.commit()

    provider = FailingRefundProvider()
    monkeypatch.setattr(payment_service, "get_payment_provider", lambda: provider)
    overrides(session, uid="admin-1", role="administrator")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/premium/admin/payments/{payment.id}/refund",
            json={"amount_cents": 10000, "reason": "Applicant requested a refund."},
        )
        assert response.status_code == 503

    refunds = (await session.scalars(select(Refund).where(Refund.payment_id == payment.id))).all()
    assert len(refunds) == 1
    assert refunds[0].status == RefundStatus.failed

    audits = (
        await session.scalars(
            select(AuditRecord).where(AuditRecord.entity_id == str(refunds[0].id))
        )
    ).all()
    assert len(audits) == 1
    assert audits[0].result == AuditResult.failure

    await session.refresh(payment)
    await session.refresh(entitlement)
    assert payment.status == PaymentStatus.success
    assert entitlement.status == EntitlementStatus.active

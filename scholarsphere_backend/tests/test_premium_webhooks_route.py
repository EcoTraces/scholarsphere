"""Dedicated route-file test for app/api/routes/premium_webhooks.py -

the success/duplicate/bad-signature paths through a configured provider
are already covered end-to-end in test_premium_billing_route.py (which
also exercises the checkout that produces the payment being verified);
this file covers premium_webhooks.py's own request-shape handling and its
behavior with no provider configured at all.
"""

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


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


def overrides(session: AsyncSession) -> None:
    async def database() -> AsyncIterator[AsyncSession]:
        try:
            yield session
        finally:
            await session.rollback()

    app.dependency_overrides[get_db] = database


@pytest.mark.asyncio
async def test_webhook_is_unauthenticated_but_still_rejects_bad_json(session: AsyncSession) -> None:
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/premium/webhooks/stripe",
            content=b"not json",
            headers={"Content-Type": "application/json", "Stripe-Signature": "whatever"},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_rejects_non_object_json_body(session: AsyncSession) -> None:
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/premium/webhooks/stripe",
            json=["not", "an", "object"],
            headers={"Stripe-Signature": "whatever"},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_webhook_with_no_provider_configured_is_rejected(session: AsyncSession) -> None:
    """Without PAYMENT_PROVIDER set, NullPaymentProvider.verify_webhook_signature

    always returns False - never treats an unconfigured provider as an
    automatic pass.
    """
    overrides(session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/premium/webhooks/stripe",
            json={"id": "evt_1", "type": "payment_intent.succeeded"},
            headers={"Stripe-Signature": "anything"},
        )
        assert response.status_code == 400

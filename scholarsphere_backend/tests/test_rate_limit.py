import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import RateLimiter
from app.main import app


class _FakeRedis:
    """In-memory stand-in for redis.asyncio.Redis, no network involved."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        return None

    async def aclose(self) -> None:
        return None


class _BrokenRedis:
    async def incr(self, key: str) -> int:
        raise ConnectionError("redis unreachable")


@pytest.mark.asyncio
async def test_requests_within_limit_are_allowed() -> None:
    limiter = RateLimiter("redis://unused", limit=3, window_seconds=60)
    limiter._client = _FakeRedis()
    assert await limiter.is_allowed("client-a")
    assert await limiter.is_allowed("client-a")
    assert await limiter.is_allowed("client-a")


@pytest.mark.asyncio
async def test_requests_over_limit_are_denied() -> None:
    limiter = RateLimiter("redis://unused", limit=2, window_seconds=60)
    limiter._client = _FakeRedis()
    assert await limiter.is_allowed("client-b")
    assert await limiter.is_allowed("client-b")
    assert not await limiter.is_allowed("client-b")


@pytest.mark.asyncio
async def test_limit_is_tracked_independently_per_key() -> None:
    limiter = RateLimiter("redis://unused", limit=1, window_seconds=60)
    limiter._client = _FakeRedis()
    assert await limiter.is_allowed("client-c")
    assert not await limiter.is_allowed("client-c")
    assert await limiter.is_allowed("client-d")


@pytest.mark.asyncio
async def test_backend_outage_fails_open_and_backs_off() -> None:
    limiter = RateLimiter("redis://unused", limit=1, window_seconds=60)
    limiter._client = _BrokenRedis()
    assert await limiter.is_allowed("client-e")
    assert limiter._outage_until > 0
    # During the backoff window, no further Redis calls are attempted, and
    # the request is still allowed through.
    limiter._client = _FakeRedis()
    assert await limiter.is_allowed("client-e")


def test_health_endpoints_bypass_rate_limiting() -> None:
    app.state.rate_limiter.limit = 0
    try:
        response = TestClient(app).get("/health/live")
    finally:
        app.state.rate_limiter.limit = 300
    assert response.status_code == 200


def test_exceeding_the_configured_limit_returns_429() -> None:
    app.state.rate_limiter._client = _FakeRedis()
    app.state.rate_limiter._outage_until = 0.0
    app.state.rate_limiter.limit = 1
    try:
        client = TestClient(app)
        first = client.get("/api/v1/opportunities")
        second = client.get("/api/v1/opportunities")
    finally:
        app.state.rate_limiter.limit = 300
        app.state.rate_limiter._client = None
    assert first.status_code == 401  # unauthenticated, but still consumes quota
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"

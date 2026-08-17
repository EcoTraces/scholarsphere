import logging
import time

import redis.asyncio as redis
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import correlation_id

logger = logging.getLogger(__name__)


_OUTAGE_BACKOFF_SECONDS = 5.0
_CONNECT_TIMEOUT_SECONDS = 0.5


class RateLimiter:
    """Fixed-window request counter backed by Redis.

    Fails open (allows the request) if Redis is unreachable so a transient
    cache outage never takes the whole API down -- rate limiting is
    defense-in-depth, not a correctness guarantee. Connection attempts use a
    short timeout, and a failed attempt suspends further Redis calls for a
    brief backoff window instead of retrying (and blocking) on every request
    while Redis is down.
    """

    def __init__(self, redis_url: str, *, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._redis_url = redis_url
        self._client: redis.Redis | None = None
        self._outage_until = 0.0

    def _get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=_CONNECT_TIMEOUT_SECONDS,
                socket_timeout=_CONNECT_TIMEOUT_SECONDS,
            )
        return self._client

    async def is_allowed(self, key: str) -> bool:
        now = time.time()
        if now < self._outage_until:
            return True
        client = self._get_client()
        window = int(now) // self.window_seconds
        bucket = f"ratelimit:{key}:{window}"
        try:
            count = await client.incr(bucket)
            if count == 1:
                await client.expire(bucket, self.window_seconds)
        except Exception:
            logger.warning("rate_limit_backend_unavailable", exc_info=True)
            self._outage_until = now + _OUTAGE_BACKOFF_SECONDS
            return True
        return count <= self.limit

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()


def install_rate_limiting(
    app: FastAPI, *, redis_url: str, limit: int, window_seconds: int
) -> RateLimiter:
    limiter = RateLimiter(redis_url, limit=limit, window_seconds=window_seconds)
    app.state.rate_limiter = limiter

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if request.url.path.startswith("/health"):
            return await call_next(request)
        client_host = request.client.host if request.client else "unknown"
        if not await limiter.is_allowed(client_host):
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Too many requests. Please try again shortly.",
                        "correlation_id": correlation_id(request),
                    }
                },
            )
        return await call_next(request)

    return limiter

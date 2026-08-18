from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes.applications import router as applications_router
from app.api.routes.external_opportunities import router as external_router
from app.api.routes.provider_opportunities import router as provider_opportunities_router
from app.api.routes.providers import router as providers_router
from app.api.routes.public_opportunities import router as public_opportunities_router
from app.core.config import get_settings
from app.core.errors import install_error_handling
from app.core.rate_limit import install_rate_limiting
from app.core.security_headers import install_security_headers
from app.db.session import AsyncSessionFactory, dispose_engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await app.state.rate_limiter.close()
    await dispose_engine()


_expose_docs = settings.app_env != "production"
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs" if _expose_docs else None,
    redoc_url="/redoc" if _expose_docs else None,
    openapi_url="/openapi.json" if _expose_docs else None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"],
)
install_error_handling(app, max_request_bytes=settings.max_request_bytes)
install_security_headers(app)
install_rate_limiting(
    app,
    redis_url=settings.redis_url,
    limit=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
app.include_router(external_router, prefix=settings.api_v1_prefix)
app.include_router(public_opportunities_router, prefix=settings.api_v1_prefix)
app.include_router(applications_router, prefix=settings.api_v1_prefix)
app.include_router(providers_router, prefix=settings.api_v1_prefix)
app.include_router(provider_opportunities_router, prefix=settings.api_v1_prefix)


@app.get("/health/live", tags=["health"])
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness() -> dict[str, str]:
    async with AsyncSessionFactory() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready"}

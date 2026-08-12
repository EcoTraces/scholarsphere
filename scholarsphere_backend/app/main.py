from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes.external_opportunities import router as external_router
from app.api.routes.public_opportunities import router as public_opportunities_router
from app.core.config import get_settings
from app.core.errors import install_error_handling
from app.db.session import AsyncSessionFactory, dispose_engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
app.include_router(external_router, prefix=settings.api_v1_prefix)
app.include_router(public_opportunities_router, prefix=settings.api_v1_prefix)


@app.get("/health/live", tags=["health"])
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness() -> dict[str, str]:
    async with AsyncSessionFactory() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready"}

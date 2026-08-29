from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes.analytics import router as analytics_router
from app.api.routes.applicant_documents import router as applicant_documents_router
from app.api.routes.applicant_profiles import router as applicant_profiles_router
from app.api.routes.applications import router as applications_router
from app.api.routes.audit import router as audit_router
from app.api.routes.backup import router as backup_router
from app.api.routes.calendar import router as calendar_router
from app.api.routes.collection import router as collection_router
from app.api.routes.data_lifecycle import router as data_lifecycle_router
from app.api.routes.experience import router as experience_router
from app.api.routes.external_opportunities import router as external_router
from app.api.routes.fraud_investigation import router as fraud_investigation_router
from app.api.routes.guidance import router as guidance_router
from app.api.routes.legal_compliance import router as legal_compliance_router
from app.api.routes.moderation import router as moderation_router
from app.api.routes.moderation import warnings_router as moderation_warnings_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.observability import router as observability_router
from app.api.routes.privacy import router as privacy_router
from app.api.routes.provider_analytics import router as provider_analytics_router
from app.api.routes.provider_opportunities import router as provider_opportunities_router
from app.api.routes.providers import router as providers_router
from app.api.routes.public_opportunities import router as public_opportunities_router
from app.api.routes.recommendation_governance import router as recommendation_governance_router
from app.api.routes.release import router as release_router
from app.api.routes.scraper_metrics import router as scraper_metrics_router
from app.api.routes.search_index import router as search_index_router
from app.api.routes.security import router as security_router
from app.api.routes.source_registry import router as source_registry_router
from app.api.routes.support import router as support_router
from app.api.routes.system_configuration import router as system_configuration_router
from app.api.routes.taxonomy import router as taxonomy_router
from app.core.auth import initialize_firebase
from app.core.config import get_settings
from app.core.errors import install_error_handling
from app.core.rate_limit import install_rate_limiting
from app.core.security_headers import install_security_headers
from app.db.session import AsyncSessionFactory, dispose_engine

settings = get_settings()


def ensure_firebase_ready_in_production(current_settings) -> None:
    """Fail fast at startup, with an actionable message, if Firebase Admin
    SDK can't initialize in production.

    Firebase Admin SDK initialization is otherwise lazy (first call to
    get_current_user) - that means a bad/missing credential would surface
    as a confusing 401/500 on the *first authenticated request* in
    production, not at deploy time. This exercises whichever credential
    mechanism is actually active (an explicit FIREBASE_CREDENTIALS_PATH or
    Application Default Credentials - config.py only validates the former
    when it's set, since ADC is also a valid choice on GCP infrastructure).
    A no-op outside app_env=production.
    """
    if current_settings.app_env != "production":
        return
    try:
        initialize_firebase()
    except Exception as error:
        raise RuntimeError(
            "Firebase Admin SDK failed to initialize at startup "
            f"(app_env=production): {error}. Set FIREBASE_CREDENTIALS_PATH "
            "to a valid service-account JSON key, or ensure Application "
            "Default Credentials are available (e.g. a service account "
            "attached to the GCP compute environment)."
        ) from error


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_firebase_ready_in_production(settings)
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
app.include_router(notifications_router, prefix=settings.api_v1_prefix)
app.include_router(applicant_profiles_router, prefix=settings.api_v1_prefix)
app.include_router(applicant_documents_router, prefix=settings.api_v1_prefix)
app.include_router(moderation_router, prefix=settings.api_v1_prefix)
app.include_router(moderation_warnings_router, prefix=settings.api_v1_prefix)
app.include_router(privacy_router, prefix=settings.api_v1_prefix)
app.include_router(support_router, prefix=settings.api_v1_prefix)
app.include_router(source_registry_router, prefix=settings.api_v1_prefix)
app.include_router(taxonomy_router, prefix=settings.api_v1_prefix)
app.include_router(calendar_router, prefix=settings.api_v1_prefix)
app.include_router(guidance_router, prefix=settings.api_v1_prefix)
app.include_router(experience_router, prefix=settings.api_v1_prefix)
app.include_router(search_index_router, prefix=settings.api_v1_prefix)
app.include_router(legal_compliance_router, prefix=settings.api_v1_prefix)
app.include_router(analytics_router, prefix=settings.api_v1_prefix)
app.include_router(recommendation_governance_router, prefix=settings.api_v1_prefix)
app.include_router(provider_analytics_router, prefix=settings.api_v1_prefix)
app.include_router(security_router, prefix=settings.api_v1_prefix)
app.include_router(audit_router, prefix=settings.api_v1_prefix)
app.include_router(system_configuration_router, prefix=settings.api_v1_prefix)
app.include_router(backup_router, prefix=settings.api_v1_prefix)
app.include_router(release_router, prefix=settings.api_v1_prefix)
app.include_router(data_lifecycle_router, prefix=settings.api_v1_prefix)
app.include_router(observability_router, prefix=settings.api_v1_prefix)
app.include_router(scraper_metrics_router, prefix=settings.api_v1_prefix)
app.include_router(fraud_investigation_router, prefix=settings.api_v1_prefix)
app.include_router(collection_router, prefix=settings.api_v1_prefix)


@app.get("/health/live", tags=["health"])
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness() -> dict[str, str]:
    async with AsyncSessionFactory() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready"}

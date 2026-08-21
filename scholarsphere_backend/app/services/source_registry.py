from datetime import timedelta
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import OpportunitySource
from app.services.parsing import utc_now

SOURCE_DEFINITIONS: Final[dict[str, dict[str, str]]] = {
    "grants_gov": {
        "source_name": "Grants.gov",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "official",
    },
    "grants_gov_individual": {
        "source_name": "Grants.gov (Individual Eligibility)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "official",
    },
    "simpler_grants": {
        "source_name": "Simpler.Grants.gov",
        "source_type": "government",
        "authentication_type": "api_key",
        "trust_level": "official",
    },
    "eu_funding_tenders": {
        "source_name": "European Commission Funding & Tenders",
        "source_type": "international_government",
        "authentication_type": "api_key",
        "trust_level": "official",
    },
    "usajobs": {
        "source_name": "USAJOBS",
        "source_type": "government",
        "authentication_type": "api_key",
        "trust_level": "official",
    },
    "reliefweb_jobs": {
        "source_name": "ReliefWeb Jobs",
        "source_type": "international_organization",
        "authentication_type": "app_identifier",
        "trust_level": "official",
    },
    "reliefweb_training": {
        "source_name": "ReliefWeb Training",
        "source_type": "international_organization",
        "authentication_type": "app_identifier",
        "trust_level": "official",
    },
    "manual_collection": {
        "source_name": "Manual/ad hoc collection",
        "source_type": "manual",
        "authentication_type": "none",
        "trust_level": "community",
    },
}


def _base_urls() -> dict[str, str]:
    settings = get_settings()
    reliefweb_base = settings.reliefweb_base_url.rstrip("/")
    return {
        "grants_gov": settings.grants_gov_base_url,
        "grants_gov_individual": settings.grants_gov_base_url,
        "simpler_grants": settings.simpler_grants_base_url,
        "eu_funding_tenders": settings.eu_funding_api_url,
        "usajobs": settings.usajobs_base_url,
        "reliefweb_jobs": f"{reliefweb_base}/jobs",
        "reliefweb_training": f"{reliefweb_base}/training",
        "manual_collection": "",
    }


async def seed_opportunity_sources(
    session: AsyncSession,
) -> dict[str, OpportunitySource]:
    """Idempotently create sources and return every configured source by code."""
    existing = {
        source.source_code: source
        for source in (
            await session.scalars(
                select(OpportunitySource).where(
                    OpportunitySource.source_code.in_(tuple(SOURCE_DEFINITIONS))
                )
            )
        ).all()
    }
    base_urls = _base_urls()
    now = utc_now()
    next_runs = {
        "grants_gov": now + timedelta(hours=6),
        "grants_gov_individual": now + timedelta(hours=6),
        "simpler_grants": now + timedelta(hours=6),
        "eu_funding_tenders": now + timedelta(hours=12),
        "usajobs": now + timedelta(hours=6),
        "reliefweb_jobs": now + timedelta(hours=6),
        "reliefweb_training": now + timedelta(hours=12),
    }
    for source_code, definition in SOURCE_DEFINITIONS.items():
        next_run = next_runs.get(source_code, now + timedelta(hours=6))
        if source_code in existing:
            if existing[source_code].next_scheduled_sync is None:
                existing[source_code].next_scheduled_sync = next_run
            continue
        source = OpportunitySource(
            source_code=source_code,
            base_url=base_urls[source_code],
            next_scheduled_sync=next_run,
            **definition,
        )
        session.add(source)
        existing[source_code] = source
    await session.flush()
    return existing

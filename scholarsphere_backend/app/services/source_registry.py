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
    # Web-scraper sources - no official API/RSS/dataset exists for these
    # organizations (see docs/AUTHORITATIVE_SOURCES.md #8-#12). trust_level
    # "web_scraped" is deliberately lower than "official": it still lands
    # in the same mandatory human-verification queue as every other
    # source (never auto-published - see
    # docs/OPPORTUNITY_VERIFICATION_SYSTEM.md), but scores lower in
    # app/services/verification_confidence.py so an officer sees the
    # trust distinction explicitly rather than it being silently implied.
    "cscuk_scholarships": {
        "source_name": "Commonwealth Scholarships (CSC UK)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "chevening": {
        "source_name": "Chevening Scholarships",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "daad_scholarships": {
        "source_name": "DAAD Scholarship Database",
        "source_type": "quasi_governmental",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "china_embassy_sl": {
        "source_name": "Chinese Embassy in Sierra Leone (Scholarship Announcements)",
        "source_type": "embassy",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "mthe_sierra_leone": {
        "source_name": "Sierra Leone Ministry of Technical and Higher Education",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    # Country-expansion single-flagship-program sources (2026-08-23) - see
    # docs/AUTHORITATIVE_SOURCES.md #13-#18.
    "wmi_scholars": {
        "source_name": "Wells Mountain Initiative (WMI) Scholars Program",
        "source_type": "funding_organization",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "turkiye_burslari": {
        "source_name": "Türkiye Bursları (Türkiye Scholarships)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "ireland_goi_ies": {
        "source_name": "Government of Ireland International Education Scholarships",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "india_iccr": {
        "source_name": "ICCR Scholarship Programme (India)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "sweden_si_scholarship": {
        "source_name": "Swedish Institute Scholarships for Global Professionals",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "eswatini_slas": {
        "source_name": "Eswatini Scholarship Loan Application System (SLAS)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "italy_maeci_scholarships": {
        "source_name": "Italian Government Scholarships (MAECI)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "greece_iky_scholarships": {
        "source_name": "IKY Foreign Nationals Scholarships (Greece)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "south_africa_nrf": {
        "source_name": "National Research Foundation (NRF) Postgraduate Funding (South Africa)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "netherlands_nuffic": {
        "source_name": "Nuffic NL Scholarship (Netherlands)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "spain_aecid": {
        "source_name": "AECID Scholarships for Latin America, Africa and Asia (Spain)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "australia_dfat_awards": {
        "source_name": "Australia Awards (DFAT)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
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
        "cscuk_scholarships": settings.cscuk_base_url,
        "chevening": settings.chevening_base_url,
        "daad_scholarships": settings.daad_base_url,
        "china_embassy_sl": settings.china_embassy_sl_base_url,
        "mthe_sierra_leone": settings.mthe_sl_base_url,
        "wmi_scholars": settings.wmi_base_url,
        "turkiye_burslari": settings.turkiye_burslari_base_url,
        "ireland_goi_ies": settings.ireland_hea_base_url,
        "india_iccr": settings.india_iccr_base_url,
        "sweden_si_scholarship": settings.sweden_si_base_url,
        "eswatini_slas": settings.eswatini_slas_base_url,
        "italy_maeci_scholarships": settings.italy_esteri_base_url,
        "greece_iky_scholarships": settings.greece_iky_base_url,
        "south_africa_nrf": settings.south_africa_nrf_base_url,
        "netherlands_nuffic": settings.netherlands_nuffic_base_url,
        "spain_aecid": settings.spain_aecid_base_url,
        "australia_dfat_awards": settings.australia_awards_base_url,
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
        # Web-scraper sources sync once daily, not every 6-12h like the
        # official APIs - lower volume of change, and a deliberately
        # gentler request cadence for sources without a documented rate
        # limit of their own (see docs/AUTHORITATIVE_SOURCES.md).
        "cscuk_scholarships": now + timedelta(hours=24),
        "chevening": now + timedelta(hours=24),
        "daad_scholarships": now + timedelta(hours=24),
        "china_embassy_sl": now + timedelta(hours=24),
        "mthe_sierra_leone": now + timedelta(hours=24),
        "wmi_scholars": now + timedelta(hours=24),
        "turkiye_burslari": now + timedelta(hours=24),
        "ireland_goi_ies": now + timedelta(hours=24),
        "india_iccr": now + timedelta(hours=24),
        "sweden_si_scholarship": now + timedelta(hours=24),
        "eswatini_slas": now + timedelta(hours=24),
        "italy_maeci_scholarships": now + timedelta(hours=24),
        "greece_iky_scholarships": now + timedelta(hours=24),
        "south_africa_nrf": now + timedelta(hours=24),
        "netherlands_nuffic": now + timedelta(hours=24),
        "spain_aecid": now + timedelta(hours=24),
        "australia_dfat_awards": now + timedelta(hours=24),
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

"""U.S. Department of State's EducationUSA "Find Financial Aid" database
(`educationusa.state.gov/find-financial-aid`) - a paginated Drupal Views
listing of individually browsable, institution-specific scholarships for
international students applying to study in the United States. Closes
this platform's United States gap: the only prior US-facing sources
(`grants_gov`, `usajobs`, `reliefweb`) are federal grants/jobs/
humanitarian postings, not international-student scholarships, and the
one dedicated candidate researched earlier (the Fulbright Foreign Student
Program) was rejected as `NOT_SUITABLE` - it has no single stable page,
being fragmented across ~160 individual US embassy sites (see
docs/COUNTRY_PROVIDER_REGISTRY.md's Fulbright entry).

Confirmed 2026-08-29 by live testing (see docs/AUTHORITATIVE_SOURCES.md
#44): `/find-financial-aid` returns real, server-rendered HTML over plain
HTTPS (no browser rendering needed) - a Drupal Views listing of 277+
`.views-row` entries, paginated via `?page=N` (0-indexed: `page=0` is
results 1-10). `robots.txt` itself returns HTTP 403 (not 200, not
unreachable) - per RFC 9309 SS2.3.1.3, a non-2xx status on robots.txt
means "no crawl restrictions apply," the same interpretation major search
engine crawlers use; there is no `Disallow` rule this adapter would be
violating even if the file were reachable, since none could be read.

Deliberately conservative about what's extracted: each row's own listing
page (title, host institution, and the site's own free-text deadline
statement, e.g. "Fall semester: July 1st; Spring semester: November
1st" - often a recurring/rolling statement, never forced into a single
parsed date, matching this project's "never silently convert an
ambiguous date" rule) is used directly, without following each entry's
external "More information" link (which would mean up to ~280 extra
per-sync fetches against arbitrary third-party university domains - out
of proportion with what this adapter needs, and a same_host_https_url-
style trust boundary concern this codebase already treats seriously -
see app/services/web_scraper_base.py). `official_application_url` and
`official_source_url` both point at the entry's own EducationUSA detail
page instead, which is itself a real, stable, official page describing
that scholarship.

Uses `app.services.pagination_engine.paginate_by_url` - the pagination
engine's first real production consumer - bounded by the shared
`MAX_PAGES_PER_SOURCE`/`MAX_RECORDS_PER_SOURCE` settings (defaults
comfortably cover this source's ~28 pages / ~280 records).
"""

import logging

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.pagination_engine import paginate_by_url
from app.services.web_scraper_base import WebScraperSource, absolute_https_url, clean_text

logger = logging.getLogger(__name__)


class EducationUsaFinancialAidSource(WebScraperSource):
    source_code = "educationusa_financial_aid"
    min_request_interval_seconds = 2.0

    def __init__(self) -> None:
        self.base_url = get_settings().educationusa_base_url.rstrip("/")

    async def collect(
        self, **_: object
    ) -> list[NormalizedExternalOpportunity]:
        async def fetch_page(url: str) -> list[dict[str, str | None]]:
            try:
                soup = await self.fetch_soup(url)
            except ExternalAPIError as error:
                logger.warning(
                    "%s_page_fetch_failed url=%s error=%s",
                    self.source_code,
                    url,
                    error,
                )
                return []

            items: list[dict[str, str | None]] = []
            for row in soup.select(".views-row"):
                link = row.select_one(".views-field-title a")
                if link is None:
                    continue
                detail_url = absolute_https_url(self.base_url, link.get("href"))
                if not detail_url:
                    continue
                items.append(
                    {
                        "title": clean_text(link),
                        "provider_name": clean_text(
                            row.select_one(".field-hei-institution-name")
                        ),
                        "deadline_text": clean_text(
                            row.select_one(".field-scholarship-deadline")
                        ),
                        "detail_url": detail_url,
                    }
                )
            return items

        result = await paginate_by_url(
            fetch_page,
            url_template=f"{self.base_url}/find-financial-aid?page={{page}}",
            key_fn=lambda item: item["detail_url"],
            start_page=0,
        )

        opportunities: list[NormalizedExternalOpportunity] = []
        for item in result.items:
            deadline_text = item.get("deadline_text")
            description = f"Apply by: {deadline_text}" if deadline_text else None
            try:
                opportunities.append(
                    NormalizedExternalOpportunity(
                        source_code=self.source_code,
                        external_id=item["detail_url"],
                        title=item["title"] or "Untitled scholarship",
                        opportunity_type="scholarship",
                        provider_name=item["provider_name"]
                        or "EducationUSA-listed institution",
                        country="United States",
                        description=description,
                        opportunity_status="posted",
                        official_source_url=item["detail_url"],
                        official_application_url=item["detail_url"],
                        raw_payload=item,
                    )
                )
            except ValidationError as error:
                logger.warning(
                    "%s_normalize_failed url=%s error=%s",
                    self.source_code,
                    item.get("detail_url"),
                    error,
                )
                continue
        return opportunities

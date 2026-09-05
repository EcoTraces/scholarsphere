"""United Arab Emirates University (UAEU), College of Graduate Studies -
its own "Scholarships, Fellowships, and Graduate Assistantships" page.
Closes two gaps at once: the UAE gap in this platform's 40-country
target list (the only prior UAE finding, government scholarships, came
back `NO_RELIABLE_SOURCE_FOUND` - predominantly outbound for Emiratis,
not inbound; see docs/COUNTRY_PROVIDER_REGISTRY.md), and this project's
first genuinely UNIVERSITY-type source (every other web-scraped source
so far is government/international-organization/foundation-typed).

Confirmed 2026-08-30: `/en/cgs/scholarship.shtml` is real, server-
rendered HTML (200, ~169KB) - no browser rendering needed. `robots.txt`
allows `User-agent: *` with only narrow, unrelated `Disallow:` rules
(specific admin/legal pages) - none matching this page.

The page's real content is a Tailwind-based accordion widget
(`.aegov-accordion` / `.accordion-item`) reused site-wide for both page
navigation AND this scholarships list - the same widget class alone
isn't unique enough. The actual scholarships accordion is scoped via
`[id^="faqs-section"]` (a CMS-generated id prefix, stable in practice
even though the hash suffix after it changes on every republish) rather
than a hardcoded full id.

Extracts **every** accordion item as its own opportunity record - 13 at
the time of writing, covering Fellowships, Research/Teaching/
Administrative Assistantships, and department-specific PhD
studentships. Deliberately **not filtered by nationality eligibility**:
several titles explicitly state "(All nationalities)"; others just as
explicitly state a restriction ("UAE nationals", "UAEU Alumni only",
"eligible Emirati students") directly in their own real title text -
this adapter extracts that text verbatim rather than acting on it,
matching this project's standing "AI's role: none, today" policy for
eligibility (see docs/OPPORTUNITY_VERIFICATION_SYSTEM.md SS10) - a human
verification officer reads the real title/description before approving
any record, exactly like every other scraped source in this project
(see app/services/embassy_announcements.py's module docstring for the
same policy applied there).

Each item's own "Details... click here"/similar link (several are PDFs,
not HTML pages) is stored as both `official_source_url` and
`official_application_url` without being fetched itself - reading a
program's own PDF guidelines is out of scope for this adapter, matching
how `educationusa_source.py` and `erasmus_mundus_source.py` also don't
follow their own per-row "more information" links.
"""

import logging

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.web_scraper_base import WebScraperSource, absolute_https_url, clean_text

logger = logging.getLogger(__name__)

_PROVIDER_NAME = "United Arab Emirates University (UAEU), College of Graduate Studies"


class UaeuScholarshipsSource(WebScraperSource):
    source_code = "uaeu_scholarships"
    min_request_interval_seconds = 2.0

    def __init__(self) -> None:
        self.base_url = get_settings().uaeu_base_url.rstrip("/")

    async def collect(
        self, **_: object
    ) -> list[NormalizedExternalOpportunity]:
        overview_url = f"{self.base_url}/en/cgs/scholarship.shtml"
        try:
            soup = await self.fetch_soup(overview_url)
        except ExternalAPIError as error:
            logger.warning(
                "%s_overview_fetch_failed url=%s error=%s",
                self.source_code,
                overview_url,
                error,
            )
            return []

        container = soup.select_one('[id^="faqs-section"]')
        if container is None:
            logger.warning(
                "%s_accordion_container_not_found url=%s", self.source_code, overview_url
            )
            return []

        opportunities: list[NormalizedExternalOpportunity] = []
        seen_urls: set[str] = set()
        for item in container.select(".accordion-item"):
            title_node = item.select_one(".accordion-title button span")
            title = clean_text(title_node)
            if not title:
                continue
            body = item.select_one(".accordion-content")
            link = body.find("a", href=True) if body is not None else None
            detail_url = (
                absolute_https_url(overview_url, link.get("href"))
                if link is not None
                else None
            )
            if not detail_url or detail_url in seen_urls:
                continue
            seen_urls.add(detail_url)

            try:
                opportunities.append(
                    NormalizedExternalOpportunity(
                        source_code=self.source_code,
                        external_id=detail_url,
                        title=title,
                        opportunity_type="scholarship",
                        provider_name=_PROVIDER_NAME,
                        country="United Arab Emirates",
                        description=clean_text(body),
                        opportunity_status="posted",
                        official_source_url=detail_url,
                        official_application_url=detail_url,
                        raw_payload={"title": title, "detail_url": detail_url},
                    )
                )
            except ValidationError as error:
                logger.warning(
                    "%s_normalize_failed title=%r error=%s",
                    self.source_code,
                    title,
                    error,
                )
                continue
        return opportunities

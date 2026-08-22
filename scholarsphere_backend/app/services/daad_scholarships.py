"""DAAD (Deutscher Akademischer Austauschdienst / German Academic Exchange
Service) scholarship database. No official API, RSS feed, or dataset
exists (see docs/AUTHORITATIVE_SOURCES.md #10) - the site's own search
widget loads results through an undocumented internal AJAX endpoint
(`/ajax/`), and `https://www.daad.de/sitemap.xml` (confirmed reachable
2026-08-22) does not include the scholarship database's individual
`?detail=<id>` listing pages, so there is no ToS-respecting way to
discover the full catalogue automatically today.

This adapter therefore monitors a curated, explicitly-configured seed list
of detail-page ids (`Settings.daad_scholarship_detail_ids`) rather than
crawling the whole database - each id was identified by name during
source research and is fetched directly by URL. This is a deliberate
scope limitation, not a placeholder: extending coverage means adding more
ids to that setting (or, better, replacing this adapter entirely if DAAD
ever documents its search endpoint or a dedicated sitemap), not writing
more scraping code.

Confirmed 2026-08-22 against the real site:
- `https://www.daad.de/robots.txt` sets `Crawl-delay: 2` and does not
  disallow the scholarship-database paths - this adapter's minimum
  request interval matches that exactly.
- A detail page (`https://www2.daad.de/deutschland/stipendium/datenbank/
  en/21148-scholarship-database/?detail=<id>`) is fully server-rendered
  (no JavaScript needed to read it) with the programme name in `<title>`
  (before the " - DAAD" suffix) and its content inside
  `#ifa-stipendien-detail`, including an "Application deadline" `<h3>`.
"""

import logging

from bs4 import BeautifulSoup
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.parsing import extract_confident_date_after, sanitize_html
from app.services.web_scraper_base import WebScraperSource, clean_text

logger = logging.getLogger(__name__)

_TITLE_SUFFIX = " - DAAD"


class DaadScholarshipsSource(WebScraperSource):
    source_code = "daad_scholarships"
    #: Matches DAAD's own published robots.txt Crawl-delay exactly.
    min_request_interval_seconds = 2.0

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.daad_base_url.rstrip("/")
        self.detail_ids = list(settings.daad_scholarship_detail_ids)

    async def collect(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[NormalizedExternalOpportunity]:
        normalized: list[NormalizedExternalOpportunity] = []
        for detail_id in self.detail_ids[:page_size]:
            url = self._detail_url(detail_id)
            try:
                soup = await self.fetch_soup(url)
            except ExternalAPIError as error:
                logger.warning(
                    "daad_detail_fetch_failed detail_id=%s error=%s", detail_id, error
                )
                continue
            try:
                normalized.append(self._normalize(detail_id, url, soup))
            except ValidationError as error:
                logger.warning(
                    "daad_normalize_failed detail_id=%s error=%s", detail_id, error
                )
                continue
        return normalized

    def _detail_url(self, detail_id: str) -> str:
        return (
            f"{self.base_url}/deutschland/stipendium/datenbank/en/"
            f"21148-scholarship-database/?detail={detail_id}"
        )

    def _normalize(
        self, detail_id: str, url: str, soup: BeautifulSoup
    ) -> NormalizedExternalOpportunity:
        raw_title = clean_text(soup.find("title")) or ""
        title = raw_title.split(_TITLE_SUFFIX)[0].strip() or "Untitled DAAD scholarship"

        content = soup.select_one("#ifa-stipendien-detail") or soup.body
        content_text = clean_text(content)
        description = sanitize_html(content_text[:5000]) if content_text else None
        deadline = (
            extract_confident_date_after(content_text, "application deadline")
            if content_text
            else None
        )

        return NormalizedExternalOpportunity(
            source_code=self.source_code,
            external_id=detail_id,
            title=title,
            opportunity_type="scholarship",
            provider_name="DAAD (German Academic Exchange Service)",
            country="Germany",
            description=description,
            deadline=deadline,
            opportunity_status="posted",
            official_source_url=url,
            official_application_url=url,
            raw_payload={"detail_id": detail_id, "url": url, "title": title},
        )

"""Commonwealth Scholarships (Commonwealth Scholarship Commission in the
UK, "CSC") - a UK government scholarship scheme with no official API, RSS
feed, or dataset (see docs/AUTHORITATIVE_SOURCES.md #8). Scrapes the
public scholarships archive page and each individual programme's own page.

Confirmed 2026-08-22 against the real site:
- `https://cscuk.fcdo.gov.uk/robots.txt` has no `Disallow` rules and no
  `Crawl-delay` (full access permitted) - this adapter still applies the
  shared 2-second minimum interval between requests as a courtesy default.
- The archive page (`/scholarships/`) links to individual programme pages
  under `/scholarships/commonwealth-<slug>/`.
- Each programme page has `<h1 class="entry-title">` for its name and a
  series of `<div class="et_pb_text_inner">` sections, each starting with
  its own heading ("Overview", "How to apply", "Applicant eligibility",
  "Eligible countries", "Financial assistance", ...).
"""

import logging

from bs4 import BeautifulSoup
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.parsing import extract_confident_date_after, sanitize_html
from app.services.web_scraper_base import WebScraperSource, absolute_https_url, clean_text

logger = logging.getLogger(__name__)

_PROGRAMME_PATH_PREFIX = "/scholarships/commonwealth-"


class CscukScholarshipsSource(WebScraperSource):
    source_code = "cscuk_scholarships"
    min_request_interval_seconds = 2.0

    #: Known programme pages as of source research (2026-08-22) - used only
    #: as a fallback if the archive page's own link discovery finds
    #: nothing (e.g. a markup change on the site); the primary discovery
    #: path is always the live archive page, not this list.
    _SEED_SLUGS = (
        "commonwealth-masters-scholarships",
        "commonwealth-shared-scholarships-applications",
        "commonwealth-phd-scholarships-for-least-developed-countries-and-vulnerable-states",
        "commonwealth-fellowships-information-for-candidates",
        "commonwealth-professional-fellowships-information-for-uk-host-organisations",
        "commonwealth-startup-fellowship-information-for-candidates",
    )

    def __init__(self) -> None:
        self.base_url = get_settings().cscuk_base_url.rstrip("/")

    async def collect(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[NormalizedExternalOpportunity]:
        urls = await self._discover_programme_urls()
        normalized: list[NormalizedExternalOpportunity] = []
        for url in urls[:page_size]:
            try:
                soup = await self.fetch_soup(url)
            except ExternalAPIError as error:
                logger.warning("cscuk_detail_fetch_failed url=%s error=%s", url, error)
                continue
            try:
                normalized.append(self._normalize(url, soup))
            except ValidationError as error:
                logger.warning("cscuk_normalize_failed url=%s error=%s", url, error)
                continue
        return normalized

    async def _discover_programme_urls(self) -> list[str]:
        list_url = f"{self.base_url}/scholarships/"
        soup: BeautifulSoup | None = None
        try:
            soup = await self.fetch_soup(list_url)
        except ExternalAPIError as error:
            logger.warning("cscuk_list_fetch_failed error=%s", error)

        urls: dict[str, None] = {}
        if soup is not None:
            for anchor in soup.find_all("a", href=True):
                absolute = absolute_https_url(list_url, anchor["href"])
                if absolute and absolute.rstrip("/").startswith(
                    f"{self.base_url}{_PROGRAMME_PATH_PREFIX}"
                ):
                    urls[absolute.rstrip("/") + "/"] = None
        if not urls:
            for slug in self._SEED_SLUGS:
                urls[f"{self.base_url}/scholarships/{slug}/"] = None
        return list(urls)

    def _normalize(self, url: str, soup: BeautifulSoup) -> NormalizedExternalOpportunity:
        title = clean_text(soup.select_one("h1.entry-title")) or clean_text(
            soup.find("h1")
        )
        sections = _section_text_by_heading(soup)
        overview = sections.get("overview")
        how_to_apply = sections.get("how to apply")
        eligibility = sections.get("applicant eligibility")
        eligible_countries = sections.get("eligible countries")
        financial = sections.get("financial assistance")

        description_parts = [
            part for part in (overview, eligibility, eligible_countries) if part
        ]
        description = (
            sanitize_html("<br><br>".join(description_parts))
            if description_parts
            else None
        )
        deadline = (
            extract_confident_date_after(how_to_apply, "closing date")
            or extract_confident_date_after(how_to_apply, "deadline")
            if how_to_apply
            else None
        )
        external_id = url.rstrip("/").rsplit("/", 1)[-1]

        return NormalizedExternalOpportunity(
            source_code=self.source_code,
            external_id=external_id,
            title=title or "Untitled Commonwealth Scholarship programme",
            opportunity_type="scholarship",
            provider_name="Commonwealth Scholarship Commission in the UK",
            country="United Kingdom",
            description=description,
            deadline=deadline,
            opportunity_status="posted",
            funding_type="fully_funded" if financial else None,
            official_source_url=url,
            official_application_url=url,
            raw_payload={
                "url": url,
                "title": title,
                "sections": sections,
            },
        )


def _section_text_by_heading(soup: BeautifulSoup) -> dict[str, str]:
    """Each content block on a CSC UK programme page is a
    `.et_pb_text_inner` div whose first child heading names the section
    (see module docstring). Returns {lowercased heading: body text}.
    """
    sections: dict[str, str] = {}
    for container in soup.select(".et_pb_text_inner"):
        heading = container.find(["h1", "h2", "h3"])
        if heading is None:
            continue
        key = clean_text(heading)
        if not key:
            continue
        heading.extract()
        body = clean_text(container)
        if body:
            sections[key.lower()] = body
    return sections

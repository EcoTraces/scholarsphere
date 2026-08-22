"""Chevening Scholarships - the UK Foreign, Commonwealth & Development
Office's global scholarship programme. Unlike CSC UK or DAAD, Chevening
runs a single annual programme with one global deadline rather than a
catalogue of separate named awards, so this adapter produces exactly one
opportunity record per sync rather than discovering a list of pages. No
official API, RSS feed, or dataset exists (see
docs/AUTHORITATIVE_SOURCES.md #9).

Confirmed 2026-08-22 against the real site:
- `https://www.chevening.org/robots.txt` was unreachable to check directly
  from this environment (network timeout); the site's own published
  application guidance is fetched at a low, courtesy-limited rate as a
  precaution.
- `/scholarships/` carries the programme overview (`<h1
  class="pagehero-title">` and a lead `<p>` description).
- `/apply/` states the live deadline in a `<span class="open">Open for
  applications until <date>, at <time> (UTC)</span>` element, repeated
  once per country's application entry point.
"""

import logging

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.parsing import extract_confident_date, sanitize_html
from app.services.web_scraper_base import WebScraperSource, clean_text

logger = logging.getLogger(__name__)


class CheveningSource(WebScraperSource):
    source_code = "chevening"
    min_request_interval_seconds = 2.0

    #: Fixed, stable id - Chevening is one recurring annual programme, not
    #: a catalogue, so re-syncing updates the same record in place (its
    #: deadline changing year over year correctly triggers
    #: reverification_required for an already-verified record - see
    #: app/services/opportunity_import.py MATERIAL_FIELDS) rather than
    #: creating a new opportunity every cycle.
    _EXTERNAL_ID = "chevening-scholarship"

    def __init__(self) -> None:
        self.base_url = get_settings().chevening_base_url.rstrip("/")

    async def collect(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[NormalizedExternalOpportunity]:
        overview_url = f"{self.base_url}/scholarships/"
        apply_url = f"{self.base_url}/apply/"
        try:
            overview_soup = await self.fetch_soup(overview_url)
        except ExternalAPIError as error:
            logger.warning("chevening_overview_fetch_failed error=%s", error)
            return []
        try:
            apply_soup = await self.fetch_soup(apply_url)
        except ExternalAPIError as error:
            logger.warning("chevening_apply_fetch_failed error=%s", error)
            apply_soup = None

        title = clean_text(overview_soup.select_one("h1.pagehero-title")) or (
            "Chevening Scholarship"
        )
        summary = clean_text(overview_soup.select_one("p.pagehero-summary"))
        lead_paragraph = clean_text(overview_soup.find("p"))
        description_parts = [part for part in (summary, lead_paragraph) if part]
        description = (
            sanitize_html("<br><br>".join(description_parts))
            if description_parts
            else None
        )

        deadline = None
        if apply_soup is not None:
            deadline_text = clean_text(apply_soup.select_one("span.open"))
            deadline = extract_confident_date(deadline_text) if deadline_text else None

        try:
            return [
                NormalizedExternalOpportunity(
                    source_code=self.source_code,
                    external_id=self._EXTERNAL_ID,
                    title=title,
                    opportunity_type="scholarship",
                    provider_name=(
                        "Chevening (UK Foreign, Commonwealth & Development Office)"
                    ),
                    description=description,
                    deadline=deadline,
                    opportunity_status="posted",
                    funding_type="fully_funded",
                    official_source_url=overview_url,
                    official_application_url=apply_url,
                    raw_payload={
                        "overview_url": overview_url,
                        "apply_url": apply_url,
                        "title": title,
                    },
                )
            ]
        except ValidationError as error:
            logger.warning("chevening_normalize_failed error=%s", error)
            return []

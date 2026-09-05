"""Erasmus Mundus Joint Masters (EMJM) catalogue - the European
Education and Culture Executive Agency's (EACEA) official, annually
updated list of EU-funded joint master's programmes delivered by
multi-university consortiums across (mostly) Europe. Closes another
slice of this platform's "multiple source types per country" gap (see
docs/COUNTRY_PROVIDER_REGISTRY.md's fifteenth-pass note): genuinely open
to applicants "from all over the world" per the catalogue's own text -
not restricted by nationality, so Sierra Leonean applicants are eligible
the same as anyone else.

Confirmed 2026-08-30: `/scholarships/erasmus-mundus-catalogue_en` is
real, server-rendered HTML (200, ~186KB) built with the EU's own ECL
(Europa Component Library) design system - `article.ecl-card` per
programme, `.ecl-content-block__title a` for the title/link,
`.ecl-pagination` with real `?page=N` (0-indexed) href links, no
browser rendering needed. The page carries `<meta name="robots"
content="follow, noindex">` - a page-level *search-engine indexing*
directive (asking Google/Bing not to index this specific page, likely
to avoid duplicate-content issues with the catalogue's own filtered
variants), not a Robots Exclusion Protocol crawl restriction - it says
nothing about whether fetching the content is permitted, only whether a
search engine should index it. `robots.txt` at the site root scopes its
`Disallow:` rules to `User-agent: Googlebot` specifically (no general
`User-agent: *` block), so no restriction applies to this backend's
generic client - the same "only specific-bot rules present" pattern
already documented for Mexico's AMEXCID (source #43).

The first production consumer of `app/services/pagination_engine.py`'s
`paginate_by_url` after `educationusa_source.py` - same shape (a plain
server-rendered `?page=N` listing, no browser needed), a second real
proof this engine generalizes across genuinely different sites rather
than being tuned to one.

Deliberately conservative about what's extracted: each card's own title
and its two links - the programme's own external website (used as
`official_application_url`, since that's genuinely where an applicant
would go) and the EU's own project-record page at
`erasmus-plus.ec.europa.eu/projects/search/details/<id>` (used as
`official_source_url`, the authoritative EU record this listing came
from) - plus the card's own short description text (an acronym plus
"Project overview", exactly what's on the page - never expanded or
guessed). No per-programme deadline is stated on this listing page
(each of the ~220 programmes' consortium sets its own - the catalogue's
own text only says "most... require applications... between October and
January", not a specific date for any one programme), so `deadline`
stays `None` for every record here - never guessed from that generic
text. Does not follow the ~220 external programme links or the EU
project-record pages to fetch more detail - out of proportion with what
this adapter needs, matching the same reasoning `educationusa_source.py`
already documents for not following its own per-row "More information"
links.
"""

import logging

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.pagination_engine import paginate_by_url
from app.services.web_scraper_base import WebScraperSource, absolute_https_url, clean_text

logger = logging.getLogger(__name__)

_PROVIDER_NAME = (
    "Erasmus Mundus Joint Masters (European Education and Culture "
    "Executive Agency, European Commission)"
)


class ErasmusMundusJointMastersSource(WebScraperSource):
    source_code = "erasmus_mundus_joint_masters"
    min_request_interval_seconds = 2.0

    def __init__(self) -> None:
        self.base_url = get_settings().erasmus_mundus_base_url.rstrip("/")

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
            for card in soup.select("article.ecl-card"):
                title_link = card.select_one(".ecl-content-block__title a")
                if title_link is None:
                    continue
                application_url = absolute_https_url(
                    self.base_url, title_link.get("href")
                )
                if not application_url:
                    continue
                description_node = card.select_one(".ecl-content-block__description")
                source_link = None
                if description_node is not None:
                    source_link = description_node.find("a", href=True)
                source_url = (
                    absolute_https_url(self.base_url, source_link.get("href"))
                    if source_link is not None
                    else None
                )
                items.append(
                    {
                        "title": clean_text(title_link),
                        "description": clean_text(description_node),
                        "application_url": application_url,
                        "source_url": source_url or application_url,
                    }
                )
            return items

        result = await paginate_by_url(
            fetch_page,
            url_template=f"{self.base_url}/scholarships/erasmus-mundus-catalogue_en?page={{page}}",
            key_fn=lambda item: item["application_url"],
            start_page=0,
        )

        opportunities: list[NormalizedExternalOpportunity] = []
        for item in result.items:
            try:
                opportunities.append(
                    NormalizedExternalOpportunity(
                        source_code=self.source_code,
                        external_id=item["application_url"],
                        title=item["title"] or "Untitled Erasmus Mundus Joint Master's",
                        opportunity_type="scholarship",
                        provider_name=_PROVIDER_NAME,
                        description=item["description"],
                        opportunity_status="posted",
                        official_source_url=item["source_url"],
                        official_application_url=item["application_url"],
                        raw_payload=item,
                    )
                )
            except ValidationError as error:
                logger.warning(
                    "%s_normalize_failed url=%s error=%s",
                    self.source_code,
                    item.get("application_url"),
                    error,
                )
                continue
        return opportunities

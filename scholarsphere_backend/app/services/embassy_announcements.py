"""Generic 'embassy/ministry announcement' scraper for official
organizations that publish scholarship notices as ordinary news articles
rather than a structured opportunities database - typically an embassy's
or ministry's press-release feed. No official API, RSS feed, or dataset
exists for either source below (see docs/AUTHORITATIVE_SOURCES.md #11,
#12).

Deliberately conservative extraction: only a headline, the article's own
URL, and its body text (as description) are read directly off the page.
Deadline is set only when a machine-parseable calendar date literal
appears *near a deadline-indicating phrase* (see `_DEADLINE_KEYWORDS`
below) - never just the first date found anywhere in the article. This
was fixed after a live smoke test (2026-08-22) against the real China
Embassy site caught the earlier, naive "first date in the body" approach
mislabeling an unrelated event date as a deadline: an article titled
"...Farewell Ceremony for Sierra Leonean Students..." (about students who
had *already* received their scholarships and were departing) had its
opening sentence's ceremony date ("On August 21, 2026, the Chinese
Embassy...") picked up as if it were an application deadline. Anchoring
on a nearby keyword instead correctly leaves that article's deadline
`null`, while still correctly extracting a real one (e.g. "By May 12,
2026 - Email materials... should be sent to...") from an article that
actually states a submission deadline. `official_application_url` is
left `None` (these are announcement pages, not application portals; the
article itself is the only official link known) rather than guessed. A
verification officer must read the source article directly before
approving any record from this adapter - see
docs/OPPORTUNITY_VERIFICATION_SYSTEM.md SS4/SS10.
"""

import hashlib
import logging
from datetime import date

from bs4 import BeautifulSoup
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.parsing import extract_confident_date_after, sanitize_html
from app.services.web_scraper_base import WebScraperSource, absolute_https_url, clean_text

logger = logging.getLogger(__name__)

_DEADLINE_KEYWORDS = (
    "deadline",
    "closing date",
    "submission deadline",
    "apply by",
    "submitted by",
    "no later than",
    "before ",
)


def _extract_deadline(body_text: str) -> date | None:
    for keyword in _DEADLINE_KEYWORDS:
        found = extract_confident_date_after(body_text, keyword)
        if found is not None:
            return found
    return None


class _EmbassyAnnouncementSource(WebScraperSource):
    """Shared fetch/parse logic. Subclasses set `list_path`,
    `provider_name`, `country`, and (optionally) `keywords`.
    """

    list_path: str
    provider_name: str
    country: str | None
    keywords: tuple[str, ...] = ("scholarship", "scholarships")
    max_articles: int = 10
    min_request_interval_seconds = 2.0

    def __init__(self) -> None:
        self.base_url = self._base_url().rstrip("/")

    def _base_url(self) -> str:
        raise NotImplementedError

    async def collect(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[NormalizedExternalOpportunity]:
        list_url = f"{self.base_url}{self.list_path}"
        try:
            list_soup = await self.fetch_soup(list_url)
        except ExternalAPIError as error:
            logger.warning(
                "%s_list_fetch_failed url=%s error=%s", self.source_code, list_url, error
            )
            return []

        article_urls = self._matching_article_urls(list_soup, list_url)
        normalized: list[NormalizedExternalOpportunity] = []
        for url in article_urls[: min(self.max_articles, page_size)]:
            try:
                article_soup = await self.fetch_soup(url)
            except ExternalAPIError as error:
                logger.warning(
                    "%s_article_fetch_failed url=%s error=%s",
                    self.source_code,
                    url,
                    error,
                )
                continue
            try:
                normalized.append(self._normalize(url, article_soup))
            except ValidationError as error:
                logger.warning(
                    "%s_normalize_failed url=%s error=%s", self.source_code, url, error
                )
                continue
        return normalized

    def _matching_article_urls(self, soup: BeautifulSoup, list_url: str) -> list[str]:
        urls: dict[str, None] = {}
        for anchor in soup.find_all("a", href=True):
            text = (clean_text(anchor) or "").lower()
            if not any(keyword in text for keyword in self.keywords):
                continue
            absolute = absolute_https_url(list_url, anchor["href"])
            if absolute:
                urls[absolute] = None
        return list(urls)

    def _normalize(self, url: str, soup: BeautifulSoup) -> NormalizedExternalOpportunity:
        title = clean_text(soup.find("title")) or clean_text(soup.find("h1"))
        body_node = (
            soup.select_one(".News_Body_Text")
            or soup.select_one("#article")
            or soup.find("article")
            or soup.body
        )
        body_text = clean_text(body_node)
        description = sanitize_html(body_text[:5000]) if body_text else None
        deadline = _extract_deadline(body_text) if body_text else None
        external_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:40]

        return NormalizedExternalOpportunity(
            source_code=self.source_code,
            external_id=external_id,
            title=(title or "Untitled scholarship announcement")[:1000],
            opportunity_type="scholarship",
            provider_name=self.provider_name,
            country=self.country,
            description=description,
            deadline=deadline,
            opportunity_status="posted",
            official_source_url=url,
            official_application_url=None,
            raw_payload={"url": url, "title": title},
        )


class ChinaEmbassySierraLeoneSource(_EmbassyAnnouncementSource):
    """The Chinese Government Scholarship / MOFCOM scholarship, as
    announced by the Chinese Embassy in Sierra Leone. Confirmed
    2026-08-22: the embassy's news index
    (`https://sl.china-embassy.gov.cn/eng/xwdt/`) lists article links
    including e.g. "Notice of 2026 Ministry of Commerce (MOFCOM)
    Scholarship Recruitment"; article pages carry their body text inside
    `<div class="News_Body_Text" id="article">`. No robots.txt restriction
    was found (unknown paths redirect to the homepage rather than serving
    a robots.txt with Disallow rules).
    """

    source_code = "china_embassy_sl"
    list_path = "/eng/xwdt/"
    provider_name = (
        "Embassy of the People's Republic of China in Sierra Leone "
        "(Chinese Government / MOFCOM Scholarship)"
    )
    country = "China"
    keywords = ("scholarship", "mofcom")

    def _base_url(self) -> str:
        return get_settings().china_embassy_sl_base_url


class SierraLeoneMTHESource(_EmbassyAnnouncementSource):
    """Sierra Leone's own Ministry of Technical and Higher Education
    (MTHE) - the channel the Government of Sierra Leone uses to announce
    both domestically-administered scholarships and scholarships it
    administers on behalf of partner governments (e.g. the Russian
    Federation's annual offer to Sierra Leonean students), per source
    research (see docs/AUTHORITATIVE_SOURCES.md #12).

    LIVE SOURCE TEST: NOT PERFORMED. `https://www.mthe.gov.sl` and
    `http://www.mthe.gov.sl` both refused connections from every
    environment this adapter was developed and tested in (confirmed
    2026-08-22, multiple attempts, both protocols) - this looks like a
    network/hosting issue outside this codebase's control, not a
    deliberate access restriction, but it could not be verified either
    way. This adapter is implemented against the same conservative
    announcement pattern as the confirmed-working embassy adapter above
    and unit-tested against a realistic fixture, but its selectors have
    never been checked against the real site's actual markup. Smoke-test
    this adapter against the live site before enabling its scheduled sync
    in an environment that can actually reach mthe.gov.sl.
    """

    source_code = "mthe_sierra_leone"
    list_path = "/"
    provider_name = "Sierra Leone Ministry of Technical and Higher Education (MTHE)"
    country = "Sierra Leone"
    keywords = ("scholarship", "scholarships")

    def _base_url(self) -> str:
        return get_settings().mthe_sl_base_url

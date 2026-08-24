"""National/organizational single-flagship-program scholarship sources.

Shared pattern for a government or quasi-governmental body that runs one
recurring international scholarship program described on its own page(s)
- the same shape as `app/services/chevening.py`, generalized so five more
sources (see docs/AUTHORITATIVE_SOURCES.md #13-#17) don't each duplicate
that logic. Each sync produces exactly one opportunity record with a
fixed external_id, so a changed deadline updates that record in place
(correctly triggering reverification_required if it was previously
verified - see app/services/opportunity_import.py MATERIAL_FIELDS)
instead of creating a new opportunity every cycle.

No official API, RSS feed, or dataset exists for any of these
organizations - each was checked for a robots.txt restriction (recorded
per-source in docs/AUTHORITATIVE_SOURCES.md) before being added, and every
fetch goes through the same HTTPS-only, timeout, size-capped,
per-host-rate-limited path every other scraper source uses
(app/services/web_scraper_base.py).

Deadline is set only when a machine-parseable date literal appears near
one of `deadline_keywords` (never the first date found anywhere on the
page - see app/services/embassy_announcements.py's module docstring for
why that distinction matters, discovered via a real live-testing bug in
an earlier source).
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


class _SingleProgramSource(WebScraperSource):
    """Subclasses set the class attributes below; `collect()` is shared."""

    #: Path (relative to base_url) for the page describing the program.
    overview_path: str
    #: Path for the page stating the current deadline, if different from
    #: overview_path (None means "same page").
    deadline_path: str | None = None
    #: CSS selectors tried in order for the opportunity title.
    title_selectors: tuple[str, ...] = ("h1",)
    #: If no title_selector matches, fall back to the <title> tag split on
    #: this separator (first segment) - for pages built with a page
    #: builder (Elementor, etc.) that has no single clean content heading
    #: but does have a descriptive, real <title>.
    title_tag_separator: str | None = None
    #: CSS selectors tried in order for the description content.
    content_selectors: tuple[str, ...] = ()
    #: Keywords tried in order when searching for a deadline date literal.
    deadline_keywords: tuple[str, ...] = ("deadline", "closing date")
    provider_name: str
    country: str | None
    external_id: str
    funding_type: str | None = "fully_funded"
    min_request_interval_seconds = 2.0

    def __init__(self) -> None:
        self.base_url = self._base_url().rstrip("/")

    def _base_url(self) -> str:
        raise NotImplementedError

    def _deadline_base_url(self) -> str:
        """Only overridden when the deadline page lives on a *different*
        host than the overview page (e.g. a ministry's separate "call
        status" portal subdomain) - defaults to the same base_url.
        """
        return self.base_url

    async def collect(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[NormalizedExternalOpportunity]:
        overview_url = f"{self.base_url}{self.overview_path}"
        try:
            overview_soup = await self.fetch_soup(overview_url)
        except ExternalAPIError as error:
            logger.warning(
                "%s_overview_fetch_failed url=%s error=%s",
                self.source_code,
                overview_url,
                error,
            )
            return []

        deadline_soup = overview_soup
        deadline_url = overview_url
        if self.deadline_path:
            deadline_host = self._deadline_base_url().rstrip("/")
            deadline_url = f"{deadline_host}{self.deadline_path}"
            try:
                deadline_soup = await self.fetch_soup(deadline_url)
            except ExternalAPIError as error:
                logger.warning(
                    "%s_deadline_page_fetch_failed url=%s error=%s",
                    self.source_code,
                    deadline_url,
                    error,
                )
                deadline_soup = None

        title = self._first_match(overview_soup, self.title_selectors)
        if not title and self.title_tag_separator:
            raw_title = clean_text(overview_soup.find("title"))
            if raw_title:
                title = raw_title.split(self.title_tag_separator)[0].strip() or None
        content_text = self._first_match(overview_soup, self.content_selectors)
        description = sanitize_html(content_text[:5000]) if content_text else None

        deadline = None
        if deadline_soup is not None:
            deadline_text = clean_text(deadline_soup)
            if deadline_text:
                for kw in self.deadline_keywords:
                    deadline = extract_confident_date_after(deadline_text, kw)
                    if deadline is not None:
                        break

        try:
            return [
                NormalizedExternalOpportunity(
                    source_code=self.source_code,
                    external_id=self.external_id,
                    title=title or self.external_id.replace("-", " ").title(),
                    opportunity_type="scholarship",
                    provider_name=self.provider_name,
                    country=self.country,
                    description=description,
                    deadline=deadline,
                    opportunity_status="posted",
                    funding_type=self.funding_type,
                    official_source_url=overview_url,
                    official_application_url=deadline_url,
                    raw_payload={
                        "overview_url": overview_url,
                        "deadline_url": deadline_url,
                        "title": title,
                    },
                )
            ]
        except ValidationError as error:
            logger.warning(
                "%s_normalize_failed error=%s", self.source_code, error
            )
            return []

    @staticmethod
    def _first_match(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str | None:
        for selector in selectors:
            text = clean_text(soup.select_one(selector))
            if text:
                return text
        return None


class WellsMountainInitiativeSource(_SingleProgramSource):
    """Wells Mountain Initiative (WMI) Scholars Program - a US-based
    nonprofit funding first-degree undergraduate study *in the student's
    own home region* (explicitly excludes students planning to study in
    the US/Canada/Australia/UK/Western Europe). Not tied to a single
    target country - `country` is left None rather than guessed.

    Confirmed 2026-08-22: `/prospective-scholars/` returns real
    WordPress-rendered HTML (200, ~24KB); robots.txt itself returned a
    JS bot-challenge page when fetched directly, but the actual content
    page did not, so this is being monitored rather than treated as
    fully blocked - re-check the robots.txt finding periodically. The
    page is built with the Elementor page builder and has no single
    `<h1>` (only several generic `<h2 class="elementor-heading-title">`
    section headings, none of which is a clean title on its own) - the
    real title comes from the `<title>` tag ("2026 Scholarship
    Application – Wells Mountain Initiative", split on the en dash).
    """

    source_code = "wmi_scholars"
    overview_path = "/prospective-scholars/"
    title_selectors = ()
    title_tag_separator = "–"
    content_selectors = (".entry-content", "article")
    deadline_keywords = ("deadline", "march", "submitted by")
    provider_name = "Wells Mountain Initiative (WMI)"
    country = None
    external_id = "wmi-scholars-program"
    funding_type = "partial_funding"

    def _base_url(self) -> str:
        return get_settings().wmi_base_url


class TurkiyeBurslariSource(_SingleProgramSource):
    """Türkiye Scholarships (Türkiye Bursları) - Government of Turkey,
    administered by the Presidency for Turks Abroad and Related
    Communities. Confirmed 2026-08-22: robots.txt has no restrictions;
    both the criteria page and the dated announcement page return real
    server-rendered HTML. The announcement page states e.g. "Application
    Dates: 10 January - 20 February 2026" - the closing date is what
    "deadline"/"application dates" keyword-anchored extraction picks up.
    """

    source_code = "turkiye_burslari"
    overview_path = "/scholarshipsprograms"
    deadline_path = "/announcements/turkiye-scholarships-2026-applications-121"
    title_selectors = ("h1",)
    content_selectors = ("main", "article", "body")
    deadline_keywords = ("application dates", "deadline", "closing date")
    provider_name = "Türkiye Bursları (Presidency for Turks Abroad and Related Communities)"
    country = "Turkey"
    external_id = "turkiye-burslari-scholarship"

    def _base_url(self) -> str:
        return get_settings().turkiye_burslari_base_url


class IrelandGoiIesSource(_SingleProgramSource):
    """Government of Ireland International Education Scholarships
    (GOI-IES) - funded by the Government of Ireland, managed by the
    Higher Education Authority (HEA), a statutory state agency.
    Confirmed 2026-08-22: robots.txt only disallows /wp-admin/; the
    policy page returns real WordPress-rendered HTML (200, ~37KB), but
    has no `<h1>` at all (custom theme with no content heading) and no
    `.entry-content` (its `<article>` element is a short, unrelated
    126-character snippet, not the real content) - the real title comes
    from the `<title>` tag, and the real content is in `<main>`
    (~5.4KB), confirmed by actually measuring extracted text length
    against each candidate selector rather than assuming WordPress
    convention held here.
    """

    source_code = "ireland_goi_ies"
    overview_path = "/policy/internationalisation/goi-ies/"
    title_selectors = ()
    title_tag_separator = "|"
    content_selectors = ("main", "article")
    deadline_keywords = ("deadline", "closing date", "applications close")
    provider_name = "Higher Education Authority (Government of Ireland)"
    country = "Ireland"
    external_id = "ireland-goi-ies-scholarship"

    def _base_url(self) -> str:
        return get_settings().ireland_hea_base_url


class IndiaIccrSource(_SingleProgramSource):
    """ICCR Scholarship Programme - Indian Council for Cultural Relations,
    Government of India (an autonomous organization of the Ministry of
    External Affairs). Confirmed 2026-08-22: robots.txt (standard Drupal
    pattern) does not block the scholarship programme page, and a plain
    `curl` fetch returns real server-rendered HTML (200, ~28KB) with two
    `<h1>` elements - Drupal's generic `h1.page-title` chrome (the node
    title, "...Scholarship Portal(A2A)") appears first in document
    order, and the real content heading ("ICCR Scholarship Programme")
    is nested inside `.field--name-body`, so the content-scoped selector
    is tried first.

    LIVE SOURCE TEST: BLOCKED, but by a different failure mode than the
    connection-timeout sources elsewhere in this file. This backend's
    real HTTP path (`app/core/http_client.py::get_html`, httpx +
    certifi's default trust store) fails with
    `SSLCertVerificationError: unable to get local issuer certificate` -
    iccr.gov.in's server is not sending a complete certificate chain.
    `curl` on this same machine still succeeds only because Windows'
    SChannel is more lenient about fetching a missing intermediate
    certificate than Python's strict OpenSSL/certifi verification is -
    this is not an artifact of one dev machine, it reflects a real gap
    between what a browser/curl tolerates and what a properly strict TLS
    client requires, so a standard-library Python deployment (the actual
    production stack) would very likely hit the same failure. Do **not**
    work around this with `verify=False` - a real fix requires
    iccr.gov.in's own operators to serve a complete chain. Re-test
    periodically in case they fix it.
    """

    source_code = "india_iccr"
    overview_path = "/iccr-scholarship/indian-council-cultural-relations-scholarship"
    title_selectors = (".field--name-body h1", "h1.page-title", "h1")
    content_selectors = (".field--name-body", ".node__content", "article")
    deadline_keywords = ("deadline", "last date", "closing date")
    provider_name = "Indian Council for Cultural Relations (ICCR), Government of India"
    country = "India"
    external_id = "india-iccr-scholarship-programme"

    def _base_url(self) -> str:
        return get_settings().india_iccr_base_url


class SwedishInstituteScholarshipSource(_SingleProgramSource):
    """Swedish Institute Scholarships for Global Professionals (SISGP) -
    the Swedish Institute (Svenska institutet), a Swedish government
    agency. Confirmed 2026-08-22: the scholarship page itself returns
    real HTML (200, ~32KB) with `<h1 class="content__title">SI
    Scholarship for Global Professionals</h1>`; robots.txt returned a
    403 when fetched directly (likely edge-level bot filtering on that
    specific path) but the actual content page did not, so this is
    monitored rather than treated as fully blocked.
    """

    source_code = "sweden_si_scholarship"
    overview_path = (
        "/en/apply/scholarships/swedish-institute-scholarships-for-global-professionals/"
    )
    title_selectors = ("h1.content__title", "h1")
    content_selectors = (".content__body", "article", "main")
    deadline_keywords = ("deadline", "application period", "closing date")
    provider_name = "Swedish Institute (Svenska institutet)"
    country = "Sweden"
    external_id = "sweden-si-scholarship-global-professionals"

    def _base_url(self) -> str:
        return get_settings().sweden_si_base_url


class ItalyMaeciScholarshipSource(_SingleProgramSource):
    """Scholarships for foreign students awarded by the Italian Government
    (MAECI - Ministry of Foreign Affairs and International Cooperation).
    Confirmed 2026-08-23: `robots.txt` on both hosts involved is empty/
    permissive; the overview page
    (`www.esteri.it/.../borsestudio_stranieri/`) is a real `esteri.it`
    government page with `<h1 class="entry-title h3">`; the current call's
    status is checked on a *different* host
    (`studyinitaly.esteri.it/ListaBandi`) - at fetch time it stated "The
    call for applications for MAECI grants for the 2025-2026 academic year
    is now closed. Please check our website regularly...", i.e. no open
    call with a stated deadline right now - honestly reflected as `null`
    rather than treating "closed" text as if it contained a real deadline.
    """

    source_code = "italy_maeci_scholarships"
    overview_path = (
        "/en/servizi-opportunita/opportunita/borse-di-studio/"
        "per-cittadini-stranieri/borsestudio_stranieri/"
    )
    deadline_path = "/ListaBandi"
    title_selectors = ("h1.entry-title", "h1")
    content_selectors = (".entry-content", "article", "main")
    deadline_keywords = ("deadline", "scadenza", "closing date")
    provider_name = (
        "Ministry of Foreign Affairs and International Cooperation (MAECI), Italy"
    )
    country = "Italy"
    external_id = "italy-maeci-scholarships"

    def _base_url(self) -> str:
        return get_settings().italy_esteri_base_url

    def _deadline_base_url(self) -> str:
        return get_settings().italy_studyinitaly_base_url


class GreeceIkyScholarshipSource(_SingleProgramSource):
    """Foreign Nationals Scholarships - the State Scholarships Foundation
    (IKY), a Greek government body operating since 1964. Confirmed
    2026-08-23: `robots.txt` (standard WordPress pattern) only disallows
    `/wp-admin/`; the page returns real HTML (200, ~30KB) with `<h1
    class="...entry-title...">Foreign Nationals Scholarships</h1>` (the
    `entry-title` class is present among several others, so
    `h1.entry-title` still matches). Content is in `<main>`, not
    `.entry-content` (a page-builder theme, not standard WordPress).

    The live page's text is informational rather than a current open
    call (it mentions postgraduate scholarships as "not open for this
    year" and references an old 2017-2018 language-course cycle still
    live on the page) - no date literal is present, so deadline
    extraction correctly yields `null` rather than picking up a stale
    date from years-old text.
    """

    source_code = "greece_iky_scholarships"
    overview_path = "/en/foreign-citizens-scholarships-iky/"
    title_selectors = ("h1.entry-title", "h1")
    content_selectors = ("main", "article")
    deadline_keywords = ("deadline", "closing date", "applications close")
    provider_name = "State Scholarships Foundation (IKY), Greece"
    country = "Greece"
    external_id = "greece-iky-foreign-nationals-scholarships"

    def _base_url(self) -> str:
        return get_settings().greece_iky_base_url


class SouthAfricaNrfScholarshipSource(_SingleProgramSource):
    """DSTI-NRF Postgraduate Student Funding - South Africa's National
    Research Foundation (NRF), a statutory government research-funding
    agency. Confirmed 2026-08-23: `robots.txt` (standard WordPress
    pattern) only disallows `/wp-admin/`; the funding-cycle announcement
    page returns real HTML (200, ~50KB) with real `<h1>` text and content
    in `.entry-content` (~4KB) - note `<article>` also matches but is a
    short, unrelated 52-character snippet elsewhere on the page (a
    different program mention), so `.entry-content` must be tried first.

    Deliberately does not attempt deadline extraction
    (`deadline_keywords = ()`): the page publishes a *table* of distinct
    closing dates per study level and per sub-programme (Honours,
    Master's, Doctoral, SARAO, first-time applicants, DA submissions,
    ...) - a generic "first date near a deadline-style keyword" heuristic
    would pick one row's date and mislabel it as *the* deadline for the
    whole opportunity, which is misleading even though every individual
    date is real. Left `null` on purpose so a human officer reads the
    actual table (see docs/OPPORTUNITY_VERIFICATION_SYSTEM.md SS4's
    `deadline_checked` step) rather than trusting a single misattributed
    extraction.
    """

    source_code = "south_africa_nrf"
    overview_path = "/dsti-nrf-postgraduate-student-funding-for-the-2027-academic-year/"
    title_selectors = ("h1",)
    content_selectors = (".entry-content", "main")
    deadline_keywords = ()
    provider_name = "National Research Foundation (NRF), South Africa"
    country = "South Africa"
    external_id = "south-africa-nrf-postgraduate-funding"

    def _base_url(self) -> str:
        return get_settings().south_africa_nrf_base_url

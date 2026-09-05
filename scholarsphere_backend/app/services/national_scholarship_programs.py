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


class NetherlandsNufficScholarshipSource(_SingleProgramSource):
    """NL Scholarship - Nuffic (the Dutch organisation for
    internationalisation in education), on behalf of the Dutch Ministry
    of Education, Culture and Science. Confirmed 2026-08-29: the program's
    old public name and domain, "Holland Scholarship"
    (hollandscholarship.nl), 301-redirects to this current page; `<title>`
    is literally "NL Scholarship | Study in NL", so this is the real
    current source, not a stale/retired one. `robots.txt` (standard
    Drupal pattern) does not disallow `/finances/nl-scholarship`; the page
    returns real HTML (200, ~49KB) with `<h1 class="page-header__title">`
    reading "NL Scholarship" and real content (~4.3KB) in `.node__content`
    (`article`/`main` also match but include surrounding
    nav/breadcrumb/footer chrome `.node__content` does not).

    Two deliberate honesty choices, both forced by the page's own text
    rather than a formatting quirk:
    - `funding_type = "partial_funding"`, not this base class's
      `"fully_funded"` default - the page states outright "the scholarship
      amounts to €5,000 ... Please note that this is not a full-tuition
      scholarship."
    - `deadline_keywords = ()`, same reasoning as South Africa NRF above:
      the page explicitly says "You can find the specific closing dates
      ... on the website of the institution you want to apply to" -
      Nuffic itself does not publish one closing date, since each of the
      ~30 participating Dutch institutions sets its own. Extracting any
      single date here would misattribute one institution's deadline to
      the whole program.
    """

    source_code = "netherlands_nuffic"
    overview_path = "/finances/nl-scholarship"
    title_selectors = ("h1.page-header__title", "h1")
    content_selectors = (".node__content", "article", "main")
    deadline_keywords = ()
    funding_type = "partial_funding"
    provider_name = "Nuffic"
    country = "Netherlands"
    external_id = "netherlands-nuffic-nl-scholarship"

    def _base_url(self) -> str:
        return get_settings().netherlands_nuffic_base_url


class SpainAecidScholarshipSource(_SingleProgramSource):
    """Becas MAEC-AECID - the Spanish Agency for International
    Development Cooperation (AECID), under the Ministry of Foreign
    Affairs, EU and Cooperation (MAEC). Confirmed 2026-08-29 (both via
    `curl` and this backend's actual httpx path - 200, real HTML,
    ~169KB): `robots.txt` (permissive, `Disallow:` empty for `*`) allows
    this path.

    AECID's generic `/becas-lectorados` hub page was deliberately **not**
    used - it links out to several distinct audiences (young Spaniards,
    lectorados, artistic residencies, and this program), most irrelevant
    to this platform's international-applicant focus. This adapter
    targets the one sub-page actually aimed at international applicants:
    `<h1>Becas para ciudadanos de países de América Latina, África y
    Asia</h1>` ("Scholarships for citizens of Latin America, Africa and
    Asia").

    That page itself lists several named sub-programs (Programa MÁSTER,
    Programa ESCUELA DIPLOMÁTICA, Programa ÁFRICA-MED Máster), each with
    its own distinct start/close date (e.g. Escuela Diplomática:
    21/05/2026-03/06/2026; África-Med: 02/07-15/07/2026) - the exact same
    shape already handled honestly for South Africa NRF and the
    Netherlands: `deadline_keywords = ()` deliberately, since a generic
    keyword-anchored extractor would pick one sub-program's date and
    mislabel it as *the* deadline for the whole page. No explicit
    "fully funded"/"full tuition" language was found on this page either
    (it states a monthly stipend + health insurance, aimed partly at
    civil servants for some sub-programs) - `funding_type` left at this
    class's inherited default is wrong here, so it's set to
    `"partial_funding"` rather than guessed as `"fully_funded"`.
    """

    source_code = "spain_aecid"
    overview_path = "/becas-para-ciudadanos-de-paises-de-america-latina-africa-y-asia"
    title_selectors = ("h1",)
    content_selectors = ("#main-content", "main")
    deadline_keywords = ()
    funding_type = "partial_funding"
    provider_name = (
        "Spanish Agency for International Development Cooperation (AECID)"
    )
    country = "Spain"
    external_id = "spain-aecid-scholarships"

    def _base_url(self) -> str:
        return get_settings().spain_aecid_base_url


class AustraliaDfatAwardsSource(_SingleProgramSource):
    """Australia Awards - the Australian Government's flagship
    scholarship program for students and professionals from the
    Indo-Pacific region, administered by the Department of Foreign
    Affairs and Trade (DFAT).

    Confirmed 2026-08-29: `dfat.gov.au` itself - the authoritative source
    for the program's actual intake/closing dates
    (`.../australia-awards-scholarships-opening-and-closing-dates`) -
    could not be reached from this environment. Every attempt (multiple
    user agents, both `curl` and this backend's actual httpx path)
    resulted in a TLS-handshake-stage timeout, not an HTTP error or a
    DNS failure - the same "connects, then nothing responds" pattern
    already documented for Sierra Leone's MTHE
    (`embassy_announcements.py`), not a WAF/anti-bot challenge page (no
    challenge content was ever returned to inspect). `deadline_path` is
    deliberately left unset rather than pointed at a host that cannot be
    verified reachable.

    `australiaawards.com.au` - a separate, DFAT-affiliated informational
    site (confirmed reachable: 200, real HTML, ~184KB; permissive
    `robots.txt`) - is used as the overview page instead. It states no
    specific deadline itself (an honest `deadline_keywords = ()`, not
    a defect) and has no `<h1>` (a page-builder-style homepage, the same
    shape as `WellsMountainInitiativeSource` above) - the real title
    comes from the bare `<title>Australia Awards</title>` tag. No
    "fully funded"/"tuition"/"stipend" language was found on the pages
    checked, so `funding_type` is left `None` rather than guessed -
    Australia Awards are widely known to be comprehensively funded in
    practice, but that is not something this adapter can honestly assert
    from the text it can actually read.
    """

    source_code = "australia_dfat_awards"
    overview_path = "/"
    title_selectors = ()
    title_tag_separator = "–"
    content_selectors = ("#content", "main")
    deadline_keywords = ()
    funding_type = None
    provider_name = "Department of Foreign Affairs and Trade (DFAT), Australia"
    country = "Australia"
    external_id = "australia-dfat-awards"

    def _base_url(self) -> str:
        return get_settings().australia_awards_base_url


class JapanMextScholarshipSource(_SingleProgramSource):
    """Japanese Government (MEXT/Monbukagakusho) Scholarship - Japan's
    Ministry of Education, Culture, Sports, Science and Technology, via
    the official "Study in Japan" government portal.

    Confirmed 2026-08-29: no `robots.txt` file exists on this host at all
    (the site returns its own branded 404 page for that path rather than
    a real robots.txt - treated as unrestricted, the standard meaning of
    a missing robots.txt). The scholarship-overview hub page
    (`/en/planning/scholarships/`) is a thin navigation page (~225 chars
    of real content) linking to several distinct scholarship families
    (MEXT, JASSO, "Other Scholarships") - this adapter targets the
    specific MEXT sub-page instead (`/mext-scholarships/`), which has
    real, substantial content (200, ~29KB, 8.4KB of real text: all seven
    MEXT scholarship types, embassy/university recommendation routes,
    durations, stipend amounts).

    `title_selectors = ()`: every page under this section shares the
    same generic `<h1>Scholarships</h1>` (the section-level heading, not
    the specific program name) - the real title comes from the `<title>`
    tag, split on the fullwidth vertical bar the site's own template uses
    (`｜`, U+FF5C - not the ASCII `|`): "Japanese Government (MEXT)
    Scholarship｜Study in Japan Official Website".

    `deadline_keywords = ()`: applications route through the applicant's
    home-country Japanese embassy or their university, each on its own
    schedule - the page itself states this explicitly ("be sure to
    confirm the latest edition of the application guidelines") and
    publishes no single global deadline, the same honest pattern already
    established for Ireland GOI-IES and Sweden SI (source #15, #17).

    Unlike Australia Awards (source #24) above, `funding_type` is *not*
    left `None` here - the page's own text explicitly confirms full
    funding ("tuition exempted", a monthly stipend of ¥117,000-242,000,
    and "round-trip travel expenses (airfare) provided"), so this
    pattern's inherited `fully_funded` default is left as-is rather than
    overridden, because it is actually verified by the source text this
    time.
    """

    source_code = "japan_mext"
    overview_path = "/en/planning/scholarships/mext-scholarships/"
    title_selectors = ()
    title_tag_separator = "｜"
    content_selectors = ("main",)
    deadline_keywords = ()
    provider_name = (
        "Ministry of Education, Culture, Sports, Science and Technology "
        "(MEXT), Japan"
    )
    country = "Japan"
    external_id = "japan-mext-scholarship"

    def _base_url(self) -> str:
        return get_settings().japan_mext_base_url


class BelgiumAresScholarshipSource(_SingleProgramSource):
    """Bourses de formations internationales - ARES (Académie de
    Recherche et d'Enseignement supérieur), the coordinating body for
    Wallonia-Brussels Federation universities and university colleges in
    Belgium.

    Confirmed 2026-08-29: ARES's `/bourses-de-mobilite` landing page is a
    category hub linking to ~8 distinct instruments (individual mobility
    grants for researchers, ASEM-DUO, research prizes, project funding,
    and this program) - not itself a single flagship page, so it was
    **not** used. This adapter targets the specific
    "Bourses de formations internationales" sub-page instead
    (`/fr/bourses`), which has a real, currently open call: "L'appel
    bourses 2027-2028 est ouvert !", real content (200, ~38KB), and
    `<h1>Bourses de formations internationales</h1>`. `robots.txt`
    (standard Drupal pattern, checked 2026-08-29) is permissive.

    `deadline_keywords = ()` despite the page stating a real, specific
    closing date ("Date limite : 18.09.2026") - deliberately, not because
    of ambiguity this time. That date is in `DD.MM.YYYY` numeric form,
    which `app/services/parsing.py::_CONFIDENT_DATE_PATTERN` does not
    match (it only recognizes "DD Month YYYY" / "Month DD, YYYY" literal
    forms, by design - see that pattern's own docstring on why guessing
    is avoided). Extending that shared regex to cover more date formats
    is a cross-cutting change affecting every scraper source, not
    something to do incidentally while adding one adapter, so this
    source honestly reports `null` rather than a half-solution.

    No "fully funded"/"tuition"/monetary-amount language was found on
    this specific page, so `funding_type` is left `None` rather than
    guessed, same reasoning as Australia Awards (source #24).
    """

    source_code = "belgium_ares"
    overview_path = "/fr/bourses"
    title_selectors = ("h1",)
    content_selectors = ("#main-content", "main")
    deadline_keywords = ()
    funding_type = None
    provider_name = (
        "Académie de Recherche et d'Enseignement supérieur (ARES), Belgium"
    )
    country = "Belgium"
    external_id = "belgium-ares-international-training-scholarships"

    def _base_url(self) -> str:
        return get_settings().belgium_ares_base_url


class FranceEiffelScholarshipSource(_SingleProgramSource):
    """France Excellence Eiffel Scholarship Program - established by the
    French Ministry for Europe and Foreign Affairs, administered by
    Campus France, to enable French higher education institutions to
    attract top foreign master's and PhD students.

    Confirmed 2026-08-29: `robots.txt` (standard Drupal pattern) is
    permissive; the page returns real HTML (200, ~146KB) with a clean
    `<h1>France Excellence Eiffel scholarship program</h1>` and real
    content in `.node__content` (~2.3KB). The 2026 campaign timeline is
    stated explicitly, including a real, parseable deadline: "Deadline
    for the reception of applications by Campus France: January 8, 2026".

    Like DAAD and Japan's MEXT Scholarship (both already implemented),
    applications are institution-mediated - "Only applications submitted
    by French higher education institutions are accepted" - but this is
    the same standard shape as those already-integrated sources (the
    student's chosen French institution nominates them), not the
    institution-*initiated* shape of Canada's SICS program (which this
    registry's research pass separately confirmed is not suitable: "Only
    Canadian post-secondary institutions are eligible to apply... Direct
    applications from individuals are not accepted" - no path for
    student awareness/initiation at all, unlike Eiffel's own "You are a
    student interested in participating? click here" link).

    No "fully funded"/tuition/monetary-amount language was found on this
    specific page (only linked PDF fact sheets, which this adapter does
    not fetch or parse), so `funding_type` is left `None` rather than
    guessed from Eiffel's real-world reputation as a generous scholarship
    - that is outside knowledge, not something this page's own text
    supports asserting.
    """

    source_code = "france_eiffel"
    overview_path = "/en/france-excellence-eiffel-scholarship-program"
    title_selectors = ("h1",)
    content_selectors = (".node__content", "article")
    deadline_keywords = ("deadline",)
    funding_type = None
    provider_name = "Campus France / French Ministry for Europe and Foreign Affairs"
    country = "France"
    external_id = "france-eiffel-excellence-scholarship"

    def _base_url(self) -> str:
        return get_settings().france_campusfrance_base_url


class AustriaOeadErnstMachSource(_SingleProgramSource):
    """Ernst Mach Grant - OeAD (Austria's Agency for Education and
    Internationalisation), financed by the Austrian Federal Ministry of
    Women, Science and Research.

    Confirmed 2026-08-29: `robots.txt` (checked at `oead.at`, the current
    domain - `www.oead.at` 301-redirects here) is permissive for `*`. The
    page returns real HTML (200, ~402KB) with a clean
    `<h1>Ernst Mach Grant</h1>`.

    Same shape as South Africa NRF and Spain AECID (sources #21, #23):
    this single page actually describes a *family* of named sub-grants
    (Ernst Mach - Ukraine, Ernst Mach - worldwide, Ernst Mach for
    Fachhochschule study, Ernst Mach Follow-Up, Ernst Mach - ASEA-UNINET,
    Ernst Mach - ASEA-UNINET Short-term), each with its own distinct
    closing date and, in at least one case, its own distinct scholarship
    amount ("715 euros per month" for the Ukraine-specific grant only).
    `deadline_keywords = ()` and `funding_type = None`, both deliberately
    - a generic extractor would misattribute one sub-grant's date or
    amount to the whole page.
    """

    source_code = "austria_oead"
    overview_path = "/en/study-research-teaching/overview-grants-and-scholarships/ernst-mach-grant"
    title_selectors = ("h1",)
    content_selectors = ("main",)
    deadline_keywords = ()
    funding_type = None
    provider_name = "OeAD (Austria's Agency for Education and Internationalisation)"
    country = "Austria"
    external_id = "austria-oead-ernst-mach-grant"

    def _base_url(self) -> str:
        return get_settings().austria_oead_base_url


class MoroccoAmciScholarshipSource(_SingleProgramSource):
    """Scholarships of the Kingdom of Morocco - AMCI (Moroccan Agency for
    International Cooperation), under the Ministry of Higher Education,
    for international students (predominantly African) in Moroccan
    public higher education institutions.

    Confirmed 2026-08-29: `robots.txt` itself returned a 403 (Apache
    "Forbidden") when fetched directly, but the actual content page did
    not - the same "monitored, not treated as fully blocked" situation
    already documented for the Swedish Institute (source #17). The page
    returns real HTML (200, ~42KB) with real content (~4.3KB) in
    `article`, including real figures (approximately 14,500 international
    students in Moroccan public institutions in 2019/2020, 12,500 of them
    from 47 African countries).

    `title_selectors = ()`: the page has no `<h1>` - the real title comes
    from the `<title>` tag ("Coopération Académique | AMCI", split on the
    ASCII pipe).

    `deadline_keywords = ()`: applications route through the applicant's
    home country's Moroccan diplomatic representation ("selon des
    modalités et échéances communiquées annuellement par l'AMCI aux
    représentations diplomatiques marocaines à l'étranger" - per
    third-party sourcing, not stated on this exact page), the same
    embassy-mediated pattern as Japan's MEXT Scholarship - no single
    global deadline is published on the official page itself either way.
    No funding-amount language was found on this page, so `funding_type`
    is left `None` rather than asserted from third-party figures this
    adapter cannot itself verify.
    """

    source_code = "morocco_amci"
    overview_path = "/cooperation-academique"
    title_selectors = ()
    title_tag_separator = "|"
    content_selectors = ("article",)
    deadline_keywords = ()
    funding_type = None
    provider_name = "Moroccan Agency for International Cooperation (AMCI)"
    country = "Morocco"
    external_id = "morocco-amci-scholarships"

    def _base_url(self) -> str:
        return get_settings().morocco_amci_base_url


class PortugalCamoesScholarshipSource(_SingleProgramSource):
    """Bolsas da Cooperação - Formação em Portugal - Camões, Instituto da
    Cooperação e da Língua, I.P., Portugal's institute for development
    cooperation and the Portuguese language, under the Ministry for
    Foreign Affairs.

    Confirmed 2026-08-29: `robots.txt` (a Joomla-standard pattern) does
    not disallow this path. Neither the top-level "Bolsas do Camões,
    I.P." hub (a thin 2-link navigation page, ~1.4KB) nor its
    "Bolsas da Cooperação" child (also thin, ~0.4KB, no further content)
    were used - both are pure navigation. This adapter targets the
    specific "Formação em Portugal" leaf page instead, which has real,
    substantial content (200, ~58KB, ~5.2KB of real text):
    `<h1>Formação em Portugal</h1>`, the 9 eligible partner countries
    named explicitly (Angola, Cabo Verde, Colômbia, Etiópia,
    Guiné-Bissau, Moçambique, São Tomé e Príncipe, Senegal,
    Timor-Leste), and a real funding table with actual euro amounts per
    degree level.

    Unlike every prior source in this initiative that left `funding_type`
    unasserted for lack of evidence, this page's table names *maintenance
    subsidy* ("Subsídio Manutenção", paid monthly), *tuition subsidy*
    ("Subsídio de Propina", up to €1306.25-2612.50/year depending on
    degree level), *housing subsidy* ("Subsídio Alojamento"), and an
    *installation subsidy* explicitly, with real figures for each -
    `funding_type = "fully_funded"` is kept at this pattern's default
    because it is, this time, genuinely supported by the source text, the
    same reasoning already applied to Japan's MEXT Scholarship (source
    #25).

    `deadline_keywords = ()`: "A apresentação das candidaturas decorre,
    unicamente, no país de origem junto das competentes autoridades
    locais" (applications are submitted only in the applicant's home
    country, through local authorities in partnership with Portugal's
    embassies) - the same embassy-mediated pattern already established
    for Japan MEXT and Morocco AMCI (sources #25, #29); no single global
    deadline is published on this page.
    """

    source_code = "portugal_camoes"
    overview_path = (
        "/activity/o-que-fazemos/bolsas-estudo/bolsas-camoes/"
        "bolsas-cooperacao/formacao-em-portugal"
    )
    title_selectors = ("h1",)
    content_selectors = (".item-page", "main")
    deadline_keywords = ()
    provider_name = (
        "Camões – Instituto da Cooperação e da Língua, I.P. (Portugal)"
    )
    country = "Portugal"
    external_id = "portugal-camoes-cooperation-scholarships"

    def _base_url(self) -> str:
        return get_settings().portugal_camoes_base_url


class ColombiaIcetexBecaExtranjerosSource(_SingleProgramSource):
    """Beca Colombia Extranjeros - ICETEX (Instituto Colombiano de Crédito
    Educativo y Estudios Técnicos en el Exterior), Colombia's national
    student-financing agency. Confirmed 2026-08-29 (both via `curl` and
    this backend's actual httpx path, with no spoofed user agent needed -
    200, real HTML, ~163KB): `robots.txt` is fully permissive
    (`Disallow:` empty for `*`).

    ICETEX's site (built on Liferay) puts a hidden accessibility
    `<h1 class="hide-accessible">Navegación</h1>` inside a skip-link
    `<nav>` before the real content - the same class of bug already
    documented for India ICCR. It also reuses a single
    `.journal-content-article` CSS class for at least 8 unrelated blocks
    on this page alone (empty wrappers, a "Contraste/Reducir letra" a11y
    toolbar, the site footer address block, and - critically - a
    "Historial" accordion holding the *previous* three application
    cycles' full text alongside the current one), so neither `h1` nor
    `.journal-content-article` alone is a safe selector. The one stable
    anchor is a CMS-level attribute Liferay stamps on the actual article
    content, keyed to the article's own title rather than any one
    cycle: `[data-analytics-asset-title='Beca Colombia Extranjeros']`.
    That element is unique on the page and, in document order, contains
    only the *current* cycle's block (checked 2026-08-29: "Beca Colombia
    Extranjeros 2026-2") - the three historical cycles live in a
    collapsed accordion `<div class="camp_html_acordeon">` reusing the
    same shared class but a different DOM branch, so this selector
    naturally excludes them.

    A companion page, `/becas/programa-de-reciprocidad-para-extranjeros-
    en-colombia`, was considered first but rejected: after resolving the
    same hidden-h1 issue there too, its real content is a single 330-
    character paragraph with no funding or deadline information at all -
    a thin landing page, not a usable source on its own. A second
    candidate link from that page, `/ies/convocatoria`, was also checked
    and rejected - it turned out to be an unrelated governance notice
    (an election of a public-university representative to ICETEX's board),
    not a scholarship page.

    The current cycle's page text does state a real deadline
    ("La convocatoria estará abierta hasta el próximo 5 de junio de
    2026") but written in Spanish month-name form
    ("5 de junio de 2026"), which `extract_confident_date_after`
    deliberately cannot parse (it only recognizes English month names -
    the same documented limitation already hit with Belgium ARES's
    numeric-date deadline). `deadline_keywords = ()` is set for that
    reason, not because no deadline exists on the page.

    No explicit funding-coverage language (tuition-free, stipend amount,
    "fully funded", etc.) appears on this page - only a description of
    what the program lets applicants study and a link to a separate PDF
    "bases de postulación" document this scraper does not parse -
    so `funding_type` is left unset (`None`) rather than guessed from the
    "Beca" (scholarship) name alone.
    """

    source_code = "colombia_icetex"
    overview_path = "/becas/beca-colombia-extranjeros"
    title_selectors = (
        "[data-analytics-asset-title='Beca Colombia Extranjeros'] h1",
        "h1",
    )
    content_selectors = ("[data-analytics-asset-title='Beca Colombia Extranjeros']",)
    deadline_keywords = ()
    funding_type = None
    provider_name = (
        "ICETEX - Instituto Colombiano de Crédito Educativo y Estudios "
        "Técnicos en el Exterior (Colombia)"
    )
    country = "Colombia"
    external_id = "colombia-icetex-beca-extranjeros"

    def _base_url(self) -> str:
        return get_settings().colombia_icetex_base_url


class ChileAgcidScholarshipSource(_SingleProgramSource):
    """Becas para Extranjeros - AGCID (Agencia Chilena de Cooperación
    Internacional para el Desarrollo), Chile's development-cooperation
    agency. Confirmed 2026-08-29 (both via `curl` and this backend's
    actual httpx path, no spoofed user agent needed - 200, real HTML,
    ~50KB): `robots.txt` (standard Joomla pattern, the same class already
    seen with Portugal Camões) only disallows CMS admin/internal paths,
    not this page.

    The single `<h1>Becas para extranjeros</h1>` and `<article>` element
    are both unique on the page, but the article itself describes
    *several* distinct bilateral/regional sub-programs bundled together
    - "Programa de Becas República de Chile" (open to a long list of
    Latin American/Caribbean countries), "Programa de becas ... Alianza
    del Pacífico" (Colombia, México, Perú only), a "Programa de
    Integración Transfronteriza" (Perú, Bolivia, Argentina only), and a
    "Movilidad Académica Manuela Sáenz" (Ecuador, Paraguay only) - each
    with its own eligible-country list, and the first two even have
    materially *different* funding coverage from each other (one
    explicitly excludes airfare, the other explicitly includes
    round-trip airfare). The page itself also carries an explicit
    disclaimer that this description is "a modo de referencia en base al
    procedimiento de convocatorias anteriores" (for reference only,
    based on *previous* calls' procedures) and that final terms must be
    confirmed once each call is officially published - the same
    multi-program shape already handled honestly for South Africa NRF,
    the Netherlands, and Spain AECID.

    `deadline_keywords = ()` and `funding_type = None` both follow
    directly from that: applications route through each home country's
    "Punto Focal" (focal point) rather than a single global deadline,
    and the two named funding formulas actively conflict with each
    other, so no single label can honestly describe the whole page.
    """

    source_code = "chile_agcid"
    overview_path = "/becas/becas-para-extranjeros"
    title_selectors = ("h1",)
    content_selectors = ("article",)
    deadline_keywords = ()
    funding_type = None
    provider_name = (
        "Agencia Chilena de Cooperación Internacional para el Desarrollo "
        "(AGCID), Chile"
    )
    country = "Chile"
    external_id = "chile-agcid-becas-extranjeros"

    def _base_url(self) -> str:
        return get_settings().chile_agcid_base_url


class PeruPronabecAlianzaPacificoSource(_SingleProgramSource):
    """Beca Alianza del Pacífico - PRONABEC (Programa Nacional de Becas y
    Crédito Educativo), under Peru's Ministry of Education. Confirmed
    2026-08-29 (both via `curl` and this backend's actual httpx path -
    200, real HTML, ~307KB): `robots.txt` (standard WordPress pattern)
    only disallows `/wp-admin/` and `/inicio/*`, not this path.

    This is a reciprocal student-mobility program among the four Pacific
    Alliance member states (Chile, Colombia, Mexico, Peru) - each hosts
    a fixed number of inbound exchange slots for the other three
    members' nationals. The page states explicitly: "Perú ofrece 50
    vacantes para ciudadanos extranjeros" (Peru offers 50 slots for
    foreign citizens), with its own dedicated section and numeric-date
    schedule "Para extranjeros que quieren aplicar a vacantes en Perú".
    Eligibility is real but narrow - restricted to Chilean, Colombian,
    or Mexican nationals only (not a globally open call) - the same
    honest bilateral/multilateral-partner pattern already used for
    Portugal Camões (9 named partner countries) rather than skipped for
    being non-global.

    The page has no `<h1>` at all (a WordPress page-builder layout, the
    same shape already seen with WMI and Australia Awards) - the real
    title comes from the `<title>` tag, split on the en dash (`–`,
    U+2013): "Beca Alianza del Pacífico – PRONABEC | ...".

    `deadline_keywords = ()`: the real inbound-to-Peru schedule given
    ("Del 29/5/2026 al 4/6/2026") is in `DD/MM/YYYY` numeric form, which
    `extract_confident_date_after` cannot parse (English month-name
    literals only) - the same documented limitation already hit with
    Belgium ARES and Colombia ICETEX.

    `funding_type = "partial_funding"`: the page explicitly lists
    concrete benefits (food, local transport, interprovincial and
    international transport, medical insurance) but never states tuition
    is covered or waived - this is an academic-exchange program where the
    student stays enrolled at their home institution, so the
    inherited `fully_funded` default would overstate what the page
    actually promises.
    """

    source_code = "peru_pronabec"
    overview_path = "/beca-alianza-del-pacifico/"
    title_selectors = ()
    title_tag_separator = " – "
    content_selectors = ("#content", "main")
    deadline_keywords = ()
    funding_type = "partial_funding"
    provider_name = (
        "Programa Nacional de Becas y Crédito Educativo (PRONABEC), "
        "Ministry of Education, Peru"
    )
    country = "Peru"
    external_id = "peru-pronabec-alianza-pacifico"

    def _base_url(self) -> str:
        return get_settings().peru_pronabec_base_url


class SouthKoreaGksScholarshipSource(_SingleProgramSource):
    """GKS (Global Korea Scholarship) Program - run by NIIED (National
    Institute for International Education), under South Korea's Ministry
    of Education. Confirmed 2026-08-29 (both via `curl` and this
    backend's actual httpx path, no spoofed user agent needed - 200,
    real HTML, ~124KB): `robots.txt` (`Allow: /` plus a narrow
    `Disallow: /Sims/`) does not disallow this path.

    The page's only real `<h1>` is the site logo ("StudyinKorea"), not a
    page title - the real title comes from `<h2 class="title">GKS
    (Global Korea Scholarship) Program</h2>`, the first of two matches
    for that selector (the second, "Other Scholarships", is a sibling
    tab for unrelated non-GKS programs). Content is scoped to
    `#gks-tab1`, the specific tab panel confirmed to hold only the GKS
    section (11,904 characters) - the surrounding `main` element also
    contains the "Other Scholarships" tab's content later in the DOM
    (confirmed by locating its heading at character 18,810, well past
    `#gks-tab1`'s own length), so `main` alone would risk bleeding
    unrelated content into a longer description.

    `deadline_keywords = ()`: applications route through either a
    Korean embassy (Embassy Track) or a designated university
    (University Track), each with its own sub-quota and schedule
    described only by month, not by any parseable date literal - the
    same embassy/university-track pattern already established for Japan
    MEXT. `funding_type` is kept at this pattern's `fully_funded`
    default - the page explicitly states benefits include "Airfare,
    language training costs, tuition, and study allowances", the same
    reasoning already applied to Japan MEXT and Portugal Camões.
    """

    source_code = "south_korea_gks"
    overview_path = "/in/plan/scholarship.do"
    title_selectors = ("h2.title",)
    content_selectors = ("#gks-tab1",)
    deadline_keywords = ()
    provider_name = (
        "National Institute for International Education (NIIED), "
        "Ministry of Education, South Korea"
    )
    country = "South Korea"
    external_id = "south-korea-gks-scholarship"

    def _base_url(self) -> str:
        return get_settings().south_korea_gks_base_url


class SaudiArabiaMoeScholarshipSource(_SingleProgramSource):
    """Government University Scholarships - Saudi Arabia's Ministry of
    Education (MOE). Confirmed 2026-08-29 (both via `curl` and this
    backend's actual httpx path - 200, real HTML, ~108KB): `robots.txt`
    only disallows `/Lists/`, not this path.

    The page (a SharePoint site) has no `<h1>` at all, and its `<title>`
    tag interleaves Arabic and English ("وزارة التعليم | \n\tScholarships
    in Public Universities:") with the real English text in the
    *second* segment - `title_tag_separator` only supports taking the
    first segment (by design, so every source shares one simple rule
    rather than each needing its own split-direction flag), so this
    source deliberately leaves `title_selectors = ()` and
    `title_tag_separator` unset, falling through to this pattern's
    final fallback (a title formatted from `external_id`) rather than
    mis-extracting the Arabic half or special-casing the shared base
    class for one source. Content is scoped to `.ms-rtestate-field`,
    the single SharePoint rich-text field on the page (confirmed unique,
    ~6.9KB).

    Two deliberate honesty choices, both forced by the page's own text:
    - `funding_type = None` - the page explicitly states Saudi
      government scholarships come in three distinct tiers ("free
      scholarships in which the student gets full benefits", "partial
      scholarships", and "grants paid for"), so no single funding label
      can honestly describe the whole opportunity - the same reasoning
      already applied to Chile AGCID.
    - `deadline_keywords = ()` - the page states explicitly "The opening
      date for the scholarship application program is determined
      according to the requirements of the academic year at
      universities", i.e. decentralized per-university, no single
      global deadline - the same pattern already established for the
      Netherlands (Nuffic).
    """

    source_code = "saudi_arabia_moe"
    overview_path = (
        "/en/education/ResidentsAndvisitors/Pages/"
        "PublicUniversitiesScholarships.aspx"
    )
    title_selectors = ()
    content_selectors = (".ms-rtestate-field",)
    deadline_keywords = ()
    funding_type = None
    provider_name = "Ministry of Education (MOE), Saudi Arabia"
    country = "Saudi Arabia"
    external_id = "saudi-arabia-moe-public-university-scholarships"

    def _base_url(self) -> str:
        return get_settings().saudi_arabia_moe_base_url


class QatarScholarshipsSource(_SingleProgramSource):
    """Qatar Scholarships - run by the Qatar Fund For Development (QFFD)
    in partnership with Qatari higher-education institutions (Lusail
    University, Hamad Bin Khalifa University/Geneva Graduate Institute,
    Doha Institute for Graduate Studies). Confirmed 2026-08-29 (both via
    `curl` and this backend's actual httpx path - 200, real HTML,
    ~178KB): `robots.txt` declares awareness of the newer
    "content-signal" convention but sets no actual `search`/`ai-input`/
    `ai-train` value either way for any use, and contains no classic
    `Disallow` rule for this path either - by the file's own stated
    rule ("If the website operator does not include a content signal
    for a corresponding use, the website operator neither grants nor
    restricts permission"), this is a documented absence of restriction
    for this platform's use (structured opportunity-discovery
    extraction with mandatory human officer review before publication),
    not a green light to ignore, so it's recorded explicitly here rather
    than treated as an ordinary permissive `robots.txt`.

    The homepage itself is a JS-rendered single-page app that serves
    only a near-empty "offline, read-only" shell to a non-JS client -
    `/en-US/Programs` was used instead, a server-rendered route with
    real substantial content (~47KB after cleaning). The page has no
    `<h1>`; `<title>` is "Programs\n\t\t· Qatar Scholarships", split on
    the literal newline.

    `funding_type = None`: the page describes several partner-
    institution programs with materially different funding - Lusail
    University and Doha Institute both state "Full tuition waiver...
    Monthly stipend... Medical insurance", but the HBKU/Geneva Graduate
    Institute Executive Diploma explicitly states "**Partial** tuition*
    ... *Students contribute CHF3,500 toward their tuition" - the same
    multi-program funding conflict already handled honestly for Chile
    AGCID. `deadline_keywords = ()`: no deadline-style date literal
    appears anywhere on the page.
    """

    source_code = "qatar_scholarships"
    overview_path = "/en-US/Programs"
    title_selectors = ()
    title_tag_separator = "\n"
    content_selectors = (".page_content",)
    deadline_keywords = ()
    funding_type = None
    provider_name = "Qatar Fund For Development (QFFD) - Qatar Scholarships"
    country = "Qatar"
    external_id = "qatar-scholarships-programs"

    def _base_url(self) -> str:
        return get_settings().qatar_scholarships_base_url


class SwitzerlandEskasScholarshipSource(_SingleProgramSource):
    """Swiss Government Excellence Scholarships (ESKAS) - awarded by the
    Federal Commission for Scholarships for Foreign Students (FCS/ESKAS),
    under the State Secretariat for Education, Research and Innovation
    (SBFI). Confirmed 2026-08-29 (both via `curl` and this backend's
    actual httpx path - 200, real HTML, ~198KB): `robots.txt` (`Disallow:`
    empty for `*`) is fully permissive.

    `deadline_keywords = ()`: the page explicitly states "Information on
    application deadlines and scholarship available by country of origin
    will be published here in August 2026" - deadlines are set and
    published per country of origin (applications route through Swiss
    diplomatic representations), not as one single global date on this
    page - the same embassy-mediated pattern already established for
    Japan MEXT and GKS.

    `funding_type = "partial_funding"`, not this pattern's `fully_funded`
    default - the page states a concrete monthly amount ("funding: CHF
    2450.--/month") but never states whether tuition fees are covered or
    waived, unlike Japan MEXT/Portugal Camões/GKS which explicitly
    confirm tuition coverage - so `fully_funded` would overstate what is
    actually promised here.
    """

    source_code = "switzerland_sbfi_eskas"
    overview_path = "/en/swiss-government-excellence-scholarships"
    title_selectors = ("h1",)
    content_selectors = ("main",)
    deadline_keywords = ()
    funding_type = "partial_funding"
    provider_name = (
        "Federal Commission for Scholarships for Foreign Students "
        "(FCS/ESKAS), State Secretariat for Education, Research and "
        "Innovation (SBFI), Switzerland"
    )
    country = "Switzerland"
    external_id = "switzerland-sbfi-eskas-scholarships"

    def _base_url(self) -> str:
        return get_settings().switzerland_sbfi_base_url


class PolandNawaMyFirstChoiceSource(_SingleProgramSource):
    """Poland My First Choice NAWA - the Polish National Agency for
    Academic Exchange (NAWA)'s scholarship programme for foreign
    nationals to pursue full-time second-cycle (master's) studies at
    Polish higher education institutions. Confirmed 2026-08-29 (both via
    `curl` and this backend's actual httpx path - 200, real HTML,
    ~291KB): `robots.txt` (standard Joomla pattern) does not disallow
    this path.

    The page has a hidden accessibility `<h1 class="sr-only">` before
    the real content `<h1 class="header">` - the same class of bug
    already documented for India ICCR and Colombia ICETEX -
    `title_selectors = ("h1.header", "h1")` skips it.

    NAWA runs several other named scholarship programmes (Banach NAWA,
    Ignacy Łukasiewicz, Polonista NAWA), each restricted to a different,
    narrower list of partner countries under Polish Development
    Assistance - "Poland My First Choice" is the one chosen here because
    it has the broadest eligible-country list (~40 named countries
    including much of the EU, several Asian and American countries) and
    is not itself a multi-program bundle like the others would be if
    listed on one shared page.

    `deadline_keywords = ()`: no deadline-style date literal, or even
    the words "deadline"/"closing date", appears anywhere on the page
    (confirmed by a full-text search, not just the description-length
    excerpt). `funding_type = "partial_funding"`: the page confirms
    "an exemption from tuition fees at public universities" explicitly,
    but only vaguely references "a scholarship" without ever stating a
    monthly amount or whether living costs are covered - a real but
    incomplete funding picture, not a page that never mentions funding
    at all (which would warrant `None` instead, as with Belgium ARES).
    """

    source_code = "poland_nawa_myfirstchoice"
    overview_path = "/en/students/foreign-students/poland-my-first-choice-programme"
    title_selectors = ("h1.header", "h1")
    content_selectors = (".item-page",)
    deadline_keywords = ()
    funding_type = "partial_funding"
    provider_name = "Polish National Agency for Academic Exchange (NAWA), Poland"
    country = "Poland"
    external_id = "poland-nawa-my-first-choice"

    def _base_url(self) -> str:
        return get_settings().poland_nawa_base_url


class CzechRepublicMsmtScholarshipSource(_SingleProgramSource):
    """Government Scholarships - Developing Countries - the Czech
    Republic's Ministry of Education, Youth and Sports (MŠMT), jointly
    with the Ministry of Foreign Affairs (MZV) and Ministry of Health.
    Confirmed 2026-08-29 (both via `curl` and this backend's actual
    httpx path - 200, real HTML, ~238KB): `robots.txt` (`Allow: /`, only
    `/api/` and `/preview/` disallowed) does not disallow this path.

    This site is a headless-CMS build (Next.js frontend over a
    WordPress backend, evidenced by genuine `wp-block-*` classes mixed
    with Tailwind utility classes) whose React-rendered wrapper divs
    carry auto-generated ids (e.g. `id="S:5"`, a React Server Components
    streaming-boundary id) that are deployment artifacts, not stable
    content anchors - deliberately not used as a selector for that
    reason. Instead, content is scoped to `.global-msmt`, a real,
    site-specific custom class the page's own developers added (the
    same class of choice already made for Colombia ICETEX's
    `data-analytics-asset-title` and Chile AGCID over positional/
    auto-generated alternatives).

    Unlike every other source in this pattern's default configuration,
    `deadline_keywords` is **not** overridden here - it is left at the
    base class's own default (`("deadline", "closing date")`) because
    this page has a genuine, singular, cleanly extractable deadline: a
    section literally titled "APPLICATION SUBMISSION AND DEADLINE"
    stating "Each applicant is obliged to fill in an electronic
    application form by 30 September 2026 at the latest" - confirmed by
    running `extract_confident_date_after` directly against the real
    fixture text and getting back `2026-09-30`, not guessed.

    `funding_type = None`: the specific monthly stipend amount (found
    only in third-party search summaries, not on this page) lives in a
    linked PDF/DOCX "Guidelines" document this scraper does not parse -
    no funding-coverage language appears in the page's own HTML text,
    so left unset rather than guessed from outside sources.
    """

    source_code = "czech_republic_msmt"
    overview_path = "/en/scholarships/government-scholarships-developing-countries"
    title_selectors = ("h1",)
    content_selectors = (".global-msmt",)
    funding_type = None
    provider_name = (
        "Ministry of Education, Youth and Sports (MŠMT) / Ministry of "
        "Foreign Affairs (MZV), Czech Republic"
    )
    country = "Czech Republic"
    external_id = "czech-republic-msmt-government-scholarships"

    def _base_url(self) -> str:
        return get_settings().czech_republic_msmt_base_url


class SerbiaWorldInSerbiaScholarshipSource(_SingleProgramSource):
    """"World in Serbia" - the Government of the Republic of Serbia's
    scholarship project, run by the Ministry of Education in cooperation
    with the Ministry of Foreign Affairs, for candidates from Non-Aligned
    Movement member/observer countries in Africa, Asia, and Central/South
    America. Confirmed 2026-08-29 (both via `curl` and this backend's
    actual httpx path - 200, real HTML, ~34KB): `robots.txt` only
    disallows `/Admin`, not this path.

    The page has no `<h1>` - its only heading is `<h2>Scholarships</h2>`,
    the single heading on the page and identical to the `<title>` tag's
    own first segment - generic but honest, the same acceptance of a
    real-if-plain heading already applied to WMI and other titleless-page
    sources in this pattern.

    `deadline_keywords = ()`: "Every year, the Ministry of Education
    announces a competition... in cooperation with the Ministry of
    Foreign Affairs, through consular representation offices" -
    embassy/consulate-mediated, no single global deadline published on
    this page, the same pattern as Japan MEXT and GKS. `funding_type`
    kept at this pattern's `fully_funded` default - the page explicitly
    states "study free of charge", "accommodation and food",
    "a monthly financial allowance", and "health insurance", genuinely
    comprehensive coverage.
    """

    source_code = "serbia_world_in_serbia"
    overview_path = "/scholarships"
    title_selectors = ("h2",)
    content_selectors = ("main",)
    deadline_keywords = ()
    provider_name = "Ministry of Education, Republic of Serbia"
    country = "Serbia"
    external_id = "serbia-world-in-serbia-scholarships"

    def _base_url(self) -> str:
        return get_settings().serbia_welcometoserbia_base_url


class RomaniaMfaScholarshipSource(_SingleProgramSource):
    """Romanian Government Scholarships - awarded by Romania's Ministry
    of Foreign Affairs (MFA) jointly with the Ministry of Education and
    Research, to foreign citizens from non-EU countries. Confirmed
    2026-08-29 (both via `curl` and this backend's actual httpx path -
    200, real HTML, ~125KB): `robots.txt` (`Allow: /`, only query-string
    paths and `/tmp`/`/cgi-bin/` disallowed) does not disallow this path.

    Content is scoped to `.about-text-block`, a unique, site-specific
    class - not the page's own generic `.content` class, which matches
    6 different unrelated blocks on the page (the first of which happens
    to be correct, by document order, but `.about-text-block` is a
    safer, self-evidently-unique choice rather than relying on match
    ordering).

    `deadline_keywords = ()` despite the page stating a real, specific
    closing date ("The deadline for submitting applications is 31 March
    2026") in a fully parseable "DD Month YYYY" literal - deliberately,
    not because the date itself is unparseable this time. The page's
    *first* occurrence of the word "deadline" is an unrelated, earlier
    mention ("comply with the enrolment deadline") with no date nearby;
    `extract_confident_date_after` only ever searches after a keyword's
    *first* occurrence (by design, to avoid ambiguity - see that
    function's own docstring), so it would search from that first, dateless
    mention and correctly find nothing - confirmed directly against the
    real fixture text. Extending that shared function to consider every
    occurrence of a keyword is a cross-cutting change affecting every
    scraper source, not something to do incidentally while adding one
    adapter, so this source honestly reports `null` rather than a
    half-solution.

    `funding_type` kept at this pattern's `fully_funded` default - the
    page explicitly confirms financing of tuition fees (both the
    preparatory year and the actual studies), a monthly scholarship, and
    accommodation expenses.
    """

    source_code = "romania_mfa"
    overview_path = "/scholarship-about"
    title_selectors = ("h1",)
    content_selectors = (".about-text-block",)
    deadline_keywords = ()
    provider_name = (
        "Ministry of Foreign Affairs (MFA) / Ministry of Education and "
        "Research, Romania"
    )
    country = "Romania"
    external_id = "romania-mfa-government-scholarships"

    def _base_url(self) -> str:
        return get_settings().romania_mfa_base_url


class HungaryStipendiumHungaricumSource(_SingleProgramSource):
    """Stipendium Hungaricum - the Hungarian Government's flagship
    higher-education scholarship programme, founded in 2013, supervised
    by the Ministry of Foreign Affairs and Trade, and managed by the
    Tempus Public Foundation. Confirmed 2026-08-29 (both via `curl` and
    this backend's actual httpx path - 200, real HTML, ~113KB):
    `robots.txt` is empty (no restrictions declared).

    This is a heavily JS-rendered site with no semantic heading markup
    at all (no `<h1>`-`<h4>` tags anywhere on the page) and a generic
    `<title>` ("About - Stipendium Hungaricum") that only ever yields
    the single word "About" once split - not usable as a title on its
    own. `title_selectors = ()` and no `title_tag_separator` is set,
    deliberately falling through to this pattern's final fallback (a
    title formatted from `external_id`), the same choice already made
    for Saudi Arabia MOE, rather than surfacing a one-word title.
    Content is scoped to `.main-wrapper`, the one wrapping div that
    contains the real body content (confirmed unique on the page).

    `deadline_keywords = ()`: no deadline-style date literal, or even
    the words "deadline"/"closing date", appears anywhere on the page.
    `funding_type` kept at this pattern's `fully_funded` default - the
    page explicitly states "Tuition-free education", a monthly stipend
    with real HUF/EUR figures for bachelor's/master's level, and a
    separate, higher monthly figure for doctoral level.
    """

    source_code = "hungary_stipendium_hungaricum"
    overview_path = "/about/"
    title_selectors = ()
    content_selectors = (".main-wrapper",)
    deadline_keywords = ()
    provider_name = (
        "Tempus Public Foundation, Ministry of Foreign Affairs and "
        "Trade, Hungary"
    )
    country = "Hungary"
    external_id = "hungary-stipendium-hungaricum-scholarship"

    def _base_url(self) -> str:
        return get_settings().hungary_stipendium_base_url


class MexicoAmexcidScholarshipSource(_SingleProgramSource):
    """Becas de Excelencia del Gobierno de México para Extranjeros -
    Mexico's Ministry of Foreign Affairs (SRE), through the Mexican
    Agency for International Development Cooperation (AMEXCID).
    Confirmed 2026-08-29 (both via `curl` and this backend's actual
    httpx path, after one transient timeout resolved on retry - 200,
    real HTML, ~59KB): `robots.txt` has no `User-agent: *` block at all
    (only specific Google-bot entries, all `Disallow:` empty), so no
    rule applies to this backend's generic client - unrestricted by
    the file's own terms.

    Content is scoped to `.col-sm-7.pull-left`, the article-body column
    - not the page's own generic `main` element, which also includes an
    unrelated "Publicaciones Recientes" (recent news) sidebar list of
    five other AMEXCID news items ahead of the actual scholarship
    content in document order.

    `deadline_keywords = ()` and `funding_type = None`: this specific
    overview page is a bilingual (Spanish/English) marketing summary of
    the programme and explicitly defers all concrete terms - dates,
    tuition/stipend coverage - to "las Condiciones Generales de la
    Convocatoria" (the official Call's General Conditions), reachable
    only by contacting `infobecas@sre.gob.mx` or a separate document not
    linked as plain HTML on this page - no funding-coverage language or
    date literal appears in the page's own text.
    """

    source_code = "mexico_amexcid"
    overview_path = "/amexcid/acciones-y-programas/becas-para-extranjeros-29785"
    title_selectors = ("h1",)
    content_selectors = (".col-sm-7.pull-left",)
    deadline_keywords = ()
    funding_type = None
    provider_name = (
        "Agencia Mexicana de Cooperación Internacional para el "
        "Desarrollo (AMEXCID), Secretaría de Relaciones Exteriores "
        "(SRE), Mexico"
    )
    country = "Mexico"
    external_id = "mexico-amexcid-excellence-scholarships"

    def _base_url(self) -> str:
        return get_settings().mexico_amexcid_base_url


class WorldBankJJWBGSPScholarshipSource(_SingleProgramSource):
    """Joint Japan/World Bank Graduate Scholarship Program (JJ/WBGSP) -
    the World Bank's Development Economics Vice Presidency (DEC), funded
    by the Government of Japan. Not tied to a single destination country
    - `country` is left `None` rather than guessed, matching Wells
    Mountain Initiative's pattern above: it funds master's study at 44
    participating programs across 24 universities in the US, Europe,
    Africa, Oceania, and Japan.

    Found while researching multi-source-type coverage for Sierra Leone
    specifically (see docs/COUNTRY_PROVIDER_REGISTRY.md's twelfth-pass
    note) - Sierra Leone is confirmed on the programme's own published
    eligible-countries list
    (`/en/programs/scholarships/brief/countries-eligible-for-jjwbgsp-scholarship`),
    not assumed.

    Confirmed 2026-08-30: `robots.txt` is `Allow: /` at the top level
    with only narrow, unrelated `Disallow:` rules (system paths, retired
    templates) - none matching this page. `/en/programs/scholarships/
    jj-wbgsp` returns real, substantial server-rendered HTML (200,
    ~58KB) with genuine eligibility criteria, funding coverage, and two
    dated application windows in its own text - no browser rendering
    needed.

    `title_selectors` targets `h2.lp__lead_lgtitle` specifically - the
    page's actual `<h1>` is the generic "World Bank Scholarships
    Program" heading shared by every sub-page under this program
    (Overview, Japanese Nationals, this page, ...), not this specific
    programme's real name. `content_selectors` takes the *first*
    `.lp__body_content` block only - the page has five (one per section:
    overview, eligibility, guideline links, selection process,
    benefits); the first one is the programme's own real lead
    description, not a sidebar or unrelated section.

    `deadline_keywords` tries "application window #1" before "window
    #2"/generic "deadline" - the page states both windows' dates
    together (e.g. "Application Window #1 from January 18 to February
    26, 2027"), and `extract_confident_date_after` correctly skips the
    day+month-only opening date ("January 18") for the first full
    day+month+year literal in the following 300 characters ("February
    26, 2027") - live-verified against the real fetched page, not
    assumed.
    """

    source_code = "world_bank_jjwbgsp"
    overview_path = "/en/programs/scholarships/jj-wbgsp"
    title_selectors = ("h2.lp__lead_lgtitle",)
    content_selectors = (".lp__body_content",)
    deadline_keywords = ("application window #1", "application window #2", "deadline")
    provider_name = "World Bank Group - Joint Japan/World Bank Graduate Scholarship Program"
    country = None
    external_id = "world-bank-jjwbgsp"

    def _base_url(self) -> str:
        return get_settings().world_bank_jjwbgsp_base_url


class RotaryPeaceFellowshipSource(_SingleProgramSource):
    """Rotary Peace Fellowships - The Rotary Foundation (Rotary
    International). Not tied to a single destination country -
    `country` is left `None`, same as Wells Mountain Initiative and
    World Bank JJ/WBGSP above: fellows study at one of eight Rotary
    Peace Centers worldwide. Genuinely open worldwide - unlike Aga Khan
    Foundation's ISP (also researched this pass but restricted to a
    named list of countries that does not include Sierra Leone, so not
    integrated), Rotary states no nationality restriction anywhere on
    its own page.

    Confirmed 2026-08-30: `robots.txt` allows `User-agent: *` with only
    narrow system-path `Disallow:` rules (none matching this page) and
    states `Crawl-delay: 10` - respected via
    `min_request_interval_seconds = 10.0` below, well above this
    project's usual 2-second default. The configured URL
    (`/en/our-programs/peace-fellowships`) 301-redirects to
    `/get-involved/our-programs/peace-fellowships`, which this adapter
    fetches directly - `app.core.http_client.get_html` already follows
    redirects, but fetching the resolved URL directly avoids the extra
    hop on every sync.

    `content_selectors` is a real, if fragile, finding worth recording
    honestly: this page has no semantic content wrapper (no `<article>`,
    no `id`/descriptive `class` on the body-copy container) - only
    Tailwind utility-class combinations. `div.flex.flex-col.gap-2`
    matches 3 elements on the page; `_first_match`'s `select_one` takes
    the first, which is the correct lead paragraph today, verified
    directly against the real fetched page - but a future CSS/utility
    refactor could silently break this without changing the page's
    visible content. If a resync ever finds `description=None` for this
    source going forward, that fragility is why - re-inspect the live
    page's markup before assuming a genuine content change.

    Similarly, `title_selectors = ("h1.typography-h1",)` is unique
    (exactly one match) and looks like a real, intentional design-system
    class Rotary reuses for every page's H1, so more likely to remain
    stable than the content selector above.

    `deadline_keywords` is kept active (not `()`, unlike AMEXCID) even
    though the page's own text at the time of writing states only a
    month+year for the next cycle ("available online in February 2027",
    no day) - `extract_confident_date_after` correctly returns `None`
    for that today (no full day+month+year literal), but a future cycle
    that does state an exact date will be picked up automatically
    without needing another code change.
    """

    source_code = "rotary_peace_fellowship"
    overview_path = "/get-involved/our-programs/peace-fellowships"
    title_selectors = ("h1.typography-h1",)
    content_selectors = ("div.flex.flex-col.gap-2",)
    deadline_keywords = ("application timeline", "apply by", "deadline")
    provider_name = "The Rotary Foundation (Rotary International) - Rotary Peace Fellowships"
    country = None
    external_id = "rotary-peace-fellowship"
    min_request_interval_seconds = 10.0

    def _base_url(self) -> str:
        return get_settings().rotary_peace_fellowship_base_url


class SchwarzmanScholarsSource(_SingleProgramSource):
    """Schwarzman Scholars - a fully-funded one-year master's program in

    Global Affairs at Tsinghua University (Beijing), founded by Stephen
    A. Schwarzman. Genuinely open worldwide: the program's own
    `/admissions/` page states eligibility (undergraduate degree, age
    18-28, English proficiency) with no nationality/country restriction
    anywhere - it runs a *separate* application track specifically for
    applicants with Chinese citizenship alongside the "U.S. and Global
    Applicants" track, which is not a restriction on the latter.

    Confirmed 2026-09-05: `robots.txt` has no `Disallow` at all for
    `User-agent: *` (`Crawl-delay: 10`, respected via
    `min_request_interval_seconds` below) and states nothing for
    `ClaudeBot` specifically - unlike United World Colleges (`uwc.org`),
    researched the same session and found to explicitly `Disallow: /`
    for `User-agent: ClaudeBot` by name even though `User-agent: *` is
    unrestricted; matching this project's existing Indonesia precedent
    (`docs/AUTHORITATIVE_SOURCES.md`), a named `ClaudeBot` block is
    treated as binding regardless of this backend's own configured
    User-Agent string, so UWC was not integrated.

    `title_selectors = ()`: the page's only `<h1>` is a marketing
    tagline ("Join the world's next generation of leaders."), not a
    usable title, and the `<title>` tag ("Admissions - Schwarzman
    Scholars") is too generic to split usefully either - falls through
    to the `external_id`-derived fallback ("Schwarzman Scholars"),
    the same documented pattern already used by several sources above.

    `deadline_keywords = ("countdown",)`, not the default `"deadline"`:
    the page states the same date twice, first in full-month-name form
    ("Countdown to September 9, 2026 Application Deadline") and again
    a few lines later in an abbreviated, unparseable form ("Application
    Deadline: Sept 9, 2026") - `extract_confident_date_after` finds the
    *first* occurrence of its keyword and only looks forward from there,
    so anchoring on "deadline" itself lands after the full-month-name
    date has already passed and finds only the abbreviated one (which
    `_CONFIDENT_DATE_PATTERN` doesn't match, since it requires a full
    month name) - "countdown" appears earlier and its own nearby JS
    countdown-timer `data-date="1788980400000"` millisecond-epoch
    attribute independently confirms the parsed date (2026-09-09) is
    the real one, not a coincidental regex match.
    """

    source_code = "schwarzman_scholars"
    overview_path = "/admissions/"
    title_selectors = ()
    content_selectors = ("main",)
    deadline_keywords = ("countdown",)
    provider_name = "Schwarzman Scholars (Tsinghua University)"
    country = "China"
    external_id = "schwarzman-scholars"
    min_request_interval_seconds = 10.0

    def _base_url(self) -> str:
        return get_settings().schwarzman_scholars_base_url


class KnightHennessyScholarsSource(_SingleProgramSource):
    """Knight-Hennessy Scholars - Stanford University's fully-endowed,
    multidisciplinary graduate leadership program (up to three years of
    funding to pursue any graduate degree at any of Stanford's seven
    schools). Genuinely open worldwide: its own `/admission/before-you-
    apply/eligibility` page states "Knight-Hennessy Scholars has no
    restrictions based on age, college or university, field of study, or
    career aspiration. We encourage citizens and residents of all
    countries to apply." - no nationality restriction anywhere.
    `country = "United States"` is recorded only as the program's *host*
    country (where Stanford is), matching the same host-vs-eligibility
    distinction already documented for Schwarzman Scholars above.

    Confirmed 2026-09-05: `robots.txt` has no `Disallow` at all for
    `User-agent: *` beyond a few asset/admin directories unrelated to
    this adapter (`Crawl-delay: 30`, respected via
    `min_request_interval_seconds` below), and no separate rule naming
    `ClaudeBot` - only `FemtosearchBot` and `SemrushBot` are blocked by
    name, neither of which is this backend's user agent.

    `overview_path = "/"`: the homepage has a single clean `<h1>`
    ("Knight-Hennessy Scholars at Stanford University") and a `<main>`
    with real descriptive program text - no need for the title-tag-
    fallback pattern several other sources in this file require.

    `deadline_path` points at the dedicated deadlines page rather than
    the homepage, and `deadline_keywords = ("deadline is",)` rather than
    the default `"deadline"`: `extract_confident_date_after` only scans
    300 characters past the *first* keyword occurrence on the full page
    (not just the `<main>` content), and this page's site-wide navigation
    contains an earlier, unrelated "Application Deadlines" menu link
    roughly 1,000 characters before the real sentence ("The
    Knight-Hennessy Scholars application deadline is October 6, 2026...")
    - anchoring on the default "deadline" keyword lands on that nav link
    and finds nothing within its 300-character window.  "deadline is"
    only occurs once on the page, immediately before the real date -
    verified directly against the live fixture, not assumed. (The page
    also states a *separate*, later "December 1, 2026" fallback deadline
    for the Stanford graduate-degree-program application itself, which
    this adapter deliberately does not extract - the KHS deadline is
    the one that gates eligibility for the fellowship this record
    represents.)
    """

    source_code = "knight_hennessy_scholars"
    overview_path = "/"
    deadline_path = "/admission/preparing-your-applications/application-deadlines"
    content_selectors = ("main",)
    deadline_keywords = ("deadline is",)
    provider_name = "Knight-Hennessy Scholars (Stanford University)"
    country = "United States"
    external_id = "knight-hennessy-scholars"
    min_request_interval_seconds = 30.0

    def _base_url(self) -> str:
        return get_settings().knight_hennessy_scholars_base_url

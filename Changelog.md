# Changelog

All notable changes to ScholarSphere are recorded here going forward. This
file starts from the project's current state as of 2026-08-21 — the
"Baseline" entry below summarizes what already existed rather than
reconstructing a fictional history; the real commit log
(`git log --oneline`) remains the authoritative historical record for
anything before this file existed.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Root-level documentation set (`PRD.md`, `Architecture.md`, `Design.md`,
  `Database.md`, `Coding_Rules.md`, `Road_map.md`, `Changelog.md`,
  `Task.md`) as the project's central source of truth, built by inspecting
  the actual codebase rather than assumption.

### Changed
—

### Fixed
—

### Removed
—

---

## [2026-08-29] — Browser-rendering fallback for JavaScript-only scraper sources

Added an opt-in headless-browser (Playwright/Chromium) rendering fallback
for scraper sources whose pages return no usable content over plain
HTTP - requested explicitly after this session's own research had already
hit several genuinely JS-only government sites (Egypt's Study-in-Egypt
portal, Indonesia's `.go.id` KNB site) that a plain HTTP fetch cannot
extract anything from.

### Added
- `app/services/browser_rendering.py`: a lazily-launched, reused headless
  Chromium instance; one isolated context/page per fetch, always closed;
  a semaphore bounding concurrent renders; bounded timeouts throughout
  (never a fixed `sleep()`); a response-size cap matching the existing
  HTTP path; known bot-challenge/CAPTCHA signature detection that raises
  immediately rather than attempting to solve or bypass anything - the
  same policy as every prior anti-bot finding in this project.
- `web_scraper_base.py`: a `looks_javascript_rendered()` heuristic and a
  new opt-in `WebScraperSource.allow_browser_rendering` flag, default
  `False` for every existing source - zero behavior change for all 43
  sources already in this registry. Plain HTTP is always tried first;
  only an opted-in source whose response the heuristic flags gets a
  browser-render retry, and any render failure falls back to the thin
  HTTP response rather than crashing the source's sync task.
- `Dockerfile` now installs Playwright's Chromium (`playwright install
  --with-deps chromium`) - a real, documented tradeoff of roughly
  +300-400MB on every image built from it (api, worker, and beat alike),
  noted as a candidate for a future `Dockerfile.worker` split if that
  becomes a real problem. CI installs the same browser so the real-
  browser tests actually run there too.
- New settings: `browser_render_timeout_ms`, `browser_render_max_concurrency`,
  `browser_executable_path` (left unset in every real deployment).

### Changed
- `app/core/http_client.py`: renamed the private `_validate_url` to
  public `validate_https_url` so both the HTTP and browser paths share
  one HTTPS-only check.

### Deliberately not built
SPA click-through navigation (filters, "Load more," infinite scroll),
reverse-engineering a site's own internal JSON/GraphQL API, a persisted
per-domain "rendering capability profile," and multi-language
deduplication - all premature generality with zero current users; see
`docs/AUTHORITATIVE_SOURCES.md`'s new "Browser-rendering fallback"
section for the full reasoning.

No existing source was converted to use this - all 43 already work over
plain HTTP - and the two live JS-only candidates already on record
(Egypt, Indonesia) were deliberately **not** flipped to
`allow_browser_rendering = True` and marked working: this session's own
sandboxed dev environment could launch a real headless Chromium (proven
against a local self-signed-HTTPS test server) but every attempt to
navigate it to a real external HTTPS site failed at the TLS layer through
the sandbox's own egress proxy - a sandbox limitation, not a defect in
the new module. Both country-registry entries were updated with this
exact finding.

Verified: 11 new tests (`tests/test_browser_rendering.py`), including a
genuine, non-mocked real headless-Chromium-launch-plus-JavaScript-
execution-plus-DOM-extraction test. Full backend suite: **586/586**
(`pytest -q`, up from 575). `pip-audit`: no known vulnerabilities in the
new `playwright` dependency.

## [2026-08-30] — Added Erasmus Mundus Joint Masters Catalogue

Continuing the "multiple source types per country" gap. The second real
production consumer of `pagination_engine.paginate_by_url` after
EducationUSA, independently proving that engine generalizes across
genuinely different real sites.

### Added
- `ErasmusMundusJointMastersSource` in new `erasmus_mundus_source.py` -
  ~220 EU-funded joint master's programmes, genuinely open worldwide by
  nationality, real server-rendered `?page=N` listing built with the
  EU's own ECL design system. No browser rendering needed. Wired
  end-to-end.
- 5 new tests against three real fixture pages (page 0, page 1, and a
  genuinely-past-the-last-page response). Full backend suite confirmed
  green: **684/684** (`pytest -q`, up from 679).

### Changed
- `tests/test_opportunity_import.py`'s hardcoded source count/set
  updated for the new source.

A real, live-observed proof of this project's HTTPS-only discipline:
two of the ~220 programmes' own listed websites use plain `http://`
rather than `https://` and are correctly, silently dropped by the
shared HTTPS-only check rather than "fixed" by guessing a scheme -
confirmed directly in the real fixtures.

## [2026-08-30] — Added Rotary Peace Fellowships

Continuing the "multiple source types per country" gap. Researched (but
did not integrate) the Aga Khan Foundation International Scholarship
Programme - real and legitimate, but its own published country list
does not include Sierra Leone, rejected on eligibility grounds. Then
researched and implemented Rotary Peace Fellowships instead - genuinely
open worldwide, real static content.

### Added
- `RotaryPeaceFellowshipSource` in `national_scholarship_programs.py` -
  real, worldwide (no nationality restriction), static server-rendered
  content. `robots.txt`-compliant `Crawl-delay: 10` respected via a
  source-specific 10-second minimum request interval. Wired end-to-end.
- 2 new tests against a real fixture captured unmodified from the fetch.
  Full backend suite confirmed green: **679/679** (`pytest -q`, up from 677).

### Changed
- `tests/test_opportunity_import.py`'s hardcoded source count/set
  updated for the new source.

One fragility recorded honestly rather than silently risked: the page
has no semantic content wrapper, only Tailwind utility-class
combinations, so the description selector is more brittle than most
sources here - verified working today, documented in both the source's
own docstring and `docs/AUTHORITATIVE_SOURCES.md`.

## [2026-08-30] — Added Joint Japan/World Bank Graduate Scholarship Program (JJ/WBGSP)

Continuing the "multiple source types per country" gap from the previous
pass. Implemented a real next candidate found while researching sources
genuinely eligible for Sierra Leone applicants.

### Added
- `WorldBankJJWBGSPScholarshipSource` in `national_scholarship_programs.py`
  - a real, major World Bank Group program (funded by the Government of
    Japan), not tied to a single destination country. Sierra Leone is
    confirmed on the programme's own published eligible-countries list,
    checked directly rather than assumed. Its overview page is real
    static server-rendered HTML - no browser rendering needed, unlike
    the Mastercard Foundation candidate from the previous pass. Wired
    end-to-end; this is the source registry's first
    `international_organization`-typed entry.
- 1 new test against a real fixture captured unmodified from the fetch.
  Full backend suite confirmed green: **677/677** (`pytest -q`, up from 676).

### Changed
- `tests/test_opportunity_import.py`'s hardcoded source count/set
  updated for the new source.

Also re-tested `sl.usembassy.gov/educational-professional-exchanges/`
(Sierra Leone's US Embassy exchanges page) - still a persistent
"Technical Difficulties" error, not fixed since the original Fulbright
research flagged it.

## [2026-08-30] — Research pass: Mastercard Foundation Scholars Program (not integrated)

Investigated as a candidate FOUNDATION-type source directly relevant to
Sierra Leone (58,000+ scholarships committed, 62 partner universities
across Africa; `robots.txt` explicitly allows `ClaudeBot`). Not
integrated: the program overview has no single deadline/application
(decentralized to partner institutions, same reason Canada/Denmark/Wales
were rejected), and the real per-institution listing page is a
client-side widget with no server-rendered fallback. Live-tested
Chromium against the exact URL to reconfirm this sandbox's standing
external-browser-automation limitation rather than assuming it still
applies. Documented as a strong candidate for a future session with
working outbound browser access. No code changes.

## [2026-08-29] — 40-country audit: United States and China closed, Eswatini reachability fixed

Cross-referenced the platform's exact 40-country target list against
`docs/COUNTRY_PROVIDER_REGISTRY.md` (already thorough from prior
sessions — 38 of 40 already had a real, live-tested classification).
Closed the two that had never been researched, and fixed one real bug
found while re-checking.

### Added
- `app/services/educationusa_source.py` — a new United States source:
  `educationusa.state.gov/find-financial-aid` (US Department of State),
  a real, live, plain-HTTPS paginated database of 277+
  institution-specific scholarships. The first production consumer of
  `app/services/pagination_engine.py`'s `paginate_by_url`. Wired
  end-to-end (config, source registry, Celery beat + task,
  opportunity_sync mapping) and verified against 3 genuinely separate
  real fetches (page 0, page 1, and a real `?page=40` zero-row
  "past the last page" response), all saved as test fixtures.

### Changed
- `eswatini_slas_base_url` corrected from `https://www.slas.gov.sz`
  (still times out) to `https://slas.gov.sz` (bare host, genuinely
  reachable — 200, real content, 3/3 attempts). The real page turned out
  to be a domestic student-loan portal with no scholarship/SADC content,
  so `EswatiniSlasSource` correctly still extracts zero records from it
  — reclassified `NOT_SUITABLE` rather than claimed newly working.
- `tests/test_opportunity_import.py`'s hardcoded source count/set
  updated for the new source; two real-Chromium new-tab-detection tests
  given a longer timeout after being found genuinely flaky under
  full-suite system load (not a production bug).

### Deliberately not touched
China: the China Scholarship Council (CSC) is a real, major program, but
every candidate page — including `robots.txt` itself — returns HTTP 412
or an obfuscated JS anti-bot challenge page, the same class of
protection as Cyprus/Brazil. Classified `BLOCKED`, never bypassed.

The remaining 35 (of 40) countries already had defensible research on
record and were not re-litigated without new information. The spec's
"multiple source types per country" ambition (university + government +
embassy + foundation sources for every country) remains a real, larger
gap beyond one session's scope — most countries here have exactly one
flagship government source today.

Verified: 6 new tests. Full backend suite confirmed green: **676/676**
(`pytest -q`, up from 670).

## [2026-08-29] — Hybrid Scholarship Discovery and Verification Engine: the rest of the spec

A continuation of the browser-rendering fallback above, building out the
remaining requirements from the 27-section hybrid-discovery-engine
specification: SPA interaction, pagination, infinite scroll, filters,
application-link discovery and validation, cookie/consent handling,
console/page-error monitoring, content-completeness scoring, source
capability profiling, metrics, and a declarative adapter architecture.
Additive throughout - none of the 43 existing scraper sources changed
behavior or was migrated onto any of the new engines.

### Added
- `app/services/browser_interaction.py` (`BrowserInteractionEngine`):
  click/wait-for-selector/extract-URL/capture-content primitives, plus
  `wait_for_navigation_or_change`, racing a new tab, a URL change
  (including a client-side `history.pushState` route), or an in-page DOM
  change under a bounded timeout - never `sleep()`. New
  `browser_rendering.interactive_session` context manager for anything
  needing more than one render.
- `app/services/pagination_engine.py`: `paginate_by_url` (URL-parameter
  pagination, no browser needed) and `paginate_by_click` (one function
  handling both a "Next" button and a "Load More" control via
  deduplication-by-key). Bounded by new `MAX_PAGES_PER_SOURCE`/
  `MAX_RECORDS_PER_SOURCE` settings.
- `app/services/infinite_scroll_engine.py`: render/extract/scroll/wait-
  for-real-DOM-growth/compare/continue, bounded by new
  `MAX_SCROLL_ITERATIONS`/`SCROLL_STAGNATION_LIMIT` settings.
- `app/services/filter_engine.py`: applies a caller-described filter set
  (auto-detecting `<select>` vs. a clickable control; an absent selector
  is skipped, never an error) and `iter_filter_combinations`, a bounded
  cartesian product generator - never an automatic full sweep.
- `app/services/application_link_discovery.py`: finds "Apply"-style
  controls, reads `href` directly where present, and for a control
  without one, clicks through and records where that led (new tab / URL
  change / in-page modal). Bounded to 5 href-less clicks per page. Never
  fills in a form, creates an account, or submits anything.
- `app/services/application_link_validation.py`: classifies a discovered
  application URL `VALID_OFFICIAL_APPLICATION` /
  `VALID_AUTHORIZED_EXTERNAL_PORTAL` / `INFORMATION_PAGE_ONLY` / `BROKEN`
  / `BLOCKED` / `UNKNOWN` by HTTP status, redirect chain, final domain,
  and content - only the source's own domain or a pre-authorized portal
  domain can ever come back `VALID_*`.
- `app/services/content_completeness.py`: scores a scraper adapter's raw
  extracted fields 0-100 across CRITICAL/IMPORTANT/OPTIONAL tiers, run
  before attempting to construct a `NormalizedExternalOpportunity`;
  `needs_review` is forced True whenever any CRITICAL field is missing
  regardless of score.
- `app/services/source_capability_profile.py`: in-process (not
  persisted) memory of what's been observed about a domain - requires
  JS, pagination shape, cookie banner, etc. - recorded automatically by
  every module above. Deliberately observability, not automation:
  nothing reconfigures a source's own fetch behavior from this evidence
  alone.
- `app/services/scraper_metrics.py` (process-wide counters + derived
  ratios; an untouched ratio reads `None`/`null`, never a fabricated
  `0.0`) and `GET /api/v1/scraper-metrics`
  (`app/api/routes/scraper_metrics.py`, staff-gated).
- `app/services/scraper_adapters.py`: `GenericHTMLAdapter`/
  `GenericJSAdapter`/`GovernmentPortalAdapter`/`UniversityPortalAdapter`/
  `SPAAdapter` base classes for a future declaratively-describable
  source - none of the 43 existing sources migrated.
- New settings: `PLAYWRIGHT_HEADLESS` (forced `true` in production),
  `AUTO_ACCEPT_REQUIRED_COOKIES`, `MAX_PAGES_PER_SOURCE`,
  `MAX_RECORDS_PER_SOURCE`, `MAX_SCROLL_ITERATIONS`,
  `SCROLL_STAGNATION_LIMIT`.

### Changed
- `app/services/browser_rendering.py`: added generic cookie/consent-
  banner detection and (only within a detected cookie/consent container,
  never page-wide) auto-accept, and structured console-error/page-error/
  failed-request/HTTP-error capture classified INFO/WARNING/ERROR/
  CRITICAL - a known third-party analytics/tracker failure is downgraded,
  never used to fail an otherwise-good render.

### Deliberately not built
Reverse-engineering a site's own internal JSON/GraphQL API (no JS-only
candidate on record has one) and multi-language deduplication - both
premature generality with zero current users. See
`docs/AUTHORITATIVE_SOURCES.md`'s requirement matrix for the full
per-requirement status.

Still not independently verified against a real external site - same
sandbox limitation as the original browser-rendering fallback (the
egress proxy fails at the TLS layer for real Chromium navigation to
external HTTPS sites). Every new module is proven against real Chromium
and purpose-built local mock pages, which proves the Playwright
mechanics genuinely work, not what a concrete adapter for a real site
like Egypt or Indonesia would need to configure. Docker also remains
unbuildable in this sandbox (daemon not running).

Verified: 84 new tests across 12 new test files plus additions to
`tests/test_browser_rendering.py` (11 more there). Full backend suite
confirmed green after every phase; final count **670/670** (`pytest -q`,
up from 586).

## [2026-08-29] — Second beyond-the-original-request pass: 8 more countries researched, zero new sources — an honest null result

A second batch of 8 countries entirely outside the original
master-prompt request: New Zealand, Singapore, Pakistan, Philippines,
Nigeria, Ghana, Rwanda, Jordan. Unlike every prior pass, **this one adds
no new sources** — recorded here in full because a real, honest research
outcome, not a gap:

- **New Zealand**: Manaaki New Zealand Scholarships is real and
  well-documented, but the entire site is built with Next.js CSS
  Modules — every wrapper down to the `<h1>`'s immediate parent uses an
  auto-generated hashed class, and even the generic `<main>` tag is
  non-unique with the wrong element first. No selector is safe from
  breaking on the next deploy.
- **Singapore**: SINGA no longer has a dedicated program page (every
  guessed/search-suggested URL 404s, confirmed against the site's full
  sitemap.xml); the one current offering is institution-initiated, not
  individually-applicable, the same shape already ruled out for Canada.
- **Pakistan**: HEC's domain fails TLS certificate verification on
  every hostname tried — the same class of finding as India ICCR and
  South Africa NRF.
- **Philippines**: CHED's official site returns 403 Forbidden, 3/3
  attempts.
- **Nigeria, Ghana, Rwanda**: each national scholarship body turned out
  to be outbound/domestic-only — no program was found funding foreign
  nationals to study in-country.
- **Jordan**: a real, genuinely bidirectional inbound mechanism exists
  across 25 partner countries, but the actual page content is only two
  sentences plus a country list — no funding, deadline, or application
  detail — the same thin-content bar that already ruled out Colombia's
  reciprocity page and Malaysia's MIS.

No code changes this round — nothing was implementable, so no source
classes, tests, or fixtures were added. `docs/COUNTRY_PROVIDER_REGISTRY.md`
updated with a new dedicated section recording all 8 findings.

Country coverage unchanged at 31 real sources — this pass added negative
findings only, which still have value: future sessions won't re-research
these 8 countries from scratch.

## [2026-08-29] — Beyond the original request: 8 new countries researched; Hungary and Mexico added

With every country/region named in the original master-prompt request
researched, this pass picked 8 new countries entirely outside that
request, spanning previously-untouched regions: Hungary, Mexico,
Indonesia, Malaysia, Vietnam, Egypt, Israel, Kenya. 2 real sources added:

- **Hungary** (Stipendium Hungaricum): a heavily JS-rendered site with
  no semantic heading markup at all and a `<title>` tag that only ever
  yields the single word "About" once split — falls back to a title
  formatted from `external_id`. `funding_type = "fully_funded"` —
  explicit tuition-free education plus real HUF/EUR monthly stipend
  figures.
- **Mexico** (AMEXCID Excellence Scholarships): content scoped to the
  article-body column specifically, not `main` (which also pulls in an
  unrelated news sidebar). `funding_type = None` — the overview page
  explicitly defers all concrete funding/deadline terms to a separate
  "Condiciones Generales" document not linked as plain HTML.

The other 6 were investigated and found unsuitable, for genuinely
varied reasons: **Indonesia** `BLOCKED` (official site is a pure JS app
with zero server-rendered content; a content-rich companion site
explicitly disallows `ClaudeBot` by name in its `robots.txt`, honored
rather than routed around with a different User-Agent). **Vietnam**
`BLOCKED` (the one candidate site doesn't support HTTPS at all — this
backend's HTTPS-only requirement is a security boundary, never relaxed
for one adapter). **Egypt** `BLOCKED` (official portal is a pure
client-side JS SPA on every route checked). **Israel** `BLOCKED` (MFA
scholarship page returns 403 on 3/3 attempts). **Malaysia**
`NOT_SUITABLE` (real program, but the page is too thin — real detail
lives only in an unparsed PDF). **Kenya** `NO_RELIABLE_SOURCE_FOUND`
(the one page found is an outbound-opportunity database, not an inbound
single program).

Source count 41 → 43. `docs/AUTHORITATIVE_SOURCES.md` (#42-#43) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` (new dedicated "Beyond the original
request" section covering all 8 findings) fully updated.

Verified: 4 new tests (2 per source) against real fixtures; full backend
suite **575/575** (`pytest -q`).

31 countries/regions now have at least one real source (up from 29),
including 2 entirely outside the original master-prompt request.

## [2026-08-29] — Europe: first research pass on the last 8 named countries; 5 sources added — no named region left unresearched

A dedicated **first** research pass on the eight remaining named European
countries from the original master-prompt request — the last
unresearched region. 5 real sources added:

- **Switzerland** (SBFI ESKAS): `funding_type = "partial_funding"` — a
  concrete monthly amount (CHF 2450) is stated but tuition coverage is
  never mentioned.
- **Poland** (NAWA "Poland My First Choice"): hidden accessibility
  `<h1 class="sr-only">` before the real `<h1 class="header">` — the
  same bug class as India ICCR and Colombia ICETEX.
- **Czech Republic** (MŠMT Government Scholarships): a headless
  Next.js-over-WordPress build whose React wrapper divs carry
  auto-generated `id="S:N"` streaming-boundary ids — deliberately not
  used as a selector; scoped instead to `.global-msmt`, a real custom
  class. Unusually, `deadline_keywords` is **left at the base class's
  default** rather than disabled — this page has a genuine, singular,
  cleanly extractable deadline ("by 30 September 2026 at the latest"),
  confirmed directly against the real fixture. The first source in this
  whole initiative where deadline extraction is actually used.
- **Serbia** ("World in Serbia"): no `<h1>` — the page's only heading is
  a plain `<h2>Scholarships</h2>`. `funding_type = "fully_funded"` —
  explicit free tuition, accommodation, food, monthly allowance, and
  health insurance.
- **Romania** (MFA Government Scholarships): a genuinely interesting
  deadline-extraction near-miss — the page states a real, parseable
  deadline ("31 March 2026") but the shared date-extraction function
  only searches after a keyword's *first* occurrence, and this page's
  first "deadline" mention is an unrelated, dateless one earlier in the
  eligibility section — confirmed directly against the real fixture that
  extraction correctly (if unluckily) returns nothing.

**Croatia** was investigated and found `NOT_SUITABLE`: every source is a
year-dated "Call for Applications" page (seven different such pages
found spanning 2020/2021 through 2026/2027), no evergreen "about" page,
plus nomination-only eligibility. **Norway** came back
`NO_RELIABLE_SOURCE_FOUND`: its two historical inbound programs (the
"Quota Scheme" and NORSTIP) are both confirmed defunct/cancelled.
**Finland** was found `NOT_SUITABLE`: its one national program (EDUFI
Fellowship) states on its own official page that it "will end at the end
of 2025. New applications cannot be submitted after 17.10.2025" —
already past by this session's date, despite several third-party
aggregators still listing it as "active in 2026" (exactly why this
project verifies against primary sources).

Source count 37 → 41. `docs/AUTHORITATIVE_SOURCES.md` (#37-#41) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` (new dedicated "Europe" section
covering all 8 findings) fully updated.

Verified: 10 new tests (2 per source) against real fixtures; full backend
suite **571/571** (`pytest -q`).

29 of the master prompt's ~40 named countries/regions now have at least
one real source (up from 24). **No named country or region from the
original master-prompt request remains unresearched** — South America,
the remaining named Asian countries, and the remaining named European
countries have each now had a full first-pass research effort.

## [2026-08-29] — Asia: first research pass on South Korea, Saudi Arabia, Qatar, Thailand; 3 sources added

A dedicated **first** research pass on the four remaining named Asian
countries from the master prompt (China and India already had narrower
coverage). 3 real sources added:

- **South Korea** (GKS Global Korea Scholarship Program, run by NIIED):
  the page's only `<h1>` is the site logo, not a title — solved with
  `<h2 class="title">GKS (Global Korea Scholarship) Program</h2>`, the
  first of two matches (the second is a sibling "Other Scholarships"
  tab). Content scoped to `#gks-tab1`, confirmed to hold only the GKS
  section.
- **Saudi Arabia** (MOE Government University Scholarships): no `<h1>`,
  and the `<title>` tag interleaves Arabic and English with the real
  text in the second segment — since `title_tag_separator` only
  supports the first segment, this source falls back to a title
  formatted from `external_id` rather than mis-extracting the Arabic
  half or special-casing the shared base class.
- **Qatar** (Qatar Scholarships, run by the Qatar Fund For
  Development/QFFD): the homepage is a JS-rendered SPA serving only an
  empty "offline" shell to a non-JS client — used `/en-US/Programs`
  instead, a server-rendered route with real content. `robots.txt` uses
  the newer "content-signal" convention but sets no actual value for
  any use — documented explicitly as a genuine absence of restriction.

All three follow this initiative's established honesty discipline:
`funding_type = None` wherever the page bundles sub-programs with
conflicting funding coverage (Saudi Arabia's three explicit tiers,
Qatar's partner institutions with differing tuition coverage), kept at
`fully_funded` only where genuinely supported (South Korea's explicit
"Airfare, language training costs, tuition, and study allowances").

**Thailand** was investigated and found `NOT_SUITABLE`, not implemented:
the government's real scholarship info lives in a rolling year-dated
announcement feed (`ops.go.th`), and a second candidate "about" page
(TICA's own TIPP overview) was real but frozen content from ~2013-2015,
not the current cycle.

Source count 34 → 37. `docs/AUTHORITATIVE_SOURCES.md` (#34-#36) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` (new dedicated "Asia" section
covering all 4 findings) fully updated.

Verified: 6 new tests (2 per source) against real fixtures; full backend
suite **561/561** (`pytest -q`).

24 of the master prompt's ~40 named countries/regions now have at least
one real source (up from 21). The only remaining unresearched territory:
the remaining named European countries (Switzerland, Poland, Czech
Republic, Croatia, Serbia, Romania, Norway, Finland).

## [2026-08-29] — South America: first research pass across all 9 countries; Colombia, Chile, Peru added

A dedicated **first** research pass on South America — none of its 9
countries had any prior research in this registry. 3 real sources added:

- **Colombia** (ICETEX Beca Colombia Extranjeros): the site (Liferay) has
  a hidden accessibility `<h1 class="hide-accessible">Navegación</h1>`
  before the real content (the same bug class already documented for
  India ICCR) and reuses one `.journal-content-article` class for 8+
  unrelated blocks, including a "Historial" accordion holding the three
  *previous* application cycles. Solved with the one stable, unique
  anchor Liferay stamps on the actual article content:
  `[data-analytics-asset-title='Beca Colombia Extranjeros']`. A thinner
  companion page and an unrelated governance-notice sub-page were both
  fetched and rejected first.
- **Chile** (AGCID Becas para Extranjeros): a single unique `<h1>` and
  `<article>`, but the article bundles several distinct
  bilateral/regional sub-programs with materially conflicting funding
  formulas, plus the page's own disclaimer that terms are
  reference-only pending each call's official republication — the same
  multi-program shape already handled honestly for South Africa NRF,
  the Netherlands, and Spain AECID.
- **Peru** (PRONABEC Beca Alianza del Pacífico): a reciprocal
  student-mobility program among the four Pacific Alliance member
  states — Peru offers 50 inbound slots for Chilean/Colombian/Mexican
  nationals specifically, the same honest bilateral-partner pattern as
  Portugal Camões. No `<h1>` at all — title falls back to the `<title>`
  tag split on the en dash.

All three follow this initiative's established honesty discipline:
`deadline_keywords = ()` wherever the real deadline is stated but in a
numeric or non-English-month form the shared parser cannot recognize
(`DD/MM/YYYY`, Spanish month names), and `funding_type` left `None` or
set to `"partial_funding"` rather than guessed wherever the page's own
funding language is absent, conflicting, or incomplete.

**Brazil** was investigated and found genuinely `BLOCKED`, not
implemented: the real program (PEC-G) has rich real content confirmed
via a browser-spoofed `curl` fetch, but this backend's actual unspoofed
httpx client is served a JavaScript bot-challenge page 3/3 attempts —
the same class of finding as Cyprus's Azure WAF block, and bypassing it
is out of scope by the same policy. **Argentina, Uruguay, Paraguay**
confirmed `NOT_SUITABLE` (a multi-entry database instead of a single
page, or residency-restricted eligibility not open to prospective
international applicants). **Ecuador, Bolivia** came back
`NO_RELIABLE_SOURCE_FOUND`.

Source count 31 → 34. `docs/AUTHORITATIVE_SOURCES.md` (#31-#33) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` (new dedicated "South America"
section covering all 9 findings) fully updated.

Verified: 6 new tests (2 per source) against real fixtures; full backend
suite **555/555** (`pytest -q`).

21 of the master prompt's ~40 named countries/regions now have at least
one real source (up from 18). Remaining unresearched territory: most of
Asia (South Korea, Saudi Arabia, Qatar, Thailand) and the remaining named
European countries (Switzerland, Poland, Czech Republic, Croatia, Serbia,
Romania, Norway, Finland).

## [2026-08-29] — Portugal (Camões) source added — the country-registry queue is now empty

Portugal was the last country this registry had queued from the original
research pass. Neither the "Bolsas do Camões, I.P." hub nor its "Bolsas
da Cooperação" child (both fetched and confirmed to be thin, content-free
navigation pages) were used — this adapter targets the specific
"Formação em Portugal" leaf page instead, with real substantial content:
9 named eligible partner countries and a real funding table with actual
euro amounts (a maintenance subsidy, a tuition subsidy up to
€1,306.25–2,612.50/year, a housing subsidy, and an installation subsidy).

Unlike Belgium/Austria/Morocco earlier in this same research initiative,
`funding_type = "fully_funded"` **is** kept here — genuinely supported by
that funding table, the same reasoning already applied to Japan's MEXT
Scholarship. `deadline_keywords = ()` — embassy-mediated applications,
same pattern as Japan MEXT and Morocco AMCI.

Source count 30 → 31. `docs/AUTHORITATIVE_SOURCES.md` (#30) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` fully updated. **The queue this
registry has tracked since 2026-08-23 is now genuinely empty**: every
candidate it ever identified is either a real, live-verified source or a
confirmed, evidence-backed non-candidate (`NOT_SUITABLE`, `BLOCKED`, or
`NO_RELIABLE_SOURCE_FOUND`) — none left as stale guesses.

Verified: 2 new tests against a real fixture; full backend suite
**549/549** (`pytest -q`).

18 of the master prompt's ~40 named countries/regions now have at least
one real source (up from 17). The only way to add more from here is a
first research pass on countries entirely outside this registry — all of
South America, most of Asia, and most of the remaining named European
countries have not been touched at all.

## [2026-08-29] — A real research pass: Belgium, France, Austria, Morocco added; Canada, Denmark confirmed unsuitable

A dedicated research pass — not a fetch-and-wire pass — on the remaining
queue: Belgium (ARES), Canada (EduCanada), France (Campus France),
Austria (OeAD), Morocco (AMCI/"Maroc Alumni"), and Denmark's
long-standing "needs a dedicated follow-up search" item. 4 of 6 turned
into real, live-verified sources; 2 were confirmed genuinely unsuitable
rather than left as stale guesses.

**Belgium (ARES)** targets the specific "Bourses de formations
internationales" sub-page (a real, currently-open call), not the general
mobility-grants hub, which links to ~8 unrelated instruments. Its real
deadline ("18.09.2026") is deliberately not extracted — that's
`DD.MM.YYYY` numeric form, which the shared date regex in
`app/services/parsing.py` doesn't match by design; extending that regex
is a cross-cutting change out of scope for one adapter.

**France (Campus France Eiffel)** is a genuinely clean single-flagship
page with a real, parseable deadline ("January 8, 2026") that *is*
extracted. Institution-mediated applications, confirmed to be the same
standard shape as DAAD/Japan MEXT (already implemented) by directly
reading the page, not assumed.

**Austria (OeAD Ernst Mach Grant)** follows the same multi-program-hub
shape as South Africa NRF/Spain AECID — 6 named sub-grants, each with its
own deadline and, for one, its own distinct monthly amount — `deadline_
keywords = ()` deliberately.

**Morocco (AMCI)** resolves the prior uncertainty about "Maroc Alumni"'s
canonical URL: the real official page is `amci.ma/cooperation-academique`.
Embassy-mediated, same honest null-deadline pattern as Japan MEXT.

**Canada — confirmed NOT_SUITABLE, not implemented.** Live-fetched
EduCanada's actual pages: its broadest international-applicant program
(Study in Canada Scholarships) states outright "Only Canadian
post-secondary institutions are eligible to apply on this call... Direct
applications from individuals are not accepted" — no path for an
individual applicant to initiate anything, unlike France's Eiffel
program. Corrected from a vague "needs deeper research" note to a
specific, evidence-backed finding.

**Denmark — confirmed NOT_SUITABLE, not implemented.** The dedicated
follow-up search this entry itself called for was done: Danish
government scholarships are "administered by the Danish universities,
who each select the students" — genuinely decentralized, no single
national awarding body. Corrected from "no reliable source found"
(implying more searching might help) to a confirmed structural fact.

No monetary/"fully funded" language was found on any of the 4 new
sources' actual pages, so `funding_type = None` on all four — not
guessed from general reputation.

Source count 26 → 30. `docs/AUTHORITATIVE_SOURCES.md` (#26-#29) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` fully updated (all 6 countries'
entries corrected with what was actually found; only Portugal remains as
a genuine queued candidate).

Verified: 8 new tests against real fixture HTML, all passing on the
first run; full backend suite **547/547** (`pytest -q`).

17 of the master prompt's ~40 named countries/regions now have at least
one real source (up from 13). South America, most of Asia, and most of
the remaining named European countries remain completely unresearched.

## [2026-08-29] — Japan (MEXT Scholarship) source added; Wales corrected to NOT_SUITABLE

Continued the country-coverage queue with Wales and Japan — but only one
turned into a new source.

**Wales — a real finding, not a new source.** Live-testing the page the
registry's prior `READY_FOR_AUTOMATION` classification was based on
(`/global-wales-postgraduate-scholarship`) found it now 404s (real "Page
not found" content, not a bot block). The site's current replacement page
states the program is no longer centrally administered — it now points
to each of eight Welsh universities' own scholarship pages individually,
plus to Chevening and Commonwealth Scholarships (both already separate
sources here). Corroborated by an independent third-party note that the
program's 2024 round has closed. The prior classification was never
live-tested before being written down — corrected in
`docs/COUNTRY_PROVIDER_REGISTRY.md` to `NOT_SUITABLE` with the finding
documented in place, rather than either silently building a source
against a defunct program or quietly leaving the stale classification for
a future session to trip over. Same discipline as the India ICCR
dual-`<h1>` bug and the corrected Firebase bundle-ID note earlier in this
project's history.

**Japan (MEXT Scholarship) — implemented, fully live-verified.** Targets
the MEXT-specific sub-page of the official "Study in Japan" government
portal, not its thin navigation hub. `deadline_keywords = ()` —
applications are embassy/university-mediated with no single global
deadline, the same honest pattern as Ireland GOI-IES and Sweden SI.
Unlike Australia Awards, `funding_type = "fully_funded"` is kept here and
is actually confirmed by the page's own text ("tuition exempted", a
monthly stipend, "round-trip travel expenses (airfare) provided"), not
guessed. `title_selectors = ()` since every page in this site section
shares the same generic `<h1>Scholarships</h1>`; the real title comes
from the `<title>` tag split on the site's own fullwidth vertical bar
(`｜`, U+FF5C, not the ASCII `|`).

Source count 25 → 26. Docs updated: `docs/AUTHORITATIVE_SOURCES.md` #25,
`docs/COUNTRY_PROVIDER_REGISTRY.md` (Japan moved to implemented; Wales
corrected in place; coverage summary, totals, and recommended-next-
candidates list all updated). Every previously `READY_FOR_AUTOMATION`
candidate in the registry is now either implemented or corrected — the
10 remaining researched countries all genuinely need a second research
pass, not just a fetch-and-wire pass.

Verified: 3 new tests against real fixture HTML; full backend suite
**539/539** (`pytest -q`).

13 of the master prompt's ~40 named countries/regions now have at least
one real source (up from 12). South America, most of Asia, and most of
the remaining named European countries remain completely unresearched.

## [2026-08-29] — Two more country sources: Spain (AECID) and Australia (DFAT Awards)

Continued the master-prompt country-coverage initiative with the top two
`READY_FOR_AUTOMATION` candidates in `docs/COUNTRY_PROVIDER_REGISTRY.md`
— same live-verification discipline as every prior source (fetched via
both `curl` and this backend's actual httpx path, `robots.txt` checked,
real HTML captured as test fixtures, never written from assumption).

**Spain (AECID)** — live-verified cleanly. Deliberately targets AECID's
specific international-applicant sub-page ("Becas para ciudadanos de
países de América Latina, África y Asia"), not its generic scholarships
hub, which mostly serves Spanish nationals and is irrelevant to this
platform. `deadline_keywords = ()`, same reasoning as South Africa NRF
and the Netherlands: the page lists several named sub-programs, each with
its own distinct closing date. `funding_type = "partial_funding"` — no
"fully funded" language found on the page.

**Australia (DFAT Awards)** — partially live-verified. The overview site
(`australiaawards.com.au`) is fully reachable; the authoritative deadline
page (`dfat.gov.au`) is not — every attempt (multiple user agents, `curl`
and httpx) hung at the TLS-handshake stage until timeout, the same
"connects, then nothing responds" pattern already documented for Sierra
Leone's MTHE, not a WAF challenge. `deadline_path` left unset rather than
pointed at an unverified host. `funding_type = None` — no
funding-coverage language was found on the reachable pages; Australia
Awards are widely known to be comprehensively funded in practice, but
that's outside knowledge the adapter's own source text doesn't support
asserting.

Source count 23 → 25. `docs/AUTHORITATIVE_SOURCES.md` (#23-#24) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` updated (both moved out of
"researched, not implemented"; Wales, Japan, and Canada are now the top
queued candidates).

Verified: 5 new tests against real fixture HTML; full backend suite
**536/536** (`pytest -q`).

**Still a small fraction of the original master prompt's ~40 named
countries/regions**: 12 now have at least one real source (up from 10).
South America (9 countries), most of Asia, and most of the remaining
named European countries remain completely unresearched — not silently
dropped, just not attempted this pass.

## [2026-08-29] — Free-hosting-tier deployment prep for the backend (Render + Neon + Upstash)

Researched the current (2026) free-tier landscape before picking a stack
— prior knowledge here goes stale fast: Render's own free Postgres now
expires after 30 days, Fly.io no longer has a real free tier at all, and
Railway removed its free tier back in 2023. Landed on **Render** (web
service) + **Neon** (Postgres — its free tier is explicitly permanent,
unlike Render's) + **Upstash** (Redis — also a permanent free tier,
500K commands/month, standard `rediss://` protocol).

New `render.yaml` Blueprint at the repo root defines the
`scholarsphere-backend` web service (Docker, free plan, `/health/ready`
health check); every credential-shaped env var
(`DATABASE_URL`/`REDIS_URL`/`FIREBASE_PROJECT_ID`/
`FIREBASE_CREDENTIALS_JSON_BASE64`/`ALLOWED_ORIGINS`) is `sync: false` so
nothing gets committed — set via the Render dashboard instead.

New `scholarsphere_backend/docker-entrypoint.sh`: optionally decodes a
base64-encoded Firebase service-account JSON to a real file (portable
across any host, not tied to a platform-specific secret-file feature),
optionally runs `alembic upgrade head` on boot (`RUN_MIGRATIONS_ON_BOOT`,
since Render's free plan has no separate release-phase step), then execs
uvicorn bound to `$PORT` — previously hardcoded to 8000, which would have
made the service unreachable on Render (it injects its own `$PORT`).
`Dockerfile` now uses this as `CMD` (deliberately not `ENTRYPOINT`, which
would have broken `docker-compose.yml`'s worker/beat services that
override the container's command entirely).

`scholarsphere_backend/README.md` gained a full "Deploying to a free
hosting tier" walkthrough with the reasoning above and step-by-step Neon/
Upstash/Firebase/Render setup instructions.

**Real, documented gap:** Render's free plan has no Background Worker or
Cron Job service type (Cron Jobs need a paid plan, $1/month/job minimum),
so the 22 scheduled Celery tasks in `opportunity_sync.py` have no
equivalently free always-on host today. The API itself works fully
without them — only the *scheduled* background jobs (source syncs,
link-health checks, reverification, notifications) don't run for free.
Not worked around by restructuring the scheduling architecture, which was
out of scope for this change.

**Not built or deployed** — no Docker daemon available in this
environment (client only) and no Neon/Upstash/Render accounts exist for
this project from here. `docker-entrypoint.sh` passed shell syntax
validation and `render.yaml` passed YAML well-formedness validation;
neither was exercised against a real build or a real Render deploy.
Verify on the first real deploy attempt.

## [2026-08-29] — GitHub Pages deployment workflow for the Flutter web build

New `.github/workflows/deploy-pages.yml`: builds `flutter build web
--release` with `--base-href "/${{ github.event.repository.name }}/"`
(required so asset URLs resolve correctly once served from a GitHub
Pages project site's `/scholarsphere/` subpath rather than root — the
app's navigation is in-memory, a single `MaterialApp`/`NavigatorKey` with
no `GoRouter`/path-based routes, so no server-side rewrite rules are
needed beyond that), adds `.nojekyll` and an `index.html` -> `404.html`
fallback, then deploys via the official `actions/upload-pages-artifact` +
`actions/deploy-pages` actions. Triggers on push to `main` touching
`lib/`, `web/`, `assets/`, `pubspec.{yaml,lock}`, or the workflow itself,
plus manual `workflow_dispatch`.

Also updated `.env.example`'s CORS section with the exact origin format
needed once a GitHub Pages deployment exists.

**Four real, unavoidable manual steps this alone does not satisfy** (the
workflow's own comments and `.env.example` document each, rather than
silently assuming they're done):
1. Enable Pages with source "GitHub Actions" in repo Settings → Pages —
   confirmed not yet done (`ecotraces.github.io/scholarsphere/` 404s
   today).
2. Deploy `scholarsphere_backend/` somewhere publicly reachable over
   HTTPS and set its URL as the `SCHOLARSPHERE_API_BASE_URL` repo Actions
   variable — it's a compile-time `--dart-define`, baked into the JS
   bundle; left unset, the deployed site falls back to
   `http://localhost:8000/api/v1`, unreachable from a visitor's browser.
   This backend is not deployed anywhere today.
3. Add the Pages origin to that backend's `ALLOWED_ORIGINS`, or its API
   calls are blocked by CORS.
4. Add the Pages origin to Firebase Console's Authorized domains, or
   Google Sign-In's redirect/popup flow won't work from it — console-only,
   same category as this project's existing bundle-ID/Google-Sign-In
   items.

Not run end-to-end — no live GitHub Actions execution or Pages
environment available from this session. The workflow YAML was validated
for well-formedness; verify the actual deploy on the first real push to
`main`.

## [2026-08-29] — Link-health monitoring, Netherlands (Nuffic) source, admin discovery-summary endpoint

Response to a "global scholarship discovery/verification" master-prompt
initiative: audited the existing discovery pipeline first (it already
implements most of the spec — official/application-URL separation, a hard
verification gate, deduplication, confidence scoring, append-only change
history, a scheduled Celery-beat loop with bounded retries, a 22-country
research inventory), then closed three concrete, testable gaps rather than
attempting all of it or every named country at once.

**Link-health monitoring.** New `ExternalOpportunity.link_checked_at`
column (migration `20260914_32`), `app/services/link_health.py`, and
`app.tasks.opportunity_sync.check_link_health` (daily, bounded to 100
published+verified opportunities per run, oldest/never-checked first). An
unreachable link demotes `verified` → `reverification_required`, logs a
`VerificationHistory` entry, and flips
`VerificationReview.application_link_checked = False` — mirrors
`detect_expired_opportunities`'s existing pattern; never deletes the
opportunity or its stored link. 6 new tests.

**Netherlands (Nuffic NL Scholarship).** The top `READY_FOR_AUTOMATION`
candidate in `docs/COUNTRY_PROVIDER_REGISTRY.md`. Live-verified through
this backend's actual httpx path (not just `curl` — see the India-ICCR/
South-Africa-NRF TLS-chain lesson already in this codebase): 200, real
HTML. `hollandscholarship.nl` (the program's old public name/domain)
301-redirects to `studyinnl.org/finances/nl-scholarship`, confirmed
current by the page's own `<title>`. Two honesty choices forced by the
page's own text: `funding_type = "partial_funding"` (page states outright
this is not a full-tuition scholarship) and `deadline_keywords = ()` (the
page says closing dates are set per participating institution, not by
Nuffic itself — same reasoning already applied to South Africa NRF). 3 new
tests against a real fixture; source count 22 → 23.
`docs/AUTHORITATIVE_SOURCES.md` and `docs/COUNTRY_PROVIDER_REGISTRY.md`
updated.

**Admin discovery-summary endpoint.** New
`GET /external-opportunities/discovery-summary` (`DiscoverySummary`
schema) fills the one real admin-visibility gap found in the audit:
source totals/active/recent-errors, opportunity totals by publication
status, duplicate-review backlog, an opportunities-by-country breakdown,
and never-link-checked/broken-links counts from the task above. 4 new
tests. Flutter: added `LiveDiscoverySummary` +
`ApiVerificationRepository.getDiscoverySummary()` (data layer only,
mirroring `getSummary()`'s existing pattern) — deliberately did **not**
wire this into the 884–1151-line dashboard screens, since this
environment has no Flutter SDK to compile or run against and a blind edit
at that size isn't a responsible bet.

Verified: 13 new backend tests; full backend suite **531/531** (`pytest
-q`). Flutter data-layer addition not compiled or run — no SDK available
here.

**Left genuinely open**, not silently dropped: the ~10 other
`READY_FOR_AUTOMATION` countries already queued in the registry, every
country outside that inventory the initiative named, true live-search-
driven multilingual discovery (recommended to keep this system's proven
one-adapter-per-researched-source pattern instead, given the real
anti-bot/ToS walls already hit), a manual review queue UI, and the admin
dashboard's actual UI wiring.

## [2026-08-29] — Dependabot alert investigation: stale nginx base image bumped, uuid CVE note corrected

Investigated the 11 Dependabot alerts (3 high, 4 moderate, 4 low) GitHub
reported on the default branch. This session's tooling has no `gh` CLI, no
Dependabot-alerts MCP tool, and no authenticated access to the Security
tab, so the exact CVE IDs could not be read directly. Instead, every
dependency manifest in the repo was audited against public advisory
databases: `pip-audit` (backend), `npm audit --json` including dev
dependencies (Cloud Functions), and an OSV.dev batch query over all 73
pub.dev-hosted packages in `pubspec.lock` (ecosystem name `Pub` confirmed
against OSV's own ecosystem list) — **all three came back with zero
findings**. Android's Gradle files declare no explicit dependency
versions (delegated to the Flutter Gradle plugin), and there is no
`Podfile.lock` or `Gemfile`, so those aren't a source either.

That leaves this repo's three Docker base images as the only remaining
Dependabot-tracked ecosystem, and the likely real source (11 OS-package
findings is a typical count for a stale Alpine/Debian base). Couldn't run
a scanner directly (no Docker daemon in this environment, and fetching a
third-party tool like Trivy from GitHub releases is blocked by this
session's repo-scoping proxy), but direct registry inspection confirmed
`nginx:1.27-alpine` (root `Dockerfile`) was three stable-branch releases
behind current — bumped to **`nginx:1.30-alpine`**, verified via registry
digest comparison to be the exact same image nginx's own `stable-alpine`
tag currently resolves to. `python:3.12-slim` and
`ghcr.io/cirruslabs/flutter:stable` are both already floating tags that
pick up the latest patched image on next build, so left unchanged.

Also corrected a stale `Task.md` note along the way: the moderate `uuid`
CVE (GHSA-w5hq-g745-h8pq) once tracked as blocked on Cloud Functions'
`firebase-admin` is already resolved — `functions/node_modules/uuid` is
`14.0.1`, past every fixed threshold (11.1.1/12.0.1/13.0.1 depending on
major line) in OSV's own advisory record, confirmed by both the OSV
lookup and a clean `npm audit`. No code change was needed there, only the
stale tracking note.

**Not verified against the actual alert list or count** — this is
reasoning from public advisory data, not a read of GitHub's own Dependabot
report. Re-check the Security tab once this lands (and once the next
scheduled image rebuild picks up the two floating tags) to confirm the
count actually drops before treating this as closed.

## [2026-08-29] — Differential Storage access for provider-granted applicant documents

Closed the `Task.md` Backend Tasks gap where a provider granted access to an
applicant's document (`ApplicantDocument.shared_with_provider_ids`, set via
`POST /applicant-documents/{id}/share`) was still denied at the Storage
layer, because `storage.rules` scopes `applicant-documents/` to owner-only
and that never changed. Rather than widen the Storage rule (which would
remove the backend as an auditable choke point), providers now read shared
files through two new backend-issued routes instead:

- `GET /applicant-documents/{id}/download-url` — mints a short-lived (15
  minute), v4 signed Storage URL via the Firebase Admin SDK, for the
  document's owner or a provider whose `Provider.id` appears in
  `shared_with_provider_ids`. Everyone else gets 404 (matching this
  router's existing owner-scoped convention of not distinguishing "not
  found" from "not yours"). Signing failures (no credentials configured)
  surface honestly as 503, never a fabricated URL.
- `GET /applicant-documents/shared-with-me` — provider-facing listing of
  documents shared with any `Provider` record the caller owns. Deliberately
  omits `storage_path`; only the download-url route above may read it.

New `app/services/document_storage.py` wraps the Admin SDK call so it can be
monkeypatched in tests, matching `app/services/firebase_users.py`'s
established pattern. Firebase app initialization
(`app/core/auth.py::initialize_firebase`) now also passes `storageBucket`
(new `Settings.firebase_storage_bucket`, defaulting to the same
`scholarsphere-d44f5.firebasestorage.app` already used in
`lib/firebase_options.dart`) — previously unset, which is why signed URLs
were never possible before. `storage.rules` and the affected route
docstrings updated to describe the new arrangement instead of the old
"not-yet-built follow-up" note.

Verified: 7 new tests in `tests/test_applicant_documents_route.py` (owner
access, unrelated applicant denied, ungranted provider denied on both
routes, granted provider allowed on both routes and correctly scoped to
their own `Provider` record, signing-failure 503, non-provider role sees an
empty shared list rather than an error). Full backend suite **518/518**
(`pytest -q`). Flutter suite not touched, not re-run this session — no
Flutter files changed; the client-side "download a shared document" UI for
providers is not part of this change.

## [2026-08-22] — Security review, Firebase officer roster, audit-read endpoint, notification-delivery honesty fix

Independent security review of the applications/verification/providers/
provider_opportunities backends (`Task.md` Critical Task), the Firebase
verification-officer roster gap (`Task.md` Critical Task), and three
backlog items were inspected, fixed where real gaps were found, tested, and
verified. Full backend suite re-run and passing after every change:
**448/448 (`pytest -q`).** Flutter suite not touched, not re-run this
session — no Flutter files changed.

### Fixed
- **Security review of applications/verification/providers/
  provider_opportunities — 4 real gaps found and fixed, 0 IDOR/auth-bypass
  found.** `providers.py`'s administrator/review/suspension/appeal
  mutations had no audit trail (added `append_audit()` calls);
  `add_administrator` stored raw wire-format permission strings instead of
  the model's enum values, silently breaking any permission check against
  them (added `permission_from_wire()` conversion); `submit_opportunity`
  checked only org-level publish rights, not the calling administrator's
  own granted permissions, so any administrator on a publish-enabled
  organization could submit opportunities regardless of their individual
  grants (added `_submitter_permission_check()`); `ProviderReviewRequest
  .decision` accepted an unconstrained string instead of the real 3-value
  set (restricted to a `Literal`). Files: `app/api/routes/providers.py`,
  `app/api/routes/provider_opportunities.py`, `app/schemas/provider.py`.
- **Firebase verification-officer roster gap.** Reverification reminders
  previously targeted officers found only via `ImportAuditLog` activity
  history, so a brand-new officer with zero prior decisions received no
  reminders. New `app/services/firebase_users.py` enumerates all Firebase
  users through the Admin SDK's real pagination mechanism, filters by the
  `role` custom claim in application code (there is no server-side
  "query by custom claim" API — confirmed against the installed SDK), and
  falls back to the audit-log heuristic if enumeration fails. File:
  `app/tasks/opportunity_sync.py`.
- **Notification-delivery honesty bug.** `process_due_notifications`
  marked `email`/`push` notifications "delivered" even though no
  SMTP/ESP or FCM/APNs provider is integrated anywhere in this backend —
  a fabricated success on the two channels most notifications actually
  use (both are in the default `NotificationPreferences.channels`).
  Restricted `_CONFIGURED_CHANNELS` to `{"in_app"}`; notifications with no
  deliverable channel now honestly report `failed` instead. File:
  `app/services/notification_dispatch.py`.

### Added
- **Security Officer read access to `ImportAuditLog`.**
  `securityAdministrator`/`administrator`/`superAdministrator` could read
  the separate `AuditRecord` trail but had no read access to
  `ImportAuditLog`, which actually covers the opportunity-verification and
  provider-lifecycle pipeline. Added `GET /audit/import-records` with
  filtering and pagination, gated on the same roles as every other route
  in `audit.py`. Files: `app/api/routes/audit.py`, `app/schemas/
  audit_log.py`.

### Reviewed, no change needed
- USAJOBS live smoke test — blocked, no `USAJOBS_API_KEY` in this
  environment; mocked coverage (`tests/test_usajobs.py`) is the strongest
  test available here.
- Differential Storage access for provider-granted applicant documents —
  re-confirmed the current state fails *safe* (a granted provider is wrongly
  denied the file, not the reverse), so left as a scoped follow-up rather
  than an unplanned feature build; see `Task.md`.
- The four dead-code domain areas (`eligibility_rules`, `integrations`,
  `data_transfer`, `platforms`) — re-confirmed still accurate as
  **DECISION REQUIRED**, a product decision rather than an engineering one.

---

## [2026-08-22] — Web-scraper source tier and confidence-triage queue signal

Requested as an autonomous-discovery/publication initiative; two decisions
were confirmed with the user before implementation rather than assumed:
keep the mandatory human-verification gate for every source (add
confidence *triage*, not auto-publish), and scrape only specific named
organizations approved individually. Full backend suite re-run and passing
after every change: **483/483 (`pytest -q`)**, up from 448.

### Added
- **Five new opportunity sources via a new web-scraper adapter tier**
  (`app/services/web_scraper_base.py`) — Commonwealth Scholarships (CSC
  UK), Chevening Scholarships, DAAD Scholarship Database (curated seed-id
  list, coverage caveat below), Chinese Embassy in Sierra Leone
  (scholarship announcements), and Sierra Leone's Ministry of Technical
  and Higher Education (government scholarship announcements, including
  partner-government offers such as Russia's). None of these
  organizations publish an official API, RSS feed, or dataset — see
  `docs/AUTHORITATIVE_SOURCES.md` #8-#12 for the per-source research and
  robots.txt/terms check performed before each was added. Every scraped
  record goes through the identical mandatory verification/publication
  pipeline as an API source (`NormalizedExternalOpportunity` enforces
  `pending`/`unpublished` at the schema level regardless of source).
  Fulbright was researched and deliberately not integrated (decentralized
  per-country administration, no single official listing) — see the
  declined-sources table in `docs/AUTHORITATIVE_SOURCES.md`.
- **`app/core/http_client.py::get_html`** — HTML fetch with the same
  HTTPS-only, timeout, response-size-cap, and bounded-retry protections
  `get_json`/`post_json` already had.
- **`app/services/verification_confidence.py`** — a deterministic,
  fully-explained (not AI/ML) confidence scorer wired into
  `GET /external-opportunities/pending-verification?sort=confidence`,
  exposing `confidence_level`/`confidence_reasons` on each queue item as a
  triage priority hint only. It has no path to set `verification_status`
  or `publication_status`; every record still requires an officer's
  explicit `approved` decision regardless of score.
- **`extract_confident_date`/`extract_confident_date_after`**
  (`app/services/parsing.py`) — sets a scraped deadline only when an
  explicit day+month+year date literal is present in the source text;
  confirmed against real prose from both DAAD and CSC UK that states a
  closing date without an adjacent year, which is correctly left `null`
  rather than guessed ("never invent data").
- 5 new `OpportunitySource` registry rows (`trust_level="web_scraped"`)
  and 5 new daily Celery beat entries.
- 34 new tests: `tests/test_cscuk_scholarships.py`, `test_chevening.py`,
  `test_daad_scholarships.py`, `test_embassy_announcements.py`,
  `test_verification_confidence.py`, new `get_html` cases in
  `test_http_client.py`, a new confidence-field case in
  `test_verification_actions.py`. Real HTML fetched from the live sites on
  2026-08-22 backs 4 of the 5 new adapters' tests
  (`tests/fixtures/*.html`); the fifth (`mthe_sierra_leone`) uses a
  clearly-labeled synthetic fixture — see "Reviewed, no change needed"
  below.
- **Live end-to-end verification.** With no Celery broker available in
  this environment, `app/tasks/opportunity_sync._run_source_sync` (the
  exact function every Celery task here calls) was invoked directly
  against a temporary database for all 5 new sources with no HTTP
  mocking, against the real live sites: `cscuk_scholarships` 6/6 created,
  `chevening` 1/1 (deadline correctly parsed, `2026-10-06`),
  `daad_scholarships` 6/6, `china_embassy_sl` 2/2, `mthe_sierra_leone` 0/0
  with a clean non-fatal error (confirming its connectivity blocker fails
  gracefully rather than crashing the sync).

### Fixed
- **`china_embassy_sl` deadline mis-extraction, found by the live run
  above.** A "Farewell Ceremony" article's publish date was picked up as
  if it were an application deadline, because deadline extraction took
  the first date literal anywhere in the article body with no context
  check. Fixed by anchoring on a nearby deadline-indicating keyword
  (`_DEADLINE_KEYWORDS` in `app/services/embassy_announcements.py`,
  matching the pattern already used for `cscuk_scholarships`/
  `daad_scholarships`); re-ran live and confirmed both real articles now
  correctly report `deadline=None`. Regression test added using the real
  HTML that caught it
  (`tests/test_embassy_announcements.py::test_china_embassy_unrelated_date_is_not_mistaken_for_a_deadline`).
  Full backend suite after the fix: **483/483**.
- `pip-audit -r requirements.txt`: no known vulnerabilities, including the
  new `beautifulsoup4` dependency.

### Changed
- `docs/AUTHORITATIVE_SOURCES.md`, `docs/OPPORTUNITY_VERIFICATION_SYSTEM.md`
  (new §6 on confidence triage; §7-§11 renumbered accordingly, with every
  internal cross-reference to the old numbering updated),
  `docs/PRODUCTION_SECURITY_AUDIT.md` §2.6 (dated update note appended;
  original finding preserved rather than rewritten), `docs/
  SECURITY_MODEL.md` (fixed a now-stale §9→§10 cross-reference),
  `scholarsphere_backend/README.md` all updated to describe the new
  architecture accurately.
- `tests/test_opportunity_import.py::test_source_seeding_is_idempotent`
  updated for the new source count (8 → 13).

### Reviewed, no change needed
- `mthe_sierra_leone`'s live-site smoke test — **blocked**:
  `https://www.mthe.gov.sl` and `http://www.mthe.gov.sl` both refused
  every connection attempted from this environment (2026-08-22, multiple
  attempts). Looks like a network/hosting issue outside this codebase's
  control, not confirmed either way. The adapter is implemented and
  tested against a synthetic fixture only — not claimed as live-verified.
  See `Task.md` Integration Tasks.

---

## [2026-08-23] — Global country-coverage expansion (WMI + 9 new sources, 23-country research inventory)

Requested: expand opportunity discovery to 23 target countries/regions plus
WMI, following the existing architecture with quality prioritized over
quantity. Full research pass across all 24 targets first (see the new
`docs/COUNTRY_PROVIDER_REGISTRY.md`), then implementation on the strongest
candidates, in two batches. Full backend suite after both batches:
**511/511 (`pytest -q`)**, up from 494. Nothing in this entry has been
committed - left for explicit review.

**Batch 2 (follow-up, same day)**: implemented the three next-recommended
candidates - Italy (MAECI), Greece (IKY), South Africa (NRF). 2 of 3
live-verified (Italy, Greece - both real syncs against the real sites);
South Africa is implemented but live-blocked by the same failure class as
India ICCR below (a real, reproducible `SSLCertVerificationError` on
NRF's own server - confirmed by two separate attempts, ruling out a
one-off fluke). New shared-architecture addition:
`_SingleProgramSource` gained an overridable `_deadline_base_url()`
method, since Italy's overview page and its deadline/call-status page are
on two different hosts - the first source needing that. South Africa's
adapter deliberately never attempts deadline extraction
(`deadline_keywords = ()`) - the real page publishes a table of distinct
closing dates per study level/sub-programme, and a generic
keyword-anchored extractor would have picked one row and mislabeled it as
*the* deadline. 14 new tests
(`tests/test_national_scholarship_programs.py`). See
`docs/AUTHORITATIVE_SOURCES.md` #19-#21, `docs/COUNTRY_PROVIDER_REGISTRY.md`.

### Added
- **6 new opportunity sources**: Wells Mountain Initiative (WMI) Scholars
  Program, Türkiye Bursları (Turkey), Government of Ireland GOI-IES,
  ICCR Scholarship Programme (India), Swedish Institute Scholarships for
  Global Professionals (Sweden), Eswatini SLAS. See
  `docs/AUTHORITATIVE_SOURCES.md` #13-#18. 4 of 6 live-verified (WMI,
  Turkey, Ireland, Sweden - real syncs against the real sites, real
  opportunities created); 2 implemented but live-blocked by documented
  external issues, not falsely claimed working (see "Fixed" below and
  Task.md for full detail).
- **`app/services/national_scholarship_programs.py`** - a new shared
  `_SingleProgramSource` base for the common shape of "one government or
  quasi-governmental body's single recurring scholarship program,"
  generalizing the pattern `chevening.py` established, used by 5 of the 6
  new sources.
- **`docs/COUNTRY_PROVIDER_REGISTRY.md`** - a full research inventory
  across all 24 targets: 7 with an integrated provider (5 supported, 2
  partially - see above), 14 with a credible official candidate
  identified and classified (`READY_FOR_AUTOMATION` /
  `REQUIRES_CURATED_SOURCE`) but not yet built, 2 with no reliable single
  source found (Denmark, UAE), 1 actively blocked by anti-bot protection
  and deliberately not pursued further (Cyprus - Azure WAF JS challenge).
- 25 new tests: `tests/test_national_scholarship_programs.py`, additions
  to `tests/test_embassy_announcements.py` (Eswatini SLAS).

### Fixed
- **Two real title-extraction bugs, found by live/fixture testing.**
  India ICCR's page has two `<h1>` elements - a generic Drupal
  page-title chrome element and the real content heading nested inside
  `.field--name-body` - so a naive `select_one("h1")` silently grabbed
  the wrong one. WMI and Ireland have *no* usable `<h1>` at all
  (page-builder/custom-theme pages); both original tests passed anyway
  because they never asserted on the actual title text, silently masking
  a fallback-only result. Fixed by adding a `title_tag_separator`
  fallback (extract from `<title>`, split on a real separator character)
  and adding title assertions to the tests so this class of bug can't
  hide again.
- **India ICCR: real TLS certificate-chain issue on the server,
  correctly not worked around.** `curl` succeeds against `iccr.gov.in`,
  but this backend's actual HTTP path (httpx + certifi's default trust
  store) fails with `SSLCertVerificationError: unable to get local
  issuer certificate` - the server isn't sending a complete certificate
  chain; `curl`/Windows SChannel tolerates this, strict OpenSSL/certifi
  verification does not. Deliberately **not** patched around with
  `verify=False` - that would remove real TLS security for a problem
  that's actually on ICCR's end to fix.

### Reviewed, no change needed
- SSRF/link-following review of the new source: `national_scholarship_programs.py`
  never follows a scraped link (every fetch target is a hardcoded class
  attribute, not discovered from page content), so it has no SSRF
  surface at all; `EswatiniSlasSource` inherits the same-host-only fix
  already applied to the embassy-announcement pattern (see the previous
  entry below).
- Eswatini SLAS live connectivity: reconfirmed the same network-timeout
  pattern already documented for Sierra Leone's MTHE - not resolved,
  not fabricated as fixed.

---

## [2026-08-23] — Production-readiness hardening: startup validation, corrected Firebase/MTHE findings, SSRF fix

A follow-up hardening pass over the previous increment's already-committed
work (`6747e20`), continuing rather than repeating it. Full backend suite
re-run and passing after every change: **494/494 (`pytest -q`)**, up from
483. Nothing in this entry has been committed - left for explicit review.

### Added
- **Startup-time Firebase credential validation** for production
  (`app/main.py::ensure_firebase_ready_in_production`, called from the
  app's `lifespan`) - Firebase Admin SDK init was previously lazy (first
  authenticated request only), so a bad credential would have surfaced as
  a confusing runtime failure instead of a clear deploy-time one.
  `app/core/config.py` also now refuses to start in production if
  `FIREBASE_CREDENTIALS_PATH` is set but the file doesn't exist. 6 new
  tests (`tests/test_startup_validation.py`).
- `.env.example` rewritten to list every setting the codebase actually
  reads (including the 5 web-scraper sources, previously missing),
  labeled by when each is really required.
- A real Celery task-interface test (`task_always_eager`, exercising
  `sync_cscuk_scholarships.apply(...)` rather than calling the underlying
  function directly), an idempotency test (same `task_id` re-run creates
  no duplicate history/opportunity), and cross-cutting scraper resilience
  tests (malformed HTML, simulated full layout change, missing-title
  fallback) - see `tests/test_opportunity_tasks.py`,
  `tests/test_scraper_resilience.py`.

### Fixed
- **SSRF-adjacent gap in the embassy-announcement adapter.**
  `app/services/embassy_announcements.py`'s link discovery filtered only
  by visible link text, not by the link's target host - a link on an
  otherwise-trusted page could point anywhere and would still be fetched.
  Added `same_host_https_url` (`app/services/web_scraper_base.py`) and
  switched this adapter to it. Regression test:
  `tests/test_scraper_resilience.py::test_discovered_links_to_a_different_host_are_never_followed`.
- **Pre-existing test-isolation bug**:
  `test_all_scheduled_task_names_resolve` only passed as part of the full
  suite (it silently relied on another test file having already imported
  `app.tasks.notifications`); failed when run alone. Not a production
  bug - a real worker loads every `include=[...]` module at startup - but
  a real test-determinism bug. Fixed by calling
  `celery_app.loader.import_default_modules()` explicitly in the test.

### Corrected (documentation, not code)
- **Firebase "old bundle ID" blocker.** Direct inspection of every config
  file (`build.gradle`, `google-services.json`, the Xcode project,
  `firebase_options.dart`) found `com.scholarsphere.app` used
  consistently everywhere - no mismatch. The real, more specific gap
  found instead: `ios/Runner/GoogleService-Info.plist` doesn't exist, and
  `Info.plist` has no Google Sign-In URL scheme. Android additionally
  needs its OAuth client's SHA-1/SHA-256 fingerprint verified against
  whichever keystore signs the build - not checkable from this
  environment. Live Google Sign-In was not tested. See `Task.md`.
- **MTHE connectivity.** Re-diagnosed precisely: DNS resolves fine
  (`www.mthe.gov.sl` → `38.145.202.15`); every TCP connection (port 80,
  port 443) and even ICMP ping times out with no response - a different
  and more specific finding than "connection refused." No official
  RSS/API/alternative source found. See `Task.md`.

### Reviewed, no change needed
- `pip-audit -r requirements.txt`: re-confirmed no known vulnerabilities.
- Fulbright: re-confirmed unsupported; no new official source found.
- Source-management and pending-verification endpoint authorization:
  confirmed unchanged and still correctly gated (`admin_access`/
  `preview_access`).

---

## [2026-08-21] — Real backend fixes: search index, verification dashboard, reverification reminders, document-sharing consent

Four wiring/completeness gaps identified in `Task.md`'s Critical Tasks were
inspected, fixed, tested, and verified against the running code (not
assumed). Full test suites re-run and passing after every change:
**431/431 backend (`pytest -q`), 88/88 Flutter (`flutter test`),
`flutter analyze` clean.**

### Fixed
- **Search index fed from fake data.** `lib/app/app.dart`'s
  `searchIndexUpdate` background-job handler read from
  `DemoOpportunityRepository` while writing to the real
  `ApiSearchIndexRepository`. Root cause was worse than a stale read:
  `POST /search-index/rebuild` prunes the entire shared index and
  re-validates every incoming id against real `external_opportunities`
  rows before keeping it, so demo ids were silently rejected — every
  rebuild was leaving the real, shared search index **empty**. Fixed by
  reading from `_apiOpportunityRepository` instead. The separate
  `expiredOpportunityDetection` client-side job was removed (not
  re-pointed): the real backend already performs this daily,
  authoritatively, via Celery beat, and the client has no
  server-authoritative way to mutate verification status (see
  `Architecture.md` decision 9). Regression-tested end-to-end
  (`test/widget_test.dart`, drives the real admin "process queued jobs"
  UI flow and asserts real backend data reaches `rebuild()`).
- **Verification Officer dashboard showed fabricated metrics.** The
  dashboard's landing panels read `assignedToUserId`,
  `VerificationWorkflowStatus`, `hasOfficialAuthority`, and other fields
  that only exist in the demo's richer two-person-workflow model — the
  real backend has none of them. Fixed by adding a real backend aggregate
  endpoint, `GET /external-opportunities/verification-summary` (pending
  count, verified-today count, reverification-due-soon count, a real
  status breakdown, 7-day decision activity, an honest official-source
  ratio, and approvals attributed to the calling officer via
  `ImportAuditLog`), and rewriting every dashboard panel to consume it
  through `ApiVerificationRepository.getSummary()`. Panels with no real
  backend equivalent ("My Assignments") were replaced with panels backed
  by real data ("Approved by You"), not relabeled fakes. The dead
  `DemoVerificationRepository`/`_opportunityRepository` wiring was removed
  from `app.dart` entirely.
- **Reverification reminders produced no real delivery.** The Celery task
  `_send_reverification_reminders` only logged a count. Fixed by creating
  real `ScholarSphereNotification` rows (in-app channel — the one channel
  this backend genuinely delivers on today; email/push are marked
  "delivered" by `process_due_notifications` without any SMTP/FCM
  provider behind them, a pre-existing gap tracked separately in
  `Task.md`) for verification officers, identified via real prior
  `verification_*` decisions in `ImportAuditLog` (this backend has no
  local user directory to draw a full officer roster from — a documented,
  honest limitation, not a fabricated recipient list). Deduplicated by a
  deterministic id (`{opportunity_id}-reverification-officer-{uid}`) so
  re-running the task never spams, and gated on each recipient's own
  notification preferences (global opt-out, missing `in_app` channel, or
  a type-specific unsubscribe all suppress creation). New
  `NotificationEventType.reverification_due`.
- **Provider document-sharing had no consent precondition.** Sharing an
  applicant document with a provider (`POST
  /applicant-documents/{id}/share`) recorded the grant unconditionally.
  Fixed by requiring an active (`granted`, not `withdrawn`)
  `third_party_sharing` `ConsentRecord` before recording the grant (`409`
  otherwise, mirroring the exact precondition
  `privacy.py::record_organization_access` already enforced elsewhere),
  and validating the target provider actually exists (`404` otherwise).
  Every successful grant now also writes a real
  `OrganizationAccessRecord`, visible to the applicant via `GET
  /privacy/access-history`. Withdrawing that consent
  (`POST /privacy/consents/thirdPartySharing/withdraw`) now cascades to
  clear every existing `shared_with_provider_ids` grant for that user, not
  just block new ones.
- **Incidental:** `JobMonitorScreen`'s three `setState(_reload)` calls
  passed a `void` arrow-function tear-off whose body was itself an
  assignment expression — at runtime it still returned the assigned
  `Future`, tripping Flutter's "setState callback returned a Future"
  guard. Found while writing the search-index regression test (the first
  test ever to actually drive "process queued jobs"); fixed by wrapping
  each call in a block body.

### Added
- `GET /external-opportunities/verification-summary` backend endpoint +
  `VerificationSummary`/`VerificationActivityDay` schemas.
- `ApiVerificationRepository.getSummary()` +
  `LiveVerificationSummary`/`VerificationActivityDay` Flutter models.
- `ScholarSphereApp.verificationRepository` constructor override, so tests
  can inject a fake `ApiVerificationRepository` the same way every other
  API repository already supports.
- 4 new backend tests (`tests/test_verification_actions.py`), 4 new
  backend tests (`tests/test_opportunity_tasks.py`), 5 new/updated backend
  tests (`tests/test_applicant_documents_route.py`), 1 new Flutter
  end-to-end widget test.

### Changed
- `scholarsphere_backend/README.md`'s "Known limitations" section
  corrected: the reverification-reminder-delivery bullet was stale (it
  predated both the 2026-08-20 real Notifications backend and this
  session's fix).

---

## [Baseline] — 2026-08-21

Snapshot of the project's real state at the point this documentation set
was created, reconstructed from `git log` and direct code inspection (not
fabricated). Dates below are real commit dates.

### Added
- **2026-08-07** — Initial commit: Flutter project scaffold.
- **2026-08-12** — `ui-ux-pro-max` design-intelligence Claude Code skill
  installed; `dart format` violations fixed project-wide.
- **2026-08-17** — Production security audit performed across the full
  repository (Flutter client, FastAPI backend, Cloud Functions, Firestore
  rules, CI, Docker/deploy config): 16 of 17 findings fixed and
  regression-tested (rate limiting, security headers, dependency CVEs,
  `FIREBASE_CHECK_REVOKED` production hardening, repo-hygiene cleanup,
  HTTPS-enforcement gap in the Flutter release build, weak client-side
  email validation). One finding (a transitive `uuid` CVE via
  `firebase-admin`) remains open with no available upstream patch.
  `docs/PRODUCTION_SECURITY_AUDIT.md`, `docs/SECURITY_MODEL.md`,
  `docs/OPPORTUNITY_VERIFICATION_SYSTEM.md`, `docs/AUTHORITATIVE_SOURCES.md`
  written as the standing security/architecture reference set.
- **2026-08-17** — `applications` and `verification` real FastAPI backends
  landed, wired into the Flutter client via `ApiApplicationRepository`/
  `ApiVerificationRepository` (an optional-constructor-override
  dependency-injection pattern introduced this round, also used to make
  widget tests possible without a live Firebase app).
- **2026-08-17** — Auth screen restructured into scrollable wide/narrow
  layouts; EU MSCA calls reclassified as fellowships; a Grants.gov
  individual-eligibility source added and classified as scholarship.
- **2026-08-18** — `ui-ux-pro-max` design system applied across applicant,
  provider, and back-office surfaces; design tokens persisted to
  `design-system/scholarsphere/MASTER.md`.
- **2026-08-18** — `providers`/`provider_opportunities` real FastAPI
  backend landed: organization registration/verification/suspend/appeal,
  server-authoritative risk scoring, case-insensitive duplicate-domain
  prevention, a 5-item provider verification checklist, real Firebase
  Storage document upload with owner-scoped `storage.rules`. A separate,
  isolated pipeline from the Grants.gov-family opportunities table.
- **2026-08-18** — Dependabot alerts (`js-yaml`, `uuid`) fixed in Cloud
  Functions.
- **2026-08-20** — Real Notifications backend added: in-app delivery,
  preferences, deadline reminders (supersedes the earlier
  demo-only-notifications status recorded in
  `scholarsphere_backend/README.md`'s Known Limitations, which now needs a
  follow-up correction).
- **2026-08-20** — Applicant Profile and Documents real backends landed
  (per commit history; not independently re-audited by the 2026-08-17
  security review, which predates them).
- **2026-08-21** — Further backend feature work landed ("backend
  features01", "completed features" per commit history).

### Known outstanding items carried into Task.md
- ~~Search-index rebuild / expired-opportunity-detection background jobs
  still read from demo (fake) opportunity data instead of the real API
  repository.~~ Fixed 2026-08-21 — see the `[2026-08-21]` entry above.
- ~~Verification Officer dashboard landing metrics still read from the demo
  repository while the queue itself is real.~~ Fixed 2026-08-21 — see the
  `[2026-08-21]` entry above.
- Several 2026-08-18 through 2026-08-21 backend additions have not yet had
  an independent security review against the 2026-08-17 audit's own
  checklist.
- Firebase console bundle-ID re-registration and real release signing
  remain blocked on access this session/tooling can't provide.

See `Road_map.md` for the full phase-by-phase status and `Task.md` for the
active task board.

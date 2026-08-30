# ScholarSphere — Authoritative Source Registry

Every source below is real, currently integrated, and confirmed against the
actual configuration and code in `scholarsphere_backend/` — none of these
URLs are invented. This is the same list as
`scholarsphere_backend/README.md`'s "Integration overview" and "Source
mappings" sections; this document restates it in the platform
specification's requested source-registry format and adds the reliability
classification and verification method for each.

Sources 1–7 are ingested via each provider's own official, documented,
structured API. **As of 2026-08-22 this is no longer the only ingestion
method** (superseding `docs/PRODUCTION_SECURITY_AUDIT.md` §2.6's earlier
"there is no web scraping in this codebase" statement, which was accurate at
the time it was written): sources 8–12 below are collected by scraping each
organization's own public HTML pages, because none of them publish an
official API, RSS feed, or dataset — see each entry's "Discovery method" for
the specific reasoning and the robots.txt/terms check performed before it
was added. Every scraper still lands its output in the exact same mandatory
human-verification queue as an API source (see
`docs/OPPORTUNITY_VERIFICATION_SYSTEM.md`) — scraping changes *how the data
is retrieved*, never *whether a human approves it*. All twenty-one sources
are governed by the shared source-adapter architecture in `app/services/` —
either a thin API client (sources 1–7) or a subclass of `WebScraperSource`
(`app/services/web_scraper_base.py`, sources 8–21). Sources 13–17 and
19–21 share the `_SingleProgramSource` base
(`app/services/national_scholarship_programs.py`), added 2026-08-23 for a
country-coverage expansion — each is one government or quasi-governmental
body's own page(s) for its single recurring international scholarship
program.

---

## 1. Grants.gov (Search2)

- **Organization**: U.S. federal government (grants.gov)
- **Route code**: `grants-gov` (`grants_gov` internally)
- **Official domain / base URL**: `https://api.grants.gov/v1/api` (`GRANTS_GOV_BASE_URL`)
- **Opportunity types**: Grants (US federal)
- **Country coverage**: United States
- **Discovery method**: Official structured search API (`Search2` endpoint)
- **API / RSS / Sitemap**: Official REST API
- **Authentication**: None required
- **Reliability classification**: Official (Level 1 — primary/authoritative government source)
- **Verification method**: Human officer review against the checklist in `docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` §4; the official detail URL is constructed from the opportunity number returned by the API
- **Sync cadence**: Every 6 hours (Celery beat, `app/tasks/opportunity_sync.py`)
- **Field mapping**: `app/services/grants_gov.py` — `id` → `external_id`, `number` → `external_reference`, agency/opening/closing dates and status normalized directly
- **Notes**: Exercised in this codebase's test suite (`scholarsphere_backend/tests/test_grants_gov.py`)

## 2. Grants.gov (Individual Eligibility)

- **Organization**: U.S. federal government (grants.gov)
- **Route code**: `grants-gov-individual` (`grants_gov_individual` internally)
- **Official domain / base URL**: `https://api.grants.gov/v1/api` (`GRANTS_GOV_BASE_URL`, same endpoint as source 1)
- **Opportunity types**: Scholarship — federal funding opportunities filtered to eligibility category `21` ("Individuals"), grants.gov's own published eligibility-category code (alongside e.g. `00` state governments, `12` 501(c)(3) nonprofits). This is funding a person applies for directly, such as graduate research fellowships, rather than an organization.
- **Country coverage**: United States
- **Discovery method**: Same `Search2` endpoint as source 1, with the `eligibilities` filter fixed to `21` rather than left unrestricted
- **API / RSS / Sitemap**: Official REST API
- **Authentication**: None required
- **Reliability classification**: Official (Level 1 — primary/authoritative government source)
- **Verification method**: Same checklist as Grants.gov above
- **Sync cadence**: Every 6 hours, offset from source 1 to avoid overlapping requests
- **Field mapping**: `app/services/grants_gov.py` — shares its normalizer with source 1 via `_GrantsGovSource`; only `opportunity_type` and the default `eligibilities` filter differ
- **Verification caveat, stated plainly rather than hidden**: eligibility category `21` covers any individually-awarded federal opportunity, not exclusively "scholarship" in the everyday sense — some results are closer to a fellowship or an individual research award. Treat this as a best-effort classification, not a guarantee.
- **Notes**: Exercised in this codebase's test suite (`scholarsphere_backend/tests/test_grants_gov.py`)

## 3. Simpler.Grants.gov

- **Organization**: U.S. federal government (the modernized Grants.gov successor)
- **Route code**: `simpler-grants` (`simpler_grants` internally)
- **Official domain / base URL**: `https://api.simpler.grants.gov` (`SIMPLER_GRANTS_BASE_URL`)
- **Opportunity types**: Grants (US federal)
- **Country coverage**: United States
- **Discovery method**: Official structured search API
- **API / RSS / Sitemap**: Official REST API
- **Authentication**: API key (`SIMPLER_GRANTS_API_KEY`, obtained through Simpler.Grants.gov's own registration process — never hardcoded, `SecretStr`-wrapped so it can't leak via logs/`repr()`)
- **Reliability classification**: Official (Level 1)
- **Verification method**: Same as Grants.gov above; official URL uses the opportunity ID
- **Sync cadence**: Every 6 hours
- **Field mapping**: `app/services/simpler_grants.py` — includes award floor/ceiling and currency (`USD`)
- **Notes**: `scholarsphere_backend/tests/test_simpler_grants.py`

## 4. European Commission Funding & Tenders Portal

- **Organization**: European Commission
- **Route code**: `eu-funding` (`eu_funding_tenders` internally)
- **Official domain / base URL**: `https://api.tech.ec.europa.eu/search-api/prod/rest/search` (`EU_FUNDING_API_URL`)
- **Opportunity types**: Grants, calls, tenders, research and funding opportunities
- **Country coverage**: European Union
- **Discovery method**: Official structured search API
- **API / RSS / Sitemap**: Official REST API
- **Authentication**: API identifier (`EU_FUNDING_API_KEY`, defaults to `SEDIA` — the portal's own published, non-secret literal key used by every consumer of this open API, not a leaked credential)
- **Reliability classification**: Official (Level 1)
- **Verification method**: Same checklist; earliest valid deadline is selected when multiple are present, currency fixed at `EUR`; supplied result URLs are preferred, otherwise a topic URL is built from the reference/identifier
- **Sync cadence**: Every 12 hours
- **Field mapping**: `app/services/eu_funding.py` — configurable metadata field extraction (type, identifier, reference, title, status, contracting authority, dates, programme, budget, keywords); description is HTML-sanitized (`bleach`) before storage
- **Notes**: `scholarsphere_backend/tests/test_eu_funding.py`

## 5. USAJOBS

- **Organization**: U.S. Office of Personnel Management
- **Route code**: `usajobs`
- **Official domain / base URL**: `https://data.usajobs.gov/api/search` (`USAJOBS_BASE_URL`)
- **Opportunity types**: Federal jobs; postings whose `HiringPath` mentions students/recent graduates/interns are typed `internship`, everything else `job`
- **Country coverage**: United States
- **Discovery method**: Official structured search API
- **API / RSS / Sitemap**: Official REST API
- **Authentication**: API key (`USAJOBS_API_KEY`, free self-service from developer.usajobs.gov) plus a required `User-Agent` header set to the exact email address registered with that key (`USAJOBS_USER_AGENT`) — USAJOBS uses this as part of authentication, so this source is exempt from the HTTP client's default `User-Agent` string
- **Reliability classification**: Official (Level 1)
- **Verification method**: Same checklist
- **Sync cadence**: Every 6 hours
- **Field mapping**: `app/services/usajobs.py`
- **Verification caveat, stated plainly rather than hidden**: this adapter's field names are based on USAJOBS' long-stable, publicly documented schema but had not been exercised against a live authenticated response as of the last backend README update — smoke-test with a real `USAJOBS_API_KEY` before enabling scheduled sync in a new environment (`scholarsphere_backend/README.md`, "Source mappings" → "USAJOBS")

## 6. ReliefWeb Jobs (UN OCHA)

- **Organization**: United Nations Office for the Coordination of Humanitarian Affairs (OCHA)
- **Route code**: `reliefweb-jobs` (`reliefweb_jobs` internally)
- **Official domain / base URL**: `https://api.reliefweb.int/v2/jobs` (`RELIEFWEB_BASE_URL` + `/jobs`)
- **Opportunity types**: Global humanitarian/development jobs and internships
- **Country coverage**: Global
- **Discovery method**: Official structured API v2
- **API / RSS / Sitemap**: Official REST API; documented at [apidoc.reliefweb.int](https://apidoc.reliefweb.int/)
- **Authentication**: Pre-approved `appname` URL parameter (`RELIEFWEB_APPNAME`) — ReliefWeb's own authentication mechanism, not a secret credential
- **Reliability classification**: Official (Level 1 — UN agency)
- **Verification method**: Same checklist; deadline = `fields.date.closing`
- **Sync cadence**: Every 6 hours
- **Field mapping**: `app/services/reliefweb.py` — field names confirmed directly against ReliefWeb's official parameter/field-table documentation
- **Notes**: `scholarsphere_backend/tests/test_reliefweb.py`

## 7. ReliefWeb Training (UN OCHA)

- **Organization**: United Nations Office for the Coordination of Humanitarian Affairs (OCHA)
- **Route code**: `reliefweb-training` (`reliefweb_training` internally)
- **Official domain / base URL**: `https://api.reliefweb.int/v2/training` (`RELIEFWEB_BASE_URL` + `/training`)
- **Opportunity types**: Training courses and workshops
- **Country coverage**: Global
- **Discovery method / API / Authentication**: Same as ReliefWeb Jobs above (shares one normalizer)
- **Reliability classification**: Official (Level 1)
- **Verification method**: Same checklist; deadline = `fields.date.registration` (the registration close date, not a course date)
- **Sync cadence**: Every 12 hours
- **Field mapping**: `app/services/reliefweb.py`

## 8. Commonwealth Scholarships (Commonwealth Scholarship Commission in the UK)

- **Organization**: Commonwealth Scholarship Commission in the UK (CSC),
  sponsored by the UK Foreign, Commonwealth & Development Office (FCDO)
- **Route code**: `cscuk-scholarships` (`cscuk_scholarships` internally)
- **Official domain / base URL**: `https://cscuk.fcdo.gov.uk`
  (`CSCUK_BASE_URL`)
- **Opportunity types**: Scholarships and fellowships (UK master's/PhD study,
  professional fellowships)
- **Country coverage**: Commonwealth countries (award applies in the UK)
- **Discovery method**: **Web scraper** — no official API, RSS feed, or
  dataset exists. `robots.txt` (checked 2026-08-22) has no `Disallow` rules
  and no `Crawl-delay`; a 2-second minimum interval between requests is
  applied anyway as a courtesy default
  (`app/services/web_scraper_base.py::WebScraperSource.min_request_interval_seconds`).
  The archive page (`/scholarships/`) is scraped for links to individual
  programme pages, each scraped for its own content.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped (`trust_level="web_scraped"`,
  below Level 1 "official" — see `app/services/verification_confidence.py`)
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours (lighter than the API sources; no
  published rate limit of its own to calibrate against)
- **Field mapping**: `app/services/cscuk_scholarships.py` — programme name
  from `<h1 class="entry-title">`; description/eligibility/funding assembled
  from named content sections ("Overview", "Applicant eligibility",
  "Eligible countries", "Financial assistance"); deadline extracted only
  when an explicit day+month+year date literal appears near "closing date"
  or "deadline" text — left `null` otherwise (verified 2026-08-22: the
  fetched Master's Scholarships page states its closing date without an
  adjacent year in the same sentence, so this is a real, expected case, not
  a hypothetical one)
- **Notes**: `scholarsphere_backend/tests/test_cscuk_scholarships.py`,
  tested against real HTML fetched from the live site on 2026-08-22 (see
  `tests/fixtures/cscuk_list.html`, `cscuk_detail.html`)

## 9. Chevening Scholarships

- **Organization**: UK Foreign, Commonwealth & Development Office (FCDO) and
  partner organisations
- **Route code**: `chevening` internally
- **Official domain / base URL**: `https://www.chevening.org`
  (`CHEVENING_BASE_URL`)
- **Opportunity types**: Scholarship (one global, fully-funded UK master's
  programme — not a catalogue of separate named awards)
- **Country coverage**: Global (160+ countries)
- **Discovery method**: **Web scraper** — no official API, RSS feed, or
  dataset exists. `robots.txt` could not be fetched from the development
  environment this adapter was built in (network timeout, checked
  2026-08-22) — the site's own pages are fetched at the same conservative
  courtesy rate as every other scraper regardless. Because Chevening runs
  one recurring annual programme rather than a catalogue, this adapter
  produces exactly one opportunity record per sync, keyed by a fixed
  external id, so a changed deadline updates that one record in place
  (correctly triggering `reverification_required` if it was previously
  verified) instead of creating a new opportunity every cycle.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **Field mapping**: `app/services/chevening.py` — title and description
  from `/scholarships/`; deadline from the `<span class="open">Open for
  applications until <date>, at <time> (UTC)</span>` element on `/apply/`
  (verified 2026-08-22: real fetched text read "Open for applications until
  6 October 2026, at 11:00 (UTC)")
- **Notes**: `scholarsphere_backend/tests/test_chevening.py`, tested against
  real HTML fetched from the live site on 2026-08-22 (see
  `tests/fixtures/chevening_list.html`, `chevening_apply.html`)

## 10. DAAD Scholarship Database

- **Organization**: DAAD (Deutscher Akademischer Austauschdienst / German
  Academic Exchange Service)
- **Route code**: `daad-scholarships` (`daad_scholarships` internally)
- **Official domain / base URL**: `https://www2.daad.de`
  (`DAAD_BASE_URL`)
- **Opportunity types**: Scholarships (study/research in Germany)
- **Country coverage**: Global (DAAD funds international students to study
  in Germany)
- **Discovery method**: **Web scraper, deliberately scoped to a curated seed
  list, not a full-catalogue crawl.** No official API, RSS feed, or dataset
  exists. `https://www.daad.de/robots.txt` (checked 2026-08-22) sets
  `Crawl-delay: 2` and does not disallow the scholarship-database paths —
  this adapter's minimum request interval matches that exactly. The site's
  own search widget loads results through an undocumented internal AJAX
  endpoint (`/ajax/`, found in the page's own script), and
  `https://www.daad.de/sitemap.xml` (confirmed reachable, 28 entries) does
  **not** include the database's individual `?detail=<id>` listing pages —
  there is no ToS-respecting way found so far to discover the full
  catalogue automatically. `Settings.daad_scholarship_detail_ids` lists the
  ids identified by name during source research; each is fetched directly
  by URL. Extending coverage means adding more ids to that setting, not
  writing more scraping code — or replacing this adapter if DAAD ever
  documents its search endpoint.
- **API / RSS / Sitemap**: A general sitemap exists but does not cover this
  database (see above)
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **Field mapping**: `app/services/daad_scholarships.py` — title from
  `<title>` (site-name suffix stripped); content from
  `#ifa-stipendien-detail`; deadline extracted only when an explicit date
  literal appears near "application deadline" text
- **Coverage caveat, stated plainly rather than hidden**: this monitors a
  small, explicitly-configured set of programmes, not DAAD's full database
  (which likely has hundreds of active listings) — see "Discovery method"
  above for exactly why, and Task.md for the follow-up item to broaden
  coverage if DAAD ever publishes a documented way to do so
- **Notes**: `scholarsphere_backend/tests/test_daad_scholarships.py`, tested
  against real HTML fetched from the live site on 2026-08-22 (see
  `tests/fixtures/daad_detail.html`)

## 11. Chinese Embassy in Sierra Leone (Scholarship Announcements)

- **Organization**: Embassy of the People's Republic of China in Sierra
  Leone (Economic and Commercial Counsellor's Office / MOFCOM)
- **Route code**: `china-embassy-sl` (`china_embassy_sl` internally)
- **Official domain / base URL**: `https://sl.china-embassy.gov.cn`
  (`CHINA_EMBASSY_SL_BASE_URL`)
- **Opportunity types**: Scholarship (Chinese Government Scholarship /
  MOFCOM Scholarship for Sierra Leonean students)
- **Country coverage**: Sierra Leone (applicants), China (destination)
- **Discovery method**: **Web scraper, conservative announcement pattern**
  (`app/services/embassy_announcements.py`) — this embassy publishes
  scholarship notices as ordinary news articles, not a structured
  opportunities database, so only a headline, the article's own URL, and its
  body text are extracted; a deadline is set only when an explicit date
  literal appears in the article body, never inferred. No robots.txt
  restriction was found (checked 2026-08-22 — unknown paths redirect to the
  homepage rather than serving a robots.txt with `Disallow` rules). The news
  index (`/eng/xwdt/`) is scraped for links whose own text mentions
  "scholarship" or "mofcom"; matching articles are fetched individually.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7 — **particularly important here**, since this adapter deliberately
  under-extracts (no application URL, deadline often absent) and an officer
  must read the source article directly
- **Sync cadence**: Every 24 hours
- **Field mapping**: `app/services/embassy_announcements.py` — confirmed
  2026-08-22 against a real fetched article
  ("Notice of 2026 Ministry of Commerce (MOFCOM) Scholarship Recruitment",
  `/eng/xwdt/202604/t20260403_11886183.htm`): title from `<title>`, body
  from `<div class="News_Body_Text" id="article">`
- **Notes**: `scholarsphere_backend/tests/test_embassy_announcements.py`,
  tested against real HTML fetched from the live site on 2026-08-22 (see
  `tests/fixtures/china_embassy_news.html`, `china_article.html`)

## 12. Sierra Leone Ministry of Technical and Higher Education (MTHE)

- **Organization**: Government of Sierra Leone, Ministry of Technical and
  Higher Education
- **Route code**: `mthe-sierra-leone` (`mthe_sierra_leone` internally)
- **Official domain / base URL**: `https://www.mthe.gov.sl`
  (`MTHE_SL_BASE_URL`)
- **Opportunity types**: Scholarship — both domestically-administered
  scholarships and scholarships MTHE announces on behalf of partner
  governments (e.g. the Russian Federation's annual offer to Sierra
  Leonean students, confirmed via web search 2026-08-22 to be announced
  through MTHE, not a Russian embassy channel)
- **Country coverage**: Sierra Leone (applicants); destination varies by
  announcement
- **Discovery method**: Same conservative announcement pattern as source 11
  above (shared base class, `app/services/embassy_announcements.py`)
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **LIVE SOURCE TEST: NOT PERFORMED.** `https://www.mthe.gov.sl` and
  `http://www.mthe.gov.sl` both refused every connection attempted from the
  development environment this adapter was built in (2026-08-22, multiple
  attempts, both protocols) — this looks like a network/hosting issue
  outside this codebase's control, not a deliberate access restriction, but
  it could not be confirmed either way, and this adapter's selectors have
  never been checked against the site's real markup. It is implemented
  against the same pattern as the confirmed-working source 11 and
  unit-tested against a clearly-labeled **synthetic** fixture (see
  `scholarsphere_backend/tests/test_embassy_announcements.py`), not real
  captured HTML. **Smoke-test this adapter against the live site, and
  correct its selectors if needed, before relying on its scheduled sync** —
  tracked in Task.md.

## 13. Wells Mountain Initiative (WMI) Scholars Program

- **Organization**: Wells Mountain Initiative, a US-based nonprofit
- **Route code**: `wmi-scholars` (`wmi_scholars` internally)
- **Official domain / base URL**: `https://www.wellsmountaininitiative.org`
  (`WMI_BASE_URL`)
- **Opportunity types**: Scholarship (partial funding, first undergraduate
  degree)
- **Country coverage**: Global, restricted to students studying *in their
  own home region* — explicitly excludes students planning to study in the
  US, Canada, Australia, the UK, or Western Europe (per the site's own
  eligibility text); `country` is left `null` rather than guessed since the
  program isn't tied to one destination
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  (`app/services/national_scholarship_programs.py::_SingleProgramSource`,
  shared with sources 14–17 below) — not a government body, but included at
  the user's request as a named, verified, legitimate funding organization.
  `robots.txt` returned a JS bot-challenge page when fetched directly
  (checked 2026-08-22/23), but the actual `/prospective-scholars/` content
  page did not — monitored rather than treated as fully blocked.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **Field mapping**: title from the `<title>` tag (the page is built with
  the Elementor page builder and has no single clean content `<h1>`);
  description from `.entry-content`; deadline extracted only near
  "deadline"/"march"/"submitted by" keywords
- **Notes**: `scholarsphere_backend/tests/test_national_scholarship_programs.py`,
  **live-tested 2026-08-23**: real sync created 1 opportunity, title "2026
  Scholarship Application", deadline `2026-03-06` (a real, keyword-anchored
  extraction, not the generic "March 1" recurring date quoted in prior-year
  summaries — the live page states this cycle's actual date)

## 14. Türkiye Bursları (Türkiye Scholarships)

- **Organization**: Government of Turkey, administered by the Presidency
  for Turks Abroad and Related Communities (YTB)
- **Route code**: `turkiye-burslari` (`turkiye_burslari` internally)
- **Official domain / base URL**: `https://www.turkiyeburslari.gov.tr`
  (`TURKIYE_BURSLARI_BASE_URL`)
- **Opportunity types**: Scholarship (associate, undergraduate, master's,
  PhD)
- **Country coverage**: Global
- **Discovery method**: **Web scraper, single-flagship-program pattern.**
  `robots.txt` (checked 2026-08-23) has no restrictions. Two pages are
  fetched: the general criteria/programs page (title, description) and a
  dated announcement page (deadline) — a deliberate two-page design since
  the criteria page doesn't carry the current cycle's dates.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **Field mapping**: `app/services/national_scholarship_programs.py` —
  deadline extracted near "application dates"/"deadline"/"closing date"
- **Notes**: `scholarsphere_backend/tests/test_national_scholarship_programs.py`,
  **live-tested 2026-08-23**: real sync created 1 opportunity, deadline
  correctly extracted as `2026-02-20` from the real fixture text
  "Application Dates: 10 January – 20 February 2026" (the closing date —
  the opening date "10 January" has no year in the same phrase and is
  correctly not extracted as a deadline)

## 15. Government of Ireland International Education Scholarships (GOI-IES)

- **Organization**: Government of Ireland, managed by the Higher Education
  Authority (HEA), a statutory state agency
- **Route code**: `ireland-goi-ies` (`ireland_goi_ies` internally)
- **Official domain / base URL**: `https://hea.ie` (`IRELAND_HEA_BASE_URL`)
- **Opportunity types**: Scholarship (NFQ level 9/10 — master's,
  postgraduate diploma, PhD)
- **Country coverage**: Global (applicants outside the EU/EEA, Switzerland,
  and the UK)
- **Discovery method**: **Web scraper, single-flagship-program pattern.**
  `robots.txt` (checked 2026-08-23) only disallows `/wp-admin/`. The page
  has no `<h1>` and no `.entry-content` (its `<article>` element is an
  unrelated 126-character snippet) — confirmed by measuring extracted text
  length per candidate selector rather than assuming WordPress convention
  held; title comes from the `<title>` tag, content from `<main>`.
- **API / RSS / Sitemap**: None published (sitemap exists but is a generic
  WordPress sitemap, not scholarship-specific)
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **Notes**: `scholarsphere_backend/tests/test_national_scholarship_programs.py`,
  **live-tested 2026-08-23**: real sync created 1 opportunity, title
  "Government of Ireland International Education Scholarships"; deadline
  `null` (the policy overview page doesn't state the current cycle's
  closing date with an adjacent year — honestly left unset rather than
  guessed, same as the DAAD/CSC UK precedent)

## 16. ICCR Scholarship Programme (India)

- **Organization**: Indian Council for Cultural Relations (ICCR), an
  autonomous organization of India's Ministry of External Affairs
- **Route code**: `india-iccr` (`india_iccr` internally)
- **Official domain / base URL**: `https://iccr.gov.in`
  (`INDIA_ICCR_BASE_URL`)
- **Opportunity types**: Scholarship (18 schemes, UG/PG/PhD across
  Non-STEM and STEM disciplines)
- **Country coverage**: Global (192 UN-recognised countries per the
  program's own materials)
- **Discovery method**: **Web scraper, single-flagship-program pattern.**
  `robots.txt` (standard Drupal pattern, checked 2026-08-23) does not
  block the scholarship page. The page has two `<h1>` elements — Drupal's
  generic page-title chrome appears first in document order, and the real
  content heading ("ICCR Scholarship Programme") is nested inside
  `.field--name-body`, so the content-scoped selector is tried first.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **LIVE SOURCE TEST: BLOCKED — a different failure mode than a network
  timeout.** A plain `curl` fetch succeeds (200, real HTML) — but this
  backend's real HTTP path (`app/core/http_client.py::get_html`, httpx +
  certifi's default trust store) fails with `SSLCertVerificationError:
  unable to get local issuer certificate`. `iccr.gov.in`'s server is not
  sending a complete TLS certificate chain; `curl`/Windows SChannel
  tolerates this (it can fetch a missing intermediate certificate itself),
  but Python's strict OpenSSL/certifi verification does not — this is not
  an artifact of one development machine, a standard-library Python
  deployment (the actual production stack) would very likely hit the same
  failure. **This was deliberately not worked around with `verify=False`**
  — that would remove real TLS security for a source whose own operators
  need to fix their certificate chain; see the class docstring in
  `app/services/national_scholarship_programs.py`. Implemented and
  unit-tested against real fixture HTML captured via `curl` (not through
  this backend's own client, given the above), but the sync itself is
  blocked until ICCR's server configuration changes. Re-test periodically.

## 17. Swedish Institute Scholarships for Global Professionals (SISGP)

- **Organization**: Swedish Institute (Svenska institutet), a Swedish
  government agency
- **Route code**: `sweden-si-scholarship` (`sweden_si_scholarship`
  internally)
- **Official domain / base URL**: `https://si.se` (`SWEDEN_SI_BASE_URL`)
- **Opportunity types**: Scholarship (full-time master's study)
- **Country coverage**: Citizens of 34 eligible countries (per the
  program's own materials)
- **Discovery method**: **Web scraper, single-flagship-program pattern.**
  `robots.txt` itself returned a 403 when fetched directly (checked
  2026-08-23, likely edge-level bot filtering on that specific path), but
  the actual scholarship content page did not — monitored rather than
  treated as fully blocked, same situation as source 13 (WMI) above.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **Notes**: `scholarsphere_backend/tests/test_national_scholarship_programs.py`,
  **live-tested 2026-08-23**: real sync created 1 opportunity, title "SI
  Scholarship for Global Professionals"; deadline `null` (this page states
  the application window only as month names without an adjacent year at
  fetch time — honestly left unset)

## 18. Eswatini Scholarship Loan Application System (SLAS)

- **Organization**: Government of Eswatini, Ministry of Labour and Social
  Security (Scholarship Secretariat)
- **Route code**: `eswatini-slas` (`eswatini_slas` internally)
- **Official domain / base URL**: `https://slas.gov.sz` (no "www." — see
  the live-test note below; `ESWATINI_SLAS_BASE_URL`)
- **Opportunity types**: Scholarship/loan (local and SADC-region study —
  Botswana, Lesotho, Zimbabwe, Tanzania, Kenya; explicitly excludes South
  Africa and Namibia)
- **Country coverage**: Eswatini (applicants). **Uses "Eswatini", the
  country's official name since 2018, consistently — never "Swaziland"**,
  per the country-name-normalization requirement for this expansion.
- **Discovery method**: Same conservative announcement pattern as sources
  11–12 (shared base class, `app/services/embassy_announcements.py`)
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **LIVE SOURCE TEST: PARTIALLY PASSED, 2026-08-29.** `https://
  www.slas.gov.sz` still times out on every attempt (same symptom as
  source 12/MTHE — DNS resolves but the TCP handshake never completes),
  but the bare `https://slas.gov.sz` (no "www.") is reachable — 200,
  real ~41KB HTML, 3/3 attempts — and is now what `ESWATINI_SLAS_BASE_URL`
  points at. However, the real homepage content turned out to be a
  domestic student-loan portal for Eswatini nationals ("Ministry of
  Labour and Social Security" / "Student Loan" / "Loan Repayment") —
  neither "scholarship" nor "SADC" appears anywhere in its HTML, so this
  adapter's own keyword-matching correctly extracts zero records from
  it (see the real fixture `tests/fixtures/eswatini_slas_homepage.html`
  and `tests/test_embassy_announcements.py`'s
  `test_eswatini_slas_real_homepage_yields_no_records`). Reachability
  is fixed; this source is not confirmed to actually produce any
  opportunity records — see docs/COUNTRY_PROVIDER_REGISTRY.md's
  Eswatini entry, reclassified `NOT_SUITABLE` rather than claimed fixed.

## 19. Italian Government Scholarships (MAECI)

- **Organization**: Ministry of Foreign Affairs and International
  Cooperation (MAECI), Italy
- **Route code**: `italy-maeci-scholarships` (`italy_maeci_scholarships`
  internally)
- **Official domain / base URL**: `https://www.esteri.it`
  (`ITALY_ESTERI_BASE_URL`) for the overview page; a second, related host
  `https://studyinitaly.esteri.it` (`ITALY_STUDYINITALY_BASE_URL`) for the
  current call's status — the first genuine two-host source in this
  registry (`_SingleProgramSource.deadline_base_url` was added to support
  this).
- **Opportunity types**: Scholarship (master's, PhD, Italian Language,
  research, Art/music/dance courses)
- **Country coverage**: Global (eligible countries list published per
  academic year)
- **Discovery method**: **Web scraper, single-flagship-program pattern.**
  `robots.txt` on both hosts (checked 2026-08-23) is empty/permissive.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **Notes**: `scholarsphere_backend/tests/test_national_scholarship_programs.py`,
  **live-tested 2026-08-23**: real sync created 1 opportunity, title
  "Scholarships for foreign students and Italian citizens living abroad
  awarded by the Italian Government"; deadline `null` — the live call
  status page states the 2025-2026 call is closed with no new date
  announced yet, correctly not treated as a deadline

## 20. IKY Foreign Nationals Scholarships (Greece)

- **Organization**: State Scholarships Foundation (IKY), Greece — a
  government body operating since 1964
- **Route code**: `greece-iky-scholarships` (`greece_iky_scholarships`
  internally)
- **Official domain / base URL**: `https://www.iky.gr`
  (`GREECE_IKY_BASE_URL`)
- **Opportunity types**: Scholarship (postgraduate studies, postdoctoral
  research, Modern Greek Language and Culture)
- **Country coverage**: Global (bilateral agreements vary by country)
- **Discovery method**: **Web scraper, single-flagship-program pattern.**
  `robots.txt` (standard WordPress pattern, checked 2026-08-23) only
  disallows `/wp-admin/`.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **Notes**: `scholarsphere_backend/tests/test_national_scholarship_programs.py`,
  **live-tested 2026-08-23**: real sync created 1 opportunity, title
  "Foreign Nationals Scholarships"; deadline `null` — the live page's text
  is informational (references an old 2017-2018 language-course cycle
  still on the page, states postgraduate scholarships are "not open for
  this year") with no current date literal, correctly left unset

## 21. National Research Foundation (NRF) Postgraduate Funding (South Africa)

- **Organization**: National Research Foundation (NRF), a South African
  statutory government research-funding agency
- **Route code**: `south-africa-nrf` (`south_africa_nrf` internally)
- **Official domain / base URL**: `https://www.nrf.ac.za`
  (`SOUTH_AFRICA_NRF_BASE_URL`)
- **Opportunity types**: Scholarship/grant (Honours, Master's, Doctoral,
  and specialized programmes e.g. SARAO)
- **Country coverage**: International applicants receive Partial Cost of
  Study (PCS) funding; Full Cost of Study is citizens/permanent-residents
  only
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading NRF's public funding-cycle announcement page (not the
  authenticated NRF Connect application portal). `robots.txt` (standard
  WordPress pattern, checked 2026-08-23) only disallows `/wp-admin/`.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choice**: `deadline_keywords = ()` — this adapter
  never attempts deadline extraction. The real page publishes a *table* of
  distinct closing dates per study level and sub-programme (Honours,
  Master's, Doctoral, SARAO, first-time applicants, Designated-Authority
  submissions, ...); a generic keyword-anchored extractor would pick one
  row and mislabel it as *the* deadline for the whole opportunity — every
  individual date is real, but attributing one to the wrong programme
  would be misleading. Left `null` on purpose so a human officer reads the
  actual table.
- **LIVE SOURCE TEST: BLOCKED — the same failure mode as source #16
  (India ICCR), not a network timeout.** A plain `curl` fetch succeeds
  (200, real HTML), but this backend's real HTTP path (httpx + certifi's
  default trust store) fails with `SSLCertVerificationError: unable to
  get local issuer certificate` on repeat testing (one earlier attempt
  surfaced as a TLS handshake timeout instead, but a retry reproduced the
  certificate error consistently, confirming it's the same underlying
  incomplete-chain issue rather than two separate problems).
  `nrf.ac.za`'s server is not sending a complete certificate chain.
  **Deliberately not worked around with `verify=False`.** Implemented and
  unit-tested against real fixture HTML captured via `curl`. Re-test
  periodically.

## 22. NL Scholarship (Netherlands)

- **Organization**: Nuffic, the Dutch organisation for internationalisation
  in education, on behalf of the Dutch Ministry of Education, Culture and
  Science, jointly funded with participating Dutch research universities
  and universities of applied sciences
- **Route code**: `netherlands-nuffic` (`netherlands_nuffic` internally)
- **Official domain / base URL**: `https://www.studyinnl.org`
  (`NETHERLANDS_NUFFIC_BASE_URL`) — the program's original public name and
  domain, "Holland Scholarship" (`hollandscholarship.nl`), now
  301-redirects here; confirmed the *current* source by the page's own
  `<title>Nl Scholarship | Study in NL</title>`, not a stale/retired one.
- **Opportunity types**: Scholarship (fixed €5,000 award toward a
  full-time bachelor's or master's programme)
- **Country coverage**: Netherlands; open to non-EEA nationals applying to
  one of the participating institutions
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading Nuffic's public program page. `robots.txt` (standard Drupal
  pattern, checked 2026-08-29) does not disallow `/finances/nl-scholarship`.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as sources
  1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `funding_type = "partial_funding"`, not this pattern's usual
    `fully_funded` default — the page states outright "the scholarship
    amounts to €5,000 ... Please note that this is not a full-tuition
    scholarship."
  - `deadline_keywords = ()`, same reasoning as source #21 (South Africa
    NRF): the page explicitly says "You can find the specific closing
    dates ... on the website of the institution you want to apply to" —
    Nuffic does not itself publish one program-wide deadline, since each
    of the ~30 participating institutions sets its own. Left `null` on
    purpose rather than misattributing one institution's date to the
    whole program.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this backend's
  actual HTTP path (httpx, not just `curl`) — 200, ~49KB real HTML,
  `<h1 class="page-header__title">NL Scholarship</h1>`, real content in
  `.node__content`. No TLS or network issue (unlike sources #16 and #21).
  Implemented and unit-tested against real fixture HTML captured from this
  live fetch.

## 23. Becas MAEC-AECID (Spain)

- **Organization**: Spanish Agency for International Development
  Cooperation (AECID), under the Ministry of Foreign Affairs, EU and
  Cooperation (MAEC)
- **Route code**: `spain-aecid` (`spain_aecid` internally)
- **Official domain / base URL**: `https://www.aecid.es`
  (`SPAIN_AECID_BASE_URL`)
- **Opportunity types**: Scholarship (several named sub-programs — a
  master's program, a diplomatic-school program, an Africa/Middle East
  program — under one umbrella call)
- **Country coverage**: Spain; open to citizens of Latin America, Africa,
  and Asia (this adapter deliberately targets that specific sub-page, not
  AECID's generic scholarships hub, which mostly links to programs for
  Spanish nationals — irrelevant to this platform's international-
  applicant focus)
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading AECID's public program page. `robots.txt` (checked 2026-08-29)
  is permissive (`Disallow:` empty for `*`).
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `deadline_keywords = ()`, same reasoning as sources #21 and #22: the
    page lists several distinct named sub-programs (e.g. Escuela
    Diplomática: 21/05–03/06/2026; África-Med: 02/07–15/07/2026), each
    with its own closing date — a generic keyword-anchored extractor
    would pick one and mislabel it as *the* deadline for the whole page.
  - `funding_type = "partial_funding"` — no "fully funded"/"full
    tuition" language was found on the page (it states a monthly stipend
    plus health insurance, and some sub-programs are aimed at civil
    servants specifically), so this pattern's `fully_funded` default was
    deliberately overridden rather than left unverified.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this backend's
  actual HTTP path (httpx, not just `curl`) — 200, ~169KB real HTML,
  `<h1>Becas para ciudadanos de países de América Latina, África y
  Asia</h1>`, real content in `#main-content`. No TLS or network issue.
  Implemented and unit-tested against real fixture HTML captured from
  this live fetch.

## 24. Australia Awards (DFAT)

- **Organization**: Department of Foreign Affairs and Trade (DFAT),
  Australian Government
- **Route code**: `australia-dfat-awards` (`australia_dfat_awards`
  internally)
- **Official domain / base URL**: `https://www.australiaawards.com.au`
  (`AUSTRALIA_AWARDS_BASE_URL`) — a DFAT-affiliated informational site,
  used instead of `dfat.gov.au` itself; see the live-test note below for
  why.
- **Opportunity types**: Scholarship (the Australian Government's
  flagship program for students and professionals from the Indo-Pacific
  region)
- **Country coverage**: Australia; open to nationals of DFAT's listed
  partner countries (predominantly Indo-Pacific — see
  `dfat.gov.au/people-to-people/australia-awards/participating-countries`,
  itself unreachable from this environment — not open to every country)
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `australiaawards.com.au`'s homepage. `robots.txt` (checked
  2026-08-29, standard WordPress pattern) only disallows
  `/wordpress/wp-admin/`.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - No `deadline_path` configured, and `deadline_keywords = ()`. The
    authoritative intake/closing-dates page
    (`dfat.gov.au/.../australia-awards-scholarships-opening-and-closing-dates`)
    is on `dfat.gov.au`, a host this environment could not reach at all
    (see the live-test note below) — rather than point `deadline_path`
    at a host that cannot be verified, it was left unset. The reachable
    overview site states no specific date itself either way.
  - `title_selectors = ()`, `title_tag_separator = "–"`: the homepage has
    no `<h1>` (a page-builder-style landing page, the same shape as
    source #13, WMI) — the real title comes from the bare
    `<title>Australia Awards</title>` tag.
  - `funding_type = None` — no "fully funded"/"tuition"/"stipend"
    language was found on the pages this adapter can actually read.
    Australia Awards are widely known to be comprehensively funded in
    practice, but that is general/outside knowledge, not something this
    adapter's own source text supports asserting — left honestly
    unclassified rather than guessed either way.
- **LIVE SOURCE TEST: PARTIAL — overview PASSED 2026-08-29, deadline page
  BLOCKED.** `australiaawards.com.au` verified through this backend's
  actual HTTP path (httpx) — 200, ~184KB real HTML. `dfat.gov.au` itself
  — tried with multiple user agents, both `curl` and httpx — consistently
  hung at the TLS-handshake stage until timeout: not an HTTP error, not a
  DNS failure, and no bot-challenge page was ever returned to inspect.
  The same "connects to nothing" pattern already documented for Sierra
  Leone's MTHE (source #12), not a WAF/anti-bot challenge like Cyprus
  (declined-sources table below). Implemented and unit-tested against
  real fixture HTML captured from the successful overview fetch.

## 25. Japanese Government (MEXT) Scholarship (Japan)

- **Organization**: Ministry of Education, Culture, Sports, Science and
  Technology (MEXT/Monbukagakusho), via the official "Study in Japan"
  government portal
- **Route code**: `japan-mext` (`japan_mext` internally)
- **Official domain / base URL**: `https://www.studyinjapan.go.jp`
  (`JAPAN_MEXT_BASE_URL`)
- **Opportunity types**: Scholarship (seven MEXT scholarship types:
  research students, teacher training, undergraduate, Japanese studies,
  college of technology, specialized training college, and the Young
  Leaders Program)
- **Country coverage**: Japan; applicants apply through their home
  country's Japanese embassy or a recommending university
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading the official government portal's MEXT sub-page. No
  `robots.txt` file exists on this host at all (checked 2026-08-29 — the
  site returns its own branded 404 page for that path, not a real
  robots.txt), treated as unrestricted per the standard meaning of a
  missing robots.txt.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - The generic scholarship-overview hub page
    (`/en/planning/scholarships/`) was **not** used — it is a thin
    navigation page (~225 chars of real content) linking to several
    distinct scholarship families (MEXT, JASSO, "Other Scholarships").
    This adapter targets the MEXT-specific sub-page instead, which has
    real, substantial content (8.4KB of real text).
  - `title_selectors = ()`: every page under this site section shares
    the same generic `<h1>Scholarships</h1>` — the real title comes from
    the `<title>` tag, split on the site's own fullwidth vertical bar
    (`｜`, U+FF5C, not the ASCII `|`).
  - `deadline_keywords = ()` — applications route through the
    applicant's home-country embassy or university, each on its own
    schedule; the page states this explicitly and publishes no single
    global deadline, the same honest pattern already established for
    Ireland GOI-IES and Sweden SI (sources #15, #17).
  - `funding_type` is left at this pattern's `fully_funded` default,
    and unlike Australia Awards above, this is *actually verified* by
    the source text: "tuition exempted", a monthly stipend of
    ¥117,000–242,000, and "round-trip travel expenses (airfare)
    provided" all appear explicitly on the page.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~29KB real
  HTML. No TLS or network issue. Implemented and unit-tested against real
  fixture HTML captured from this live fetch.

## 26. ARES International Training Scholarships (Belgium)

- **Organization**: ARES (Académie de Recherche et d'Enseignement
  supérieur), the coordinating body for Wallonia-Brussels Federation
  universities and university colleges in Belgium
- **Route code**: `belgium-ares` (`belgium_ares` internally)
- **Official domain / base URL**: `https://www.ares-ac.be`
  (`BELGIUM_ARES_BASE_URL`)
- **Opportunity types**: Scholarship (bachelor's, one-year specialized
  master's, or 6-month continuing-training programs in Belgium)
- **Country coverage**: Belgium; open to permanent residents of ARES's
  31 partner countries holding a higher-education diploma
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading ARES's specific "Bourses de formations internationales"
  sub-page — **not** the generic `/bourses-de-mobilite` hub, which is a
  category page linking to ~8 distinct instruments (individual mobility
  grants, ASEM-DUO, research prizes, project funding, and this program).
  `robots.txt` (checked 2026-08-29, standard Drupal pattern) is
  permissive.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choice**: `deadline_keywords = ()`, despite a real
  specific closing date appearing on the page ("Date limite :
  18.09.2026") — that date is `DD.MM.YYYY` numeric form, which
  `app/services/parsing.py::_CONFIDENT_DATE_PATTERN` does not match (it
  only recognizes `DD Month YYYY` / `Month DD, YYYY` literal forms by
  design). Extending that shared regex is a cross-cutting change
  affecting every scraper source, not something to do incidentally while
  adding one adapter — left honestly `null` rather than a half-solution.
  `funding_type` is also left `None` — no monetary-amount language was
  found on this page.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~38KB real
  HTML. No TLS or network issue. Implemented and unit-tested against real
  fixture HTML captured from this live fetch.

## 27. France Excellence Eiffel Scholarship Program (France)

- **Organization**: Campus France, on behalf of the French Ministry for
  Europe and Foreign Affairs
- **Route code**: `france-eiffel` (`france_eiffel` internally)
- **Official domain / base URL**: `https://www.campusfrance.org`
  (`FRANCE_CAMPUSFRANCE_BASE_URL`)
- **Opportunity types**: Scholarship (master's and PhD study at French
  higher education institutions)
- **Country coverage**: France; open to non-French applicants up to 29
  (master's) or 35 (PhD) years old
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading Campus France's official program page. `robots.txt` (standard
  Drupal pattern, checked 2026-08-29) is permissive.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `deadline_keywords = ("deadline",)` — the page states a real,
    parseable deadline ("Deadline for the reception of applications by
    Campus France: January 8, 2026") and this one *is* extracted, unlike
    Belgium's above (different date format).
  - Applications are institution-mediated ("Only applications submitted
    by French higher education institutions are accepted") — the same
    standard shape as DAAD and Japan's MEXT Scholarship (both already
    implemented), where the student's chosen institution nominates them,
    not the institution-*initiated* shape this same research pass ruled
    out for Canada's SICS program (see the declined-sources table
    below).
  - `funding_type = None` — no monetary-amount language was found on
    this page (only linked PDF fact sheets, not fetched/parsed);
    Eiffel's real-world reputation as a generous scholarship is outside
    knowledge this page's own text doesn't support asserting.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~146KB real
  HTML. No TLS or network issue. Implemented and unit-tested against real
  fixture HTML captured from this live fetch.

## 28. OeAD Ernst Mach Grant (Austria)

- **Organization**: OeAD (Austria's Agency for Education and
  Internationalisation), financed by the Austrian Federal Ministry of
  Women, Science and Research
- **Route code**: `austria-oead` (`austria_oead` internally)
- **Official domain / base URL**: `https://oead.at`
  (`AUSTRIA_OEAD_BASE_URL`) — `www.oead.at` 301-redirects here; this is
  the current canonical domain.
- **Opportunity types**: Scholarship/grant (a family of named sub-grants
  for research and study stays in Austria)
- **Country coverage**: Austria; open to students/researchers from
  outside Austria (specific eligible countries vary per named sub-grant)
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading OeAD's "Ernst Mach Grant" page. `robots.txt` (checked
  2026-08-29) is permissive for `*`.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choice**: same shape as South Africa NRF and Spain
  AECID (sources #21, #23) — this single page actually describes a
  *family* of named sub-grants (Ernst Mach – Ukraine, worldwide, for
  Fachhochschule study, Follow-Up, ASEA-UNINET, ASEA-UNINET Short-term),
  each with its own distinct closing date and, in at least one case
  (Ukraine), its own distinct monthly amount ("715 euros per month").
  `deadline_keywords = ()` and `funding_type = None`, both deliberate —
  a generic extractor would misattribute one sub-grant's figures to the
  whole page.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~402KB real
  HTML. No TLS or network issue. Implemented and unit-tested against real
  fixture HTML captured from this live fetch.

## 29. AMCI Scholarships of the Kingdom of Morocco (Morocco)

- **Organization**: AMCI (Moroccan Agency for International Cooperation)
- **Route code**: `morocco-amci` (`morocco_amci` internally)
- **Official domain / base URL**: `https://www.amci.ma`
  (`MOROCCO_AMCI_BASE_URL`)
- **Opportunity types**: Scholarship (higher education and professional
  training in Moroccan public institutions)
- **Country coverage**: Morocco; predominantly African international
  students (~85% of AMCI scholarship holders per the page's own stated
  figures)
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading AMCI's academic-cooperation page.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `title_selectors = ()`: the page has no `<h1>` — the real title
    comes from the `<title>` tag ("Coopération Académique | AMCI"),
    split on the ASCII pipe.
  - `deadline_keywords = ()`: applications route through the applicant's
    home country's Moroccan diplomatic representation, the same
    embassy-mediated pattern as Japan's MEXT Scholarship — no single
    global deadline is published on the official page.
  - `funding_type = None` — no funding-amount language was found on this
    specific page (third-party sources cite a monthly stipend figure,
    but this adapter does not assert what its own source text doesn't
    state).
- **LIVE SOURCE TEST: PARTIAL — content page PASSED 2026-08-29,
  `robots.txt` itself returned 403.** The same "monitored, not treated as
  fully blocked" situation already documented for the Swedish Institute
  (source #17): `robots.txt` returned an Apache 403 when fetched
  directly, but the actual content page returned 200 with real HTML
  (~42KB) through this backend's actual httpx path. Implemented and
  unit-tested against real fixture HTML captured from this live fetch.

## 30. Camões Cooperation Scholarships (Portugal)

- **Organization**: Camões – Instituto da Cooperação e da Língua, I.P.,
  under Portugal's Ministry for Foreign Affairs
- **Route code**: `portugal-camoes` (`portugal_camoes` internally)
- **Official domain / base URL**: `https://www.instituto-camoes.pt`
  (`PORTUGAL_CAMOES_BASE_URL`)
- **Opportunity types**: Scholarship (bachelor's, integrated master's,
  master's, and PhD study at Portuguese higher education institutions)
- **Country coverage**: Portugal; open to nationals/residents of 9 named
  bilateral-cooperation partner countries (Angola, Cabo Verde, Colômbia,
  Etiópia, Guiné-Bissau, Moçambique, São Tomé e Príncipe, Senegal,
  Timor-Leste)
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading Camões's specific "Formação em Portugal" leaf page — **not**
  the "Bolsas do Camões, I.P." hub (a thin 2-link navigation page) or its
  "Bolsas da Cooperação" child (also thin, no further content), both of
  which were fetched and confirmed to be pure navigation before this
  deeper page was chosen. `robots.txt` (a Joomla-standard pattern,
  checked 2026-08-29) does not disallow this path.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `funding_type` is kept at this pattern's `fully_funded` default —
    unlike Belgium, Austria, and Morocco earlier in this same research
    pass, this classification *is* genuinely supported by the source
    text: a real funding table names a maintenance subsidy (monthly), a
    tuition subsidy ("Subsídio de Propina", up to €1,306.25–2,612.50/year
    depending on degree level), a housing subsidy, and an installation
    subsidy, each with real euro amounts — the same reasoning already
    applied to Japan's MEXT Scholarship (source #25).
  - `deadline_keywords = ()` — "A apresentação das candidaturas decorre,
    unicamente, no país de origem junto das competentes autoridades
    locais" (applications are submitted only in the applicant's home
    country, through local authorities and Portugal's embassies) — the
    same embassy-mediated pattern already established for Japan MEXT and
    Morocco AMCI (sources #25, #29); no single global deadline is
    published on this page.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~58KB real
  HTML. No TLS or network issue (note: the page is UTF-8 but a raw
  `curl`-saved copy decoded incorrectly with Python's strict UTF-8
  reader during initial inspection — httpx's own encoding detection
  handled it correctly, confirmed by re-fetching through this backend's
  actual client before trusting the result). Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 31. Beca Colombia Extranjeros (Colombia)

- **Organization**: ICETEX – Instituto Colombiano de Crédito Educativo y
  Estudios Técnicos en el Exterior (Colombia's national student-financing
  agency)
- **Route code**: `colombia-icetex` (`colombia_icetex` internally)
- **Official domain / base URL**: `https://web.icetex.gov.co`
  (`COLOMBIA_ICETEX_BASE_URL`)
- **Opportunity types**: Scholarship (Spanish-language courses, and
  specialization/master's study for foreign nationals in Colombia)
- **Country coverage**: Colombia
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading ICETEX's `/becas/beca-colombia-extranjeros` page. The site
  (Liferay) puts a hidden accessibility `<h1 class="hide-accessible">
  Navegación</h1>` before the real content — the same class of bug
  already documented for India ICCR — and reuses one
  `.journal-content-article` class for at least 8 unrelated blocks on the
  page, including a "Historial" accordion holding the three *previous*
  application cycles' full text. Selectors are scoped to the one stable,
  unique anchor Liferay stamps on the actual article content:
  `[data-analytics-asset-title='Beca Colombia Extranjeros']`, keyed to the
  article's own title rather than any one cycle, and confirmed
  2026-08-29 to contain only the current cycle's block in document order.
  A companion page, `/becas/programa-de-reciprocidad-para-extranjeros-en-
  colombia`, was fetched and rejected first — after resolving the same
  hidden-h1 issue there, its real content is a single 330-character
  paragraph with no funding or deadline information, too thin to be a
  usable source on its own. A second candidate link from that page,
  `/ies/convocatoria`, was also fetched and rejected — it is an unrelated
  governance notice (election of a public-university representative to
  ICETEX's board), not a scholarship page. `robots.txt` (checked
  2026-08-29) is fully permissive (`Disallow:` empty for `*`).
- **API / RSS / Sitemap**: None published (a `sitemap.xml` is referenced
  in `robots.txt` but was not used — no API/feed for opportunity data)
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `funding_type = None` — no explicit funding-coverage language
    (tuition-free, stipend amount, "fully funded", etc.) appears on the
    page itself, only a description of what the program lets applicants
    study and a link to a separate PDF "bases de postulación" document
    this scraper does not parse. Left unset rather than guessed from the
    "Beca" (scholarship) name alone.
  - `deadline_keywords = ()` — the current cycle's page text does state a
    real deadline ("La convocatoria estará abierta hasta el próximo 5 de
    junio de 2026") but in Spanish month-name form, which
    `extract_confident_date_after` cannot parse (it only recognizes
    English month names) — the same documented limitation already hit
    with Belgium ARES's numeric-date deadline (source #26). Left unset
    because the parser cannot honestly extract it, not because no
    deadline exists.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~163KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 32. Becas para Extranjeros (Chile)

- **Organization**: AGCID – Agencia Chilena de Cooperación Internacional
  para el Desarrollo (Chile's development-cooperation agency)
- **Route code**: `chile-agcid` (`chile_agcid` internally)
- **Official domain / base URL**: `https://www.agcid.gob.cl`
  (`CHILE_AGCID_BASE_URL`)
- **Opportunity types**: Scholarship (master's-level study and training
  courses for foreign nationals in Chile)
- **Country coverage**: Chile
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading AGCID's `/becas/becas-para-extranjeros` page — a single unique
  `<h1>` and `<article>` element, both confirmed unique on the page.
  `robots.txt` (standard Joomla pattern, the same class already seen with
  Portugal Camões) does not disallow this path.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `deadline_keywords = ()` and `funding_type = None` — the article
    bundles several distinct bilateral/regional sub-programs (a
    "República de Chile" program open to a long Latin American/Caribbean
    country list, a Pacific Alliance program limited to Colombia/México/
    Perú, a cross-border-integration program limited to Perú/Bolivia/
    Argentina, and a Manuela Sáenz mobility program limited to Ecuador/
    Paraguay), and the two most-described sub-programs have materially
    *different* funding formulas (one explicitly excludes airfare, the
    other explicitly includes round-trip airfare). The page itself also
    carries an explicit disclaimer that the description is "a modo de
    referencia en base al procedimiento de convocatorias anteriores"
    (reference only, based on *previous* calls) pending each call's
    official republication — the same multi-program shape already
    handled honestly for South Africa NRF, the Netherlands, and Spain
    AECID (sources #21-#23).
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~50KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 33. Beca Alianza del Pacífico (Peru)

- **Organization**: PRONABEC – Programa Nacional de Becas y Crédito
  Educativo, under Peru's Ministry of Education
- **Route code**: `peru-pronabec` (`peru_pronabec` internally)
- **Official domain / base URL**: `https://www.pronabec.gob.pe`
  (`PERU_PRONABEC_BASE_URL`)
- **Opportunity types**: Scholarship (one-semester academic exchange for
  undergraduate, doctoral, and postdoctoral students/researchers/faculty
  at Peruvian higher-education institutions)
- **Country coverage**: Peru; inbound applicants restricted to nationals
  of the other three Pacific Alliance member states (Chile, Colombia,
  Mexico) — a real but narrow eligibility, the same honest
  bilateral/multilateral-partner pattern already used for Portugal
  Camões (source #30) rather than skipped for being non-global.
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading PRONABEC's `/beca-alianza-del-pacifico/` page, which states
  explicitly "Perú ofrece 50 vacantes para ciudadanos extranjeros" (Peru
  offers 50 slots for foreign citizens) with its own dedicated schedule
  section for foreign applicants. `robots.txt` (standard WordPress
  pattern) only disallows `/wp-admin/` and `/inicio/*`, not this path.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `title_selectors = ()`, `title_tag_separator = " – "` — the page has
    no `<h1>` at all (a WordPress page-builder layout, the same shape
    already seen with WMI and Australia Awards); the real title comes
    from the `<title>` tag, split on the en dash (U+2013):
    "Beca Alianza del Pacífico – PRONABEC | ...".
  - `deadline_keywords = ()` — the real inbound-to-Peru schedule stated
    on the page ("Del 29/5/2026 al 4/6/2026") is in `DD/MM/YYYY` numeric
    form, which `extract_confident_date_after` cannot parse (English
    month-name literals only) — the same documented limitation already
    hit with Belgium ARES and Colombia ICETEX (sources #26, #31).
  - `funding_type = "partial_funding"` — the page explicitly lists
    concrete benefits (food, local transport, interprovincial and
    international transport, medical insurance) but never states tuition
    is covered or waived; as an academic-exchange program the student
    stays enrolled at their home institution, so this pattern's inherited
    `fully_funded` default would overstate what the page actually
    promises.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~307KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 34. GKS (Global Korea Scholarship) Program (South Korea)

- **Organization**: NIIED – National Institute for International
  Education, under South Korea's Ministry of Education
- **Route code**: `south-korea-gks` (`south_korea_gks` internally)
- **Official domain / base URL**: `https://www.studyinkorea.go.kr`
  (`SOUTH_KOREA_GKS_BASE_URL`)
- **Opportunity types**: Scholarship (undergraduate, associate, master's,
  and doctoral degree study, including Korean-language training, at
  designated Korean universities)
- **Country coverage**: South Korea
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `/in/plan/scholarship.do`. The page's only real `<h1>` is the
  site logo ("StudyinKorea"), not a title — the real title comes from
  `<h2 class="title">GKS (Global Korea Scholarship) Program</h2>`, the
  first of two matches for that selector (the second, "Other
  Scholarships", is a sibling tab for unrelated programs). Content is
  scoped to `#gks-tab1`, confirmed to hold only the GKS section
  (~12KB) — the surrounding `main` element also contains the "Other
  Scholarships" tab's content later in the DOM. `robots.txt` (`Allow: /`
  plus a narrow `Disallow: /Sims/`) does not disallow this path.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `deadline_keywords = ()` — applications route through either a
    Korean embassy (Embassy Track) or a designated university
    (University Track), each with its own sub-quota and schedule
    described only by month, not a parseable date literal — the same
    embassy/university-track pattern already established for Japan
    MEXT (source #25).
  - `funding_type` kept at this pattern's `fully_funded` default — the
    page explicitly states benefits include "Airfare, language training
    costs, tuition, and study allowances", genuinely supported by the
    source text, the same reasoning already applied to Japan MEXT and
    Portugal Camões.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~124KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 35. Government University Scholarships (Saudi Arabia)

- **Organization**: Ministry of Education (MOE), Saudi Arabia
- **Route code**: `saudi-arabia-moe` (`saudi_arabia_moe` internally)
- **Official domain / base URL**: `https://www.moe.gov.sa`
  (`SAUDI_ARABIA_MOE_BASE_URL`)
- **Opportunity types**: Scholarship (undergraduate through doctoral
  study at Saudi public universities, excluding health/medical
  specialties)
- **Country coverage**: Saudi Arabia — specifically the "external
  scholarships" track for non-Saudi students applying from outside the
  Kingdom (the page also describes a separate "internal scholarships"
  track for non-Saudi students already resident in the Kingdom, which
  this platform's inbound-discovery use case does not target)
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `/en/education/ResidentsAndvisitors/Pages/
  PublicUniversitiesScholarships.aspx` (a SharePoint site).
  `robots.txt` only disallows `/Lists/`, not this path.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `title_selectors = ()`, no `title_tag_separator` — the page has no
    `<h1>` at all, and its `<title>` tag interleaves Arabic and English
    ("وزارة التعليم | \n\tScholarships in Public Universities:") with
    the real English text in the *second* segment.
    `title_tag_separator` only supports taking the first segment (by
    design, so every source shares one simple rule rather than each
    needing its own split-direction flag) — rather than mis-extracting
    the Arabic half or special-casing the shared base class for one
    source, this source deliberately falls through to this pattern's
    final fallback (a title formatted from `external_id`).
  - `funding_type = None` — the page explicitly states Saudi government
    scholarships come in three distinct tiers ("free scholarships in
    which the student gets full benefits", "partial scholarships", and
    "grants paid for"), so no single funding label can honestly
    describe the whole opportunity — the same reasoning already applied
    to Chile AGCID (source #32).
  - `deadline_keywords = ()` — the page states explicitly "The opening
    date for the scholarship application program is determined
    according to the requirements of the academic year at
    universities", i.e. decentralized per-university — the same
    pattern already established for the Netherlands Nuffic (source
    #22).
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~108KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 36. Qatar Scholarships (Qatar)

- **Organization**: Qatar Fund For Development (QFFD), in partnership
  with Qatari higher-education institutions (Lusail University, Hamad
  Bin Khalifa University/Geneva Graduate Institute, Doha Institute for
  Graduate Studies)
- **Route code**: `qatar-scholarships` (`qatar_scholarships` internally)
- **Official domain / base URL**: `https://www.qatarscholarships.qa`
  (`QATAR_SCHOLARSHIPS_BASE_URL`)
- **Opportunity types**: Scholarship (undergraduate, executive/
  professional diploma, and graduate study at partner Qatari
  institutions)
- **Country coverage**: Qatar
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `/en-US/Programs`. The homepage itself is a JS-rendered
  single-page app that serves only a near-empty "offline, read-only"
  shell to a non-JS client, so `/en-US/Programs` was used instead — a
  server-rendered route with real substantial content (~47KB after
  cleaning; two other guessed routes, `/Eligibility` and `/Scholarships`,
  both 404). The page has no `<h1>`; `<title>` is "Programs\n\t\t· Qatar
  Scholarships", split on the literal newline.
  `robots.txt` declares awareness of the newer "content-signal"
  convention but sets no actual `search`/`ai-input`/`ai-train` value
  either way for any use, and contains no classic `Disallow` rule for
  this path either — by the file's own stated rule ("If the website
  operator does not include a content signal for a corresponding use,
  the website operator neither grants nor restricts permission"), this
  is a documented absence of restriction for this platform's use
  (structured opportunity-discovery extraction with mandatory human
  officer review before publication), recorded explicitly here rather
  than treated as an ordinary permissive `robots.txt`.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `funding_type = None` — the page describes several partner-
    institution programs with materially different funding: Lusail
    University and Doha Institute both state "Full tuition waiver...
    Monthly stipend... Medical insurance", but the HBKU/Geneva Graduate
    Institute Executive Diploma explicitly states "**Partial** tuition*
    ... *Students contribute CHF3,500 toward their tuition" — the same
    multi-program funding conflict already handled honestly for Chile
    AGCID (source #32).
  - `deadline_keywords = ()` — no deadline-style date literal appears
    anywhere on the page.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~178KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 37. Swiss Government Excellence Scholarships (ESKAS) (Switzerland)

- **Organization**: Federal Commission for Scholarships for Foreign
  Students (FCS/ESKAS), under the State Secretariat for Education,
  Research and Innovation (SBFI)
- **Route code**: `switzerland-sbfi-eskas` (`switzerland_sbfi_eskas`
  internally)
- **Official domain / base URL**: `https://www.sbfi.admin.ch`
  (`SWITZERLAND_SBFI_BASE_URL`)
- **Opportunity types**: Scholarship (postgraduate research at any Swiss
  cantonal university, university of applied sciences, ETHZ/EPFL, or an
  ETH Domain research institute; and a separate art-scholarship track)
- **Country coverage**: Switzerland; open to applicants from 183 countries
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `/en/swiss-government-excellence-scholarships`. `robots.txt`
  (`Disallow:` empty for `*`) is fully permissive.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `deadline_keywords = ()` — the page explicitly states "Information
    on application deadlines and scholarship available by country of
    origin will be published here in August 2026"; deadlines are set
    per country of origin, routed through Swiss diplomatic
    representations — the same embassy-mediated pattern already
    established for Japan MEXT and GKS (sources #25, #34).
  - `funding_type = "partial_funding"`, not this pattern's
    `fully_funded` default — the page states a concrete monthly amount
    ("funding: CHF 2450.--/month") but never states whether tuition
    fees are covered, unlike Japan MEXT/Portugal Camões/GKS which
    explicitly confirm tuition coverage.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~198KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 38. Poland My First Choice (NAWA) (Poland)

- **Organization**: Polish National Agency for Academic Exchange (NAWA)
- **Route code**: `poland-nawa-myfirstchoice` (`poland_nawa_myfirstchoice`
  internally)
- **Official domain / base URL**: `https://nawa.gov.pl`
  (`POLAND_NAWA_BASE_URL`)
- **Opportunity types**: Scholarship (full-time second-cycle/master's
  study at Polish higher education institutions)
- **Country coverage**: Poland; open to citizens of ~40 named countries
  and territories
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `/en/students/foreign-students/poland-my-first-choice-programme`.
  The page has a hidden accessibility `<h1 class="sr-only">` before the
  real content `<h1 class="header">` — the same class of bug already
  documented for India ICCR and Colombia ICETEX (source #31) —
  `title_selectors = ("h1.header", "h1")` skips it. NAWA runs several
  other named programmes (Banach NAWA, Ignacy Łukasiewicz, Polonista
  NAWA), each restricted to a narrower partner-country list under
  Polish Development Assistance; "Poland My First Choice" was chosen
  because it has the broadest eligible-country list and is not itself a
  multi-program bundle. `robots.txt` (standard Joomla pattern) does not
  disallow this path.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `deadline_keywords = ()` — no deadline-style date literal, or even
    the words "deadline"/"closing date", appears anywhere on the page
    (confirmed by a full-text search).
  - `funding_type = "partial_funding"` — the page confirms "an
    exemption from tuition fees at public universities" explicitly, but
    only vaguely references "a scholarship" without ever stating a
    monthly amount or whether living costs are covered.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~291KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 39. Government Scholarships – Developing Countries (Czech Republic)

- **Organization**: Ministry of Education, Youth and Sports (MŠMT),
  jointly with the Ministry of Foreign Affairs (MZV) and Ministry of
  Health
- **Route code**: `czech-republic-msmt` (`czech_republic_msmt`
  internally)
- **Official domain / base URL**: `https://msmt.gov.cz`
  (`CZECH_REPUBLIC_MSMT_BASE_URL`)
- **Opportunity types**: Scholarship (bachelor's, follow-up master's,
  and doctoral study at Czech public higher education institutions,
  including a one-year Czech-language preparatory course)
- **Country coverage**: Czech Republic; open to citizens of 13 named
  developing/partner countries for the 2027/2028 academic year
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `/en/scholarships/government-scholarships-developing-countries`.
  This site is a headless-CMS build (Next.js frontend over a WordPress
  backend, evidenced by genuine `wp-block-*` classes mixed with
  Tailwind utility classes) whose React-rendered wrapper divs carry
  auto-generated ids (e.g. `id="S:5"`, a React Server Components
  streaming-boundary id) that are deployment artifacts, not stable
  content anchors — deliberately not used. Content is instead scoped to
  `.global-msmt`, a real, site-specific custom class the page's own
  developers added — the same class of choice already made for
  Colombia ICETEX's `data-analytics-asset-title` and Chile AGCID over
  positional/auto-generated alternatives. `robots.txt` (`Allow: /`,
  only `/api/` and `/preview/` disallowed) does not disallow this path.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - Unlike every other source in this initiative's default
    configuration, `deadline_keywords` is **not** overridden here — it
    is left at the base class's own default (`("deadline", "closing
    date")`) because this page has a genuine, singular, cleanly
    extractable deadline: a section literally titled "APPLICATION
    SUBMISSION AND DEADLINE" stating "Each applicant is obliged to fill
    in an electronic application form by 30 September 2026 at the
    latest" — confirmed by running `extract_confident_date_after`
    directly against the real fixture text and getting back
    `2026-09-30`.
  - `funding_type = None` — the specific monthly stipend amount (found
    only in third-party search summaries, not on this page) lives in a
    linked PDF/DOCX "Guidelines" document this scraper does not parse —
    no funding-coverage language appears in the page's own HTML text.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~238KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 40. "World in Serbia" Scholarships (Serbia)

- **Organization**: Ministry of Education, Republic of Serbia, in
  cooperation with the Ministry of Foreign Affairs
- **Route code**: `serbia-world-in-serbia` (`serbia_world_in_serbia`
  internally)
- **Official domain / base URL**: `https://welcometoserbia.gov.rs`
  (`SERBIA_WELCOMETOSERBIA_BASE_URL`)
- **Opportunity types**: Scholarship (bachelor's, master's, doctoral,
  and professional study at Serbian public universities, including a
  free intensive Serbian-language course)
- **Country coverage**: Serbia; open to candidates from Non-Aligned
  Movement member/observer countries in Africa, Asia, and Central/South
  America
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `/scholarships`. `robots.txt` only disallows `/Admin`, not
  this path.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `title_selectors = ("h2",)` — the page has no `<h1>`; its only
    heading is `<h2>Scholarships</h2>`, generic but honest (identical to
    the `<title>` tag's own first segment), the same acceptance of a
    real-if-plain heading already applied to WMI and other titleless-
    page sources in this pattern.
  - `deadline_keywords = ()` — "Every year, the Ministry of Education
    announces a competition... in cooperation with the Ministry of
    Foreign Affairs, through consular representation offices" —
    consulate-mediated, no single global deadline, the same pattern as
    Japan MEXT and GKS.
  - `funding_type` kept at this pattern's `fully_funded` default — the
    page explicitly states "study free of charge", "accommodation and
    food", "a monthly financial allowance", and "health insurance".
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~34KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 41. Romanian Government Scholarships (MFA) (Romania)

- **Organization**: Ministry of Foreign Affairs (MFA), jointly with the
  Ministry of Education and Research
- **Route code**: `romania-mfa` (`romania_mfa` internally)
- **Official domain / base URL**:
  `https://scholarships.studyinromania.gov.ro` (`ROMANIA_MFA_BASE_URL`)
- **Opportunity types**: Scholarship (bachelor's, master's, and doctoral
  study at accredited Romanian higher education institutions)
- **Country coverage**: Romania; open to foreign citizens from non-EU
  countries (with named exceptions — Romanian-heritage communities,
  protection-status holders, diplomatic staff, etc., who have separate
  programmes)
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `/scholarship-about`. Content is scoped to
  `.about-text-block`, a unique, site-specific class — not the page's
  own generic `.content` class, which matches 6 different unrelated
  blocks on the page. `robots.txt` (`Allow: /`, only query-string paths
  and `/tmp`/`/cgi-bin/` disallowed) does not disallow this path.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `deadline_keywords = ()` despite the page stating a real, specific
    closing date ("The deadline for submitting applications is 31
    March 2026") in a fully parseable "DD Month YYYY" literal —
    deliberately, not because the date itself is unparseable this time.
    The page's *first* occurrence of the word "deadline" is an
    unrelated, earlier mention ("comply with the enrolment deadline")
    with no date nearby; `extract_confident_date_after` only ever
    searches after a keyword's *first* occurrence (by design — see that
    function's own docstring), so it correctly finds nothing here,
    confirmed directly against the real fixture text. Extending that
    shared function to consider every occurrence of a keyword is a
    cross-cutting change affecting every scraper source, not something
    to do incidentally while adding one adapter.
  - `funding_type` kept at this pattern's `fully_funded` default — the
    page explicitly confirms financing of tuition fees (both the
    preparatory year and the actual studies), a monthly scholarship, and
    accommodation expenses (this language appears further down the page
    than the 5,000-character description excerpt reaches, but was read
    in full before classifying).
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~125KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 42. Stipendium Hungaricum (Hungary)

- **Organization**: Tempus Public Foundation, under Hungary's Ministry
  of Foreign Affairs and Trade
- **Route code**: `hungary-stipendium-hungaricum`
  (`hungary_stipendium_hungaricum` internally)
- **Official domain / base URL**: `https://stipendiumhungaricum.hu`
  (`HUNGARY_STIPENDIUM_BASE_URL`)
- **Opportunity types**: Scholarship (bachelor's, master's, one-tier
  master's, doctoral, and non-degree study at Hungarian higher
  education institutions)
- **Country coverage**: Hungary; available in over 100 countries across
  five continents via bilateral education agreements
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `/about/`. `robots.txt` is empty (no restrictions declared).
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `title_selectors = ()`, no `title_tag_separator` — a heavily
    JS-rendered site with no semantic heading markup at all (no
    `<h1>`-`<h4>` tags anywhere on the page) and a generic `<title>`
    ("About - Stipendium Hungaricum") that only ever yields the single
    word "About" once split — deliberately falls through to this
    pattern's final fallback (a title formatted from `external_id`),
    the same choice already made for Saudi Arabia MOE (source #35).
  - `deadline_keywords = ()` — no deadline-style date literal, or even
    the words "deadline"/"closing date", appears anywhere on the page.
  - `funding_type` kept at this pattern's `fully_funded` default — the
    page explicitly states "Tuition-free education", a monthly stipend
    with real HUF/EUR figures for bachelor's/master's level, and a
    separate, higher monthly figure for doctoral level.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~113KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 43. Becas de Excelencia del Gobierno de México (AMEXCID) (Mexico)

- **Organization**: Agencia Mexicana de Cooperación Internacional para
  el Desarrollo (AMEXCID), under Mexico's Secretaría de Relaciones
  Exteriores (SRE)
- **Route code**: `mexico-amexcid` (`mexico_amexcid` internally)
- **Official domain / base URL**: `https://www.gob.mx`
  (`MEXICO_AMEXCID_BASE_URL`)
- **Opportunity types**: Scholarship (master's and doctoral study,
  graduate/postdoctoral research, and undergraduate/graduate academic
  mobility, at participating Mexican higher education institutions)
- **Country coverage**: Mexico; open to citizens of over 170 countries
  via bilateral agreements, multilateral mechanisms, and special
  agreements
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `/amexcid/acciones-y-programas/becas-para-extranjeros-29785`
  (one transient timeout on the first attempt, resolved cleanly on
  retry — 2/2 subsequent attempts succeeded). `robots.txt` has no
  `User-agent: *` block at all (only specific Google-bot entries, all
  `Disallow:` empty), so no rule applies to this backend's generic
  client.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - Content is scoped to `.col-sm-7.pull-left`, the article-body column
    — not the page's own generic `main` element, which also includes an
    unrelated "Publicaciones Recientes" (recent news) sidebar list of
    five other AMEXCID news items ahead of the actual scholarship
    content in document order.
  - `deadline_keywords = ()` and `funding_type = None` — this specific
    overview page is a bilingual (Spanish/English) marketing summary
    that explicitly defers all concrete terms — dates, tuition/stipend
    coverage — to "las Condiciones Generales de la Convocatoria" (the
    official Call's General Conditions), reachable only by contacting
    `infobecas@sre.gob.mx` or a document not linked as plain HTML on
    this page — no funding-coverage language or date literal appears in
    the page's own text.
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx, not just `curl`) — 200, ~59KB real
  HTML, no spoofed user agent required. Implemented and unit-tested
  against real fixture HTML captured from the httpx fetch.

---

## 44. EducationUSA "Find Financial Aid" Database (United States)

Closes this platform's United States gap — the only prior US-facing
sources (Grants.gov, USAJOBS, ReliefWeb, sources 1–7) are federal
grants/jobs/humanitarian postings, not international-student
scholarships, and the one dedicated candidate researched earlier
(Fulbright Program) was rejected as unsuitable (see the table below —
fragmented across ~160 individual US embassy pages with no single stable
page).

- **Organization**: U.S. Department of State, Bureau of Educational and
  Cultural Affairs (ECA) — EducationUSA network
- **Route code**: `educationusa-financial-aid`
  (`educationusa_financial_aid` internally)
- **Official domain / base URL**: `https://educationusa.state.gov`
  (`EDUCATIONUSA_BASE_URL`) — a `.state.gov` federal government domain
- **Opportunity types**: Scholarship (institution-specific awards for
  international students, spanning undergraduate through
  doctorate/post-doctorate)
- **Country coverage**: United States (study destination); most listed
  scholarships are open to international students broadly, a subset are
  restricted to applicants from specific countries (the listing's own
  country filter) — this adapter records only what each entry's own page
  states, never inferring eligibility for any nationality
- **Discovery method**: **Web scraper, paginated-listing pattern** —
  the first production consumer of `app/services/pagination_engine.py`'s
  `paginate_by_url`. `/find-financial-aid?page=N` (`N` 0-indexed) is a
  real, plain server-rendered Drupal Views listing (no browser rendering
  needed) of 277+ individual scholarships (~28 pages), each a `.views-row`
  with a title/link (`.views-field-title a`), a host institution
  (`.field-hei-institution-name`), and the site's own free-text deadline
  statement (`.field-scholarship-deadline` — often recurring/rolling,
  e.g. "Fall semester: July 1st; Spring semester: November 1st"; kept as
  a plain description string, never forced into a single parsed date).
  Each entry's own EducationUSA detail page (not its external "More
  information" link, which would mean ~280 extra per-sync fetches
  against arbitrary third-party university domains) is used as both
  `official_source_url` and `official_application_url`.
- **robots.txt**: returns HTTP 403 (not 200, not unreachable). Per
  RFC 9309 §2.3.1.3, a non-2xx status on robots.txt means no crawl
  restrictions apply — the same interpretation major search-engine
  crawlers use — so there is no `Disallow` rule this adapter could be
  violating even if the file were readable.
- **API / RSS / Sitemap**: None published for this specific listing
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **LIVE SOURCE TEST: PASSED 2026-08-29.** Verified through this
  backend's actual HTTP path (httpx) — 200, real Drupal-rendered HTML,
  no spoofed user agent required, on three separate real fetches (page
  0, page 1, and a genuinely-past-the-last-page response confirming the
  listing's own "no more results" behavior, `?page=40` → 0 rows).
  Implemented and unit-tested against all three real fixture pages,
  captured unmodified from the httpx fetches
  (`tests/fixtures/educationusa_find_financial_aid_*.html`) — proving
  the pagination engine's stop-on-empty-page and dedup-by-key logic
  against the real site's real termination behavior, not a synthetic
  stand-in.

---

## 45. Joint Japan/World Bank Graduate Scholarship Program (JJ/WBGSP)

Found while researching multi-source-type coverage for Sierra Leone
specifically (see docs/COUNTRY_PROVIDER_REGISTRY.md's twelfth-pass note)
— a second source type (FUNDING_ORGANIZATION / international
organization) beyond the single flagship government source most
countries in this registry have.

- **Organization**: World Bank Group, Development Economics Vice
  Presidency (DEC); funded by the Government of Japan
- **Route code**: `world-bank-jjwbgsp` (`world_bank_jjwbgsp` internally)
- **Official domain / base URL**: `https://www.worldbank.org`
  (`WORLD_BANK_JJWBGSP_BASE_URL`)
- **Opportunity types**: Scholarship (master's degree, development-related
  fields, at 44 participating programs across 24 universities in the US,
  Europe, Africa, Oceania, and Japan)
- **Country coverage**: Not tied to a single destination country — left
  `None` rather than guessed, same as Wells Mountain Initiative (source
  #13). Open to citizens of World Bank member developing countries;
  **Sierra Leone is confirmed on the programme's own published eligible-
  countries list** (`/en/programs/scholarships/brief/countries-eligible-
  for-jjwbgsp-scholarship`), checked directly rather than assumed.
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `/en/programs/scholarships/jj-wbgsp`. `robots.txt` is
  `Allow: /` at the top level with only narrow, unrelated `Disallow:`
  rules (system paths, retired templates) — none matching this page.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `title_selectors = ("h2.lp__lead_lgtitle",)` — the page's actual
    `<h1>` is the generic "World Bank Scholarships Program" heading
    shared by every sub-page under this program, not this specific
    programme's real name.
  - `content_selectors = (".lp__body_content",)` — the page has five
    `.lp__body_content` blocks (overview, eligibility, guideline links,
    selection process, benefits); only the first (the programme's own
    real lead description) is used, matching `_first_match`'s
    take-the-first-match behavior.
  - `deadline_keywords = ("application window #1", "application window
    #2", "deadline")` — the page states both application windows
    together (e.g. "Application Window #1 from January 18 to February
    26, 2027"); `extract_confident_date_after` correctly skips the
    day+month-only opening date for the first full day+month+year
    literal that follows, live-verified against the real fetched page.
- **LIVE SOURCE TEST: PASSED 2026-08-30.** Verified via `curl` and this
  backend's actual parsing path — 200, ~58KB real server-rendered HTML,
  no browser rendering needed, no spoofed user agent required.
  Implemented and unit-tested against a real fixture captured unmodified
  from the fetch (`tests/fixtures/world_bank_jjwbgsp_overview.html`),
  confirming the extracted deadline (2027-02-26) matches the page's own
  stated Window #1 closing date.

---

## Sources evaluated and deliberately not integrated

Documented in full in `scholarsphere_backend/README.md` ("Source research
notes") — restated here because the platform specification asks for a
record of what was checked, not just what was added:

| Candidate | Why not integrated |
|---|---|
| StudyPortals / ScholarshipPortal / MastersPortal / PhDPortal | No official public API; only unofficial scraper wrappers exist |
| ScholarshipAPI.com | Real commercial product, but its endpoint/auth documentation could not be independently fetched in the environment this was researched from — not integrated against unverified assumptions |
| Devpost | No officially documented public API |
| Eventbrite | Removed its public Event Search API in 2019; remaining endpoints don't support open-ended discovery |
| UKRI Gateway to Research (`gtr.ukri.org`) | Real, free, official API — but it publishes *already-awarded* grants, not open calls to apply to. Presenting historical awards as live opportunities would conflict with the platform's "never mislead" rule, so it was left out |
| EURAXESS | No official public API found; only third-party scrapers |
| Fulbright Program | Researched 2026-08-22. The US-student-facing site (`us.fulbrightonline.org`) is the wrong audience for this platform; the foreign-student program is administered per-country through ~160 individual US embassy pages with no single list of open calls; the one Sierra-Leone-specific page checked (`sl.usembassy.gov/educational-professional-exchanges/`) returned a generic "Technical Difficulties" error page rather than real content — no single stable page to scrape reliably |
| China Scholarship Council (CSC) / `csc.edu.cn` / `studyinchina.csc.edu.cn` | Researched 2026-08-29 — `BLOCKED`, see `docs/COUNTRY_PROVIDER_REGISTRY.md`'s China entry. A real, major, legitimate official program (the Chinese Government Scholarship), but every page checked — including `robots.txt` itself — returns HTTP 412 or an obfuscated JavaScript anti-bot challenge page ("系统繁忙，请稍后再试" / "system busy, try again later"), not real content. Never bypassed. |
| Mastercard Foundation Scholars Program (`mastercardfdn.org`) | Researched 2026-08-30 — real, major (58,000+ scholarships committed, 62 partner universities across Africa and internationally), directly relevant to Sierra Leone. `robots.txt` explicitly `Allow: /` for `ClaudeBot` by name. The program's own overview page is real, static, server-rendered content, but — same reason Canada/Denmark/Wales were rejected — has no single deadline or application path: "the application process and decision-making are managed individually by each partner" institution. The actual per-institution listing (`.../where-to-apply/`, "Search the listings below") is a client-side widget with **no server-rendered fallback** — a plain fetch returns literally "Institutions Error loading data. Please try again." instead of the list. Its underlying data API could not be located in the page's own static JS (no inline endpoint URL, and the referenced `kachow.js` bundle is a small unrelated utility script, not the widget itself) without executing the page's JS, which this sandbox cannot do against external sites (same `net::ERR_CONNECTION_RESET` proxy-TLS limitation documented for the original browser-rendering fallback work — re-confirmed live against this exact URL, 2026-08-30). **Not integrated, but a strong candidate for a future session with a working outbound browser-automation path**: enable `allow_browser_rendering` on a listing-page adapter for `/where-to-apply/`, live-verify the rendered institution list's structure, and confirm robots.txt still allows it before implementing. |

DAAD, Chevening, and Commonwealth Scholarships were in this table until
2026-08-22 for the same reason as the rows above (no public API) — they are
now sources 8–10, added via the web-scraper tier once that became an
explicitly approved ingestion method (see the top of this document).

**The remaining real coverage gap**: most other named, well-known
scholarship programs — university-specific funds and smaller foundations —
still publish no public API and have not been evaluated for scraping.
Closing that gap further needs either a licensed commercial data feed,
per-provider partnership/manual-entry work, or evaluating specific
additional named sites for scraping the same way sources 8–12 were (see
`app/services/web_scraper_base.py`) — not a generic crawler.

## Browser-rendering fallback (JavaScript-only sites)

Every source above works with a plain HTTPS GET (`app/core/
http_client.py::get_html`) - no source in this registry has ever needed
more than that. This session's research did, however, run into several
official government sites that return no usable content without
executing JavaScript (Egypt's EGYAID/Study-in-Egypt portal and
Indonesia's `.go.id` KNB site both return a near-empty client-side-app
shell over plain HTTP - see their entries in
`docs/COUNTRY_PROVIDER_REGISTRY.md`), so `app/services/
browser_rendering.py` adds an opt-in, headless-Chromium (Playwright)
rendering fallback for exactly that case:

- **Opt-in per source, not automatic.** A `WebScraperSource` subclass
  sets `allow_browser_rendering = True` (and, optionally,
  `browser_wait_for_selector` naming a CSS selector to wait for) only
  after live-testing shows its plain-HTTP response really is an
  unrendered JS shell - the same live-verification discipline every
  other design choice in this document already follows. No source does
  this yet as of this section's own addition.
- **HTTP stays the default and the fast path.** `WebScraperSource.
  _fetch_html` always tries plain HTTP first; a browser render is only
  attempted when the response looks like a JS shell
  (`web_scraper_base.py::looks_javascript_rendered` - conservative by
  design, tuned well below the thinnest confirmed-real page in this
  registry, Colombia ICETEX's 330-character reciprocity page, so a
  legitimately thin real page is never misclassified) *and* the source
  opted in.
- **Never treated as more trustworthy than plain HTML.** Rendered
  content goes through the exact same parsing, the same "never invent a
  field" discipline, and the same mandatory human-verification gate as
  every other source - browser rendering solves a technical extraction
  problem, not the source-authenticity problem, so nothing about the
  verification workflow changes.
- **Never bypasses a real block.** If a rendered page matches a known
  bot-challenge/CAPTCHA signature (Cloudflare's interstitial, hCaptcha/
  reCAPTCHA, a generic "access denied" page), `fetch_rendered_html`
  raises immediately rather than attempting to solve or route around
  it - the exact same policy already applied to Cyprus's Azure WAF,
  Brazil's F5/Distil challenge, and Israel's active 403 block (see
  `docs/COUNTRY_PROVIDER_REGISTRY.md`).
- **Resource-bounded.** One Chromium instance is launched lazily and
  reused across fetches; each fetch gets an isolated context/page,
  always closed; a semaphore
  (`settings.browser_render_max_concurrency`, default 2) caps concurrent
  renders; navigation and selector-waiting both use bounded timeouts
  (`settings.browser_render_timeout_ms`), never a fixed `sleep()`.
- **Verified end to end**, but not yet against a real government site
  from a session in this project. `tests/test_browser_rendering.py`
  proves the actual mechanics - real Chromium launch, real JavaScript
  execution, real rendered-DOM extraction, HTTPS-only enforcement,
  challenge-page detection, and `WebScraperSource`'s fallback/graceful-
  degradation wiring - against a local, self-signed-HTTPS test server
  (127.0.0.1, never leaving the machine); it skips cleanly wherever a
  browser isn't installed, and CI (`.github/workflows/ci.yml`) installs
  one so these tests run there too. What has **not** been verified: this
  session's own outbound network path could launch and drive a real
  Chromium instance, but every external `https://` navigation attempt
  through the sandbox's own egress proxy failed at the TLS layer
  (`net::ERR_CONNECTION_RESET`, distinct from the proxy's ordinary
  cert-trust accommodations, and not reproducible with plain httpx/curl
  in the same sandbox) - a sandbox limitation, not a defect in this
  module. Before actually flipping `allow_browser_rendering = True` on
  Egypt, Indonesia, or any other JS-only candidate, a session with a
  working outbound path for browser automation still needs to
  live-verify it against the real site first, the same as every other
  source in this document.
### Beyond a single render: SPA interaction, pagination, filters, application-link discovery, verification (2026-08-29)

The bullets above describe the original single-page-render fallback. A
later pass, in response to an explicit hybrid-discovery-engine
specification, added the rest of the interaction surface a real SPA
listing page can need - still nothing any existing source uses yet (see
the same "no source opts in yet" caveat above), but now genuinely built,
tested against real Chromium, and available for the next JS-only source
that needs it:

- **`app/services/browser_interaction.py` (`BrowserInteractionEngine`)** -
  reusable click/wait-for-selector/extract-URL/capture-content primitives
  on top of a live Playwright page opened via `browser_rendering.
  interactive_session`. `wait_for_navigation_or_change` races three real
  outcomes (a new tab, a URL change including a client-side
  `history.pushState` route, or an in-page DOM change) under a bounded
  timeout - never a fixed `sleep()`. Verified against real Chromium with
  mock pages exercising all three outcomes plus the "nothing happened"
  case (`tests/test_browser_interaction.py`).
- **`app/services/pagination_engine.py`** - `paginate_by_url` (no
  browser needed - a plain async `fetch_page(url)` callable) for
  `?page=N`-style pagination, and `paginate_by_click` (built on the
  interaction engine) for a "Next" button or a "Load More" control where
  the URL never changes - the same function handles both shapes because
  it deduplicates by key rather than assuming which one a site uses.
  Bounded by `MAX_PAGES_PER_SOURCE`/`MAX_RECORDS_PER_SOURCE`
  (`app/core/config.py`), and stops the moment a page yields no new
  records, an empty page, a disabled/absent "next" control, or a fetch
  failure - never an unbounded loop. `paginate_by_url` is tested with a
  plain in-memory fake (`tests/test_pagination_engine.py`);
  `paginate_by_click` against real Chromium and a stateful local test
  server serving three linked pages (`tests/test_browser_click_pagination.py`).
- **`app/services/infinite_scroll_engine.py`** - render → extract →
  scroll → wait for real DOM growth (`page.wait_for_function`, never a
  fixed delay) → extract → compare → continue, exactly the workflow
  named in the spec. Bounded by `MAX_SCROLL_ITERATIONS`/
  `SCROLL_STAGNATION_LIMIT`/`MAX_RECORDS_PER_SOURCE`. Verified against a
  real local mock page that appends batches of items on `scroll` events
  for a bounded number of rounds then stops, proving both the collection
  and the stagnation-based stop condition (`tests/test_infinite_scroll_engine.py`).
- **`app/services/filter_engine.py`** - applies a caller-described set of
  filters (`{"degree": FilterSpec(selector, value)}`) to a rendered page,
  auto-detecting a `<select>` vs. a clickable control; a filter whose
  selector isn't present on the page is skipped, never an error.
  `iter_filter_combinations` generates a bounded cartesian product of
  caller-supplied options (capped by `max_combinations`) - it never
  sweeps every possible combination on its own, matching the spec's own
  "avoid combinatorial explosion" rule. Verified against a real mock
  page with a `<select>` whose `onchange` visibly updates the page
  (`tests/test_filter_engine.py`).
- **`app/services/application_link_discovery.py`** - finds "Apply"-style
  controls on a rendered page (matched against a broad set of apply-
  phrase patterns, not just literal button text), reads `href` directly
  where present, and for a control without one (a JS-driven button),
  clicks through the interaction engine and records where that led (new
  tab, URL change, or an in-page modal with no distinct URL). Bounded to
  at most 5 href-less clicks per page. Never fills in a form, never
  creates an account, never submits anything - discovery only. Verified
  against real Chromium mock pages covering all three discovery methods
  plus the click-count bound (`tests/test_application_link_discovery.py`).
- **`app/services/application_link_validation.py`** - independently
  fetches a discovered (or already-known) application URL and classifies
  it `VALID_OFFICIAL_APPLICATION` / `VALID_AUTHORIZED_EXTERNAL_PORTAL` /
  `INFORMATION_PAGE_ONLY` / `BROKEN` / `BLOCKED` / `UNKNOWN`, by HTTP
  status, redirect chain, final domain, and (for a 2xx) whether the page
  itself looks like an application flow. Only the source's own domain or
  an explicitly pre-authorized portal domain can ever come back
  `VALID_*` - an unrecognized-but-reachable domain comes back `UNKNOWN`
  with `needs_review=True`, never silently treated as verified. No
  browser needed - tested entirely with `respx`-mocked HTTP responses
  (`tests/test_application_link_validation.py`).
- **`app/services/content_completeness.py`** - scores a scraper
  adapter's extracted-but-not-yet-validated field mapping 0-100 across
  CRITICAL (title, provider)/IMPORTANT (application URL, deadline,
  description)/OPTIONAL tiers; `needs_review` is forced True whenever any
  CRITICAL field is missing regardless of the numeric score - the score
  alone is never sufficient, per the spec's own rule. Runs on the raw
  field mapping an adapter builds, before attempting to construct a
  `NormalizedExternalOpportunity` (whose own schema already guarantees
  title/provider are non-empty once that construction succeeds - this
  check is what decides whether that attempt is even worth making).
  Pure-Python, no browser needed (`tests/test_content_completeness.py`).
- **`app/services/source_capability_profile.py`** - in-process (not
  persisted across restarts, same design as the metrics counters below)
  memory of what's actually been observed about a domain: does it need
  JavaScript, what pagination shape did it use, does it have a cookie
  banner, and so on - recorded automatically by every module above as it
  runs, for *every* source's own domain regardless of whether that
  source has opted into browser rendering. This is deliberately
  observability, not automation: nothing reconfigures a source's own
  fetch behavior on the strength of this evidence by itself -
  `allow_browser_rendering` stays a human decision made only after the
  kind of live-testing this whole document already requires. A future
  session deciding whether to flip that flag on a candidate source can
  consult this evidence rather than re-discovering it from nothing.
- **`app/services/scraper_metrics.py`** + **`GET /api/v1/scraper-metrics`**
  (`app/api/routes/scraper_metrics.py`, staff-gated) - process-wide
  counters (HTTP/browser attempts and successes, JS-shell detections,
  pagination/infinite-scroll pages visited, application-link discovery/
  validation outcomes, cookie banners, console errors, CAPTCHA blocks,
  timeouts) plus derived ratios; an untouched ratio reads `null`, never a
  fabricated `0.0`. In-memory only, resets on process restart - this
  project's existing preference for using its own logging/counters over
  a heavyweight monitoring platform, extended here rather than replaced.
- **`app/services/browser_rendering.py`** also gained: configurable
  headless mode (`PLAYWRIGHT_HEADLESS`, forced back to `true` whenever
  `APP_ENV=production` - a headed browser needs a display no deployment
  has), generic cookie/consent-banner detection and (only within a
  detected cookie/consent container, never page-wide) auto-accept
  (`AUTO_ACCEPT_REQUIRED_COOKIES`), and structured console-error/page-
  error/failed-request/HTTP-error capture classified INFO/WARNING/ERROR/
  CRITICAL (a known third-party analytics/ad-tracker failure is
  downgraded, never used to fail an otherwise-successful render) - all
  verified against real Chromium and real mock pages
  (`tests/test_browser_rendering.py`).
- **`app/services/scraper_adapters.py`** - `GenericHTMLAdapter`/
  `GenericJSAdapter`/`GovernmentPortalAdapter`/`UniversityPortalAdapter`/
  `SPAAdapter` base classes, for a *future* source whose extraction is
  simple enough to describe declaratively (CSS selectors) rather than
  needing bespoke parsing code. None of the 43 existing sources has been
  migrated to these, and none needs to be - "prefer generic behavior
  first" per the spec, reached for only when it materially reduces
  bespoke code for a genuinely new source, never forced onto working
  code. `SPAAdapter` is deliberately left as a named interface, not a
  generic implementation - an SPA's own click/detail-open flow is
  inherently site-specific.

**Deliberately still not built**, because no current source needs it and
building it speculatively would be exactly the kind of premature
generality this codebase avoids elsewhere: reverse-engineering a site's
own internal JSON/GraphQL API (the spec's own priority order already
prefers a documented public API when one exists - none of the JS-only
candidates on record has one), and multi-language deduplication. If a
future source genuinely needs one of these, it should be designed
against that source's real, live-tested page - not built in the abstract
ahead of any real user.

**Still not independently verified in this session**, for the same
sandbox-network reason as the original single-render fallback above: none
of the new interaction/pagination/filter/discovery modules has been run
against a real external JS-only site, only against local mock pages built
specifically to exercise each code path. The mock-page tests prove the
Playwright mechanics genuinely work (real clicks, real DOM/URL changes,
real scrolling, real form-less link discovery); they can't prove any
*particular* real site's own markup matches what a concrete adapter would
need to configure. A session with a working outbound browser-automation
path still needs to live-test against Egypt/Indonesia (or any other
JS-only candidate) before a concrete adapter is written for either.

## Requirement matrix (JavaScript/SPA scraping specification)

Tracks the 2026-08-29 hybrid-discovery-engine specification's own
numbered requirements against what's actually built, in the same
COMPLETE / PARTIALLY_COMPLETE / BLOCKED_BY_ENVIRONMENT / NOT_APPLICABLE
vocabulary that spec itself asks for.

| Requirement | Status | Where |
| --- | --- | --- |
| Hybrid HTTP-first/browser-fallback architecture | COMPLETE | `web_scraper_base.py::_fetch_html` |
| Playwright as the rendering framework | COMPLETE | `browser_rendering.py` |
| Rendering decision engine | COMPLETE | `web_scraper_base.py::looks_javascript_rendered` |
| Event-driven waits, never fixed `sleep()` | COMPLETE | `browser_rendering.py`, `browser_interaction.py`, `infinite_scroll_engine.py` all use `wait_for_selector`/`wait_for_function`/`wait_for_event` |
| SPA click/detail-open navigation | COMPLETE (generic engine) | `browser_interaction.py` |
| Pagination (standard, URL, "Load More") | COMPLETE | `pagination_engine.py` |
| Infinite scroll | COMPLETE | `infinite_scroll_engine.py` |
| Dynamic UI filters | COMPLETE (generic engine) | `filter_engine.py` |
| Dynamic application-link discovery | COMPLETE | `application_link_discovery.py` |
| Application-link validation/classification | COMPLETE | `application_link_validation.py` |
| Cookie/consent-banner handling | COMPLETE | `browser_rendering.py::_maybe_accept_cookie_banner` |
| JS console/page-error monitoring | COMPLETE | `browser_rendering.py`'s `PageEvent` capture + classification |
| Content-completeness verification | COMPLETE | `content_completeness.py` |
| Source capability profiling | COMPLETE (observability only, not automation - see above) | `source_capability_profile.py` |
| Source-specific adapter architecture | COMPLETE (interface only; unused by existing sources) | `scraper_adapters.py` |
| Metrics tracking | COMPLETE | `scraper_metrics.py` |
| Metrics reporting | COMPLETE | `GET /api/v1/scraper-metrics` |
| Headless-mode configurability | COMPLETE | `PLAYWRIGHT_HEADLESS`, forced `true` in production |
| Browser resource management (reuse, concurrency limits, cleanup) | COMPLETE | `browser_rendering.py`'s shared `_browser`/semaphore/`finally: context.close()` |
| CAPTCHA/anti-bot handling - never bypass | COMPLETE | `browser_rendering.py::_looks_like_a_challenge_page` (raises, never solves) |
| API-first priority (Public API → HTTP → Playwright → manual review) | PARTIALLY_COMPLETE | HTTP-before-Playwright is real; there is no separate "check for a public API first" discovery step, because no JS-only candidate on record has ever been found to have one - would be built against a real source that needs it, not speculatively |
| GraphQL/internal-API reverse-engineering | NOT_APPLICABLE | no current source needs it; would violate this project's own scoping discipline to build without one |
| Multi-language deduplication | NOT_APPLICABLE | no current source needs it |
| Docker/Playwright production validation | BLOCKED_BY_ENVIRONMENT | this sandbox's Docker daemon is not running; the `Dockerfile`'s `playwright install --with-deps chromium` step is reviewed by inspection only, never build-tested here |
| Real JS-only source validation (Egypt, Indonesia, ...) | BLOCKED_BY_ENVIRONMENT | this sandbox's egress proxy fails at the TLS layer for real Chromium navigation to external HTTPS sites (confirmed not a cert-trust issue - plain httpx/curl work fine, only browser-driven TLS breaks); proven against local mock pages instead |
| "Hybrid Scholarship Discovery and Verification Engine" naming | COMPLETE | this document and `Task.md`/`Changelog.md` describe it that way throughout, never as "a simple web scraper" |

## Source registry data model

Each row above is a real `OpportunitySource` database record
(`app/models/external_opportunity.py`), seeded idempotently by
`app/services/source_registry.py`'s `SOURCE_DEFINITIONS` at startup/first
sync. Administrators can deactivate/reactivate a source via
`PATCH /external-opportunities/sources/{source}` (audited); adding a new
source still requires a code change to `SOURCE_DEFINITIONS` (and, for a
scraper, a new `WebScraperSource` subclass), not a UI action — a
Super-Administrator-editable source registry UI (as described in the
platform specification §5/§18) does not exist yet.

Live per-source health (last successful/failed sync, most recent error,
next scheduled run) is available to verification staff at
`GET /external-opportunities/health`.

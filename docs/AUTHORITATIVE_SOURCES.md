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
- **Official domain / base URL**: `https://www.slas.gov.sz`
  (`ESWATINI_SLAS_BASE_URL`)
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
- **LIVE SOURCE TEST: NOT PERFORMED.** `https://www.slas.gov.sz` timed out
  on every connection attempt (2026-08-22/23, both protocols) — the same
  symptom as source 12 (MTHE) above: DNS resolves but the TCP handshake
  never completes, pointing at a network-level issue rather than an
  application-level block. Implemented against the same conservative
  pattern and unit-tested against a realistic **synthetic** fixture only.
  Smoke-test against the live site before enabling its scheduled sync.

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

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
is retrieved*, never *whether a human approves it*. All twelve sources are
governed by the shared source-adapter architecture in `app/services/` —
either a thin API client (sources 1–7) or a subclass of `WebScraperSource`
(`app/services/web_scraper_base.py`, sources 8–12).

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

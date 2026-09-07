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
- **(2026-09-06 update)** Added a seventh monitored detail id,
  `10000108` — **Konrad-Adenauer-Stiftung (KAS): Scholarship Programme
  for International Students** — in response to a request for another
  fully funded Master's scholarship in Germany. This is an addition to
  this *existing* multi-record source (extending
  `Settings.daad_scholarship_detail_ids`, exactly as this adapter's own
  module docstring describes as the intended way to grow coverage), not
  a new 81st `OpportunitySource` row — the platform's total registered-
  source count is unaffected.
  - Genuinely fully funded: a monthly grant of EUR 992 for Bachelor's/
    Master's recipients (Germany's standard BAfoeG maximum living-cost
    rate) plus health- and long-term-care insurance and child/family
    allowances where applicable, at German public universities, which
    charge no tuition for a first Master's degree in 15 of Germany's 16
    federal states. Documented honestly rather than glossed over: the
    one well-known exception is Baden-Württemberg, which has charged
    non-EU students tuition (around EUR 1,500/semester) since 2017, and
    this programme's own page does not separately address that state.
  - **Country coverage / eligibility**: the live page's own
    country-eligibility dropdown (used to gate which country's
    applicants may apply) lists "Sierra Leone" by name among ~150
    countries — confirmed directly against the live site during
    research. That dropdown text falls past this shared adapter's
    5000-character description-truncation for this particular (longer
    than most) detail page, so it is not itself present in the stored
    `description`, but eligibility was still verified against the live
    page's actual HTML, not inferred from a vague label.
  - **`funding_type` implementation note**: the original six seed ids
    were never individually researched for funding completeness and
    predate this field's use elsewhere in the codebase — rather than
    retroactively guessing a classification for programmes not
    researched with that question in mind, a new
    `_FUNDING_TYPE_OVERRIDES` dict in `daad_scholarships.py` classifies
    only this specifically-researched id; the other six keep
    `funding_type = None` exactly as before, unaffected.
  - Deliberately extracts no deadline: the page states "Closing date
    for applications is 15 July (12 o'clock noon) of each year" — a
    real, recurring annual cycle with no year attached, so
    `extract_confident_date_after` correctly resolves to `None` rather
    than guessing a year, the same pattern already covered by this
    source's own `test_no_year_adjacent_deadline_text_is_left_null`
    test for a different detail id.
  - **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
    backend's actual HTTP path — 200, real server-rendered HTML from
    `www2.daad.de`. Implemented and unit-tested against a real fixture,
    captured unmodified from the live fetch
    (`tests/fixtures/daad_detail_kas.html`).

### Researched this pass (Germany fully-funded Master's follow-up), not integrated

- **Konrad-Adenauer-Stiftung's own website** (`kas.de`) — genuine
  bot-protection: `kas.de/robots.txt` itself returns a Web Application
  Firewall block page ("Your request was blocked due to security
  reasons"), not a robots.txt. Per this project's "never bypass
  CAPTCHA/bot-protection" rule, not circumvented — used the identical
  programme's DAAD-hosted mirror page instead (`www2.daad.de`, already
  an audited, unblocked source for this platform), which is not
  KAS's own site but is DAAD's own official database entry for the
  programme.
- **Friedrich-Ebert-Stiftung (FES): Scholarship for International
  Students** — a real, generous programme (base stipend EUR 992-1,500/
  month, health insurance, child allowance) with an explicit,
  checkable eligibility rule (Global South/post-Soviet/eastern-and-
  south-eastern-EU applicants, explicitly excluding OECD countries —
  Sierra Leone qualifies on both counts), but its own DAAD-hosted page
  states applicants must "already study in Germany" and have
  "enrolment at a state or state-recognised higher education
  institution in Germany" as an Academic Requirement — this is
  support for students already admitted/enrolled in Germany, not a
  scholarship a prospective Sierra Leonean applicant could use to fund
  initial admission from abroad, unlike KAS (whose own page does not
  state a prior-enrolment requirement for Master's applicants). Left
  unintegrated for this specific "another Master's scholarship"
  request rather than presented as an equivalent option.
- **RWTH Aachen** — its "High Potential Student Grant" (up to 25%
  tuition reduction) and "Global Talent Scholarship" (up to 35% tuition
  coverage, restricted to five named countries not including Sierra
  Leone) are both explicitly partial — `PARTIALLY_FUNDED`.
- **Elite Network of Bavaria — Max Weber Programme** — a real, well-
  regarded programme extending to Master's students at Bavarian
  universities, but its own materials describe a "Semester Allowance"
  of EUR 1,800/semester (not an explicit full-cost statement) and
  require German language proficiency at B2/C1 level as a precondition
  — `PARTIALLY_FUNDED`/out of scope for an English-medium applicant.
- **Constructor University (formerly Jacobs University Bremen)** — its
  current, generally-available scholarships (Academic Achievement,
  Talent) are explicitly partial tuition coverage (EUR 7,000-10,000/
  year against tuition well above that); a historical one-off "full
  tuition" scholarship reported for fall 2022 could not be confirmed as
  a current, recurring programme on the university's own site —
  `PARTIALLY_FUNDED`/`UNVERIFIED`.
- **Hertie School Berlin** — full scholarships exist but are explicitly
  tuition-only ("cannot be used for anything other than tuition"),
  with living-cost support, where available at all, coming from
  separate third-party organisations rather than the school itself —
  `TUITION_ONLY` relative to the school's own funding.

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

## 46. Rotary Peace Fellowships (Rotary International)

A second addition to the same "multiple source types per country" gap
as source #45. Genuinely open worldwide by nationality (unlike Aga Khan
Foundation's International Scholarship Programme, also researched this
pass — real and legitimate, but restricted to a named list of countries
that does not include Sierra Leone, so not integrated).

- **Organization**: The Rotary Foundation (Rotary International)
- **Route code**: `rotary-peace-fellowship` (`rotary_peace_fellowship`
  internally)
- **Official domain / base URL**: `https://www.rotary.org`
  (`ROTARY_PEACE_FELLOWSHIP_BASE_URL`)
- **Opportunity types**: Fellowship (master's degree or professional
  development certificate, peace and development studies, at one of
  eight Rotary Peace Centers worldwide)
- **Country coverage**: Not tied to a single destination country — left
  `None`, same as Wells Mountain Initiative (source #13) and World Bank
  JJ/WBGSP (source #45)
- **Discovery method**: **Web scraper, single-flagship-program pattern**
  reading `/get-involved/our-programs/peace-fellowships` (the resolved
  target of a 301 redirect from `/en/our-programs/peace-fellowships`,
  fetched directly to skip the extra hop). `robots.txt` allows
  `User-agent: *` with only narrow system-path `Disallow:` rules (none
  matching this page) and states `Crawl-delay: 10` — respected via
  `min_request_interval_seconds = 10.0`, well above this project's usual
  2-second default.
- **API / RSS / Sitemap**: None published
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices, and one honestly-recorded fragility**:
  - `title_selectors = ("h1.typography-h1",)` — unique on the page
    (exactly one match) and reads like a real, intentional design-
    system class Rotary reuses across pages.
  - `content_selectors = ("div.flex.flex-col.gap-2",)` — this page has
    **no semantic content wrapper** (no `<article>`, no `id`/descriptive
    `class` on the body-copy container), only Tailwind utility-class
    combinations. This selector matches 3 elements; `_first_match`'s
    `select_one` takes the first, which is the correct lead paragraph
    today (live-verified against the real fetched page) — but a future
    CSS/utility refactor could silently break it without the page's
    visible content changing. Recorded honestly rather than silently
    risked: if a future resync finds `description=None` for this
    source, re-inspect the live page's markup before assuming a genuine
    content change (a broken selector fails safe to `None`, never a
    crash or fabricated content).
  - `deadline_keywords` kept active rather than disabled (`()`) even
    though the page's own text at the time of writing states only a
    month+year for the next application cycle ("available online in
    February 2027", no day) — `extract_confident_date_after` correctly
    returns `None` for that today; a future cycle stating an exact date
    will be picked up automatically without another code change.
- **LIVE SOURCE TEST: PASSED 2026-08-30.** Verified via `curl` (following
  the real 301 redirect) and this backend's actual parsing path — 200,
  ~287KB real server-rendered HTML, no browser rendering needed, no
  spoofed user agent required. Implemented and unit-tested against a
  real fixture captured unmodified from the fetch
  (`tests/fixtures/rotary_peace_fellowships.html`).

---

## 47. Erasmus Mundus Joint Masters Catalogue (EACEA)

A third addition to the "multiple source types per country" gap, and
the second real production consumer of `app/services/
pagination_engine.py`'s `paginate_by_url` after EducationUSA (source
#44) — a second, independently-verified proof that engine generalizes
across genuinely different real sites rather than being tuned to one.

- **Organization**: European Education and Culture Executive Agency
  (EACEA), European Commission
- **Route code**: `erasmus-mundus-joint-masters`
  (`erasmus_mundus_joint_masters` internally)
- **Official domain / base URL**: `https://www.eacea.ec.europa.eu`
  (`ERASMUS_MUNDUS_BASE_URL`)
- **Opportunity types**: Scholarship (EU-funded joint master's degrees,
  delivered by multi-university consortiums, ~220 active programmes
  across nearly every discipline)
- **Country coverage**: Not tied to a single destination country — left
  `None`. Genuinely open to applicants "from all over the world" per the
  catalogue's own text — not restricted by nationality, so Sierra
  Leonean applicants are eligible the same as anyone else.
- **Discovery method**: **Web scraper, paginated-listing pattern**
  reading `/scholarships/erasmus-mundus-catalogue_en?page=N` (`N`
  0-indexed) — a real, plain server-rendered listing built with the EU's
  own ECL (Europa Component Library) design system
  (`article.ecl-card` per programme), no browser rendering needed.
- **robots.txt / indexing note**: the page carries `<meta
  name="robots" content="follow, noindex">` — a page-level *search-
  engine indexing* directive, not a Robots Exclusion Protocol crawl
  restriction; it says nothing about whether fetching the content is
  permitted. The site's actual `robots.txt` scopes its `Disallow:`
  rules to `User-agent: Googlebot` specifically (no general
  `User-agent: *` block) — the same "only specific-bot rules present"
  pattern already documented for Mexico's AMEXCID (source #43).
- **API / RSS / Sitemap**: None published for this specific listing
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - Each card's own title, its programme website link (used as
    `official_application_url` — genuinely where an applicant would go),
    and the EU's own project-record link (used as `official_source_url`
    — the authoritative EU record this listing came from), plus the
    card's own short description text (an acronym and "Project
    overview", exactly what's on the page).
  - No per-programme deadline is stated on this listing page — each
    consortium sets its own, and the catalogue's own text only says
    "most... require applications... between October and January," not
    a specific date for any one programme — `deadline` stays `None` for
    every record, never guessed from that generic text.
  - Does not follow the ~220 external programme links or the EU
    project-record pages for more detail — out of proportion with what
    this adapter needs, the same reasoning already documented for
    EducationUSA's own per-row "More information" links.
  - **A real, live-observed HTTPS-only enforcement worth noting**: two
    of the ~220 programmes' own listed websites (RESCO, European
    Forestry) are plain `http://`, not `https://` — correctly and
    silently dropped by the shared `absolute_https_url` check, never
    "fixed" by guessing a scheme. Confirmed directly in the real
    fixtures, not assumed - see
    `tests/test_erasmus_mundus_source.py`'s explicit assertions on this.
- **LIVE SOURCE TEST: PASSED 2026-08-30.** Verified through this
  backend's actual HTTP path (httpx) — 200, real ECL-rendered HTML, no
  spoofed user agent required, on three separate real fetches (page 0,
  page 1, and a genuinely-past-the-last-page response, `?page=15` → 0
  cards). Implemented and unit-tested against all three real fixture
  pages, captured unmodified from the httpx fetches
  (`tests/fixtures/erasmus_mundus_catalogue_*.html`).

## 48. UAEU Scholarships, Fellowships, and Graduate Assistantships (United Arab Emirates University)

Closes two gaps at once: the United Arab Emirates line item in the
40-country target list (the only prior UAE finding, government
scholarships, came back `NO_RELIABLE_SOURCE_FOUND` — predominantly
outbound for Emiratis, not inbound), and this project's first genuinely
**university**-typed source (`source_type = "university"`, a new but
valid value on the existing free-text `source_type` column — every other
web-scraped source so far is government/international-organization/
funding-organization-typed).

- **Organization**: United Arab Emirates University (UAEU), College of
  Graduate Studies
- **Route code**: `uaeu-scholarships` (`uaeu_scholarships` internally)
- **Official domain / base URL**: `https://www.uaeu.ac.ae`
  (`UAEU_BASE_URL`)
- **Opportunity types**: Scholarship (a mix of fellowships, research/
  teaching/administrative assistantships, and department-specific PhD
  studentships — 13 distinct programmes at the time of writing)
- **Country coverage**: United Arab Emirates
- **Discovery method**: **Web scraper, single-page structured-widget
  pattern** reading `/en/cgs/scholarship.shtml` — real, plain
  server-rendered HTML (200, ~169KB), no browser rendering needed. The
  page's real content lives inside a Tailwind-based accordion widget
  (`.aegov-accordion` / `.accordion-item`) that the site reuses for
  *both* page-navigation menus *and* this scholarships list — the widget
  class alone isn't a unique-enough selector (27 total accordion-items
  on the page; only 13 are real scholarship/fellowship/assistantship
  entries). Scoped correctly via `[id^="faqs-section"]`, a CSS
  attribute-prefix selector matching the CMS-generated container id's
  stable prefix (the random hash suffix after it changes on every
  republish, confirmed by inspecting the real fetched markup).
- **robots.txt / indexing note**: `User-agent: *` is allowed with only a
  handful of narrow, unrelated `Disallow:` rules (specific admin/legal
  pages) — none matching this page.
- **API / RSS / Sitemap**: None published for this specific listing
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - Extracts **every** accordion item as its own opportunity record,
    deliberately **not filtered by nationality eligibility**: several
    titles explicitly state "(All nationalities)"; others just as
    explicitly state a restriction ("UAE nationals", "UAEU Alumni only")
    directly in their own real title text — this adapter extracts that
    text verbatim rather than acting on it, matching this project's
    standing "AI's role: none, today" eligibility policy
    (`docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` §10). A human verification
    officer reads the real title/description before approving any
    record, exactly like every other scraped source in this project.
  - Each item's own "Details"/similar link (several are PDFs, not HTML
    pages) is stored as both `official_source_url` and
    `official_application_url` without being fetched itself — reading a
    programme's own PDF guidelines is out of scope for this adapter,
    matching how EducationUSA's and Erasmus Mundus's own per-row "more
    information" links also aren't followed.
  - No per-programme deadline is stated in a consistently parseable form
    across all 13 items — `deadline` stays `None` for every record,
    never guessed.
  - A real page artifact (multiple internal spaces, and a non-breaking
    space `\xa0`) inside several titles is preserved verbatim by the
    shared `clean_text` utility, never silently "fixed" beyond what that
    utility already does for every other source — confirmed directly in
    `tests/test_uaeu_scholarships_source.py`'s explicit assertion on
    this.
- **LIVE SOURCE TEST: PASSED 2026-08-30.** Verified through this
  backend's actual HTTP path (httpx) — 200, real server-rendered HTML, no
  spoofed user agent required. Implemented and unit-tested against the
  real fixture page, captured unmodified from the httpx fetch
  (`tests/fixtures/uaeu_scholarship.html`); extraction verified to yield
  exactly the 13 real programmes present on the live page at fetch time.

---

## 49. Mastercard Foundation Scholars Program

Previously listed below under "Sources evaluated and deliberately not
integrated" (researched 2026-08-30, left out because the institution
listing was a client-side widget with no server-rendered fallback and no
locatable underlying API). Re-investigated 2026-09-05 after the
foundation restructured its site — the old `/all/scholars-program/
where-to-apply/` URL now 404s — and the actual blocker turned out to be
different from what the original research found: the current listing's
data comes from a **plain static JSON asset**, not a client-rendered
widget with no fallback at all.

- **Organization**: The Mastercard Foundation
- **Route code**: `mastercard-foundation-scholars`
  (`mastercard_foundation_scholars` internally)
- **Official domain / base URL**: `https://mastercardfdn.org`
  (`MASTERCARD_FOUNDATION_BASE_URL`)
- **Opportunity types**: Scholarship — one record per partner higher-
  education institution (31 distinct institutions at fetch time)
- **Country coverage**: Global — institutions across Africa (Ethiopia,
  Ghana, Rwanda, Nigeria, South Africa, Benin, Burkina Faso, Uganda,
  Morocco, Cameroon and others via a regional AIMS network), North
  America (Canada, USA), Europe (United Kingdom, France), the Middle
  East (Lebanon), and Costa Rica
- **Discovery method**: **Web adapter reading a static JSON asset**,
  `/assets/json/institution.json` — confirmed via `curl` to be a plain
  `GET` returning the real per-institution data directly (no JavaScript
  execution needed), unlike the client-side "All Partners" directory
  widget on `/en/partners/` (a *different*, much broader endpoint
  spanning every program the foundation runs, not just this one).
- **robots.txt / indexing note**: `Allow: /` for `User-agent: *`, and
  explicitly by name for `ClaudeBot`, `GPTBot`, `OAI-SearchBot`, and
  `ChatGPT-User`.
- **API / RSS / Sitemap**: The static JSON asset itself functions as an
  unofficial but genuinely structured data source — not a documented
  public API, but not scraped HTML either
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - The JSON asset mixes English and French locale duplicates of every
    institution in one flat array (`__languageCode: "en"` vs `"fr"` —
    e.g. Cape Town appears twice, once as itself and once as its French
    rendering "Le Cap"). Filtered to `__languageCode == "en"` only,
    which yields exactly 31 unique institutions with no duplicate
    slugs — live-verified, not assumed.
  - The foundation's own program page separately advertises "62 Global
    partners" as a headline stat, but that figure spans every kind of
    partner across the foundation's many programs (implementing NGOs
    included), not just this Scholars Program institution list — 31 is
    what this adapter can actually verify and extract from the real
    data, reported as such rather than reused as a round headline
    number that doesn't match what's actually collected.
  - Every institution is extracted regardless of its current
    `application_window` ("open"/"closed"/empty) — a program with no
    live currently-open cohort is still a real, verifiable partner
    institution; the field is recorded verbatim in `description` and
    `raw_payload` rather than used to silently drop a record.
  - Deliberately does not fetch each institution's own detail page
    (`.../where-to-apply/<slug>/`) or follow through to the
    institution's own external site — out of proportion with what this
    adapter needs, the same reasoning `erasmus_mundus_source.py` and
    `educationusa_source.py` already document for not chasing their own
    per-row "more information" links. The foundation's own institution
    detail page at that URL *is* the accurate, stable "how to apply"
    record (it explicitly instructs the applicant to apply through the
    institution directly and links to its site) — used as-is for both
    `official_source_url` and `official_application_url`, matching
    source #48's (UAEU) same single-URL choice.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path (httpx) — 200, real static JSON, no browser
  rendering, no spoofed user agent required. Implemented and unit-tested
  against the real fixture, captured unmodified from the httpx fetch
  (`tests/fixtures/mastercard_foundation_institutions.json`); extraction
  verified to yield exactly the 31 real, unique English-language
  institutions present in the live data at fetch time.

---

## 50. Schwarzman Scholars

Researched 2026-09-05 in the same pass that rejected United World Colleges
(UWC) below — both are `_SingleProgramSource` candidates evaluated back to
back, one accepted and one rejected, on the same robots.txt criterion.

- **Organization**: Schwarzman Scholars (hosted at Tsinghua University,
  Beijing; founded by Stephen A. Schwarzman)
- **Route code**: `schwarzman-scholars` (`schwarzman_scholars` internally)
- **Official domain / base URL**: `https://www.schwarzmanscholars.org`
  (`SCHWARZMAN_SCHOLARS_BASE_URL`)
- **Opportunity types**: Scholarship — one fully-funded, one-year master's
  program in Global Affairs
- **Country coverage**: Global. The program's own `/admissions/` page
  states eligibility (undergraduate degree, age 18–28, English
  proficiency) with no nationality or country restriction anywhere; it
  runs a *separate* application track for applicants with Chinese
  citizenship alongside the "U.S. and Global Applicants" track, which is
  not a restriction on the latter — recorded with `country = "China"`
  here only because that is the program's *host* country (where the
  degree is conferred and study takes place), not a claim about who is
  eligible to apply.
- **Discovery method**: Web scraper (plain HTTPS GET, WordPress-rendered
  HTML, no JavaScript execution needed) reading `/admissions/`
- **robots.txt / indexing note**: No `Disallow` at all for
  `User-agent: *` (`Crawl-delay: 10`, respected via
  `min_request_interval_seconds = 10.0`) and no separate rule naming
  `ClaudeBot` — confirmed by direct fetch 2026-09-05.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `title_selectors = ()`: the page's only `<h1>` is a marketing
    tagline ("Join the world's next generation of leaders."), not a
    usable title, and the `<title>` tag ("Admissions - Schwarzman
    Scholars") is too generic to split usefully either — falls through
    to the `external_id`-derived fallback ("Schwarzman Scholars"), the
    same documented pattern already used by `wmi_scholars` and others.
  - `deadline_keywords = ("countdown",)`, not the default `"deadline"`:
    the page states the same date twice — first in full-month-name form
    ("Countdown to September 9, 2026 Application Deadline") and again a
    few lines later in an abbreviated, unparseable form ("Application
    Deadline: Sept 9, 2026"). `extract_confident_date_after` finds the
    *first* occurrence of its keyword and only searches forward from
    there, so anchoring on "deadline" itself lands after the
    full-month-name date has already passed and finds only the
    abbreviated one (which the parser's date pattern doesn't match,
    since it requires a full month name). "countdown" appears earlier
    in the text, and the extracted date (2026-09-09) was independently
    cross-checked against the page's own JS countdown-timer
    `data-date="1788980400000"` millisecond-epoch attribute
    (= 2026-09-09 19:00:00 UTC) — not a coincidental regex match.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path (httpx) — 200, real WordPress HTML, no
  browser rendering, no spoofed user agent required. Implemented and
  unit-tested against the real fixture, captured unmodified from the
  httpx fetch (`tests/fixtures/schwarzman_scholars_admissions.html`).

---

## 51. Knight-Hennessy Scholars

Researched 2026-09-05, the same session as Schwarzman Scholars — another
fully-funded, university-hosted graduate program with genuinely global,
no-nationality-restriction eligibility.

- **Organization**: Knight-Hennessy Scholars, Stanford University
- **Route code**: `knight-hennessy-scholars` (`knight_hennessy_scholars`
  internally)
- **Official domain / base URL**: `https://knight-hennessy.stanford.edu`
  (`KNIGHT_HENNESSY_SCHOLARS_BASE_URL`)
- **Opportunity types**: Scholarship — a fully-endowed, multidisciplinary
  leadership program funding up to three years of graduate study at any
  of Stanford's seven schools
- **Country coverage**: Global. The program's own `/admission/before-
  you-apply/eligibility` page states: "Knight-Hennessy Scholars has no
  restrictions based on age, college or university, field of study, or
  career aspiration. We encourage citizens and residents of all
  countries to apply." `country = "United States"` is recorded only as
  the program's *host* country (where Stanford is), not a claim about
  who is eligible to apply — the same host-vs-eligibility distinction
  already documented for Schwarzman Scholars (#50).
- **Discovery method**: Web scraper (plain HTTPS GET, server-rendered
  HTML, no JavaScript execution needed) — homepage for title/
  description, a dedicated deadlines page for the application deadline
- **robots.txt / indexing note**: `Allow: /` for `User-agent: *`
  (`Crawl-delay: 30`, respected via `min_request_interval_seconds`
  below) beyond a few asset/admin directories unrelated to this
  adapter; only `FemtosearchBot` and `SemrushBot` are disallowed by
  name, not `ClaudeBot` — confirmed by direct fetch 2026-09-05.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `deadline_keywords = ("deadline is",)`, not the default `"deadline"`:
    `extract_confident_date_after` only scans 300 characters past the
    *first* occurrence of its keyword on the whole page (not just the
    `<main>` content), and this site's own navigation contains an
    earlier, unrelated "Application Deadlines" menu link roughly 1,000
    characters before the real sentence ("The Knight-Hennessy Scholars
    application deadline is October 6, 2026...") — anchoring on the
    default "deadline" keyword lands on that nav link and finds nothing
    within its window. "deadline is" occurs exactly once on the page,
    immediately before the real date — verified directly against the
    live fixture.
  - The deadlines page also states a *separate*, later "December 1,
    2026" fallback deadline for the Stanford graduate-degree-program
    application itself (distinct from the Knight-Hennessy Scholars
    application deadline). This adapter deliberately extracts only the
    first, KHS-specific deadline (October 6, 2026) — the one that
    actually gates eligibility for the fellowship this record
    represents, not the graduate program's separate deadline.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path (httpx) — 200 on both the homepage and the
  deadlines page, real server-rendered HTML, no browser rendering, no
  spoofed user agent required. Implemented and unit-tested against real
  fixtures, captured unmodified from the httpx fetch
  (`tests/fixtures/knight_hennessy_scholars_home.html` and
  `tests/fixtures/knight_hennessy_scholars_deadlines.html`).

---

## 52. Yenching Academy of Peking University

Researched 2026-09-05, the same session as Schwarzman and Knight-Hennessy
Scholars — a third fully-funded, university-hosted graduate program with
genuinely global, no-nationality-restriction eligibility.

- **Organization**: Yenching Academy, Peking University
- **Route code**: `yenching-academy-scholars` (`yenching_academy_scholars`
  internally)
- **Official domain / base URL**: `https://yenchingacademy.pku.edu.cn`
  (`YENCHING_ACADEMY_BASE_URL`)
- **Opportunity types**: Scholarship — a fully-funded interdisciplinary
  master's program in China Studies
- **Country coverage**: Global. The admissions page states international
  students comprise roughly 75% of the ~120-student annual cohort, and
  its "For International Candidates" eligibility text requires only
  "non-Chinese citizens with a valid passport" — no country-of-origin
  list anywhere. `country = "China"` is recorded only as the program's
  *host* country, the same host-vs-eligibility distinction already
  documented for Schwarzman (#50) and Knight-Hennessy (#51) Scholars.
- **Discovery method**: Web scraper (plain HTTPS GET, server-rendered
  HTML, no JavaScript execution needed) — a single admissions page
  (`/ADMISSIONS.htm`) carries eligibility, funding, and the deadline
  together
- **robots.txt / indexing note**: Returns a genuine HTTP 404 (the site's
  own generic "page not found, redirecting home" error page, not a
  bot-challenge or block page) — no robots.txt file exists at all. Per
  RFC 9309, a 4xx response to the robots.txt fetch itself means "no
  rules apply" (unlike a 5xx response, treated as a temporary full
  disallow) — confirmed by direct fetch 2026-09-05 and treated as
  unrestricted, the same as an explicit `Allow: /`.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - `title_selectors = ()`: no `<h1>` exists anywhere on the page, and
    its `<title>` tag ("ADMISSIONS-Yenching Academy of Peking
    University") splits into a useless first segment ("ADMISSIONS") on
    any reasonable separator — falls through to the `external_id`-
    derived fallback ("Yenching Academy Scholars").
  - `content_selectors = ("body",)`: no `<main>`/`<article>` wrapper
    exists, and the one content-specific CSS class found
    (`.layui-container`) matches multiple nested, mostly-empty elements
    rather than one content block — `body` was verified directly to
    place real eligibility/fellowship text within the first ~2KB, well
    inside the 5000-character description cap.
  - **Deliberately extracts no deadline**, even though the page
    literally states "Application deadline: November 30, 2026" twice:
    the source HTML fragments that date across separate `<span>` tags
    (evidently pasted from a word processor), which — once the shared
    HTML-to-text extraction joins each fragment — produces "November
    30 , 2026" with a stray space before the comma that the shared
    confident-date regex (`app/services/parsing.py`) correctly declines
    to match. Verified directly: `extract_confident_date` on that exact
    literal string returns `None`. Patching the shared date-extraction
    regex to tolerate this one page's malformed markup was judged out
    of proportion and risky for the 50+ other sources depending on it —
    a missing deadline here is safe (a human confirms the real date), a
    hand-rolled workaround that starts silently matching different
    malformed input elsewhere would not be.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path (httpx) — 200, real server-rendered HTML,
  no browser rendering, no spoofed user agent required. Implemented and
  unit-tested against the real fixture, captured unmodified from the
  httpx fetch (`tests/fixtures/yenching_academy_admissions.html`).

---

## 53. ETH Zurich Excellence Scholarship & Opportunity Programme (ESOP)

Researched 2026-09-05, the same session as Schwarzman, Knight-Hennessy,
and Yenching — a fourth fully-funded, university-hosted graduate program
whose eligibility page never mentions nationality at all.

- **Organization**: ETH Zurich (Swiss Federal Institute of Technology)
- **Route code**: `eth-zurich-excellence-scholarship` (`eth_zurich_esop`
  internally)
- **Official domain / base URL**: `https://ethz.ch`
  (`ETH_ZURICH_ESOP_BASE_URL`)
- **Opportunity types**: Scholarship — a fully-funded Master's
  scholarship (tuition fee waiver plus CHF 12,000–13,500 per semester
  living/study expenses), applied for concurrently with the Master's
  admission application itself, the same pattern as Knight-Hennessy
  Scholars (#51)
- **Country coverage**: Global. The eligibility page never mentions
  nationality, citizenship, or country of origin anywhere — verified
  directly, not assumed — only a "very good result" (top 10%) in a
  prior Bachelor's degree. `country = "Switzerland"` is recorded only
  as the program's *host* country, the same host-vs-eligibility
  distinction already documented for the three sources above.
- **Discovery method**: Web scraper (plain HTTPS GET, server-rendered
  HTML, no JavaScript execution needed) — a single scholarship page
  carries eligibility, funding, and the application window together
- **robots.txt / indexing note**: Returns a genuine HTTP 404 (the
  site's own generic German-language "Seite nicht gefunden" error page,
  not a bot-challenge or block page) — no robots.txt file exists at
  all. Per RFC 9309, treated as unrestricted, the same reasoning
  already documented for Yenching Academy (#52).
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Deliberately extracts no deadline**: the page states its one
    application-window date range only in abbreviated-month form
    ("Nov, 1 - Nov, 30 2026"), never in the full-month-name form the
    shared confident-date regex (`app/services/parsing.py`) requires —
    verified directly with `extract_confident_date`, which returns
    `None` for the page's exact real text regardless of which keyword
    is anchored on. A missing deadline is safe here (a human confirms
    the real one); this project does not special-case its shared date
    regex to parse abbreviated months for one source.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path (httpx) — 200, real server-rendered HTML,
  no browser rendering, no spoofed user agent required. Implemented and
  unit-tested against the real fixture, captured unmodified from the
  httpx fetch (`tests/fixtures/eth_zurich_esop.html`).

## 54. Hong Kong PhD Fellowship Scheme (HKPFS)

Researched 2026-09-05, an "opportunity expansion" pass explicitly
targeting genuinely new government/university flagship programmes not
already covered by this platform's existing 54 sources (cross-checked
against this file and `docs/COUNTRY_PROVIDER_REGISTRY.md` first — DAAD,
Chevening, Commonwealth, MEXT, GKS, Swiss ESKAS, Swedish Institute,
Campus France, Australia Awards, Erasmus Mundus, Belgium ARES, and the
other national/university flagships requested were all already
implemented).

- **Organization**: Research Grants Council (RGC) of Hong Kong,
  established 2009; funds PhD study at eight participating Hong Kong
  universities
- **Route code**: `hong-kong-phd-fellowship-scheme` (`hkpfs` internally)
- **Official domain / base URL**: `https://cerg1.ugc.edu.hk`
  (`HKPFS_BASE_URL`)
- **Opportunity types**: Scholarship — a PhD fellowship providing an
  annual stipend of HK$344,400 (~US$44,150) plus a HK$14,400 (~US$1,840)
  conference/research-travel allowance per year, for up to three years;
  around 400 fellowships awarded per academic year. The page does not
  state whether tuition is separately covered — not extracted, not
  invented.
- **Country coverage**: Global. The eligibility text states candidates
  qualify "irrespective of their country of origin, prior work experience
  and ethnic background" — verified directly against the live page, not
  assumed.
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML — an old-style HTML-table layout with no JavaScript
  needed) across two pages: `/hkpfs/index.html` (overview/eligibility)
  and `/hkpfs/apply.html` (application procedure/deadline)
- **robots.txt / indexing note**: Returns a genuine HTTP 404 (the site's
  own "Not found - GRF/PPR/HKPFS" error page, not a bot-challenge page)
  — no robots.txt file exists at all. Per RFC 9309, treated as
  unrestricted, the same reasoning already documented for Yenching
  Academy (#52) and ETH Zurich (#53).
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Deadline keyword choice**: `apply.html` repeats "Application
    Deadline: 1 December 2026" once per participating university (eight
    rows), plus one stale, seemingly-never-updated "Application
    Deadline: 1 December 2015" row for a ninth section — rather than
    anchor on any of those repeated/inconsistent per-university rows,
    the adapter anchors on the RGC's own single unambiguous sentence
    ("...to obtain an HKPFS Reference Number by 1 December 2026 at Hong
    Kong Time 12:00:00...") — the deadline that actually gates
    eligibility for the whole scheme, verified directly against the live
    fixture to occur exactly once on the page.
  - **Current cycle, verified directly, not inferred from a prior year**:
    as of 2026-09-05, the 2027/28 round opened 1 September 2026 (noon
    HKT) with an initial-application deadline of 1 December 2026 (noon
    HKT) — confirmed both in `apply.html`'s body text and its `news.html`
    announcement page, and cross-checked against the HTML source
    directly (not just an AI summary of it) before being written into
    the adapter.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML from both
  pages, no browser rendering needed. Implemented and unit-tested against
  real fixtures, captured unmodified from the live fetch
  (`tests/fixtures/hkpfs_index.html`, `tests/fixtures/hkpfs_apply.html`).

## 55. TaiwanICDF International Higher Education Scholarship Program

Researched 2026-09-05, a follow-up "find another one" pass immediately
after HKPFS (#54) in the same opportunity-expansion effort.

- **Organization**: Taiwan International Cooperation and Development
  Fund (TaiwanICDF), operating since 1998
- **Route code**: `taiwan-icdf-scholarship` (`taiwan_icdf_scholarship`
  internally)
- **Official domain / base URL**: `https://www.icdf.org.tw`
  (`TAIWAN_ICDF_BASE_URL`)
- **Opportunity types**: Scholarship — full scholarships (the page
  states "offers full scholarships to outstanding students from partner
  countries") to pursue higher education at TaiwanICDF's partner
  universities in Taiwan
- **Country coverage**: Restricted to Taiwan's diplomatic/partner
  countries (the page says "students from partner countries" without
  itemizing them on this page — the full list lives only in a
  downloadable PDF guidebook, which this project's adapters don't parse,
  consistent with the same choice already made for Malaysia in
  `docs/COUNTRY_PROVIDER_REGISTRY.md`). `country = "Taiwan"` records the
  program's host location, the same host-vs-eligibility distinction used
  for Schwarzman/Knight-Hennessy/Yenching/ETH Zurich above — the
  restriction itself is preserved in the free-text description rather
  than invented into a structured field this schema doesn't have.
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML, no JavaScript execution needed) — a single program page
  carries the description and current-cycle announcement together. The
  "Eligibility" and "Apply Now" URLs surfaced by web search both
  redirect to a dead `xItem` on the live site (the CMS has since
  reassigned those content IDs) — recorded here rather than guessed at;
  only the one confirmed-working overview page is used.
- **robots.txt / indexing note**: Returns a genuine HTTP 404 (nginx's
  own generic error page, not a bot-challenge page), confirmed
  consistently across three separate fetch attempts — no robots.txt
  file exists at all. Per RFC 9309, treated as unrestricted, the same
  reasoning already documented for Yenching Academy (#52), ETH Zurich
  (#53), and HKPFS (#54).
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Title selector**: the page's real `<h1>` is only the site-wide
    logo link (the same "site-builder page with a useless h1" pattern
    already documented for WMI/Yenching above) — `h2.title` correctly
    matches the first of three same-classed headings on the page, which
    is the real program title.
  - **Deadline keyword choice**: the page's current-cycle banner reads
    "The 2027 TaiwanICDF Scholarship applications open from December 1,
    2026 to March 15, 2027!" — anchoring on the default "deadline"
    keyword finds nothing (that word never appears on the page), and
    anchoring on "applications open" would find the *opening* date
    (December 1, 2026) first, since it appears earlier in the same
    sentence. The adapter anchors on "to march" instead, so the
    300-character search window starts immediately after "to ",
    correctly extracting the real deadline (March 15, 2027) rather than
    the opening date — verified directly against the live fixture. A
    future cycle phrased differently would correctly yield no deadline
    rather than risk extracting the wrong one.
  - **Current cycle, verified directly, not inferred from a prior
    year**: as of 2026-09-05, the *next* (2027) cycle is officially
    announced but not yet open — applications run 1 December 2026
    through 15 March 2027. The *2026* cycle (deadline 15 March 2026) had
    already closed by the research date; this adapter does not fabricate
    an "open now" status by reusing that closed cycle's dates, and does
    not guess the 2027 dates from the 2026 ones — both were read
    directly off the live page's own current announcement.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML, no
  browser rendering needed. Implemented and unit-tested against a real
  fixture, captured unmodified from the live fetch
  (`tests/fixtures/taiwan_icdf_scholarship.html`).

## 56. Humboldt Research Fellowship (Alexander von Humboldt Foundation)

Researched 2026-09-05, a "source diversity" pass explicitly targeting
categories underrepresented in the registry (at the time: 40 government
sources against 5 university, 2 funding organization, 1 foundation, 1
embassy, 0 research institution).

- **Organization**: Alexander von Humboldt Foundation (a **Foundation**,
  not a government body — Germany's DAAD, already source #10, is the
  government-run scholarship agency; the Humboldt Foundation is legally
  and organizationally independent)
- **Route code**: `humboldt-research-fellowship`
  (`humboldt_research_fellowship` internally)
- **Official domain / base URL**: `https://www.humboldt-foundation.de`
  (`HUMBOLDT_FOUNDATION_BASE_URL`)
- **Opportunity types**: Fellowship (postdoctoral) — 6-24 months of
  research in Germany, with "further financial support, including
  family benefits for children and partners, subsidies for private full
  health insurance and allowances for travel expenses"
- **Country coverage**: Global. The page states plainly: "The Humboldt
  Research Fellowship for researchers of all nationalities and research
  areas" — verified directly, not assumed.
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML, no JavaScript execution needed)
- **robots.txt / indexing note**: `Allow: /` for `User-agent: *`, with
  only TYPO3-internal (`/typo3conf/`, `/typo3/`) and print-view paths
  disallowed — none of which cover this program page
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **No single annual deadline, and deliberately no fabricated one**:
    unlike every other source in this file, this program runs three
    calls per year (15 March / 15 July / 15 November), each closing once
    a fixed application cap (currently 800) is reached rather than on a
    calendar date. The live page states, in real time: "We have received
    the maximum number of applications for the current call... The next
    call will open on November 15, 2026." That is an *opening* date, not
    a deadline — extracting it into this schema's `deadline` field would
    mislabel it, so this adapter's `deadline_keywords` stay at the base
    class default ("deadline", "closing date"), verified directly to
    match nothing on this page and correctly leave `deadline` `None`.
    The real, current status text is still preserved in the scraped
    description for a human reviewer.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML. Implemented
  and unit-tested against a real fixture, captured unmodified from the
  live fetch (`tests/fixtures/humboldt_research_fellowship.html`).

## 57. Max Planck Schools

Researched 2026-09-05, the same source-diversity pass as Humboldt (#56)
— this platform's first **Research Institution**-classified source (a
category that had zero entries before this pass).

- **Organization**: Max Planck Schools — a joint doctoral program of 30
  German universities and 33 non-university research organizations
  (distinct from an individual Max Planck Institute)
- **Route code**: `max-planck-schools` (`max_planck_schools` internally)
- **Official domain / base URL**: `https://www.maxplanckschools.org`
  (`MAX_PLANCK_SCHOOLS_BASE_URL`)
- **Opportunity types**: PhD position — full funding for up to five
  years, no tuition fees, across four interdisciplinary fields
  (Biomedical AI, Cognition, Matter to Life, Photonics); open to both
  Bachelor's graduates (integrated MSc/PhD track) and Master's graduates
  (standalone PhD track)
- **Country coverage**: Global. The page states: "The Max Planck Schools
  invite highly ambitious and promising candidates from around the world
  to apply."
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML, no JavaScript execution needed)
- **robots.txt / indexing note**: No `Disallow` rules at all for
  `User-agent: *` (only a `Sitemap:` directive) — fully unrestricted
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Why this and not the general Max Planck Institute PhD route**:
    the general route's own official page (`mpg.de/doctoral_students`)
    states plainly "There is no central application procedure. Doctoral
    positions for individual doctorates are advertised all year round"
    by each of roughly 80 independent institutes — verified directly,
    the same decentralized, no-individually-applicable-portal pattern
    already found `NOT_SUITABLE` for Canada/Denmark/Singapore in
    `docs/COUNTRY_PROVIDER_REGISTRY.md`. The Max Planck Schools are the
    one part of the ecosystem that *does* run a single, centrally-
    applied-to program with a real recurring deadline, so this is the
    program actually integrated.
  - **Title selector**: the page's real `<h1>` is a page-specific
    call-to-action ("APPLY NOW - until DECEMBER 1"), not a stable
    program name — `title_selectors = ()` falls through to the
    external_id-derived fallback ("Max Planck Schools"), the same
    pattern already used for WMI/Yenching/HKPFS above.
  - **Deliberately extracts no deadline**: the page states the annual
    application window only as "September 1 to December 1 of the
    preceding year" — a real, recurring cycle, but never paired with a
    specific year anywhere on the page (unlike HKPFS or TaiwanICDF above)
    — verified directly that no year-qualified date literal exists for
    `extract_confident_date` to match. This adapter does not guess which
    calendar year "the preceding year" refers to.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch (`tests/fixtures/max_planck_schools.html`).

### Researched this pass (source diversity), not integrated

- **University of Melbourne Graduate Research Scholarships** — a real,
  currently-open scholarship (deadline 31 October 2026, confirmed via
  secondary sources), but `scholarships.unimelb.edu.au` returned a
  genuine HTTP 403 on every fetch attempt (including its own
  `robots.txt`), consistent with an active bot-protection layer rather
  than a page-specific block. Recorded for manual verification rather
  than circumvented, per this project's standing anti-bot-evasion rule.
- **UNSW Scientia PhD Scholarship Scheme** — the official page
  (`scientia.unsw.edu.au`) states plainly "UNSW is not currently
  recruiting candidates for this Scheme," with no next-cycle date
  announced — not integrated per the "never mark Open/Upcoming without
  source confirmation" rule. UNSW's general `unsw.edu.au/scholarships`
  page is real and fetchable (200, real robots.txt with no relevant
  disallow), but is a filterable, paginated scholarship database rather
  than a single flagship page — architecturally closer to this
  platform's `ExternalOpportunity` multi-record sources than the
  single-record `_SingleProgramSource` pattern, and out of scope for
  this pass.
- **Wellcome Trust** (International Masters Fellowships in Public
  Health and Tropical Medicine) — a real, well-known funding
  organization, but `wellcome.org` returned HTTP 202 with an empty body
  on every fetch attempt (including `robots.txt`), consistent with an
  async bot-challenge rather than a normal page response. Recorded for
  manual verification rather than circumvented.
- **AAUW (American Association of University Women) International
  Fellowships** — a real, well-known funding organization for women
  pursuing graduate study outside their home country, but
  `aauw.org` returned a genuine HTTP 403 on the fellowships page
  (`robots.txt` itself is fetchable and imposes no relevant
  restriction). Recorded for manual verification rather than
  circumvented.

## 58. TU Delft — Justus & Louise van Effen Excellence Scholarships

Researched 2026-09-05, a dedicated Germany + Netherlands university
expansion pass — this platform's 6th university-classified source (5
existed before this pass: UAEU, Schwarzman, Knight-Hennessy, Yenching,
ETH Zurich, none of which were in Germany or the Netherlands).

- **Organization**: Delft University of Technology (TU Delft), financed
  by the legacy of Justus and Louise van Effen — a genuinely
  university-administered award, distinct from the Dutch government's
  NL Scholarship
- **Route code**: `tudelft-van-effen-excellence-scholarship`
  (`tudelft_van_effen_scholarship` internally)
- **Official domain / base URL**: `https://www.tudelft.nl`
  (`TUDELFT_VAN_EFFEN_BASE_URL`)
- **Opportunity types**: Scholarship — "Full tuition fees per year for a
  TU Delft MSc programme ... AND contribution for the living expenses,"
  genuinely fully-funded (2 scholarships per faculty)
- **Country coverage**: Open to "excellent international applicant(s)"
  (conditionally) admitted to a 2-year TU Delft MSc programme —
  explicitly **not** open to TU Delft's own bachelor's graduates or to
  internationals who completed their bachelor's at a Dutch university,
  so this is narrower than "any international student," verified
  directly from the page's own exclusion list rather than assumed
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML, no JavaScript execution needed)
- **robots.txt / indexing note**: `Allow: /` for `User-agent: *`, with
  only TYPO3-internal and query-parameter paths disallowed — none of
  which cover this program page
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Current cycle verified directly**: the live page states
    "Application deadline 1 December 2026 (23:59 CET)" for the 2027/28
    admission round — a genuinely future deadline as of the 2026-09-05
    research date, not a stale prior-year figure (secondary sources
    found during discovery cited a since-superseded "December 1, 2025"
    date for the previous cycle).
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/tudelft_van_effen_scholarship.html`).

## 59. TUM — Scholarship for International Students

Researched 2026-09-05, the same Germany + Netherlands expansion pass as
TU Delft (#58) — this platform's 7th university-classified source and
its first in Germany.

- **Organization**: Technical University of Munich (TUM). Funded
  through Bavarian state government budget resources, but administered
  directly by TUM (the application, selection, and payout are all
  TUM's own) — `source_type = university`, not `government`, per the
  "classify by who actually administers it" rule.
- **Route code**: `tum-international-student-scholarship`
  (`tum_international_student_scholarship` internally)
- **Official domain / base URL**: `https://www.tum.de`
  (`TUM_INTERNATIONAL_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Grant — a one-time, need-based top-up of
  EUR 500–1,800 per semester (reapplied each semester, max 36 months of
  total funding), correctly recorded as `funding_type = "partial_
  funding"`, never `"fully_funded"`
- **Country coverage / eligibility**: **Not** for incoming or
  prospective applicants — the page's own eligibility text requires the
  candidate to already be enrolled at TUM (2nd semester of a Master's,
  or 1st if the Bachelor's was also at TUM) and ineligible for BAföG
  "due to their nationality." This is a need-based retention grant for
  currently-enrolled international students, verified directly rather
  than assumed from "TUM has international students."
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML, no JavaScript execution needed)
- **robots.txt / indexing note**: Only disallows `/typo3/` and a
  pagination pattern (`/*/1000`), neither of which covers this page
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Deliberately extracts no deadline**: the live page states the
    current "Application period winter semester 2026/27" as "1st
    October – 15th October 2026" (ordinal-suffixed days, e.g. "1st",
    "15th") and, separately, a recurring "Deadline: 15 November / 15
    May" for supporting-document submission with no year attached to
    either date. Verified directly that `extract_confident_date`
    matches neither: the ordinal suffix breaks the shared date-literal
    pattern's `\d{1,2}\s+` requirement (no digit-then-space before the
    month), and the November/May reference never carries a year at all.
    Both are exactly the kinds of ambiguous date text this codebase's
    shared regex is designed to decline rather than guess.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/tum_international_student_scholarship.html`).

### Researched this pass (Germany + Netherlands), not integrated

- **TU Delft general Excellence Scholarships hub, RWTH Aachen
  scholarships page, University of Freiburg Deutschlandstipendium
  page** — all three had their expected URLs (found via secondary-
  source citation) return HTTP 404 on the live site: university CMS
  content IDs had moved since those citations were written. Only TU
  Delft's Van Effen page (found via a follow-up search of the live
  site's own current link structure, not the stale cached URL) was
  successfully re-located and verified; the others were not chased
  further within this pass's effort budget.
- **Heidelberg University — Germany Scholarship (Deutschlandstipendium)**
  — real and confirmed genuinely current ("The application portal is
  closed. Feedback on the outcome of your application is expected to be
  sent in November," with the underlying application window "1 August –
  31 August 2026" found on its "How can I apply?" subpage), but that
  subpage renders its actual content as an embedded JSON payload inside
  a client-rendered app shell rather than semantic server-rendered HTML
  — `BeautifulSoup.get_text()` against it would return unreadable
  fragments, not real prose. Building JSON-payload extraction for one
  page was judged out of proportion for this pass; recorded for future
  work rather than forced into the existing selector-based pattern.
- **TU Delft general "scholarships.tudelft.nl" listing, TUM
  Deutschlandstipendium listing** — both are real, multi-record,
  filterable scholarship databases rather than single flagship pages,
  the same architectural mismatch already documented for UNSW's general
  scholarships page above — out of scope for this pass's
  `_SingleProgramSource` pattern.

## 60. Imperial Inspires scholarships (Imperial College London)

Researched 2026-09-05, a dedicated England university expansion pass —
this platform's 8th university-classified source and its first in
England.

- **Organization**: Imperial College London
- **Route code**: `imperial-inspires-scholarships`
  (`imperial_inspires_scholarship` internally)
- **Official domain / base URL**: `https://www.imperial.ac.uk`
  (`IMPERIAL_INSPIRES_BASE_URL`)
- **Opportunity types**: Scholarship — "at least 300 scholarships worth
  £15,000 per year" for 2027 entry, across undergraduate and selected
  postgraduate taught courses in Engineering, Natural Sciences,
  Medicine, and Imperial Business School
- **Country coverage / eligibility**: International students eligible
  to pay the "Overseas" rate of tuition. Explicitly a **partial**
  scholarship — the page itself states "you will be responsible for
  covering any remaining tuition fees and living costs not covered by
  the award" — `funding_type = "partial_funding"`, never
  `"fully_funded"`.
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML, no JavaScript execution needed)
- **robots.txt / indexing note**: Does not disallow this content path
  (only unrelated Imperial Business School CMS/admin paths are
  disallowed)
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Deliberately extracts no deadline**: applications open "in
    September 2026" and undergraduate scholarships are "awarded by
    mid-April 2027" — both stated only as a month (or month + "mid-"),
    never a specific calendar date, verified directly to not match the
    shared confident-date pattern.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/imperial_inspires_scholarships.html`).

## 61. Vice-Chancellor's International Scholarships (Newcastle University)

Researched 2026-09-05, the same England expansion pass as Imperial
Inspires (#60) — this platform's 9th university-classified source.

- **Organization**: Newcastle University
- **Route code**: `newcastle-vc-international-scholarship`
  (`newcastle_vc_international_scholarship` internally)
- **Official domain / base URL**: `https://www.ncl.ac.uk`
  (`NEWCASTLE_VCIS_BASE_URL`)
- **Opportunity types**: Scholarship — a partial (GBP 7,000/year)
  tuition fee award for undergraduate applicants starting the 2027/28
  academic year, `funding_type = "partial_funding"`
- **Country coverage / eligibility**: Restricted to applicants domiciled
  in a specific, explicitly-published list — verified directly from the
  live page, not assumed from "international students eligible":
  Algeria, Bahrain, Bangladesh, Brazil, Canada, Colombia, Egypt, Ghana,
  Hong Kong, India, Indonesia, Japan, Jordan, Kenya, Malaysia, Mexico,
  Morocco, Myanmar, Nepal, Nigeria, Norway, Pakistan, Peru, Singapore,
  South Africa, South Korea, Sri Lanka, Switzerland, Taiwan, Thailand,
  Turkey, UAE, Ukraine, USA, Vietnam, Zimbabwe, and all EU member
  states. **Sierra Leone is not on this list** — checked explicitly per
  this platform's standing "never assume African eligibility, verify
  the actual list" rule; the description scraped for this record
  preserves the full list so this is auditable from the stored data
  itself, not just this document.
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML, no JavaScript execution needed)
- **robots.txt / indexing note**: Only disallows a set of specific,
  unrelated old PDF filenames — not this HTML page
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Title selector robustness**: the page's raw HTML contains a
    *second*, stale `<h1>` wrapped inside an HTML comment — verified
    directly that BeautifulSoup's tag parser only surfaces the real,
    current one ("Vice-Chancellor's International Scholarships
    (Undergraduate) (2027)"), confirming the commented-out duplicate
    poses no risk of being picked up by `title_selectors = ("h1",)`.
  - **Admission vs funding, recorded accurately**: the page states
    eligible candidates are "automatically considered ... as part of
    their academic course application" — no separate scholarship
    application exists, preserved as-is in the scraped description
    rather than a fabricated "apply here" step.
  - **Deliberately extracts no deadline**: the page states "Awards will
    be allocated throughout the academic year before the start of the
    student's degree" (no fixed date) and separately references a UCAS
    "Equal Consideration Deadline of 13th January 2027" and later dates
    — all written with ordinal suffixes ("13th", "31st", "3rd") that
    break the shared date-literal pattern's day-then-space requirement,
    verified directly that none match. This also correctly avoids
    conflating the *UCAS course-application* deadline with a distinct
    *scholarship* deadline that doesn't actually exist here.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/newcastle_vc_international_scholarship.html`).

## 62. International Postgraduate Scholarship 2027 (University of Sheffield)

Researched 2026-09-05, a follow-up "add another England postgraduate
scholarship" pass after Imperial Inspires (#60) and Newcastle's VCIS
(#61) — this platform's 10th university-classified source and its first
England source specifically for postgraduate applicants (both prior
England sources are primarily undergraduate).

- **Organization**: University of Sheffield
- **Route code**: `sheffield-international-postgraduate-scholarship-2027`
  (`sheffield_pg_scholarship` internally)
- **Official domain / base URL**: `https://sheffield.ac.uk`
  (`SHEFFIELD_PG_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — a partial GBP 7,000 tuition fee
  reduction for taught postgraduate offer-holders starting September
  2027, `funding_type = "partial_funding"`
- **Country coverage / eligibility**: Restricted to permanent residents
  of, or those who have lived for the last three years in, a specific
  published list — verified directly from the live page: India,
  Indonesia, Japan, Kenya, Nigeria, South Korea, Taiwan, Thailand,
  Türkiye, and Vietnam. **Sierra Leone is not on this list** (Kenya and
  Nigeria are the only African countries included) — checked explicitly
  per this platform's standing Sierra-Leone-eligibility discipline, same
  as Newcastle's VCIS (#61). Awarded "automatically to eligible offer
  holders, with no additional application required."
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML, no JavaScript execution needed). Note: the university
  publishes a *separate*, China-specific variant of this scholarship
  (`international-postgraduate-scholarship-china`) at a different URL —
  correctly treated as a distinct record if ever added, not merged with
  this "selected regions" one, per this platform's duplicate-control
  rule that different awards from the same provider must stay separate.
- **robots.txt / indexing note**: A standard Drupal file (`/core/`,
  `/profiles/`, `/admin/`, etc. disallowed) that does not cover this
  content path
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Title selector robustness**: the page's raw HTML contains *two*
    generic placeholder `<h1>` tags inside HTML comments ("Library item
    label woz ere") — the same "commented-out heading poses no risk"
    property already verified directly for Newcastle's VCIS (#61);
    `soup.find_all("h1")` on this page returns exactly the one real
    heading.
  - **Deadline keyword choice**: this is the first England source to
    successfully extract a real, exact, future deadline. The page's
    real sentence is "You must accept your offer from the University
    before 4pm (UK time) on Tuesday 6 July 2027" — the literal word
    "deadline" does appear once elsewhere on the page ("If you accept
    your first offer by the deadline...") but more than 300 characters
    *after* the actual date, so the default "deadline" keyword would
    anchor too late and find nothing; `deadline_keywords = ("accept
    your offer",)` anchors on the sentence's own start instead,
    verified directly against the live fixture to correctly extract
    `2027-07-06`.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/sheffield_international_postgraduate_scholarship.html`).

## 63. Global Futures Scholarships (University of Manchester)

Researched 2026-09-05, a second "add another England postgraduate
scholarship" follow-up in the same session — this platform's 11th
university-classified source.

- **Organization**: University of Manchester
- **Route code**: `manchester-global-futures-scholarship`
  (`manchester_global_futures_scholarship` internally)
- **Official domain / base URL**: `https://www.manchester.ac.uk`
  (`MANCHESTER_GFS_BASE_URL`)
- **Opportunity types**: Scholarship — "more than 350 partial
  merit-based scholarships" (totalling over £6 million) for September
  2027 entry, open to both undergraduate and master's (postgraduate
  taught) students. Genuine postgraduate applicability, not assumed:
  the page names "Taiwan (postgraduate taught master's only)" as one
  region, `funding_type = "partial_funding"`.
- **Country coverage / eligibility**: Restricted to a specific published
  list — verified directly, not assumed: Bangladesh, Botswana, Canada,
  Egypt, Ghana, India, Indonesia, Kenya, Malaysia, Mauritius, Nigeria,
  Pakistan, Saudi Arabia, Singapore, South Africa, Sri Lanka, Taiwan,
  Thailand, Türkiye, UAE, USA, Vietnam, Zimbabwe. **Sierra Leone is not
  on this list** — the same Sierra-Leone-eligibility check already
  applied to Newcastle's VCIS (#61) and Sheffield's PG Scholarship
  (#62).
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML, no JavaScript execution needed)
- **robots.txt / indexing note**: Does not disallow this content path
  (only unrelated campaign/search/media-library paths are disallowed)
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Deliberately extracts no deadline**: the page states plainly "The
    level of award, eligibility criteria and application deadlines
    differ for each region so check your country profile for specific
    details" — there genuinely is no single deadline on this hub page,
    only per-country sub-pages this adapter does not fetch. Verified
    directly that no confident date literal exists anywhere in the
    scraped text, so nothing was guessed or fabricated to fill the
    field.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/manchester_global_futures_scholarship.html`).

### Researched this pass (England postgraduate follow-up), not integrated

- **Aston University Vice-Chancellor's International Scholarship** —
  fetched successfully (200, real content), but the live page's own
  text is genuinely stale: it references "Undergraduate Scholarship
  Applications for September 2024," a postgraduate deadline of "Monday
  2 October 2023" / "Tuesday 31 October 2023," and no evidence of a
  current 2026/27 or 2027/28 cycle anywhere on the page — verified
  directly by reading the scraped text, not assumed from the page
  returning 200. Per this platform's "never convert a historical
  opportunity into a current one" rule, this was left unintegrated
  rather than presented as live.
- **Aston Postgraduate Impact Scholarship** — its expected URL
  redirects to a generic funding hub page; the specific scholarship page
  appears to have been retired or merged. Not chased further within
  this pass.
- **Nottingham Trent University** (international scholarships hub and
  postgraduate Master's scholarships page) — both returned a genuine
  HTTP 403 on every fetch attempt (including `robots.txt` itself, and
  with a plain browser user agent), consistent with active bot
  protection rather than a page-specific block. Recorded for manual
  verification, not circumvented.
- **University of Leicester** (International Postgraduate Taught Merit
  Scholarship, Global Excellence Scholarship, Chancellor's International
  Postgraduate Taught Scholarship, and the general international
  scholarships hub) — all four returned a genuine HTTP 403, while
  `robots.txt` itself is fetchable (200) — a targeted block on these
  content paths specifically. Recorded for manual verification.
- **University of Birmingham Postgraduate High Fliers Scholarship** — a
  real, fetchable (200), and richly-detailed page, but its own FAQ text
  states "there is a deadline, the closing date is 31 July 2026" for
  the September 2026 intake it describes — already past as of the
  2026-09-05 research date, with no evidence of an announced next
  (2027) cycle found on the page. Per the "never present a closed
  cycle as current, never fabricate a next cycle" rule, this was left
  unintegrated rather than added as a stale or invented record.

## 64. International Postgraduate Scholarship (University of Nottingham)

Researched 2026-09-05, a third "add another England postgraduate
scholarship" follow-up in the same session — this platform's 12th
university-classified source.

- **Organization**: University of Nottingham
- **Route code**: `nottingham-international-postgraduate-scholarship`
  (`nottingham_pg_scholarship` internally)
- **Official domain / base URL**: `https://www.nottingham.ac.uk`
  (`NOTTINGHAM_PG_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — an automatic tuition-fee
  deduction for self-funded international students starting a
  full-time, UK-campus-based postgraduate taught Master's degree,
  `funding_type = "partial_funding"`
- **Country coverage / eligibility**: Genuinely distinct from this
  platform's other England sources (#60–63, all restricted to a
  specific published country list and/or a named entry year): this page
  states no country/nationality restriction at all — only "an
  international fee-paying student" — and no entry-year lock anywhere
  in its text, a genuinely evergreen description rather than one tied to
  a single admissions cycle. "No scholarship application needed. This
  will be automatically awarded."
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML, no JavaScript execution needed). Note: the
  university's own `.aspx`-templated "International Postgraduate
  Masters Scholarship" page (a different URL for the same programme)
  renders its actual descriptive content client-side and was not used
  for that reason — the shorter `/pgstudy/funding/...` page used
  instead is genuinely server-rendered with the same substance.
- **robots.txt / indexing note**: Only disallows internal search-result
  paths (`/search.aspx` and equivalents, added specifically because a
  parameterised search-result URL had leaked into Bing's index) — not
  this content page
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **No funding amount asserted in code**: secondary sources
    encountered during discovery cited "£3,000," but the actual page
    used as this source's overview does not state a specific amount
    (only that the award "will be deducted from your master's tuition
    fee") — nothing beyond what the scraped description itself contains
    is asserted, per the "never invent a funding value the source
    doesn't state" rule.
  - **Deliberately extracts no deadline**: none is stated on the page —
    correctly absent, not an extraction failure.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/nottingham_pg_scholarship.html`).

### Researched this pass (third England postgraduate follow-up), not integrated

- **University of Leeds International Masters Regional Scholarships /
  International Excellence Scholarships** — both real and fetchable
  (200), but genuinely ambiguous in currency: the hub page explicitly
  states the International Excellence Scholarships are "now closed"
  for the 2026 cycle they describe, and the Regional Scholarships page,
  while not marked closed, is scoped to students "starting in September
  2026" — a cohort whose admissions window is effectively over as of
  the 2026-09-05 research date. Checked directly for a 2027 successor
  page (`international-regional-scholarships-2027`,
  `international-excellence-scholarships-2027`): both URLs return
  HTTP 200 but are soft-404s (the page's own `<title>` reads
  "404-error" despite the 200 status) — verified directly by reading
  the title, not assumed from the status code alone. Left unintegrated
  rather than presented as a fresh 2027 opportunity that doesn't yet
  exist.
- **Queen Mary University of London** (postgraduate January 2027 start
  page and its scholarships) — returned a genuine HTTP 403 on every
  fetch attempt, including `robots.txt` itself. Recorded for manual
  verification, not circumvented.
- **University of Warwick** (Doctoral College PGR Scholarship
  Competitions) — real and fetchable, but the page is a multi-tab
  listing of six distinct competitions (Chancellors, AHRC, Doctoral
  Access–Sanctuary, Doctoral Access–Pathway, Monash-Warwick, China
  Scholarship Council-Warwick) rather than a single flagship
  scholarship — the same multi-record architectural mismatch already
  documented for UNSW's and TU Delft's general scholarship hubs above,
  out of scope for this pass's `_SingleProgramSource` pattern.

## 65. Presidential bursaries (University of Southampton)

Researched 2026-09-05, a fourth "add another England postgraduate [and
undergraduate]" follow-up in the same session — this platform's 13th
university-classified source.

- **Organization**: University of Southampton
- **Route code**: `southampton-presidential-bursaries`
  (`southampton_presidential_bursaries` internally)
- **Official domain / base URL**: `https://www.southampton.ac.uk`
  (`SOUTHAMPTON_PRESIDENTIAL_BURSARIES_BASE_URL`)
- **Opportunity types**: Grant/bursary — a PhD-level fee-difference
  bursary: "funds the difference between UK and international level
  tuition fees," `funding_type = "partial_funding"` (not a stipend, not
  full funding)
- **Country coverage / eligibility**: "Open to all international
  candidates demonstrating exceptional academic performance" — no
  country/nationality restriction, unlike this platform's other England
  postgraduate sources (Sheffield #62, Manchester #63). Requires
  accepting a PhD offer and starting studies "between 1 August 2026 and
  31 January 2027" plus a first-class undergraduate degree.
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML behind gzip/brotli compression — required `curl
  --compressed` during verification; the codebase's own HTTP client
  already handles this transparently via `httpx`'s default decoding, so
  no special-casing was needed in the adapter itself)
- **robots.txt / indexing note**: Does not disallow this content path
  (the one relevant disallow entry targets a different page,
  `/study/postgraduate-research/projects/`)
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Narrow content selector, verified directly**: the page's
    `<article class="page--detail">` wrapper also contains a large
    left-hand sidebar listing dozens of unrelated scholarship names
    (Chevening, Commonwealth, Fulbright, and many others) *before* the
    real content in document order — selecting that broader wrapper
    would exhaust the 5000-character description cap on the nav list
    alone. `div.body--content` is the narrower, correct target,
    confirmed by fetching the real page rather than assumed from
    structure alone.
  - **Deliberately extracts no deadline**: "You do not need to make a
    separate application. If you meet the eligibility criteria, your
    Faculty will apply ... for you" — there is no application deadline
    to extract. The only date literal on the page (1 August 2026) is
    the eligibility window's *opening*, not a deadline; default
    `deadline_keywords` correctly match nothing.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/southampton_presidential_bursaries.html`).

## 66. Merit scholarships for international undergraduates (University of Southampton)

Researched 2026-09-05, discovered via the sidebar navigation on
Southampton's own Presidential bursaries page (#65) above — this
platform's first England **undergraduate**-specific source since
Newcastle's VCIS (#61) and Imperial Inspires (#60), and its 14th
university-classified source overall.

- **Organization**: University of Southampton
- **Route code**: `southampton-merit-undergraduate-scholarship`
  (`southampton_merit_undergraduate_scholarship` internally)
- **Official domain / base URL**: `https://www.southampton.ac.uk`
  (`SOUTHAMPTON_MERIT_UG_BASE_URL`)
- **Opportunity types**: Scholarship — "up to £4,500 off the first year
  of tuition fees," `funding_type = "partial_funding"`. Structurally
  distinct from every other England source in this file: award is based
  on exceeding academic offer conditions (A-level/IB grades above the
  standard offer), by school/subject, not a country/region eligibility
  list.
- **Country coverage / eligibility**: Any student who "need[s] to pay
  the overseas tuition fee" — no nationality/country restriction stated.
  The one country-specific carve-out mentioned on the page (the
  "Southampton Canadian Prestige Scholarship for Law") is a distinct,
  separate award referenced in passing, not this scholarship's own
  eligibility rule — preserved as-is in the scraped description, not
  conflated with it. Explicitly excludes PGCert/PGDip/Foundation/PGR/
  Distance Learning/Malaysia-campus/CPD courses, per the page's own
  exclusion list.
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML, gzip/brotli-compressed like #65 above)
- **robots.txt / indexing note**: Does not disallow this content path
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Deliberately extracts no deadline**: eligibility is grade-
    outcome-based ("exceed your offer"), not deadline-based — "You do
    not need to apply for merit scholarships. If you meet the
    eligibility criteria, we will award you this scholarship" —
    verified directly that no date literal exists anywhere on the page.
- **LIVE SOURCE TEST: PASSED 2026-09-05.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/southampton_merit_undergraduate_scholarship.html`).

## 67. Durham Inspiring Excellence Scholarship (Undergraduate) (Durham University)

Researched 2026-09-06 — this platform's first Durham University source,
and its 15th university-classified source overall.

- **Organization**: Durham University
- **Route code**: `durham-inspiring-excellence-undergraduate-scholarship`
  (`durham_inspiring_excellence_undergraduate_scholarship` internally)
- **Official domain / base URL**: `https://www.durham.ac.uk`
  (`DURHAM_INSPIRING_EXCELLENCE_UG_BASE_URL`)
- **Opportunity types**: Scholarship — a competitive tuition-fee discount
  worth up to £15,000–£30,000 over a three-year undergraduate programme
  (two award tiers: £5,000/year and £10,000/year). `funding_type =
  "partial_funding"` — a fee discount, not full funding.
- **Country coverage / eligibility**: "Available to all self-funded
  international applicants" classified as "Overseas student for tuition
  fee purposes" — no nationality/country restriction stated, so Sierra
  Leone applicants are eligible like any other international student.
  Excludes two named Theology programmes and anyone applying via
  Clearing, Insurance Choice, or the Durham University International
  Study Centre progression route.
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML from a Terminal Four-built page)
- **robots.txt / indexing note**: `durham.ac.uk/robots.txt`'s
  `User-Agent: *` block has a blanket empty `Disallow:` (i.e. no
  restriction), and none of its named `Disallow:` entries (internal
  test/build/asset paths) match this content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **No `<h1>` on the page** (like several other England sources here):
    `title_selectors` is left at its default `("h1",)`, which does not
    match, so `collect()` falls back to the `external_id`-derived title —
    verified this reads correctly as "Durham Inspiring Excellence
    Undergraduate Scholarship."
  - **Content selector is `div.col-md-9`, deliberately NOT
    `div.t4-text-long`**: the latter is a second, later block on the same
    page holding only the scholarship's Terms and Conditions (withdrawal/
    notification rules) — verified directly via a BeautifulSoup
    structural walk of the fetched page that `div.col-md-9` is the page's
    actual Summary/Amount/Eligibility/How-to-apply content, in document
    order, before the Terms and Conditions block.
  - **`deadline_keywords` uses the specific phrase "1st round application
    deadline", not the generic "deadline"**: the page's first plain
    "deadline" occurrence is an unrelated "UCAS reply deadline" phrase
    with no date literal within the following 300 characters, so the
    generic keyword resolves to no match. The specific phrase correctly
    and consistently resolves to the first (earliest) of the page's three
    stated application rounds for September 2027 entry: 7 December 2026.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/durham_inspiring_excellence_undergraduate_scholarship.html`).

## 68. Durham Inspiring Excellence Scholarship (Postgraduate) (Durham University)

Researched 2026-09-06 — the Master's-level counterpart of #67 above, on
its own flagship page with its own eligibility rules.

- **Organization**: Durham University
- **Route code**: `durham-inspiring-excellence-postgraduate-scholarship`
  (`durham_inspiring_excellence_postgraduate_scholarship` internally)
- **Official domain / base URL**: `https://www.durham.ac.uk`
  (`DURHAM_INSPIRING_EXCELLENCE_PG_BASE_URL`)
- **Opportunity types**: Scholarship — a competitive tuition-fee discount
  worth up to £10,000 for a one-year, full-time taught Master's
  programme (MSc/MA/LLM/MDS; MBA, MSW, and MA in Theology and Ministry
  excluded). `funding_type = "partial_funding"` — a fee discount, not
  full funding.
- **Country coverage / eligibility**: "Available to all self-funded
  international applicants" with no nationality/country restriction
  stated — Sierra Leone applicants are eligible. Durham alumni may apply
  but cannot combine this award with the university's separate Alumni
  Discount.
- **Discovery method**: Web scraper (plain HTTPS GET, real server-
  rendered HTML from the same Terminal Four-built site as #67)
- **robots.txt / indexing note**: Same finding as #67 above — no
  restriction on this content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - Same no-`<h1>` / `external_id`-fallback title behaviour and the same
    `div.col-md-9` vs. `div.t4-text-long` (Terms and Conditions block)
    content-selector distinction documented on #67 — verified
    independently against this page's own fetched HTML, not assumed from
    the undergraduate page's structure.
  - Same three-round deadline structure and phrasing as #67
    ("1st round application deadline: 7 December 2026") — confirmed
    independently on this page's own fetched HTML that
    `deadline_keywords = ("1st round application deadline",)` resolves to
    2026-12-07 here too.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/durham_inspiring_excellence_postgraduate_scholarship.html`).

### Researched this pass (England postgraduate/masters/undergraduate follow-up), not integrated

- **University of Bristol — Think Big / GREAT Scholarships** — real,
  official (`bristol.ac.uk`), and clearly describes postgraduate taught
  scholarships (£6,500/£13,000/£26,000 tiers) with no country
  restriction found. Not integrated this pass: every application
  deadline found for the current 2026-27 cycle (April 2026) has already
  passed as of this research date (2026-09-06), and no 2027-28 cycle
  page or dates have been published yet on Bristol's own site — per the
  "never guess a future deadline/cycle from a stale prior one" rule, this
  was left unintegrated rather than pointing at closed-cycle content.
  Worth revisiting once Bristol publishes its next cycle's page.
- **University of York — International Masters/Undergraduate Achievement
  Scholarships** — real, official (`york.ac.uk`), automatic (no separate
  application) tuition-fee-discount scholarships. Not integrated this
  pass: the undergraduate scholarship's stated eligibility window ("hold
  an offer by 30 June 2026") is for the 2026 entry cycle, which has
  already passed as of this research date, and no 2027-entry page with
  its own dates was found yet on York's own site — same "no stale-cycle
  guessing" reasoning as Bristol above. Worth revisiting once York
  publishes its next cycle's page.

## 69. Deutschlandstipendium (University of Freiburg)

Researched 2026-09-06, in response to a request for another Germany
postgraduate, masters, and undergraduate universities scholarship — this
platform's second Germany-university source (after TUM's International
Student Scholarship, #59), and its 17th university-classified source
overall. Unlike the England sources above
(one page per degree level), this single page explicitly covers both
halves of the request: "students enrolled on an undergraduate degree
programme or a Master's degree programme" are both eligible.

- **Organization**: University of Freiburg
- **Route code**: `freiburg-deutschlandstipendium`
  (`freiburg_deutschlandstipendium` internally)
- **Official domain / base URL**: `https://uni-freiburg.de`
  (`FREIBURG_DEUTSCHLANDSTIPENDIUM_BASE_URL`) — the page search engines
  index under `studium.uni-freiburg.de` 301-redirects to this canonical
  host; confirmed identical content on both, and `overview_path` targets
  the canonical URL directly rather than relying on the scraper's HTTP
  client to follow the redirect.
- **Opportunity types**: Scholarship — EUR 300/month for one year (a
  stipend supplement, not full tuition/living coverage), half funded by
  the federal government and half by private sponsors.
  `funding_type = "partial_funding"`.
- **Country coverage / eligibility**: "Students of all nationalities may
  apply for the Deutschlandstipendium" — no nationality/country
  restriction, so Sierra Leone applicants are eligible. Requires being
  enrolled as a regular student at the University of Freiburg — the same
  "already enrolled, not a brand-new applicant" shape as this platform's
  existing TUM International Student Scholarship source (#59), which is
  not a barrier to listing it.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  WordPress-rendered HTML)
- **robots.txt / indexing note**: `uni-freiburg.de/robots.txt` only
  disallows `/wp-admin/`, not this content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Content selector is the first `div.wp-block-columns`, deliberately
    NOT the much larger `main`** (42KB, mostly a tabbed FAQ accordion
    repeating the same eligibility/process detail): the chosen selector
    captures both the program's general description/funding/eligibility
    summary *and* the page's current application-cycle status in one
    clean ~1.7KB block — verified directly via a BeautifulSoup structural
    walk of the fetched page before choosing it.
  - **Deliberately extracts no deadline despite two dates being
    present**: the page states the 2026/2027 award year's application
    deadline "has passed" (no date literal within reach of that phrase)
    and that "you can apply for the 2027/2028 scholarship round from 1
    March 2027 to 31 March 2028" — a thirteen-month window that
    contradicts the page's own description elsewhere of a short, roughly
    one-month March application period each year (and the university's
    own FAQ text: "you can only apply the following March for a
    scholarship"). Given that internal inconsistency, this reads as a
    likely typo on the university's own page (probably meant 31 March
    **2027**) rather than a literal fact to report — so, per this
    platform's "extract nothing rather than guess wrong" rule, no
    deadline is extracted rather than reporting a suspect date verbatim
    or silently correcting it.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/freiburg_deutschlandstipendium.html`).

### Researched this pass (Germany postgraduate/masters/undergraduate
follow-up), not integrated

Ten other Germany candidates were researched live before settling on
Freiburg's Deutschlandstipendium above, and none fit this platform's
single-flagship-page shape:

- **Heidelberg University** — its "Scholarship Programmes" and
  "Scholarships and Fundings" pages are both about Heidelberg students
  studying *abroad* (outgoing), not incoming international applicants to
  Heidelberg; no incoming-applicant flagship page was found.
- **University of Bonn** — its "Degree Completion Scholarship" and
  related scholarships require the student to already be enrolled and
  expected to graduate within 12 months, with funding/application
  details for the current round "to be published" — not yet concrete;
  its own Deutschlandstipendium page (German-only, no English version)
  states the 2026/2027 application round "has ended"
  (*Das Bewerbungsverfahren ... ist beendet*) with no next round dates
  published yet.
- **Constructor University Bremen** (formerly Jacobs University) — three
  named scholarships checked (BSc Software/Data/Technology and MSc
  Advanced Software Technology JetBrains Foundation scholarships, and the
  Sparkasse Mathematics Scholarship): all three state a single deadline
  in the March 2026 range for the current intake, already passed as of
  this research date, with no next-cycle dates published on the same
  pages.
  Its general financing pages are also, like ESMT and WHU below, a hub of
  many separately-named scholarships rather than one flagship program.
- **University of Mannheim** — the "Opportunity Mannheim Scholarship"
  (excludes Master's applicants entirely) and the general "Mannheim
  Scholarship" both state their 2026/2027 application windows "have
  ended," with no next round dates published yet.
- **ESMT Berlin** (MBA and Master's programs) — genuinely live, rolling
  application cycles (January 2027 MBA intake still open), but each
  "Fees & Financing"/"Scholarships" page is a hub of roughly ten
  separately-named, separately-sponsored awards (Gender pay gap
  scholarship, Rainbow scholarship, five Regional scholarships, Dean's
  Excellence, Vali Berlin entrepreneurship, BMW Group Change Maker
  Fellowship, e-Fellows scholarship, and more) — the same multi-record
  architecture mismatch already documented for Warwick's Doctoral College
  page (source research, `docs/AUTHORITATIVE_SOURCES.md` #64's "not
  integrated" note) and TU Delft's general scholarship hub, not forced
  into a single-record shape it doesn't have.
- **WHU – Otto Beisheim School of Management** (Bachelor and MSc
  programs) — same multi-record hub shape as ESMT: roughly ten
  separately-named scholarships (Merit, Excellence, Responsible Leader,
  Social Impact, In Praxi Diversity, In Praxi Women in Business,
  e-Fellows, Women in Management, Women in Finance, Business Leaders,
  Female Founders, Global Community, Global IB, and more) sharing one
  page and one deadline but each with its own distinct eligibility
  criterion — not integrated for the same reason as ESMT above. Its
  separate "Germany Scholarship" (Deutschlandstipendium) page is a
  donor/fundraising page with no application process or deadline
  described for students.
- **Frankfurt School of Finance & Management** — same multi-record hub
  pattern again (Corporate Governance Scholarship, Beyond Capital
  Partners Scholarship, Alumni Association Scholarship, Klaus-Peter
  Müller Scholarship, and more).
- **University of Göttingen** — its widely-advertised "DAAD Scholarship"
  for Göttingen's agricultural/forestry/environmental Master's programs
  is DAAD-administered (already covered by this platform's existing DAAD
  source, #10), not a distinct Göttingen-university program, and its
  stated deadline window ("October 1st to November 15th") carries no
  year.
- **IU International University of Applied Sciences** — no reachable
  official scholarship page found; its on-campus scholarship content
  appears to be rendered client-side (a Vue/Nuxt single-page app) and did
  not appear in this platform's plain-HTTP fetch of the on-campus
  overview page.

## 70. Amsterdam Merit Scholarship, Master's (University of Amsterdam)

Researched 2026-09-06, in response to a directive for a deep, exhaustive
Netherlands university scholarship expansion — this platform's second
Netherlands *university* source (TU Delft's Van Effen Scholarship, #58,
was the first; #22 is the Nuffic-administered, government-classified NL
Scholarship, not a university source), and its 18th university-classified
source overall.

- **Organization**: University of Amsterdam
- **Route code**: `uva-amsterdam-merit-scholarship-master`
  (`uva_amsterdam_merit_scholarship_master` internally)
- **Official domain / base URL**: `https://www.uva.nl`
  (`UVA_AMSTERDAM_MERIT_SCHOLARSHIP_MASTER_BASE_URL`)
- **Opportunity types**: Scholarship — a merit award, no specific amount
  stated on this general overview page (a EUR 25,900 figure for
  2026-2027 was seen on one Faculty-specific subpage — Amsterdam Law
  School's — but never on this general page, so it is not asserted
  here). `funding_type = "partial_funding"`.
- **Country coverage / eligibility**: "Students who hold a non-EU/EEA
  passport" — Sierra Leone applicants are eligible.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML)
- **robots.txt / indexing note**: `uva.nl/robots.txt` is a genuine empty
  file — HTTP 200, zero bytes — so no restrictions are declared at all.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Deliberately extracts no deadline and states no specific amount**:
    this general overview page says outright that "Deadlines for the AMS
    differ per Faculty or Graduate School" and links to nine separate
    faculty pages, each administering its own deadline — verified
    directly, not assumed. Per-faculty administered variants (e.g. the
    Faculty of Economics and Business also separately runs an "Amsterdam
    Economics and Business Talent Fund" alongside the AMS) were not
    modeled as separate sources this pass.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/uva_amsterdam_merit_scholarship_master.html`).

## 71. Amsterdam Merit Scholarship, Bachelor's (University of Amsterdam)

Researched 2026-09-06, same pass — the undergraduate counterpart of #70,
on its own separate overview page with its own continuation-of-funding
condition (approximately 80% credits/year).

- **Organization**: University of Amsterdam
- **Route code**: `uva-amsterdam-merit-scholarship-bachelor`
  (`uva_amsterdam_merit_scholarship_bachelor` internally)
- **Official domain / base URL**: `https://www.uva.nl`
  (`UVA_AMSTERDAM_MERIT_SCHOLARSHIP_BACHELOR_BASE_URL`)
- **Opportunity types**: Scholarship — same merit-award shape as #70,
  no specific amount stated on this page. `funding_type =
  "partial_funding"`.
- **Country coverage / eligibility**: Same as #70 — non-EU/EEA passport
  holders; Sierra Leone applicants are eligible.
- **Discovery method / robots.txt / API / Authentication / Reliability /
  Verification / Sync cadence**: Same as #70.
- **Deliberate design choices**: Same "deadlines differ per Faculty, no
  deadline extracted" reasoning as #70, verified independently on this
  page's own fetched HTML.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/uva_amsterdam_merit_scholarship_bachelor.html`).

## 72. Eric Bleumink Fellowship (University of Groningen)

Researched 2026-09-06, same pass.

- **Organization**: University of Groningen
- **Route code**: `groningen-eric-bleumink-fellowship`
  (`groningen_eric_bleumink_fellowship` internally)
- **Official domain / base URL**: `https://www.rug.nl`
  (`GRONINGEN_ERIC_BLEUMINK_FELLOWSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — "covers tuition fee, costs of
  international travel, subsistence, books, and health insurance," a
  genuinely comprehensive package. `funding_type = "fully_funded"` — a
  deliberate, evidence-based classification, not a default.
- **Country coverage / eligibility**: Restricted to an explicit list of
  roughly 80 named developing countries — **Sierra Leone is confirmed
  present in that list directly** (`Countries of Origin: ... Sierra
  Leone ...`), not inferred from a vague "developing countries" label.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML). The URL search results index
  (`.../eric-bleumink-fund`) 302-redirects to the canonical
  `.../eric-bleumink-fellowship` URL used directly.
- **robots.txt / indexing note**: `rug.nl/robots.txt` does not disallow
  this content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Nomination-based, not a separate scholarship application**: "It
    is not possible to actively apply... Suitable candidates will be
    informed about a nomination" — made entirely by the University of
    Groningen's own Admission Office as a byproduct of a regular
    Master's application submitted before 1 December, not by a separate
    third-party institution's own quota. A materially different shape
    from Vanier Canada Graduate Scholarships (documented at #66's
    "researched previous pass" note as unsuitable for exactly that
    reason) and closer to this platform's existing "automatic
    consideration" sources (e.g. Nottingham's PG Scholarship, #64).
  - **Deliberately extracts no deadline**: both stated dates ("before
    February," "before 1st of December") are recurring annual points
    with no year attached, and the page's own "Last modified: 11 August
    2026" timestamp confirms it is current, not a stale prior-year
    snapshot.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/groningen_eric_bleumink_fellowship.html`).

## 73. Law, Economics and Governance International Talent Scholarship (Utrecht University)

Researched 2026-09-06, same pass.

- **Organization**: Utrecht University (Faculty of Law, Economics and
  Governance)
- **Route code**: `utrecht-legits-scholarship`
  (`utrecht_legits_scholarship` internally)
- **Official domain / base URL**: `https://www.uu.nl`
  (`UTRECHT_LEGITS_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — "will cover the tuition fee"
  (statutory rate for EU/EEA, institutional rate for non-EU/EEA) — no
  living-cost, travel, or insurance coverage mentioned, so
  `funding_type = "partial_funding"`.
- **Country coverage / eligibility**: "Both EU/EEA and non-EU/EEA
  students are eligible to apply" — Sierra Leone applicants are
  eligible. Restricted to applicants without a Dutch secondary
  education qualification or Dutch Bachelor's degree, for a Sept 2027
  intake.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML)
- **robots.txt / indexing note**: `uu.nl/robots.txt` is a standard
  Drupal file that does not disallow this content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Utrecht's central, university-wide Utrecht Excellence Scholarship
    was deliberately NOT used**: confirmed live and directly on
    Utrecht's own page that it has been discontinued — "Due to
    significant budget cuts, the Utrecht Excellence Scholarship (UES)
    will no longer be offered for programmes starting in the 2026-2027
    academic year. No new UES applications will be accepted." Utrecht's
    separate **Bright Minds Fellowships** were also not used — confirmed
    restricted to "EU/EEA students (including Dutch students)" only, so
    Sierra Leone applicants would not be eligible.
  - **Deliberately extracts no deadline**: the stated deadline ("before
    February 1st 23:59 CET") never carries a year on this page, even
    though a *different*, unrelated date on the same page (the
    application portal's "1 November 2026" opening) does — verified
    directly that `extract_confident_date_after` does not accidentally
    resolve to that unrelated date.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/utrecht_legits_scholarship.html`).

## 74. UM NL-High Potential Scholarship (Maastricht University)

Researched 2026-09-06, same pass.

- **Organization**: Maastricht University
- **Route code**: `maastricht-high-potential-scholarship`
  (`maastricht_high_potential_scholarship` internally)
- **Official domain / base URL**: `https://www.maastrichtuniversity.nl`
  (`MAASTRICHT_HIGH_POTENTIAL_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — "18 full scholarships, including
  tuition fee waiver and monthly stipend, each academic year."
  `funding_type = "fully_funded"` — a deliberate, evidence-based
  classification, not a default.
- **Country coverage / eligibility**: Open to nationals of "a country
  outside the EU/EEA, Switzerland or Surinam" — Sierra Leone applicants
  are eligible (the Suriname carve-out is a historical NL-Suriname
  relationship exception, recorded as-is).
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML)
- **robots.txt / indexing note**: `maastrichtuniversity.nl/robots.txt`
  does not disallow this content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Already updated for the *next* application cycle as of this
    research date**: applicants must have "applied for admission to a
    participating full-time master's programme at Maastricht University
    for the 2027-2028 academic year" with a full application submitted
    "before 10 December 2026" — a real, not-yet-passed deadline, unlike
    several other Netherlands candidates researched this pass (VU
    Amsterdam's VUFP, TU Eindhoven's Scholarship for Excellence,
    Erasmus's Trustfonds Scholarship — see the "not integrated" note
    below) which were all still locked to their already-closed
    2026-2027 cycles with no next-cycle page published yet.
  - `deadline_keywords` uses the specific phrase "before 10 December"
    (appearing exactly once on the page) rather than the generic
    "deadline" keyword, whose first occurrence has no date literal
    nearby.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/maastricht_high_potential_scholarship.html`).

## 75. University of Twente Scholarship (UTS)

Researched 2026-09-06, same pass.

- **Organization**: University of Twente
- **Route code**: `university-of-twente-scholarship`
  (`university_of_twente_scholarship` internally)
- **Official domain / base URL**: `https://www.utwente.nl`
  (`UTWENTE_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — a cash award of EUR 3,000-22,000
  for one year, "meant as a compensation for study related costs...
  No costs (e.g. tuition fees) will be paid on your behalf" —
  `funding_type = "partial_funding"` rather than a tuition waiver.
- **Country coverage / eligibility**: The page lists an explicit
  "Countries eligible for this scholarship" enumeration of nearly every
  non-EU/EEA country in the world — **confirmed directly that Sierra
  Leone appears in it**, in correct alphabetical position between
  Seychelles and Singapore, not assumed from "non-EU/EEA."
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML)
- **robots.txt / indexing note**: `utwente.nl/robots.txt` does not
  disallow this content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Already updated for the 2027/2028 intake** as of this research
    date: "Application deadline 1 April 2027" — a real, not-yet-passed
    date, verified to resolve reliably via `extract_confident_date_after`
    (its only three occurrences on the page all refer to this same
    date).
  - The huge eligible-countries enumeration sits well past this
    platform's 5000-character description truncation point, so it does
    not crowd out the more informative opening sections in the stored
    description.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/university_of_twente_scholarship.html`).

## 76. Anne van den Ban Fund (Wageningen University & Research)

Researched 2026-09-06, same pass.

- **Organization**: Wageningen University & Research
- **Route code**: `wageningen-anne-van-den-ban-fund`
  (`wageningen_anne_van_den_ban_fund` internally)
- **Official domain / base URL**: `https://www.wur.nl`
  (`WAGENINGEN_ANNE_VAN_DEN_BAN_FUND_BASE_URL`)
- **Opportunity types**: Scholarship — "full or partial funding for an
  MSc programme," varying by selected student, so `funding_type =
  "partial_funding"` rather than asserting `fully_funded` for every
  award this fund makes.
- **Country coverage / eligibility**: Restricted to "students from
  low-income countries" — a real World Bank income-classification term
  (not a vague "developing countries" or "Africa" label) that Sierra
  Leone falls under. Unlike this platform's Eric Bleumink Fellowship
  source (#72), this page does not itself enumerate a specific country
  list, so this is recorded with that caveat rather than as a
  directly-confirmed-on-page fact the way Groningen's is.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML). The URL search results index
  (`.../named-funds/anne-van-den-ban-fonds`) 308-redirects to the
  canonical `.../anne-van-den-ban-fund` URL; the "Selection Anne van den
  Ban Fund" applicant-information page is used directly rather than the
  fund's own donor/fundraising page (fetched and compared directly
  before choosing).
- **robots.txt / indexing note**: `wur.nl/robots.txt` does not disallow
  this content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Nomination-based, not a separate application**: "The fund does
    not consider individual applications... interested parties must
    wait until an Anne van den Ban scholarship is offered" from among
    already-admitted Master's applicants, selected annually each spring
    by the fund's own board together with Wageningen University — the
    same "internal nomination, not a third-party quota" shape as
    Groningen's Eric Bleumink Fellowship (#72).
  - **Deliberately extracts no deadline**: the only timing given
    (spring/May notification, "if you have not received an offer by 1
    June") is a recurring annual window with no year attached.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/wageningen_anne_van_den_ban_fund.html`).

## 77. ITC Excellence Scholarship Programme (University of Twente)

Researched 2026-09-06, in response to a follow-up request for another
Netherlands Master's/postgraduate scholarship. A distinct scholarship
from the university-wide University of Twente Scholarship (#75, already
added) — administered specifically by the Faculty of Geo-Information
Science and Earth Observation (ITC) for two of its own Master's
programmes, with its own eligibility list, cost breakdown, and
application page.

- **Organization**: University of Twente (Faculty of Geo-Information
  Science and Earth Observation, ITC)
- **Route code**: `utwente-itc-scholarship` (`utwente_itc_scholarship`
  internally)
- **Official domain / base URL**: `https://www.utwente.nl`
  (`UTWENTE_ITC_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — a genuinely partial scholarship
  with an exact cost breakdown stated on the page: the ITC waiver covers
  EUR 25,000 of a EUR 74,370 two-year total cost (tuition + living
  allowance + insurance + residence permit), leaving EUR 17,000 of "own
  contribution" the applicant must independently secure.
  `funding_type = "partial_funding"`.
- **Country coverage / eligibility**: An explicit "Countries eligible
  for this scholarship" enumeration of roughly 100 named low- and
  middle-income countries — **confirmed directly that Sierra Leone
  appears in it**, not assumed. Restricted to the Geo-information
  Science & Earth Observation and Spatial Systems & Society Master's
  programmes.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML)
- **robots.txt / indexing note**: `utwente.nl/robots.txt` does not
  disallow this content path (same finding as the UTS source, #75).
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Deliberately extracts no deadline**: the page states plainly
    "APPLICATIONS 2026 CLOSED. A possible next round is expected to
    open in December" — a real, current status (the page is not stale
    or un-updated), but "December" alone carries no day or year, so no
    confident date literal exists to extract. Recorded transparently in
    the description rather than a deadline being fabricated or a status
    field being invented for it.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/utwente_itc_scholarship.html`).

### Researched this pass (Netherlands Master's/postgraduate follow-up), not integrated

Several other candidates were researched live before settling on the
ITC Excellence Scholarship Programme:

- **VU Amsterdam — Faculty of Law Fellowship Programme** — real, but a
  *visiting-researcher* fellowship (for doctoral candidates and senior
  research fellows on temporary leave from their own institutions), not
  a Master's/postgraduate degree scholarship for enrolling students —
  out of scope for this request.
- **Erasmus MC (Erasmus University Rotterdam) — Erasmus Trustfonds
  Scholarship, Ter Kulve Scholarship, and Erasmus Trustfonds/TSH
  Changemaker Scholarship** — all three real, and the Ter Kulve
  Scholarship in particular is genuinely well-targeted (World Bank
  low/middle-income-country nationality requirement, EUR 17,500 +
  tuition waiver), but all three share the exact same already-passed
  deadline (1 April 2026, verified independently on each page) with no
  2027 refresh yet, and the Erasmus Trustfonds Scholarship is limited to
  a single award per year at Erasmus MC.
- **Erasmus School of Health Policy & Management (ESHPM) — Erasmus
  Trust Fund Scholarship** — restricted to "EEA/EU nationals" only
  (the opposite eligibility direction from what most candidates in this
  project need), and also locked to the already-closed 2026-2027 cycle.
- **TU Delft — Delft Global Scholarship Fund** — real and genuinely
  Africa/Sierra-Leone-relevant in spirit ("promising young engineers
  from various African countries," "students from Sub-Saharan Africa"),
  but its own page is purely a donor/fundraising page for Delft
  University Fund with no eligibility criteria, deadline, or application
  process for students — contributions "go 100% to the Delft Global
  Scholarships," which appear to be administered through TU Delft's
  existing general scholarship application pipeline (the same one
  behind the already-added Van Effen Scholarship, #58) rather than
  through a separately-applicable programme of their own.
- **TU Delft — Costas Lemos Innovation Programme (CLIP) Scholarship** —
  restricted to applicants holding "a Greek passport or Greek
  residence," and its "Call for applications is closed" with no next
  round mentioned.

## 78. Merit Based Scholarship (UPF Barcelona School of Management, Universitat Pompeu Fabra)

Researched 2026-09-06, in response to a request for another Spain
Master's/postgraduate scholarship — this platform's first Spain
*university* source (the existing Spain source, #23, is the
government-classified Becas MAEC-AECID), and its 26th
university-classified source overall.

- **Organization**: UPF Barcelona School of Management (Universitat
  Pompeu Fabra)
- **Route code**: `upf-bsm-merit-scholarship` (`upf_bsm_merit_scholarship`
  internally)
- **Official domain / base URL**: `https://www.bsm.upf.edu`
  (`UPF_BSM_MERIT_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — "covers 25% of the total tuition
  fee," extendable to "an additional 25%" for demonstrated financial
  need. `funding_type = "partial_funding"`.
- **Country coverage / eligibility**: No nationality/country
  restriction stated anywhere in the eligibility criteria (a completed
  university qualification and a minimum 3.0/4.0 GPA, explicitly
  including degrees "obtained abroad") — Sierra Leone applicants are
  eligible.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML from a React/Next.js frontend)
- **robots.txt / indexing note**: `bsm.upf.edu/robots.txt` does not
  disallow this content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Content selector is `div.body-content`**: the page uses
    auto-generated CSS-in-JS class names for most wrapper elements
    (React/Next.js), but this one class is stable and semantic —
    verified directly via a BeautifulSoup structural walk to hold
    exactly the real content, with none of the surrounding navigation.
    A sibling UPF-BSM page (`master-of-science-scholarships`, a hub
    listing several named scholarships) was checked first and rejected:
    its real content never appears in the plain-HTTP response at all
    (client-side rendered), unlike this page.
  - **`deadline_keywords` uses the specific phrase "3rd call", not the
    generic "deadline"**: the page lists four rolling annual
    application rounds with concrete dates (18 June 2026, 3 September
    2026, 26 November 2026, 21 January 2027 — the last two reserved for
    programmes starting in Q1 2027). As of this research date the first
    two rounds have already passed, so the specific "3rd call" phrase
    is used to reliably resolve to the next genuinely upcoming round,
    2026-11-26, rather than the generic "deadline" keyword (which
    resolves to nothing on this page) or the first round's
    already-passed date.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/upf_bsm_merit_scholarship.html`).

### Researched this pass (Spain Master's/postgraduate follow-up), not integrated

Several other Spanish institutions were researched live before settling
on the UPF-BSM Merit Based Scholarship, and a consistent pattern emerged
— Spanish private universities favor multi-scholarship hub pages (like
several German and Dutch business schools documented earlier in this
project) far more than the single-flagship-scholarship pages common at
English and Dutch public universities:

- **IE University — Master's Scholarship Programs** (IE Foundation) —
  real and well-funded ("covering up to full tuition and living
  expenses"), but a hub of roughly ten separately-named,
  separately-sponsored scholarships (Olaf Díaz-Pintado, LPDP Indonesia,
  Fundación Casa de México, Laidlaw Women's Leadership, Kistefos Africa,
  Kistefos Norway, Fulbright, and more) — the same multi-record
  architecture mismatch documented for ESMT, WHU, and IE's own Navarra-
  style peers elsewhere in this project. Notably, the one Africa-focused
  award in the list (Kistefos Young Talented Leaders Scholarship for
  Africa) is itself restricted to "Ethiopia, Ghana, Liberia, Nigeria,
  South Africa and Tanzania" — Sierra Leone is not among the named
  countries. IE's separate "Master's Awards and Scholarships" page
  describes a promising general "IE Awards" tier (10-40% of tuition, no
  country restriction, evergreen "deadline is the program start date"),
  but its actual detail is rendered client-side and did not appear in a
  plain-HTTP fetch.
- **University of Navarra — Scholarships and grants for master's
  degrees** — the same hub pattern (Impactun Foundation, School of
  Architecture/Foro América, School of Science research grants, ALCAT,
  Barcelona/Antoni Gutiérrez-Rubí scholarships, and more), with most
  individual scholarships' actual rules published only as downloadable
  PDF documents rather than a scrapable HTML applicant page.
- **ESADE — MSc Fees and Financing (Excellence Awards)** — a genuinely
  single-scheme, geography-tiered structure closer to this platform's
  accepted pattern (one "Esade MSc Excellence Awards" programme with
  regional variants, including an "African Talent Award" open to
  candidates from African countries generally, no narrower exclusion
  found), but the page's own stated deadline for the award ("July 15,
  2026 (for the 2026 intake)") has already passed, even though the
  surrounding page has otherwise been updated with 2027-2028 tuition
  figures — the scholarship-specific cycle information itself was not
  refreshed, so this was left unintegrated per the "never guess a future
  cycle from a stale prior one" rule rather than assuming a same-shaped
  2027 round exists.
- **UPF Barcelona School of Management — Master of Science Scholarships**
  (the general hub page, as opposed to the Merit Based Scholarship page
  actually used) — its real content is rendered client-side and did not
  appear in a plain-HTTP fetch, confirmed directly before falling back to
  the working `talent-scholarship` URL.

### Researched this pass (2026-09-06, general "another Spain scholarship" follow-up), not integrated

A broader, degree/funding-unrestricted pass (not limited to Master's or
to fully-funded) checked six further Spanish institutions live and
found no new qualifying candidate:

- **Universidad Carlos III de Madrid (UC3M)** — its official
  `/postgraduate/aid` page (redirects to `/postgraduate/scholarships`)
  is a hub listing its own "UC3M Scholarships" (fixed tuition-fee
  coverage, several parallel calls AM02–AM05) and a research-oriented
  "AEM_UC3M" aid programme, alongside many externally-funded and
  country-specific schemes (Mexico's FIDERH, Colombia's ICETEX/PCB,
  Santander-UC3M grants, India-specific funds). Every 2026/27-cycle
  item shown is explicitly marked "Final decision" (already resolved,
  July 2026) or "CLOSED DEADLINE" — not a currently-open single scheme,
  and the same multi-record architecture mismatch documented elsewhere
  in this project.
- **University of Salamanca (USAL) — Becas Internacionales de la USAL**
  — a genuinely strong-sounding programme (tuition exemption,
  accommodation, meals, and health/accident/liability insurance across
  76 official Master's titles), but its own International Relations
  Service host, `rel-int.usal.es` — the only site actually publishing
  the current call's full terms — sets `Disallow: /` for all user
  agents in its `robots.txt`, disallowing this platform's scraper from
  the entire subdomain. A Faculty of Law news page on a different,
  unrestricted subdomain (`derecho.usal.es`) merely links back to the
  disallowed host and is itself a stale 2019 announcement for the
  2019/2020 cycle. Per this project's "respect robots.txt" rule, not
  circumvented.
- **USAL's "Mujeres por África" sub-component** (2 of USAL's
  international scholarship seats, mentioned as a specifically
  Africa-focused strand) — checked specifically for Sierra Leone
  relevance given its Africa focus, but this turned out to be
  externally administered by the Fundación Mujeres por África
  (`mujeresporafrica.es`), with USAL as just one of many partner host
  universities, not a USAL-administered scheme — `EXTERNAL_ONLY`
  relative to USAL — and its 2026 cycle's own registration deadline (14
  May 2026) had already passed as of this research date with no
  next-cycle page found.
- **Universitat Autònoma de Barcelona (UAB) — "Solicitar beca"
  (general grant)** — its official page describes the AGAUR
  (Catalonia)/MEFPD (rest of Spain) "beca de carácter general," which
  explicitly requires "domicilio familiar" (family residence) within
  Spain as of 31 December 2025 — a domestic Spanish student grant, not
  available to an international applicant from abroad — `NOT_
  INTERNATIONAL`.
- **University of Barcelona (UB) and Universidad Complutense de Madrid
  (UCM)** — live search for each surfaced only vague, aggregator-level
  claims ("many scholarships," "up to 70+ expected") with no single,
  specific, official page identified describing one particular
  scheme's exact eligibility and funding terms — Level 3 sources only,
  not treated as sufficient evidence per this project's "official
  university source required, aggregators are discovery-only" rule.

No new source was added this pass — the request itself was a short,
open-scope "find another Spain opportunity" (no Master's-only or
fully-funded-only restriction), and a genuine research pass across six
further institutions found every real, well-documented candidate
either blocked by its own `robots.txt`, externally administered,
domestically restricted, or already closed with no next-cycle
evidence — reported honestly rather than forced into the dataset.

### Researched this pass (Netherlands exhaustive expansion), not integrated

Six further Netherlands universities were researched live and found
genuinely unsuitable — either blocked, stale, or lacking a real
international-facing scholarship — rather than integrated:

- **Vrije Universiteit Amsterdam** — the VU Fellowship Programme (VUFP)
  master's page explicitly ties itself to the already-closed 2025/2026
  application cycle (deadline 1 December 2025, for September 2026
  entry) with no next-cycle info published; its own text confirms this
  ("students... not awarded the VUFP scholarship in 2025/2026 are not
  eligible... for 2026/2027"). VU's Bachelor's scholarships page has
  only the external, Aon-funded, tiny (2 awards), already-enrolled-
  students-only Aon Scholarship — not a VU-administered incoming-
  applicant award.
- **TU Eindhoven** — explicitly states it offers no Bachelor's
  scholarships at all ("TU/e does not offer scholarships for bachelor's
  students"); its one Master's scholarship (Scholarship for Excellence)
  explicitly scopes itself to the already-closed 2026-2027 cycle
  (deadline 1 February 2026) with no 2027-2028 cycle published yet
  ("Conditions and deadlines may differ in future academic years").
- **Leiden University** — `universiteitleiden.nl` returns a genuine
  bot-protection CAPTCHA challenge ("Access Blocked," an F5/Shape-style
  obfuscated JS challenge) on every path tested, including robots.txt
  itself. Per this platform's "never bypass CAPTCHA/bot-protection"
  rule, not circumvented.
- **Erasmus University Rotterdam** — the Erasmus School of Economics'
  Erasmus Trustfonds Scholarship page is explicitly titled and locked to
  the already-closed 2026-2027 cycle (h1 literally reads "Erasmus
  Trustfonds Scholarship 2026-2027," deadline 1 February 2026);
  Rotterdam School of Management's MSc Scholarships page returned only
  navigation/footer text via a plain HTTP fetch, consistent with
  client-side-rendered content not present in the initial HTML response.
- **Radboud University** — the Radboud Scholarship Programme page
  explicitly states "The deadline for 2026-2027 has passed" with no
  2027-2028 cycle information anywhere on the page; the separate Radboud
  Encouragement Scholarship page requires SURFconext login (HTTP 403 for
  anonymous access).
- **Tilburg University** — `tilburguniversity.edu` returns a genuine
  Cloudflare bot-protection challenge ("Just a moment...", HTTP 403) on
  every path tested, including the homepage. Not circumvented.

### Researched previous pass, not integrated

- **EU Marie Skłodowska-Curie Actions (MSCA) Postdoctoral Fellowships**
  — real, official (European Commission), and the "European Postdoctoral
  Fellowships" track is genuinely open to "researchers of any
  nationality." Not integrated this pass: (1) its 2026 call deadline is
  9 September 2026 — only 4 days after this research was conducted — so
  it would need to show as closed almost immediately, with no next cycle
  officially announced yet to point to instead; and (2) unlike this
  platform's other single-flagship sources, the actual application is
  submitted through the separate EU Funding & Tenders Portal rather than
  a page this program's own site controls, which doesn't fit the
  existing `_SingleProgramSource` shape without further design work.
  Worth revisiting once a 2027 call is officially published with more
  runway before its deadline.
- **Vanier Canada Graduate Scholarships** (`vanier.gc.ca`) — its
  eligibility page returned HTTP 503 on two independent fetch attempts
  2026-09-05 (a real server error, not a proxy artifact — confirmed via
  both `curl` and an independent fetch path). Per this platform's
  "do not circumvent access restrictions; record for manual verification
  instead" rule, this was not retried further or worked around. Also
  consistent with this project's existing Canada finding
  (`docs/COUNTRY_PROVIDER_REGISTRY.md`'s "Canada — NOT_SUITABLE"): Vanier
  is nomination-based through Canadian universities' own quotas, not a
  single individually-applicable federal portal.
- **EPFL Excellence Fellowships** (Switzerland) — real program (distinct
  from ETH Zurich's ESOP, #53), but every source found describing a
  current deadline was a third-party aggregator (Scholars4Dev,
  WeMakeScholars, etc.), not EPFL's own site, and the deadlines those
  aggregators cite (December 2025 / March 2026) have already passed as
  of this research date (2026-09-05) with no confirmed 2027 cycle dates
  found on an official EPFL page. Per the "official sources first, never
  infer next year's deadline from an old cycle" rule, this was left
  unintegrated rather than guessed at.

## 79. Mastercard Foundation Scholars Program, graduate/Master's track (Sciences Po)

Researched 2026-09-06, in response to a request to build a France
fully-funded-Master's-only university scholarship dataset. This
platform's **first France university source** — France Excellence
Eiffel and Erasmus Mundus were deliberately kept out of the main dataset
as government/Campus France and externally-administered programmes
respectively, per that request's own explicit instruction (a university
nominating candidates for Eiffel does not make Eiffel a university
scholarship). Its 27th university-classified source overall.

- **Organization**: Sciences Po (in partnership with the Mastercard
  Foundation)
- **Route code**: `sciencespo-mastercard-scholars`
  (`sciencespo_mastercard_scholars` internally)
- **Official domain / base URL**: `https://www.sciencespo.fr`
  (`SCIENCESPO_MASTERCARD_SCHOLARS_BASE_URL`)
- **Opportunity types**: Scholarship — genuinely fully funded, not a
  large stipend: "A comprehensive grant: Scholarships cover the full
  cost of tuition and living expenses in France, throughout the
  recipient's time studying at Sciences Po" (parent hub page), and
  independently, on the page actually scraped, "The Program covers the
  full financial needs of selected Scholars and provides comprehensive
  support throughout their two years of study at Sciences Po." Also
  includes reserved Paris housing. `funding_type = "fully_funded"`.
- **Country coverage / eligibility**: The sole nationality criterion is
  "Hold the citizenship of an African country" (dual citizens holding a
  non-African citizenship are excluded). Sierra Leone is an African
  country and is not excluded by name or by omission from any narrower
  list, so Sierra Leone applicants are eligible on nationality grounds.
  Documented honestly rather than glossed over: applicants must
  *additionally* hold (or be completing) a Bachelor's degree from one of
  the Program's own approved partner universities, or have completed a
  recognised bridge/mentoring programme, or hold UNHCR refugee status —
  this narrows practical eligibility beyond "any Sierra Leonean citizen
  may apply" without excluding the country itself. Only two-year
  Master's programmes qualify for this specific scholarship track;
  one-year Master's and dual-degree programmes are explicitly excluded.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML — a Drupal site, not client-side rendered)
- **robots.txt / indexing note**: `sciencespo.fr/robots.txt` does not
  disallow the `/students/` content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Overview/content page is the graduate-study sub-page**
    (`.../mastercard-foundation-scholarships/graduate-study/`), not the
    parent hub page — it is the one that states the Master's-specific
    eligibility criteria and the explicit full-funding language, and its
    own `<h1>` ("Become a Mastercard Foundation Scholar at graduate
    level") is itself a specific, accurate title.
  - **Content selector is `#main-content-page`**: a stable, semantic
    HTML id (an anchor-scroll target used by the page's own in-page
    navigation), not one of the site's auto-generated CSS-module hash
    classes — verified directly via a BeautifulSoup structural walk to
    hold the full real content (both the funding statement and the
    eligibility section), with only a short, harmless breadcrumb ("Home
    > Fees & Funding > ...") ahead of it.
  - **Deadline deliberately left unextracted**: as of this research date
    the page states plainly that "detailed information and the
    application timeline ... will be published on this page from
    September 2026" and that "applications for the fee waiver will be
    open from October to mid-December 2026" — a real, current
    between-cycles status, but "mid-December 2026" alone carries no day
    number, so no confident date literal exists for
    `extract_confident_date_after` to match on the default `"deadline"`/
    `"closing date"` keywords, correctly resolving to `None` rather than
    guessing a specific December date. The page's one full date literal,
    "17 October 2026", is an information-session/Open House date, not
    the application deadline, and is never reached by the default
    keywords.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/sciencespo_mastercard_scholars.html`).

### Researched this pass (France fully-funded Master's university engine), not integrated

A broad but necessarily non-exhaustive pass across French institutions —
Sciences Po, Université Paris-Saclay (and CentraleSupélec, which shares
its scholarship scheme), Institut Polytechnique de Paris/École
Polytechnique, PSL, Aix-Marseille Université, University of Bordeaux,
Université de Strasbourg, and Télécom Paris — found the strict
"full tuition **and** substantial living support, evidenced by the
university's own words" bar genuinely rare among French university
scholarships for internationals. Rejected, all for concrete,
evidence-based reasons rather than a blanket "not found":

- **Sciences Po — Émile Boutmy Scholarship** — real and well-known, but
  it is explicitly a **tuition-fee exemption only** ("€18,500 exemption
  from tuition fees for each of the two years of the Master's
  programme"), with no living-cost component at all —
  `funding_classification = TUITION_ONLY`, correctly rejected from the
  fully-funded dataset per this pass's own stated rule.
- **France Excellence Eiffel** (French Ministry for Europe and Foreign
  Affairs / Campus France) — real, important, and covers a monthly
  living allowance (reported at €1,200/month from January 2026) plus
  benefits, but it is a **government/Campus France programme**: French
  universities nominate candidates, they do not administer or fund it
  themselves. Kept out of the main France-university dataset per this
  pass's own explicit instruction (`funding_classification =
  EXTERNAL_ONLY`), not fabricated into a university scholarship.
- **Erasmus Mundus Joint Masters** — real, EU-funded, and already a
  separate opportunity source on this platform (#49,
  `erasmus_mundus_joint_masters`), but it is externally administered by
  the European Commission/EACEA across a multi-university consortium,
  not a single French university's own scholarship —
  `funding_classification = EXTERNAL_ONLY` for the purposes of this
  France-university-only dataset.
- **Université Paris-Saclay (and CentraleSupélec, which participates in
  the same scheme) — International Master's Scholarships Program** — a
  real, genuinely useful award (€10,000/year plus up to €900 for travel
  and visa costs, auto-renewing into M2), and Paris-Saclay's own
  materials describe it as covering "both living costs and the majority
  of academic fees" — but that phrasing itself concedes it is not full
  coverage of either component, and it explicitly cannot be combined
  with Eiffel or Erasmus Mundus. `funding_classification =
  PARTIALLY_FUNDED`, rejected per the "€8,000–10,000 tuition/living
  award → reject unless official evidence shows a complete package"
  rule.
- **Institut Polytechnique de Paris / École Polytechnique** — the
  Master's Excellence Scholarship (€10,000/year) and the École
  Polytechnique Foundation scholarship (€8,000/year after the first
  Master's year) are real but explicitly partial relative to published
  tuition (up to €15,400/year for some specializations) and Paris living
  costs — `funding_classification = PARTIALLY_FUNDED`.
- **PSL Université** — the central PSL scholarships/grants page
  describes low, publicly-regulated tuition (€3,700–4,000/year) plus
  scattered merit scholarships awarded at the level of individual PSL
  Graduate Programmes rather than one central, fully-funded PSL-wide
  Master's scheme — no single page found stating full tuition-and-living
  coverage; PSL's genuinely fully-funded tracks are PhD-linked
  (MSc+PhD 5-year tracks), which fall outside this pass's Master's-only
  scope. `funding_classification = UNVERIFIED` / out of scope.
- **Aix-Marseille Université — TIGER Master Excellence Grants** —
  €10,000/year plus guaranteed CROUS-subsidized accommodation, awarded
  automatically on admission to an eligible programme — a strong partial
  package, but Aix-Marseille's own materials do not state it covers the
  *full* cost of tuition and living, only that it substantially
  contributes toward both. `funding_classification = PARTIALLY_FUNDED`.
- **University of Bordeaux** — its only prominently documented
  international-student funding routes are Eiffel (`EXTERNAL_ONLY`,
  excluded per the rule above) and a joint Erasmus Mundus programme with
  Bayreuth/Porto (`EXTERNAL_ONLY`); no Bordeaux-administered
  fully-funded Master's scholarship was found.
- **Télécom Paris** — its "International Excellence" scholarship is
  restricted to students already recruited through Télécom Paris' own
  international-recruitment activities (not an open, generally
  applicable award), and its other funding route referenced by
  aggregators is Eiffel itself (`EXTERNAL_ONLY`).

## 80. Peking University Scholarship for International Students

Researched 2026-09-06, in response to a request to build a China
fully-funded Master's university scholarship engine — this platform's
first China *university* source (Schwarzman Scholars and Yenching
Academy, sources #50 and #52, are elite named programmes hosted at
Tsinghua/PKU respectively, not this general institution-wide
scholarship open to PKU's whole international-applicant pool).

- **Organization**: Peking University (International Students Division,
  Office of International Relations)
- **Route code**: `pku-international-scholarship`
  (`pku_international_scholarship` internally)
- **Official domain / base URL**: `https://isd.pku.edu.cn`
  (`PKU_INTERNATIONAL_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — "It covers tuition, a living
  stipend and medical insurance," for undergraduate (4 years), Master's
  (2-3 years), or doctoral (4 years) students. `funding_type =
  "fully_funded"`.
- **Country coverage / eligibility**: No nationality/country
  restriction stated anywhere — eligibility is framed only around PKU's
  own international-admission requirements and not already holding
  another scholarship — Sierra Leone applicants are eligible.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML — a plain, old-style institutional page with no
  JavaScript rendering needed)
- **robots.txt / indexing note**: `isd.pku.edu.cn/robots.txt` returns
  this site's own custom-styled 404 page, not a robots.txt — no
  `Disallow` rules exist for this host.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **`title_selectors = ()`, `title_tag_separator = " | "`**: the page
    has no `<h1>` at all — a separator absent from the real `<title>`
    text ("Peking University Scholarship for International Students")
    is used so the split is a no-op and the already-clean title tag
    text is used directly, rather than falling through to a less
    precise external_id-derived fallback.
  - **Content selector `div.article-cont`**: verified directly via a
    BeautifulSoup structural walk to hold exactly the real scholarship
    text (scope, duration, eligibility, application process), with none
    of the page's surrounding navigation sidebar.
  - Deliberately extracts no deadline: the page states "Application
    Time: Generally in January and March each year" — a real, recurring
    annual window with no year attached, verified directly with a
    standalone script that neither the default `"deadline"` keyword nor
    an `"Application Time"` keyword resolves to a date.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/pku_international_scholarship.html`).

## 81. Shanghai Jiao Tong University — Master's SJTU Scholarship

Researched 2026-09-06, same pass — this platform's second China
*university* source.

- **Organization**: Shanghai Jiao Tong University
- **Route code**: `shanghai-jiao-tong-university-masters-scholarship`
  (`sjtu_masters_scholarship` internally)
- **Official domain / base URL**: `https://global.sjtu.edu.cn`
  (`SJTU_MASTERS_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — "Master's SJTU Scholarship
  includes Monthly stipend, standard tuition waiver, group
  comprehensive insurance in China, and accommodation subsidy (covering
  partial accommodation expenses)." `funding_type = "fully_funded"`.
  Deliberately distinct from, and not to be confused with, the same
  page's separately-named "Tuition Waiver Scholarship" (tuition +
  insurance only, no stipend — not integrated as its own record).
- **Country coverage / eligibility**: No nationality/country
  restriction stated anywhere — the whole hub page is framed under
  "Prospective International Students" with an application portal
  literally named "Foreign Students Apply" — Sierra Leone applicants
  are eligible.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML, tab/accordion layout)
- **robots.txt / indexing note**: `global.sjtu.edu.cn/robots.txt`
  returns a generic 404 page, not a robots.txt — no `Disallow` rules
  exist for this host.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Overview page is a general prospective-students hub**
    (`Study@SJTU`), covering undergraduate, graduate, and non-degree
    programmes on one page — not itself rejected as a multi-record hub
    (unlike ESMT/WHU/Universidad de Navarra elsewhere in this project),
    because the specific scholarship recorded here is precisely,
    separately described within one identifiable tab panel, distinct
    from the Undergraduate programmes' own separately-tiered
    scholarship scheme in a sibling panel on the same page.
  - **Content selector `div.page-item + div.page-item`** (an
    adjacent-sibling CSS selector, not a hash class): the page has
    exactly two `div.page-item` tab panels — "Undergraduate Programs"
    and "Graduate Programs" — verified directly via a BeautifulSoup
    structural walk; the sibling-combinator selector deliberately
    targets the second (Graduate Programs) panel, which holds both the
    PhD and Master's SJTU Scholarship descriptions, without pulling in
    the Undergraduate panel's unrelated tiered-scholarship text.
  - **`title_selectors = ()`, no `title_tag_separator`**: the page's own
    `<title>` ("Study@SJTU - Shanghai Jiao Tong University") describes
    the whole hub, not this specific scholarship, so it is deliberately
    not used — falls through to the external_id-derived fallback
    ("Shanghai Jiao Tong University Masters Scholarship"), the same
    documented pattern already used for WMI/Yenching/HKPFS/Max Planck
    Schools elsewhere in this file. `external_id` spells the
    university's name out in full (rather than the common "SJTU"
    abbreviation) specifically so that fallback title-cases cleanly,
    rather than producing "Sjtu".
  - Deliberately extracts no deadline: this panel states no deadline or
    application-window date at all — verified directly that neither the
    default `"deadline"` keyword nor a `"March"` keyword matches
    anything on the full page text.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/sjtu_masters_scholarship.html`).

### Researched this pass (China fully-funded Master's university engine), not integrated

A necessarily non-exhaustive first pass across major Chinese
universities — Peking University, Tsinghua University, Fudan
University, Shanghai Jiao Tong University, and Zhejiang University —
found that most Chinese universities channel international Master's
funding primarily through the Chinese Government Scholarship (CGS/CSC)
and provincial/municipal government scholarships (Beijing, Shanghai,
Zhejiang, etc.) rather than running their own comprehensive,
university-only fully-funded Master's scheme. Per this pass's own
explicit instruction, CGS and other government/CSC routes are
deliberately kept out of this platform's university-classified dataset
even where a university administers the application, since the funding
provider is the Chinese government, not the university itself:

- **Tsinghua University** — its own "Financial Aid System" page
  explicitly distinguishes CGS (government-funded, full or partial)
  from its own "Tuition Scholarships" (Beijing Government Scholarship
  and the Tsinghua University Tuition Scholarship), which the page
  itself states "cover full or partial tuition fees" only — no living
  stipend component — `TUITION_ONLY`/`PARTIALLY_FUNDED` for the
  university's own (non-CGS) offering, correctly not classified as
  fully funded.
- **Zhejiang University** — its "Master's Scholarships" page is a hub
  listing CGS Type A/B, CGS Youth of Excellence Scheme, the Zhejiang
  (provincial) Government Scholarship, a China-ASEAN scholarship, and
  two school-specific awards (ZIBS Hai Scholarship, ISM Freshman
  Scholarship) — the same multi-record architecture mismatch documented
  for ESMT/WHU/Universidad de Navarra elsewhere in this project, and
  most individual pages carry dated 2022 URLs suggesting stale,
  non-evergreen content. Not integrated as a single record; no
  standalone "Zhejiang University Scholarship" package distinct from
  CGS/provincial funding was found.
- **Fudan University** — its International Students Office primarily
  channels applicants toward CGS, the Shanghai Government Scholarship,
  and the Confucius Institute Scholarship; no standalone,
  university-funded "Fudan University Scholarship" page comparable to
  PKU's or SJTU's own was found.
- **SJTU's own Tuition Waiver Scholarship** (the sibling scheme to the
  Master's SJTU Scholarship actually integrated above) — "standard
  tuition waiver and group comprehensive insurance in China" only, no
  monthly stipend — `TUITION_ONLY`, correctly not classified as fully
  funded and not integrated as its own record.

**(2026-09-06, continuation pass)** The same request was resubmitted
asking for continued search. Six further Chinese universities were
researched live and found genuinely unsuitable rather than integrated,
none for the same reason twice:

- **Nanjing University** — its central "Scholarships" page (English
  site) auto-redirects via inline JavaScript straight to the Chinese
  Government Scholarship page, and the only other listed options are
  the Nanjing Municipal Scholarship (municipal government), the
  International Chinese Language Teachers Scholarship (Confucius
  Institute-specific, not a general Master's route), and the Confucius
  China Studies Program (China-studies research fellowship) — no
  standalone NJU-funded Master's scheme exists at all, confirmed by
  reading the university's own scholarship menu directly rather than a
  third-party summary.
- **University of Science and Technology of China (USTC)** — its
  international admissions site (`isa.ustc.edu.cn`) is genuinely stale:
  its own "Scholarship" detail page is titled "2020 USTC Scholarship
  Program" (last updated 2017-04-10, application deadline "March 31,
  2020"), and its Notice board's most recent scholarship-relevant post
  is a "2022 USTC 'Chinese Government Scholarship – Chinese University
  Program'" announcement — no 2023-2027 content of any kind was found
  anywhere on the site. Per this project's "never present stale content
  as current" rule, not integrated regardless of how the 2020-era page
  itself described the funding package.
- **Wuhan University** — every scholarship route found (live search,
  not the university's own page directly, since no standalone WHU-
  funded page turned up) is Chinese Government Scholarship-branded;
  no distinct Wuhan University-funded Master's scheme was found.
- **Sun Yat-sen University** — a genuinely real, distinct,
  university-funded scheme (First/Second/Third-Class tiers, tuition
  waiver plus a living allowance up to RMB 30,000/year for the top
  tier, explicitly *not* combinable with CGS/CLEC funding, so a real
  non-government alternative in spirit) — but its own official page's
  `<h1>` reads, verbatim, "CLOSED | 2026 Guidelines for the Application
  of Scholarship for International Students at Sun Yat-sen University."
  No "2027," "next cycle," or forward-looking language of any kind
  appears anywhere on the page (confirmed by a direct text search) —
  unlike University of Twente's ITC Excellence Scholarship (which
  states "a possible next round is expected to open in December"),
  this page gives no evidence a next cycle is coming, so per the "never
  guess a future cycle from a stale prior one" rule, not integrated. A
  strong candidate to re-check in a future pass once a 2027 cycle is
  published.
- **Renmin University of China** — a live search found only ambiguous,
  tiered "tuition scholarships" described as covering "full tuition or
  partial tuition, or a tuition refund," plus small named merit awards
  (Academic Performance/Progress/Social Activity/Leadership) with no
  living-stipend component described — `UNVERIFIED`/`PARTIALLY_FUNDED`
  in spirit; the official page itself was not fetched directly since
  the available evidence already read as insufficiently comprehensive
  to warrant it.
- **Xi'an Jiaotong University — Siyuan International Student
  Scholarship** — a real, named, university-funded scheme (tiered
  monthly stipends up to RMB 3,500/month for Master's students,
  distinct from CGS) discovered via live search, but its own detail
  page (`sie.xjtu.edu.cn`) returned a genuine, active JavaScript
  anti-bot challenge on direct fetch — a "网站正在加载中..." ("website
  is loading...") interstitial that fingerprints the browser
  (`navigator.webdriver`/PhantomJS detection), computes a challenge
  hash, and POSTs it to a `/dynamic_challenge` endpoint before
  redirecting — the same class of active bot-protection already
  documented for China's own CSC portal, Cyprus, and Brazil elsewhere
  in this project. Per this project's "never bypass CAPTCHA/anti-bot
  protection" rule, not circumvented; recorded as `BLOCKED`, not
  pursued further.

No new source was added this continuation pass — per this project's
own "accuracy over quantity" standard, a genuine second round of
research that finds no qualifying candidate is itself the correct,
honest outcome, not a gap to paper over.

## 82. McGill University — Mastercard Foundation Scholars Program

Researched 2026-09-06, in response to a request for another fully
funded Master's scholarship in Canada — this platform's **first Canada
source of any kind**. Canada was previously found `NOT_SUITABLE` at the
national/government level (EduCanada's Study in Canada Scholarships is
confirmed institution-initiated, not individually-applicable — see
`docs/COUNTRY_PROVIDER_REGISTRY.md`'s "Canada — NOT_SUITABLE" finding,
which remains correct and unaffected); this is a university-
administered source instead, the same partnership pattern already used
for Sciences Po's own Mastercard Foundation Scholars Program (source
#79).

- **Organization**: McGill University (in partnership with the
  Mastercard Foundation)
- **Route code**: `mcgill-mastercard-scholars`
  (`mcgill_mastercard_scholars` internally)
- **Official domain / base URL**: `https://www.mcgill.ca`
  (`MCGILL_MASTERCARD_SCHOLARS_BASE_URL`)
- **Opportunity types**: Scholarship — "The scholarship includes: ...
  Full international student tuition, On-campus housing, Personal
  monthly stipend ..., Academic tools and resources (book allowance,
  laptop, tutoring, etc.), ... Post-graduation transition expenses (ex.
  ... return flight, etc.)" — full tuition plus substantial living/
  housing support plus several additional benefits. `funding_type =
  "fully_funded"`.
- **Country coverage / eligibility**: The *separate* Eligibility page
  (`/mastercardfdn-scholars/apply/eligibility`, not itself scraped for
  this record) states "Be a citizen of and live in an African country"
  and lists an explicit ~54-country "Eligible Countries" table that
  names **Sierra Leone** directly — confirmed by fetching that page
  live during research. Limited to 13 named graduate programmes
  (nutrition, public health, public policy, sustainable agriculture)
  and a first Master's degree only ("Have NEVER registered for, nor
  completed a master's degree") — documented honestly as a real scope
  constraint rather than implying university-wide eligibility.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML — a Drupal site)
- **robots.txt / indexing note**: `mcgill.ca/robots.txt` sets
  `Crawl-delay: 5` for `User-agent: *` and does not disallow this
  content path — `min_request_interval_seconds` is set to 5.0 to match
  that Crawl-delay exactly, more conservative than this project's usual
  2.0s default.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Overview/content page is the "About" page**, not the separate
    "Eligibility" page — it is the one stating the full funding
    package. Content selector `div.field-name-body`: a stable, semantic
    Drupal field class, verified directly via a BeautifulSoup
    structural walk to hold exactly the real article content, with none
    of the surrounding navigation.
  - **`title_tag_separator = " - McGill University"`**: the raw
    `<title>` ("About the Program | Mastercard Foundation Scholars
    Program at McGill University - McGill University") has two
    site-name fragments; splitting on the fuller, more specific one
    (rather than the more common `" | "` separator, which would leave
    just the vague "About the Program") produces a properly descriptive
    title.
  - Deliberately extracts no deadline: this page states none. (A
    separate "Information Sessions" page, also not scraped for this
    record, shows the Fall 2027 cycle's own sessions already concluded
    as of this research date — a real, current between-cycles status
    for a genuinely recurring annual program, the same category as
    University of Twente's ITC Excellence Scholarship elsewhere in this
    file, not a defunct or fabricated one.)
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/mcgill_mastercard_scholars.html`).

### Researched this pass (Canada fully-funded Master's follow-up), not integrated

A pass across five major Canadian research universities — Calgary,
Alberta, Waterloo, Toronto, and McGill (in addition to the scholarship
actually integrated above) — found that Canadian research universities
almost universally structure graduate funding as a guaranteed *stipend*
(via a combination of scholarships, teaching assistantships, and
research assistantships), not a full tuition waiver, for international
Master's students — a structurally different pattern from the
tuition-waiver-plus-stipend model common at Chinese, Dutch, and French
universities documented elsewhere in this project:

- **University of Calgary** — thesis-based MA/MSc students receive a
  guaranteed "minimum funding package" of $25,455/year for
  international students, plus a separate, much smaller "International
  Graduate Tuition Award" (~$3,060/year total). Neither the funding
  package's own page nor any linked page states that the $25,455 figure
  itself goes toward tuition, and the separate tuition award is a small
  fraction of typical international graduate tuition — `PARTIALLY_
  FUNDED` (a real, generous stipend, but not a full-tuition package).
- **University of Alberta** — thesis-based programmes advertise minimum
  funding packages of $19,000–$28,000/year (a combination of
  assistantships and department scholarships), while international
  graduate tuition is separately quoted at $9,000–$18,000/year — no
  official page found stating the funding package is inclusive of or
  additional to that tuition amount — `UNVERIFIED`/`PARTIALLY_FUNDED`.
- **University of Waterloo** — its own International Student Funding
  page states plainly that Waterloo "does not offer full-ride
  scholarships that cover all tuition and living costs"; its
  International Master's Award of Excellence is $2,500/term (a
  supplementary award, not a comprehensive package) — `PARTIALLY_
  FUNDED`, confirmed by the university's own negative statement rather
  than inferred.
- **University of Toronto** — funding packages are set per graduate
  unit/department (e.g., a base stipend plus tuition coverage in some
  units, base stipend only in others) rather than one central,
  university-wide, evergreen scholarship page fitting this project's
  single-flagship-source pattern — no single record integrated.
- **University of British Columbia** — its International Tuition Award
  is explicitly small (~$3,200/year) and only for students already
  registered in a research-based graduate programme, not a comprehensive
  entrance scholarship — `PARTIALLY_FUNDED`.
- **McCall MacBain Scholarship** (also hosted at McGill, via an
  independent foundation rather than McGill itself administering
  eligibility/selection) — genuinely comprehensive (full tuition +
  fees + a CAD 2,300/month stipend + relocation grant), and ten seats
  are reserved for applicants from outside Canada/the US, but McGill's
  own page for it lives under `/gradapplicants/funding/**external**/
  mccall-macbain-scholarship` — McGill's own site classifies it as an
  *external* scholarship it merely lists, not one it administers
  end-to-end the way it does the Mastercard Foundation Scholars
  Program — left as a candidate for a future *external*-classified
  source rather than integrated into the university-administered
  dataset here.

## 83. Gates Cambridge Scholarship (University of Cambridge / Gates Cambridge Trust)

Researched 2026-09-06, in response to a request to build an England
fully-funded Master's university scholarship engine — this platform's
**first England source classified as genuinely fully funded**. The
nine pre-existing England sources (Imperial Inspires, Newcastle VC
International, Sheffield PG, Manchester Global Futures, Nottingham PG,
Southampton's Presidential Bursaries and Merit Undergraduate
Scholarship, Durham's Inspiring Excellence UG and PG) are all
`partial_funding`.

- **Organization**: Gates Cambridge Trust, a body established at the
  University of Cambridge by a 2000 donation from the Gates Foundation
- **Route code**: `gates-cambridge-scholarship`
  (`gates_cambridge_scholarship` internally)
- **Official domain / base URL**: `https://www.gatescambridge.org`
  (`GATES_CAMBRIDGE_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — "A Gates Cambridge Scholarship
  covers the full cost of studying at Cambridge," itemized as the
  University Composition Fee (tuition), a maintenance allowance (GBP
  22,050 for 12 months at the 2025-26 rate, pro rata for shorter
  courses), one economy return airfare, and inbound visa costs plus the
  Immigration Health Surcharge. `funding_type = "fully_funded"`,
  comfortably exceeding the minimum tuition-plus-substantial-living
  bar.
- **Country coverage / eligibility**: From the separate `/apply/
  eligibility/` page (confirmed live, not itself scraped for this
  record): "a citizen of any country outside the United Kingdom" — no
  narrower list at all, worldwide eligibility, Sierra Leone included.
  Funds "PhD ... MLitt ... [or a] one-year postgraduate course," with a
  named exceptions list (MASt, part-time degrees other than the PhD,
  MBA/EMBA/MFin and other professional-development courses, PGCE,
  medical degrees) that does not exclude the standard one-year taught/
  research Master's route (e.g. MPhil) — genuinely Master's-eligible,
  not PhD-only.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML — a WordPress site)
- **robots.txt / indexing note**: `gatescambridge.org/robots.txt` only
  disallows `/wp-admin/`, unrelated to this content path.
- **API / RSS / Sitemap**: A general sitemap exists (`sitemap.xml`);
  no dedicated funding/scholarship API
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Overview/content page is `/programme/the-scholarship/`**, not
    the separate `/apply/eligibility/` or `/apply/timeline/` pages — it
    is the one stating the full funding package. Content selector
    `section#funding`: a stable, semantic HTML id, verified directly
    via a BeautifulSoup structural walk to hold exactly the funding
    section (Core components, Discretionary components, "What is not
    covered?"), with none of the page's general programme description
    or surrounding navigation.
  - **`title_selectors = ()`, no `title_tag_separator`**: this page's
    own `<h1>` ("The Scholarship") and `<title>` ("Postgraduate
    Cambridge University Scholarship | Gates Cambridge") are both too
    generic to serve as a specific scholarship title on their own —
    falls through to the external_id-derived fallback ("Gates Cambridge
    Scholarship"), the scholarship's own well-known name, the same
    documented pattern already used for WMI/Yenching/HKPFS/Max Planck
    Schools/SJTU elsewhere in this file.
  - Deliberately extracts no deadline: the funding page itself states
    no dates at all (verified directly). The separate Timeline page
    does have real, current 2026/27-cycle dates, but deliberately was
    not used as a deadline source: it lists three different deadlines
    depending on applicant category and course (a US-citizens-
    resident-in-the-US round closing 14 October 2026, and an "all other
    eligible applicants" round closing either 8 December 2026 or 6
    January 2027 depending on the specific course) — there is no single
    canonical date a generic keyword could correctly resolve to, and
    naively taking the first date literal on that page would surface
    the narrow US-only round's deadline as if it applied to every
    applicant, misleading far more readers (including Sierra Leonean
    applicants) than it would help.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/gates_cambridge_scholarship.html`).

### Researched this pass (England fully-funded Master's university engine), not integrated

- **Oxford — Clarendon Fund** — official evidence (confirmed via live
  search summaries of Oxford's own page) shows it is a genuinely
  strong candidate: full course-fee coverage plus a living grant, no
  nationality restriction, automatic consideration for any Master's or
  DPhil applicant who applies by the relevant December/January
  deadline. However, `ox.ac.uk` — every path tested directly, including
  the specific Clarendon page itself and even `robots.txt` — returns an
  active Cloudflare "Just a moment..." managed challenge (a JavaScript
  browser-verification interstitial, HTTP 403). Per this project's
  "never bypass CAPTCHA/anti-bot protection" rule, not circumvented.
  This is a funding-independent access blocker, not a rejection of the
  scholarship itself — Clarendon should be reconsidered in a future
  pass if Oxford ever narrows or removes that challenge.

### Researched this pass (Netherlands fully-funded Master's university engine, continuation), not integrated

The Netherlands fully-funded-only mega-prompt was resubmitted after
three genuinely fully-funded Dutch university sources already existed
(TU Delft's Van Effen Scholarship #58, Groningen's Eric Bleumink
Fellowship #72, Maastricht's High Potential Scholarship #74 — confirmed
by direct source-code inspection before starting, not assumed) and
seven partial ones (Nuffic, UvA Master's/Bachelor's, Utrecht LEGITS,
UTwente's UTS and ITC, Wageningen's Anne van den Ban Fund). A further
live pass found no new qualifying candidate, for four distinct reasons:

- **TU Delft** — searched specifically for other MSc scholarships
  beyond Van Effen (already integrated); the only other named
  full-scholarship route found was the Fulbright Scholarship, which is
  US-government-funded and restricted to the Faculty of Industrial
  Design Engineering — `EXTERNAL_ONLY`, not a TU Delft-administered
  scheme.
- **University of Twente's scholarship finder** — fetched the full
  finder listing directly (22 named schemes) and checked the three
  that looked most likely to be UTwente-administered rather than
  merely listed external funders: the **Kipaji Scholarship** (up to
  EUR 12,000) and the **Professor De Winter Scholarship** (EUR 10,000)
  are both explicitly *dependent add-ons* — their own pages state they
  are "meant as additional support for UTS scholarship students" and
  cannot be applied for independently, with no official statement that
  UTS-plus-add-on together constitute full funding — per the "do not
  pretend combined awards form one full scholarship without official
  confirmation" rule, not integrated as fully funded. The **STEM for
  ALL scholarship** is a small (EUR 5,000), externally-funded (Thales
  Solidarity Charitable Fund) award primarily aimed at Bachelor's-level
  applicants — `PARTIAL_TUITION_ONLY`/`EXTERNAL_ONLY`.
- **Radboud University — Radboud Encouragement Scholarship** — the
  most interesting finding of this pass. Radboud's own scholarships hub
  page (`ru.nl/en/education/scholarships`) exposes a filter facet
  confirming exactly one of its listed scholarships is tagged "Full
  scholarship" by the university's own classification system (the
  other five scholarship-type results are tagged "Partial scholarship")
  — and live search results independently identify that one as the
  Radboud Encouragement Scholarship, described as covering "the full
  tuition fee and living costs ... for the duration of the Master's
  programme," open to non-EU/EEA applicants across multiple faculties.
  However, fetching the specific detail page directly
  (`ru.nl/en/education/scholarships/radboud-encouragement-scholarship`)
  returned HTTP 403 with the page's own `<title>` reading "Login |
  Radboud University" and body text "Log in to view this content" (a
  SURFconext institutional login wall) — genuinely different from the
  general scholarships hub page, which remains publicly readable. Per
  this project's "never bypass authentication barriers" rule, not
  circumvented. Left unintegrated as `VERIFICATION_REQUIRED` due to an
  access barrier, not a funding classification failure — a strong
  candidate to re-check if Radboud ever exposes this specific page
  publicly, or via an official PDF/handbook copy of its terms.
- **Erasmus University Rotterdam — Joint Japan/World Bank Graduate
  Scholarship Program (JJ/WBGSP) at ISS** — genuinely fully funded
  (full tuition, living allowance, travel, health insurance) for the
  Master in Development Studies at Erasmus's International Institute
  of Social Studies, but this is the same World Bank-funded,
  Japan-government-financed programme already on this platform as
  source #45 (`world_bank_jjwbgsp`), which funds 44 participating
  programmes across 24 universities worldwide and is correctly
  government/multilateral-classified rather than tied to any single
  host university — not re-integrated as a separate Erasmus-specific
  record, since doing so would double-count an existing source under a
  different institutional label.

No new source was added this continuation pass — per this project's
own "accuracy over quantity, do not pad the database" standard
(explicit in this pass's own section 39), a genuine second round of
research that finds no qualifying candidate — while still surfacing a
real, credible lead (Radboud Encouragement Scholarship) blocked purely
by an access barrier rather than a funding shortfall — is itself the
correct, complete outcome to report.

## 84. Heinrich Böll Foundation ("Tailwind for Talents") Scholarship for Graduates and PhD students

Researched 2026-09-06, in response to an open-scope "find another
scholarship opportunities in germany" request — unlike the recent
country mega-prompts, this stated no degree-level or funding-type
restriction, so the research pass considered any genuinely new,
verifiable German opportunity rather than only fully-funded Master's
candidates. This platform's second **Foundation**-classified source
(Humboldt Research Fellowship, #56, is the first) and its third
Germany source of any kind alongside DAAD (#10, government) and the
university sources TUM (#59) and Freiburg (#69).

- **Organization**: Heinrich Böll Foundation (Heinrich-Böll-Stiftung) —
  a political foundation affiliated with Alliance 90/The Greens,
  legally independent of government even though its international-
  student track is financed by the Federal Ministry of Research,
  Technology and Space (BMFTR) and the Federal Foreign Office (AA);
  the foundation itself runs the selection and payout, not a government
  agency, matching this project's "classify by who actually
  administers it" rule already applied to Humboldt and to DAAD's KAS
  addition.
- **Route code**: `heinrich-boll-scholarship`
  (`heinrich_boll_scholarship` internally)
- **Official domain / base URL**: `https://www.boell.de`
  (`HEINRICH_BOLL_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — covers both a Master's/graduate
  track and a PhD track on the same overview page (like Freiburg's
  Deutschlandstipendium, #69, covering both undergraduate and Master's
  on one page). For the Federal-Foreign-Office-funded, non-EU
  international-student Master's track (verified on the foundation's
  own separate "Financial support" page, confirmed live but not itself
  scraped for this record, since the overview page's own content is
  sufficient and more stable): a base scholarship of EUR 992/month, a
  health-insurance allowance of up to EUR 100/month, reimbursement of
  German tuition fees up to EUR 10,000/year (covering the same
  Baden-Württemberg non-EU-tuition exception already documented for
  DAAD's KAS entry), a EUR 38/month fixed fringe-benefit allowance, and
  family/child allowances where applicable — genuinely fully funded.
  `funding_type = "fully_funded"`.
- **Country coverage / eligibility**: "we support graduate students and
  PhD students from DAC countries who intend to pursue a Master's
  degree or PhD in Germany," with priority to applicants from DAC
  (OECD Development Assistance Committee) countries who have "not yet
  taken up residence in Germany at the time of their application" —
  Sierra Leone is a DAC-listed Least Developed Country, so it is
  covered, not merely un-excluded. Genuinely open to **prospective**
  applicants, not only those already enrolled in Germany: the
  foundation's separate application-process page (confirmed live but
  not itself scraped) states the certificate of enrollment/admission
  "may be submitted at a later point, but no later than the interview"
  — the opposite of this platform's earlier Friedrich-Ebert-Stiftung
  research finding (documented above under DAAD, #10), which required
  applicants to *already* be enrolled in Germany and was left
  unintegrated for exactly that reason. Documented plainly rather than
  glossed over: international applicants must separately demonstrate
  German-language proficiency of at least B2 level or DSH1 (stated on
  the foundation's application page, not itself scraped) — a language
  requirement, not a nationality restriction; it does not exclude
  Sierra Leone.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered Drupal HTML, no JavaScript execution needed)
- **robots.txt / indexing note**: `boell.de/robots.txt` (a Drupal
  default) disallows only CMS-internal paths (`/core/`, `/profiles/`,
  `/admin/`, `/user/login`, etc.) — none of which cover `/en/
  scholarships`.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Overview page is `/en/scholarships`, deliberately not the
    separate `/en/applying-scholarship` page**: both official pages
    describe the same programme, but `/en/applying-scholarship`'s own
    "graduate scholarship" section still displays an already-passed
    "Fall 2026: 15 July 2026 until 1 September 2026" cycle as current
    — a real content-freshness lag on that specific page, confirmed by
    fetching both pages live on the same research date — while `/en/
    scholarships` correctly lists only genuinely future cycles
    ("Spring 2027" and "Fall 2027"). Chose the current page over the
    stale one, per this project's "no stale-cycle guessing" rule.
  - **Content selector `div.node__content`**: a stable Drupal content
    wrapper, verified directly via a BeautifulSoup structural walk to
    hold the programme description, the current deadlines, and the
    "Who can apply?" eligibility text in one clean ~2KB block, with
    none of the page's navigation or footer chrome.
  - **`deadline_keywords` deliberately overridden to `("until",)`,
    skipping the base class's default `("deadline", "closing date")`
    entirely**: the page's own deadline text reads "Our next
    application deadlines: Spring 2027: 15 January 2027 until 1 March
    2027 Fall 2027: ...". A case-insensitive search for "deadline"
    matches inside "deadlines" first, and the nearest date literal
    after that point is 15 January 2027 — the application-*window-
    opening* date, not the deadline. Anchoring on "until" instead
    correctly lands on the first *closing* date, 1 March 2027,
    immediately following it — verified directly against the live
    fixture before writing the test.
- **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/heinrich_boll_scholarship.html`).

### Researched this pass (2026-09-06, general "another Germany scholarship" follow-up), not integrated

An open-scope pass (not restricted to Master's or to fully funded)
checked five further German political-foundation and university
candidates live before settling on Heinrich Böll above, and found a
consistent, genuine access barrier common to most of them:

- **Friedrich Naumann Foundation for Freedom (`freiheit.org`) —
  Scholarships for foreign students** — its own page requires the
  applicant to "still have two remaining semesters" of study left at
  the time of funding, i.e. already enrolled at a German university,
  not a prospective applicant — `ALREADY_ENROLLED`, the same pattern
  already documented for Friedrich-Ebert-Stiftung above. Application
  materials and the selection interview must also be conducted in
  German.
- **Rosa Luxemburg Foundation (`rosalux.de`) — scholarship for
  international students** — explicitly requires "[e]nrollment at a
  state or state-recognised university in Germany" as a formal
  eligibility condition, and caps applications to within 15 months of
  first arriving in Germany — `ALREADY_ENROLLED`, not a scholarship a
  prospective Sierra Leonean applicant abroad could use to fund initial
  admission.
- **Hanns Seidel Foundation (`hss.de`) — international scholarships** —
  a real, genuinely prospective-applicant-friendly programme in
  principle (proof of enrollment/admission letter accepted "no later
  than the time of the interview," the same pattern as Heinrich Böll),
  but its own published application process is explicitly routed
  through country-specific national HSF offices (India, Pakistan,
  Vietnam, Myanmar, Jordan, and others found live) with no office, page,
  or stated process found covering Sierra Leone or West Africa more
  broadly — a genuine, undocumented access gap rather than a funding or
  nationality exclusion, left unintegrated as `VERIFICATION_REQUIRED`
  rather than assumed accessible.
- **Universität Hamburg — Merit Scholarships** (also listed on DAAD's
  database) — its own eligibility rule requires the applicant to have
  "been enrolled at Universität Hamburg for at least 1 semester" before
  applying — `ALREADY_ENROLLED`, architecturally the same
  already-enrolled-retention-grant shape as this platform's existing
  TUM International Student Scholarship (#59), not a new kind of
  coverage.
- **Technical University of Berlin (TU Berlin)** — no single official
  TU-Berlin-administered flagship scholarship page was found; every
  aggregator result pointed back to DAAD's own Study Scholarship and
  EPOS programmes (both already covered by this platform's existing
  DAAD source, #10) or to unrelated political-foundation scholarships,
  not a distinct TU Berlin-run scheme.

### Researched this pass (2026-09-07, Eswatini — five-country autonomous engine), not integrated

Part of a simultaneous five-country research pass (Austria, Eswatini,
Australia, USA, Russia). Eswatini was researched as a scholarship
*study destination* (i.e. genuine opportunities for an international
applicant, such as one from Sierra Leone, to study *at* an Eswatini
institution) — not to be confused with this platform's existing
Eswatini SLAS source (#18), which is the reverse: a domestic
Eswatini-government loan/scholarship for **Eswatini nationals** to
study locally or in the SADC region, already correctly classified
`NOT_SUITABLE` for that reason. Checked every accredited Eswatini
higher-education institution named in the research brief, live,
finding no qualifying inbound scholarship at any of them:

- **University of Eswatini (UNESWA)** — genuinely inaccessible from
  this environment, and for a reason distinct from every other access
  barrier documented elsewhere in this file: `https://www.uneswa.ac.sz`
  fails TLS negotiation with "SSL certificate problem: unable to get
  local issuer certificate" (confirmed via a verbose TLS handshake
  trace — the server presents an incomplete certificate chain, missing
  its intermediate CA) — a genuine misconfiguration on the university's
  own server, not a proxy artifact (plain `http://` to the same host
  succeeds and 301-redirects to the broken `https://` URL) and not a
  bot-block. Per this project's absolute rule against disabling
  certificate verification (that would create a real
  man-in-the-middle-vulnerable code path — an OWASP-class security
  regression), not bypassed with `-k`/`verify=False`. A second,
  independent fetch attempt via a different tool (`WebFetch`) also
  failed (HTTP 503), consistent with a genuinely unreliable server
  rather than an environment-specific block. Left unintegrated as
  `VERIFICATION_REQUIRED` — a real institution with real content that
  cannot currently be safely reached.
- **Southern Africa Nazarene University (SANU)** — fully reachable
  (`www.sanu.ac.sz`, no robots.txt restriction), with a dedicated
  `/scholarship-information/` page located via its own sitemap. Read
  directly: the page states plainly "It is the student's responsibility
  to look for educational funding, ... International students undergo
  the application process like all prospective students and **seek for
  their funding**" — an explicit self-funding disclaimer, not a
  scholarship offer. SANU does not administer its own scholarship
  programme for international students; not fabricated into one.
- **Eswatini Medical Christian University (EMCU)** — reachable
  (`emcu.ac.sz`, redirects cleanly from `www.`, no robots.txt
  restriction), but its own homepage's only funding-related link is a
  "Government Scholarship Application" pointing to `slas.gov.sz` — the
  same domestic/SADC-only government programme already on this
  platform as source #18, not a distinct EMCU-administered scholarship.
- **Limkokwing University of Creative Technology (Eswatini campus)** —
  `limkokwing.net` returns an active Cloudflare managed challenge
  ("Just a moment...", HTTP 403 on every path including `robots.txt`)
  — genuine bot protection, not circumvented, per this project's
  standing rule.
- **Eswatini government scholarship apparatus more broadly** — live
  search confirms the Ministry of Labour and Social Security's SLAS
  programme (#18) and the Ministry of Foreign Affairs' international
  scholarship listings are both outbound programmes *for Eswatini
  nationals* studying elsewhere, not inbound programmes for
  international students to study in Eswatini. No government-run
  inbound international scholarship was found.

No new source was added for Eswatini this pass. Per this project's own
explicit "never invent opportunities to make the country look
complete" instruction for this exact scenario, the honest result — a
real institution blocked by its own broken TLS configuration, one
institution with an explicit no-scholarship disclaimer, one
institution merely redirecting to an already-covered government
programme, and one institution genuinely bot-protected — is reported
as-is rather than padded.

## 85. Helmut Veith Stipend (TU Wien, via the Vienna Center for Logic and Algorithms / VCLA)

Researched 2026-09-07, the second country of a simultaneous
five-country research pass (Austria, Eswatini, Australia, USA,
Russia). This platform's first Austria **university** source — the
only prior Austria source, OeAD Ernst Mach Grant (#28), is
government-classified.

- **Organization**: TU Wien, administered through its Vienna Center
  for Logic and Algorithms (VCLA) research center
- **Route code**: `helmut-veith-stipend` (`helmut_veith_stipend`
  internally)
- **Official domain / base URL**: `https://www.vcla.at`
  (`HELMUT_VEITH_STIPEND_BASE_URL`)
- **Opportunity types**: Scholarship — EUR 7,000/year for up to two
  years, plus a full waiver of TU Wien tuition fees, for female
  Master's students in Computer Science. `funding_type =
  "partial_funding"`.
- **Country coverage / eligibility**: No nationality restriction stated
  anywhere on the page — open worldwide, Sierra Leone included.
  Restricted by gender ("female master's students (male students are
  not eligible)") and by academic background (Bachelor's in Computer
  Science, Mathematics, or equivalent; admitted or eligible for
  admission to one of TU Wien's English-taught Computer Science
  Master's programmes; interest in one of Helmut Veith's research
  areas). Documented plainly: this is a genuine gender restriction, not
  a nationality one. Explicitly accepts a not-yet-final degree: "If the
  final academic certificate is not yet available at the time of the
  application deadline, a preliminary certificate (indicating the type
  of degree and the expected graduation date) ... must be provided" —
  a real "expected graduation accepted" case, read directly from the
  page rather than inferred.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered WordPress HTML)
- **robots.txt / indexing note**: `vcla.at/robots.txt` only disallows
  `/wp-admin/`, unrelated to this content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Overview page is the dedicated `vcla.at/helmut-veith-stipend/`
    announcement, deliberately not TU Wien Informatics' general
    scholarships hub page** (`informatics.tuwien.ac.at/study-services/
    scholarships/`), which links to it: the hub page's own text states
    a stale "EUR 6,000 p.a." award figure, while this dedicated page
    (fetched live the same day) states the current "EUR 7000 annually"
    and a live 30 November 2026 deadline covering the next three
    admission semesters (winter 2026/2027, summer 2027, winter
    2027/2028) — the more current, authoritative page was chosen
    deliberately, per this project's "no stale-cycle guessing" rule.
    The hub page is also a multi-record listing of several unrelated
    TU Wien scholarships (a StudFG-governed Merit Scholarship Grant, a
    Funding Grant, a Scholarship for Completion, a Siemens Award)
    sharing one page — the same multi-record architecture mismatch
    documented elsewhere in this file, out of scope regardless of the
    stale-figure issue.
  - **Content selector `div.postarea`**: verified directly via a
    BeautifulSoup structural walk to start exactly at the page's own
    heading and hold the full announcement (award, eligibility,
    application process, FAQ) with none of the site's navigation menu
    text.
  - **`title_selectors = ()`, no `title_tag_separator`**: this page's
    own `<h1>` is the *site's* name ("Vienna Center for Logic and
    Algorithms"), not the scholarship's name — falls through to the
    external_id-derived fallback ("Helmut Veith Stipend"), the same
    documented pattern already used for Max Planck Schools/Gates
    Cambridge/SJTU elsewhere in this file.
  - **Genuinely `partial_funding`, not `fully_funded`**: live research
    confirms Vienna's own documented student cost of living runs
    approximately EUR 950–1,300/month, and non-EU tuition at Austrian
    public universities is itself only around EUR 1,453/year — so EUR
    7,000/year (~EUR 583/month) plus the tuition waiver still covers
    under half of typical living costs. A real, substantial award, but
    not "fully funded" by this project's own standard.
  - **Relies on the base class's default `deadline_keywords`**
    (`("deadline", "closing date")`) rather than overriding them: the
    page's first "deadline" occurrence — "The deadline for the current
    call is November 30, 2026." — is itself the correct, current
    answer; a second, later "Application Deadline ... November 30th"
    mention carries no year and is never reached, since the first
    keyword match already succeeds.
- **LIVE SOURCE TEST: PASSED 2026-09-07.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/helmut_veith_stipend.html`).

### Researched this pass (2026-09-07, Austria — five-country autonomous engine), not integrated

Checked five further Austrian universities live before settling on the
Helmut Veith Stipend above, and found a consistent, systemic access
barrier common to most of them:

- **TU Wien, University of Vienna, University of Graz, Johannes Kepler
  University Linz, University of Innsbruck — general "Merit
  Scholarship" / "Leistungsstipendium"** — every one of these
  universities administers the same nationally-mandated scholarship
  scheme under Austria's Studienförderungsgesetz (StudFG, "Student
  Support Act"), fetched and read directly at TU Wien's own page
  (`informatics.tuwien.ac.at/study-services/scholarships/`): eligible
  applicants must hold "Austrian citizenship or equal status," be "EEA
  citizens," or be "[t]hird-country nationals with a long-term
  residence permit who have lived in Austria for at least 5 years" —
  categorically excluding a prospective Sierra Leonean applicant
  applying from abroad. This is a systemic, legally-defined restriction
  across Austrian public universities, not a university-by-university
  finding — `NOT_INTERNATIONAL`.
- **WU Vienna (Vienna University of Economics and Business) — Mondi
  International Scholarships** — a real, genuinely promising-sounding
  programme found via secondary sources (covers costs for "socially or
  financially disadvantaged, high-potential international students"
  pursuing a Master's, no nationality restriction stated), but WU's own
  2021 announcement page explicitly scopes it to "the academic years
  2021/22 and 2022/23" only, and it does not appear anywhere on WU's
  current, live "Grants and Scholarships" master's-guide page — a
  genuinely discontinued two-cohort pilot, not a currently-open
  scholarship. Per this project's "no stale-cycle guessing" rule, not
  integrated as if still open.
- **BOKU (University of Natural Resources and Life Sciences, Vienna)**
  — search and its own tuition-fee page confirm only the same StudFG
  merit scholarship (identical restriction as above) and outbound
  exchange grants for BOKU's own students studying abroad — no inbound
  international scholarship found.
- **Johannes Kepler University Linz (JKU) — Merit Scholarship for
  Exchange Students** — real, and explicitly not restricted by
  nationality, but restricted by a different axis: it funds temporary
  *exchange* students from JKU's partner universities for a limited
  term, not degree-seeking Master's applicants applying for full
  admission — a different opportunity shape than this pass's
  university-scholarship target, not integrated as a substitute.

No further Austria source was added this pass beyond the Helmut Veith
Stipend above. Given that Austria's entire public-university merit/
need-based scholarship apparatus is governed by the same
nationally-mandated, EEA/long-term-residency-restricted StudFG law,
this systemic barrier is documented once here rather than re-discovered
university by university in future passes.

## 86. University of Sydney — RTP Scholarships (International)

Researched 2026-09-07, the third country (Australia) of the
simultaneous five-country pass. This platform's first Australia
**university** source of any kind — the only prior Australia source,
Australia Awards (#24), is government/DFAT-classified.

- **Organization**: University of Sydney
- **Route code**: `usyd-rtp-international` (`usyd_rtp_international`
  internally)
- **Official domain / base URL**: `https://www.sydney.edu.au`
  (`USYD_RTP_INTERNATIONAL_BASE_URL`)
- **Opportunity types**: Scholarship — the Australian Government
  Research Training Program (RTP), for students "commencing or
  enrolled in a higher degree by research" — Australia's HDR category,
  which includes both **Master's-by-Research and PhD, not PhD-only**,
  verified directly rather than assumed from the page's own PhD
  preference language. `funding_type = "fully_funded"`.
- **Country coverage / eligibility**: No nationality restriction stated
  on this page — open to "international students" broadly, Sierra
  Leone included. "Preference ... given to applicants who [are]
  intending to enrol or currently enrolled in a PhD" is a preference in
  a competitive process, not an exclusion of Master's-by-Research
  applicants.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered Adobe Experience Manager HTML, no JavaScript
  execution needed)
- **robots.txt / indexing note**: `sydney.edu.au/robots.txt` sets
  `Allow: /` for `User-agent: *`, with only a small number of unrelated
  legacy/search paths disallowed.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Content selector `div.cmp-container__inner:not(:empty)`**: the
    page's AEM markup places the real page body in a
    `div.cmp-container__inner`, but a *second*, empty sibling of the
    same class also exists earlier in the DOM — verified directly via
    a BeautifulSoup structural walk that a plain selector would
    incorrectly match that empty element first (`_first_match` takes
    the first selector match), so `:not(:empty)` is used to skip it.
  - **`title_selectors = ()`, `title_tag_separator = " - "`** (a
    literal hyphen, not the page's own "–" en dash): the page has no
    `<h1>`, and its `<title>` reads "RTP scholarships – International -
    The University of Sydney" — splitting on the hyphen yields "RTP
    scholarships – International," a specific title distinguishing
    this page from Sydney's separate domestic RTP page.
  - **Funding**: an AUD 44,293/year stipend (2027 rate, confirmed live
    and distinct from the shown 2026 rate of AUD 42,754), a 100%
    tuition fee offset ("RTP Fee Offset") for up to 14 research
    periods, relocation and thesis allowances, and Overseas Student
    Health Cover (OSHC).
  - **`deadline_keywords` deliberately overridden to `("submission
    deadline",)`**, skipping the base class's default `("deadline",
    "closing date")` entirely: the full page's *first* "deadline"
    occurrence is an earlier prose sentence ("Submit the scholarship
    application form by the deadlines") with no date literal anywhere
    nearby, which would resolve to `None` under the default. The
    page's own deadline table ("Research period | Submission deadline
    | Outcomes Issued from | Outcomes Finalised") is headed by the
    literal phrase "Submission deadline," and once flattened to plain
    text by `BeautifulSoup.get_text()`, that phrase sits immediately
    before the first data row's cells in reading order — so the first
    date literal after this keyword match is exactly that row's own
    submission deadline (11 September 2026, for "Research Period 1 and
    2, 2027," the nearest still-open upcoming cycle) — verified
    directly against the live fixture before writing the test.
- **LIVE SOURCE TEST: PASSED 2026-09-07.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/usyd_rtp_international.html`).

## 87. University of Queensland — Graduate Research School Scholarships (UQGRSS)

Researched 2026-09-07, the same Australia pass as USYD's RTP
scholarship above. This platform's second Australia university source.

- **Organization**: University of Queensland
- **Route code**: `uq-graduate-research-scholarships`
  (`uq_graduate_research_scholarships` internally)
- **Official domain / base URL**: `https://scholarships.uq.edu.au`
  (`UQ_GRADUATE_RESEARCH_SCHOLARSHIPS_BASE_URL`)
- **Opportunity types**: Scholarship, on the "Scholarships for PhD and
  MPhil students" page. **Genuinely covers Master's-by-Research, not
  PhD-only**: the page's own title and text explicitly name "Master of
  Philosophy (MPhil)" alongside "Doctor of Philosophy (PhD)"
  throughout — MPhil is a real, examined Master's-level research
  degree in the Australian system, distinct from a taught/coursework
  Master's. `funding_type = "fully_funded"`.
- **Country coverage / eligibility**: the flagship Graduate Research
  School Scholarship (UQGRSS) is explicitly stated to be "available for
  domestic and international students" — no nationality restriction,
  Sierra Leone included. Two narrower scholarships mentioned on the
  same page are **not** represented by this record, documented rather
  than silently conflated: the "Fellowship support scheme" ("available
  for domestic students" only) and the "Aboriginal and Torres Strait
  Islander Research Scholarships" (an ethnicity restriction, not a
  nationality one, but still distinct from UQGRSS's own general
  eligibility).
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered Drupal HTML)
- **robots.txt / indexing note**: `scholarships.uq.edu.au/robots.txt`
  (a Drupal default) does not disallow this content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML (a
  `sitemap.xml` exists but is not itself scraped)
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Content selector `article`**: verified directly via a
    BeautifulSoup structural walk to hold the full page body (funding-
    type explanations, the UQGRSS description, and the narrower
    domestic-only/restricted scholarships mentioned alongside it) with
    none of the site's navigation or footer chrome.
  - **Funding**: UQGRSS "fund[s] tuition fees, living stipend of $39.2K
    a year tax free (2026 rate), indexed yearly" and "include[s] Single
    Overseas Student Health Cover (OSHC)."
  - **Deliberately extracts no deadline**: the page states only that
    "Graduate Research School Scholarships are offered in rounds during
    the year" with a pointer to "round deadlines" on a separate,
    unlinked-by-URL page — no date literal appears anywhere in this
    page's own text, verified directly rather than assumed.
- **LIVE SOURCE TEST: PASSED 2026-09-07.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch (`tests/fixtures/uq_grsss_phd_mphil.html`).

### Researched this pass (2026-09-07, Australia — five-country autonomous engine), not integrated

Checked several further Australian universities live before settling on
the two sources above:

- **UNSW Sydney — "UNSW Scholarships for International Students
  Commencing Term 1, 2027"** — a genuinely current, live page (opens
  15/07/2026, closes 30/10/2026), but a multi-record hub listing at
  least five separately-named, separately-valued awards on one page
  (International Scientia Coursework Scholarship, UNSW Law & Justice
  International Award, UNSW Business School International Pathways
  Award, UNSW Business School International Scholarship, and more) —
  the same multi-record architecture mismatch documented elsewhere in
  this file, out of scope for the single-record `_SingleProgramSource`
  pattern. Every listed award is also explicitly tuition-only ("paid
  directly towards tuition fees"), with no living-stipend component —
  `TUITION_ONLY`/`PARTIALLY_FUNDED` even before the architecture
  question, consistent with this pass's own "$20,000 tuition
  contribution ≠ fully funded" instruction.
- **Monash University — Monash Graduate Scholarship (MGS)** —
  genuinely fully-funded-sounding (AUD 37,145/year stipend + full
  tuition coverage for Research Doctorate and Research Master's
  students), but `monash.edu` returns an active Cloudflare managed
  challenge ("Just a moment...", HTTP 403) on every path tested,
  including `robots.txt` — genuine bot protection, not circumvented.
- **University of Melbourne — Melbourne Research Scholarship** — a
  re-confirmation of an access barrier already documented in this
  file's earlier "Researched this pass (source diversity), not
  integrated" note (#57): `scholarships.unimelb.edu.au` still returns
  the same active Cloudflare managed challenge on every path tested as
  of this research date — genuinely still blocked, not a stale finding
  left uncorrected.
- **Western Sydney University — "Western Sydney International
  Scholarships – Postgraduate"** — a real, current, single-flagship
  page (explicitly states "The scholarship is a partial tuition fee
  waiver and does not cover costs associated with living expenses,
  accommodation, transport, overseas student health cover" —
  genuinely `PARTIALLY_FUNDED`, AUD 5,000-10,000/year for the 2027
  cycle, matching exactly the example this pass's own research brief
  cited). Not integrated this pass for an architectural reason rather
  than a funding or access one: the page is built from many small
  Adobe-Experience-Manager "component--band" fragments with no single
  enclosing content region that excludes the site's own navigation and
  footer chrome — isolating just the scholarship text would need more
  than this codebase's single-CSS-selector `_first_match` pattern
  supports. Deferred rather than forced into a selector that would
  silently capture nav junk; a real, verified, currently-open candidate
  worth returning to.

## 88. University of Texas at Austin — Harrington Graduate Fellows Program

Researched 2026-09-07, the fourth country (USA) of the simultaneous
five-country pass. This platform's first USA **university** source
(Knight-Hennessy Scholars, #51, is hosted at Stanford but was
researched as a "host-country-vs-eligibility" case, not a USA-specific
search).

- **Organization**: University of Texas at Austin, via the Harrington
  Fellowship
- **Route code**: `harrington-graduate-fellows`
  (`harrington_graduate_fellows` internally)
- **Official domain / base URL**: `https://harrington.utexas.edu`
  (`HARRINGTON_GRADUATE_FELLOWS_BASE_URL`)
- **Opportunity types**: Fellowship — a 12-month USD 40,000 stipend,
  full tuition and required fees, a health-insurance stipend, and a
  USD 2,000/year expense allowance, for up to five years.
  `funding_type = "fully_funded"`.
- **Country coverage / eligibility**: the programme's own stated goal
  is "bringing outstanding graduate students to UT Austin from around
  the world" — no nationality restriction found, Sierra Leone
  included. Documented plainly: this is a **nomination-only** award —
  "potential graduate students cannot apply to the Harrington Graduate
  Fellows Program directly," candidates are nominated by their own
  graduate programme — the same honestly-disclosed shape as this
  platform's existing nomination-based sources (e.g. Wageningen's Anne
  van den Ban Fund). **Genuinely includes a Master's track, not
  PhD-only**: alongside "Harrington Doctoral Fellows," the page names
  "Harrington Master's Fellows — for incoming graduate students,"
  specifically for "professional or terminal master's degrees, for
  example, the MFA, MSSW, or MSLIS."
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered Drupal HTML)
- **robots.txt / indexing note**: `harrington.utexas.edu/robots.txt`
  (a Drupal default) does not disallow this content path.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Content selector `article`**: verified directly via a
    BeautifulSoup structural walk to hold the full page body
    (programme overview, all three fellowship tracks, contact) with
    none of the site's navigation or footer chrome.
  - **Deliberately extracts no deadline**: this is a nomination-only
    programme with no fixed, directly-facing application deadline of
    its own (each nominating graduate programme has its own admission
    timeline) — no date literal appears anywhere in this page's text.
- **LIVE SOURCE TEST: PASSED 2026-09-07.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/harrington_graduate_fellows.html`).

## 89. Vanderbilt University — Cornelius Vanderbilt Scholarship

Researched 2026-09-07, the same USA pass as Harrington's Graduate
Fellows Program above. This platform's second USA university source,
and its first at the **undergraduate** level.

- **Organization**: Vanderbilt University
- **Route code**: `cornelius-vanderbilt-scholarship`
  (`vanderbilt_cornelius_scholarship` internally)
- **Official domain / base URL**: `https://www.vanderbilt.edu`
  (`VANDERBILT_CORNELIUS_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship — "guaranteed full-tuition awards
  plus summer stipends for study abroad, research or service
  projects," renewable for four years of undergraduate study.
  Correctly `funding_type = "partial_funding"`, **not**
  `fully_funded`: full tuition plus an occasional summer stipend is
  not stated to cover room, board, or general living costs — the same
  "full tuition alone is not fully funded" standard applied
  consistently throughout this project.
- **Country coverage / eligibility**: no nationality restriction stated
  on the overview page. Verified directly on Vanderbilt's own separate
  international-admissions page (confirmed live but not itself
  scraped for this record): "For international students admitted for
  fall 2026, Vanderbilt offered need-based aid and/or merit
  scholarships to 89 students representing 54 countries" — genuinely
  open to international applicants, not US-citizens-only.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML)
- **robots.txt / indexing note**: `vanderbilt.edu` has no `robots.txt`
  file at all — the request returns a genuine HTTP 404 (served via
  CloudFront/S3, confirmed not a proxy artifact) — no restrictions
  declared.
- **API / RSS / Sitemap**: None found; plain scraped HTML
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Overview page names two signature programmes together under one
    shared 1 December 2026 deadline**: the Cornelius Vanderbilt
    Scholarship (general academic-achievement-and-leadership merit)
    and the Ingram Scholars Program (a differently-focused track for
    students combining a professional/business career with civic-
    minded service and entrepreneurship). This record represents the
    Cornelius Vanderbilt Scholarship specifically — Ingram Scholars is
    a separate, differently-focused sibling programme sharing the same
    page and deadline, **not** represented by this record, the same
    "narrower sibling" documentation pattern already used for UQ's
    Graduate Research School Scholarships (#87).
  - **Content selector `main`**: verified directly via a BeautifulSoup
    structural walk to hold the full page body (both programmes'
    descriptions and the shared deadline line) with none of the site's
    navigation or footer chrome.
  - **`title_selectors = ()`, no `title_tag_separator`**: the page's
    own `<h1>` ("Merit Scholarship Opportunities") describes the whole
    page rather than this specific scholarship — falls through to the
    external_id-derived fallback ("Cornelius Vanderbilt Scholarship"),
    the same documented pattern already used for WMI/Gates Cambridge/
    Helmut Veith elsewhere in this file.
- **LIVE SOURCE TEST: PASSED 2026-09-07.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch
  (`tests/fixtures/vanderbilt_cornelius_scholarship.html`).

### Researched this pass (2026-09-07, USA — five-country autonomous engine), not integrated

Given the sheer scale of the US higher-education ecosystem explicitly
flagged in the research brief, this pass prioritized verifying two
genuinely strong, well-documented candidates deeply (above) over a
shallow sweep of many universities. One further strong candidate was
researched and found blocked:

- **University of Michigan — Helen Zell Writers' Program (MFA)** — a
  genuinely fully-funded programme by reputation ("full tuition
  remission and a monthly stipend generous enough to cover a
  reasonable local rent and modest living expenses" for every admitted
  student, no partial-funding tiers), but `lsa.umich.edu` returns an
  active Cloudflare managed challenge (`cf-mitigated: challenge`,
  confirmed via a verbose response-header trace, not merely an HTTP
  403 guess) on the specific funding page — genuine bot protection,
  not circumvented.
- **Onsi Sawiris Scholarship** (Stanford, University of Chicago,
  Harvard, University of Pennsylvania) — found via secondary sources
  as a "fully funded master's scholarship for international students,"
  but this programme is specifically restricted to Egyptian nationals
  (named for an Egyptian businessman, administered through AUC/Sawiris
  Foundation channels) — not researched further as a candidate for a
  Sierra Leonean applicant.

## 90. Skoltech (Skolkovo Institute of Science and Technology) — Admissions Scholarship

Researched 2026-09-07, the fifth and final country (Russia) of the
simultaneous five-country pass (Austria, Eswatini, Australia, USA,
Russia). This platform's **first Russia source of any kind**.

- **Organization**: Skolkovo Institute of Science and Technology
  (Skoltech)
- **Route code**: `skoltech-scholarship` (`skoltech_scholarship`
  internally)
- **Official domain / base URL**: `https://www.skoltech.ru`
  (`SKOLTECH_SCHOLARSHIP_BASE_URL`)
- **Opportunity types**: Scholarship, covering both MSc and PhD
  programmes together on one page (14 fields listed for each degree
  level). A competitively-awarded monthly stipend — "for MSc students:
  40,000 rubles per month; for PhD students: 75,000 rubles per month"
  — plus insurance. **Deliberately conservative funding
  classification**: `funding_type = "partial_funding"`, not
  `fully_funded`. This page's own text does **not** state that tuition
  is waived for every admitted student; secondary sources describe
  Skoltech as broadly tuition-free but also note a listed tuition fee
  for MSc applicants who do not receive the competitive scholarship
  (consistent with the page's own "for highest-scoring applicants"
  framing for the top-tier stipend rate). Classified from what this
  specific official page actually states, not from aggregator "fully
  funded" claims, per this project's "official source over aggregator"
  rule.
- **Country coverage / eligibility**: no nationality restriction
  stated — "international environment," English-taught, worldwide
  applicability.
- **Discovery method**: Web scraper (plain HTTPS GET, real
  server-rendered HTML, no JavaScript execution needed)
- **robots.txt / indexing note**: `skoltech.ru/robots.txt` sets
  `Allow: /` for `User-agent: *`, disallowing only `/admin/`, `/api/`,
  and query-string/JSON/XML paths — none of which cover this content
  path. Also confirmed the site is genuinely reachable from this
  environment (a real live fetch, 200, server-rendered HTML) — contrary
  to any assumption that sanctions or geo-blocking would prevent
  access; this is an outbound-facing international-admissions page,
  not a Russia-internal service.
- **API / RSS / Sitemap**: A sitemap exists (`skoltech.ru/sitemap.xml`)
  but is not itself scraped
- **Authentication**: None
- **Reliability classification**: Web-scraped
- **Verification method**: Human officer review, same checklist as
  sources 1–7
- **Sync cadence**: Every 24 hours
- **Deliberate design choices**:
  - **Content selector `main`**: verified directly via a BeautifulSoup
    structural walk to hold the admissions status, programme list, and
    "scholarships and benefits" section with none of the site's
    navigation or footer chrome.
  - **`title_selectors = ()`, no `title_tag_separator`**: the page has
    no `<h1>`, and its `<title>` ("Admissions | Сколтех") is too
    generic on its own — falls through to the external_id-derived
    fallback ("Skoltech Scholarship"), the same documented pattern
    already used for WMI/Gates Cambridge/Helmut Veith elsewhere in this
    file.
  - **Deliberately extracts no deadline**: the page states plainly
    "The application period for Skoltech master's and PhD programs is
    now closed. To apply for the 2027 start, check back in autumn" —
    no date literal for the next cycle exists yet, per this project's
    "no stale-cycle guessing" rule.
- **LIVE SOURCE TEST: PASSED 2026-09-07.** Verified through this
  backend's actual HTTP path — 200, real server-rendered HTML.
  Implemented and unit-tested against a real fixture, captured
  unmodified from the live fetch (`tests/fixtures/skoltech_admissions.html`).

### Researched this pass (2026-09-07, Russia — five-country autonomous engine), not integrated

- **"Open Doors: Russian Scholarship Project" (Global Universities
  Association, hosted on `admissions.hse.ru/en/globaluni/`)** — a
  genuinely enormous and credible programme (100,000+ participants a
  year, 6,000+ admitted over 7 years, tuition-free admission with no
  entrance exams for competition winners), but architecturally a
  large multi-university, multi-programme catalogue listing dozens of
  distinct Bachelor's and Master's programmes across many different
  Russian universities and fields, each with its own selection
  criteria — the same multi-record architecture mismatch documented
  repeatedly elsewhere in this file (closer to the Erasmus Mundus
  catalogue's shape, #47, than a single-record flagship page). Out of
  scope for this pass's `_SingleProgramSource` pattern; a strong
  candidate for a dedicated future pass using this platform's
  multi-record/pagination architecture instead.
- **`education-in-russia.com`** — the official Russian government
  portal for the international Government Quota programme
  (Rossotrudnichestvo) — reachable and unrestricted per its own
  `robots.txt` (a large named-bot blocklist with no catch-all `User-
  agent: *` rule, so this platform's own identified `ScholarSphere/1.0`
  scraper is not disallowed), but its homepage is a client-side-
  rendered single-page application shell (5.4 KB of HTML, no readable
  programme content without executing JavaScript) — a technical
  limitation, not a bot-block, consistent with this project's
  documented distinction between the two categories.
- **HSE University's own general merit/tuition-discount scholarships**
  — real (up to 50% tuition discount at the Master's level, a smaller
  number of full-tuition-waiver "top applicant" places), but described
  across multiple separate programme-specific pages with differing
  terms per Master's programme rather than one flagship page — the
  same multi-record mismatch as Open Doors above.

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
| Aga Khan Foundation International Scholarship Programme (ISP) | Researched 2026-08-30 — real, legitimate, long-running programme for gifted students from developing countries with no other means of financing postgraduate study. Rejected on eligibility grounds, not a technical one: the programme's own published country scope (Bangladesh, India, Pakistan, Afghanistan, Tajikistan, Kyrgyzstan, Syria, Egypt, Kenya, Tanzania, Uganda, Madagascar, Mozambique) does not include Sierra Leone — this platform's own "never invent eligibility" rule cuts both ways: a source that explicitly excludes Sierra Leone from its stated country list is exactly the "clearly ineligible" case, not integrated on that basis rather than a reachability/JS-rendering issue. |
| United World Colleges (UWC), `uwc.org` | Researched 2026-09-05 — a real, legitimate global scholarship movement with 152 national committees (Sierra Leone's included) confirmed live over plain HTTPS, real per-country content, no JS-rendering issue at all. Rejected purely on `robots.txt`: it explicitly states `User-agent: ClaudeBot` / `Disallow: /`, even though `User-agent: *` is otherwise unrestricted. Per this project's own established precedent (see Indonesia's KNB entry, `docs/COUNTRY_PROVIDER_REGISTRY.md`), a named `ClaudeBot` disallow rule is treated as binding regardless of this backend's own actual configured User-Agent header — not circumvented. |
| OPEC Fund (OFID) Scholarship Award, `opecfund.org` | Researched 2026-09-05 — a real, legitimate, genuinely global scholarship (nationals of developing countries, OFID member countries excluded) with no technical blocker at all (200, real server-rendered content, permissive robots.txt). Rejected because the program itself is not currently open: its own live page states verbatim "the OPEC Fund is currently restructuring its scholarship program and is not accepting applications at this time" — the same "don't present a non-open call as a live opportunity" principle already applied to UKRI Gateway to Research above, just for a temporarily-paused program rather than a permanently historical one. Worth re-checking in a future session once the restructuring concludes. |
| International Foundation for Science (IFS) research grants, `ifs.se` | Researched 2026-09-05 — a real, long-running (since 1972) grant program for developing-country scientists, widely documented by third parties (Devex, Terra Viva Grants, and others) as still active. Not integrated because the organization's own documented domain, `www.ifs.se`, no longer resolves to IFS at all — it 301-redirects to an unrelated Swedish website. No current official URL could be located in this session; re-investigate if IFS's real current domain is found. |

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

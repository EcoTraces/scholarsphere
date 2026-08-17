# ScholarSphere — Authoritative Source Registry

Every source below is real, currently integrated, and confirmed against the
actual configuration and code in `scholarsphere_backend/` — none of these
URLs are invented. This is the same list as
`scholarsphere_backend/README.md`'s "Integration overview" and "Source
mappings" sections; this document restates it in the platform
specification's requested source-registry format and adds the reliability
classification and verification method for each.

All six are ingested via each provider's own official, documented,
structured API — **there is no web scraping in this codebase.**
(`docs/PRODUCTION_SECURITY_AUDIT.md` §2.6, confirmed by repository-wide
search for scraping libraries.)

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

## 2. Simpler.Grants.gov

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

## 3. European Commission Funding & Tenders Portal

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

## 4. USAJOBS

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

## 5. ReliefWeb Jobs (UN OCHA)

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

## 6. ReliefWeb Training (UN OCHA)

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

**The biggest real coverage gap**: individual-student scholarships and
fellowships. Almost none of the well-known providers (DAAD, Chevening,
Fulbright, Commonwealth Scholarships, university-specific funds) publish a
public API. Closing this gap needs either a licensed commercial data feed or
per-provider partnership/manual-entry work — a materially different and
larger effort than the API integrations above, and not yet undertaken.

## Source registry data model

Each row above is a real `OpportunitySource` database record
(`app/models/external_opportunity.py`), seeded idempotently by
`app/services/source_registry.py`'s `SOURCE_DEFINITIONS` at startup/first
sync. Administrators can deactivate/reactivate a source via
`PATCH /external-opportunities/sources/{source}` (audited); adding a
*seventh* source today requires a code change to `SOURCE_DEFINITIONS`, not a
UI action — a Super-Administrator-editable source registry UI (as described
in the platform specification §5/§18) does not exist yet.

Live per-source health (last successful/failed sync, most recent error,
next scheduled run) is available to verification staff at
`GET /external-opportunities/health`.

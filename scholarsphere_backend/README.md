# ScholarSphere external-opportunity backend

This FastAPI service collects funding and scholarship opportunities from
official APIs and, for a small set of named organizations with no API, their
own public web pages. Every collector retains the exact source payload,
normalizes it, detects possible duplicates, and places every record into
human verification. **No external record is ever published automatically**,
regardless of source or how complete it looks - see
`docs/OPPORTUNITY_VERIFICATION_SYSTEM.md`.

## Integration overview and coverage

Supported sources:

| Route | Source | Method | Primary coverage |
|---|---|---|---|
| `grants-gov` | Grants.gov Search2 | Official API | US federal grants |
| `grants-gov-individual` | Grants.gov Search2 (eligibility `21`, "Individuals") | Official API | US federal scholarships/fellowships a person applies for directly |
| `simpler-grants` | Simpler.Grants.gov | Official API | US federal grants |
| `eu-funding` | EC Funding & Tenders | Official API | European grants, calls, tenders, research and funding opportunities |
| `usajobs` | USAJOBS | Official API | US federal jobs and student/internship postings (Pathways hiring path) |
| `reliefweb-jobs` | ReliefWeb Jobs (UN OCHA) | Official API | Global humanitarian/development jobs and internships |
| `reliefweb-training` | ReliefWeb Training (UN OCHA) | Official API | Global humanitarian/development training courses and workshops |
| `cscuk-scholarships` | Commonwealth Scholarships (CSC UK) | Web scraper | UK government scholarships for Commonwealth countries |
| `chevening` | Chevening Scholarships | Web scraper | UK government global master's scholarship |
| `daad-scholarships` | DAAD Scholarship Database | Web scraper (curated seed list) | German study/research scholarships |
| `china-embassy-sl` | Chinese Embassy in Sierra Leone | Web scraper (announcements) | Chinese Government / MOFCOM scholarships for Sierra Leonean students |
| `mthe-sierra-leone` | Sierra Leone Ministry of Technical and Higher Education | Web scraper (announcements) | Government-announced scholarships for Sierra Leonean students (including partner-government offers, e.g. Russia) |
| `wmi-scholars` | Wells Mountain Initiative (WMI) | Web scraper | Partial undergraduate scholarships for students studying in their own home region |
| `turkiye-burslari` | Türkiye Bursları (Turkey) | Web scraper | Government of Turkey scholarships, all levels |
| `ireland-goi-ies` | Government of Ireland GOI-IES | Web scraper | Irish government master's/PhD scholarships for non-EU/EEA/UK applicants |
| `india-iccr` | ICCR Scholarship Programme (India) | Web scraper | Government of India scholarships across 18 schemes (**live-blocked**: ICCR's server has an incomplete TLS certificate chain — see `docs/AUTHORITATIVE_SOURCES.md` #16) |
| `sweden-si-scholarship` | Swedish Institute Scholarships for Global Professionals | Web scraper | Swedish government master's scholarships |
| `eswatini-slas` | Eswatini Scholarship Loan Application System (SLAS) | Web scraper (announcements) | Government of Eswatini local/SADC-region scholarships (**live-blocked**: network timeout, same pattern as MTHE above) |
| `italy-maeci-scholarships` | Italian Government Scholarships (MAECI) | Web scraper | Italian government scholarships for foreign students |
| `greece-iky-scholarships` | IKY Foreign Nationals Scholarships (Greece) | Web scraper | Greek government scholarships (postgraduate, research, language/culture) |
| `south-africa-nrf` | NRF Postgraduate Funding (South Africa) | Web scraper | South African government research funding, international PCS track (**live-blocked**: TLS certificate-chain issue on NRF's server — see `docs/AUTHORITATIVE_SOURCES.md` #21) |

The web-scraper sources exist only because no official API, RSS feed, or
dataset is published for these organizations - see
`docs/AUTHORITATIVE_SOURCES.md` for the per-source research (domain
confirmation, robots.txt/terms check, page-structure verification) performed
before each was added, and `app/services/web_scraper_base.py` for the shared
fetch/rate-limit/never-invent-data discipline every scraper follows. They
carry a lower `trust_level` (`web_scraped` vs `official`) that feeds into
`app/services/verification_confidence.py`, but they go through the exact same
mandatory human verification queue as every API source - a lower trust level
changes queue priority, never whether approval is required.

These sources do not contain every scholarship, internship, webinar,
conference, summit, exchange, fellowship, or course. ScholarSphere will
continue to need verified provider submissions, manual entry, official feeds,
partner APIs, and collection from official sources where permission and terms
allow it.

### Source research notes (what was checked, and what was checked and rejected)

Before adding `usajobs` and `reliefweb-jobs`/`reliefweb-training`, the
following candidates were researched for broader coverage (scholarships,
fellowships, competitions, conferences, exchange programs) and found *not*
suitable for a direct API integration at this time:

- **StudyPortals / ScholarshipPortal, MastersPortal, PhDPortal** - no
  official public API; only unofficial third-party scraper wrappers exist.
- **ScholarshipAPI.com** - a real commercial product with a free tier, but
  its actual endpoint/auth documentation could not be independently fetched
  (blocked automated access) in the environment this was researched from, so
  no integration was written against unverified assumptions about its
  contract. Worth revisiting with direct access to their docs.
- **Devpost** (hackathons/competitions) - has no officially documented
  public API; only an undocumented internal endpoint used by unofficial
  scrapers, which does not meet this project's "official/documented source"
  bar.
- **Eventbrite** (webinars/conferences/workshops) - removed public
  Event Search API access in 2019; only organizer/venue-scoped endpoints
  remain, which don't support open-ended discovery.
- **UKRI Gateway to Research** (`gtr.ukri.org`) - a real, free, no-key
  official API, but it publishes a database of *already-awarded* UK
  research grants, not open calls to apply to. Integrating it would mean
  presenting closed/historical awards as live opportunities, which
  conflicts with the "never mislead" principle, so it was left out.
- **EURAXESS** (European researcher jobs/fellowships) - no official public
  API found, only third-party scrapers.

Four of those coverage gaps (DAAD, Chevening, Commonwealth Scholarships, and
two Sierra-Leone-specific government-announcement channels) were later closed
by adding a small, explicitly-scoped web-scraper tier
(`app/services/web_scraper_base.py` and its subclasses) rather than an API
integration, since none of these organizations publish one - see
`docs/AUTHORITATIVE_SOURCES.md` #8-#12 for the per-source research and
robots.txt/terms check. **Fulbright was researched and deliberately not
integrated**: the US-student-facing site (`us.fulbrightonline.org`) is the
wrong audience for this platform, the foreign-student program
(`foreign.fulbrightonline.org`) is administered per-country through ~160
individual US embassy pages with no single list of open calls, and the one
Sierra-Leone-specific page checked
(`sl.usembassy.gov/educational-professional-exchanges/`) returned a generic
"Technical Difficulties" error page when fetched (2026-08-22) rather than
real content - there is no single stable page to scrape reliably.

The remaining real gap is everything not covered above: most named
university-specific and foundation scholarship funds still publish no
public API and were not evaluated for scraping. Closing that gap further
needs either a licensed commercial data feed, per-provider partnership, or
evaluating specific additional named sites for scraping the same way the
five above were - not a generic crawler.

The production flow is enforced as:

```text
External API -> raw record -> schema validation -> normalization
-> duplicate detection -> pending verification -> verification review
-> approval -> explicit publication
```

Imports always start as `verification_status=pending` and
`publication_status=unpublished`. Approval still leaves an opportunity
unpublished; an administrator must publish it separately.

## Dependencies

- Python 3.12
- PostgreSQL 16
- Redis 7
- FastAPI, SQLAlchemy asyncio, asyncpg, Alembic and Pydantic
- HTTPX, Bleach and python-dateutil
- BeautifulSoup4 (`html.parser` backend, no extra C-extension parser
  dependency) for the web-scraper sources
- Celery worker and Celery Beat
- Pytest, pytest-asyncio, RESPX and aiosqlite for tests

Install locally:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

`requirements.txt` lists only the production runtime dependencies (installed by
`Dockerfile`); `requirements-dev.txt` layers testing and dependency-audit tools
on top of it for local development and CI.

## Environment variables

Copy `.env.example` to `.env`; never commit `.env` or Firebase service-account
JSON. Required/operational values include:

| Variable | Purpose |
|---|---|
| `APP_ENV` | Environment name |
| `API_V1_PREFIX` | API prefix, normally `/api/v1` |
| `POSTGRES_PASSWORD` | Docker PostgreSQL password; required by Compose |
| `DATABASE_URL` | `postgresql+asyncpg://...` connection URL |
| `REDIS_URL` | Celery broker/result backend |
| `FIREBASE_PROJECT_ID` | Accepted Firebase token audience |
| `FIREBASE_CREDENTIALS_PATH` | Optional server credential JSON path |
| `ALLOWED_ORIGINS` | Comma-separated trusted frontend origins |
| `HTTP_TIMEOUT_SECONDS` | External request timeout |
| `HTTP_MAX_RETRIES` | Bounded retry count |
| `HTTP_MAX_RESPONSE_BYTES` | Maximum external response size |
| `MAX_REQUEST_BYTES` | Maximum accepted request `Content-Length` |
| `GRANTS_GOV_BASE_URL` | HTTPS Grants.gov base URL |
| `SIMPLER_GRANTS_BASE_URL` | HTTPS Simpler.Grants.gov base URL |
| `SIMPLER_GRANTS_API_KEY` | Secret Simpler API key |
| `EU_FUNDING_API_URL` | HTTPS EC search URL |
| `EU_FUNDING_API_KEY` | EC API identifier, normally `SEDIA` |
| `EU_FUNDING_*` | Configurable filters, mappings, language and fields |
| `USAJOBS_BASE_URL` | HTTPS USAJOBS Search API base URL |
| `USAJOBS_API_KEY` | Free, self-service key from developer.usajobs.gov |
| `USAJOBS_USER_AGENT` | The email address registered with the USAJOBS key - USAJOBS requires this exact value as the `User-Agent` header for authentication, not a generic client string |
| `RELIEFWEB_BASE_URL` | HTTPS ReliefWeb API v2 base URL |
| `RELIEFWEB_APPNAME` | Pre-approved ReliefWeb application identifier (not a secret) |

Obtain a Simpler.Grants.gov API key through the current registration process
linked from the official Simpler.Grants.gov API documentation. Put the issued
value only in `SIMPLER_GRANTS_API_KEY` or a production secret manager. Never
place it in Flutter code, Docker images, command arguments, logs, or source
control.

All external endpoint settings are rejected at startup unless they use HTTPS.
API-key settings use Pydantic secret values so configuration representations are
masked.

## PostgreSQL and migrations

Create a PostgreSQL database and set `DATABASE_URL`, then run:

```powershell
alembic upgrade head
alembic current
```

```bash
alembic upgrade head
alembic current
```

Safe migration rehearsal on a disposable database:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Do not downgrade a production database without a reviewed backup and change
plan.

## Running services without Docker

FastAPI:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Redis:

```powershell
docker run --name scholarsphere-redis -p 6379:6379 redis:7-alpine redis-server --appendonly yes
```

```bash
redis-server --appendonly yes
```

Celery worker and Beat, in separate terminals:

```powershell
celery -A app.tasks.opportunity_sync.celery_app worker --loglevel=info
celery -A app.tasks.opportunity_sync.celery_app beat --loglevel=info
```

```bash
celery -A app.tasks.opportunity_sync.celery_app worker --loglevel=info
celery -A app.tasks.opportunity_sync.celery_app beat --loglevel=info
```

Swagger is available at `http://localhost:8000/docs`; ReDoc is at `/redoc`.

## Docker

Docker Compose uses one PostgreSQL service, one Redis service, an Alembic
migration job, FastAPI, a Celery worker, and Celery Beat. Migrations must finish
successfully before application processes start.

```powershell
Copy-Item .env.example .env
# Set POSTGRES_PASSWORD and SIMPLER_GRANTS_API_KEY in .env.
docker compose up --build -d
docker compose ps
docker compose logs -f migrate api worker beat
```

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD and SIMPLER_GRANTS_API_KEY in .env.
docker compose up --build -d
docker compose ps
docker compose logs -f migrate api worker beat
```

Stop without deleting PostgreSQL/Redis volumes:

```bash
docker compose down
```

## API usage

Every protected request needs a Firebase ID token:

```text
Authorization: Bearer <firebase-id-token>
X-Correlation-ID: optional-client-correlation-id
```

Preview without saving:

```powershell
$headers = @{ Authorization = "Bearer $env:SCHOLARSPHERE_TOKEN" }
Invoke-RestMethod -Headers $headers -Uri "http://localhost:8000/api/v1/external-opportunities/grants-gov/preview?keyword=education&page=1&page_size=25"
```

```bash
curl -H "Authorization: Bearer $SCHOLARSPHERE_TOKEN" \
  "http://localhost:8000/api/v1/external-opportunities/grants-gov/preview?keyword=education&page=1&page_size=25"
```

Import immediately:

```bash
curl -X POST -H "Authorization: Bearer $SCHOLARSPHERE_TOKEN" \
  "http://localhost:8000/api/v1/external-opportunities/simpler-grants/import?page=1&page_size=25"
```

Queue synchronization:

```bash
curl -X POST -H "Authorization: Bearer $SCHOLARSPHERE_TOKEN" \
  http://localhost:8000/api/v1/external-opportunities/eu-funding/sync
```

View sources, health, history, and verification queue:

```bash
curl -H "Authorization: Bearer $SCHOLARSPHERE_TOKEN" http://localhost:8000/api/v1/external-opportunities/sources
curl -H "Authorization: Bearer $SCHOLARSPHERE_TOKEN" http://localhost:8000/api/v1/external-opportunities/health
curl -H "Authorization: Bearer $SCHOLARSPHERE_TOKEN" "http://localhost:8000/api/v1/external-opportunities/sync-history?page=1&page_size=25"
curl -H "Authorization: Bearer $SCHOLARSPHERE_TOKEN" "http://localhost:8000/api/v1/external-opportunities/pending-verification?page=1&page_size=25"
```

Approve after all checks, then publish separately:

```bash
curl -X POST -H "Authorization: Bearer $SCHOLARSPHERE_TOKEN" -H "Content-Type: application/json" \
  -d '{"decision":"approved","notes":"Official source confirmed","source_checked":true,"application_link_checked":true,"deadline_checked":true,"duplicate_checked":true}' \
  http://localhost:8000/api/v1/external-opportunities/opportunities/OPPORTUNITY_UUID/verification

curl -X POST -H "Authorization: Bearer $SCHOLARSPHERE_TOKEN" -H "Content-Type: application/json" \
  -d '{"published":true}' \
  http://localhost:8000/api/v1/external-opportunities/opportunities/OPPORTUNITY_UUID/publication
```

## Source mappings

### Grants.gov Search2

`id` becomes `external_id`; `number` becomes `external_reference`; agency,
opening/closing dates and status map to their normalized equivalents. Type is
`grant`, country is `United States`, and the official detail URL is built from
the opportunity number.

### Grants.gov Search2 (Individual Eligibility)

Shares its normalizer with plain Grants.gov above (`_GrantsGovSource` in
`app/services/grants_gov.py`); the only differences are the source code,
`opportunity_type` (`scholarship` instead of `grant`), and the `eligibilities`
search filter, which defaults to `21` ("Individuals" — grants.gov's own
published eligibility-category code) instead of being left unrestricted. This
surfaces federal funding opportunities a person applies for directly, such as
graduate research fellowships, rather than opportunities restricted to
organizations. Eligibility category `21` is broader than "scholarship" in the
everyday sense — some results are closer to a fellowship or an individual
research award — so this is a best-effort classification, not a guarantee.

### Simpler.Grants.gov

Opportunity ID/number/title, agency, summary/description, post/close dates,
status and award floor/ceiling are normalized. Type is `grant`, country is
`United States`, currency is `USD`, and the official URL uses the opportunity
ID.

### European Commission Funding & Tenders

Configurable metadata fields include type, identifier, reference, title,
status, contracting authority, start/deadline dates, programme information,
budget and keywords. Scalars, lists, objects and nulls are handled safely. The
earliest valid deadline is selected; currency is `EUR`; country is
`European Union`. Supplied result URLs are preferred, otherwise a topic URL is
built from reference or identifier.

### USAJOBS

`PositionID`/`MatchedObjectId` becomes `external_id`; `PositionTitle`,
`OrganizationName`/`DepartmentName`, `PositionStartDate` and
`ApplicationCloseDate` map to their normalized equivalents. Postings whose
`HiringPath` mentions students, recent graduates or interns are typed
`internship`; everything else is typed `job`. Country is always
`United States`. Authentication requires `Host: data.usajobs.gov`,
`Authorization-Key: <key>` and `User-Agent: <registered email>` on every
request - USAJOBS uses the `User-Agent` value as part of authentication,
so it is exempt from the HTTP client's default `User-Agent` override.

**Verification note:** the response field names above come from USAJOBS'
long-stable, widely-documented schema, but this adapter has not been
exercised against a live authenticated response in this codebase's
development environment (no outbound internet access when it was written).
Smoke-test it with a real `USAJOBS_API_KEY` before enabling scheduled sync.

### ReliefWeb (UN OCHA)

Two independent sources share one normalizer: `reliefweb-jobs` (job/
internship postings) and `reliefweb-training` (training courses and
workshops). Both map `id` to `external_id`, `fields.title`,
`fields.source[0].name`, `fields.country[0].name` and `fields.url` to their
normalized equivalents, and `fields.date.created` to `opening_date`.
Jobs use `fields.date.closing` as the deadline; training uses
`fields.date.registration` (the registration close date). Every request
requires a pre-approved `appname` as a URL parameter (ReliefWeb's own
authentication mechanism, not a secret credential) - see
[apidoc.reliefweb.int](https://apidoc.reliefweb.int/). Field names were
confirmed directly against ReliefWeb's official parameter and field-table
documentation.

## Duplicate detection and reverification

Exact duplicates use source plus external ID and deterministic payload SHA-256.
Unchanged payloads are skipped. Cross-source candidates use normalized title,
provider and deadline fingerprints; candidates are flagged for review and are
never merged automatically.

Material changes to title, provider, deadline, official/application URLs,
award amounts, or source status create audit/history records and move a
previously reviewed opportunity to `reverification_required`.

## Security

- Firebase token authentication and role checks protect management routes.
- Only verification officers, administrators and super administrators import or sync.
- Only administrators and super administrators publish or change source state.
- External URLs must use HTTPS and normalized output URLs are validated.
- HTTPX applies timeouts, response-size limits and bounded selective retries.
- Sensitive headers, response bodies and API keys are excluded from logs/errors.
- Bleach removes executable HTML, event handlers, unsafe schemes and embedded content.
- Correlation IDs appear in safe API errors and response headers.
- Per-record savepoints isolate malformed records; outer transactions roll back safely.
- External records never publish automatically.

Firebase web/mobile API keys in generated Firebase client configuration are
public project identifiers, not server provider secrets. Protect Firebase with
Security Rules, authorized domains, API restrictions, App Check where
appropriate, and never place service-account credentials in the client.

## Testing and validation

```powershell
python -m compileall -q app alembic tests
pytest
flutter analyze
flutter test
```

```bash
python -m compileall -q app alembic tests
pytest
flutter analyze
flutter test
```

No Python formatter, linter, or static type checker is currently configured.
Add project-wide tooling deliberately rather than applying an unreviewed
formatter to unrelated code.

Useful checks:

```bash
alembic upgrade head
python -c "from app.main import app; print(app.title)"
python -c "from app.tasks.opportunity_sync import celery_app; print(sorted(celery_app.tasks))"
curl http://localhost:8000/openapi.json
redis-cli -u "$REDIS_URL" ping
```

## Troubleshooting

- `SIMPLER_GRANTS_API_KEY is not configured`: obtain a key and set it server-side.
- PostgreSQL connection refused: verify `DATABASE_URL`, PostgreSQL health and firewall.
- Redis/Celery unavailable: verify `REDIS_URL`, `redis-cli ping`, worker and Beat logs.
- Migration import error: activate the backend environment and install requirements.
- Firebase 401: verify project ID, credentials, token audience, expiry and revocation. Revocation checking (`check_revoked=True`) requires a real service-account credential (`FIREBASE_CREDENTIALS_PATH` or ADC) - without one, every token fails even if it's genuinely valid. The server logs `firebase_token_verification_failed` with the exception type (never the token) when this happens. For local/demo runs with no service account, set `FIREBASE_CHECK_REVOKED=false`; never do this in production.
- 429/503: inspect the returned correlation ID and safe worker logs; retries are bounded.
- Empty previews: confirm source filters and upstream availability without bypassing TLS.

## Known limitations

- The seven feeds cover US/EU government grants, individually-eligible US federal awards (a partial scholarship/fellowship proxy, not a dedicated scholarship database), US federal jobs, and UN humanitarian jobs/training - named scholarship programs (DAAD, Chevening, Fulbright, etc.), conferences, competitions, and exchange programs remain a real gap (see "Source research notes" above for what was checked and why it wasn't integrated).
- The USAJOBS adapter's response field names are based on established public documentation, not a live-verified response in this development environment; smoke-test with a real key before enabling scheduled sync.
- ~~Reverification reminders currently produce worker/audit signals; user delivery needs both a backend notification provider *and* a live-backed client notification repository - the Flutter client's entire notification feature (`lib/features/notifications/`) is still demo/in-memory only today, unlike applications and verification.~~ Fixed (2026-08-20/2026-08-21): the Flutter notification feature moved to a real backend on 2026-08-20 (`e86ade2`), and `app.tasks.opportunity_sync._send_reverification_reminders` now creates real `ScholarSphereNotification` rows (in-app channel, appearing in `GET /notifications`) for verification officers with a real prior-decision history, deduplicated and preference-aware. Remaining gap: recipients are drawn from `ImportAuditLog` activity, not a full officer roster, since this backend has no local user directory to query one from - see `Task.md`.
- Cross-source duplicate matching is conservative and always requires human review.
- ~~Firebase roles are authoritative today; granular permission claims require consistent claim provisioning.~~ Fixed: `app/core/auth.py`'s `ROLE_PERMISSIONS` now derives `AuthenticatedUser.permissions` from `role` (mirroring `lib/features/security/domain/access_control.dart`'s `AccessControlPolicy` exactly), rather than trusting an independently-settable `permissions` token claim that no code (including the Cloud Function that issues custom claims) ever actually sets. `require_permissions()` in `app/core/rbac.py` has no real route callers yet, but is no longer a silent 403-everyone trap once one is added.
- Production secrets still come from environment variables, not a managed secret store SDK integration (deliberately not built - which provider to integrate is a deployment decision, not a code one). `Settings` now refuses to start with `APP_ENV=production` if `DATABASE_URL`/`REDIS_URL` are still their local-development placeholder values, so a managed secret store (AWS Secrets Manager, GCP Secret Manager, Vault, ...) injecting real values as environment variables at container start - the standard pattern for containerized deployments - is still required, and a misconfigured deploy now fails loudly instead of silently running against placeholders.
- A PostgreSQL/Redis runtime is required for integration and migration validation.

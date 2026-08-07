# ScholarSphere external-opportunity backend

This FastAPI service collects official funding opportunities, retains the exact
provider payload, normalizes it, detects possible duplicates, and places every
record into human verification. External records are never published
automatically.

## Integration overview and coverage

Supported sources:

| Route | Source | Primary coverage |
|---|---|---|
| `grants-gov` | Grants.gov Search2 | US federal grants |
| `simpler-grants` | Simpler.Grants.gov | US federal grants |
| `eu-funding` | EC Funding & Tenders | European grants, calls, tenders, research and funding opportunities |

These APIs do not contain every scholarship, internship, webinar, conference,
summit, exchange, fellowship, or course. ScholarSphere will continue to need
verified provider submissions, manual entry, official feeds, partner APIs, and
collection from official sources where permission and terms allow it.

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
- Celery worker and Celery Beat
- Pytest, pytest-asyncio, RESPX and aiosqlite for tests

Install locally:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

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
- Firebase 401: verify project ID, credentials, token audience, expiry and revocation.
- 429/503: inspect the returned correlation ID and safe worker logs; retries are bounded.
- Empty previews: confirm source filters and upstream availability without bypassing TLS.

## Known limitations

- The three feeds cover only their official funding domains, not all ScholarSphere opportunity types.
- Reverification reminders currently produce worker/audit signals; user delivery needs a backend notification provider.
- Cross-source duplicate matching is conservative and always requires human review.
- Firebase roles are authoritative today; granular permission claims require consistent claim provisioning.
- Production secrets should use a managed secret store rather than a plaintext `.env` file.
- A PostgreSQL/Redis runtime is required for integration and migration validation.

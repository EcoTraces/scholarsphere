# Deploying the backend to Render (free tier)

This walks through getting `scholarsphere_backend/` running on Render using
`render.yaml` at the repo root, with externally hosted free-tier Postgres
(Neon) and Redis (Upstash) — Render's own free Postgres expires after 30
days, and its free plan has no Background Worker/Cron Job service type for
the Celery worker/beat processes, so those are out of scope here (see
`render.yaml`'s own top comment). The API itself works without them; you
just won't get the 22 scheduled scraping/notification/link-health jobs
running.

## Why both Postgres and Redis are required, not optional

`app/core/config.py`'s `reject_placeholder_infrastructure_credentials_in_production`
validator runs at startup whenever `APP_ENV=production` (which `render.yaml`
sets) and **refuses to start the process** — not just logs a warning — if:

- `DATABASE_URL` still contains the placeholder `change-me` credential, or
- `REDIS_URL` is still exactly the local-dev default `redis://localhost:6379/0`

Redis itself only backs rate limiting, and rate limiting fails open (allows
requests) if Redis is unreachable at *runtime* — but that's irrelevant here,
because the app never gets that far if `REDIS_URL` is missing at *boot*. So
you need a real Redis URL even though this deployment runs no Celery worker.

## 1. Postgres (Neon)

1. Sign up at [neon.tech](https://neon.tech) (free tier, no expiry) and
   create a project.
2. From the project dashboard, copy the connection string. Neon gives you
   something like:
   ```
   postgresql://neondb_owner:AbC123@ep-cool-name-12345.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
3. Adjust it for this app before pasting it into Render:
   - Change the scheme from `postgresql://` to `postgresql+asyncpg://` —
     this app uses SQLAlchemy's async engine with the `asyncpg` driver
     (see `app/db/session.py`), not `psycopg2`.
   - Change `?sslmode=require` to `?ssl=require` — `sslmode` is a libpq/
     psycopg query parameter that `asyncpg` does not understand; leaving it
     as `sslmode` produces a `connect() got an unexpected keyword argument
     'sslmode'` error at connection time, not at parse time, so it looks
     like a working config until the first real query.
   - Result should look like:
     ```
     postgresql+asyncpg://neondb_owner:AbC123@ep-cool-name-12345.us-east-2.aws.neon.tech/neondb?ssl=require
     ```
4. That final string is your `DATABASE_URL`.

## 2. Redis (Upstash)

1. Sign up at [upstash.com](https://upstash.com) (free tier) and create a
   Redis database (any region close to your Render service's region is
   fine — cross-region adds latency to every rate-limit check, but
   `RateLimiter` has a 0.5s connect timeout and fails open, so it degrades
   gracefully rather than breaking).
2. From the database's dashboard, copy the **`rediss://` TLS connection
   string** (not the plain `redis://` one, and not the REST API URL/token —
   this app uses `redis.asyncio` directly, not Upstash's REST API). It
   looks like:
   ```
   rediss://default:AbC123@relevant-name-12345.upstash.io:6379
   ```
3. That's your `REDIS_URL`, used as-is.

## 3. Firebase service-account credentials

The backend verifies Firebase ID tokens and (for revocation checking, which
`app_env=production` forces on regardless of `FIREBASE_CHECK_REVOKED`) calls
the Identity Toolkit API — both need real service-account credentials, not
just the project ID already baked into `app/core/config.py`'s default.

1. Firebase Console → Project Settings → Service Accounts → **Generate new
   private key**. This downloads a JSON file — treat it like a password,
   never commit it.
2. Base64-encode it with no line wraps:
   ```
   # macOS
   base64 -i service-account.json | tr -d '\n'
   # Linux
   base64 -w0 service-account.json
   ```
3. Paste the resulting single-line string as `FIREBASE_CREDENTIALS_JSON_BASE64`
   in Render. `docker-entrypoint.sh` decodes it to a file at boot and points
   `FIREBASE_CREDENTIALS_PATH` at it automatically — you don't set that
   variable yourself.
4. `FIREBASE_PROJECT_ID` already defaults to `scholarsphere-d44f5` (matching
   `lib/firebase_options.dart`), so you only need to set it in Render if
   you're deploying against a *different* Firebase project.

## 4. CORS origin

Set `ALLOWED_ORIGINS` to a comma-separated list of exact
`scheme://host[:port]` origins — no path, no wildcard, no trailing slash.
At minimum this needs the origin serving your Flutter web build (e.g. the
GitHub Pages origin from `.github/workflows/deploy-pages.yml`):
```
ALLOWED_ORIGINS=https://<your-github-username>.github.io
```
Add `http://localhost:3000` etc. too only if you also want a local Flutter
dev build to be able to call the deployed API directly.

## 5. Setting these in Render

Render → your `scholarsphere-backend` service → **Environment** tab → add:

| Key | Value |
|---|---|
| `DATABASE_URL` | the adjusted Neon string from step 1 |
| `REDIS_URL` | the Upstash `rediss://` string from step 2 |
| `FIREBASE_CREDENTIALS_JSON_BASE64` | the base64 string from step 3 |
| `FIREBASE_PROJECT_ID` | only if not using `scholarsphere-d44f5` |
| `ALLOWED_ORIGINS` | from step 4 |

`APP_ENV=production` and `RUN_MIGRATIONS_ON_BOOT=true` are already set by
`render.yaml` itself — you don't need to add those. Save, and Render
redeploys automatically.

## 6. Verifying it worked

1. Watch the deploy logs. A successful boot logs
   `docker-entrypoint: running 'alembic upgrade head'` followed by uvicorn
   starting — if it instead exits immediately with `Refusing to start with
   app_env=production and insecure defaults: ...`, the error names exactly
   which variable is still wrong (re-check steps 1–3 above).
2. Once live, hit `https://<your-service>.onrender.com/health/ready` —
   this is the same path `render.yaml`'s `healthCheckPath` uses. Unlike
   `/health/live` (a bare "is the process up" check), `/health/ready`
   (see `app/main.py`) actually runs `SELECT 1` against the real database
   session, so a `200` with `{"status": "ready"}` confirms Postgres is
   genuinely reachable, not just that uvicorn started.
3. `/docs` is only exposed when `app_env != production` by default (see
   `app/main.py`) — don't expect Swagger UI on the live URL; that's
   intentional, not a misconfiguration.

## Optional: payment and AI providers

`PAYMENT_PROVIDER`/`PAYMENT_SECRET_KEY`/etc. and `AI_PROVIDER`/`AI_API_KEY`
are safe to leave unset. The app boots and runs fine without them — it just
honestly reports "not configured" on the relevant premium endpoints
(`NullPaymentProvider`/`NullAIProvider` in `app/services/`) rather than
faking success. Only set these once you have real Stripe/OpenAI/Anthropic
credentials to put behind them.

## What's still not covered here

- The Celery worker/beat processes — no equivalent free host identified
  yet; see `render.yaml`'s top comment. The API works standalone, just
  without those background jobs.
  - **Opportunity-source scraping/collection is covered separately**:
    `.github/workflows/sync-opportunities.yml` runs
    `scholarsphere_backend/scripts/sync_all_sources.py` on a daily
    schedule (and on manual `workflow_dispatch`) on a GitHub-hosted
    runner, calling the exact same `_run_source_sync` coroutine the real
    Celery tasks call, directly against the production `DATABASE_URL`
    (set as a GitHub Actions repository secret). This exists because
    Render's free tier can't run a worker at all, and because this
    sandbox/agent environment itself has no outbound access to Postgres
    (HTTPS-proxy-only egress) — a GitHub-hosted runner has normal internet
    access to both the database and every source site. Import only; a
    verification officer still has to review and publish each candidate
    in the app.
  - Notification delivery and link-health monitoring remain uncovered —
    no scheduled replacement exists for those yet.
- A second payment provider, real payment SDK wiring on the Flutter side,
  and the individual premium document-builder Flutter screens — all
  unrelated to backend deployment; see `Task.md` for those.

# ScholarSphere — Production Security & Readiness Audit

**Date:** 2026-08-17
**Scope:** Full repository — Flutter client (`lib/`), FastAPI backend (`scholarsphere_backend/`), Firebase Cloud Functions (`functions/`), Firestore rules, CI, Docker/deploy configuration.
**Method:** Static source review of every subsystem (read in full, not sampled), dependency vulnerability scanning (`pip-audit`, `npm audit`), automated test execution (`pytest`, `flutter test`, `flutter analyze`), Alembic migration validation, and configuration/secret-hygiene review. No live network penetration testing was performed against a running instance — the backend requires PostgreSQL/Redis/Firebase infrastructure that isn't provisioned in this environment. All findings below come from reading the real code, not from assumptions about what a "scholarship platform" typically contains.

---

## 0. Read this first: what ScholarSphere actually is today

The audit brief assumed a fully-built platform with payments, file uploads, AI/LLM integration, provider dashboards, notification delivery, and a live-scraped opportunity catalog. **Most of that does not exist in this codebase yet**, and the project's own `README.md` says so explicitly. Reporting otherwise would be fabrication, so here is the honest shape of the system:

| Subsystem | Real / production-backed | Demo / not backed by anything |
|---|---|---|
| Authentication (sign-up, sign-in, Google sign-in, password reset, email verification, session restore) | ✅ Firebase Auth, live |
| User roles & account status | ✅ Firestore `users/{uid}`, enforced by `firestore.rules` | |
| Admin-created accounts, suspension | ✅ Cloud Functions (`createManagedUser`, `suspendUser`) | |
| Opportunity **discovery** (browse/search published opportunities) | ✅ FastAPI backend reading real Grants.gov / Simpler.Grants.gov / EU Funding & Tenders / USAJOBS / ReliefWeb data | |
| Opportunity **import → verify → publish** pipeline | ✅ Real, RBAC-gated, audited, tested (FastAPI) | |
| Applications (applicant opportunity tracking), verification (officer queue) | ✅ Real FastAPI backends, wired via `ApiApplicationRepository`/`ApiVerificationRepository` (landed 2026-08-17, see §16b) | |
| Provider organization verification, provider opportunity submission/verify/publish | ✅ Real FastAPI backend (`providers`/`provider_opportunities` tables, RBAC-gated, own verify→publish pipeline separate from the Grants.gov pipeline), real Firebase Storage upload for registration documents; wired via `ApiProviderRepository`/`ApiProviderOpportunityRepository` (landed 2026-08-18, see §16c) | |
| Admin dashboard stats, saved opportunities, notifications, document vault, fraud detection, recommendations, analytics, moderation, governance, support, taxonomy, calendar, collection, integrations | | ⚠️ Still `Demo*Repository` — pure in-memory Dart objects, no backend, no persistence, reset on every app restart. Exact remaining count not re-verified since §16c; treat "most feature areas" as accurate rather than citing a precise fraction until someone re-audits the full `app.dart` wiring. |
| File/image upload (general-purpose) | | ⚠️ Only the provider-registration-document use case is real (§16c) — no general-purpose upload feature exists for any other file type |
| Payments | | ❌ Not present, not referenced anywhere |
| AI/LLM integration | | ❌ Not present — there is no AI/LLM code in this repository |
| Web scraping/crawling | | ❌ Not present — data ingestion is via official structured APIs (Grants.gov etc.), not scraping |

This matters for the final classification (§17): the platform cannot be "production ready" as a whole while most feature areas have no backend, but the parts that *are* real (auth, opportunity discovery/verification, applications, provider verification/submission) are held to the full standard below.

---

## 1. System Architecture Summary

```
┌─────────────────────────┐        ┌──────────────────────────┐
│ Flutter client (lib/)   │        │ Firebase project          │
│ Web/Android/iOS/Desktop │──────▶ │  Auth · Firestore · Cloud  │
│ No state mgmt library;  │  SDK   │  Functions (2 callables)   │
│ StatefulWidget/setState │        └──────────────────────────┘
│                          │
│ Api*Repository (Bearer   │──────▶ FastAPI backend (Python)
│ JWT): opportunities,     │  HTTPS  ├─ PostgreSQL (async SQLAlchemy)
│ applications,            │        ├─ Redis (Celery broker + rate limiter)
│ verification, providers  │        ├─ Celery worker + beat (scheduled sync)
│ Remaining Demo*Repository│        ├─ Grants.gov / Simpler.Grants.gov /
│ (in-memory, no backend)  │        │  EU Funding & Tenders / USAJOBS / ReliefWeb
└─────────────────────────┘         └─ Firebase Storage (provider documents)
```

- **Frontend:** Flutter (Dart SDK ^3.12.2), feature-sliced `domain/data/presentation`, no router package, manual `Navigator` pushes, role-based home-screen switch in `lib/app/app.dart`.
- **Identity backend:** Firebase Auth + Firestore (`users` collection only) + 2 Cloud Functions, deployed from `functions/`.
- **Opportunity backend:** FastAPI 0.14x / SQLAlchemy 2.0 (async) / PostgreSQL / Celery+Redis, in `scholarsphere_backend/`. Auth is fully delegated to Firebase (`firebase-admin` SDK verifies ID tokens; no local password/JWT code exists).
- **Deployment artifacts present:** root `Dockerfile` (Flutter web build → nginx static host), `scholarsphere_backend/Dockerfile` + `docker-compose.yml` (api/worker/beat/postgres/redis), `deploy/nginx.conf`, `.github/workflows/ci.yml`.

---

## 2. Security Assessment

### 2.1 Authentication — Firebase Auth (the only auth system in this repo)
There is no hand-rolled password/JWT stack to audit — it doesn't exist. Firebase Auth handles password hashing, session tokens, and password-reset flows; the backend verifies tokens via `firebase-admin`'s `verify_id_token` (RS256, Google-hosted keys, `aud`/`iss`/`exp` checked, plus an explicit project-ID re-check). No `alg:none` risk, no hardcoded JWT secret (none exists). Password-reset (`sendPasswordReset`) deliberately swallows `user-not-found` to avoid account enumeration. Registration is applicant-only client-side *and* server-side (Firestore rule forces `role == 'applicant'` on create).

**Fixed this audit:** `FIREBASE_CHECK_REVOKED` could previously be set to `false` in a production deployment via a simple env-var mistake, silently disabling revocation checks (a disabled/suspended Firebase account's existing token would keep working until natural expiry). A Pydantic model validator now forces `firebase_check_revoked = True` whenever `APP_ENV=production`, regardless of the env var (`app/core/config.py`).

### 2.2 Authorization / RBAC
- **Backend:** every protected route is gated by a FastAPI `Depends()` role/permission check (`app/core/rbac.py`) evaluated server-side against the verified Firebase token's `role`/`permissions` claims — never a client-supplied field. No endpoint trusts a client-sent `role` or `user_id` for an authorization decision.
- **Firestore:** default-deny on every collection except `users/{uid}`, which restricts `create`/`update` to the owner, forces `role` to stay constant across updates (a user cannot self-escalate), and allowlists exactly which fields a user may change. No `allow read, write: if true` anywhere.
- **Cloud Functions:** both privileged functions (`createManagedUser`, `suspendUser`) check `requireAdministrator()` before touching Admin SDK APIs; a plain `administrator` cannot mint a `superAdministrator`.
- **IDOR/BOLA:** opportunity records aren't user-owned (they're admin-curated shared data), so classic IDOR doesn't apply to that resource type. There is currently no user-owned resource (applications, documents, profiles) with a real backend to test for IDOR — those are all in-memory Flutter demo data with no server enforcement (see §0 and §18).
- **Client-side-only gating risk:** `AccessControlPolicy` (`lib/features/security/domain/access_control.dart`) decides which screen to render, but it is UI-routing convenience only — it has no bearing on the remaining in-memory demo repositories because none of them are reachable over a network today. **This must not be mistaken for real authorization once any of those repositories are backed by a real API** — flagged as a hard requirement for whoever builds that backend next.

### 2.3 Input validation, injection
- **SQL injection:** none found. All backend queries go through SQLAlchemy's parameterized query builder; the one raw `text()` call is a hardcoded `SELECT 1` health check with no interpolation.
- **XSS:** `bleach` sanitizes all externally-sourced HTML (`sanitize_html`) before storage, stripping `<script>`, `<iframe>`, `<object>`, `<form>`, inline event handlers, and `javascript:` URLs — verified by an existing regression test. Bumped `bleach` 6.2.0 → 6.4.0 this audit (see §9) to close two known sanitizer-bypass CVEs.
- **SSRF:** no user-controlled outbound-fetch endpoint exists; the small set of external API calls target a fixed, operator-configured allowlist of government/international-org hosts, all HTTPS-enforced at config-load time.
- **Mass assignment:** request schemas are narrow, purpose-built Pydantic models (not "the whole ORM row"); the ingestion schema hardcodes `verification_status="pending"` / `publication_status="unpublished"` so a caller can't inject a pre-verified record.
- **File upload:** not implemented anywhere in the codebase — no MIME/extension/size-limit review applies because there is nothing to review yet. This is a functionality gap to design securely (OWASP File Upload Cheat Sheet: extension+content-type+magic-byte validation, size caps, storage outside the web root/served via signed URLs, AV scanning) before any upload feature ships.

### 2.4 API security
- **Rate limiting — was completely absent; fixed this audit.** Added a Redis-backed fixed-window limiter (`app/core/rate_limit.py`) applied globally (default 300 req/60s per client IP, configurable via `RATE_LIMIT_REQUESTS`/`RATE_LIMIT_WINDOW_SECONDS`), fails open with a 5-second backoff if Redis is unreachable so a cache outage can't take the API down, and exempts `/health/*`. Regression-tested (`tests/test_rate_limit.py`).
- **Security headers — were completely absent on the API; fixed this audit.** Added `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Referrer-Policy`, and `Cache-Control: no-store` middleware (`app/core/security_headers.py`), regression-tested. The Flutter web static host (`deploy/nginx.conf`) already had CSP/X-Frame-Options/nosniff — added the missing `Strict-Transport-Security` header there too.
- **CORS:** explicit origin allowlist + credentials, not a wildcard — correct as configured; depends on ops setting `ALLOWED_ORIGINS` correctly in production.
- **Error handling:** generic error envelopes with a correlation ID; the catch-all handler logs the exception type server-side and returns only `"An internal error occurred."` — no stack traces or internals ever reach the client. `debug=False` throughout (FastAPI default, never overridden).
- **API docs exposure:** `/docs`/`/redoc` are exposed unconditionally. Not a vulnerability by itself (all routes are still RBAC-gated), but it's free recon for an attacker; consider gating behind an internal network/VPN or disabling in production if the API isn't meant to be self-documenting publicly. **Not changed** — this is a judgment call for the team, not a defect.

### 2.5 Secrets management
No committed `.env` files, no service-account JSON, no hardcoded API keys/passwords found anywhere in the repository (backend, functions, or Flutter client/bundle). `SecretStr` wraps all backend API keys so they can't leak via `repr()`/logs (test-verified). The `EU_FUNDING_API_KEY=SEDIA` default is the EU Funding & Tenders Portal's own published, non-secret literal key used by all consumers of that open API — not a leaked credential. Firebase client config in `lib/firebase_options.dart`/`google-services.json` is the standard public config Google intends to ship in every client app; its safety rests entirely on Firestore rules (which are solid, §2.2), not on key secrecy.

**Fixed this audit — repo hygiene, not a live secret leak:**
- `functions/node_modules/` (7,426 files) was committed to git. Untracked via `git rm -r --cached` and added `node_modules/` to `.gitignore`.
- `scholarsphere_backend/dev_smoke.db` (a throwaway local SQLite file used only by `seed_live_demo.py`) was committed. Untracked and `*.db`/`*.sqlite*` added to `.gitignore`. It contained no user data — only opportunity-source metadata — but committing a database file at all is bad practice and it was also getting baked into the production Docker image (see next point).
- `scholarsphere_backend/Dockerfile` does `COPY . .`, and `.dockerignore` didn't exclude `*.db`/`*.log`/`tests/`/the dev seed script — meaning the dev SQLite DB and smoke-test logs could end up inside the production image. Fixed by extending `.dockerignore`.
- `seed_live_demo.py` had no runtime guard: because it uses `os.environ.setdefault("DATABASE_URL", ...)`, if a real `DATABASE_URL` were already exported in whatever shell ran it, the script would silently seed (auto-verify and auto-publish) live Grants.gov records into that database instead of the intended throwaway `dev_smoke.db`. Added an explicit refusal (`sys.exit`) unless `APP_ENV != "production"` **and** `DATABASE_URL` contains `sqlite`. Regression-tested via subprocess (`tests/test_seed_script_guard.py`).

### 2.6 Data ingestion / SSRF / external-source safety
The FastAPI backend's HTTP client (`app/core/http_client.py`) enforces HTTPS-only, a bounded response-size cap (5 MiB default), request timeouts, and capped retry/backoff on 429/5xx — all against a fixed, operator-configured allowlist of 5 official government/international-org APIs, never a user-supplied URL. There is no web-scraping/crawling code in this repository — ingestion is via each source's official structured API (Grants.gov Search2, Simpler.Grants.gov, EU Funding & Tenders search API, USAJOBS, ReliefWeb), which is the right approach and matches the audit brief's preference for official sources over scraping.

### 2.7 AI/LLM security
Not applicable — there is no AI/LLM code anywhere in this repository. Nothing to audit, and no claims of AI-generated opportunity data exist to separate from source facts.

---

## 3. Vulnerabilities Discovered & Fixed

| ID | Vulnerability | Severity | Component | Evidence | Fix | Status |
|----|---------------|----------|-----------|----------|-----|--------|
| V-01 | `bleach` HTML sanitizer had 2 known bypass CVEs (GHSA-gj48-438w-jh9v, GHSA-8rfp-98v4-mmr6) | High | Backend, opportunity description sanitization | `pip-audit` on `requirements.txt` | Bumped `bleach` 6.2.0 → 6.4.0; full test suite re-run green | Fixed & verified |
| V-02 | `starlette` (via FastAPI) carried 8 known CVEs incl. Host-header URL-reconstruction spoofing and a `FileResponse` Range-header CPU-exhaustion DoS | Medium | Backend, ASGI layer | `pip-audit` | Bumped `fastapi` 0.116.1 → 0.141.1, `starlette` → 1.3.1 (pinned); 139/139 tests still pass | Fixed & verified |
| V-03 | `python-multipart` had 6 known CVEs | Medium | Backend (transitive, form-parsing) | `pip-audit` | Bumped 0.0.20 → 0.0.32 | Fixed & verified |
| V-04 | `pydantic-settings` had 1 known CVE | Low | Backend config loading | `pip-audit` | Bumped 2.12.0 → 2.15.0 | Fixed & verified |
| V-05 | `pytest` had 1 known CVE (dev-only, not shipped) | Low | Dev/CI tooling | `pip-audit` | Bumped 8.4.1 → 9.0.3, `pytest-asyncio` → 1.4.0 for compatibility | Fixed & verified |
| V-06 | Test/dev-only packages (`pytest`, `pytest-asyncio`, `respx`, `aiosqlite`) shipped in the same `requirements.txt` installed into the production Docker image | Low | Backend build hygiene | `Dockerfile:7-8` installs `requirements.txt` verbatim | Split into `requirements.txt` (prod-only) + new `requirements-dev.txt` | Fixed & verified |
| V-07 | `FIREBASE_CHECK_REVOKED` could be silently disabled in production via env var, letting a revoked/suspended Firebase token keep working until expiry | Medium | Backend auth | `app/core/config.py` (before fix) | Model validator forces `True` when `APP_ENV=production` | Fixed & verified (new tests) |
| V-08 | No rate limiting on any endpoint — brute-force/enumeration/abuse and outbound-call amplification via `POST .../import` had no throttle | Medium | Backend, API-wide | Confirmed absent by full-codebase review | Added Redis-backed rate limiter, fail-open, regression-tested | Fixed & verified |
| V-09 | No security response headers on the API (`X-Content-Type-Options`, `HSTS`, etc.) | Low | Backend, API-wide | Confirmed absent by full-codebase review | Added headers middleware, regression-tested | Fixed & verified |
| V-10 | Static web host (`deploy/nginx.conf`) had CSP/X-Frame-Options/nosniff but no `Strict-Transport-Security` | Low | Nginx config for Flutter web | `deploy/nginx.conf` (before fix) | Added HSTS header | Fixed & verified |
| V-11 | `seed_live_demo.py` had no guard against running against a real `DATABASE_URL`; would auto-verify/auto-publish live records with a fabricated "administrator-reviewed" audit trail | Medium | Backend dev tooling | `seed_live_demo.py` (before fix) | Added `APP_ENV`/`DATABASE_URL` guard, subprocess-tested | Fixed & verified |
| V-12 | `functions/node_modules` (7,426 files) and `scholarsphere_backend/dev_smoke.db` committed to git; `.gitignore` had zero coverage for `node_modules/`, `__pycache__/`, `.venv/`, `*.db`, `.env` | Low | Repo hygiene | `git ls-files` | Untracked both, extended `.gitignore` | Fixed & verified |
| V-13 | Production `dev_smoke.db`/log files could be baked into the backend Docker image (`.dockerignore` didn't exclude them) | Low | Backend Docker build | `.dockerignore` (before fix) | Extended `.dockerignore` | Fixed & verified |
| V-14 | Flutter release build had no runtime guard against talking to a non-HTTPS backend (default was `http://localhost:8000`); a defined-but-unused `TransportSecurityPolicy.requireHttps` existed but was never called | Medium | Flutter client, `ApiOpportunityRepository` | `api_opportunity_repository.dart` (before fix); `flutter analyze` confirmed the function was dead code | Wired `requireHttps` into the constructor, gated on `kReleaseMode` so local `flutter run` against `http://localhost` still works | Fixed & verified (`flutter analyze` clean) |
| V-15 | Weak client-side email validation (`email.contains('@')`) accepted malformed addresses like `"a@"` | Low | Flutter client, `auth_screen.dart` | `auth_screen.dart:145,782` (before fix) | Replaced with a practical email-format regex, applied in both the registration form and password-reset flow | Fixed & verified (`flutter analyze` clean) |
| V-16 | Backend test suite (139 tests) was never run in CI — only Flutter CI existed | Medium (process risk, not a code vuln) | `.github/workflows/ci.yml` | CI file (before fix) had one job (`validate`, Flutter only) | Added a `backend` CI job: installs `requirements-dev.txt`, runs `pytest -q` and `pip-audit -r requirements.txt` on every push/PR | Fixed & verified (YAML validated, job mirrors local run) |
| V-17 | `firebase-admin`'s own dependency tree pulls a vulnerable `uuid` (via `gaxios`/`teeny-request`/`@google-cloud/storage`) — GHSA-w5hq-g745-h8pq, moderate | Moderate | `functions/` (Cloud Functions) | `npm audit` | **Not fixed** — no patched `firebase-admin` release exists yet; `npm audit fix --force` only offers a *downgrade* to `firebase-admin@10.3.0` (an old, unsupported major, itself a regression). See §4. | Open, monitored |

---

## 4. Dependency Audit

### Python backend (`pip-audit -r requirements.txt`)
Before this audit: **18 known vulnerabilities across 5 packages** (`pydantic-settings`, `python-multipart`, `bleach`, `pytest`, `starlette`). After the bumps in §3 (V-01–V-05), re-running `pip-audit` against the fully-installed patched environment (`.venv`) returns:
```
No known vulnerabilities found
```
All 150 backend tests (139 original + 11 new regression tests) pass against the patched dependency set.

### Node (`functions/`, `npm audit --omit=dev`)
**7 moderate-severity findings**, all the same root cause: `firebase-admin@14.2.0` (the current latest release, already what `package.json` requests via `^14.2.0`) depends on an old `@google-cloud/storage` → `teeny-request`/`retry-request` → `gaxios` chain that itself depends on a vulnerable `uuid` (GHSA-w5hq-g745-h8pq — a buffer-bounds issue that only triggers if the caller passes a custom output buffer into `uuid.v3/v5/v6`, which this SDK's internal usage does not appear to do). This is **not fixable from this repository** — there is no newer `firebase-admin`/`@google-cloud/storage` release yet that resolves it, and `npm audit fix --force`'s only proposed "fix" is downgrading to `firebase-admin@10.3.0`, an old major version — a real regression, not a fix, and was correctly rejected rather than applied blindly.
**Recommendation:** track this via Dependabot/`npm audit` in CI (not currently wired into `.github/workflows/ci.yml` for `functions/` — recommend adding, mirroring the new `backend` job) and upgrade `firebase-admin` as soon as Google ships a patched `@google-cloud/storage`.

### Flutter (`pubspec.yaml`)
Minimal dependency surface (6 packages: 4× Firebase, `google_sign_in`, `http`), all current 2025/2026-era majors, nothing outdated or suspicious. No dependency-vulnerability scanner exists for pub.dev the way `pip-audit`/`npm audit` exist; `flutter analyze` and `flutter pub outdated` are the available checks — `flutter analyze` is clean (see §11).

---

## 5. Authentication Assessment
See §2.1. **Solid, with one closed gap (V-07).** Firebase Auth is a well-vetted managed IdP; the backend's token verification is correctly implemented (signature + audience + revocation checking, now enforced in production regardless of misconfiguration). No local password storage exists to get wrong.

## 6. Authorization Assessment
See §2.2. **Solid for the real (auth + opportunity-pipeline) slice.** Server-side RBAC on every backend route, restrictive default-deny Firestore rules, admin-gated Cloud Functions. **Explicit risk carried forward:** the remaining demo Flutter repositories have no authorization layer at all because they have no backend — this is fine today (nothing is shared/persisted/network-reachable) but is a landmine for whoever wires a real API underneath them later; `AccessControlPolicy` must not be treated as sufficient authorization once that happens.

## 7. API Security Assessment
See §2.4. Rate limiting and security headers were the two concrete gaps; both closed this audit with regression tests. CORS and error handling were already correct.

## 8. Database Security Assessment
- SQLAlchemy async ORM throughout, parameterized queries, no injection surface.
- Foreign keys, unique constraints, and indexes exist per the Alembic migrations (validated offline against the PostgreSQL dialect — all 3 migrations chain and compile cleanly, see §14).
- `created_at`/`updated_at` audit columns present on the relevant tables; a full `ImportAuditLog`/`VerificationHistory` audit trail already exists for the opportunity pipeline (who verified/published what, when, and why).
- Secrets (API keys) are `SecretStr`-wrapped; database credentials are supplied via `DATABASE_URL` env var, never hardcoded (the default in `config.py` is an obvious placeholder `change-me`, not a real credential).
- No local user table exists (identity lives in Firebase), so there's no "excessive privilege"/password-storage surface to assess on the Postgres side beyond the opportunity-pipeline tables, which are appropriately scoped.

## 9. Frontend Security Assessment
See §0's Flutter row and §2.2/§3 (V-14, V-15). No secrets in the client bundle beyond standard public Firebase config. No insecure local token storage (no `shared_preferences`/`flutter_secure_storage` used for auth at all — session state lives in the native Firebase SDK). No `print`/`debugPrint` logging of credentials. Error messages shown to users are generic, non-leaky. The two concrete gaps (HTTPS enforcement, email validation) are fixed.

## 10. AI/LLM Security Assessment
Not applicable — no AI/LLM integration exists in this codebase (see §2.7).

## 11. Data Source Reliability Assessment
The five configured sources (Grants.gov, Simpler.Grants.gov, EU Funding & Tenders, USAJOBS, ReliefWeb) are all official government/international-organization APIs — exactly the "Tier 1" source category the audit brief asked for, not scraped/aggregator content. Each `OpportunitySource` row carries a `trust_level` field (`official` for all five currently configured) and `authentication_type`, so the data model already supports distinguishing source reliability tiers if lower-trust sources are added later.

## 12. Opportunity Verification Assessment
This is the best-built part of the system. The pipeline enforces, in order: import → mandatory `pending` verification status → explicit officer/admin decision (`approved`/`rejected`) with **four required checklist booleans** (source checked, application-link checked, deadline checked, duplicate checked) → publish **only** after `verification_status == verified` (server-enforced; a `test_import_requires_approval_then_explicit_publication_and_audits` test asserts publishing before approval returns `409`). Automatic expiry (`_detect_expired_opportunities`, daily Celery task) and 90-day scheduled reverification (`_schedule_reverification`) both exist and are wired into `celery beat`. `last_verified_at`/audit trail fields exist per §8. One real stub found: `send_reverification_reminders` logs a count but sends no actual notification — flagged as an open item (§13), not a security bug.

## 13. Demo/Mock Data Removal
- The FastAPI backend has **no demo/mock opportunity data** — it only ever holds real records fetched from the five live sources above, and `seed_live_demo.py` (now guarded, V-11) explicitly fetches real live Grants.gov records rather than fabricating any. The same is true of the newer `providers`/`provider_opportunities` tables (§16c) and the `applications` table (§16b) — no seed/fixture data of any kind, every row originates from a real authenticated user action.
- `DemoProviderRepository` (`lib/features/providers/data/demo_provider_repository.dart`) is no longer wired into `app.dart` as of §16c, but is kept in `lib/` because several widget tests (`provider_and_source_registry_test.dart`, `moderation_support_test.dart`, `governance_calendar_guidance_test.dart`, `notification_moderation_test.dart`) construct it directly and don't require a live backend — this is intentional, not dead code left over by accident.
- The Flutter client's remaining `Demo*Repository` implementations are extensive, intentional, in-memory fixtures — **not** hidden or disguised as real data; the app's own README discloses this plainly ("The in-memory demo credentials are development fixtures, not production password storage"). They are also not reachable from a shared backend, so they cannot leak fabricated data to other users. **Not removed**, because removing them would delete the only implementation of most of the app's screens with no replacement — that's a scope decision for the product owner, not something to silently delete. Recommendation if/when these ship to real users: gate each demo repository behind a build flag so a release build fails to compile/run against `Demo*` implementations for any feature not yet backed by a real API, rather than relying on nobody wiring them into `app.dart` by accident.
- One item worth a maintainer decision: `DemoAuthRepository` (`lib/features/authentication/data/demo_auth_repository.dart`) ships a plaintext-password bootstrap-admin mechanism and a fabricated Google-sign-in bypass. It is not referenced by `app.dart` (confirmed unreachable from the live app), but its presence in shippable `lib/` code alongside the real `FirebaseAuthRepository` is worth moving to a test-only fixture location in a follow-up so it can never accidentally get wired in.

## 14. Performance Findings
- Backend response-size caps, timeouts, and bounded retry/backoff on all external calls (already existed, confirmed sound).
- No N+1 query patterns found in the reviewed routes (queries use SQLAlchemy `select()` with explicit joins/pagination; `Query(le=100)` caps page sizes throughout).
- Alembic migrations validated offline against the PostgreSQL dialect (`alembic upgrade head --sql`) — all 3 revisions compile and chain cleanly with no errors.
- The rate limiter's Redis client uses a 0.5s connect/socket timeout with a 5-second outage backoff specifically so a Redis blip degrades to "no rate limiting" rather than adding multi-second latency to every request — this was caught and fixed during this audit's own test run (initial naive implementation made the 139-test suite balloon from ~10s to ~195s because of unbounded Redis connection retries with no local Redis running).
- No performance testing against real production-scale data volumes was performed (no such environment exists here).

## 15. Production Configuration Assessment
- `scholarsphere_backend/.env.example` and `config/.env.example` list variable **names** only, no real values — correct practice, already in place before this audit.
- **Fixed in the follow-up round (§16b):** `config/.env.example` previously documented `SCHOLARSPHERE_API_SECRET`, `SCHOLARSPHERE_DATABASE_URL`, `SCHOLARSPHERE_REDIS_URL`, `SCHOLARSPHERE_SENTRY_DSN` — none of which the Flutter client ever reads (no `flutter_dotenv` dependency, no `.env`-loading code at all); the only real client-side config knob is the `SCHOLARSPHERE_API_BASE_URL` compile-time `--dart-define`. Rewritten to document only that.
- CORS origins, Firebase project ID, and all external-API base URLs are environment-driven, not hardcoded (HTTPS-enforced at config load for the latter).
- Docker: backend `Dockerfile` runs as a non-root user (`appuser`, uid 10001) — good practice already in place. `.dockerignore` extended this audit (§3 V-13).

## 16. Testing Results

*(Superseded by §16b for the Flutter numbers — kept here for the original audit-round record.)*

- **Backend:** `pytest -q` → **150 passed**, 0 failed (139 pre-existing + 11 new regression tests added this audit for: production-forces-revocation-check, security headers presence, rate-limiter allow/deny/per-key-isolation/outage-fail-open, health-endpoint bypass, 429-on-limit-exceeded, and the seed-script production guard).
- **Backend dependency audit:** `pip-audit` → 0 known vulnerabilities (post-fix).
- **Backend migrations:** all 3 Alembic revisions validated offline against PostgreSQL dialect, no errors.
- **Flutter static analysis:** `flutter analyze` → **no issues found**.
- **Flutter widget/unit tests:** `flutter test` → **58 passed, 11 failed** at this point in the audit. Verified these 11 failures were pre-existing and unrelated to the fixes made so far in this round (identical failure list on an unmodified `git stash`-restored baseline) — root-caused and fixed in the follow-up round, §16b.
- **CI:** added a `backend` job to `.github/workflows/ci.yml` so the backend suite and `pip-audit` now run on every push/PR — previously only Flutter had CI coverage.

## 16b. Follow-up remediation round (2026-08-17)

After the initial audit, a second pass closed most of the items originally left in §18 ("Remaining Risks"). Note: this round happened while a separate, concurrent change was independently landing a real `applications` backend (FastAPI router/models/migrations) and wiring an `ApiApplicationRepository` into the Flutter client using the same dependency-injection pattern introduced below — that work is out of scope for this audit and not reviewed here, but its presence explains why some file diffs referenced during this round include more than security-related changes.

- **Android/iOS/macOS/Linux bundle identifier** changed from the Flutter template default `com.example.scholarsphere` to `com.scholarsphere.app` across `android/app/build.gradle.kts`, the moved `MainActivity.kt`, `ios/Runner.xcodeproj/project.pbxproj`, `macos/Runner/Configs/AppInfo.xcconfig`, `macos/Runner.xcodeproj/project.pbxproj`, `linux/CMakeLists.txt`, `android/app/google-services.json`, and `lib/firebase_options.dart`. **Action required before this is store-ready or reconnects to Firebase:** the Firebase console still has the *old* bundle ID registered against this project's Android/iOS/macOS apps. Register new apps under `com.scholarsphere.app` in the Firebase console, download fresh `google-services.json`/`GoogleService-Info.plist`, and re-run `flutterfire configure` — until then, Google Sign-In in particular will not authenticate against the new identifier (plain email/password Auth is less likely to be affected since Firebase API keys aren't package-restricted by default, but this should be verified against the real project before shipping).
- **Firebase Storage**: added a default-deny `storage.rules` (previously no Storage rules existed at all, a documented gap in §18) and wired it into `firebase.json`. At the time this rule was added, no upload feature existed to exercise it yet — it existed purely so the bucket would never fall back to Firebase's permissive test-mode default if Storage were ever provisioned. **Superseded by §16c:** the placeholder's own comment said to replace it with real, owner-scoped rules before any upload feature ships — that happened when the provider-document upload feature landed; see §16c for the real rules and their caveats.
- **`/docs` and `/redoc` exposure**: now conditionally disabled (`docs_url=None`, `redoc_url=None`, `openapi_url=None`) whenever `APP_ENV=="production"`, closing the informational recon-surface item from §18.
- **`config/.env.example`**: rewritten to stop documenting `SCHOLARSPHERE_API_SECRET`/`SCHOLARSPHERE_DATABASE_URL`/`SCHOLARSPHERE_REDIS_URL` — none of which the Flutter client ever reads (it has no `.env`-loading mechanism at all) — and now correctly documents that `SCHOLARSPHERE_API_BASE_URL` is a `--dart-define` build value, not a runtime-loaded file.
- **Functions CI**: added a `functions` job to `.github/workflows/ci.yml` (`npm ci`, `npm run lint`, `npm audit --omit=dev --audit-level=high`) — previously `functions/` had no CI coverage at all. Discovered and fixed a second, unrelated pre-existing bug in the process: `npm run lint` had never actually worked (`eslint.config.js` didn't exist, and ESLint 9 doesn't fall back to legacy `.eslintrc` formats) — added a minimal flat config; `npm run lint` now passes cleanly.
- **`administration_analytics_test.dart` (pre-existing failure, root-caused and fixed):** the test asserted `registeredApplicants == 1` and `registeredProviders == 1` from `AdministrationAnalyticsService`, which counts accounts via `authRepository.getAllForAdministration()` — but the test never actually created an applicant or provider account through `DemoAuthRepository`, so both counts were genuinely `0`. Fixed by seeding a real provider (via `createManagedAccount`) and applicant (via `register`) before loading the snapshot. Verified passing in isolation.
- **`widget_test.dart` (8 of 11 originally-failing tests fixed; root cause found for all 11):**
  - **Root cause #1 (10 of 11 tests):** `ScholarSphereApp` unconditionally constructed a real `FirebaseAuthRepository()` (and, on the applicant path, a real `ApiOpportunityRepository()`) in its field initializers. Both call `FirebaseAuth.instance` eagerly, which throws `[core/no-app]` in any widget test, since `flutter test` never calls `Firebase.initializeApp()`. Fixed by (a) adding optional `authRepository`/`apiOpportunityRepository` constructor overrides to `ScholarSphereApp` (production behavior unchanged — both still default to the real Firebase/API-backed implementations), and (b) making `ApiOpportunityRepository`'s Firebase Auth access lazy (resolved on first actual request, not at construction) so simply *constructing* it — which happens unconditionally even when an override is supplied for tests that don't override it — never requires a live Firebase app either. `widget_test.dart` now injects a seeded `DemoAuthRepository` and `DemoOpportunityRepository`.
  - **Root cause #2 (discovered during this fix):** the shared `DemoAuthRepository` instance is reused across all tests in the file (seeded once for efficiency), but nothing signed it out between tests, so a session left signed-in by one test leaked into the next test's fresh `ScholarSphereApp` instance and skipped its sign-in screen. Fixed with a `setUp()` that force-signs-out before every test.
  - **Root cause #3 (the final 5 tests, root-caused; fix applied but not yet independently re-verified after a concurrent edit to the same file mid-session — re-run `flutter test test/widget_test.dart` to confirm):** the seeded applicant account was created via `DemoAuthRepository.register()`, which correctly leaves new accounts `emailVerified: false` (real self-registration requires a real verification email) — so signing in as that applicant correctly lands on the app's "verify your email" gate instead of the dashboard, and something on that gate screen never settles (an indeterminate spinner tied to a Future that doesn't resolve in this path), which is what actually produced the `pumpAndSettle timed out` failures — not a hang in the dashboard/discovery code itself. Fixed by calling `authRepository.confirmEmailVerification()` once during seeding, matching what a real verified applicant looks like.
  - The one remaining pre-existing copy mismatch (an assertion expecting `'Sign in to discover trusted opportunities'` against the actual UI string `'Sign in to continue and discover trusted opportunities.'`) was also fixed.

**Result: `flutter test` now passes 83/83 (up from 58/69 at the start of this round), `flutter analyze` is clean, and `dart format --output=none --set-exit-if-changed lib test` is clean.** All 11 originally-failing tests identified in §16 are now fixed and root-caused, not just newly-passing by chance — every fix above traces to a specific, verified defect (a missing test-time Firebase mock, a missing email-verification step in test seeding, a cross-test session leak, a missing account-seeding call, and a stale UI-copy assertion).

## 16c. Provider backend: organization verification, opportunity submission, file upload (2026-08-18)

A third feature area — Provider (`ProviderRepository` and the provider-facing slice of `OpportunityRepository`) — moved from `Demo*Repository` in-memory fixtures to a real backend, following the same pattern §16b's `applications`/`verification` work established.

**What's real now:**
- `providers` table (organization registration/verification/suspend/appeal, sub-administrators with per-admin permission subsets, an append-only activity-history and appeals audit trail as separate child tables) — `scholarsphere_backend/app/models/provider.py`, `app/api/routes/providers.py`, migration `20260818_05_providers.py`.
- Server-authoritative risk scoring (`app/services/provider_risk.py`) — a byte-for-byte port of the Dart demo repository's heuristic, computed server-side only; the registration endpoint's request schema has no field a client could use to set its own score.
- Case-insensitive duplicate-organization-domain prevention enforced by a real Postgres functional unique index (`lower(official_email_domain)`), not just an application-level check — closes a TOCTOU race the app-level-only version of this check would have left open under concurrent registration.
- Provider verification requires all 5 checklist booleans server-side before a `verified` decision is accepted (409 otherwise), mirroring the existing opportunity-verification pipeline's `decide_verification` pattern exactly.
- `provider_opportunities` table — a **separate, dedicated pipeline** from the Grants.gov-family `external_opportunities` table (different verification-status value set, different verification-review/history tables), because the two genuinely don't share a schema or a review model. Submission is gated on the caller being the owner or a registered administrator of a `verified` provider with `publish_opportunities` permission, checked server-side against the caller's Firebase UID — never trusting a client-asserted `provider_id`. **Explicitly verified by test:** provider-submitted opportunities, once verified and published, do **not** leak into the applicant-facing `/api/v1/opportunities` public listing — the two pipelines stay isolated by design (`test_verify_then_publish_is_visible_but_not_via_public_opportunities`).
- Real file upload for provider registration documents, replacing a plain text field. `storage.rules` (previously a deliberate deny-all placeholder specifically left for this moment, see §16b) now allows owner-scoped read/write under `provider-documents/{uid}/{fileName}`, plus read access for `verificationOfficer`/`administrator`/`superAdministrator` custom-claim roles — matching the exact role-claim idiom `firestore.rules`'s `isAdministrator()` already uses, not a new pattern. Size capped at 10 MB, content-type allowlisted to PDF/JPEG/PNG at the Storage-rules level (the actual enforcement boundary; client-side checks in `provider_document_upload.dart` are defense-in-depth only). The backend never receives file bytes — it only accepts and validates the resulting Storage *path* (rejecting anything not shaped like `provider-documents/{caller's own uid}/...`), consistent with the "backend never proxies binary uploads" decision recorded when `storage.rules` was first stubbed out.
- **Not done, flagged as an accepted gap, not silently skipped:** the backend does not call the Firebase Admin Storage API to verify an uploaded document path actually exists before accepting it into a `Provider` record — it validates the path *shape* only. A client could theoretically claim a path it never uploaded to. This is the same risk class a free-text URL field would have carried, and `storage.rules`'s write-side uid-match is what actually prevents anyone but the owner from writing there in the first place; closing the residual gap would require adding `firebase-admin`'s Storage SDK to the backend, deferred as a follow-up rather than done here.
- **Not independently re-tested against a live Firebase Storage bucket or Firebase console** — this environment has no live Firebase project credentials. `storage.rules` was validated for syntax and reasoned about against the existing `firestore.rules` idiom, but was not deployed and exercised against a real bucket. Do that before this ships.

**Testing:** `pytest -q` → **213/213 passing** (full backend suite, including the 22 new tests this round added: 14 in `tests/test_providers_route.py`, 8 in `tests/test_provider_opportunities_route.py`). Both new Alembic migrations (`20260818_05`, `20260818_06`) validated offline via `alembic upgrade head --sql` against the PostgreSQL dialect, including a caught-and-fixed Postgres 63-character identifier-length violation on one index name. `flutter analyze` clean, `flutter test` 86/86 passing (up from 83, reflecting the new dependencies resolving and the provider-facing screens still rendering correctly under the new wiring).

**Scope not touched:** `ApiOpportunityRepository`/`ExternalOpportunity` (the Grants.gov-family pipeline) — no changes. Every other `_opportunityRepository` consumer in `app.dart` (verification, moderation, collection, administration analytics) deliberately stays on `DemoOpportunityRepository`, matching the existing documented rationale that those screens' richer assumptions don't match either backend's leaner data model yet.

## 17. Deployment Readiness

### Exact commands to build/run in production

**Flutter web (root):**
```sh
flutter pub get
dart format --output=none --set-exit-if-changed lib test
flutter analyze
flutter test               # 86/86 passing as of §16c
flutter build web --release --dart-define=SCHOLARSPHERE_API_BASE_URL=https://<your-api-host>/api/v1
docker build -t scholarsphere-web .
```

**FastAPI backend:**
```sh
cd scholarsphere_backend
cp .env.example .env       # fill in real values; never commit .env
python -m pip install -r requirements-dev.txt
pytest -q
pip-audit -r requirements.txt
docker compose up -d --build
```

**Firebase (Auth/Firestore/Functions/Storage):**
```sh
cd functions
npm ci
npm run lint
npm audit --omit=dev --audit-level=high
firebase deploy --only functions,firestore:rules,storage:rules
```

### Required environment variables

**`scholarsphere_backend/.env`** (see `scholarsphere_backend/.env.example` for the full authoritative list): `APP_ENV=production`, `DATABASE_URL`, `REDIS_URL`, `FIREBASE_PROJECT_ID`, `FIREBASE_CREDENTIALS_PATH`, `ALLOWED_ORIGINS`, `SIMPLER_GRANTS_API_KEY`, `USAJOBS_API_KEY`, `RELIEFWEB_APPNAME`, plus the newly-added `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` (sane defaults of 300/60 apply if unset). `FIREBASE_CHECK_REVOKED` should be left at its default `true` — it is now force-enabled in production regardless.

**Flutter build:** `SCHOLARSPHERE_API_BASE_URL` via `--dart-define` — must be an `https://` URL or a release build will now refuse to start (V-14 fix).

**Firebase:** project ID `scholarsphere-d44f5` is already configured in `.firebaserc`; the managed-account Cloud Functions require the project to be on the Blaze plan (per `docs/firebase_authentication.md`, unchanged by this audit).

### Deployment instructions for this stack
1. Provision managed PostgreSQL 16 and Redis 7 (or use `docker-compose.yml` for a self-hosted setup — it already wires `postgres`/`redis`/`api`/`worker`/`beat` with health checks).
2. Run `alembic upgrade head` (the `docker-compose.yml` `migrate` service already does this before `api` starts).
3. Deploy the FastAPI container behind TLS termination (the app itself doesn't terminate TLS).
4. Deploy `functions/` via `firebase deploy --only functions` (Blaze plan required) and `firestore:rules`.
5. Build and host the Flutter web bundle (root `Dockerfile` → nginx, headers already hardened) — or ship Android/iOS/macOS/Linux builds through their respective stores. The bundle ID was changed from the Flutter template default to `com.scholarsphere.app` in the follow-up round (§16b) — **before shipping, register a new Android/iOS/macOS app under that identifier in the Firebase console and download fresh `google-services.json`/`GoogleService-Info.plist`**, since the currently-checked-in Firebase config was generated against the old identifier.
6. Point the Flutter build's `SCHOLARSPHERE_API_BASE_URL` at the deployed backend's HTTPS URL.

---

## 18. Remaining Risks (not fixed, tracked explicitly)

Everything else originally listed here (Storage rules, `/docs`/`/redoc` exposure, `config/.env.example`, bundle ID, functions CI, and all 11 pre-existing Flutter test failures) was resolved in the follow-up round — see §16b. What's left:

| Risk | Severity | Why not fixed here |
|---|---|---|
| Most Flutter feature areas still have no real backend (notifications, documents, fraud detection, admin analytics, etc. — `applications`, `verification`, and `provider` (org verification + submission) moved from demo to real API-backed as of 2026-08-18, see §16b/§16c) | High (completeness, not a live vuln) | Building real backends for the remaining feature areas is a multi-month product/engineering effort, not a security patch. Flagged in §0 and §13. |
| `firebase-admin`'s transitive `uuid` dependency (moderate CVE) | Moderate | No upstream patch exists yet; forcing a downgrade would be a regression, not a fix (§4). CI now gates on `--audit-level=high` specifically so this known, accepted finding doesn't block every build. |
| Firebase console still has the *old* `com.example.scholarsphere` bundle ID registered against this project's Android/iOS/macOS apps | Medium, blocks Google Sign-In on the renamed apps until fixed | Registering a new app under `com.scholarsphere.app` and downloading fresh config is a Firebase-console action outside what this session can perform. See §16b/§17. |
| Android/iOS/macOS release builds are unsigned (backend `Dockerfile` runs as non-root correctly, but the Flutter `release` build type signs with the debug key, per `android/app/build.gradle.kts`'s `signingConfig = signingConfigs.getByName("debug")`) | Medium, blocks real app-store submission | Real release signing requires the team's own keystore/certificates, which can't be generated or supplied by this session. |

## 18b. Note on concurrent work during this audit
A separate, apparently independent change landed during the follow-up round (§16b) that added a real FastAPI `applications` backend (router, models, Alembic migration, tests) and a real `verification` API backend, wiring both into the Flutter client via `ApiApplicationRepository`/`ApiVerificationRepository` using the same optional-constructor-override pattern this audit introduced for `authRepository`/`apiOpportunityRepository`. That work was not authored or reviewed as part of this audit and should get its own security pass (the same categories as §2 — auth, authz, input validation — applied to the new `applications`/`verification` endpoints) before being considered covered by this report's conclusions.

## 19. Recommended Monitoring
- Wire the new `backend` CI job's `pip-audit` step (and add an equivalent `npm audit --omit=dev` step for `functions/`) to fail the build on new HIGH/CRITICAL findings, not just report them.
- Add Dependabot (or Renovate) for all three ecosystems (`pip`, `npm`, `pub`) so dependency CVEs like V-01–V-05 surface automatically instead of requiring a manual audit.
- Application-level: the backend already has structured logging with correlation IDs on every request/error — wire this to a real log aggregator (not configured in this repo) and alert on spikes in `429`/`5xx` rates once the rate limiter is live in production.
- Track the `firebase-admin`/`uuid` advisory (§4) and re-run `npm audit` monthly until a patched release exists.

## 20. Recommended Backup Strategy
- PostgreSQL: enable automated daily snapshots + point-in-time recovery on whatever managed Postgres is used in production (not configured in this repo — infrastructure-as-code for the database wasn't in scope/present here).
- Firestore: enable scheduled exports (Google Cloud's native Firestore export-to-GCS) given it holds the only source of truth for user accounts/roles.
- Redis: treat as ephemeral (rate-limit counters and Celery queue state) — no backup needed, but Celery task idempotency should be verified so a Redis flush doesn't double-run scheduled syncs.

## 21. Incident Response Recommendations
- The Cloud Functions' `suspendUser` (disables the Auth account + revokes refresh tokens + sets Firestore `status: suspended`) is already a usable "kill switch" for a compromised account — document this as the first response step for account-compromise incidents.
- The `ImportAuditLog`/`VerificationHistory` tables already provide a full audit trail of who verified/published/rejected what and when — useful for investigating a bad-data incident on the opportunity side.
- No formal incident-response runbook exists in the repo (`docs/operations.md` is a short operations note, not an IR plan) — recommend writing one covering: compromised Firebase Admin credentials, a bad opportunity published to production, and a Redis/Postgres outage, none of which are covered today.

---

## 22. Final Production Readiness Status

# NOT READY FOR PRODUCTION

**Reasoning:** The security posture of the subsystems this audit fully reviewed — Firebase Auth/Firestore/Functions and the FastAPI opportunity-discovery/verification backend — is genuinely solid, and every concrete vulnerability found in them has been fixed and regression-tested across both rounds (17 initial findings, 16 fixed, 1 open with no available upstream patch; plus the full follow-up remediation in §16b: bundle ID, Storage rules, `/docs` gating, config cleanup, functions CI, and all 11 pre-existing test failures root-caused and fixed). Current totals as of §16c: **86/86 Flutter tests and 213/213 backend tests passing.** If ScholarSphere's product scope were "an opportunity-discovery and verification platform with Firebase auth," this would be close to **READY WITH MINOR RISKS** pending the two remaining blockers in §18 (Firebase console re-registration for the new bundle ID; real release signing).

Three things still stand in the way of a stronger classification:

1. The product as described by its own README and the audit brief — notifications, document management, fraud detection, admin analytics, recommendations, and most other feature areas — still has **no backend at all**; those screens run entirely on in-memory demo data that resets on every restart and enforces no authorization because there is nothing to authorize access to yet. That is a completeness gap, not a patchable security bug, and no amount of hardening the reviewed subsystems changes it. (Applications, verification, and provider organization/opportunity workflows are no longer in this bucket — see §16b/§16c.)
2. The `applications`/`verification` backend (§16b) and the `providers`/`provider_opportunities` backend (§16c) have **not** had an independent adversarial security pass through this document's own §2 checklist (auth, authz, input validation, IDOR) — they were built following the same patterns already validated there (server-side RBAC, ownership checks via Firebase UID never a client-supplied field, 404-not-403 on non-owned resources, server-authoritative business logic never trusting client-sent values), but "built consistently with a reviewed pattern" is not the same claim as "independently reviewed," and this report should not blur that distinction.
3. `storage.rules`'s new provider-document rules (§16c) have been reasoned about and written consistently with `firestore.rules`'s existing idiom, but have not been deployed and exercised against a real Firebase Storage bucket in this environment — do that before relying on them in production.

**Path to production:** (1) security-review the `applications`/`verification` backend and the `providers`/`provider_opportunities` backend against the same checklist used in §2; (2) deploy and test `storage.rules` against a real Firebase Storage bucket; (3) decide, feature-by-feature, which of the remaining demo areas are in scope for launch and build real backends + authorization for those; (4) complete the Firebase console re-registration and real release signing from §18; (5) keep the CI gates from this audit (`backend`, `functions`, and Flutter's `validate` jobs in `.github/workflows/ci.yml`) green on every change from here forward, and extend the `functions` job's `npm audit` step to fail on new HIGH/CRITICAL findings once the current moderate finding has an upstream fix.

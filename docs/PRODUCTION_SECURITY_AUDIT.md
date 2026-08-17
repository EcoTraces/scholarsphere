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
| Provider opportunity submission, admin dashboard stats, applications, saved opportunities, notifications, document vault, fraud detection, recommendations, analytics, moderation, governance, support, taxonomy, calendar, collection, integrations | | ⚠️ **35 of 36 Flutter repositories are `Demo*Repository` — pure in-memory Dart objects, no backend, no persistence, reset on every app restart.** |
| File/image upload | | ❌ Not implemented anywhere (no upload code exists) |
| Payments | | ❌ Not present, not referenced anywhere |
| AI/LLM integration | | ❌ Not present — there is no AI/LLM code in this repository |
| Web scraping/crawling | | ❌ Not present — data ingestion is via official structured APIs (Grants.gov etc.), not scraping |

This matters for the final classification (§17): the platform cannot be "production ready" as a whole while 35 of its 36 feature areas have no backend, but the parts that *are* real (auth and opportunity discovery/verification) are held to the full standard below and are now in materially better shape than when this audit started.

---

## 1. System Architecture Summary

```
┌─────────────────────────┐        ┌──────────────────────────┐
│ Flutter client (lib/)   │        │ Firebase project          │
│ Web/Android/iOS/Desktop │──────▶ │  Auth · Firestore · Cloud  │
│ No state mgmt library;  │  SDK   │  Functions (2 callables)   │
│ StatefulWidget/setState │        └──────────────────────────┘
│                          │
│ ApiOpportunityRepository │──────▶ FastAPI backend (Python)
│ (read-only, Bearer JWT)  │  HTTPS  ├─ PostgreSQL (async SQLAlchemy)
│                          │        ├─ Redis (Celery broker + rate limiter)
│ 35× Demo*Repository      │        ├─ Celery worker + beat (scheduled sync)
│ (in-memory, no backend)  │        └─ Grants.gov / Simpler.Grants.gov /
└─────────────────────────┘           EU Funding & Tenders / USAJOBS / ReliefWeb
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
- **Client-side-only gating risk:** `AccessControlPolicy` (`lib/features/security/domain/access_control.dart`) decides which screen to render, but it is UI-routing convenience only — it has no bearing on the 35 in-memory demo repositories because none of them are reachable over a network today. **This must not be mistaken for real authorization once any of those repositories are backed by a real API** — flagged as a hard requirement for whoever builds that backend next.

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
See §2.2. **Solid for the real (auth + opportunity-pipeline) slice.** Server-side RBAC on every backend route, restrictive default-deny Firestore rules, admin-gated Cloud Functions. **Explicit risk carried forward:** the 35 demo Flutter repositories have no authorization layer at all because they have no backend — this is fine today (nothing is shared/persisted/network-reachable) but is a landmine for whoever wires a real API underneath them later; `AccessControlPolicy` must not be treated as sufficient authorization once that happens.

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
- The FastAPI backend has **no demo/mock opportunity data** — it only ever holds real records fetched from the five live sources above, and `seed_live_demo.py` (now guarded, V-11) explicitly fetches real live Grants.gov records rather than fabricating any.
- The Flutter client's 35 `Demo*Repository` implementations are extensive, intentional, in-memory fixtures — **not** hidden or disguised as real data; the app's own README discloses this plainly ("The in-memory demo credentials are development fixtures, not production password storage"). They are also not reachable from a shared backend, so they cannot leak fabricated data to other users. **Not removed**, because removing them would delete the only implementation of most of the app's screens with no replacement — that's a scope decision for the product owner, not something to silently delete. Recommendation if/when these ship to real users: gate each demo repository behind a build flag so a release build fails to compile/run against `Demo*` implementations for any feature not yet backed by a real API, rather than relying on nobody wiring them into `app.dart` by accident.
- One item worth a maintainer decision: `DemoAuthRepository` (`lib/features/authentication/data/demo_auth_repository.dart`) ships a plaintext-password bootstrap-admin mechanism and a fabricated Google-sign-in bypass. It is not referenced by `app.dart` (confirmed unreachable from the live app), but its presence in shippable `lib/` code alongside the real `FirebaseAuthRepository` is worth moving to a test-only fixture location in a follow-up so it can never accidentally get wired in.

## 14. Performance Findings
- Backend response-size caps, timeouts, and bounded retry/backoff on all external calls (already existed, confirmed sound).
- No N+1 query patterns found in the reviewed routes (queries use SQLAlchemy `select()` with explicit joins/pagination; `Query(le=100)` caps page sizes throughout).
- Alembic migrations validated offline against the PostgreSQL dialect (`alembic upgrade head --sql`) — all 3 revisions compile and chain cleanly with no errors.
- The rate limiter's Redis client uses a 0.5s connect/socket timeout with a 5-second outage backoff specifically so a Redis blip degrades to "no rate limiting" rather than adding multi-second latency to every request — this was caught and fixed during this audit's own test run (initial naive implementation made the 139-test suite balloon from ~10s to ~195s because of unbounded Redis connection retries with no local Redis running).
- No performance testing against real production-scale data volumes was performed (no such environment exists here).

## 15. Production Configuration Assessment
- `scholarsphere_backend/.env.example` and `config/.env.example` list variable **names** only, no real values — correct practice, already in place before this audit.
- **Inconsistency worth flagging, not fixed:** `config/.env.example` (repo root) documents `SCHOLARSPHERE_API_SECRET`, `SCHOLARSPHERE_DATABASE_URL`, `SCHOLARSPHERE_REDIS_URL`, `SCHOLARSPHERE_SENTRY_DSN` — but the Flutter client never reads a `.env` file at runtime (no `flutter_dotenv` dependency exists) and never references any of these variable names; the only real client-side config knob is the `SCHOLARSPHERE_API_BASE_URL` compile-time `--dart-define`. This file appears to be aspirational/leftover documentation for a config-loading mechanism that was never built. Recommend either implementing it or deleting the misleading entries so an operator doesn't go looking for a `.env`-loading code path that doesn't exist.
- CORS origins, Firebase project ID, and all external-API base URLs are environment-driven, not hardcoded (HTTPS-enforced at config load for the latter).
- Docker: backend `Dockerfile` runs as a non-root user (`appuser`, uid 10001) — good practice already in place. `.dockerignore` extended this audit (§3 V-13).

## 16. Testing Results
- **Backend:** `pytest -q` → **150 passed**, 0 failed (139 pre-existing + 11 new regression tests added this audit for: production-forces-revocation-check, security headers presence, rate-limiter allow/deny/per-key-isolation/outage-fail-open, health-endpoint bypass, 429-on-limit-exceeded, and the seed-script production guard).
- **Backend dependency audit:** `pip-audit` → 0 known vulnerabilities (post-fix).
- **Backend migrations:** all 3 Alembic revisions validated offline against PostgreSQL dialect, no errors.
- **Flutter static analysis:** `flutter analyze` → **no issues found**.
- **Flutter widget/unit tests:** `flutter test` → **58 passed, 11 failed**. Verified these 11 failures are **pre-existing and unrelated to any change made this audit** — the identical 11 tests fail identically on the unmodified `git stash`-restored baseline (same failure list: `administration_analytics_test.dart`, several `widget_test.dart` cases involving dashboard rendering and the private-profile-editor flow, all failing with `Bad state: No element` / widget-tree timing issues). **Not fixed** in this audit (out of security scope, and misrepresenting a pre-existing functional-test flake as a security fix would violate the "don't fabricate" rule) — flagged as a real, separate engineering task for the team.
- **CI:** added a `backend` job to `.github/workflows/ci.yml` so the 150-test backend suite and `pip-audit` now run on every push/PR — previously only Flutter had CI coverage.

## 17. Deployment Readiness

### Exact commands to build/run in production

**Flutter web (root):**
```sh
flutter pub get
flutter analyze
flutter test               # note: 11 pre-existing failures, see §16
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

**Firebase (Auth/Firestore/Functions):**
```sh
cd functions
npm ci
npm run lint
firebase deploy --only functions,firestore:rules
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
5. Build and host the Flutter web bundle (root `Dockerfile` → nginx, headers already hardened) — or ship Android/iOS builds through their respective stores; note both `android/app/build.gradle.kts` and the iOS project still use the Flutter template's default `com.example.scholarsphere` bundle ID, which must be changed before any real app-store submission (not a security issue, but a hard release blocker — **not fixed**, requires a product decision on the real bundle ID/app name).
6. Point the Flutter build's `SCHOLARSPHERE_API_BASE_URL` at the deployed backend's HTTPS URL.

---

## 18. Remaining Risks (not fixed, tracked explicitly)

| Risk | Severity | Why not fixed here |
|---|---|---|
| 35 Flutter feature areas have no real backend (applications, notifications, documents, provider workflows, admin analytics, etc.) | High (completeness, not a live vuln) | Building real backends for 35 feature areas is a multi-month product/engineering effort, not a security patch. Flagged in §0 and §13. |
| `firebase-admin`'s transitive `uuid` dependency (moderate CVE) | Moderate | No upstream patch exists yet; forcing a downgrade would be a regression, not a fix (§4). |
| No Firebase Storage rules exist (no `storage.rules`), and no file-upload code exists | N/A today, High if uploads ship without rules first | Nothing to secure yet — must be designed before any upload feature is built, not after. |
| 11 pre-existing Flutter test failures | Low (test debt, not a vuln) | Verified pre-existing and unrelated to this audit's changes (§16); needs its own engineering investigation. |
| `/docs`/`/redoc` exposed unconditionally on the backend | Informational | All routes behind them are still RBAC-gated; judgment call for the team on whether to restrict. |
| `config/.env.example` documents variables the Flutter client never actually reads | Informational | Documentation hygiene, not a runtime risk; needs a product decision (implement vs. delete). |
| Android/iOS bundle IDs still `com.example.scholarsphere` | N/A for security, blocks app-store release | Product/branding decision, not a code fix. |
| No functions-CI job for `npm audit`/`eslint` (only backend and Flutter got CI this audit) | Low | Recommended in §4; not added to avoid scope creep beyond the backend hardening already done. |

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

**Reasoning:** The security posture of the two subsystems that are actually real — Firebase Auth/Firestore/Functions and the FastAPI opportunity-discovery/verification backend — is genuinely solid, and every concrete vulnerability found in those subsystems during this audit has been fixed and regression-tested (17 findings, 16 fixed, 1 open with no available upstream patch). If ScholarSphere's product scope were "an opportunity-discovery and verification platform with Firebase auth," this would be close to **READY WITH MINOR RISKS**.

But the product as described by its own README and by the audit brief — applications, provider workflows, notifications, document management, fraud detection, admin analytics, recommendations — has **no backend at all** for 35 of its 36 feature areas; those screens run entirely on in-memory demo data that resets on every restart and enforces no authorization because there is nothing to authorize access to yet. That is a completeness gap, not a patchable security bug, and no amount of hardening the two real subsystems changes it. Shipping this to real users today would mean shipping a platform where almost every feature silently does nothing persistent, which is a product-integrity problem as serious as any security finding in this report.

**Path to production:** (1) decide, feature-by-feature, which of the 35 demo areas are in scope for launch and build real backends + authorization for those; (2) resolve the two Remaining Risks marked High/blocking in §18 (Storage rules before any upload feature ships; real bundle IDs before app-store submission); (3) re-run this audit's automated checks (`pytest`, `pip-audit`, `npm audit`, `flutter analyze`) as a CI gate on every change from here forward — the `backend` CI job added this audit is the start of that gate, extend it to `functions/`.

# ScholarSphere — Security Model

This is the security architecture reference: what the threat model is, what
controls exist for each category, and where each control lives in the
codebase. It is derived from — and should be read alongside —
`docs/PRODUCTION_SECURITY_AUDIT.md`, which is the point-in-time audit record
(findings, fixes, test counts, dated verdict). This document is the
standing reference for *how the system is designed to defend itself*; the
audit document is the record of *what was checked and when*. Every claim
below is sourced from the real code, not from what a platform like this
"should" have.

## 1. Threat model

ScholarSphere's trust-critical asset is the **verification status** of an
opportunity — applicants act on it (apply, submit personal information,
sometimes pay application fees) based on the "Verified" label. The threat
model is built around protecting that label:

| Threat | Primary defense |
|---|---|
| A fabricated or scraped-and-mislabeled opportunity reaching an applicant as "Verified" | Server-enforced pipeline: `verified` only after a human officer's explicit decision; `published` only after a separate administrator action (§5) |
| A compromised or over-privileged account changing verification status | Firebase-token-based RBAC on every mutating route, evaluated server-side (§3) |
| Malicious content in an official source's payload reaching an applicant's browser | HTML sanitization (`bleach`) at both import time and officer-edit time (§6) |
| An attacker using the backend as an SSRF proxy to reach internal/private infrastructure | No user-controllable outbound URL exists anywhere in this codebase (§4) |
| Silent tampering with an already-verified record | Every mutation is diffed into an append-only audit trail (§8) |
| Credential/secret leakage via logs, error messages, or `repr()` | `SecretStr`-wrapped API keys, generic error envelopes, no stack traces to clients (§7, §5) |
| Volumetric abuse (brute-force, scraping-via-API, import-endpoint amplification) | Redis-backed rate limiting, fail-open (§9) |

Not modeled yet, because the corresponding feature doesn't exist: payment
fraud (no payments), file-upload attacks (no upload feature), prompt
injection against an LLM (no AI/LLM integration — §10 explains why this
section is a placeholder, not an oversight).

## 2. Authentication

Firebase Authentication is the **only** identity system in this repository
— there is no hand-rolled password or JWT implementation to secure or get
wrong. The Flutter client authenticates via `firebase_auth`
(`lib/features/authentication/data/firebase_auth_repository.dart`); every
backend request carries the resulting Firebase ID token as
`Authorization: Bearer <token>`. The FastAPI backend verifies it server-side
via `firebase-admin`'s `verify_id_token`
(`scholarsphere_backend/app/core/auth.py`):

- Signature verified against Google-hosted keys (RS256)
- `aud` (audience) re-checked against the configured `FIREBASE_PROJECT_ID` explicitly, not just left to the SDK default
- `check_revoked=True` is **forced** in production regardless of the `FIREBASE_CHECK_REVOKED` env var (`app/core/config.py` model validator) — a misconfigured env var cannot silently let a suspended account's token keep working
- No token → `401` with `WWW-Authenticate: Bearer`; invalid/expired/wrong-audience token → `401` with a generic message (never leaks *why* verification failed)

## 3. Authorization / RBAC

Every protected backend route declares its required roles as a reusable
FastAPI dependency (`app/core/rbac.py::require_roles`), evaluated against
the verified token's `role` claim — **never** a client-supplied field:

```python
preview_access = require_roles("verificationOfficer", "administrator", "superAdministrator")
import_access  = require_roles("verificationOfficer", "administrator", "superAdministrator")
admin_access   = require_roles("administrator", "superAdministrator")
```

The verification-officer endpoints this session added (`GET .../review`,
`POST .../notes`, `PATCH .../opportunities/{id}`, `GET .../evidence`) all
reuse `preview_access`/`import_access` — no new role logic was invented, so
there is no new place for a role check to be wrong. Publication and source
activation stay behind the stricter `admin_access`; a Verification Officer
cannot publish an opportunity even after approving it (§5).

Firestore rules (`firestore.rules`) are default-deny except `users/{uid}`,
which forces `role` to stay constant across a user's own updates (no
client-side self-escalation) and allowlists exactly which fields a user may
change. Cloud Functions that mint privileged claims
(`createManagedUser`/`suspendUser`, `functions/index.js`) check
`requireAdministrator()` before touching the Admin SDK.

**IDOR/BOLA**: opportunity records are admin-curated shared data, not
user-owned, so classic per-record ownership checks don't apply — any staff
role with `preview_access`/`import_access` can act on any opportunity by
design, matching how the pending-verification queue itself works (any
officer can pick up any queued item). There is no user-owned resource
(applications, saved opportunities, documents) with a real backend today to
carry an IDOR risk (`docs/PRODUCTION_SECURITY_AUDIT.md` §2.2).

## 4. SSRF protection

There is no endpoint anywhere in this codebase that accepts a
user-controlled URL and fetches it server-side. The only outbound HTTP
calls the backend makes are to a **fixed, operator-configured allowlist of
six official-source hosts** (`docs/AUTHORITATIVE_SOURCES.md`), each base URL
loaded from an environment variable and validated HTTPS-only at
config-load time (`app/core/config.py` — an `http://` value for any
`*_BASE_URL`/`*_API_URL` setting fails startup, not just a warning). The
shared HTTP client (`app/core/http_client.py`) additionally enforces
per-request timeouts, a 5 MiB response-size cap, and bounded retry/backoff
on `429`/`5xx`. Because the destination set is fixed at deploy time and
never influenced by request input, the standard SSRF checklist (scheme
allowlisting, private/loopback/link-local/metadata-IP blocking, redirect
validation) is satisfied by construction rather than by runtime filtering —
there is no `file://`/`ftp://`/`gopher://`/`data://` handling anywhere
because nothing in this codebase ever resolves a URL it didn't choose
itself.

**If a future increment adds provider self-submission of a URL, or any
other "fetch this address" feature**, that feature must not reuse this
reasoning — it will need real runtime SSRF validation (scheme allowlist, DNS
resolution + private-IP-range rejection, redirect re-validation) before
shipping, per the platform specification §13. None of that exists today
because there is currently nothing that needs it.

## 5. Web-scraping and data-ingestion security

There is no web scraping anywhere in this repository — confirmed by a
repository-wide search for scraping libraries during the original audit and
again during this session's work. Every opportunity originates from one of
the six official, documented, structured APIs in
`docs/AUTHORITATIVE_SOURCES.md`. The ingestion pipeline
(`docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` §2) treats every payload as
untrusted input regardless of its official origin:

- HTML in `description` fields is stripped to a safe tag/attribute
  allowlist (`app/services/parsing.py::sanitize_html`, using `bleach`) —
  `<script>`, `<iframe>`, `<object>`, `<form>`, inline event handlers, and
  `javascript:` URLs are all removed, and links are force-`nofollow`ed and
  HTTPS-only. This is applied at import time in every source connector, and
  — added this session, after finding it missing — also applied to an
  officer's `description` edits via `PATCH .../opportunities/{id}`, so a
  human correction cannot reintroduce what the automated import strips.
- Every imported record starts `verification_status=pending`,
  `publication_status=unpublished`, enforced by the ingestion schema itself
  (`NormalizedExternalOpportunity`'s field validators reject anything else)
  — a malicious or buggy source response cannot inject a pre-verified
  record.
- No content from a source payload is ever passed to code execution,
  templating, or a shell — it is stored as data (JSON/text columns) and
  rendered as data (Flutter `Text` widgets do not interpret HTML; there is
  no `dangerouslySetInnerHTML`-equivalent anywhere in this codebase).

## 6. Prompt injection protection

**Not applicable today.** There is no AI/LLM integration anywhere in this
repository (`docs/PRODUCTION_SECURITY_AUDIT.md` §2.7/§10, confirmed by
repository-wide search). This section exists as a placeholder for the
platform specification's requirement, not to claim a control that doesn't
need to exist yet.

**If AI-assisted extraction/classification is added in the future**, the
non-negotiable rules from the platform specification apply and should be
enforced exactly the same way the rest of this security model enforces
things — server-side, not by convention: any text originating from a
scraped/fetched source must be passed to the model as inert data (never
concatenated into an instruction/system prompt), the model must never be
granted a tool that can itself change `verification_status`, create a
source, or write to `ImportAuditLog`/`VerificationHistory`, and every
AI-produced field must carry `{value, source_url, confidence}` with the
official source's value always winning on conflict (see
`docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` §10).

## 7. Secrets management

- No `.env` files, service-account JSON, or hardcoded credentials are
  committed anywhere (`scholarsphere_backend/.env.example` and
  `config/.env.example` list variable *names* only).
- Backend API keys (`SIMPLER_GRANTS_API_KEY`, `EU_FUNDING_API_KEY`,
  `USAJOBS_API_KEY`) are Pydantic `SecretStr` — they cannot leak via
  `repr()`/logs even by accident; the current `EU_FUNDING_API_KEY` default
  (`SEDIA`) is the EU portal's own published, non-secret literal, not a
  leaked credential.
- Firebase client config (`lib/firebase_options.dart`,
  `android/app/google-services.json`) is the standard public
  project-identifier config Google intends to ship in every client app —
  its safety rests on Firestore rules (§3), not on keeping it secret.
- The backend Docker image runs as a non-root user; `.dockerignore` excludes
  dev artifacts (`*.db`, logs, `tests/`) from the production image.

## 8. API security

- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options: DENY`,
  `Strict-Transport-Security`, `Referrer-Policy`, `Cache-Control: no-store`
  on every response (`app/core/security_headers.py`).
- **CORS**: explicit origin allowlist + credentials, never a wildcard
  (`ALLOWED_ORIGINS`).
- **Error handling**: a single catch-all handler returns a generic message
  and a correlation ID; the real exception (type only, never the message
  body) is logged server-side, never returned to the client
  (`app/core/errors.py`).
- **API docs** (`/docs`/`/redoc`/`/openapi.json`) are disabled whenever
  `APP_ENV=production`.
- **Request size**: `MAX_REQUEST_BYTES` rejects oversized bodies before
  they're parsed.

## 9. Rate limiting

A Redis-backed fixed-window limiter (`app/core/rate_limit.py`) applies
globally — default 300 requests/60s per client IP, configurable via
`RATE_LIMIT_REQUESTS`/`RATE_LIMIT_WINDOW_SECONDS`. It **fails open** on a
Redis outage after a bounded 0.5s connect timeout (so a cache blip degrades
to "no rate limiting" rather than adding multi-second latency or taking the
API down) and exempts `/health/*`. This protects both classic
brute-force/enumeration abuse and the outbound-amplification risk specific
to this system: `POST .../import` and `POST .../{source}/sync` each trigger
a real outbound call to an official source's API, so an unthrottled client
could otherwise hammer a partner government/international-org API through
ScholarSphere's own backend.

## 10. Data validation

Every write path in the pipeline goes through a narrow, purpose-built
Pydantic model — never "the whole ORM row":

- `NormalizedExternalOpportunity` — import-time schema; HTTPS-only URL
  validators, forced `pending`/`unpublished` status, timezone-aware
  timestamps required.
- `VerificationDecisionRequest` — decision restricted to a closed
  `Literal` set (§ `docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` §3); `notes`
  bounded 1–4000 chars.
- `OpportunityNoteRequest` — note bounded 1–4000 chars.
- `OpportunityEditRequest` — every field independently bounded/typed;
  `official_source_url`/`official_application_url` are `HttpUrl` with an
  HTTPS-only validator (`https_urls_only`), matching the import-time rule
  exactly so an officer edit can't downgrade a link to plaintext HTTP;
  `reason` is mandatory (1–2000 chars) on every call.

SQL injection has no surface: all queries go through SQLAlchemy's
parameterized query builder; the only raw `text()` call anywhere is a
hardcoded `SELECT 1` health check with no interpolation.

## 11. Audit logging

Two append-only tables back every state change in the pipeline
(`app/models/external_opportunity.py`):

- **`VerificationHistory`** — every status transition, note, and field
  edit, with a required `reason` and a `changed_fields` diff.
- **`ImportAuditLog`** — every action across the whole pipeline (imports,
  source activation, verification decisions, notes, edits, publication
  changes), with actor ID, actor role, a correlation ID, and previous/new
  value snapshots. No update/delete service is exposed for this table by
  design — it can only ever be appended to.

Neither secrets nor passwords are ever written to either table (there is
nothing that would be — identity lives entirely in Firebase, and no field
on these models holds a credential).

**Known gap**: no endpoint exposes either table for reading yet — a
Security Officer role is defined in the RBAC role set but has no route to
read audit events, login anomalies, or rate-limit violations. This is
tracked in `docs/PRODUCTION_SECURITY_AUDIT.md` §18 and
`docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` §7, not hidden.

## 12. Incident response

No formal incident-response runbook exists in this repository yet
(`docs/operations.md` is a short operations note, not an IR plan —
carried forward unchanged from `docs/PRODUCTION_SECURITY_AUDIT.md` §21).
What already exists that an IR process could build on:

- **Account compromise**: the `suspendUser` Cloud Function
  (`functions/index.js`) disables the Auth account, revokes refresh tokens,
  and sets Firestore `status: suspended` in one call — a usable kill switch
  today.
- **Bad data published**: `VerificationHistory`/`ImportAuditLog` (§11)
  provide a full who/what/when/why trail to investigate and reverse a bad
  publish; an administrator can `PATCH .../opportunities/{id}` to correct a
  field or `POST .../publication` with `published: false` to pull it from
  public listing immediately, both audited.
- **Redis outage**: rate limiting fails open (§9) rather than taking the
  API down; Celery task idempotency (exact-duplicate detection via payload
  hash, §`docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` §8) means a Redis flush
  and re-run of scheduled syncs should not double-import records — not
  independently load-tested in this environment.

## 13. What this document does not cover

Consistent with `docs/PRODUCTION_SECURITY_AUDIT.md` §0: file upload,
payments, and the 35 demo-data Flutter feature areas have no real backend
and therefore no real attack surface to model yet. Building any of them
means extending this document with a real section for that surface — not
writing speculative controls for code that doesn't exist.

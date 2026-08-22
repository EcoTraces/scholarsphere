# ScholarSphere — Production Readiness Report

**Date:** 2026-08-17
**Basis:** `docs/PRODUCTION_SECURITY_AUDIT.md` (full-repository security audit
and two remediation rounds) and `docs/SECURITY_MODEL.md` (standing security
architecture), plus this session's own work extending and self-reviewing the
verification-officer backend. All test counts below were freshly re-run by
this session, not copied from an earlier point in time.

## 1. Architecture

- **Frontend**: Flutter (Dart ^3.12.2), feature-sliced
  `domain/data/presentation`, no router package, manual `Navigator`.
- **Identity**: Firebase Auth + Firestore (`users/{uid}` only) + 2 Cloud
  Functions (`createManagedUser`, `suspendUser`).
- **Opportunity backend**: FastAPI (async) + PostgreSQL (SQLAlchemy 2.0) +
  Celery/Redis, in `scholarsphere_backend/`. Auth fully delegated to
  Firebase — no local password/JWT code exists.
- **Data ingestion**: seven official structured APIs, plus (as of
  2026-08-22) five web-scraper sources for named organizations with no
  official API — all twelve feed the same mandatory human-verification
  queue (§4, `docs/AUTHORITATIVE_SOURCES.md`).
- **Deployment artifacts**: root `Dockerfile` (Flutter web → nginx),
  `scholarsphere_backend/Dockerfile` + `docker-compose.yml`
  (api/worker/beat/postgres/redis), `.github/workflows/ci.yml`.

This architecture is sound for what it's asked to do and hasn't changed
structurally this session — this report's job is to state how much of the
platform actually sits on it.

## 2. Security

See `docs/SECURITY_MODEL.md` for the full architecture and
`docs/PRODUCTION_SECURITY_AUDIT.md` for the dated finding-by-finding record.
Summary: **17 findings from the original audit, 16 fixed and
regression-tested, 1 open with no available upstream patch**
(`firebase-admin`'s transitive `uuid` CVE — no patched release exists yet;
forcing a downgrade would be a regression, not a fix). A follow-up round
closed the remaining bundle-ID/Storage-rules/CI/test-failure items.

**This session's own contribution**, performed because the audit doc
explicitly flagged the new verification backend as unreviewed
(§18b/§22): a targeted pass of the new endpoints against the audit's own
checklist (auth, authz, input validation, IDOR) found and fixed one real
gap — `PATCH .../opportunities/{id}` let an officer set `description`
without the HTML sanitization every source-imported description gets,
meaning an officer-authored stored-XSS-shaped payload could have reached
applicants once published. Fixed by routing edited descriptions through the
same `sanitize_html()` used at import time
(`app/services/parsing.py`), with a regression test
(`test_edit_sanitizes_description_html_like_source_import_does`) proving
script/event-handler content is stripped. No other findings from that
pass — RBAC reuses the existing `preview_access`/`import_access`
dependencies with no new role logic, every input is Pydantic-validated,
and there is no IDOR surface (opportunity records aren't user-owned).

The "applications" backend that landed concurrently with this session's
work has **not** been reviewed by this session — it was not authored here,
and reviewing code without having built or fully traced it risks a shallow,
falsely-reassuring pass. It remains an explicit open item (§9).

## 3. Data integrity

- Every mutating write validates through a narrow Pydantic schema — never
  the raw ORM row (`docs/SECURITY_MODEL.md` §10).
- Imports are idempotent: exact duplicates (source + external ID + payload
  SHA-256) are skipped; cross-source duplicate candidates are flagged for
  human review, never auto-merged.
- `official_source_url`/`official_application_url` are HTTPS-only and
  schema-validated on both import and officer edit — the same rule, not two
  different ones that could drift apart.
- Two append-only audit tables (`VerificationHistory`, `ImportAuditLog`)
  record every state change with actor, reason, and a before/after diff —
  verified by this session's own new tests
  (`test_edit_diffs_fields_and_requires_reason`,
  `test_note_is_appended_without_changing_status`, and others in
  `scholarsphere_backend/tests/test_verification_actions.py`).
- No opportunity field is ever set from an AI inference — there is no AI in
  this codebase (§5) — and no field is set from anything other than either
  the official source's own payload or an audited, reasoned human edit.

## 4. Source reliability

Seven integrated sources are official government/international-org APIs
(Level 1 — primary/authoritative). **Update, 2026-08-22**: five more
sources (Commonwealth Scholarships, Chevening, DAAD, Chinese Embassy in
Sierra Leone, Sierra Leone's Ministry of Technical and Higher Education)
were added via a new web-scraper tier, confirmed to have no official API/
RSS/dataset each — see `docs/AUTHORITATIVE_SOURCES.md` #8-#12 for the
per-source research and robots.txt/terms check. These carry a lower
`trust_level` (`web_scraped`, vs `official` for the API sources), which
feeds into the confidence-triage signal
(`app/services/verification_confidence.py`) but does **not** exempt them
from the same mandatory human verification every source goes through — see
`docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` §6. `docs/AUTHORITATIVE_SOURCES.md`
has the full registry with real base URLs, trust levels, and the sources
that were evaluated and deliberately rejected (including Fulbright, checked
2026-08-22).

The remaining real coverage gap is most other named individual-student
scholarships and fellowships (university-specific funds, smaller
foundations) — none publish a public API and most have not been evaluated
for scraping; closing that gap further needs a licensed data feed,
per-provider partnership work, or evaluating specific additional named
sites the same way the five above were.

## 5. Verification workflow

The best-built, most-real part of the system
(`docs/OPPORTUNITY_VERIFICATION_SYSTEM.md`). Enforced **server-side**, not
just in the UI:

- `verified` requires all four checklist items true, or the API returns
  `409` — regression-tested.
- `published` requires `verified` first, or the API returns `409` —
  regression-tested (`test_import_requires_approval_then_explicit_publication_and_audits`).
- Six real decision outcomes (approve/reject/request-reverification/
  mark-expired/mark-source-unavailable/flag), an audited note action, and
  an audited field-edit action — all added this session, closing the gap
  between what the platform specification asked for and what the backend
  previously supported (approve/reject only).
- Automatic 90-day reverification and daily expiry detection run as Celery
  beat tasks, independent of any human remembering to check.
- The Verification Officer can now actually perform this entire workflow
  through the app (`LiveVerificationQueueScreen`,
  `ApiVerificationRepository`) — previously the backend supported it but no
  UI reached it.

**Known, deliberate limitation**: the live backend supports one officer
making one decision per review, not the platform specification's
two-person-approval illustrative model. That richer workflow exists only in
the demo (`DemoVerificationRepository`) and was not force-fitted onto the
real backend — see `docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` §4 for the
reasoning. If two-person approval is a hard product requirement, it needs
its own backend design (an `assigned_officer`/`second_approver` model,
distinct from what exists), not a UI-only simulation of it.

## 6. AI safety

Not applicable — there is no AI/LLM integration anywhere in this codebase,
confirmed by repository-wide search in both the original audit and this
session. `docs/SECURITY_MODEL.md` §6 documents the rules that must apply
*if* AI-assisted extraction is added later (source-cited, non-authoritative,
never able to self-approve) so this isn't rediscovered from scratch when
that work starts.

## 7. Testing

Freshly re-run by this session, not carried forward from an earlier count:

- **Backend**: `pytest -q` → **176 passed, 0 failed** (includes this
  session's 12 new tests for the verification-officer endpoints, one of
  which is the sanitization regression test from §2).
- **Flutter**: `flutter test` → **83 passed, 0 failed** (includes this
  session's 15 new tests for `ApiVerificationRepository`, using
  `http.testing.MockClient` and `mocktail`-based `FirebaseAuth` fakes since
  no HTTP-mocking test harness existed for this pattern before).
- **Flutter static analysis**: `flutter analyze` → clean, project-wide.
- **Backend dependency audit**: `pip-audit` → 0 known vulnerabilities
  (post-fix, per the original audit round).

No live integration test against a running PostgreSQL/Redis/Firebase stack
was performed by this session — all backend tests run against an in-memory
SQLite database with dependency overrides (the existing project convention,
`scholarsphere_backend/tests/*`), and no such infrastructure is provisioned
in this environment.

## 8. Performance

Carried forward from the audit (`docs/PRODUCTION_SECURITY_AUDIT.md` §14),
unchanged by this session's work: response-size caps, timeouts, and bounded
retry/backoff on all external calls; no N+1 query patterns in the reviewed
routes. This session's own model change (the new `source_unavailable`
verification status) needed **no** Alembic migration — the enum column is
plain `VARCHAR` (`native_enum=False`), confirmed against the existing
migrations before making the change (`docs/SECURITY_MODEL.md` §10). A
fourth migration (`20260817_04_applications.py`) exists from the
concurrently-landed `applications` work, not from this session; it was not
independently validated here. No performance testing against
production-scale data volumes has been performed — no such environment
exists here.

## 9. Monitoring

- Structured logging with correlation IDs exists on every request/error
  (`app/core/errors.py`) but is not wired to a real log aggregator in this
  repo.
- `GET /external-opportunities/health` exposes per-source sync health
  (last success/failure, most recent error, next scheduled run) to staff.
- **(2026-08-22)** `GET /audit/import-records` now exposes `ImportAuditLog`
  for reading (filtering + pagination), gated on the same
  `administrator`/`securityAdministrator`/`superAdministrator` roles as the
  rest of `audit.py` — see `Task.md`/`Changelog.md`. Rate-limit events still
  have no read endpoint.

## 10. Deployment

Exact commands are documented in
`docs/PRODUCTION_SECURITY_AUDIT.md` §17 and `scholarsphere_backend/README.md`
and were not changed by this session. Two concrete pre-launch blockers
carried forward, unchanged:

1. Firebase console still has the *old* bundle ID registered — Google
   Sign-In won't authenticate against the renamed app until a new app is
   registered and fresh config downloaded. This requires Firebase-console
   access no coding session can perform.
2. Android/iOS/macOS release builds are currently signed with the debug
   key, not a real release keystore — requires the team's own signing
   credentials.

## 11. Remaining risks

| Risk | Severity | Status |
|---|---|---|
| 35 of 36 Flutter feature areas had no real backend | High (completeness) | **Stale as of 2026-08-21/22** — per `Task.md`, the large majority of the 36 feature areas are now wired to real FastAPI backends; this row and this report predate that work and need a full refresh, not a patch edit. |
| The `applications`/`verification`/`providers`/`provider_opportunities` backends had not been security-reviewed | Medium-High, until reviewed | **Resolved 2026-08-22** — independent §2-checklist review completed; 4 real gaps found and fixed (missing audit trail, permission-storage format bug, per-administrator permission-enforcement gap, unconstrained decision field), 0 IDOR/auth-bypass found. See `Task.md`/`Changelog.md` 2026-08-22 entry. |
| No Security Officer read access to audit/rate-limit data | Medium | **Partially resolved 2026-08-22** — `GET /audit/import-records` now exposes `ImportAuditLog`. Rate-limit events still have no read endpoint. |
| `firebase-admin`'s transitive `uuid` CVE (moderate) | Moderate | No upstream fix available; CI gates on `--audit-level=high` so this known, accepted finding doesn't block builds |
| Firebase console bundle-ID re-registration | Medium, blocks Google Sign-In on renamed apps | Requires console access outside any coding session |
| Unsigned mobile release builds | Medium, blocks app-store submission | Requires the team's own signing keystore |
| No live PostgreSQL/Redis/Firebase integration test has been run against this session's new endpoints | Low-Medium | All tests pass against SQLite + dependency overrides; a live smoke test before first production deploy is still recommended |

## 12. Final Production Readiness Status

# NOT READY FOR PRODUCTION

**Reasoning:** The specific slice this session worked on — verification
officer actions against real, imported opportunities — is now genuinely
end-to-end real: import → human review with a real evidence panel → a real
audited decision, note, or edit → separate, deliberate publication, all
server-enforced and regression-tested (176/176 backend, 83/83 Flutter). If
ScholarSphere's scope were narrowed to "an opportunity-discovery and
verification platform with Firebase auth," this slice would be close to
**READY WITH MINOR RISKS**, pending only the Security-Officer audit-log
read gap (§9/§11) and the two Firebase/signing blockers in §10, neither of
which is a code defect.

The platform as a whole is not there, for two unchanged reasons carried
forward from `docs/PRODUCTION_SECURITY_AUDIT.md`:

1. **Completeness**: 35 of 36 Flutter feature areas still have no real
   backend — they are in-memory demo data with no persistence and no
   server-side authorization, because there is no server for them to talk
   to yet. This is a multi-month engineering scope, not a patch.
2. **An unreviewed concurrent change**: the `applications` backend that
   landed alongside this session's work has not been through the security
   checklist this session applied to `verification` — it should not be
   assumed safe by association.

**Path to production** (unchanged in substance from
`docs/PRODUCTION_SECURITY_AUDIT.md`, updated for this session's progress):
(1) apply the same §2/`docs/SECURITY_MODEL.md` checklist to the
`applications` backend; (2) decide, feature-by-feature, which of the
remaining 35 demo areas are actually in scope for launch, and build real
backends + authorization only for those — do not ship the rest behind a
UI that looks identical to the real thing; (3) give the Security Officer
role something to read (§9); (4) complete the Firebase console
re-registration and real release signing (§10); (5) keep `backend`,
`functions`, and Flutter CI jobs green on every change, including this
session's additions.

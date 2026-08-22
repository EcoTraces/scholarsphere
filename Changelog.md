# Changelog

All notable changes to ScholarSphere are recorded here going forward. This
file starts from the project's current state as of 2026-08-21 — the
"Baseline" entry below summarizes what already existed rather than
reconstructing a fictional history; the real commit log
(`git log --oneline`) remains the authoritative historical record for
anything before this file existed.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Root-level documentation set (`PRD.md`, `Architecture.md`, `Design.md`,
  `Database.md`, `Coding_Rules.md`, `Road_map.md`, `Changelog.md`,
  `Task.md`) as the project's central source of truth, built by inspecting
  the actual codebase rather than assumption.

### Changed
—

### Fixed
—

### Removed
—

---

## [2026-08-21] — Real backend fixes: search index, verification dashboard, reverification reminders, document-sharing consent

Four wiring/completeness gaps identified in `Task.md`'s Critical Tasks were
inspected, fixed, tested, and verified against the running code (not
assumed). Full test suites re-run and passing after every change:
**431/431 backend (`pytest -q`), 88/88 Flutter (`flutter test`),
`flutter analyze` clean.**

### Fixed
- **Search index fed from fake data.** `lib/app/app.dart`'s
  `searchIndexUpdate` background-job handler read from
  `DemoOpportunityRepository` while writing to the real
  `ApiSearchIndexRepository`. Root cause was worse than a stale read:
  `POST /search-index/rebuild` prunes the entire shared index and
  re-validates every incoming id against real `external_opportunities`
  rows before keeping it, so demo ids were silently rejected — every
  rebuild was leaving the real, shared search index **empty**. Fixed by
  reading from `_apiOpportunityRepository` instead. The separate
  `expiredOpportunityDetection` client-side job was removed (not
  re-pointed): the real backend already performs this daily,
  authoritatively, via Celery beat, and the client has no
  server-authoritative way to mutate verification status (see
  `Architecture.md` decision 9). Regression-tested end-to-end
  (`test/widget_test.dart`, drives the real admin "process queued jobs"
  UI flow and asserts real backend data reaches `rebuild()`).
- **Verification Officer dashboard showed fabricated metrics.** The
  dashboard's landing panels read `assignedToUserId`,
  `VerificationWorkflowStatus`, `hasOfficialAuthority`, and other fields
  that only exist in the demo's richer two-person-workflow model — the
  real backend has none of them. Fixed by adding a real backend aggregate
  endpoint, `GET /external-opportunities/verification-summary` (pending
  count, verified-today count, reverification-due-soon count, a real
  status breakdown, 7-day decision activity, an honest official-source
  ratio, and approvals attributed to the calling officer via
  `ImportAuditLog`), and rewriting every dashboard panel to consume it
  through `ApiVerificationRepository.getSummary()`. Panels with no real
  backend equivalent ("My Assignments") were replaced with panels backed
  by real data ("Approved by You"), not relabeled fakes. The dead
  `DemoVerificationRepository`/`_opportunityRepository` wiring was removed
  from `app.dart` entirely.
- **Reverification reminders produced no real delivery.** The Celery task
  `_send_reverification_reminders` only logged a count. Fixed by creating
  real `ScholarSphereNotification` rows (in-app channel — the one channel
  this backend genuinely delivers on today; email/push are marked
  "delivered" by `process_due_notifications` without any SMTP/FCM
  provider behind them, a pre-existing gap tracked separately in
  `Task.md`) for verification officers, identified via real prior
  `verification_*` decisions in `ImportAuditLog` (this backend has no
  local user directory to draw a full officer roster from — a documented,
  honest limitation, not a fabricated recipient list). Deduplicated by a
  deterministic id (`{opportunity_id}-reverification-officer-{uid}`) so
  re-running the task never spams, and gated on each recipient's own
  notification preferences (global opt-out, missing `in_app` channel, or
  a type-specific unsubscribe all suppress creation). New
  `NotificationEventType.reverification_due`.
- **Provider document-sharing had no consent precondition.** Sharing an
  applicant document with a provider (`POST
  /applicant-documents/{id}/share`) recorded the grant unconditionally.
  Fixed by requiring an active (`granted`, not `withdrawn`)
  `third_party_sharing` `ConsentRecord` before recording the grant (`409`
  otherwise, mirroring the exact precondition
  `privacy.py::record_organization_access` already enforced elsewhere),
  and validating the target provider actually exists (`404` otherwise).
  Every successful grant now also writes a real
  `OrganizationAccessRecord`, visible to the applicant via `GET
  /privacy/access-history`. Withdrawing that consent
  (`POST /privacy/consents/thirdPartySharing/withdraw`) now cascades to
  clear every existing `shared_with_provider_ids` grant for that user, not
  just block new ones.
- **Incidental:** `JobMonitorScreen`'s three `setState(_reload)` calls
  passed a `void` arrow-function tear-off whose body was itself an
  assignment expression — at runtime it still returned the assigned
  `Future`, tripping Flutter's "setState callback returned a Future"
  guard. Found while writing the search-index regression test (the first
  test ever to actually drive "process queued jobs"); fixed by wrapping
  each call in a block body.

### Added
- `GET /external-opportunities/verification-summary` backend endpoint +
  `VerificationSummary`/`VerificationActivityDay` schemas.
- `ApiVerificationRepository.getSummary()` +
  `LiveVerificationSummary`/`VerificationActivityDay` Flutter models.
- `ScholarSphereApp.verificationRepository` constructor override, so tests
  can inject a fake `ApiVerificationRepository` the same way every other
  API repository already supports.
- 4 new backend tests (`tests/test_verification_actions.py`), 4 new
  backend tests (`tests/test_opportunity_tasks.py`), 5 new/updated backend
  tests (`tests/test_applicant_documents_route.py`), 1 new Flutter
  end-to-end widget test.

### Changed
- `scholarsphere_backend/README.md`'s "Known limitations" section
  corrected: the reverification-reminder-delivery bullet was stale (it
  predated both the 2026-08-20 real Notifications backend and this
  session's fix).

---

## [Baseline] — 2026-08-21

Snapshot of the project's real state at the point this documentation set
was created, reconstructed from `git log` and direct code inspection (not
fabricated). Dates below are real commit dates.

### Added
- **2026-08-07** — Initial commit: Flutter project scaffold.
- **2026-08-12** — `ui-ux-pro-max` design-intelligence Claude Code skill
  installed; `dart format` violations fixed project-wide.
- **2026-08-17** — Production security audit performed across the full
  repository (Flutter client, FastAPI backend, Cloud Functions, Firestore
  rules, CI, Docker/deploy config): 16 of 17 findings fixed and
  regression-tested (rate limiting, security headers, dependency CVEs,
  `FIREBASE_CHECK_REVOKED` production hardening, repo-hygiene cleanup,
  HTTPS-enforcement gap in the Flutter release build, weak client-side
  email validation). One finding (a transitive `uuid` CVE via
  `firebase-admin`) remains open with no available upstream patch.
  `docs/PRODUCTION_SECURITY_AUDIT.md`, `docs/SECURITY_MODEL.md`,
  `docs/OPPORTUNITY_VERIFICATION_SYSTEM.md`, `docs/AUTHORITATIVE_SOURCES.md`
  written as the standing security/architecture reference set.
- **2026-08-17** — `applications` and `verification` real FastAPI backends
  landed, wired into the Flutter client via `ApiApplicationRepository`/
  `ApiVerificationRepository` (an optional-constructor-override
  dependency-injection pattern introduced this round, also used to make
  widget tests possible without a live Firebase app).
- **2026-08-17** — Auth screen restructured into scrollable wide/narrow
  layouts; EU MSCA calls reclassified as fellowships; a Grants.gov
  individual-eligibility source added and classified as scholarship.
- **2026-08-18** — `ui-ux-pro-max` design system applied across applicant,
  provider, and back-office surfaces; design tokens persisted to
  `design-system/scholarsphere/MASTER.md`.
- **2026-08-18** — `providers`/`provider_opportunities` real FastAPI
  backend landed: organization registration/verification/suspend/appeal,
  server-authoritative risk scoring, case-insensitive duplicate-domain
  prevention, a 5-item provider verification checklist, real Firebase
  Storage document upload with owner-scoped `storage.rules`. A separate,
  isolated pipeline from the Grants.gov-family opportunities table.
- **2026-08-18** — Dependabot alerts (`js-yaml`, `uuid`) fixed in Cloud
  Functions.
- **2026-08-20** — Real Notifications backend added: in-app delivery,
  preferences, deadline reminders (supersedes the earlier
  demo-only-notifications status recorded in
  `scholarsphere_backend/README.md`'s Known Limitations, which now needs a
  follow-up correction).
- **2026-08-20** — Applicant Profile and Documents real backends landed
  (per commit history; not independently re-audited by the 2026-08-17
  security review, which predates them).
- **2026-08-21** — Further backend feature work landed ("backend
  features01", "completed features" per commit history).

### Known outstanding items carried into Task.md
- ~~Search-index rebuild / expired-opportunity-detection background jobs
  still read from demo (fake) opportunity data instead of the real API
  repository.~~ Fixed 2026-08-21 — see the `[2026-08-21]` entry above.
- ~~Verification Officer dashboard landing metrics still read from the demo
  repository while the queue itself is real.~~ Fixed 2026-08-21 — see the
  `[2026-08-21]` entry above.
- Several 2026-08-18 through 2026-08-21 backend additions have not yet had
  an independent security review against the 2026-08-17 audit's own
  checklist.
- Firebase console bundle-ID re-registration and real release signing
  remain blocked on access this session/tooling can't provide.

See `Road_map.md` for the full phase-by-phase status and `Task.md` for the
active task board.

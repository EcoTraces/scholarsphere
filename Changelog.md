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

## [2026-08-22] — Security review, Firebase officer roster, audit-read endpoint, notification-delivery honesty fix

Independent security review of the applications/verification/providers/
provider_opportunities backends (`Task.md` Critical Task), the Firebase
verification-officer roster gap (`Task.md` Critical Task), and three
backlog items were inspected, fixed where real gaps were found, tested, and
verified. Full backend suite re-run and passing after every change:
**448/448 (`pytest -q`).** Flutter suite not touched, not re-run this
session — no Flutter files changed.

### Fixed
- **Security review of applications/verification/providers/
  provider_opportunities — 4 real gaps found and fixed, 0 IDOR/auth-bypass
  found.** `providers.py`'s administrator/review/suspension/appeal
  mutations had no audit trail (added `append_audit()` calls);
  `add_administrator` stored raw wire-format permission strings instead of
  the model's enum values, silently breaking any permission check against
  them (added `permission_from_wire()` conversion); `submit_opportunity`
  checked only org-level publish rights, not the calling administrator's
  own granted permissions, so any administrator on a publish-enabled
  organization could submit opportunities regardless of their individual
  grants (added `_submitter_permission_check()`); `ProviderReviewRequest
  .decision` accepted an unconstrained string instead of the real 3-value
  set (restricted to a `Literal`). Files: `app/api/routes/providers.py`,
  `app/api/routes/provider_opportunities.py`, `app/schemas/provider.py`.
- **Firebase verification-officer roster gap.** Reverification reminders
  previously targeted officers found only via `ImportAuditLog` activity
  history, so a brand-new officer with zero prior decisions received no
  reminders. New `app/services/firebase_users.py` enumerates all Firebase
  users through the Admin SDK's real pagination mechanism, filters by the
  `role` custom claim in application code (there is no server-side
  "query by custom claim" API — confirmed against the installed SDK), and
  falls back to the audit-log heuristic if enumeration fails. File:
  `app/tasks/opportunity_sync.py`.
- **Notification-delivery honesty bug.** `process_due_notifications`
  marked `email`/`push` notifications "delivered" even though no
  SMTP/ESP or FCM/APNs provider is integrated anywhere in this backend —
  a fabricated success on the two channels most notifications actually
  use (both are in the default `NotificationPreferences.channels`).
  Restricted `_CONFIGURED_CHANNELS` to `{"in_app"}`; notifications with no
  deliverable channel now honestly report `failed` instead. File:
  `app/services/notification_dispatch.py`.

### Added
- **Security Officer read access to `ImportAuditLog`.**
  `securityAdministrator`/`administrator`/`superAdministrator` could read
  the separate `AuditRecord` trail but had no read access to
  `ImportAuditLog`, which actually covers the opportunity-verification and
  provider-lifecycle pipeline. Added `GET /audit/import-records` with
  filtering and pagination, gated on the same roles as every other route
  in `audit.py`. Files: `app/api/routes/audit.py`, `app/schemas/
  audit_log.py`.

### Reviewed, no change needed
- USAJOBS live smoke test — blocked, no `USAJOBS_API_KEY` in this
  environment; mocked coverage (`tests/test_usajobs.py`) is the strongest
  test available here.
- Differential Storage access for provider-granted applicant documents —
  re-confirmed the current state fails *safe* (a granted provider is wrongly
  denied the file, not the reverse), so left as a scoped follow-up rather
  than an unplanned feature build; see `Task.md`.
- The four dead-code domain areas (`eligibility_rules`, `integrations`,
  `data_transfer`, `platforms`) — re-confirmed still accurate as
  **DECISION REQUIRED**, a product decision rather than an engineering one.

---

## [2026-08-22] — Web-scraper source tier and confidence-triage queue signal

Requested as an autonomous-discovery/publication initiative; two decisions
were confirmed with the user before implementation rather than assumed:
keep the mandatory human-verification gate for every source (add
confidence *triage*, not auto-publish), and scrape only specific named
organizations approved individually. Full backend suite re-run and passing
after every change: **483/483 (`pytest -q`)**, up from 448.

### Added
- **Five new opportunity sources via a new web-scraper adapter tier**
  (`app/services/web_scraper_base.py`) — Commonwealth Scholarships (CSC
  UK), Chevening Scholarships, DAAD Scholarship Database (curated seed-id
  list, coverage caveat below), Chinese Embassy in Sierra Leone
  (scholarship announcements), and Sierra Leone's Ministry of Technical
  and Higher Education (government scholarship announcements, including
  partner-government offers such as Russia's). None of these
  organizations publish an official API, RSS feed, or dataset — see
  `docs/AUTHORITATIVE_SOURCES.md` #8-#12 for the per-source research and
  robots.txt/terms check performed before each was added. Every scraped
  record goes through the identical mandatory verification/publication
  pipeline as an API source (`NormalizedExternalOpportunity` enforces
  `pending`/`unpublished` at the schema level regardless of source).
  Fulbright was researched and deliberately not integrated (decentralized
  per-country administration, no single official listing) — see the
  declined-sources table in `docs/AUTHORITATIVE_SOURCES.md`.
- **`app/core/http_client.py::get_html`** — HTML fetch with the same
  HTTPS-only, timeout, response-size-cap, and bounded-retry protections
  `get_json`/`post_json` already had.
- **`app/services/verification_confidence.py`** — a deterministic,
  fully-explained (not AI/ML) confidence scorer wired into
  `GET /external-opportunities/pending-verification?sort=confidence`,
  exposing `confidence_level`/`confidence_reasons` on each queue item as a
  triage priority hint only. It has no path to set `verification_status`
  or `publication_status`; every record still requires an officer's
  explicit `approved` decision regardless of score.
- **`extract_confident_date`/`extract_confident_date_after`**
  (`app/services/parsing.py`) — sets a scraped deadline only when an
  explicit day+month+year date literal is present in the source text;
  confirmed against real prose from both DAAD and CSC UK that states a
  closing date without an adjacent year, which is correctly left `null`
  rather than guessed ("never invent data").
- 5 new `OpportunitySource` registry rows (`trust_level="web_scraped"`)
  and 5 new daily Celery beat entries.
- 34 new tests: `tests/test_cscuk_scholarships.py`, `test_chevening.py`,
  `test_daad_scholarships.py`, `test_embassy_announcements.py`,
  `test_verification_confidence.py`, new `get_html` cases in
  `test_http_client.py`, a new confidence-field case in
  `test_verification_actions.py`. Real HTML fetched from the live sites on
  2026-08-22 backs 4 of the 5 new adapters' tests
  (`tests/fixtures/*.html`); the fifth (`mthe_sierra_leone`) uses a
  clearly-labeled synthetic fixture — see "Reviewed, no change needed"
  below.
- **Live end-to-end verification.** With no Celery broker available in
  this environment, `app/tasks/opportunity_sync._run_source_sync` (the
  exact function every Celery task here calls) was invoked directly
  against a temporary database for all 5 new sources with no HTTP
  mocking, against the real live sites: `cscuk_scholarships` 6/6 created,
  `chevening` 1/1 (deadline correctly parsed, `2026-10-06`),
  `daad_scholarships` 6/6, `china_embassy_sl` 2/2, `mthe_sierra_leone` 0/0
  with a clean non-fatal error (confirming its connectivity blocker fails
  gracefully rather than crashing the sync).

### Fixed
- **`china_embassy_sl` deadline mis-extraction, found by the live run
  above.** A "Farewell Ceremony" article's publish date was picked up as
  if it were an application deadline, because deadline extraction took
  the first date literal anywhere in the article body with no context
  check. Fixed by anchoring on a nearby deadline-indicating keyword
  (`_DEADLINE_KEYWORDS` in `app/services/embassy_announcements.py`,
  matching the pattern already used for `cscuk_scholarships`/
  `daad_scholarships`); re-ran live and confirmed both real articles now
  correctly report `deadline=None`. Regression test added using the real
  HTML that caught it
  (`tests/test_embassy_announcements.py::test_china_embassy_unrelated_date_is_not_mistaken_for_a_deadline`).
  Full backend suite after the fix: **483/483**.
- `pip-audit -r requirements.txt`: no known vulnerabilities, including the
  new `beautifulsoup4` dependency.

### Changed
- `docs/AUTHORITATIVE_SOURCES.md`, `docs/OPPORTUNITY_VERIFICATION_SYSTEM.md`
  (new §6 on confidence triage; §7-§11 renumbered accordingly, with every
  internal cross-reference to the old numbering updated),
  `docs/PRODUCTION_SECURITY_AUDIT.md` §2.6 (dated update note appended;
  original finding preserved rather than rewritten), `docs/
  SECURITY_MODEL.md` (fixed a now-stale §9→§10 cross-reference),
  `scholarsphere_backend/README.md` all updated to describe the new
  architecture accurately.
- `tests/test_opportunity_import.py::test_source_seeding_is_idempotent`
  updated for the new source count (8 → 13).

### Reviewed, no change needed
- `mthe_sierra_leone`'s live-site smoke test — **blocked**:
  `https://www.mthe.gov.sl` and `http://www.mthe.gov.sl` both refused
  every connection attempted from this environment (2026-08-22, multiple
  attempts). Looks like a network/hosting issue outside this codebase's
  control, not confirmed either way. The adapter is implemented and
  tested against a synthetic fixture only — not claimed as live-verified.
  See `Task.md` Integration Tasks.

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

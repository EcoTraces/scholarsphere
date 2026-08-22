# ScholarSphere — Active Development Task Board

**Last verified against the codebase:** 2026-08-21. Cross-referenced with
`Road_map.md` (phase view) and `PRD.md` (feature status). Move a task to
**Completed** only after it's actually implemented *and* verified (tests
run, not just read).

Status: `[ ]` Not started · `[~]` In progress · `[x]` Completed · `[!]` Blocked

---

## Current Project Status

ScholarSphere is a Flutter + Firebase + FastAPI/PostgreSQL platform for
verified scholarship/opportunity discovery. As of 2026-08-21, the large
majority of the 36 Flutter feature areas are wired to real FastAPI backends
(see PRD.md §3.1) — this is a significant jump from the 2026-08-17 security
audit's "35 of 36 still demo" finding, because five more days of backend
work landed after that audit was written. **The four wiring/completeness
gaps this session was scoped to fix — search-index background job, real
Verification Officer dashboard metrics, reverification reminder delivery,
and provider document-sharing consent — are now done and verified**; see
Changelog.md for the dated entry and Completed Tasks below.

Test baseline as of this session's own verified run (2026-08-21, after the
four fixes below): **431/431 backend tests passing** (`pytest -q`),
**88/88 Flutter tests passing** (`flutter test`), `flutter analyze` clean
project-wide. Re-run both suites before trusting these numbers if more
than a few commits have landed since.

---

## Critical Tasks

- [ ] **Security-review the applications/verification and
      providers/provider_opportunities backends.** Neither has been through
      the 2026-08-17 audit's own §2 checklist (auth, authz, input
      validation, IDOR) — they were built consistent with reviewed
      patterns, which is not the same as independently reviewed. Files:
      `scholarsphere_backend/app/api/routes/{applications,verification via
      external_opportunities,providers,provider_opportunities}.py`. Note:
      this session's new `GET /external-opportunities/verification-summary`
      endpoint and the `applicant_documents.py` consent-gating change (see
      Completed Tasks) are both read-mostly/precondition-only additions
      that reuse existing `preview_access`/RBAC and consent patterns
      exactly — worth including in the same review pass rather than
      treating as pre-cleared by association.
- [ ] **Build a Firebase Admin SDK "list users by custom claim" helper for
      reverification-reminder recipients.** The fix landed this session
      (see Completed Tasks) targets officers via `ImportAuditLog` activity
      history, since there's no local user directory — real, but it means
      a brand-new officer with zero prior decisions gets no reminders
      until their first one. Needs a live Firebase project to build and
      test `firebase_admin.auth.list_users()` filtering against; not
      available in this environment. File:
      `scholarsphere_backend/app/tasks/opportunity_sync.py`
      (`_reverification_recipients`).

## Backend Tasks

- [ ] Smoke-test the USAJOBS adapter against a live authenticated response
      — field names are based on documentation only, never exercised live
      (`app/services/usajobs.py`). Requires a real `USAJOBS_API_KEY`.
- [ ] Add email/push/SMS delivery providers for
      `ScholarSphereNotification`. Today only the `in_app` channel is
      genuinely delivered (appearing in `GET /notifications` *is* the
      delivery for that channel); `process_due_notifications` marks
      email/push as "delivered" without any SMTP/FCM/Twilio integration
      behind it — a pre-existing gap, not introduced this session, but
      directly relevant now that reverification reminders (this session)
      and deadline reminders both depend on it. Needs real provider
      credentials and an SDK integration, not a code-only fix.
- [ ] Add a Security Officer read endpoint for `ImportAuditLog` and
      rate-limit events — role exists in RBAC, no route reads it. New file
      likely `app/api/routes/security_audit_read.py` or an extension to
      `audit.py`.
- [ ] Add Firebase Admin Storage existence check for provider-document
      paths before accepting them into a `Provider` record (currently
      validates path *shape* only). Requires adding `firebase-admin`'s
      Storage SDK usage to the backend.
- [ ] Add differential Storage access for provider-granted applicant
      documents. The Postgres-level grant is now consent-gated (fixed this
      session — see Completed Tasks), but `storage.rules` still scopes
      `applicant-documents/` to owner-only, so a provider granted access in
      Postgres still cannot fetch the actual file, and there is no
      provider-facing "list documents shared with me" endpoint yet either.
      Files: `storage.rules`, a new provider-facing read route.
- [ ] Decide whether `eligibility_rules`, `integrations`, `data_transfer`,
      `platforms` get real backends or get deleted — currently dead code
      (domain model + demo repository, no route, no screen). Product
      decision needed before engineering work.

## Frontend Tasks

- [ ] Consider gating `Demo*Repository` construction behind a build flag so
      a release build fails to compile against a demo implementation for
      any feature that's supposed to be real-backend-only —
      recommendation from `docs/PRODUCTION_SECURITY_AUDIT.md` §13, not yet
      implemented.
- [ ] Move `DemoAuthRepository` (plaintext-password bootstrap admin,
      fabricated Google-sign-in bypass) to a test-only fixture location so
      it can never accidentally get wired into a real build — currently
      unreachable from `app.dart` but still shippable `lib/` code.

## Database Tasks

- [ ] None outstanding at the schema level — all 31 migrations are current
      and validated. Revisit this section once new features (eligibility
      rules, security-officer audit read, etc.) require schema changes.

## Integration Tasks

- [ ] Investigate a licensed data feed or per-provider partnership for
      named individual-scholarship programs (DAAD, Chevening, Fulbright,
      etc.) — the single largest real coverage gap, and not addressable
      with more of the current API-integration pattern (`docs/
      AUTHORITATIVE_SOURCES.md`).
- [ ] Register a new Firebase app under `com.scholarsphere.app` in the
      Firebase console and download fresh `google-services.json`/
      `GoogleService-Info.plist` — **blocked**, requires Firebase console
      access outside any coding session. Blocks Google Sign-In on the
      renamed bundle ID.

## Testing Tasks

- [ ] Re-run `pytest -q` and `flutter test` periodically and update the
      numbers cited in this file and `Road_map.md` — current verified
      counts (431/431 backend, 88/88 Flutter, 2026-08-21) will go stale as
      soon as more commits land.
- [ ] Add an IR-relevant test: verify `suspendUser` actually revokes
      refresh tokens end-to-end against a real (non-mocked) Firebase
      project before relying on it as the documented "kill switch" for
      account compromise.

## Bugs and Issues

- [!] Firebase console still has the **old** bundle ID
      (`com.example.scholarsphere`) registered — Google Sign-In won't
      authenticate against the renamed app until re-registered. Blocked on
      console access.
- [!] Android/iOS/macOS release builds sign with the debug key, not a real
      release keystore. Blocked on the team's signing credentials.
- [ ] `firebase-admin`'s transitive `uuid` dependency carries a moderate
      CVE (GHSA-w5hq-g745-h8pq) with no patched release yet — tracked, not
      actionable today; re-check `npm audit` monthly.
- [ ] `storage.rules`'s new provider-document rules have been reasoned
      about but never deployed and exercised against a real Firebase
      Storage bucket in any environment this project has had access to.

## Completed Tasks

Moved here only after real, verified implementation — see `Changelog.md`
for the full dated history.

- [x] Firebase Auth (email/password + Google), applicant self-registration
      with email verification, password reset, session restore.
- [x] Firestore `users/{uid}` persistence with default-deny rules elsewhere.
- [x] Admin-created managed accounts + suspension via Cloud Functions.
- [x] Opportunity discovery, evidence-backed verification pipeline
      (4-item checklist, 6 decisions, separate publication step), automatic
      90-day reverification and daily expiry.
- [x] Provider organization registration/verification + provider-submitted
      opportunity pipeline, isolated from the Grants.gov-family pipeline.
- [x] Applications (10-stage tracking), applicant profiles, applicant
      documents (real Firebase Storage upload).
- [x] Notifications (in-app, preferences, deadline reminders, admin tools).
- [x] Moderation, fraud investigation, privacy, legal compliance, data
      lifecycle, support, source registry, taxonomy, calendar, guidance,
      experience preferences, recommendations, provider analytics,
      analytics, audit (hash-chained), security (sessions/login
      history/alerts), operations console (backup/observability/release/
      system configuration), collection ledger.
- [x] Redis-backed rate limiting, security response headers, production
      config hardening, dependency vulnerability remediation (16/17
      findings fixed).
- [x] CI: Flutter (`analyze`/`test`/`build`), backend (`pytest`/
      `pip-audit`), functions (`lint`/`audit`) jobs.
- [x] Client-side form-validation design system (`lib/app/design/
      form_validation_styles.dart`) applied to auth, provider-registration,
      and applicant-profile forms.
- [x] **(2026-08-21)** Search-index background job fixed to read from the
      real `_apiOpportunityRepository`; the client-side
      `expiredOpportunityDetection` job (redundant with the real backend's
      own daily Celery task) was removed rather than re-pointed. Files:
      `lib/app/app.dart`. Verified: `flutter analyze` clean; new end-to-end
      widget test (`test/widget_test.dart`, "search-index background job
      rebuilds from the real opportunity repository, not demo data") drives
      the actual admin UI flow and asserts the real repository's data
      reaches `SearchIndexRepository.rebuild()`; full suite (88/88) passes.
- [x] **(2026-08-21)** Verification Officer dashboard now reads exclusively
      from `ApiVerificationRepository`, including a new
      `GET /external-opportunities/verification-summary` endpoint (pending
      count, verified-today count, reverification-due-soon count, status
      breakdown, 7-day decision activity, official-source ratio,
      approvals attributed to the calling officer). Dead
      `DemoVerificationRepository`/`_opportunityRepository` wiring removed
      from `app.dart`. Files: `scholarsphere_backend/app/api/routes/
      external_opportunities.py`, `app/schemas/external_source.py`,
      `lib/features/verification/data/api_verification_repository.dart`,
      `lib/features/verification/presentation/
      verification_officer_dashboard_screen.dart`, `lib/app/app.dart`.
      Verified: 4 new backend tests (`tests/test_verification_actions.py`)
      + full backend suite (431/431); rewritten Flutter widget test
      asserting real panel titles/metrics render; full Flutter suite
      (88/88).
- [x] **(2026-08-21)** Reverification reminders now create real
      `ScholarSphereNotification` rows (in-app channel — the one channel
      genuinely delivered by this backend today) for verification officers
      identified via real prior-decision history in `ImportAuditLog`,
      deduplicated by deterministic id, gated on the recipient's own
      notification preferences. New `NotificationEventType.reverification_due`.
      Files: `app/models/notification.py`, `app/services/
      notification_dispatch.py`, `app/tasks/opportunity_sync.py`. Verified:
      4 new tests (`tests/test_opportunity_tasks.py`) covering creation,
      dedup-on-rerun, preference opt-out, and honest zero-recipients
      reporting; full backend suite (431/431).
- [x] **(2026-08-21)** Provider document-sharing now requires an active
      `third_party_sharing` `ConsentRecord` (409 otherwise) and a real,
      existing `Provider` (404 otherwise); every successful grant writes an
      `OrganizationAccessRecord`; withdrawing that consent cascades to
      clear every existing `shared_with_provider_ids` grant. Files:
      `app/api/routes/applicant_documents.py`, `app/api/routes/privacy.py`,
      `lib/features/documents/data/api_document_repository.dart` (surfaces
      the real backend error message instead of a generic one). Verified:
      5 new/updated backend tests (`tests/test_applicant_documents_route.py`)
      covering the consent-blocked, withdrawn-consent, revocation-cascade,
      and unknown-provider cases; full backend suite (431/431); full
      Flutter suite (88/88, including the pre-existing demo-repository
      consent test).
- [x] **(2026-08-21)** Incidental fix found while verifying the above:
      `JobMonitorScreen`'s three `setState(_reload)` calls passed a `void`
      arrow-function tear-off whose body was itself an assignment
      expression, which still returns its value at runtime — tripping
      Flutter's "setState callback returned a Future" guard the first time
      any test actually drove that screen's actions. Fixed by wrapping each
      call in a block body. File: `lib/features/background_jobs/
      presentation/job_monitor_screen.dart`.

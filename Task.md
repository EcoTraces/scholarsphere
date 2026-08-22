# ScholarSphere — Active Development Task Board

**Last verified against the codebase:** 2026-08-22. Cross-referenced with
`Road_map.md` (phase view) and `PRD.md` (feature status). Move a task to
**Completed** only after it's actually implemented *and* verified (tests
run, not just read).

Status: `[ ]` Not started · `[~]` In progress · `[x]` Completed · `[!]` Blocked

---

## Current Project Status

ScholarSphere is a Flutter + Firebase + FastAPI/PostgreSQL platform for
verified scholarship/opportunity discovery. As of 2026-08-22, the large
majority of the 36 Flutter feature areas are wired to real FastAPI backends
(see PRD.md §3.1). **This session's independent security review of the
applications/verification/providers/provider_opportunities backends is
complete** (4 findings fixed, 0 IDOR/auth bypass found), the **Firebase
verification-officer roster gap is closed** (reminders now reach every
officer with the role, not just ones with prior decisions), a **Security
Officer audit-read endpoint** for `ImportAuditLog` now exists, the
notification-delivery status honesty bug (email/push silently marked
"delivered" with no provider behind them) is fixed, and a **web-scraper
source tier** (5 new sources: Commonwealth Scholarships, Chevening, DAAD,
Chinese Embassy in Sierra Leone, Sierra Leone's Ministry of Technical and
Higher Education) plus an **explainable confidence-triage signal** for the
verification queue were added — see Changelog.md for the dated entry and
Completed Tasks below. The mandatory human-verification gate was
deliberately kept: no opportunity, from any source, publishes without an
explicit officer decision — see
`docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` §6 for why, a decision confirmed
with the user rather than assumed.

Test baseline as of this session's own verified run (2026-08-22): **483/483
backend tests passing** (`pytest -q`, up from 448 — 34 new tests for the
scraper sources, confidence engine, `get_html`, and a live-testing
regression). Flutter suite not re-run this session (no Flutter files
changed). Re-run both suites before
trusting these numbers if more than a few commits have landed since.

---

## Critical Tasks

None outstanding. Both items below were resolved and verified this session
— see Completed Tasks for the full writeup.

## Backend Tasks

- [!] Smoke-test the USAJOBS adapter against a live authenticated response
      — field names are based on documentation only, never exercised live
      (`app/services/usajobs.py`). **Blocked:** `USAJOBS_API_KEY` is empty
      in this environment's `.env` and no live credential is available;
      mocked unit coverage (`tests/test_usajobs.py`) is the strongest test
      that can run here. Do not mark this done from mocked coverage alone.
- [!] Add real email/push/SMS delivery providers for
      `ScholarSphereNotification`. **Partially addressed this session:**
      the dishonest half of this gap is fixed — `process_due_notifications`
      no longer marks email/push "delivered" with no provider behind them
      (see Completed Tasks) — but no SMTP/ESP or FCM/APNs integration
      exists yet, so email/push notifications now honestly report `failed`
      instead of a fabricated `delivered`. Building real delivery still
      needs provider credentials and an SDK integration, not a code-only
      fix. Blocked on credentials.
- [ ] Add Firebase Admin Storage existence check for provider-document
      paths before accepting them into a `Provider` record (currently
      validates path *shape* only). Requires adding `firebase-admin`'s
      Storage SDK usage to the backend (no `storageBucket` is configured on
      the Firebase app today — see `app/core/auth.py::initialize_firebase`).
- [ ] Add differential Storage access for provider-granted applicant
      documents. **Reviewed again this session, no change made:** the
      Postgres-level grant is consent-gated (`applicant_documents.py`), but
      `storage.rules` still scopes `applicant-documents/` to owner-only, so
      a provider granted access in Postgres still cannot fetch the actual
      file. This fails *safe*, not open — a granted provider is wrongly
      denied, not an ungranted one wrongly allowed — so it is a
      completeness gap, not a security hole, and was left as a scoped
      follow-up rather than an unplanned mid-session feature build (it
      needs a signed-URL-issuing download route plus a
      provider-facing "list documents shared with me" endpoint). Files:
      `storage.rules`, a new provider-facing read route.
- [ ] **DECISION REQUIRED:** decide whether `eligibility_rules`,
      `integrations`, `data_transfer`, `platforms` get real backends or get
      deleted — currently dead code (domain model + demo repository, no
      route, no screen). This is a product decision, not an engineering
      one; re-confirmed still accurate this session, no code change made.

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

- [x] **(2026-08-22)** DAAD, Chevening, and Commonwealth Scholarships (CSC
      UK) — three of the named individual-scholarship programs previously
      listed as the largest coverage gap — are now integrated via a new
      web-scraper source tier (`app/services/web_scraper_base.py`), since
      none publish a public API. See `docs/AUTHORITATIVE_SOURCES.md` #8-#10.
- [!] Smoke-test the `mthe_sierra_leone` scraper
      (`app/services/embassy_announcements.py::SierraLeoneMTHESource`)
      against the real `mthe.gov.sl` site. **Blocked:** the site refused
      every connection attempted from this development environment
      (2026-08-22, both `http://` and `https://`, multiple attempts) — this
      looks like a network/hosting issue outside this codebase's control,
      not confirmed either way. The adapter is implemented and
      unit-tested against a clearly-labeled synthetic fixture, not real
      captured HTML — do not mark this done from that alone. See
      `docs/AUTHORITATIVE_SOURCES.md` #12.
- [ ] Broaden `daad_scholarships`' coverage beyond its current curated seed
      list (`Settings.daad_scholarship_detail_ids`, 6 ids). DAAD's search
      widget loads results via an undocumented AJAX endpoint and its
      public sitemap does not cover the scholarship database's detail
      pages — no ToS-respecting bulk-discovery method was found this
      session. Either add more ids manually as they're identified, or
      replace the adapter if DAAD ever documents its search endpoint. See
      `docs/AUTHORITATIVE_SOURCES.md` #10.
- [ ] Investigate a licensed data feed or per-provider partnership for the
      remaining named individual-scholarship programs not covered above
      (Fulbright — researched and deliberately not integrated, see
      `docs/AUTHORITATIVE_SOURCES.md`'s declined-sources table — plus
      university-specific and foundation funds generally) — not
      addressable with more of the current API-integration pattern, and
      only some of it is addressable by more scraping (`docs/
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
- [x] **(2026-08-22)** Independent security review of `applications.py`,
      `providers.py`, `provider_opportunities.py`, and the
      verification/external-opportunities routes (auth, RBAC, IDOR,
      ownership, mass assignment, input validation, auditability). No
      IDOR/auth-bypass found — every ownership check correctly 404s (not
      403) on mismatch. Four real gaps found and fixed:
      1) `providers.py`'s administrator/provider-review/suspension/appeal
      mutations had no audit trail — added `append_audit()` calls.
      2) `add_administrator` stored wire-format (camelCase) permission
      strings directly instead of converting to the model's enum values,
      which silently broke any future permission check against them —
      added `permission_from_wire()` and applied it before storage.
      3) `submit_opportunity` only checked org-level
      "does this provider have publish rights at all", not the *calling*
      administrator's own granted permissions — added
      `_submitter_permission_check()` so an administrator without
      `publishOpportunities` on their own record is correctly 403'd even
      when the organization overall has publish rights.
      4) `ProviderReviewRequest.decision` accepted an unconstrained string
      instead of the actual 3-value decision set — restricted to a
      `Literal`. Files: `app/api/routes/providers.py`,
      `app/api/routes/provider_opportunities.py`, `app/schemas/
      provider.py`. Verified: `tests/test_provider_opportunities_route.py`
      (2 new tests: permission-denied and owner-always-allowed cases) +
      `tests/test_providers_route.py`; full backend suite (433/433 at the
      time, then 445/445 after Firebase work below).
- [x] **(2026-08-22)** Firebase verification-officer roster gap closed.
      Reminders previously targeted officers found via `ImportAuditLog`
      activity history only, so a brand-new officer with zero prior
      decisions got no reminders. New `app/services/firebase_users.py`
      enumerates *all* Firebase users via the Admin SDK's real, verified
      pagination mechanism (`auth.list_users()` /
      `page.get_next_page()` — confirmed via `inspect.signature()` against
      the installed SDK; there is no "query by custom claim" API), filters
      by the `role` custom claim in application code, excludes disabled
      users, and dedupes. Falls back to the previous audit-log heuristic if
      Firebase enumeration fails, so the reminder system degrades
      gracefully instead of silently sending zero notifications. File:
      `app/tasks/opportunity_sync.py` (`_reverification_recipients`).
      Verified: 10 new unit tests (`tests/test_firebase_users.py`) covering
      role filtering, disabled-user exclusion, multi-page pagination,
      dedup, empty roster, non-matching claims, snake_case normalization,
      and both full and partial-pagination SDK failure; 2 new + 4 updated
      integration tests (`tests/test_opportunity_tasks.py`) proving the
      brand-new-officer gap is closed and the audit-log fallback fires
      correctly. **Not tested against a live Firebase project** — no live
      credentials available in this environment; this is honestly declared
      rather than assumed.
- [x] **(2026-08-22)** Security Officer read access to `ImportAuditLog`.
      `securityAdministrator`/`administrator`/`superAdministrator` could
      already read `AuditRecord` (backup/collection/data_lifecycle/
      release/system_configuration events) but had no way to read
      `ImportAuditLog`, the separate trail that actually covers the
      opportunity-verification and provider-lifecycle pipeline — the one
      that protects this platform's "Verified" trust label. Added
      `GET /audit/import-records` with `actor_id`/`action`/`entity_type`/
      `entity_id`/`result` filters and pagination, gated on the same
      `audit_access` roles as every other route in `audit.py`. Files:
      `app/api/routes/audit.py`, `app/schemas/audit_log.py`. Verified: 3
      new tests (`tests/test_audit_route.py`) covering access-denial for
      non-audit roles, successful read with seeded rows, and
      filter+pagination; full backend suite (448/448).
- [x] **(2026-08-22)** Notification-delivery honesty fix. Discovered while
      reviewing the email/push backlog item: `process_due_notifications`'s
      `_CONFIGURED_CHANNELS` wrongly listed `email` and `push` alongside
      `in_app`, so any notification on those channels (which is most of
      them — `email`/`push` are in the default `NotificationPreferences`)
      was marked `delivered` even though no SMTP/ESP or FCM/APNs
      integration exists anywhere in this backend — a fabricated success,
      not a real one. Fixed by restricting `_CONFIGURED_CHANNELS` to
      `{"in_app"}`; a notification with real delivery capacity on at least
      one channel (`in_app`) still reports `delivered`, one with only
      undeliverable channels now honestly reports `failed` with reason
      "Delivery provider is not configured." File: `app/services/
      notification_dispatch.py`. Verified: new test
      (`tests/test_notification_tasks.py`,
      `test_process_due_notifications_task_does_not_fabricate_email_or_push_delivery`)
      covering email-only, push-only, and mixed in_app+email cases; full
      backend suite (448/448). Real email/push delivery is still not
      built — see Backend Tasks — this fix only stops the false-positive
      status, it does not add a provider.
- [x] **(2026-08-22)** Web-scraper source tier and confidence-triage
      signal added, following an explicit two-part product decision
      confirmed with the user before implementation: (1) keep the
      mandatory human-verification gate for every source, including
      trusted ones — no auto-publish — and add explainable confidence
      scoring only to help officers triage the queue; (2) add web
      scraping, but only for specific named organizations approved
      individually, each checked for an official-domain/robots.txt/terms
      concern before being built.
      - **New sources** (`app/services/web_scraper_base.py` and its
        subclasses): Commonwealth Scholarships (CSC UK), Chevening
        Scholarships, DAAD Scholarship Database (curated seed-id list —
        see Integration Tasks for the coverage caveat), Chinese Embassy in
        Sierra Leone (scholarship announcements), Sierra Leone Ministry of
        Technical and Higher Education (government scholarship
        announcements, including partner-government offers like Russia's —
        **live-test blocked**, see Integration Tasks). Four of five were
        tested against real HTML fetched from the live sites on
        2026-08-22 (fixtures in `tests/fixtures/`); `mthe_sierra_leone`
        was not (connection refused from this environment) and is tested
        against a labeled-synthetic fixture instead — declared honestly
        rather than assumed working. Fulbright was researched and
        deliberately not integrated — see `docs/AUTHORITATIVE_SOURCES.md`'s
        declined-sources table for why.
      - **New infrastructure**: `app/core/http_client.py::get_html` (HTML
        fetch with the same HTTPS-only/timeout/size-cap/retry protections
        `get_json`/`post_json` already had); `app/services/parsing.py`'s
        `extract_confident_date`/`extract_confident_date_after` (a deadline
        is set only when an explicit day+month+year date literal is
        present in the source text — confirmed against real prose from
        both DAAD and CSC UK that states a closing date *without* an
        adjacent year, which is correctly left `null` rather than guessed).
      - **Confidence triage**: `app/services/verification_confidence.py`,
        a deterministic, fully-explained (not AI/ML) scorer wired into
        `GET /external-opportunities/pending-verification?sort=confidence`
        (`confidence_level`/`confidence_reasons` on each item) — a
        priority hint only; every record still requires an officer's
        explicit `approved` decision regardless of score.
      - **Registry/scheduling**: 5 new `OpportunitySource` rows
        (`trust_level="web_scraped"`, distinguishing them from
        `"official"` API sources in the confidence scorer), 5 new Celery
        beat entries syncing daily (lighter cadence than the 6-12h API
        sources).
      - Files: `app/core/http_client.py`, `app/core/config.py`,
        `app/services/{web_scraper_base,cscuk_scholarships,chevening,
        daad_scholarships,embassy_announcements,verification_confidence,
        parsing,source_registry}.py`, `app/tasks/opportunity_sync.py`,
        `app/api/routes/external_opportunities.py`,
        `app/schemas/external_source.py`, `requirements.txt`.
      - Docs updated: `docs/AUTHORITATIVE_SOURCES.md` (5 new source
        entries, corrected the now-stale "no web scraping" claim),
        `docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` (new §6 on confidence
        triage, renumbered §7-§11), `docs/PRODUCTION_SECURITY_AUDIT.md`
        §2.6 (dated update note, original finding preserved), `docs/
        SECURITY_MODEL.md` (fixed a now-stale cross-reference),
        `scholarsphere_backend/README.md`.
      - Verified: 33 new tests (`tests/test_cscuk_scholarships.py`,
        `test_chevening.py`, `test_daad_scholarships.py`,
        `test_embassy_announcements.py`, `test_verification_confidence.py`,
        new `get_html` cases in `test_http_client.py`, a new confidence
        case in `test_verification_actions.py`) plus one existing test
        updated for the new source count
        (`test_opportunity_import.py::test_source_seeding_is_idempotent`).
      - **Live end-to-end verification (2026-08-22, follow-up).** No
        Celery broker/worker is available in this environment (no Redis,
        no Docker), so `app/tasks/opportunity_sync._run_source_sync` — the
        exact function every Celery task in this file calls — was invoked
        directly against a temporary SQLite database for all 5 new
        sources, with **no HTTP mocking**, hitting the real live sites.
        Results: `cscuk_scholarships` 6/6 records created;
        `chevening` 1/1, deadline correctly parsed as `2026-10-06`;
        `daad_scholarships` 6/6; `china_embassy_sl` 2/2;
        `mthe_sierra_leone` 0/0 with `status=completed` and a clean logged
        error (`External page is temporarily unavailable`) — confirming
        the earlier connection-refused finding is handled as a graceful,
        non-fatal sync failure, not a crash. `OpportunitySyncHistory`,
        `ExternalOpportunity`, and duplicate-detection state were all
        inspected directly from the database, not just the task's return
        value.
      - **Real defect found and fixed by this live run.** The
        `china_embassy_sl` sync initially returned a *wrong* deadline for
        both articles (`2026-05-12` and `2026-08-21`) — inspection showed
        the second was the publish date of a "Farewell Ceremony" article
        (about students who had *already* received their scholarships),
        not an application deadline; the naive "first date literal
        anywhere in the article body" extraction in
        `app/services/embassy_announcements.py` had picked it up
        regardless. Fixed by anchoring extraction on a nearby
        deadline-indicating keyword (`_DEADLINE_KEYWORDS`), matching the
        pattern already used for `cscuk_scholarships`/`daad_scholarships`;
        re-ran live and confirmed both articles now correctly report
        `deadline=None`. Added a regression test using the real HTML that
        caught the bug
        (`tests/test_embassy_announcements.py::test_china_embassy_unrelated_date_is_not_mistaken_for_a_deadline`,
        `tests/fixtures/china_article_farewell.html`). This is exactly why
        Phase 14's real-data-testing loop matters — mocked-only tests
        would never have caught this.
      - `./.venv/Scripts/python.exe -m pip_audit -r requirements.txt`:
        **no known vulnerabilities**, including the new `beautifulsoup4`
        dependency (first attempt hit a pypi.org network timeout in this
        environment; retried successfully).
      - Full backend suite after the fix: **483/483**.
      - **Still not done, and not claimed**: no source was synced through
        an actual running Celery beat schedule + broker in this session
        (no Redis/Docker available here) — the task *function* was
        verified directly and end-to-end as described above, which
        exercises the same code Celery would call, but the
        scheduling/broker/worker layer itself was not independently
        re-verified for these 5 additions. `mthe_sierra_leone`'s
        connectivity blocker was reconfirmed (not resolved) — it remains
        an environment/network limitation outside this codebase's
        control, not fabricated as fixed.

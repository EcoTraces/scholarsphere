# ScholarSphere — Active Development Task Board

**Last verified against the codebase:** 2026-08-23. Cross-referenced with
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

**(2026-08-23 update)** A follow-up production-readiness hardening pass
added: startup-time Firebase credential validation (was lazy, first-request
only — see Completed Tasks), a corrected Firebase bundle-ID investigation
(the previous "old bundle ID" note was stale — see Bugs and Issues), a more
precise MTHE connectivity diagnosis (DNS resolves, TCP times out — not a
refusal), a real same-host-only fix for a genuine SSRF-adjacent gap in the
embassy-announcement adapter, a real (`task_always_eager`) Celery
task-interface test, an idempotency test, and cross-cutting scraper
resilience tests. `pip-audit` re-confirmed clean.

**(2026-08-23, country-expansion update)** A global target-country
expansion added 9 more web-scraper sources across two batches — Wells
Mountain Initiative (WMI), Türkiye Bursları, Government of Ireland GOI-IES,
ICCR (India), Swedish Institute (Sweden), Eswatini SLAS, then Italy
(MAECI), Greece (IKY), and South Africa (NRF) — following the exact same
architecture, never-invent-data discipline, and mandatory-human-review gate
as every prior source. 6 of 9 are live-verified; 3 are implemented but
live-blocked by documented external issues (India and South Africa: a real,
reproducible TLS certificate-chain defect on each server's own end;
Eswatini: the same network-timeout pattern already seen with Sierra
Leone's MTHE). A full 23-country research inventory was also produced —
see `docs/COUNTRY_PROVIDER_REGISTRY.md` — of which 11 more countries have a
credible official candidate identified but not yet implemented, 2 have no
reliable source found, and 1 (Cyprus) is blocked by active anti-bot
protection that was deliberately not bypassed.

Test baseline as of this session's own verified run (2026-08-29): **531/531
backend tests passing** (`pytest -q`, up from 511 on 2026-08-23 — 7 for
differential Storage access, 6 for link-health monitoring, 3 for the
Netherlands source, 4 for the discovery-summary endpoint). Flutter suite
not re-run this session (no Flutter SDK available in this environment); one
small Flutter data-layer addition landed (see Completed Tasks' master-prompt
entry) but was not compiled or run. Re-run both suites before trusting
these numbers if more than a few commits have landed since.

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
      validates path *shape* only). **Partially unblocked (2026-08-29):**
      `Settings.firebase_storage_bucket` now exists and
      `initialize_firebase()` passes `storageBucket` (added for the
      differential-Storage-access feature below), so the Admin SDK's
      Storage client can now actually be constructed — the existence
      check itself (calling it from `providers.py`'s submission route)
      is still not implemented.
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
- [x] **(2026-08-23)** Global country-coverage expansion. Full research
      inventory across WMI + 23 target countries produced first (see
      `docs/COUNTRY_PROVIDER_REGISTRY.md`), then implementation on the
      strongest candidates rather than a blind pass through the whole
      list. 6 new sources added, sharing a new
      `_SingleProgramSource` base
      (`app/services/national_scholarship_programs.py`) for the 5 that fit
      the single-flagship-program shape (WMI, Türkiye Bursları, Ireland
      GOI-IES, India ICCR, Sweden SI), plus Eswatini SLAS on the existing
      embassy-announcement pattern. See `docs/AUTHORITATIVE_SOURCES.md`
      #13-#18 for full per-source detail. Status:
      - **Live-verified 2026-08-23** (real sync against the real site,
        real opportunity created): WMI (deadline `2026-03-06`), Türkiye
        Bursları (deadline `2026-02-20`, correctly the closing date of a
        "10 January – 20 February 2026" range), Ireland GOI-IES (deadline
        `null` — honestly absent from that page, not guessed), Sweden SI
        (deadline `null`, same reason).
      - **Implemented, live-blocked, not falsely claimed working**: India
        ICCR — a real `curl` fetch succeeds, but this backend's actual
        HTTP path (httpx + certifi's strict TLS verification) fails with
        `SSLCertVerificationError: unable to get local issuer certificate`
        — ICCR's own server isn't sending a complete certificate chain.
        Deliberately **not** worked around with `verify=False`; that would
        remove real TLS security. Eswatini SLAS — same network-timeout
        pattern already documented for Sierra Leone's MTHE (DNS resolves,
        every TCP connection times out).
      - **Real bugs found and fixed by live/fixture testing before this
        was reported as done**: India ICCR's page has two `<h1>` elements
        (a generic Drupal page-title chrome one, and the real content
        heading nested inside `.field--name-body`) — the naive
        `select_one("h1")` silently picked the wrong one; WMI and Ireland
        have *no* usable `<h1>` at all (page-builder/custom-theme pages) —
        both original tests passed anyway because they never asserted on
        the actual title text, silently masking a fallback-only result.
        Added a `title_tag_separator` fallback (extract from `<title>`,
        split on a separator) for exactly this case, fixed both adapters,
        and added title assertions to the tests so this class of bug
        can't hide again.
      - **Researched, not implemented**: 14 more countries have a
        credible official candidate classified `READY_FOR_AUTOMATION` or
        `REQUIRES_CURATED_SOURCE` in `docs/COUNTRY_PROVIDER_REGISTRY.md`
        (Japan, Netherlands, France, Italy, Portugal, Belgium, Spain,
        Australia, Austria, South Africa, Morocco, Greece, Wales, Canada).
        Italy, Greece, South Africa are flagged as the strongest next
        candidates (official government domains, single-flagship shape or
        an existing reusable pattern).
      - **No reliable source found**: Denmark (no single confidently-
        identified awarding body in this pass — needs a dedicated
        follow-up search, likely under `ufm.dk`), UAE (predominantly funds
        outbound Emirati students, not inbound international applicants,
        at the national-government level).
      - **Blocked, not pursued**: Cyprus — `gov.cy` is behind an active
        Azure WAF JavaScript bot-challenge; per this initiative's explicit
        rule against bypassing anti-bot protections, this was not
        attempted further.
      - Country names normalized per the request (Eswatini, never
        Swaziland) — enforced directly in adapter code (`country =
        "Eswatini"`), not extracted from page text, so it can't drift.
      - Verified: 25 new tests
        (`tests/test_national_scholarship_programs.py`, additions to
        `tests/test_embassy_announcements.py`), one existing test updated
        for the new source count
        (`test_opportunity_import.py::test_source_seeding_is_idempotent`,
        13 → 19 sources); full backend suite **506/506**.
      - **Not committed** — left for explicit review/approval, per this
        increment's instructions.
- [x] **(2026-08-23, follow-up)** Implemented the three next-recommended
      candidates from `docs/COUNTRY_PROVIDER_REGISTRY.md`: Italy (MAECI),
      Greece (IKY), South Africa (NRF) — 3 more sources, 22 total. See
      `docs/AUTHORITATIVE_SOURCES.md` #19-#21.
      - **Live-verified 2026-08-23**: Italy (deadline `null` — the real
        call-status page states the 2025-2026 call is closed with no new
        date yet) and Greece (deadline `null` — the real page's text is
        informational, referencing an old 2017-2018 cycle, no current
        call). Both real syncs against the real sites created a real
        opportunity.
      - **Implemented, live-blocked, not falsely claimed working**: South
        Africa NRF — the same failure mode as India ICCR above (a real,
        reproducible `SSLCertVerificationError: unable to get local
        issuer certificate` through this backend's actual HTTP path,
        while `curl` succeeds) — confirmed by two separate attempts
        (the first surfaced as a TLS handshake timeout, the retry
        reproduced the certificate error consistently, confirming one
        underlying cause rather than two). Not worked around with
        `verify=False`.
      - **New architecture, not just new adapters**: Italy's overview
        page (`esteri.it`) and its deadline/call-status page
        (`studyinitaly.esteri.it`) are on two different hosts - the first
        source in this registry that needed it - so
        `_SingleProgramSource` gained an overridable `_deadline_base_url()`
        method (defaults to the same host, matching every existing
        source's behavior unchanged).
      - **Deliberate non-extraction, not a gap**: South Africa NRF's
        `deadline_keywords` is intentionally empty - the real page
        publishes a table of distinct closing dates per study level and
        sub-programme, and a generic keyword-anchored extractor would
        have picked one row and mislabeled it as *the* deadline. Locked
        in with a dedicated test
        (`test_south_africa_nrf_never_attempts_deadline_extraction`).
      - Verified: 14 new tests; one existing test updated for the new
        source count (19 → 22 sources); full backend suite **511/511**
        (one unrelated, unrepeatable flaky failure was observed during an
        abnormally slow ~4.5-hour run under heavy concurrent background
        load in this environment — `test_observability_route.py::
        test_enforce_log_retention_removes_expired` — reproduced as
        passing cleanly in isolation and in a subsequent clean full-suite
        re-run; not a real regression, noted honestly rather than
        silently ignored).
      - **Not committed** — left for explicit review/approval.
- [!] Smoke-test the `mthe_sierra_leone` scraper
      (`app/services/embassy_announcements.py::SierraLeoneMTHESource`)
      against the real `mthe.gov.sl` site. **Blocked, more precisely
      diagnosed 2026-08-23:** `nslookup www.mthe.gov.sl` resolves cleanly
      to `38.145.202.15` (DNS is fine), but every TCP connection attempt
      — port 80, port 443, and even raw ICMP ping — times out with no
      response at all (not a refusal/RST, an actual timeout; `curl -v`
      confirms "Connection timed out" on both ports). That pattern
      (DNS resolves, all TCP silently times out) points to network-level
      filtering/blackholing somewhere between this environment and that
      host, not an HTTP-level or application-level block - and not
      something a different request pattern, header, or retry strategy
      can work around. Researched for an official alternative (RSS,
      API, structured feed, alternative government domain): none found;
      the Ministry's only other known public presence is a Facebook page,
      which is not a legitimate substitute (would need Graph API
      app-review/permissions this project doesn't have, and scraping it
      directly would violate Facebook's terms - not attempted). The
      adapter is implemented and unit-tested against a clearly-labeled
      synthetic fixture, not real captured HTML — do not mark this done
      from that alone; re-test from an environment that can actually
      reach this host. See `docs/AUTHORITATIVE_SOURCES.md` #12.
      MTHE LIVE SOURCE STATUS: BLOCKED / NOT VERIFIED.
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

- [!] **(Corrected 2026-08-23 — the previous "old bundle ID" note above was
      stale; do not act on it as written.)** Direct inspection of every
      config file found `com.scholarsphere.app` used **consistently**:
      `android/app/build.gradle` (`applicationId`/`namespace`),
      `android/app/google-services.json` (`package_name`, last updated in
      commit `cef19ec`), `ios/Runner.xcodeproj/project.pbxproj`
      (`PRODUCT_BUNDLE_IDENTIFIER`), and `lib/firebase_options.dart`
      (`iosBundleId`, plus matching `appId`s for web/android/ios/macos, all
      under Firebase project `scholarsphere-d44f5`). No bundle-ID mismatch
      exists in the repository as committed. `firebase_options.dart` could
      only have been generated by a successful `flutterfire configure`
      run against a console project that already had these apps
      registered under this identifier — so the console-side
      re-registration this note used to describe appears to have already
      happened, just never reflected here.
      **What's actually still missing, found by direct inspection:**
      (1) `ios/Runner/GoogleService-Info.plist` does not exist anywhere in
      the iOS project — never added/committed, despite `firebase_options.dart`
      having a full iOS config block; (2) `ios/Runner/Info.plist` has no
      `CFBundleURLSchemes`/reversed-client-ID entry, which
      `google_sign_in`'s native iOS flow needs for the OAuth redirect.
      Android needs no equivalent file changes, but Google Sign-In there
      also requires the OAuth client's SHA-1/SHA-256 certificate
      fingerprint to be registered in the Firebase/Google Cloud console
      against whichever keystore actually signs the build (currently the
      debug key — see the release-signing item below) - this cannot be
      checked from this environment (no local debug keystore has ever
      been generated here, and no console access). **Live Google Sign-In
      was not tested** (no device/emulator/live OAuth flow available in
      this environment) — do not mark this resolved from file inspection
      alone. See `docs/PRODUCTION_READINESS.md` for the full checklist.
- [!] Android/iOS/macOS release builds sign with the debug key, not a real
      release keystore. Blocked on the team's signing credentials.
- [x] **(2026-08-29)** `firebase-admin`'s transitive `uuid` dependency's
      moderate CVE (GHSA-w5hq-g745-h8pq, fixed at 11.1.1/12.0.1/13.0.1
      depending on major line) is resolved — `functions/node_modules/uuid`
      is now `14.0.1`, well past every fixed threshold, and
      `npm audit --json` in `functions/` reports zero vulnerabilities at
      any severity (checked directly, not just this line's stale claim).
      No code change was needed; this note was simply never updated after
      a `firebase-admin` bump pulled in a patched `uuid` transitively. See
      `Changelog.md`.
- [ ] `storage.rules`'s new provider-document rules have been reasoned
      about but never deployed and exercised against a real Firebase
      Storage bucket in any environment this project has had access to.
- [!] **(2026-08-29)** GitHub reported 11 Dependabot alerts (3 high, 4
      moderate, 4 low) on the default branch when this session's previous
      push landed. **Could not be read directly** — this environment has
      no `gh` CLI, the GitHub MCP server has no Dependabot-alerts tool, and
      the Security/Dependabot tab needs authenticated repo access
      `WebFetch` can't reach; ask a maintainer to export the alert list
      (Security → Dependabot alerts) if exact CVE IDs are needed. Instead,
      every dependency manifest in the repo was audited directly against
      public advisory databases: `pip-audit` (backend, `requirements.txt`)
      **0 findings**; `npm audit --json` including dev deps (`functions/`)
      **0 findings** (also disproves this file's own now-corrected `uuid`
      CVE note above); an OSV.dev batch query (ecosystem `Pub`, confirmed
      correct against OSV's own ecosystem list) over all 73 pub.dev-hosted
      packages in `pubspec.lock` **0 findings**; the Android Gradle files
      declare no explicit dependency versions (delegated entirely to the
      Flutter Gradle plugin), so there is no separate Gradle dependency
      graph to audit; no `Podfile.lock` (iOS) or `Gemfile` exists. That
      leaves the three Docker base images as the only remaining ecosystem
      Dependabot tracks here — and the likely real source, since 11
      OS-package-level findings is a typical count for a stale Alpine/
      Debian base, not application code. Couldn't be scanned directly (no
      Docker daemon available in this environment, and downloading a
      third-party scanner like Trivy from GitHub releases is blocked by
      this session's repo-scoping proxy), but registry inspection
      (`registry-1.docker.io` — not proxy-restricted) confirmed
      `nginx:1.27-alpine` (root `Dockerfile`) was 3 stable-branch releases
      behind current (`1.30-alpine` now resolves to the same digest as
      nginx's own `stable-alpine` tag) — **bumped to `nginx:1.30-alpine`**.
      `python:3.12-slim` (`scholarsphere_backend/Dockerfile`) and
      `ghcr.io/cirruslabs/flutter:stable` (build stage) are both already
      floating "latest patch" tags that self-update on the next `docker
      build` without a text change, so left as-is. **Not verified against
      the actual alert list** — re-check the Security tab after this
      lands and after the next scheduled rebuild to confirm the count
      actually drops; do not mark this resolved from reasoning alone.

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
- [x] **(2026-08-23)** Production-readiness hardening follow-up. Corrected
      this file's baseline claim (was reported 482/482 mid-increment; the
      actual, already-committed state was 483/483 — see the prior entry)
      and continued from there rather than repeating finished work.
      - **Dependency security audit re-confirmed**: `pip_audit -r
        requirements.txt` — no known vulnerabilities (unchanged from the
        prior entry; re-run to confirm reproducibility, not a fluke).
      - **Startup configuration hardening.** Firebase Admin SDK
        initialization was lazy (first authenticated request only), so a
        bad/missing production credential would have surfaced as a
        confusing failure on the first real login rather than at deploy
        time. Added `app/main.py::ensure_firebase_ready_in_production`
        (called from the app's `lifespan`, a no-op outside
        `app_env=production`) that eagerly initializes Firebase at
        startup and fails with an actionable `RuntimeError` if it can't -
        whether the deployment uses `FIREBASE_CREDENTIALS_PATH` or
        Application Default Credentials. Also extended
        `reject_placeholder_infrastructure_credentials_in_production` in
        `app/core/config.py` to refuse startup if
        `FIREBASE_CREDENTIALS_PATH` is set but points at a file that
        doesn't exist. Files: `app/main.py`, `app/core/config.py`.
        Verified: 6 new tests
        (`tests/test_startup_validation.py`).
      - **`.env.example` rewritten** with every real setting the codebase
        reads (including the 5 new scraper sources, which were missing),
        each labeled by when it's actually required (local dev / testing
        / background jobs / Firebase / production / optional) rather than
        left as an undifferentiated flat list.
      - **Firebase bundle-ID finding corrected** — see the "Bugs and
        Issues" entry above for the full, evidence-based writeup. The
        previously-documented "old bundle ID" blocker does not match what
        the actual config files say; a different, more specific gap (a
        missing `GoogleService-Info.plist` and missing iOS URL scheme)
        was found by direct inspection instead. Live Google Sign-In was
        **not** tested (no device/emulator available) — not claimed as
        working.
      - **MTHE connectivity re-diagnosed precisely** — see the
        "Integration Tasks" entry above. DNS resolves; TCP times out on
        every port tried, including ICMP — a different, more specific
        finding than "connection refused." No official RSS/API/alternative
        source found on further research.
      - **Real defect found and fixed: SSRF-adjacent gap in the
        embassy-announcement adapter.** `_matching_article_urls`
        (`app/services/embassy_announcements.py`) filtered discovered
        links only by their visible text (does it mention "scholarship"?)
        with no check that the link's target host matched the source's
        own configured domain - a compromised or simply mischievous link
        on an otherwise-trusted page could have made this adapter fetch
        an arbitrary third-party HTTPS URL. Added
        `same_host_https_url` (`app/services/web_scraper_base.py`) and
        switched this adapter to use it; `absolute_https_url` (used
        elsewhere, where a different-host link is legitimate, e.g. an
        official application portal on its own domain) is unchanged.
        Regression test:
        `tests/test_scraper_resilience.py::test_discovered_links_to_a_different_host_are_never_followed`.
      - **Real Celery task-interface test added** (not just direct
        function calls): `sync_cscuk_scholarships.apply(...)` under
        `task_always_eager=True`, exercising the actual `@celery_app.task`
        binding machinery. Explicitly labeled in its own docstring as an
        eager/in-process test, not a real broker/worker test — a real
        Redis broker + worker + beat scheduler still could not be
        exercised in this environment (no Redis/Docker available) and
        remains a genuine, undone verification gap.
      - **Fixed a pre-existing test-isolation bug**, found while adding
        the above: `test_all_scheduled_task_names_resolve` only passed
        when run as part of the full suite, because it silently depended
        on another test file having already imported
        `app.tasks.notifications` as a side effect (which is what
        actually registers those two tasks into the shared `celery_app`
        singleton). Failed when run alone. Not a production bug — a real
        worker loads every module in `Celery(..., include=[...])` at
        startup — but a real test-determinism bug. Fixed by calling
        `celery_app.loader.import_default_modules()` explicitly in the
        test, which is exactly what a real worker does.
      - **Idempotency test added**: re-running `_run_source_sync` with the
        same `task_id` twice creates exactly one `OpportunitySyncHistory`
        row and does not duplicate the opportunity (relies on the
        existing `payload_hash`-based skip-if-unchanged path in
        `app/services/opportunity_import.py`, which was already correct -
        this closes a coverage gap, not a bug).
      - **Cross-cutting scraper resilience tests added**
        (`tests/test_scraper_resilience.py`): malformed HTML, a simulated
        full site-layout change (every expected selector gone), and a
        missing-title fallback — all confirmed to degrade to a safe
        empty/placeholder result rather than raising, on the first try
        (the existing defensive coding was already correct; this adds the
        coverage that proves it).
      - Fulbright: re-confirmed unsupported, no new official source found
        this pass; the existing declined-sources documentation already
        satisfies "designed so it can be added later without
        architectural changes" (a new adapter class + registry entry is
        all that would be needed - no framework change).
      - Full backend suite: **494/494** (`pytest -q`).
      - **Not committed** — left for explicit review/approval per this
        increment's instructions, unlike the previous increment where
        committing and pushing was explicitly requested.
- [x] **(2026-08-29)** Differential Storage access for provider-granted
      applicant documents — the Backend Tasks gap immediately above this
      line is now closed. Two new routes:
      `GET /applicant-documents/{id}/download-url` (owner or a granted
      provider gets a 15-minute v4 signed Storage URL via the Admin SDK;
      everyone else 404; signing failure honestly 503s, never a fabricated
      URL) and `GET /applicant-documents/shared-with-me` (provider-facing
      listing, `storage_path` deliberately omitted). New
      `app/services/document_storage.py` wraps the Admin SDK signing call
      behind a monkeypatchable function, matching
      `app/services/firebase_users.py`'s pattern. Added
      `Settings.firebase_storage_bucket` (previously unset, so signing was
      never actually possible before — `initialize_firebase()` now passes
      `storageBucket`). `storage.rules` and the `grant_provider_access`
      docstring updated to describe the new arrangement instead of the old
      "not-yet-built follow-up" note; the rule itself is unchanged
      (deliberately still owner-only — the backend stays the one auditable
      choke point for third-party access). See `Changelog.md` for full
      detail. Verified: 7 new tests
      (`tests/test_applicant_documents_route.py`); full backend suite
      **518/518** (`pytest -q`). Flutter not touched — the provider-side
      "download a shared document" UI is a separate, not-yet-built
      follow-up.
- [x] **(2026-08-29)** Global scholarship-discovery master-prompt initiative
      — audited against the existing discovery/verification pipeline
      first (per the prompt's own Phase 1/2 instructions), found it
      already implements the large majority of the spec (official vs.
      application-URL separation, hard verification gate, deduplication,
      confidence scoring, change history, scheduled Celery-beat loop with
      bounded retries, a 22-country research inventory). Picked three
      concrete, testable gaps rather than attempting all 60 sections or
      dozens of countries at once (would require skipping this project's
      own live-verification rigor):
      1. **Link-health monitoring** (spec gap — deadline expiry existed,
         periodic application-link reachability did not). New
         `ExternalOpportunity.link_checked_at` column (migration
         `20260914_32`), `app/services/link_health.py`, and
         `app.tasks.opportunity_sync.check_link_health` (daily, bounded to
         100 published+verified opportunities per run, oldest-checked
         first). An unreachable link demotes `verified` →
         `reverification_required` and logs a `VerificationHistory` entry
         and flips `VerificationReview.application_link_checked = False`
         — mirrors `detect_expired_opportunities`'s existing pattern
         exactly, never deletes the opportunity or its link. 6 new tests.
      2. **Netherlands** (Nuffic NL Scholarship) — the top
         `READY_FOR_AUTOMATION` candidate in
         `docs/COUNTRY_PROVIDER_REGISTRY.md`. Live-verified 2026-08-29
         through this backend's actual httpx path (not just `curl`, per
         this project's own India-ICCR/South-Africa-NRF lesson about TLS
         chain differences between the two): 200, real HTML,
         `<h1 class="page-header__title">NL Scholarship</h1>`.
         `hollandscholarship.nl` (the program's old public name/domain)
         301-redirects to `studyinnl.org/finances/nl-scholarship`,
         confirmed current by the page's own `<title>`. Two honesty
         choices forced by the page's own text, not a formatting quirk:
         `funding_type = "partial_funding"` (page states outright "not a
         full-tuition scholarship", fixed €5,000) and
         `deadline_keywords = ()` (page says closing dates are set by each
         of ~30 participating institutions individually, same reasoning as
         South Africa NRF). 3 new tests against a real fixture; source
         count 22 → 23. Docs updated:
         `docs/AUTHORITATIVE_SOURCES.md` #22, `docs/
         COUNTRY_PROVIDER_REGISTRY.md` (moved out of "researched, not
         implemented", coverage summary and recommended-next-candidates
         list updated).
      3. **Admin discovery dashboard** — spec's admin-visibility gap
         (`GET /sources` and `GET /verification-summary` already existed;
         no source/country/link-health aggregate view did). New
         `GET /external-opportunities/discovery-summary`
         (`DiscoverySummary` schema): source totals/active/recent-errors,
         opportunity totals by publication status, duplicate-review
         backlog, opportunities-by-country breakdown, and
         never-link-checked/broken-links counts from the task above. 4 new
         tests. **Flutter**: added the data-layer piece only
         (`LiveDiscoverySummary` + `ApiVerificationRepository
         .getDiscoverySummary()` in `api_verification_repository.dart`,
         mirroring `getSummary()`'s exact existing pattern) — did **not**
         wire this into `administration_dashboard_screen.dart` or
         `verification_officer_dashboard_screen.dart` (884–1151 lines
         each): this environment has no Flutter SDK to compile or run
         against, and blind edits to files that size with no way to catch
         a mistake would be irresponsible. UI wiring is a real, scoped
         follow-up for an environment that can run `flutter analyze`/
         `flutter test`.
      - Verified: 13 new backend tests; full backend suite **531/531**
        (`pytest -q`). Flutter: data-layer addition only, **not compiled
        or run** — no Flutter SDK available in this environment; flag any
        issue found when it's next built.
      - **Genuinely still open** (not attempted, listed honestly rather
        than silently dropped): the other ~10 `READY_FOR_AUTOMATION`
        countries in the registry (Spain, Australia, Wales, Japan, ...);
        every country outside that inventory the master prompt named
        (most of Asia, all of South America, the Middle East); true
        live-search-driven multilingual discovery (this system's proven
        pattern is one hand-vetted adapter per researched source, not a
        search-engine-query crawler — recommended to keep, not replace,
        given real anti-bot/ToS walls already hit); a manual review queue
        UI beyond the existing verification queue; and the admin
        dashboard's actual UI wiring, per the Flutter caveat above.

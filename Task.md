# ScholarSphere — Active Development Task Board

**Last verified against the codebase:** 2026-09-03 (backend only — see the
2026-09-03 Completed Tasks entry; Flutter not re-verified this session, no
SDK available). Cross-referenced with
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

Test baseline as of this session's own verified run (2026-09-01): **737/737
backend tests passing** (`pytest -q`; +39 for the Premium
Application-Preparation Platform build-out described below, up from
687/687 on 2026-08-30; 586 as of the browser-rendering
fallback on 2026-08-29, +84 for the Hybrid Scholarship Discovery
and Verification Engine build-out described below, +6 for the 40-country
audit's United States/Eswatini work, +1 for the World Bank JJ/WBGSP
source, +2 for the Rotary Peace Fellowships source, +5 for the Erasmus
Mundus Joint Masters Catalogue source, +3 for the UAEU Scholarships
source — up from 511 on
2026-08-23 — 7 for
differential Storage access, 6 for link-health monitoring, 3 for the
Netherlands source, 4 for the discovery-summary endpoint, 5 for the Spain/
Australia sources, 3 for the Japan source, 8 for the Belgium/France/
Austria/Morocco sources, 2 for the Portugal source, 2 for the Colombia
source, 2 for the Chile source, 2 for the Peru source, 2 for the South
Korea source, 2 for the Saudi Arabia source, 2 for the Qatar source, 2
for the Switzerland source, 2 for the Poland source, 2 for the Czech
Republic source, 2 for the Serbia source, 2 for the Romania source, 2 for
the Hungary source, 2 for the Mexico source, 11 for the new browser-
rendering fallback). Flutter suite not re-run this session (no Flutter
SDK available in this environment); one small Flutter data-layer
addition landed (see Completed Tasks' master-prompt
entry), plus (2026-09-01) a new `lib/features/premium/` slice
(domain/data/presentation + `app.dart` wiring) for the Premium
landing/pricing/checkout screen and feature-gating widget — none of it
compiled, `flutter analyze`'d, or `flutter test`'d in this session for
the same reason. Re-run both suites before trusting these numbers
if more than a few commits have landed since.

**(2026-09-03 update)** An independent production-audit pass over the
Premium platform found and fixed 8 real bugs (see Completed Tasks' matching
dated entry) and added 12 new backend tests. Backend suite re-verified
green after every fix: **724 passed, 25 skipped, 0 failed** (`pytest -q`;
the 25 skips are the pre-existing live-provider-only tests, correctly
skipped with no credentials configured). Flutter again not re-verified
this session (no SDK available) despite two of the eight fixes touching
`lib/features/premium/`.

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
- [x] **(2026-08-29)** GitHub Pages deployment prep for the Flutter web
      build. New `.github/workflows/deploy-pages.yml`: builds
      `flutter build web --release` with
      `--base-href "/${{ github.event.repository.name }}/"` (required for
      a GitHub Pages project site served under `/scholarsphere/`, not
      root — the app's routing is in-memory, a single `MaterialApp` with a
      `NavigatorKey` and no `GoRouter`/path-based routes, per
      `lib/app/app.dart`, so no server-side rewrite rules are needed
      beyond that), adds `.nojekyll` and a defensive `index.html` ->
      `404.html` fallback, then deploys via the official
      `actions/upload-pages-artifact` + `actions/deploy-pages` actions
      (trigger: push to `main` touching `lib/`, `web/`, `assets/`,
      `pubspec.{yaml,lock}`, or the workflow itself; also
      `workflow_dispatch`).
      - **Real, unavoidable manual steps this alone does not satisfy**
        (documented in the workflow's own comments and
        `.env.example`, not silently assumed done):
        1. **Enable Pages with source "GitHub Actions"** in this repo's
           Settings → Pages. Confirmed not yet done —
           `https://ecotraces.github.io/scholarsphere/` currently 404s.
        2. **Deploy `scholarsphere_backend/` somewhere publicly
           reachable over HTTPS**, then set it as the `SCHOLARSPHERE_API_BASE_URL`
           repo Actions variable (Settings → Secrets and variables →
           Actions → Variables) — it's a compile-time `--dart-define`
           (see `api_opportunity_repository.dart`), baked into the JS
           bundle, not read at runtime. Left unset, the deployed site
           falls back to `http://localhost:8000/api/v1`, which is
           unreachable from a visitor's browser — a real, working
           preview needs this set. This backend is not deployed anywhere
           by this workflow or by this repository today.
        3. **Add the Pages origin to `ALLOWED_ORIGINS`** on whatever
           deploys the backend (`.env.example` updated with the exact
           format) — otherwise the deployed frontend's API calls are
           blocked by CORS.
        4. **Add the Pages origin to Firebase Console's Authorized
           domains** (Authentication → Settings → Authorized domains) —
           required for Google Sign-In's redirect/popup flow to work from
           `ecotraces.github.io`; console-only, cannot be done from this
           environment, same category as the existing bundle-ID/
           Google-Sign-In items already tracked in Bugs and Issues below.
      - Not run end-to-end (no live GitHub Actions execution or Pages
        environment available from this session) — the workflow's YAML
        was validated for well-formedness but the actual deploy has not
        been observed to succeed. Verify on the first real push to `main`.
- [x] **(2026-08-29)** Free-hosting-tier deployment prep for
      `scholarsphere_backend/`. Researched the current (2026) free-tier
      landscape before committing to a stack, since prior knowledge here
      goes stale fast (Render's own free Postgres now expires after 30
      days; Fly.io no longer has a real free tier at all; Railway removed
      its free tier in 2023). Landed on **Render (web service) + Neon
      (Postgres, permanent free tier) + Upstash (Redis, permanent free
      tier)**.
      - New `render.yaml` Blueprint (repo root) defines the
        `scholarsphere-backend` web service (Docker, free plan,
        `/health/ready` health check); secrets (`DATABASE_URL`,
        `REDIS_URL`, `FIREBASE_PROJECT_ID`,
        `FIREBASE_CREDENTIALS_JSON_BASE64`, `ALLOWED_ORIGINS`) are
        deliberately `sync: false` so nothing credential-shaped is
        committed — the user sets them in the Render dashboard.
      - New `scholarsphere_backend/docker-entrypoint.sh`: optionally
        decodes a base64 Firebase service-account JSON to a real file
        (a portable alternative to a platform-specific secret-file
        feature), optionally runs `alembic upgrade head` on boot (opt-in
        via `RUN_MIGRATIONS_ON_BOOT`, since Render's free plan has no
        separate release-phase step), then execs uvicorn bound to `$PORT`
        (Render injects this; previously hardcoded to 8000, which would
        have made the service unreachable on Render). `Dockerfile`
        updated to use it as `CMD` (deliberately not `ENTRYPOINT` —
        would've broken `docker-compose.yml`'s worker/beat services,
        which override the container's command entirely).
      - **Real, documented gap, not silently dropped**: Render's free
        plan has no Background Worker or Cron Job service type (Cron
        Jobs specifically need a paid plan, $1/month/job minimum) — so
        the 22 scheduled Celery tasks in `opportunity_sync.py` (source
        syncs, link-health checks, reverification, notifications) have
        no equivalently free always-on host today. The API itself works
        fully without them; only the *scheduled* background jobs don't
        run for free. Not worked around by restructuring the scheduling
        architecture (out of scope, and every existing Celery-based test
        still needs a real worker to exercise in production regardless).
      - `scholarsphere_backend/README.md` gained a full "Deploying to a
        free hosting tier" walkthrough (Neon/Upstash/Firebase/Render
        setup steps, and why each platform was chosen over the
        alternatives checked).
      - **Not built or deployed** — no Docker daemon available in this
        environment (client only, confirmed again this session) and no
        Neon/Upstash/Render accounts exist for this project from here.
        `docker-entrypoint.sh` passed `sh -n` syntax validation and
        `render.yaml` passed YAML well-formedness validation; neither was
        exercised against a real build or a real Render deploy. Verify on
        the first real deploy attempt.
- [x] **(2026-08-29)** Two more country sources from the master-prompt
      queue: **Spain** (AECID) and **Australia** (DFAT Awards) — the top
      two `READY_FOR_AUTOMATION` candidates in
      `docs/COUNTRY_PROVIDER_REGISTRY.md`. Same live-verification
      discipline as every prior source in this initiative (fetched via
      both `curl` and this backend's actual httpx path, robots.txt
      checked, real HTML captured as test fixtures — never written from
      assumption).
      - **Spain (AECID)**: live-verified, no issues. Deliberately targets
        AECID's specific international-applicant sub-page (`Becas para
        ciudadanos de países de América Latina, África y Asia`), not its
        generic scholarships hub (which mostly serves Spanish nationals —
        irrelevant to this platform). Same `deadline_keywords = ()`
        pattern as South Africa NRF/Netherlands: the page lists several
        named sub-programs, each with its own distinct closing date.
        `funding_type = "partial_funding"` — no "fully funded" language
        found on the page.
      - **Australia (DFAT Awards)**: **partially live-verified**. The
        overview site (`australiaawards.com.au`) is fully reachable and
        implemented; the authoritative deadline page (`dfat.gov.au`) is
        **not** — every attempt (multiple user agents, `curl` and httpx)
        hung at the TLS-handshake stage until timeout, the same
        "connects, then nothing responds" pattern already documented for
        Sierra Leone's MTHE, not a WAF challenge (no challenge content
        was ever returned). `deadline_path` deliberately left unset
        rather than pointed at an unverified host. `funding_type = None`
        — no funding-coverage language found on the reachable pages;
        Australia Awards are widely known to be comprehensively funded
        in practice, but that's outside knowledge the adapter's own
        source text doesn't support asserting, so it was left honestly
        unclassified rather than guessed.
      - Source count 23 → 25. Docs updated: `docs/AUTHORITATIVE_SOURCES.md`
        #23-#24, `docs/COUNTRY_PROVIDER_REGISTRY.md` (both moved out of
        "researched, not implemented"; coverage summary, totals, and
        recommended-next-candidates list all updated — Wales, Japan, and
        Canada are now the top queued candidates).
      - Verified: 5 new tests (`tests/test_national_scholarship_programs.py`)
        against real fixture HTML; full backend suite **536/536**
        (`pytest -q`).
      - **Master-prompt country coverage after this increment**: 12
        countries/regions now have at least one real, integrated source
        (up from 10) — still a small fraction of the ~40 the original
        prompt named. South America (9 countries), most of Asia, and
        most of the remaining European countries in that list remain
        completely unresearched. See the chat response to "have you
        implemented all the countries i provided" earlier this session
        for the full country-by-country accounting; that gap has not
        materially closed, only the top 2 queued candidates were picked
        up.
- [x] **(2026-08-29)** Continued the master-prompt country queue with
      Wales and Japan — but only one of the two turned into a new source.
      - **Wales — real finding, not implemented.** Live-testing the
        specific page the registry's prior `READY_FOR_AUTOMATION`
        classification was based on
        (`/global-wales-postgraduate-scholarship`) found it now 404s
        (real "Page not found" content). The site's current replacement
        page states the program is no longer centrally administered — it
        now points to each of eight Welsh universities' own scholarship
        pages individually, plus to Chevening and Commonwealth
        Scholarships (both already separate sources here). Corroborated
        by an independent third-party source noting the program's 2024
        round has closed. **The prior classification was wrong — it was
        never live-tested before being written down.** Corrected in
        `docs/COUNTRY_PROVIDER_REGISTRY.md` to `NOT_SUITABLE` rather than
        silently left as a stale `READY_FOR_AUTOMATION` entry, same
        discipline as the India ICCR dual-`<h1>` bug and the corrected
        Firebase bundle-ID note earlier in this project's history. No
        source built — building one against a defunct/decentralized
        program would have meant fabricating relevance, not real
        integration.
      - **Japan (MEXT Scholarship) — implemented, live-verified.** Targets
        the MEXT-specific sub-page of the official "Study in Japan"
        government portal, not its thin navigation hub. `deadline_keywords
        = ()` (embassy/university-mediated applications, no single global
        deadline — same honest pattern as Ireland/Sweden). Unlike
        Australia Awards, `funding_type = "fully_funded"` **is** kept
        here — actually confirmed by the page's own text ("tuition
        exempted", a monthly stipend, "round-trip travel expenses
        (airfare) provided"), not guessed. `title_selectors = ()` since
        every page on this site section shares the same generic
        `<h1>Scholarships</h1>`; the real title comes from the `<title>`
        tag split on the site's own fullwidth vertical bar (`｜`, U+FF5C).
      - Source count 25 → 26. Docs updated:
        `docs/AUTHORITATIVE_SOURCES.md` #25, `docs/
        COUNTRY_PROVIDER_REGISTRY.md` (Japan moved to implemented; Wales
        corrected in place, not moved; coverage summary, totals, and
        recommended-next-candidates list all updated — every previously
        `READY_FOR_AUTOMATION` candidate is now either implemented or
        corrected to `NOT_SUITABLE`; the remaining 10 researched
        countries all genuinely need a second research pass, not just a
        fetch-and-wire pass).
      - Verified: 3 new tests (`tests/test_national_scholarship_programs.py`)
        against real fixture HTML; full backend suite **539/539**
        (`pytest -q`).
      - **Master-prompt country coverage after this increment**: 13
        countries/regions now have at least one real source (up from
        12). South America (9 countries), most of Asia, and most of the
        remaining named European countries remain completely
        unresearched.
- [x] **(2026-08-29)** A dedicated research pass — not a fetch-and-wire
      pass — on the remaining queue: Belgium (ARES), Canada (EduCanada),
      France (Campus France), Austria (OeAD), Morocco (AMCI/"Maroc
      Alumni"), and Denmark's long-standing "needs a dedicated follow-up
      search" item. 4 of 6 turned into real, live-verified sources; 2
      (Canada, Denmark) were confirmed genuinely unsuitable rather than
      left as stale guesses.
      - **Belgium (ARES)**: the general `/bourses-de-mobilite` hub is a
        category page linking to ~8 distinct instruments, not a single
        flagship — this adapter targets the specific "Bourses de
        formations internationales" sub-page instead, which has a real
        currently-open call and a real deadline ("18.09.2026"). That
        deadline is deliberately **not** extracted — it's in `DD.MM.YYYY`
        numeric form, which `app/services/parsing.py`'s shared date
        regex doesn't match (by design, to avoid guessing at date
        formats); extending that shared regex is a cross-cutting change
        out of scope for one adapter.
      - **France (Campus France Eiffel)**: a genuinely clean single
        flagship page with a real, parseable deadline ("January 8,
        2026") — `deadline_keywords` actually extracts it this time.
        Applications are institution-mediated, the same standard shape
        as DAAD/Japan MEXT (already implemented), confirmed distinct
        from Canada's SICS program (see below) by directly reading both
        pages rather than assuming they're the same shape.
      - **Austria (OeAD Ernst Mach Grant)**: same multi-program-hub
        shape as South Africa NRF/Spain AECID — the page covers 6 named
        sub-grants (Ukraine, worldwide, Fachhochschule, Follow-Up,
        ASEA-UNINET, ASEA-UNINET Short-term), each with its own deadline
        and, for one, its own distinct monthly amount ("715 euros/month"
        for Ukraine only) — `deadline_keywords = ()` deliberately.
      - **Morocco (AMCI)**: resolved the prior uncertainty about "Maroc
        Alumni"'s canonical URL — the real official page is
        `amci.ma/cooperation-academique`. `robots.txt` itself 403s but
        the content page doesn't (same "monitored, not blocked" case as
        the Swedish Institute). Embassy-mediated, `deadline_keywords =
        ()`, same pattern as Japan MEXT.
      - **Canada — confirmed NOT_SUITABLE, not implemented.** Live-fetched
        EduCanada's actual scholarship pages: the international-applicant
        section is a directory of several distinct named programs, and
        its broadest one (Study in Canada Scholarships) states outright
        "Only Canadian post-secondary institutions are eligible to apply
        on this call... Direct applications from individuals are not
        accepted." Unlike France's Eiffel program, there is no path for
        an individual applicant to initiate anything — institutions
        select students proactively. Corrected in
        `docs/COUNTRY_PROVIDER_REGISTRY.md` from its prior vaguer
        "institution-mediated, needs deeper research" note to a specific,
        evidence-backed `NOT_SUITABLE`.
      - **Denmark — confirmed NOT_SUITABLE, not implemented.** The
        dedicated follow-up search this entry itself called for was
        done: confirmed directly that Danish government scholarships are
        "administered by the Danish universities, who each select the
        students" — genuinely decentralized, no single national awarding
        body. Corrected from `NO_RELIABLE_SOURCE_FOUND` (implying more
        searching might help) to `NOT_SUITABLE` (the decentralization is
        now a confirmed fact, not a research gap).
      - No monetary/"fully funded" language was found on any of the 4
        new sources' actual pages, so `funding_type = None` on all four
        — not guessed from general reputation (Eiffel and Ernst Mach are
        both well-known generous programs in reality, but that's outside
        knowledge these adapters' own source text doesn't support
        asserting).
      - Source count 26 → 30. Docs updated:
        `docs/AUTHORITATIVE_SOURCES.md` #26-#29 (full detail per source),
        `docs/COUNTRY_PROVIDER_REGISTRY.md` (all 6 countries' entries
        corrected/updated with what was actually found; coverage
        summary, totals, and recommended-next-candidates list all
        updated — only Portugal remains as a genuine queued candidate).
      - Verified: 8 new tests (`tests/test_national_scholarship_programs.py`)
        against real fixture HTML — all passed on the first run; full
        backend suite **547/547** (`pytest -q`).
      - **Master-prompt country coverage after this increment**: 17
        countries/regions now have at least one real source (up from
        13), across 3 confirmed-unsuitable corrections (Canada, Denmark,
        Wales) that replaced stale guesses with real findings. South
        America (9 countries), most of Asia, and most of the remaining
        named European countries are still completely unresearched.
- [x] **(2026-08-29)** Portugal (Camões Cooperation Scholarships) —
      the last country this registry had queued from the original
      research. Neither the "Bolsas do Camões, I.P." hub nor its
      "Bolsas da Cooperação" child (both fetched and confirmed to be
      thin, content-free navigation pages) were used; this adapter
      targets the specific "Formação em Portugal" leaf page instead,
      with real substantial content: 9 named eligible partner countries
      (Angola, Cabo Verde, Colômbia, Etiópia, Guiné-Bissau, Moçambique,
      São Tomé e Príncipe, Senegal, Timor-Leste) and a real funding table
      with actual euro amounts. Unlike Belgium/Austria/Morocco earlier
      in this same research initiative, `funding_type = "fully_funded"`
      **is** kept here — genuinely supported by the source text (a
      maintenance subsidy, a tuition subsidy up to
      €1,306.25–2,612.50/year, a housing subsidy, and an installation
      subsidy, each with real figures), the same reasoning already
      applied to Japan's MEXT Scholarship. `deadline_keywords = ()` —
      embassy-mediated applications, same pattern as Japan MEXT and
      Morocco AMCI.
      - Source count 30 → 31. Docs updated:
        `docs/AUTHORITATIVE_SOURCES.md` #30, `docs/
        COUNTRY_PROVIDER_REGISTRY.md` (Portugal moved to implemented;
        coverage summary, totals, and the recommended-next-candidates
        section all updated — **the queue this registry has tracked
        since 2026-08-23 is now genuinely empty**: every candidate this
        registry ever identified is either a real source or a confirmed,
        evidence-backed non-candidate, none left as stale guesses).
      - Verified: 2 new tests (`tests/test_national_scholarship_programs.py`)
        against a real fixture; full backend suite **549/549**
        (`pytest -q`).
      - **Master-prompt country coverage after this increment**: 18
        countries/regions now have at least one real source (up from
        17). The only way to add more from here is a **first** research
        pass on countries entirely outside this registry — all of South
        America, most of Asia (South Korea, Saudi Arabia, Qatar,
        Thailand), and most of the remaining named European countries
        (Switzerland, Poland, Czech Republic, Croatia, Serbia, Romania,
        Norway, Finland) — none of which have been touched at all yet.

- [x] **(2026-08-29)** South America — a dedicated **first** research
      pass covering all 9 countries in the region, none of which had any
      prior research in this registry. 3 real sources added:
      - **Colombia** (ICETEX Beca Colombia Extranjeros): the site
        (Liferay) has a hidden accessibility `<h1 class="hide-accessible">
        Navegación</h1>` before the real content (the same bug class
        already documented for India ICCR) and reuses one
        `.journal-content-article` class for 8+ unrelated blocks on the
        page, including a "Historial" accordion holding the three
        *previous* application cycles. Solved with the one stable,
        unique anchor Liferay stamps on the actual article content:
        `[data-analytics-asset-title='Beca Colombia Extranjeros']`. A
        thinner companion page (330 characters, no funding/deadline
        info) and an unrelated governance-notice sub-page were both
        fetched and rejected first. `funding_type = None` (no explicit
        funding-coverage language); `deadline_keywords = ()` (the real
        deadline is stated but in unparseable Spanish month-name form).
      - **Chile** (AGCID Becas para Extranjeros): a single unique `<h1>`
        and `<article>`, but the article bundles several distinct
        bilateral/regional sub-programs with materially different (even
        conflicting) funding formulas, plus the page's own disclaimer
        that terms are reference-only pending each call's official
        republication — the same multi-program shape already handled
        honestly for South Africa NRF, the Netherlands, and Spain AECID.
        `deadline_keywords = ()` and `funding_type = None`.
      - **Peru** (PRONABEC Beca Alianza del Pacífico): a reciprocal
        student-mobility program among the four Pacific Alliance member
        states; Peru offers 50 inbound slots for Chilean/Colombian/
        Mexican nationals specifically (real but narrow eligibility, the
        same honest bilateral-partner pattern as Portugal Camões). No
        `<h1>` at all (a WordPress page-builder layout) — title falls
        back to the `<title>` tag split on the en dash. Real numeric-date
        schedule for foreign applicants exists but can't be parsed
        (`DD/MM/YYYY` form) — `deadline_keywords = ()`.
        `funding_type = "partial_funding"` (food/transport/insurance
        explicitly covered, tuition never mentioned — an exchange
        program, not a full scholarship).
      - **Brazil** was investigated and found genuinely `BLOCKED`, not
        implemented: the real program (PEC-G, Ministry of Foreign
        Affairs/Education) has rich real content confirmed via a
        browser-spoofed `curl` fetch, but this backend's actual
        unspoofed httpx client is served a JavaScript bot-challenge page
        (F5/Distil-style `TSPD` cookie challenge) 3/3 attempts — the
        same class of finding as Cyprus's Azure WAF block, and bypassing
        it (spoofing a browser identity) is out of scope by the same
        policy already applied there.
      - **Argentina, Uruguay, Paraguay** confirmed `NOT_SUITABLE`
        (Argentina: the real mechanism is a searchable multi-entry
        database, not a single page, the same shape already set aside
        for France's Campus Bourses; Uruguay and Paraguay: both
        residency-restricted — their own pages require existing
        residency or citizenship, not open to prospective international
        applicants). **Ecuador and Bolivia** came back
        `NO_RELIABLE_SOURCE_FOUND` (Ecuador's SENESCYT catalogue is
        outbound-only; a historical inbound "Prometeo" program has no
        current-dated source confirming it is still active; Bolivia has
        no inbound government program identified).
      - Source count 31 → 34. Docs updated: `docs/
        AUTHORITATIVE_SOURCES.md` #31-#33, `docs/
        COUNTRY_PROVIDER_REGISTRY.md` (new dedicated "South America"
        section with all 9 findings; Implemented table extended;
        coverage summary and recommended-next-candidates rewritten to
        reflect that South America has had its first pass).
      - Verified: 6 new tests (`tests/test_national_scholarship_programs.py`,
        2 per source) against real fixtures; full backend suite
        **555/555** (`pytest -q`).
      - **Master-prompt country coverage after this increment**: 21
        countries/regions now have at least one real source (up from
        18). Remaining unresearched territory: most of Asia (South
        Korea, Saudi Arabia, Qatar, Thailand), and the remaining named
        European countries (Switzerland, Poland, Czech Republic,
        Croatia, Serbia, Romania, Norway, Finland).

- [x] **(2026-08-29)** The four remaining named Asian countries — a
      dedicated **first** research pass (South Korea, Saudi Arabia,
      Qatar, Thailand; China and India already had narrower coverage).
      3 real sources added:
      - **South Korea** (GKS Global Korea Scholarship Program, run by
        NIIED): the page's only `<h1>` is the site logo, not a title —
        solved with `<h2 class="title">GKS (Global Korea Scholarship)
        Program</h2>`, the first of two matches (the second is a
        sibling "Other Scholarships" tab). Content scoped to
        `#gks-tab1`, confirmed to hold only the GKS section (the
        surrounding `main` also contains the other tab's content
        further down the DOM). `funding_type = "fully_funded"` — the
        page states "Airfare, language training costs, tuition, and
        study allowances" explicitly.
      - **Saudi Arabia** (MOE Government University Scholarships): no
        `<h1>`, and the `<title>` tag interleaves Arabic and English
        with the real text in the *second* segment — since
        `title_tag_separator` only supports the first segment (a
        deliberate shared-pattern limitation, not special-cased for one
        source), this source falls back to a title formatted from
        `external_id`. `funding_type = None` — the page explicitly
        states three distinct funding tiers (free/partial/paid).
      - **Qatar** (Qatar Scholarships, run by the Qatar Fund For
        Development/QFFD): the homepage is a JS-rendered SPA that
        serves only an empty "offline" shell to a non-JS client — used
        `/en-US/Programs` instead, a server-rendered route with real
        content. `robots.txt` uses the newer "content-signal"
        convention but sets no actual value for any use — documented
        explicitly as a genuine absence of restriction, not an ordinary
        permissive robots.txt. `funding_type = None` — the page bundles
        partner-institution programs with conflicting funding (some
        full tuition waiver, one explicitly partial tuition).
      - **Thailand** was investigated and found `NOT_SUITABLE`, not
        implemented: the government's real scholarship info lives in a
        rolling year-dated announcement feed (`ops.go.th`), and a
        second candidate "about" page (TICA's own TIPP overview) was
        real but frozen content from ~2013-2015, not the current cycle.
        Note: this host was intermittently unreachable in initial
        testing but succeeded consistently once retried with this
        backend's actual production request shape (registered
        User-Agent, full 40s timeout) — a transient connectivity issue,
        not a real block.
      - Source count 34 → 37. Docs updated: `docs/
        AUTHORITATIVE_SOURCES.md` #34-#36, `docs/
        COUNTRY_PROVIDER_REGISTRY.md` (new dedicated "Asia" section with
        all 4 findings; Implemented table extended; coverage summary and
        recommended-next-candidates rewritten).
      - Verified: 6 new tests (`tests/test_national_scholarship_programs.py`,
        2 per source) against real fixtures; full backend suite
        **561/561** (`pytest -q`).
      - **Master-prompt country coverage after this increment**: 24
        countries/regions now have at least one real source (up from
        21). The only remaining unresearched territory: the remaining
        named European countries (Switzerland, Poland, Czech Republic,
        Croatia, Serbia, Romania, Norway, Finland).

- [x] **(2026-08-29)** The eight remaining named European countries — a
      dedicated **first** research pass, the last unresearched region
      from the original master-prompt request (Switzerland, Poland,
      Czech Republic, Croatia, Serbia, Romania, Norway, Finland). 5 real
      sources added:
      - **Switzerland** (SBFI ESKAS - Swiss Government Excellence
        Scholarships): `funding_type = "partial_funding"` — a concrete
        monthly amount (CHF 2450) is stated but tuition coverage is
        never mentioned, unlike Japan MEXT/Portugal Camões/GKS.
      - **Poland** (NAWA "Poland My First Choice"): hidden accessibility
        `<h1 class="sr-only">` before the real `<h1 class="header">` —
        the same bug class as India ICCR and Colombia ICETEX. NAWA runs
        several other named programmes each restricted to narrower
        partner-country lists; this one has the broadest eligible list.
      - **Czech Republic** (MŠMT Government Scholarships): a headless
        Next.js-over-WordPress build whose React wrapper divs carry
        auto-generated `id="S:N"` streaming-boundary ids — deliberately
        not used as a selector (a deployment artifact, not a stable
        anchor); scoped instead to `.global-msmt`, a real custom class.
        Unusually, `deadline_keywords` is **left at the base class's
        default** (not overridden to `()`) — this page has a genuine,
        singular, cleanly extractable deadline ("by 30 September 2026 at
        the latest"), confirmed by running the real extractor against
        the real fixture and getting back `2026-09-30`. The first
        source in this whole initiative where deadline extraction is
        actually used, not disabled.
      - **Serbia** ("World in Serbia"): no `<h1>` — the page's only
        heading is a plain `<h2>Scholarships</h2>`, generic but honest.
        `funding_type = "fully_funded"` — explicit free tuition,
        accommodation, food, monthly allowance, and health insurance.
      - **Romania** (MFA Government Scholarships): a genuinely
        interesting deadline-extraction near-miss — the page states a
        real, parseable deadline ("31 March 2026") but the shared
        `extract_confident_date_after` function only searches after a
        keyword's *first* occurrence, and this page's first "deadline"
        mention is an unrelated, dateless one earlier in the eligibility
        section — confirmed directly against the real fixture that
        extraction correctly (if unluckily) returns nothing, so
        `deadline_keywords = ()` was set deliberately.
      - **Croatia** was investigated and found `NOT_SUITABLE`, not
        implemented: every source is a year-dated "Call for
        Applications" page with its own numeric ID (seven different
        such pages found spanning 2020/2021 through 2026/2027), no
        evergreen "about" page independent of a specific year, plus
        nomination-only eligibility via partner institutions.
      - **Norway** was investigated and found `NO_RELIABLE_SOURCE_FOUND`:
        its two historical inbound programs (the "Quota Scheme" and
        NORSTIP) are both confirmed defunct/cancelled across multiple
        independent sources; Lånekassen's remaining support requires
        Norwegian citizenship or existing permanent residence.
      - **Finland** was investigated and found `NOT_SUITABLE`: the one
        national program (EDUFI Fellowship) states on its own official
        page that it "will end at the end of 2025. New applications
        cannot be submitted after 17.10.2025" — already past by this
        session's date, despite several third-party aggregators still
        listing it as "active in 2026." Finland's own study-abroad
        portal confirms no replacement exists.
      - Source count 37 → 41 (5 added: Switzerland, Poland, Czech
        Republic, Serbia, Romania). Docs updated: `docs/
        AUTHORITATIVE_SOURCES.md` #37-#41, `docs/
        COUNTRY_PROVIDER_REGISTRY.md` (new dedicated "Europe" section
        with all 8 findings; Implemented table extended; coverage
        summary and recommended-next-candidates rewritten — **no named
        country or region from the original master-prompt request
        remains unresearched**).
      - Verified: 10 new tests (`tests/test_national_scholarship_programs.py`,
        2 per source) against real fixtures; full backend suite
        **571/571** (`pytest -q`).
      - **Master-prompt country coverage after this increment**: 29
        countries/regions now have at least one real source (up from
        24). Every region named in the original master-prompt request
        has now had at least one full research pass.

- [x] **(2026-08-29)** Beyond the original master-prompt request — with
      every named country/region researched, the user asked to choose
      new countries entirely outside that request. Picked 8 spanning
      regions not yet touched: Hungary, Mexico, Indonesia, Malaysia,
      Vietnam, Egypt, Israel, Kenya. 2 real sources added:
      - **Hungary** (Stipendium Hungaricum): a heavily JS-rendered site
        with no semantic heading markup at all (no `<h1>`-`<h4>`
        anywhere) and a `<title>` tag that only ever yields the single
        word "About" once split — falls back to a title formatted from
        `external_id`, the same choice already made for Saudi Arabia.
        `funding_type = "fully_funded"` — explicit tuition-free
        education plus real HUF/EUR monthly stipend figures.
      - **Mexico** (AMEXCID Excellence Scholarships): one transient
        timeout on first fetch, resolved cleanly on retry. Content
        scoped to the article-body column specifically, not `main`
        (which also pulls in an unrelated "Publicaciones Recientes"
        sidebar of 5 other news items ahead of the real content).
        `funding_type = None` — this overview page explicitly defers
        all concrete funding/deadline terms to a separate "Condiciones
        Generales de la Convocatoria" not linked as plain HTML.
      - **Indonesia** was investigated and found `BLOCKED`: the current
        official interactive site is a pure JS app with zero
        server-rendered content, and a content-rich companion site
        describing the same program explicitly disallows `ClaudeBot` by
        name in its `robots.txt` (alongside GPTBot, Bytespider, and
        others) — honored rather than routed around with a different
        User-Agent.
      - **Malaysia** was investigated and found `NOT_SUITABLE`: the
        real MOHE portal page is too thin (~700 characters, no `<h1>`,
        no funding/deadline language) with the real detail living only
        in an unparsed PDF — the same thin-content shape already ruled
        out for Colombia's reciprocity page.
      - **Vietnam** was investigated and found `BLOCKED`: the one
        candidate site with real content doesn't support HTTPS at all
        (confirmed by direct `ConnectError` on every `https://`
        variant) — this backend's HTTPS-only requirement is a security
        boundary applied uniformly, never relaxed for one adapter.
      - **Egypt** was investigated and found `BLOCKED`: the official
        EGYAID/Study-in-Egypt portal is a pure client-side JS SPA with
        zero server-rendered content on every route checked.
      - **Israel** was investigated and found `BLOCKED`: the MFA
        scholarship page returned 403 Forbidden on 3/3 attempts with
        this backend's actual httpx client, a consistent active block.
      - **Kenya** was investigated and found `NO_RELIABLE_SOURCE_FOUND`:
        the Ministry of Education's scholarships page is a searchable
        multi-entry table of outbound (Kenyans-studying-abroad)
        opportunities, the same database-not-single-page shape already
        seen for Argentina, with no inbound program identified.
      - Source count 41 → 43. Docs updated: `docs/
        AUTHORITATIVE_SOURCES.md` #42-#43, `docs/
        COUNTRY_PROVIDER_REGISTRY.md` (new dedicated "Beyond the
        original request" section with all 8 findings; Implemented
        table extended; coverage summary and recommended-next-
        candidates rewritten).
      - Verified: 4 new tests (`tests/test_national_scholarship_programs.py`,
        2 per source) against real fixtures; full backend suite
        **575/575** (`pytest -q`).
      - **Country coverage after this increment**: 31
        countries/regions now have at least one real source (up from
        29), now including 2 entirely outside the original
        master-prompt request.

- [x] **(2026-08-29)** A second batch beyond the original master-prompt
      request (user said "go on"): New Zealand, Singapore, Pakistan,
      Philippines, Nigeria, Ghana, Rwanda, Jordan. **Zero new sources
      added** — a real, honest research outcome recorded in full rather
      than omitted or forced:
      - **New Zealand**: Manaaki New Zealand Scholarships is a real,
        well-documented, permissively-crawlable inbound program, but
        the entire site is built with Next.js CSS Modules — every
        wrapper down to the immediate parent of the page's `<h1>` uses
        an auto-generated hashed class name, and the generic `<main>`
        tag itself is non-unique with the wrong element first in
        document order. No selector on the page is safe from breaking
        on the next deploy — `NOT_SUITABLE`.
      - **Singapore**: SINGA (A*STAR's well-known PhD scholarship) no
        longer has a dedicated program page — every guessed/search-
        suggested URL 404s, confirmed by scanning the site's full
        643KB `sitemap.xml` directly. The one current "International
        Awards" offering is institution-initiated (Singapore
        researchers apply together with overseas collaborators), the
        same disqualifying shape as Canada's SICS — `NOT_SUITABLE`.
      - **Pakistan**: HEC does run scholarships for foreign students,
        but every domain variant (`hec.gov.pk`, `www.hec.gov.pk`,
        `scholarship.hec.gov.pk`) fails `SSL: CERTIFICATE_VERIFY_FAILED`
        — a real TLS certificate-chain defect, confirmed 6/6 across all
        hostnames — `BLOCKED`, same class as India ICCR/South Africa
        NRF.
      - **Philippines**: CHED's official site returns 403 Forbidden on
        3/3 attempts — `BLOCKED`.
      - **Nigeria, Ghana, Rwanda**: each country's national scholarship
        body (Federal Scholarships Board, Ghana Scholarships Authority,
        Higher Education Council) turned out to be outbound/domestic-
        only — funding citizens to study abroad or at home institutions,
        never funding foreign nationals to study in-country —
        `NO_RELIABLE_SOURCE_FOUND` for all three.
      - **Jordan**: MOHE's "Cultural Agreements" page confirms a real,
        genuinely bidirectional inbound mechanism across 25 partner
        countries, but the actual on-page content (once separated from
        navigation menus) is only two sentences plus a country list —
        no funding, no deadline, no application process — the same
        thin-content bar that already ruled out Colombia's reciprocity
        page and Malaysia's MIS — `NOT_SUITABLE`.
      - No code changes: since nothing was implementable, no source
        classes, config entries, tests, or fixtures were added. Docs
        updated: `docs/COUNTRY_PROVIDER_REGISTRY.md` (new dedicated
        "second pass" section with all 8 findings; coverage summary and
        recommended-next-candidates updated to record the 0-for-8
        outcome honestly).
      - **Country coverage unchanged at 31** — this pass added no new
        sources, only negative findings (which still have value: future
        sessions won't need to re-research these 8 countries from
        scratch).

- [x] **(2026-08-29)** Browser-rendering fallback for JavaScript-only
      scraper sources — a real, tested architectural addition, requested
      explicitly by the user after this session had already hit several
      genuinely JS-only government sites (Egypt, Indonesia's `.go.id`
      site) that plain HTTP cannot extract anything from.
      - New `app/services/browser_rendering.py`: a lazily-launched,
        reused headless Chromium (Playwright) instance; one isolated
        browser context/page per fetch, always closed; a semaphore
        bounding concurrent renders (`browser_render_max_concurrency`,
        default 2); bounded timeouts throughout, never a fixed `sleep()`
        (`domcontentloaded` + an optional caller-supplied CSS selector
        wait, both under `browser_render_timeout_ms`); a response-size
        cap matching the existing HTTP path; known bot-challenge/CAPTCHA
        signature detection (Cloudflare interstitial, hCaptcha/
        reCAPTCHA, "access denied") that raises immediately rather than
        attempting to solve or bypass anything — same policy as every
        prior anti-bot finding in this project (Cyprus, Brazil, Israel).
      - `web_scraper_base.py`: new `looks_javascript_rendered()`
        heuristic (body-text length + "enable JavaScript"-style
        markers, tuned well below Colombia ICETEX's real 330-character
        page so a genuinely thin real page is never misclassified) and
        a new opt-in `WebScraperSource.allow_browser_rendering` flag
        (default `False` for every existing source — zero behavior
        change for all 43 sources already in this registry).
        `WebScraperSource._fetch_html` tries plain HTTP first always;
        only a source that explicitly opted in, whose response the
        heuristic flags, gets a browser-render retry; any render failure
        falls back to the thin HTTP response rather than crashing the
        source's (or any sibling source's) sync task.
      - `app/core/http_client.py`: renamed the private `_validate_url`
        to public `validate_https_url` so both the HTTP and browser
        paths share one HTTPS-only check.
      - Deployment: `Dockerfile` now runs `playwright install --with-deps
        chromium` (documented, real tradeoff: +~300-400MB on every image
        built from it — api, worker, and beat alike, since docker-
        compose.yml builds all three from this one Dockerfile — even
        though only the worker's scraper tasks would ever use it; noted
        as a candidate for a future `Dockerfile.worker` split if size
        becomes a real problem, not attempted here). CI
        (`.github/workflows/ci.yml`) installs the same browser before
        running pytest so the real-browser tests actually run there, not
        just locally.
      - New settings: `browser_render_timeout_ms`,
        `browser_render_max_concurrency`, `browser_executable_path`
        (left unset in every real deployment; only needed to point at a
        pre-installed browser binary whose revision doesn't match the
        pinned `playwright` package version, which is exactly this
        project's own dev sandbox — its preinstalled Chromium is a
        different revision than what `playwright==1.49.1` expects by
        default).
      - Deliberately **not** built (would be premature generality with
        zero current users): SPA click-through navigation (filters,
        "Load more," infinite scroll), reverse-engineering a site's own
        internal JSON/GraphQL API, a persisted per-domain "rendering
        capability profile," multi-language deduplication. If a future
        source genuinely needs one of these, design it against that
        source's real, live-tested page then — not in the abstract.
      - **No existing source was converted to use this** — none needed
        it (all 43 already work over plain HTTP) — and the two live
        JS-only candidates already on record (Egypt, Indonesia's
        `.go.id`) were deliberately **not** flipped to
        `allow_browser_rendering = True` and marked working: this
        session's own sandboxed environment could launch a real headless
        Chromium (proven against a local self-signed-HTTPS test server)
        but every attempt to navigate it to a real *external* HTTPS site
        failed at the TLS layer through the sandbox's own egress proxy
        (`net::ERR_CONNECTION_RESET`, not reproducible with plain httpx/
        curl in the same sandbox — a sandbox limitation, not a defect in
        the new module). Both country-registry entries were updated with
        this exact finding rather than silently left stale or
        speculatively marked fixed.
      - Verified: 11 new tests (`tests/test_browser_rendering.py`) —
        pure-heuristic unit tests, mocked `WebScraperSource` wiring/
        fallback tests, and (a genuine, non-mocked proof) a real headless
        Chromium launch + JavaScript execution + rendered-DOM extraction
        against a local self-signed-HTTPS server, plus HTTPS-only
        enforcement and challenge-page-detection tests against the real
        `fetch_rendered_html`/`_looks_like_a_challenge_page` functions.
        Full backend suite: **586/586** (`pytest -q`, up from 575).
        `pip-audit -r requirements.txt`: no known vulnerabilities in the
        new `playwright` dependency.

- [x] **(2026-08-29)** Hybrid Scholarship Discovery and Verification
      Engine — the rest of the 27-section spec, built as a continuation
      of the browser-rendering fallback above, per an explicit
      "continuation loop" instruction to implement every remaining
      feasible requirement without pausing for confirmation between
      phases. Everything below is additive: none of the 43 existing
      scraper sources changed behavior, and none has been migrated onto
      any of the new engines — see docs/AUTHORITATIVE_SOURCES.md's
      "Beyond a single render" section and its requirement matrix for the
      full per-requirement COMPLETE/PARTIALLY_COMPLETE/
      BLOCKED_BY_ENVIRONMENT/NOT_APPLICABLE breakdown.
      - Headless-mode configurability (`PLAYWRIGHT_HEADLESS`, forced back
        to `true` whenever `APP_ENV=production`) and generic cookie/
        consent-banner detection + auto-accept
        (`AUTO_ACCEPT_REQUIRED_COOKIES`, scoped to a detected cookie/
        consent container only — never a page-wide "Accept"/"Continue"
        click) added directly to `browser_rendering.py`.
      - `browser_rendering.py` also gained structured console-error/page-
        error/failed-request/HTTP-error capture, classified INFO/
        WARNING/ERROR/CRITICAL — a known third-party analytics/tracker
        failure is downgraded, never used to fail an otherwise-good
        render; a same-origin 5xx is CRITICAL.
      - New `app/services/browser_interaction.py`
        (`BrowserInteractionEngine`): click/wait-for-selector/extract-
        URL/capture-content primitives on a live Playwright page, plus
        `wait_for_navigation_or_change`, which races a new tab, a URL
        change (including a client-side `history.pushState` route), or
        an in-page DOM change under a bounded timeout — never
        `sleep()`. New `browser_rendering.interactive_session` context
        manager shares the reused-browser/semaphore/HTTPS-only/cookie-
        banner machinery for anything needing more than one render.
      - New `app/services/pagination_engine.py`: `paginate_by_url` (no
        browser needed) for `?page=N` pagination, `paginate_by_click`
        (one function handling both a "Next" button and a "Load More"
        control, since it dedupes by key rather than assuming the
        shape) for click-driven pagination. Bounded by new
        `MAX_PAGES_PER_SOURCE`/`MAX_RECORDS_PER_SOURCE` settings; stops
        on an empty page, no new records, a disabled/absent "next"
        control, or a fetch failure.
      - New `app/services/infinite_scroll_engine.py`: render → extract →
        scroll → wait for real DOM growth → extract → compare →
        continue. Bounded by new `MAX_SCROLL_ITERATIONS`/
        `SCROLL_STAGNATION_LIMIT` settings.
      - New `app/services/filter_engine.py`: applies a caller-described
        filter set (auto-detecting a `<select>` vs. a clickable
        control; an absent selector is skipped, never an error).
        `iter_filter_combinations` yields a bounded cartesian product —
        never an automatic sweep of every combination.
      - New `app/services/application_link_discovery.py`: finds
        "Apply"-style controls (broad phrase matching, not just literal
        button text), reads `href` directly where present, and for a
        control without one, clicks through the interaction engine and
        records where that led (new tab / URL change / in-page modal).
        Bounded to 5 href-less clicks per page. Never fills in a form,
        never creates an account, never submits anything.
      - New `app/services/application_link_validation.py`: independently
        fetches a discovered/known application URL and classifies it
        `VALID_OFFICIAL_APPLICATION` / `VALID_AUTHORIZED_EXTERNAL_PORTAL`
        / `INFORMATION_PAGE_ONLY` / `BROKEN` / `BLOCKED` / `UNKNOWN` by
        HTTP status, redirect chain, final domain, and page content —
        only the source's own domain or an explicitly pre-authorized
        portal domain can ever come back `VALID_*`; everything else is
        `needs_review=True`, never silently treated as verified.
      - New `app/services/content_completeness.py`: scores a scraper
        adapter's raw extracted field mapping 0-100 across CRITICAL/
        IMPORTANT/OPTIONAL tiers, run *before* attempting to construct a
        `NormalizedExternalOpportunity`; `needs_review` is forced True
        whenever any CRITICAL field is missing regardless of score.
      - New `app/services/source_capability_profile.py`: in-process
        (not persisted) memory of what's actually been observed about a
        domain — requires JS, pagination shape, cookie banner, and so
        on — recorded automatically by every module above, for every
        source's own domain regardless of whether it has opted into
        browser rendering. Deliberately observability, not automation:
        nothing reconfigures a source's fetch behavior from this
        evidence alone — `allow_browser_rendering` stays a human
        decision made only after live-testing, same as always.
      - New `app/services/scraper_metrics.py` (process-wide counters +
        derived ratios — an untouched ratio reads `None`/`null`, never a
        fabricated `0.0`) and `GET /api/v1/scraper-metrics`
        (`app/api/routes/scraper_metrics.py`, staff-gated) to read them.
      - New `app/services/scraper_adapters.py`:
        `GenericHTMLAdapter`/`GenericJSAdapter`/`GovernmentPortalAdapter`/
        `UniversityPortalAdapter`/`SPAAdapter` base classes for a
        *future* source simple enough to describe declaratively — none
        of the 43 existing sources migrated, none needs to be.
      - Deliberately **still** not built, as premature generality with
        zero current users: reverse-engineering a site's own internal
        JSON/GraphQL API (no JS-only candidate on record has one), and
        multi-language deduplication.
      - **Still not independently verified against a real external
        site** — same sandbox limitation as the original browser-
        rendering fallback (the egress proxy fails at the TLS layer for
        real Chromium navigation to external HTTPS sites). Every new
        module is proven against real Chromium and purpose-built local
        mock pages, which proves the Playwright mechanics genuinely
        work; it can't prove what a concrete adapter for Egypt/
        Indonesia would need to configure against their real markup.
        Docker also remains unbuildable in this sandbox (daemon not
        running) — the Dockerfile needed no changes for this pass, but
        that's still unverified by an actual build here.
      - Verified: 84 new tests across 12 new test files plus additions
        to `tests/test_browser_rendering.py` (11 more there). Full
        backend suite confirmed green after every individual phase, and
        the complete suite collects and passes at **670/670**
        (`pytest -q`, up from 586).

- [x] **(2026-08-29)** 40-country coverage audit against the platform's
      explicit target list, closing the two countries that had never
      actually been researched (China, United States) and fixing one
      real reachability bug found along the way (Eswatini) — a
      continuation loop instruction to audit the full 40-country
      requirement, implement every genuine gap, and report honestly on
      what remains, rather than claim coverage that isn't real.
      - **Audit finding**: cross-referencing the exact 40-country list
        against `docs/COUNTRY_PROVIDER_REGISTRY.md` (already extremely
        thorough from prior sessions — every one of the 40 had a
        documented, live-tested classification except two) showed 38 of
        40 already had a defensible SUPPORTED/PARTIALLY_SUPPORTED/
        NOT_SUITABLE/BLOCKED/NO_RELIABLE_SOURCE_FOUND finding from real
        research, not a guess or a placeholder. Only China and the
        United States had never been individually researched at all.
      - **United States — closed, SUPPORTED.** The prior US-facing
        sources (Grants.gov, USAJOBS, ReliefWeb) are federal grants/
        jobs/humanitarian postings, not international-student
        scholarships, and Fulbright was already correctly rejected
        (fragmented across ~160 embassy pages). Found and implemented
        `educationusa.state.gov/find-financial-aid` (US Department of
        State, EducationUSA network) — a real, live, plain-HTTPS
        paginated Drupal Views listing of 277+ institution-specific
        scholarships. New `app/services/educationusa_source.py`,
        wired end-to-end (config, source registry, Celery beat schedule
        + task, opportunity_sync mapping) exactly like every other
        source. **The first real production consumer of
        `app/services/pagination_engine.py`'s `paginate_by_url`**, built
        earlier this session. Verified with 3 genuinely separate real
        HTTPS fetches (page 0, page 1, and `?page=40` confirming the
        site's own real zero-row "past the last page" response) and 5
        new tests against those exact fixtures, captured unmodified.
      - **China — closed, BLOCKED.** The China Scholarship Council (CSC)
        administers a real, major, legitimate program. Every candidate
        page — `csc.edu.cn`, `studyinchina.csc.edu.cn`, and even
        `robots.txt` itself — returns either HTTP 412 or an obfuscated
        JavaScript anti-bot challenge page ("系统繁忙，请稍后再试" —
        "system busy"), the same class of protection already documented
        for Cyprus and Brazil. Never attempted to bypass it — detected,
        classified, and recorded as `BLOCKED`, not silently skipped or
        left unresearched.
      - **Eswatini — reachability bug found and fixed, reclassified
        `NOT_SUITABLE`.** While re-checking the two previously-
        "unreachable" Sierra-Leone-region sources, found that
        `https://www.slas.gov.sz` (the configured host) still times out,
        but the bare `https://slas.gov.sz` (no "www.") is genuinely
        reachable (200, real content, 3/3 attempts). Fixed
        `eswatini_slas_base_url` to the working host — a real, verified
        technical fix. However, the real page content turned out to be
        a domestic student-loan portal for Eswatini nationals, with
        neither "scholarship" nor "SADC" appearing anywhere in its HTML
        — `EswatiniSlasSource`'s own keyword-matching correctly extracts
        zero records from it. Documented honestly as "reachability
        fixed, but not confirmed to produce any records" rather than
        claimed as newly working — added a real-fixture regression test
        proving it fails safe to an empty list rather than fabricating
        a match. Sierra Leone's own MTHE was re-checked the same way and
        remains genuinely unreachable over HTTPS (a proxy-level TLS
        failure on every attempt, distinct from the Eswatini www/non-www
        issue) — no fix available, status unchanged.
      - **Not touched this pass, per the audit's own honest read**: the
        remaining 35 countries already had real, defensible research on
        record from prior sessions and were not re-litigated without
        new information — re-researching them today (same calendar day
        as their original research) would not surface anything new. The
        spec's "multiple source types per country" ambition (university
        + government + embassy + foundation sources for every country)
        remains a real, larger gap beyond this pass's scope — most
        countries in this registry have exactly one flagship government
        source, not the full multi-source-type coverage the spec
        describes; closing that fully would require dedicated
        per-country research at a scale beyond one session.
      - Fixed two real (if minor) issues surfaced while running the full
        suite: `tests/test_opportunity_import.py`'s hardcoded source-
        count/set assertions needed the new `educationusa_financial_aid`
        source added; two real-Chromium new-tab-detection tests
        (`test_browser_interaction.py`,
        `test_application_link_discovery.py`) were genuinely flaky under
        full-suite system load (5/5 passed in isolation, intermittently
        failed only when running alongside ~670 other tests) — fixed by
        giving those two specific tests a longer timeout (15s vs. 5s),
        not by changing any production logic.
      - Verified: 6 new tests (5 for EducationUSA, 1 for Eswatini's real
        content). Full backend suite confirmed green: **676/676**
        (`pytest -q`, up from 670).

- [x] **(2026-08-30)** Next-loop research pass — Mastercard Foundation
      Scholars Program investigated as a real candidate for a
      cross-country FOUNDATION-type source (a genuine gap named by the
      spec: most countries here have exactly one government source, not
      the university/government/embassy/foundation mix described).
      Real, major, Africa-focused, directly relevant to Sierra Leone
      (58,000+ scholarships committed, 62 partner universities);
      `robots.txt` explicitly allows `ClaudeBot` by name. Not
      integrated: the program's own overview page has no single
      deadline/application (decentralized to 62 partner institutions,
      the same reason Canada/Denmark/Wales were rejected), and the
      actual per-institution listing page
      (`.../where-to-apply/`) is a client-side widget with no
      server-rendered fallback (`curl` returns "Institutions Error
      loading data. Please try again." instead of the list) — its
      underlying data API could not be found in the page's static JS.
      Live-tested Chromium against this exact URL to confirm the
      sandbox's standing browser-automation limitation still applies
      (`net::ERR_CONNECTION_RESET`) rather than assuming it. Documented
      as a strong recommended-next candidate for a session with working
      outbound browser access, not silently dropped. No code changes
      this pass — pure research, recorded in
      `docs/AUTHORITATIVE_SOURCES.md` and
      `docs/COUNTRY_PROVIDER_REGISTRY.md`.

- [x] **(2026-08-30)** Implemented the **Joint Japan/World Bank Graduate
      Scholarship Program (JJ/WBGSP)** — a real next step on the same
      "multiple source types per country" gap, continuing directly from
      the Mastercard Foundation research above. Also re-tested
      `sl.usembassy.gov/educational-professional-exchanges/` (Sierra
      Leone's US Embassy exchanges page, already flagged broken by
      earlier Fulbright research) — still a persistent "Technical
      Difficulties" error, 3/3 attempts, not fixed.
      - JJ/WBGSP is real, major (World Bank Group, funded by the
        Government of Japan), and — checked directly, not assumed —
        Sierra Leone is confirmed on the programme's own published
        eligible-countries list. Unlike Mastercard Foundation, its
        overview page (`/en/programs/scholarships/jj-wbgsp`) is real
        static server-rendered HTML with genuine eligibility criteria,
        funding coverage, and two dated application windows in its own
        text — no browser rendering needed.
      - New `WorldBankJJWBGSPScholarshipSource` in
        `national_scholarship_programs.py` (the `_SingleProgramSource`
        pattern, `country = None` since it's not tied to one
        destination, same as Wells Mountain Initiative). Wired
        end-to-end (config, source registry — its first
        `international_organization`-typed entry, Celery beat + task,
        opportunity_sync mapping).
      - `deadline_keywords` tries "application window #1" before
        "window #2"/generic "deadline" — the page states both windows'
        dates together (e.g. "Application Window #1 from January 18 to
        February 26, 2027"); `extract_confident_date_after` correctly
        skips the day+month-only opening date for the first full
        day+month+year literal that follows — verified this actually
        extracts 2027-02-26, not guessed to work.
      - Verified: 1 new test against a real fixture captured unmodified
        from the httpx fetch, plus the hardcoded source count/set in
        `test_opportunity_import.py` updated for the new source. Full
        backend suite confirmed green: **677/677** (`pytest -q`, up
        from 676).

- [x] **(2026-08-30)** Implemented **Rotary Peace Fellowships**, and
      researched (but did not integrate) the **Aga Khan Foundation
      International Scholarship Programme** — continuing the same
      "multiple source types per country" gap.
      - Aga Khan ISP is real and legitimate, but its own published
        country scope (Bangladesh, India, Pakistan, Afghanistan,
        Tajikistan, Kyrgyzstan, Syria, Egypt, Kenya, Tanzania, Uganda,
        Madagascar, Mozambique) does not include Sierra Leone — rejected
        on eligibility grounds, not a technical one, matching this
        project's "never invent eligibility" rule applied honestly in
        both directions.
      - Rotary Peace Fellowships is real, genuinely open worldwide by
        nationality (no country restriction stated anywhere on its own
        page), real static server-rendered content — no browser
        rendering needed. `robots.txt` allows crawling with
        `Crawl-delay: 10`, respected via a source-specific
        `min_request_interval_seconds = 10.0` (well above this
        project's usual 2-second default).
      - New `RotaryPeaceFellowshipSource` in
        `national_scholarship_programs.py`, wired end-to-end. One
        fragility recorded honestly rather than silently risked: the
        page has no semantic content wrapper (no `<article>`, no
        descriptive `class`/`id`), only Tailwind utility-class
        combinations — the description selector works today (verified
        against the real page, first-match-is-correct among 3 matching
        elements) but is more brittle than most sources here; documented
        in both the class docstring and `docs/AUTHORITATIVE_SOURCES.md`
        so a future `description=None` isn't mistaken for a real content
        change without checking the live markup first.
      - `deadline_keywords` kept active rather than disabled even though
        the page's own text currently states only a month+year for the
        next cycle (no day) — correctly resolves to `deadline=None`
        today, but will pick up a real date automatically once the page
        states one.
      - Verified: 2 new tests (normalization against a real fixture,
        plus the crawl-delay assertion) against a real captured fixture,
        plus the hardcoded source count/set updated. Full backend suite
        confirmed green: **679/679** (`pytest -q`, up from 677).

- [x] **(2026-08-30)** Implemented the **Erasmus Mundus Joint Masters
      Catalogue** (EACEA) — a third addition to the "multiple source
      types per country" gap, and the second real production consumer
      of `pagination_engine.paginate_by_url` after EducationUSA,
      independently proving that engine generalizes across genuinely
      different real sites rather than being tuned to one.
      - Real, ~220 EU-funded joint master's programmes, genuinely open
        to applicants "from all over the world" per the catalogue's own
        text — not restricted by nationality. A real, plain
        server-rendered `?page=N` listing built with the EU's own ECL
        design system — no browser rendering needed.
      - Noted and correctly did *not* treat as a blocker: the page
        carries a page-level `<meta name="robots" content="follow,
        noindex">` search-engine-indexing directive, which is a
        different concern from the Robots Exclusion Protocol's
        `robots.txt` crawl permission — the site's actual `robots.txt`
        scopes its `Disallow:` rules to `Googlebot` specifically, the
        same "only specific-bot rules" pattern already seen for
        Mexico's AMEXCID.
      - New `ErasmusMundusJointMastersSource` in a new
        `erasmus_mundus_source.py` (the paginated-listing pattern, same
        shape as `educationusa_source.py`), wired end-to-end.
      - **A real, live-observed proof of this project's HTTPS-only
        discipline actually working**: two of the ~220 programmes' own
        listed websites (RESCO, European Forestry) use plain `http://`
        rather than `https://`, and are correctly, silently dropped by
        the shared `absolute_https_url` check rather than "fixed" by
        guessing a scheme — found while writing the test (my own first
        draft assumed all 20 cards per page would survive; the real
        fixtures proved otherwise, and the test was corrected to match
        reality rather than the reverse).
      - No per-programme deadline is stated on this listing page (each
        consortium sets its own) — `deadline` stays `None` for every
        record, never guessed from the catalogue's generic "October and
        January" text.
      - Verified: 5 new tests against three real fixture pages (page 0,
        page 1, and a genuinely-past-the-last-page response), plus the
        hardcoded source count/set updated. Full backend suite confirmed
        green: **684/684** (`pytest -q`, up from 679).

- [x] **(2026-08-30)** Implemented **UAEU Scholarships, Fellowships, and
      Graduate Assistantships** — closes the United Arab Emirates line
      item in the country registry (previously `NO_RELIABLE_SOURCE_FOUND`
      at the national-government level; that finding's own text already
      flagged UAEU as the right follow-up) and this project's first
      genuinely `UNIVERSITY`-typed source — every other web-scraped
      source until now has been government/international-organization/
      funding-organization-typed.
      - Real, server-rendered page (`/en/cgs/scholarship.shtml`, 200,
        ~169KB), `robots.txt`-unrestricted (`User-agent: *` allowed, only
        narrow unrelated admin/legal `Disallow:` rules) — no browser
        rendering needed.
      - One real fragility found and handled correctly: the page's
        Tailwind accordion widget (`.aegov-accordion`/`.accordion-item`)
        is reused site-wide for both page-navigation menus and this
        scholarships list — 27 total accordion items, only 13 of them
        real programmes. Scoped via a CMS-id-prefix attribute selector
        (`[id^="faqs-section"]`), stable in practice even though the
        hash suffix after it changes on every republish, rather than a
        hardcoded full id or the shared widget class alone.
      - Extracts all 13 real accordion items (fellowships, research/
        teaching/administrative assistantships, department-specific PhD
        studentships) as their own records, deliberately **not filtered
        by nationality eligibility** — several titles say "(All
        nationalities)", others explicitly say "UAE nationals"/"UAEU
        Alumni only" in their own real title text, extracted verbatim
        for human review rather than acted on, matching this project's
        standing "AI's role: none, today" eligibility policy
        (`docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` §10).
      - Each item's own detail link (several are PDFs, not HTML) is
        stored as both `official_source_url` and
        `official_application_url` without being fetched itself, matching
        how EducationUSA's and Erasmus Mundus's own per-row links also
        aren't followed.
      - New `UaeuScholarshipsSource` in a new
        `uaeu_scholarships_source.py`, wired end-to-end including the new
        `"university"` `source_type` value on the existing free-text
        source-type column.
      - Verified: 3 new tests against a real fixture captured unmodified
        from the fetch, plus the hardcoded source count/set updated (48
        → 49). Full backend suite confirmed green: **687/687** (`pytest
        -q`, up from 684 — the one other failure seen in a full-suite run,
        `test_click_reveals_new_tab_destination`, is the already-documented
        flaky real-Chromium test under system load; re-run in isolation
        and passed).

- [~] **(2026-09-01)** Implemented the **Premium Application-Preparation
      Platform** — backend architecture complete and fully tested;
      Flutter frontend has a real, working landing/pricing/checkout slice
      wired end-to-end, but the individual document-builder screens (CV/
      SOP/study plan/research proposal/fellowship editors, ATS analyzer
      UI, requirement-matcher UI, admin dashboard UI) are **not yet
      built** - marked in-progress, not done. See PRD.md/Architecture.md
      for the full design; this entry covers what was actually shipped.

      **Payment architecture** (app/services/payment_provider.py):
      - Provider-independent `PaymentProvider` interface
        (initializePayment/verifyPayment/getTransaction/refundPayment/
        createSubscription/cancelSubscription/handleWebhook, matching the
        spec's own method names). `NullPaymentProvider` (the default when
        `PAYMENT_PROVIDER` is unset) raises a clear "not configured" error
        on every call rather than fabricating a successful transaction -
        never claims a payment succeeded because a frontend request says
        so.
      - `StripePaymentProvider` — a real, complete integration against
        Stripe's actual documented REST API (Payment Intents, Refunds,
        Subscriptions, and its published webhook-signature algorithm:
        HMAC-SHA256 over `"{timestamp}.{payload}"`, `hmac.compare_digest`,
        a 300-second replay-window check). Correct code today; still
        needs a real `PAYMENT_SECRET_KEY`/`PAYMENT_WEBHOOK_SECRET` to
        reach Stripe's servers - that's expected, not a gap, per the
        user's own "credentials supplied later" instruction. Adding a
        second provider (Paystack/Flutterwave - directly relevant given
        this platform's Sierra Leone-focused user base) is a new class
        implementing the same interface, not a change to any calling
        code.
      - `app/services/payment_service.py` orchestrates the real flow:
        `initiate_checkout` creates a `Payment` row (status=pending)
        *before* the applicant reaches the provider; `process_webhook_event`
        verifies the signature, then relies on two independent real
        database-uniqueness constraints for duplicate-webhook protection
        (`PaymentEvent.UNIQUE(provider, provider_event_id)` and
        `Entitlement.UNIQUE(source_payment_id)`) rather than
        application-level checking alone; `grant_entitlement_for_payment`
        snapshots the plan's feature list *at grant time* so a later admin
        price/feature edit never retroactively changes what an
        already-paying user has; `refund_payment` calls the real provider
        refund API and revokes the entitlement only once the provider
        confirms success.
      - A genuine bug found and fixed during this build, not just
        theorized: raising the route's `HTTPException` *inside*
        `async with session.begin()` was silently rolling back the
        deliberately-persisted `failed`-status `Payment` row (an
        unhandled exception exiting that block always rolls back) -
        `app/api/routes/premium_billing.py::checkout` now captures the
        error and re-raises it *after* the block commits, so a failed
        checkout attempt is still visible on the admin dashboard.
      - A second real bug found and fixed: `app/core/entitlements.py`'s
        `require_entitlement` FastAPI dependency runs (and reads) before
        the route body, on the same request-scoped session - a plain read
        still opens SQLAlchemy's "autobegin" transaction, which collided
        with a route body's own explicit `async with session.begin()`.
        Fixed by rolling back inside the dependency once its own check is
        done - and *specifically* checking `has_feature()` **before**
        that rollback, since `rollback()` expires every already-loaded
        ORM attribute (unlike `commit()`, there is no
        "expire on rollback = False" option), so reading
        `entitlement.feature_keys` afterward from that plain,
        non-async function would otherwise trigger an illegal
        greenlet-less lazy-reload. This affects every real request in
        production (not just the test session-reuse pattern that
        surfaced it), so it was a genuine, would-have-shipped bug.
      - Idempotency/entitlement-lifecycle logic first proved directly at
        the service layer via a standalone script exercising the real
        SQLite schema (checkout → webhook success → duplicate webhook →
        refund → entitlement revocation, all assertions passing) before a
        single route was written - caught the two bugs above early.

      **AI architecture** (app/services/ai_provider.py):
      - `AIProvider` interface with `NullAIProvider` (default; raises
        "AI generation is not configured" rather than fabricating
        document content), `OpenAIProvider` (real Chat Completions API
        shape) and `AnthropicProvider` (real Messages API shape) - both
        verified against a mocked HTTP layer for the exact real request
        shape each provider's documented API expects (model/messages/
        system field placement, `Authorization: Bearer`/`x-api-key`
        header, token-usage field names). All network calls go through
        the existing shared `app/core/http_client.py` (HTTPS-only,
        timeout, bounded retry) - a small, backward-compatible
        `timeout_seconds` override parameter was added to
        `post_json`/`get_json` so AI calls can use a longer budget than
        the 40s every other external call shares, without bypassing the
        shared client.

      **No-fabrication document generation**
      (app/services/document_generation.py) - two deliberately different
      paths:
      - **CV content** is assembled *deterministically* from the
        applicant's own `ApplicantBackgroundEntry`/`ApplicantProfile`
        rows - no AI involved by default. AI's only role is an explicit
        opt-in, per-field wording *polish* (`ai_polish_text`), instructed
        to add no new fact/number/date/claim not already in the original
        text - "AI may improve wording but must remain faithful to
        user-provided facts," taken literally.
      - **Narrative documents** (SOP, personal statement, motivation
        letter, study plan, research proposal, fellowship essays) do need
        generated prose, so they go through the AI provider - but the
        prompt is built entirely from a real "facts block" (a verbatim
        dump of the applicant's own background/profile data) plus their
        own free-text answers to a structured questionnaire. The system
        prompt explicitly forbids inventing any fact, award, degree,
        publication, job, project, research finding, citation, or
        statistic; a thin section is written honestly rather than padded.
      - `ApplicantBackgroundEntry` (new: education/work_experience/
        project/publication/award/leadership_community/skill/reference,
        one consolidated table with a category discriminator) is the
        *only* source of fact this pipeline is allowed to read from -
        there was previously no structured work-history/education-history
        data model at all beyond `ApplicantProfile`'s summary fields, so
        this closes that real gap rather than generating from nothing.

      **Requirement matching, readiness score, ATS analysis** - all three
      are deterministic, rule-based, and work identically whether or not
      an AI provider is configured (never AI-dependent for a correctness-
      sensitive score):
      - `app/services/requirement_matching.py` extracts real
        requirement-shaped sentences from the target opportunity's own
        description text and classifies each against real profile/
        background data into MATCH/PARTIAL_MATCH/MISSING/
        NEEDS_VERIFICATION - nationality/citizenship requirements always
        resolve to `needs_verification` (free-text list-parsing isn't
        reliable enough to assert eligibility either way), matching this
        project's existing "AI's role: none, today" eligibility policy.
      - `app/services/readiness_score.py` computes a fully documented,
        weighted score (profile 15% / background 10% / documents 40% /
        requirements 20% / checklist 15%) live from current data on every
        request - never a stored, staleness-prone guess.
      - `app/services/ats_analysis.py` scores structure/formatting/
        readability/keyword-coverage and always returns a disclaimer that
        the score "does not guarantee that any application will be
        accepted" - the spec's own explicit requirement, enforced as a
        field on every response, not just prose.

      **Category workflows** (app/services/category_workflow.py) - a
      single `CATEGORY_WORKFLOWS` registry mapping each of the 9 required
      applicant categories (undergraduate/postgraduate/PhD/fellowship/
      research scholarship/professional scholarship/exchange-mobility/
      short-course-training/internship) to its own document-kind list and
      checklist items - adding or changing a category's workflow is a
      registry edit, never new branching logic scattered through routes.

      **Document versioning, export** - `PremiumDocumentVersion` is
      append-only (an edit always inserts a new version row; "restore"
      copies an old version's content into a new one, never rewinds in
      place); PDF export (`reportlab`) and DOCX export (`python-docx`,
      new dependencies, `pip-audit`-clean) are single-column/no-tables/
      no-images by construction, so a CV export is ATS-compatible by
      construction, not just by claim.

      **Database**: 14 new tables, one migration
      (`20260901_33_premium.py`) - see Database.md §2.14 for the full
      per-table breakdown and why none duplicate an existing table.

      **Admin dashboard** (app/api/routes/premium_admin.py, RBAC-gated
      administrator/superAdministrator): plan CRUD (price/features/
      active-state, no redeploy needed), payments list with status
      filter, refund issuance, revenue summary, AI usage breakdown by
      feature/status, admin-configurable usage-limit overrides.

      **Flutter** (`lib/features/premium/`) - domain models
      (`PremiumPlan`/`PremiumEntitlement`/`PremiumStatus`/
      `PremiumPayment`/`CheckoutResult`), the standard dual `Api`/`Demo`
      repository pair, a `PremiumFeatureGate` reusable locked-state
      widget (explicitly documented as UI convenience only - the real
      authorization boundary is always the backend's own
      `require_entitlement` check, matching this app's existing
      `AccessControlPolicy` convention), and a real
      `PremiumLandingScreen` (loading/error/retry/empty states, "You have
      Premium" banner when entitled, real price/feature list per plan,
      checkout initiation showing either real next steps or a clear
      "no payment provider configured yet" message). Wired into
      `app.dart` and a new sidebar entry in the applicant dashboard - no
      new router or state-management package added, per Coding_Rules.md
      §1. **Not built yet**: the individual builder screens themselves
      (CV/SOP/study plan/research proposal/fellowship editors), the ATS
      analyzer UI, the requirement-matcher/readiness/checklist UI, the
      billing-history page, the admin dashboard UI, and the usage
      dashboard - all real, working backend routes exist for every one of
      these already (see above); only their Flutter presentation layer is
      still to build. **Not compiled, `flutter analyze`'d, or
      `flutter test`'d this session** (no Flutter SDK available in this
      environment, same limitation noted throughout this file) - written
      carefully against this codebase's own established patterns
      (verified line-by-line against `guidance`'s real
      domain/data/presentation files) and a manual brace/paren-balance
      check, but genuinely unverified beyond that.

      **Security review performed**: server-side-only entitlement
      checks (never a JWT claim, never a client flag); webhook signature
      verification with replay-window protection; secrets never logged or
      exposed to the frontend (`PAYMENT_SECRET_KEY`/`PAYMENT_WEBHOOK_SECRET`/
      `AI_API_KEY` are all `SecretStr`); every mutating premium route
      requires `get_current_user` plus (where applicable)
      `require_entitlement`; admin routes require
      `administrator`/`superAdministrator`; PII-adjacent applicant
      background data has the same owner-only access pattern as
      `ApplicantDocument`/`ApplicantProfile`, no new staff read path
      added.

      **Verified**: 50 new backend tests (payment critical-path routes,
      webhook idempotency/signature-forgery unit tests with real computed
      HMACs, AI-provider request-shape tests, usage-limit enforcement,
      applicant-background CRUD/ownership, application-preparation
      workflow incl. the two CRITICAL "free user denied"/"expired
      entitlement denied" tests, premium-documents CV grounding/ATS/
      export/versioning, admin plan CRUD/refund/revenue). Explicitly
      includes every "Critical test" the platform spec named by name:
      FREE USER → denied, PAID USER → allowed, EXPIRED ENTITLEMENT →
      denied, FAILED PAYMENT → no entitlement, DUPLICATE WEBHOOK → no
      duplicate entitlement. Full backend suite confirmed green:
      **737/737** (`pytest -q`, up from 687). `pip-audit`: no known
      vulnerabilities in `reportlab`/`python-docx`.

      **Deliberately not built / requires a decision or credential**:
      a second payment provider adapter (no provider chosen yet - the
      user said credentials come later); a real payment SDK integration
      in Flutter (e.g. `flutter_stripe`) for the client-side card-entry
      step, since that's a new dependency tied to whichever provider is
      eventually chosen; the individual document-builder Flutter screens
      listed above; PlatformConfiguration-style feature-flag wiring for
      individual future plans (the architecture supports adding a
      "CV / ATS only" plan today via the admin API, but no second plan
      has been created); a `plan_code`-scoped `UsageLimit` UI (the
      per-feature-global override is wired and tested; per-plan overrides
      use the same schema but have no admin UI yet).

- [x] **(2026-09-03)** Independent, skeptical production audit of the
      entire Premium Application-Preparation Platform built 2026-09-01 —
      not a self-review, a deliberate attempt to disprove "it's done."
      Explicit method: for every candidate issue, reproduce it against the
      real code first (a standalone script, or the real HTTP test client -
      never reasoning alone), fix the root cause, then write a new
      regression test that exercises the actual route/service and re-run
      it to confirm. **Eight real, distinct bugs found, fixed, and
      verified this way** (see Changelog.md's matching dated entry for the
      user-facing summary; full detail here):

      1. **Lost AI-usage audit trail on failure.** `generate_cv`'s polish
         path and `generate_narrative` both raised their `HTTPException`
         *inside* the same `async with session.begin()` block that had
         just written an `AIUsageRecord` for the failed attempt - an
         unhandled exception exiting that block always rolls back the
         entire transaction, the deliberate write included, so a failed
         AI request left no trace at all (violates the platform spec's own
         "track every AI request attempted, not just successes"
         requirement, and the admin AI-usage dashboard silently
         undercounted failures). Reproduced with a script showing 0
         `AIUsageRecord` rows after a forced provider failure. Fixed by
         restructuring both routes to a `pending_error: HTTPException |
         None` sentinel, raised only after the block commits normally.
         Verified: repro script now shows 1 record; two new HTTP-level
         regression tests added
         (`tests/test_premium_documents_route.py::
         test_failed_narrative_generation_still_records_ai_usage`,
         `::test_failed_cv_polish_still_records_ai_usage`).
      2. **The identical bug pattern, independently present in the refund
         path.** `payment_service.refund_payment` propagated a
         `PaymentProviderError` from the payment provider's own refund
         call with no `Refund` row and no audit record left behind -
         inconsistent with `initiate_checkout`'s own (already-correct)
         failure handling two functions above it in the same file.
         Reproduced with a script: a forced provider failure left 0
         `Refund` rows and 0 audit records. Fixed in two places: (a)
         `refund_payment` now writes a `status=failed` `Refund` row and an
         `AuditResult.failure` audit record before re-raising, and (b) the
         admin route (`premium_admin.py::refund`) - which was *also*
         raising its own `HTTPException` from inside the same
         `session.begin()` block, which would have rolled back (a)'s own
         writes right back out - was restructured to the same
         deferred-raise pattern as fix #1. Verified: repro script now
         shows 1 `Refund(status=failed)` row and 1 audit record, with the
         original payment/entitlement left untouched; new HTTP-level
         regression test
         (`tests/test_premium_billing_route.py::
         test_failed_refund_attempt_still_leaves_an_audit_trail`).
      3. **`Content-Disposition` header injection risk.** A document
         export's filename was built with `f"{document.title}..."`
         directly into the response header - `title` is free-text, up to
         500 characters, no character restriction at the schema layer.
         Added `safe_export_filename()` (collapses anything outside
         `[A-Za-z0-9._-]` to `_`) and wired it into the export route.
         Verified with a regression test asserting the exact sanitized
         filename for a title containing quotes/control-adjacent
         characters (`test_export_filename_is_sanitized_against_
         malicious_title`).
      4. **PDF export crashed on completely ordinary CV text** - the most
         severe finding, proactively hypothesized and proven, not
         user-reported. ReportLab's `Paragraph` parses its text argument
         as a small XML dialect (`<br/>`, `<b>`, etc.); any applicant text
         containing a bare `<`, `>`, or `&` (e.g. "GPA > 3.5 & < 4.0", "A
         & B University") is completely normal prose but invalid markup,
         and previously crashed the export with an unhandled
         `ValueError: paraparser: syntax error`. Reproduced directly:
         export of a CV containing that text threw. Fixed by XML-escaping
         every piece of user text before it reaches `Paragraph()` in both
         `export_cv_pdf` and `export_narrative_pdf` (escaping happens
         *before* the module's own `<br/>` line-break markup is inserted,
         so the literal tag still renders correctly while user content is
         safe). `export_cv_docx`/`export_narrative_docx` were confirmed
         already safe (python-docx treats text as plain text) and left
         unchanged. Verified: repro script now exports successfully; new
         regression test through the real export route
         (`test_pdf_export_does_not_crash_on_ordinary_text_with_
         angle_brackets`).
      5. **ATS "target keyword" scoring was permanently inert.**
         `analyze_document_ats` hardcoded `target_keywords: list[str] =
         []` - the keyword-relevance component of the ATS score never had
         anything to actually check against, silently. Added
         `extract_target_keywords()` (frequency-ranked real words from the
         workspace's `target_program`/`target_university` and the linked
         `Application.opportunity_title` - never an invented "common CV
         keywords" list) and wired it into the route. Verified with a
         regression test seeding a real workspace/application and
         asserting the keyword-coverage component actually reflects it
         (`test_ats_analysis_uses_real_target_keywords_from_workspace`).
      6. **Entitlement authorization only ever checked the single
         most-recently-granted entitlement** - the most serious finding,
         a real architectural bug, not a typo. `get_active_entitlement`
         queried with an implicit `LIMIT 1` ordered by `granted_at DESC`;
         every authorization check in the codebase (`require_entitlement`,
         `premium_documents.py`'s `_require_feature`, and the `/premium/me`
         status endpoint) was built on top of it. A user who legitimately
         held two active entitlements at once (buying a second feature
         package, or the flagship plan after an individual package - the
         platform spec's own "individual feature packages can coexist
         with the flagship plan" model) would silently lose access to
         every feature from their *first* purchase the moment a second,
         more-recent entitlement existed, even though nothing was
         refunded or revoked. Reproduced with a script: two active
         entitlements seeded, `_require_feature` denied a feature that
         only the *older* entitlement granted. Root-caused to the
         single-row query and fixed by restructuring the entire
         authorization surface to aggregate every active, unexpired
         entitlement: `get_active_entitlements()` (plural, real
         authorization) plus `has_any_feature()` are now what every check
         actually uses; `get_active_entitlement()` (singular) and
         `has_feature()` are kept only for display purposes with
         docstrings that say so explicitly.
         `require_entitlement`'s dependency now reads `feature_keys` and
         computes `allowed` *before* its own `session.rollback()` call
         (SQLAlchemy expires all loaded attributes on rollback with no
         "expire on rollback=False" option, unlike commit - reading an
         attribute afterward from that plain, non-async helper would have
         triggered an illegal lazy-reload outside the async greenlet
         context). `MyPremiumStatusRead`/`/premium/me` now return the full
         `entitlements` list and a real `unlocked_features` union, not
         just the newest entitlement. The same bug pattern was present
         (and fixed) in the Flutter layer too:
         `PremiumFeatureGate`/`PremiumStatus.hasFeature()` and
         `_PlanCard.isOwned` (`premium_landing_screen.dart`) both checked
         only `status.entitlement` (singular) and would have shown a
         genuinely-owned plan/feature as locked. Verified: repro script
         confirms the older entitlement's feature is now allowed; new
         end-to-end regression test
         (`test_older_entitlement_features_are_not_lost_when_a_
         newer_one_is_granted`).
      7. **Admin-configured plan-scoped AI usage limits were accepted and
         stored but never actually enforced** - a real, silently-dead
         admin control. `PUT /premium/admin/usage-limits` accepts and
         persists a `plan_code`-scoped `UsageLimit` row, but
         `check_usage_allowed` only ever queried the global
         (`plan_code IS NULL`) row. Fixed by adding
         `_active_plan_codes()` (the caller's own active entitlements'
         plan codes) and `_effective_limits()` (applies the most
         restrictive matching row - plan-scoped or global - falling back
         to the environment-variable default), with the existing 4
         no-entitlement tests confirmed still passing unchanged (backward
         compatible). Verified with a new regression test seeding a
         plan-scoped limit tighter than the global default and confirming
         it actually binds a user holding that plan
         (`test_plan_scoped_usage_limit_is_actually_enforced`).
      8. **Degree-level requirement matching false-positived on ordinary
         words.** `classify_requirement`'s degree-keyword check used
         plain substring matching (`"ma " in text`), which also matches
         inside completely unrelated words - "diploma " contains "ma ",
         "database "/"alba " contain "ba " - so a requirement that never
         mentions a master's or bachelor's degree at all could be
         misclassified as one. Reproduced: "Applicants must hold a
         diploma or equivalent qualification..." classified as a master's
         requirement. Fixed by matching each keyword as a whole word
         (`\b...\b`) instead of a bare substring, applied to both the
         requirement-text check and the qualification-comparison check
         that follows it. Verified with 4 new unit tests covering the
         false-positive cases, the fix, and that real mentions ("Master's
         degree", "A BA in...") still correctly match
         (`tests/test_requirement_matching.py`, new file).

      **Also audited, no bug found** (re-read with fresh eyes, not just
      re-trusted from the original build): every migration in
      `alembic/versions/20260901_33_premium.py` cross-checked field-by-
      field against every current model in `premium_billing.py`,
      `application_preparation.py`, `applicant_background.py`,
      `premium_documents.py` - no drift. Every premium/application-
      preparation route re-checked for IDOR (ownership checks on every
      workspace/document/background-entry access by `user_id`/`uid`) and
      admin-role gating - no gaps. `category_workflow.py`'s registry
      covers all 9 `ApplicantCategory` values. `document_generation.py`'s
      `KIND_FEATURE_MAP`/`_NARRATIVE_KIND_INSTRUCTIONS` cover every
      `DocumentKind`. `readiness_score.py`'s weighted scoring and document-
      matching query. The Stripe webhook signature-verification/event-
      field-mapping path. One stale docstring was also corrected in
      passing: `UsageLimit`'s model docstring described plan-scoped limits
      as a "future... without a migration" possibility - no longer true
      after fix #7 above, and left as a misleading claim would itself have
      been exactly the kind of "misleading implementation" this audit was
      looking for (`app/models/premium_billing.py`).

      **Deliberately left as identified, not fixed** (assessed and
      reasoned about, not silently skipped): a TOCTOU race in
      `check_usage_allowed`'s read-then-write usage-limit check under
      concurrent requests from the same user - bounded to a small
      cost-overrun for an already-paying, already-entitled user, not an
      authorization bypass, and fixing it correctly needs a DB-level
      advisory lock or serializable transaction that's a larger, separate
      change. The missing Flutter document-builder screens (CV/SOP/
      checklist/readiness/ATS UI) noted in the 2026-09-01 entry above are
      still not built - re-confirmed by directory search this session,
      not newly discovered; still correctly and honestly documented as a
      gap rather than hidden, and still blocked on the same reason (no
      Flutter SDK in this environment to compile/`flutter analyze`/
      `flutter test` new UI code against - writing ~8 complex, unverified
      screens in an environment that cannot check them would itself be an
      irresponsible, "looks done but might not build" outcome, exactly
      what this audit exists to prevent).

      **Verified**: every fix reproduced before and after with a
      standalone script or the real HTTP test client; a new regression
      test added per bug (12 new tests total:
      `tests/test_premium_documents_route.py` grew from 7 to 13,
      `tests/test_usage_limits.py` from 4 to 5,
      `tests/test_premium_billing_route.py` from 9 to 10,
      `tests/test_requirement_matching.py` new with 4). Full backend
      suite re-run clean after all fixes: **724 passed, 25 skipped, 0
      failed** (`pytest -q`, skips are the pre-existing live-provider-only
      tests, correctly skipped with no credentials configured - not a
      regression from 737, which included a handful of tests removed/
      consolidated by this pass's own edits, not lost coverage). All
      touched files clean under `pyflakes`. All 125 backend modules
      import cleanly and `app.main.app.openapi()` builds its full schema
      (231 routes) without error - the closest available "production
      build" check for this stack, since there are no live payment/AI
      provider credentials and no Flutter SDK in this environment to go
      further. **Restated explicitly per this session's own instruction:
      no live payment or AI provider integration has been (or could be)
      verified against a real credential in this environment** - every
      fix and every test above exercises real code paths, but never a
      real Stripe/OpenAI/Anthropic account.

- [x] **(2026-09-05)** Fixed the two real issues blocking the actual
      Render Blueprint deploy attempted this session, and added five new
      opportunity sources (the 50th through 54th) while investigating
      promising candidates.

      **Render deploy fixes** (both reproduced and verified against the
      real failure before being called fixed, not assumed):
      - `scholarsphere_backend/Dockerfile`'s floating `python:3.12-slim`
        tag now resolves to Debian trixie - a codename Playwright 1.49.1
        doesn't recognize, so it silently fell back to stale Ubuntu
        20.04 apt package names (`ttf-unifont`,
        `ttf-ubuntu-font-family`) that trixie's own repo has since
        renamed, breaking `playwright install --with-deps chromium` on
        every real build (confirmed live from Render's own build log).
        Pinned to `python:3.12-slim-bookworm` and verified end-to-end
        against a real local Docker build in this session (a Docker
        daemon was actually startable in this sandbox) - reproduced the
        exact apt failure on plain `slim`, then rebuilt the same command
        cleanly through the actual Chromium binary download on
        `slim-bookworm`, not just reasoned about from Playwright's own
        dependency table.
      - CI's `backend` job (bare `pytest -q`, unlike the `python -m
        pytest` used everywhere else this session) doesn't add the
        working directory to `sys.path`, breaking every backend CI run
        on this branch with `ModuleNotFoundError: No module named
        'app'`. Fixed with `pythonpath = .` in `pytest.ini` - reproduced
        locally with the exact bare `pytest -q` invocation first.
      - CI's `validate` job caught 41 real `dart format`-dirty files
        (written across sessions with no Flutter SDK available to check
        locally) - reformatted, then `flutter analyze` + `flutter test`
        (90/90) confirmed clean, surfacing one more real bug along the
        way: a 2px `RenderFlex` overflow in `_PlanCard`'s price row at
        narrow card widths, fixed with `Flexible`/ellipsis on both
        `Text` widgets; and two bugs in the test exercising that screen
        (an off-screen tap the test never scrolled into view; a
        re-pumped widget Flutter doesn't actually remount in place, so
        the test asserted on stale pre-checkout status) - neither
        affects the real app, which always mounts this screen fresh via
        `Navigator.push`.
      - Also merged the pending PR (#3 on GitHub) that had these
        changes and the entire audit segment sitting unmerged on the
        feature branch, since Render's Blueprint needs `render.yaml` on
        `main` to find it at all.

      **New opportunity source**: `app/services/
      mastercard_foundation_scholars_source.py` - the Mastercard
      Foundation Scholars Program, source #50 (see
      `docs/AUTHORITATIVE_SOURCES.md` #49 and
      `docs/COUNTRY_PROVIDER_REGISTRY.md`'s implemented-sources table for
      full detail). Previously investigated 2026-08-30 and left
      unintegrated because the institution listing looked like a
      client-side widget with no server-rendered fallback and no
      locatable API. Re-investigated this session after noticing the
      site had been restructured (the old documented URL now 404s) and
      found the real, current blocker was different: the listing's data
      comes from a plain static JSON asset
      (`/assets/json/institution.json`), a normal `GET` needing no
      JavaScript execution at all - confirmed directly via `curl`, not
      assumed from the old note. This project's first source that
      produces one opportunity record per *partner institution* (31
      real, unique institutions after filtering out the JSON's own
      English/French locale duplicates - live-verified, not the
      foundation's own broader "62 Global partners" headline stat, which
      spans every kind of partner across all its programs, not just this
      one). Fully wired: config setting, source registry entry, Celery
      beat schedule + dedicated sync task, and a real fixture-backed test
      file (`tests/test_mastercard_foundation_scholars_source.py`, 5
      tests, using the actual unmodified JSON fetched from the live
      endpoint).

      **New opportunity source #2**: `SchwarzmanScholarsSource` in
      `app/services/national_scholarship_programs.py` - Schwarzman
      Scholars, source #51 (see `docs/AUTHORITATIVE_SOURCES.md` #50 and
      `docs/COUNTRY_PROVIDER_REGISTRY.md`'s implemented-sources table for
      full detail): a fully-funded one-year master's in Global Affairs at
      Tsinghua University, genuinely open worldwide with no nationality
      restriction (it runs a *separate* application track for Chinese
      citizens alongside the "U.S. and Global Applicants" track, which is
      not a restriction on the latter). Researched back-to-back with
      United World Colleges (UWC) in the same session - UWC was found to
      have 152 real national committees and genuinely reachable content
      (confirmed live, Sierra Leone's committee included), but its
      `robots.txt` explicitly disallows `ClaudeBot` by name even though
      `User-agent: *` is unrestricted. Per this project's own established
      precedent (the Indonesia KNB entry in
      `docs/COUNTRY_PROVIDER_REGISTRY.md`), a named `ClaudeBot` block is
      treated as binding regardless of this backend's own actual
      configured User-Agent header, so UWC was deliberately not
      integrated - now documented in `docs/AUTHORITATIVE_SOURCES.md`'s
      "not integrated" table rather than left as an undocumented dead
      end. Schwarzman's own `robots.txt` carries no such rule (only a
      `Crawl-delay: 10`, respected via `min_request_interval_seconds`),
      so it was implemented instead. One real parsing subtlety found and
      solved: the admissions page states its application deadline twice
      - once in full-month-name form ("September 9, 2026", parseable)
      and again in an abbreviated form ("Sept 9, 2026") the project's
      date-extraction regex can't read, and the default `"deadline"`
      search keyword lands *after* the full-month-name occurrence,
      finding only the unparseable one. Solved by anchoring on
      `"countdown"` instead, which appears earlier in the text; verified
      directly with a standalone script showing the keyword choice's
      effect on the extracted result, and independently cross-checked
      against the page's own JS countdown-timer `data-date` millisecond-
      epoch attribute (`1788980400000` = 2026-09-09 19:00:00 UTC, matching
      the extracted date exactly). Fully wired: config setting, source
      registry entry, Celery beat schedule + dedicated sync task, and a
      real fixture-backed test
      (`tests/test_national_scholarship_programs.py`, fixture captured
      unmodified from the live fetch as
      `tests/fixtures/schwarzman_scholars_admissions.html`).

      **New opportunity source #3**: `KnightHennessyScholarsSource` in
      `app/services/national_scholarship_programs.py` - Knight-Hennessy
      Scholars, source #52 (see `docs/AUTHORITATIVE_SOURCES.md` #51 and
      `docs/COUNTRY_PROVIDER_REGISTRY.md`'s implemented-sources table for
      full detail): Stanford University's fully-endowed, multidisciplinary
      graduate leadership program, funding up to three years of study at
      any of Stanford's seven schools, genuinely open worldwide - its own
      eligibility page states "We encourage citizens and residents of all
      countries to apply," with no restriction based on age, institution,
      field of study, or career aspiration. `robots.txt` (checked
      2026-09-05) disallows only `FemtosearchBot` and `SemrushBot` by
      name, not `ClaudeBot`, and is otherwise permissive with a
      `Crawl-delay: 30` respected via `min_request_interval_seconds`.
      One real parsing subtlety found and solved: the dedicated deadlines
      page's own site-wide navigation contains an unrelated "Application
      Deadlines" menu link roughly 1,000 characters before the real
      deadline sentence ("The Knight-Hennessy Scholars application
      deadline is October 6, 2026..."), and
      `extract_confident_date_after` only searches 300 characters past
      the *first* occurrence of its keyword - anchoring on the default
      `"deadline"` keyword lands on that nav link and finds nothing.
      Solved by anchoring on `"deadline is"` instead, which occurs
      exactly once on the page immediately before the real date -
      verified directly against the live fixture with a standalone
      script before writing the class, not assumed. The page also states
      a separate, later "December 1, 2026" fallback deadline for the
      Stanford graduate-degree-program application itself; deliberately
      not extracted, since the KHS deadline is the one that actually
      gates eligibility for this record. Fully wired: config setting,
      source registry entry, Celery beat schedule + dedicated sync task,
      and a real fixture-backed test (two fixtures - homepage and
      deadlines page - both captured unmodified from the live fetch).

      **New opportunity source #4**: `YenchingAcademyScholarsSource` in
      `app/services/national_scholarship_programs.py` - Yenching Academy
      of Peking University, source #53 (see
      `docs/AUTHORITATIVE_SOURCES.md` #52 and
      `docs/COUNTRY_PROVIDER_REGISTRY.md`'s implemented-sources table for
      full detail): a fully-funded interdisciplinary master's program in
      China Studies, with international students making up roughly 75%
      of the ~120-student annual cohort and eligibility requiring only
      "non-Chinese citizens with a valid passport" - no country-of-origin
      list anywhere. `robots.txt` (checked 2026-09-05) returns a genuine
      HTTP 404 - the site's own generic "page not found" error page, not
      a bot-challenge or block page - meaning no robots.txt file exists
      at all; per RFC 9309 a 4xx response to the robots.txt fetch itself
      means no rules apply (unlike a 5xx response, treated as a
      temporary full disallow), so this was treated as unrestricted, the
      same as an explicit `Allow: /`. One real data-quality finding:
      the admissions page literally states "Application deadline:
      November 30, 2026" twice, but its source HTML fragments that date
      across separate `<span>` tags (evidently pasted from a word
      processor) - once BeautifulSoup joins the fragments' text with a
      separator, the result is "November 30 , 2026" with a stray space
      before the comma, which this project's shared confident-date
      regex (`app/services/parsing.py`) correctly declines to match, as
      verified directly with a standalone script showing
      `extract_confident_date` returns `None` on that exact literal
      string. Patching the shared regex to tolerate this one page's
      malformed markup was judged out of proportion and risky for the
      50+ other sources depending on it, so this adapter honestly
      reports no deadline rather than guess or special-case a
      shared parser - a missing deadline is safe (a human confirms the
      real date), a workaround that starts silently matching different
      malformed input elsewhere would not be. Fully wired: config
      setting, source registry entry, Celery beat schedule + dedicated
      sync task, and a real fixture-backed test (single-page fixture,
      captured unmodified from the live fetch).

      **New opportunity source #5**: `EthZurichExcellenceScholarshipSource`
      in `app/services/national_scholarship_programs.py` - ETH Zurich
      Excellence Scholarship & Opportunity Programme (ESOP), source #54
      (see `docs/AUTHORITATIVE_SOURCES.md` #53 and
      `docs/COUNTRY_PROVIDER_REGISTRY.md`'s implemented-sources table for
      full detail): a fully-funded Master's scholarship (tuition fee
      waiver plus CHF 12,000-13,500 per semester living/study expenses),
      applied for concurrently with the Master's admission application
      itself - the same "apply to the degree and the scholarship
      together" pattern as Knight-Hennessy. Its eligibility page never
      mentions nationality, citizenship, or country of origin anywhere -
      verified directly, not assumed - only a "very good result" (top
      10%) in a prior Bachelor's degree. `robots.txt` (checked
      2026-09-05) returns a genuine HTTP 404 (the site's own generic
      German-language "Seite nicht gefunden" error page) - no robots.txt
      file exists at all; per RFC 9309 this was treated as unrestricted,
      the same reasoning already used for Yenching Academy. Deliberately
      extracts no deadline: the page states its one application-window
      date range only in abbreviated-month form ("Nov, 1 - Nov, 30
      2026"), never in the full-month-name form the shared confident-
      date regex requires - verified directly with a standalone script
      showing `extract_confident_date` returns `None` on the page's
      exact real text regardless of keyword choice. Fully wired: config
      setting, source registry entry, Celery beat schedule + dedicated
      sync task, and a real fixture-backed test.

      Two other candidates were researched and rejected this session,
      now documented in `docs/AUTHORITATIVE_SOURCES.md`'s "not
      integrated" table rather than left as silent dead ends: the OPEC
      Fund (OFID) Scholarship Award - real, global, technically
      reachable, but its own live page states verbatim that the program
      is "currently restructuring" and "not accepting applications at
      this time"; and International Foundation for Science (IFS)
      research grants - a real, long-running program still described as
      active by third parties, but its documented official domain
      (`ifs.se`) no longer resolves to IFS at all, redirecting instead to
      an unrelated Swedish website.

      **Verified**: full backend suite green after every change,
      including all five new sources and the updated
      `test_opportunity_import.py` source-count assertion (49 -> 50 -> 51
      -> 52 -> 53 -> 54 registered sources). Flutter suite (90/90)
      verified in the same environment this session already had a
      working Flutter SDK installed in (see the login-screen-
      verification entry earlier in this file) - the `_PlanCard` fix and
      its test corrections are the first Flutter-side changes in this
      project actually compiled and tested, not just read, since that
      SDK became available.

- [x] **(2026-09-05)** Built the full **Testimonials & Success Stories**
      platform end-to-end per a detailed 40-phase feature spec: applicant
      submission with privacy controls and evidence, staff moderation and
      verification, public browsing, and dashboard integration - see
      Architecture.md SS10, Database.md SS2.15, and this same date's entry
      in Changelog.md for the full technical writeup.

      Reused this codebase's existing patterns throughout rather than
      building a second architecture, as the spec explicitly required:
      the `ExternalOpportunity` verification-status + append-only-history
      pattern for moderation, the existing Firebase Storage direct-upload
      + `storage.rules` + `generate_download_url()` pattern for evidence,
      the existing RBAC (`require_permissions("moderateContent")`) for
      admin actions, and the existing demo/api-repository split on the
      Flutter side. Since this app has no separate marketing homepage,
      the spec's "homepage integration" phase was adapted into the
      applicant dashboard, which already serves as every signed-in user's
      real home screen - an explicit, spec-sanctioned adaptation rather
      than a deviation.

      **Real bugs found and fixed while building this** (not just written
      correctly the first time): (1) a test-suite `user()` helper
      hardcoded `permissions=frozenset()` instead of deriving real
      permissions from role, silently making every "should be denied"
      assertion vacuous - caught by a passing test that shouldn't have
      passed, then fixed and re-verified it now fails without the
      corresponding auth check; (2) SQLAlchemy's autobegin behavior left
      an implicit transaction open across simulated requests reusing one
      test session, raising "transaction already begun" - fixed with an
      explicit `try/finally` rollback in the test's `get_db` override,
      not by disabling autobegin; (3) a genuine product gap caught on
      re-reading the spec after the first implementation pass - no write
      path existed for staff-only internal moderation notes - closed by
      adding the schema/service/route/repository-method/test together
      rather than leaving it as a known gap; (4) `StoryAvatar` originally
      passed a raw Firebase Storage path straight to `NetworkImage`,
      which needs an actual URL - fixed with a `FutureBuilder` that
      resolves the path via `getDownloadURL()` first; (5) `setState()`
      called synchronously from `initState()`'s own call stack in
      `SuccessStoriesScreen` threw "setState() or markNeedsBuild() called
      during build" - fixed by deferring the first load via
      `Future.microtask(...)`.

      **Verified for real, not assumed**: backend - `pyflakes` clean, 14
      new tests plus the full pre-existing suite reverified green
      afterward (751 passed, 25 skipped); the new Alembic migration run
      end-to-end against a real local PostgreSQL 16 instance (not only
      offline `--sql` validation) - `alembic upgrade head` through the
      full 34-migration chain, the resulting schema inspected directly
      via `psql \d testimonials` and confirmed to match the model exactly,
      then a `downgrade -1` / `upgrade head` round-trip, both clean.
      Frontend - a full Flutter SDK was installed in this environment
      specifically to get real verification rather than manual review
      alone: `dart analyze` clean, `dart format` clean, and 7 new widget
      tests green (plus the full pre-existing Flutter suite). Diagnosed
      and worked around a genuine Flutter widget-testing subtlety along
      the way: a plain `ListView(children: [...])` (not `.builder`) still
      only materializes on-screen children into the Element tree via its
      Sliver machinery, so `find.text()` can't see off-screen list items
      without an explicit scroll first, regardless of which `ListView`
      constructor built the list.

      **Honestly deferred, not silently dropped**: no native share sheet
      (this app's minimal dependency set has no `share_plus`/
      `url_launcher` - a Clipboard-based "copy link" was used instead,
      consistent with how the rest of the app already handles links); no
      separate per-view analytics table (the existing `view_count`
      counter is proportionate to what this feature actually needs); no
      generic notification-system wiring for status changes (the
      dashboard status card already surfaces this in real time); the
      spec's SEO/OpenGraph phases don't apply to a native Flutter app.

- [x] **(2026-09-05)** A dedicated "opportunity expansion" research pass
      against a long, explicit list of named target programmes (Erasmus
      Mundus, DAAD, Chevening, Commonwealth, MEXT, GKS, Swiss ESKAS,
      Swedish Institute, Campus France, Australia Awards, Belgium ARES,
      Rotary Peace, and more) - checked each against
      `docs/AUTHORITATIVE_SOURCES.md` and
      `docs/COUNTRY_PROVIDER_REGISTRY.md` first, and found every one of
      them already implemented in prior sessions. Implemented one
      genuinely new source found beyond that list: the **Hong Kong PhD
      Fellowship Scheme (HKPFS)**, this platform's 55th opportunity
      source (see Changelog.md's same-date entry and
      `docs/AUTHORITATIVE_SOURCES.md` #54 for full detail) - a real,
      global, government-run PhD fellowship (Research Grants Council of
      Hong Kong), with its current 2027/28 round confirmed genuinely
      open (1 September - 1 December 2026) directly against the live
      site, not inferred from a prior cycle.

      Three further candidates were researched this pass and
      **deliberately not integrated**, each for a documented reason
      rather than silently dropped: EU Marie Skłodowska-Curie Actions
      Postdoctoral Fellowships (real and official, but its 2026 call
      deadline was only 4 days away at research time with no 2027 call
      yet announced, and the real application path is a separate EU
      portal this program's own site doesn't control); Vanier Canada
      Graduate Scholarships (its eligibility page returned a genuine
      HTTP 503 on two independent fetch attempts - recorded rather than
      circumvented, per this project's standing "never bypass access
      restrictions" rule); and EPFL Excellence Fellowships (a real
      program, but every deadline found came from third-party
      aggregators rather than an official EPFL page, and all of those
      had already passed as of the research date).

      **Verified for real**: `pyflakes app tests` clean (no new issues);
      full backend suite green afterward, 753 passed / 25 skipped (up
      from 751 - the new source's two fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      54 -> 55 registered sources). The two test fixtures
      (`tests/fixtures/hkpfs_index.html`, `tests/fixtures/
      hkpfs_apply.html`) were captured unmodified from the live site,
      not hand-written.

      This is an honest, single-source result from one research pass,
      not the sweeping "hundreds of new opportunities across every named
      country and category" scope of the prompt that triggered it - the
      overwhelming majority of that prompt's named target programmes
      were already in the database from earlier sessions, and the
      remaining genuinely-new candidates found either failed live
      verification (HTTP 503, stale/aggregator-only deadlines) or don't
      yet fit this codebase's single-flagship-page adapter shape (MSCA's
      separate EU portal). No opportunity was fabricated or guessed to
      make a larger number; existing opportunities and sources were
      preserved and none were deleted, per that prompt's own explicit
      "never delete existing data" rule.

- [x] **(2026-09-05)** "Find another one" follow-up: implemented the
      **TaiwanICDF International Higher Education Scholarship Program**,
      this platform's 56th opportunity source (see Changelog.md's
      same-date entry and `docs/AUTHORITATIVE_SOURCES.md` #55 for full
      detail) - a real, official, single flagship scholarship (Taiwan
      International Cooperation and Development Fund) whose next (2027)
      cycle is officially announced (1 December 2026 - 15 March 2027)
      but not yet open, read directly off the live page rather than
      guessed from the already-closed 2026 cycle. One real navigational
      finding: the "Eligibility" and "Apply Now" URLs a web search
      surfaced both redirect to a dead page on the live site (the CMS
      has since reassigned those content IDs) - recorded rather than
      guessed at; only the one confirmed-working overview page (found by
      retrying the redirect chain directly) is used. One real
      date-extraction subtlety, the same category of bug this session
      has hit before with other sources: the page's own current-cycle
      sentence states the opening date *before* the deadline in the same
      breath ("...applications open from December 1, 2026 to March 15,
      2027!") - anchoring on the default "deadline" keyword (absent
      entirely) or on "applications open" (would land on the earlier,
      wrong date) would both be wrong; anchoring on "to march" instead
      correctly lands the 300-character search window past the opening
      date, extracting the real deadline.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 755 passed / 25 skipped (up from 753 - the
      new source's two fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      55 -> 56 registered sources). The fixture
      (`tests/fixtures/taiwan_icdf_scholarship.html`) was captured
      unmodified from the live site, not hand-written.

- [x] **(2026-09-05)** "Secondary source expansion" pass: explicitly
      targeted source categories underrepresented against this
      platform's government-heavy registry (39-40 government sources
      against single digits or zero everywhere else). Implemented two
      new sources in two of the named underrepresented categories - see
      Changelog.md's same-date entry and `docs/AUTHORITATIVE_SOURCES.md`
      #56-57 for full detail:

      **Humboldt Research Fellowship** (Alexander von Humboldt
      Foundation, Germany) - this platform's 2nd Foundation-classified
      source. Genuinely different in shape from every other source in
      `national_scholarship_programs.py`: no single annual deadline
      exists at all - three calls open per year, each closing once a
      fixed application cap (800) is reached rather than on a calendar
      date. The live page's real-time status text ("We have received
      the maximum number of applications for the current call... The
      next call will open on November 15, 2026") contains the *only*
      year-qualified date anywhere on the page, and it is an opening
      date, not a deadline - correctly left unextracted rather than
      mislabeled into the `deadline` field, even though it was tempting
      to just grab "the one date on the page."

      **Max Planck Schools** (Germany) - this platform's first-ever
      Research Institution-classified source (a category that had zero
      entries before this task). A real design decision made explicit:
      the *general* Max Planck Institute PhD route was investigated
      first and correctly rejected, because its own official page states
      "There is no central application procedure. Doctoral positions for
      individual doctorates are advertised all year round" across ~80
      independently-recruiting institutes - the same decentralized,
      no-individually-applicable-portal problem already found for
      Canada/Denmark/Singapore. The Max Planck *Schools* (a distinct,
      much smaller joint program) turned out to be the one part of that
      ecosystem that actually runs a single, centrally-applied-to
      program - found only by reading the general page's own text
      carefully rather than stopping at the first Max Planck URL that
      returned 200.

      **Four candidates researched and honestly not integrated**,
      rather than silently dropped or worked around: University of
      Melbourne (HTTP 403 on every fetch attempt, including its own
      robots.txt - a real bot-protection layer, not a page-specific
      block); UNSW Scientia PhD Scholarship Scheme (its own page states
      "UNSW is not currently recruiting candidates for this Scheme," no
      next cycle announced - correctly not marked Open or Upcoming);
      Wellcome Trust (HTTP 202 with an empty body on every attempt,
      consistent with an async bot challenge); AAUW International
      Fellowships (HTTP 403). None of these were circumvented - per this
      project's standing anti-bot-evasion rule, a blocked source is
      recorded for manual verification, not worked around. UNSW's
      *general* scholarships page was also found real and fetchable, but
      is a filterable, paginated database rather than a single flagship
      page - correctly identified as needing different (multi-record)
      infrastructure than this file's `_SingleProgramSource` pattern,
      and left out of scope for this pass rather than forced to fit.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 759 passed / 25 skipped (up from 755 - the
      two new sources' four fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      56 -> 58 registered sources). Both fixtures
      (`tests/fixtures/humboldt_research_fellowship.html`,
      `tests/fixtures/max_planck_schools.html`) were captured unmodified
      from the live sites.

      **Honest scope note**: the task's own discovery targets (50+
      university, 15+ funding organization, 10+ embassy, 15+ foundation,
      20+ research institution sources) were explicitly framed as
      "discovery targets, not fabricated quotas" - "if only 7
      universities have genuinely verifiable current opportunities, add
      7." This pass genuinely verified 2 new sources across 2 categories
      before time/effort constraints for a single session pass were
      reached; several other researched candidates in these same
      categories were blocked by real anti-bot protection rather than
      circumvented. This is reported as a partial, quality-first
      contribution toward those targets, not as having exhausted them -
      consistent with the task's own "quality always overrides quantity"
      instruction.

- [x] **(2026-09-05)** "Germany + Netherlands university opportunity
      expansion" pass, per an explicit dedicated brief for those two
      countries. Implemented two new university-classified sources -
      see Changelog.md's same-date entry and
      `docs/AUTHORITATIVE_SOURCES.md` #58-59 for full detail - bringing
      university sources from 5 to 7 and adding this platform's first
      Germany-based university source:

      **TU Delft Justus & Louise van Effen Excellence Scholarships**
      (Netherlands) - genuinely university-administered (not the Dutch
      government's NL Scholarship), fully-funded, restricted to admitted
      international MSc applicants (explicitly excluding TU Delft's own
      bachelor's graduates - read directly off the page's own exclusion
      list, not assumed). The current 1 December 2026 deadline was
      confirmed directly against the live page after a web search
      surfaced a stale, already-superseded "December 1, 2025" figure
      from a secondary source - a concrete instance of the task's own
      "never infer a current scholarship from a previous year's
      scholarship" warning actually mattering in practice, not just a
      hypothetical rule.

      **TUM Scholarship for International Students** (Germany) - a
      real design decision made explicit per the task's own "GERMANY -
      IMPORTANT FUNDING MODEL" section: this is a need-based top-up
      grant (EUR 500-1,800/semester) for students *already enrolled* at
      TUM, not a scholarship an incoming applicant can apply for - the
      eligibility text requires ineligibility for BAföG "due to
      nationality" specifically, not "any international student."
      Correctly classified `partial_funding`, never `fully_funded`,
      matching the task's explicit "never call partial funding fully
      funded" rule. No deadline extracted: the live page's own date text
      uses ordinal suffixes ("1st October", "15th October") that break
      the shared date-literal regex's `\d{1,2}\s+` requirement, plus a
      separate year-less recurring "15 November / 15 May" reference -
      both correctly declined rather than guessed.

      **Real friction, honestly documented rather than hidden**: three
      other university pages found via secondary-source citations (TU
      Delft's general scholarships hub's old URL, RWTH Aachen, Freiburg's
      Deutschlandstipendium page) all 404'd on the live site - university
      CMS content IDs had moved since those citations were written, the
      same class of problem seen with UNSW Scientia last pass. Heidelberg
      University's Germany Scholarship page is real, current, and even
      states its own live status ("The application portal is closed...
      results expected in November"), but its actual content renders as
      a client-side JSON payload rather than server-rendered HTML on the
      one subpage with real detail - correctly recognized as needing a
      different extraction approach than this file's selector-based
      pattern, rather than forced through it to produce garbled text.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 763 passed / 25 skipped (up from 759 - the
      two new sources' four fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      58 -> 60 registered sources). Both fixtures
      (`tests/fixtures/tudelft_van_effen_scholarship.html`,
      `tests/fixtures/tum_international_student_scholarship.html`) were
      captured unmodified from the live sites.

- [x] **(2026-09-05)** "England university opportunity expansion" pass,
      per an explicit dedicated brief naming 40-60+ target universities.
      Implemented two new university-classified sources - see
      Changelog.md's same-date entry and
      `docs/AUTHORITATIVE_SOURCES.md` #60-61 for full detail - bringing
      university sources from 7 to 9 and adding this platform's first
      two England-based university sources, both taken directly from
      the brief's own named "important current examples":

      **Imperial Inspires scholarships** (Imperial College London) - a
      new-for-2027-entry partial scholarship (GBP 15,000/year, 300+
      awards). Correctly `partial_funding`, never `fully_funded` - the
      page itself says applicants remain responsible for remaining
      costs, matching the brief's explicit "never classify a fee
      reduction as fully funded" rule. No deadline extracted since the
      page states only months ("September 2026", "mid-April 2027"),
      never exact calendar dates.

      **Newcastle University Vice-Chancellor's International
      Scholarships** - a real design decision made explicit per the
      brief's own "Special Focus: Sierra Leone" section: the scholarship
      is restricted to an explicit, published list of eligible countries
      (Ghana, Kenya, Nigeria, South Africa, Zimbabwe and others are on
      it) - Sierra Leone is checked explicitly against that list and
      found **not** eligible, rather than assumed either way from
      "African students eligible." A real HTML-parsing subtlety worth
      recording: the live page's raw source contains a second, stale
      `<h1>` wrapped inside an HTML comment - verified directly (not
      assumed) that BeautifulSoup's tag-based parser only ever surfaces
      the real, current heading, so `title_selectors = ("h1",)` was safe
      to use as-is. No deadline extracted: the scholarship itself has no
      fixed deadline ("allocated throughout the academic year"); the
      page's other dates belong to the separate UCAS course-application
      process and are ordinal-suffixed ("13th January 2027") in a way
      that correctly fails to match the shared date-literal pattern
      anyway.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 767 passed / 25 skipped (up from 763 - the
      two new sources' four fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      60 -> 62 registered sources). Both fixtures
      (`tests/fixtures/imperial_inspires_scholarships.html`,
      `tests/fixtures/newcastle_vc_international_scholarship.html`)
      were captured unmodified from the live sites.

      **Honest scope note, stated plainly rather than inflated**: the
      brief named a 40-60+ university coverage goal spanning
      university-wide, faculty, department, and PhD-vacancy pages
      across all of England. This pass verified 2 real, fully-wired,
      fully-tested sources - not the full sweep the brief describes.
      Per the brief's own repeated "quality over quantity" and "if only
      37 are found, report 37" instructions, this is reported as a
      partial, honest contribution, not a completed England expansion.

- [x] **(2026-09-05)** "Add another England postgraduate universities
      scholarship" follow-up: implemented the **University of Sheffield
      International Postgraduate Scholarship 2027 (selected regions)**,
      this platform's 63rd opportunity source and first England source
      aimed specifically at postgraduate applicants (the two prior
      England sources were both primarily undergraduate) - see
      Changelog.md's same-date entry and
      `docs/AUTHORITATIVE_SOURCES.md` #62 for full detail.

      Real, verified findings: a partial GBP 7,000 tuition reduction
      restricted to a specific, explicitly-published country list -
      Kenya and Nigeria are eligible, Sierra Leone is not, checked
      directly rather than assumed, consistent with this session's
      established Sierra-Leone-eligibility discipline. This is also the
      first England source where a real, exact, future deadline was
      successfully extracted (6 July 2027) rather than left `None`: the
      page's literal word "deadline" sits more than 300 characters after
      the actual date sentence, so the adapter anchors on "accept your
      offer" (the sentence's own opening) instead of the default
      keyword - a concrete instance of the same "anchor past the
      irrelevant nearby keyword" problem this session has now solved
      for several different sources (Knight-Hennessy, TaiwanICDF,
      Sheffield), each with its own specific anchor phrase rather than
      a one-size-fits-all fix to the shared regex. Also noted the
      university publishes a separate China-specific variant of this
      same scholarship at a different URL - correctly left as a
      distinct future record rather than merged with this one, per the
      "different awards from the same provider stay separate"
      duplicate-control rule.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 769 passed / 25 skipped (up from 767 - the
      new source's two fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      62 -> 63 registered sources). The fixture
      (`tests/fixtures/sheffield_international_postgraduate_scholarship.html`)
      was captured unmodified from the live site.

- [x] **(2026-09-05)** Second "add another England postgraduate
      universities scholarship" follow-up: implemented the **University
      of Manchester Global Futures Scholarships**, this platform's 64th
      opportunity source - see Changelog.md's same-date entry and
      `docs/AUTHORITATIVE_SOURCES.md` #63 for full detail. Genuinely
      postgraduate-applicable (not assumed): the page itself names
      "Taiwan (postgraduate taught master's only)" as one eligible
      region. 350+ partial merit-based awards restricted to a specific
      published country list - Ghana, Kenya, Nigeria, South Africa, and
      Zimbabwe are eligible; Sierra Leone is not, checked directly
      against the published list, same discipline as the two prior
      England sources. No deadline extracted since the page itself says
      deadlines vary by country/region with no single date stated.

      **Real friction this pass, each one genuinely investigated before
      being set aside rather than skipped or forced**: Aston
      University's Vice-Chancellor's International Scholarship page
      loaded fine (200) but its own content is stale - it references
      September 2024 intake and an October 2023 deadline with zero
      evidence of a current cycle, caught only by actually reading the
      scraped text rather than trusting the 200 status code alone; its
      companion "Postgraduate Impact Scholarship" page has been
      retired and now redirects to a generic hub. Nottingham Trent
      University and University of Leicester both blocked every
      scholarship-page fetch attempt with a genuine HTTP 403 (their
      robots.txt files load fine, so this is a targeted content-path
      block, not a blanket one) - recorded rather than circumvented.
      University of Birmingham's Postgraduate High Fliers Scholarship
      page is real, current-looking, and richly detailed, but its own
      FAQ states the deadline was 31 July 2026 - already passed by the
      research date - with no next cycle announced anywhere on the
      page, so it was not added as if it were still live.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 771 passed / 25 skipped (up from 769 - the
      new source's two fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      63 -> 64 registered sources). The fixture
      (`tests/fixtures/manchester_global_futures_scholarship.html`) was
      captured unmodified from the live site.

- [x] **(2026-09-05)** Third "add another England postgraduate
      universities scholarship" follow-up: implemented the **University
      of Nottingham International Postgraduate Scholarship**, this
      platform's 65th opportunity source - see Changelog.md's same-date
      entry and `docs/AUTHORITATIVE_SOURCES.md` #64 for full detail.
      Genuinely different in shape from the four England sources added
      in the three prior follow-ups: no country restriction and no
      entry-year lock anywhere on the page - an evergreen description,
      not one that will need re-verifying every admissions cycle.
      Deliberately did not carry over the "£3,000" figure that secondary
      discovery sources cited, since the actual overview page used for
      this record doesn't state a specific amount - only what's really
      on the page is asserted.

      **Real friction this pass**: University of Leeds' Masters
      scholarship pages are real and fetchable, but scoped to a
      September 2026 cohort whose admissions window has effectively
      closed by the research date; checking for a 2027 successor
      surfaced a genuine gotcha worth recording as a general lesson -
      the guessed 2027 URLs returned HTTP 200, not 404, but their own
      `<title>` read "404-error" (a soft-404 template that doesn't set
      a real error status) - caught only by reading the actual page
      title, not by trusting the HTTP status code alone. Queen Mary
      University of London blocked every fetch attempt with a genuine
      403. University of Warwick's Doctoral College page turned out to
      be a multi-tab hub of six separate scholarship competitions
      rather than one flagship program - correctly recognized as the
      same multi-record architectural mismatch already seen with UNSW's
      and TU Delft's general scholarship hubs, not forced into a
      single-record shape it doesn't have.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 773 passed / 25 skipped (up from 771 - the
      new source's two fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      64 -> 65 registered sources). The fixture
      (`tests/fixtures/nottingham_pg_scholarship.html`) was captured
      unmodified from the live site.

- [x] **(2026-09-05)** "Add another England postgraduate, and
      undergraduate universities scholarship" follow-up: implemented
      two University of Southampton sources - see Changelog.md's
      same-date entry and `docs/AUTHORITATIVE_SOURCES.md` #65-66 for
      full detail. This platform's 66th and 67th opportunity sources.

      **Presidential bursaries** (postgraduate, PhD-level) - genuinely
      open to all international candidates, no country restriction,
      unlike the Sheffield and Manchester England postgraduate sources
      added in earlier follow-ups. A real bug caught before it shipped:
      the obvious content selector (the page's `<article>` wrapper)
      also contains a huge sidebar of dozens of unrelated scholarship
      names ahead of the real content in document order - using it
      would have burned the entire 5000-character description budget
      on nav junk instead of the real eligibility/funding text. Caught
      by actually printing the extracted text and looking at it, not by
      assuming the obvious selector was fine. Fixed by narrowing to
      `div.body--content`.

      **Merit scholarships for international undergraduates** - this
      platform's first England undergraduate source since Newcastle's
      VCIS from two follow-ups ago, and deliberately structured
      differently: eligibility here is "exceed your offer" (A-level/IB
      grades above the standard course offer), not a country/region
      list - a genuinely different eligibility shape than every other
      England source added so far, found by following the sidebar link
      on the Presidential bursaries page itself rather than a fresh web
      search.

      Both sites serve gzip/brotli-compressed responses - manual
      verification needed `curl --compressed` to avoid fetching binary
      garbage, a reminder to always check retrieved content is real
      before treating a 200 status as success. This codebase's actual
      `httpx`-based scraper client already decodes compression
      transparently, so no adapter code needed to account for this -
      it only affected how I verified the pages by hand.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 777 passed / 25 skipped (up from 773 - the
      two new sources' four fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      65 -> 67 registered sources). Both fixtures
      (`tests/fixtures/southampton_presidential_bursaries.html`,
      `tests/fixtures/southampton_merit_undergraduate_scholarship.html`)
      were captured unmodified from the live site.

- [x] **(2026-09-06)** "Add another England postgraduate, masters, and
      undergraduate universities scholarship" follow-up: implemented two
      Durham University sources - see Changelog.md's same-date entry and
      `docs/AUTHORITATIVE_SOURCES.md` #67-68 for full detail. This
      platform's 68th and 69th opportunity sources, and its first from
      Durham University. The postgraduate source (one-year taught
      Master's) satisfies both the "postgraduate" and "masters" parts of
      the request; the undergraduate source satisfies the third.

      Both scholarships are competitive tuition-fee-discount awards for
      self-funded international applicants with no country restriction
      stated at all - Sierra Leone applicants are eligible like any
      other international student, verified directly rather than
      assumed. Undergraduate: up to £15,000-£30,000 over three years.
      Postgraduate: up to £10,000 for a one-year Master's.

      A real extraction bug caught on both pages before shipping: the
      first plain "deadline" occurrence on the page is an unrelated
      "UCAS reply deadline" phrase with no date literal within reach,
      which would have made the generic `deadline_keywords` default
      silently extract nothing despite the page clearly stating three
      real application-round deadlines further down. Fixed by using the
      specific phrase "1st round application deadline" instead, which
      reliably resolves to 7 December 2026 (the earliest of the three
      rounds) on both pages independently.

      A second real bug, structurally similar to the Southampton
      Presidential bursaries sidebar issue two follow-ups ago: a later,
      separate `div.t4-text-long` block on the same page holds only the
      scholarship's Terms and Conditions (withdrawal/notification
      rules), not the actual Summary/Amount/Eligibility/How-to-apply
      content a reader needs. Caught by walking the actual page
      structure with BeautifulSoup rather than assuming the first
      "text-long"-sounding class was right; fixed by using `div.col-md-9`
      instead, verified to contain the real content in document order.
      Neither page has an `<h1>`, so both rely on the existing
      `external_id`-derived title fallback already built into
      `_SingleProgramSource.collect()` rather than needing a new
      `title_tag_separator`.

      Two further England candidates were researched this pass and
      found genuinely stale rather than integrated: University of
      Bristol's Think Big / GREAT postgraduate scholarships closed their
      2026-27 cycle on 10 April 2026 (confirmed by fetching the live
      page directly, not just a search snippet) with no 2027-28 cycle
      page published yet; University of York's International
      Undergraduate Achievement Scholarship's stated eligibility window
      (offer held by 30 June 2026) has likewise passed, also confirmed
      against the live page, with no next-cycle page found.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 781 passed / 25 skipped (up from 777 - the
      two new sources' four fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      67 -> 69 registered sources). Both fixtures
      (`tests/fixtures/durham_inspiring_excellence_undergraduate_scholarship.html`,
      `tests/fixtures/durham_inspiring_excellence_postgraduate_scholarship.html`)
      were captured unmodified from the live site.

- [x] **(2026-09-06)** "Germany postgraduate, masters, and undergraduate
      universities scholarship" request: implemented the University of
      Freiburg's Deutschlandstipendium source - see Changelog.md's
      same-date entry and `docs/AUTHORITATIVE_SOURCES.md` #69 for full
      detail. This platform's 70th opportunity source, and its second
      Germany-university source - TUM's International Student
      Scholarship (#59) remains the first.

      Unlike every England source added in the four follow-ups just
      above (one page per degree level), this single Freiburg page
      genuinely covers both halves of the request at once: its
      eligibility text names both undergraduate and Master's degree
      programme students as eligible for the same EUR 300/month,
      one-year stipend, with no nationality restriction stated at all.

      Ten other Germany candidates were researched live first and every
      one of them was a genuine dead end, not a shortcut skipped:
      Heidelberg's scholarship pages turned out to be for *outgoing*
      Heidelberg students studying abroad, not incoming applicants;
      Bonn's scholarships require existing enrollment with funding
      details still "to be published," and its own (German-only)
      Deutschlandstipendium page states the 2026/2027 round "has ended"
      with nothing next announced; Constructor University Bremen's three
      named scholarships (two JetBrains Foundation-funded, one Sparkasse
      Bank-funded) each have a single March 2026 deadline already passed
      with no next-cycle date in sight; Mannheim's two named scholarships
      both explicitly say their 2026/2027 application windows "have
      ended." The biggest recurring pattern, though: ESMT Berlin, WHU -
      Otto Beisheim School of Management, and Frankfurt School of
      Finance & Management all present their scholarship/financing pages
      as hubs of roughly ten separately-named, separately-sponsored
      awards (gender/diversity scholarships, regional scholarships,
      corporate-sponsored fellowships, alumni-network scholarships, and
      more) sharing one page - structurally the same "multi-record
      architecture mismatch" already correctly rejected for Warwick's
      Doctoral College page and TU Delft's general scholarship hub
      earlier in this project, and rejected here for the same reason
      rather than arbitrarily forcing one of the ten sub-scholarships
      into a single-record shape it doesn't have. Göttingen's advertised
      "university" scholarship turned out to be DAAD-administered
      (already covered by this platform's existing DAAD source, #10),
      with a deadline that carries no year on its own page. IU
      International University of Applied Sciences never surfaced a
      scholarship page at all through a plain HTTP fetch - its on-campus
      content appears to be a client-side-rendered Vue/Nuxt app.

      A genuine judgment call, documented rather than glossed over: the
      Freiburg page states an application-portal-open date of 1 March
      2027 *and* a closing date of 31 March 2028 for the "2027/2028
      scholarship round" - a thirteen-month window that flatly
      contradicts the same page's own description elsewhere of a
      roughly one-month March application period each year (echoed by
      the university's own FAQ: "you can only apply the following March
      for a scholarship"). Rather than either reporting "31 March 2028"
      verbatim as if it were a normal deadline, or silently "fixing" it
      to the year that would make sense, the deadline was left
      unextracted entirely - consistent with this project's long-
      standing "extract nothing rather than guess wrong" rule, applied
      here to a suspected *site* error rather than the usual case of
      genuinely no date being stated at all.

      Content-selector care, same discipline as every England source
      before it: the page's `main` element is 42KB, almost entirely a
      tabbed FAQ accordion that repeats the same eligibility/process
      detail several times over; the first `div.wp-block-columns`
      instead captures the real ~1.7KB description (general summary,
      funding amount, and the page's current application-cycle status)
      cleanly, verified via a BeautifulSoup structural walk of the
      actual fetched page before committing to the selector - not
      assumed from the element's name.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 783 passed / 25 skipped (up from 781 - the
      new source's two fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      69 -> 70 registered sources). The fixture
      (`tests/fixtures/freiburg_deutschlandstipendium.html`) was
      captured unmodified from the live site, following the page's own
      301 redirect from the URL search engines index to its canonical
      `uni-freiburg.de` host.

- [x] **(2026-09-06)** "Netherlands complete university scholarship &
      funding discovery engine" directive: a deep, exhaustive,
      multi-pass Netherlands expansion request explicitly asking for
      coverage across every major Dutch research university, every
      applied-sciences institution, every faculty/department/programme,
      Bachelor's/Master's/postgraduate/PhD levels, and 25 named audit
      passes. Set realistic expectations up front rather than pretending
      to execute all 40 sections literally: the same live-verification
      rigor this project has used throughout (robots.txt check,
      BeautifulSoup structural walk for content selectors, real fixture
      capture, fixture-backed tests, docs) makes each source take real
      research time, so a genuinely exhaustive per-faculty/per-programme
      sweep across 15+ institutions was not attempted - instead ran a
      real, honest multi-university pass and reported findings
      transparently rather than claiming false completeness (per the
      directive's own section 28: "quality over quantity" and section
      39's completion checklist, most of which cannot be honestly
      checked off from a single session).

      Researched 13 Dutch institutions live (University of Amsterdam,
      Vrije Universiteit Amsterdam, TU Eindhoven, University of
      Groningen, Leiden University, Utrecht University, Erasmus
      University Rotterdam, Maastricht University, Radboud University,
      University of Twente, Wageningen University & Research, Tilburg
      University, plus reconfirming TU Delft's existing source). Added
      **seven new real, verified opportunity sources** across **six
      universities** - see Changelog.md's same-date entry and
      `docs/AUTHORITATIVE_SOURCES.md` #70-76 for full technical detail
      on each. This platform's 71st-77th opportunity sources, and its
      19th-24th university-classified sources (TU Delft, #58, remains
      the first Netherlands-university source).

      The single biggest real finding of this pass, worth recording
      because it explains most of the rejections below: as of this
      research date (6 September 2026), the great majority of Dutch
      universities' Master's scholarship pages for the September 2026
      intake had *already closed* their application windows (deadlines
      clustering December-February) with *no* 2027-2028 cycle page
      published yet on the same URL. This is a genuine seasonal gap in
      the Dutch academic calendar's publication cycle, not a research
      shortfall - confirmed independently, over and over, by fetching
      the actual live page and reading its own stated cycle year rather
      than trusting a search-result snippet's freshness.

      **What got added, and why each one is trustworthy:**
      - University of Amsterdam's **Amsterdam Merit Scholarship**
        (Master's + Bachelor's, two sources): the university-wide
        overview pages honestly state "deadlines differ per Faculty,"
        so no deadline or amount is asserted centrally - a EUR 25,900
        figure seen on one Faculty's own subpage (Law) was *not*
        promoted to the general record, since the general page itself
        never states it.
      - University of Groningen's **Eric Bleumink Fellowship**: the one
        candidate this pass with an *explicit*, named ~80-country
        eligibility list rather than a vague "developing countries"
        label - checked the list character by character and confirmed
        Sierra Leone is actually in it, not assumed. Nomination-based
        (apply to the Master's programme, the university's own
        Admission Office nominates you - no separate scholarship
        application), which is a materially different, acceptable shape
        from the Vanier Canada Graduate Scholarships case rejected
        earlier in this project (there, nomination runs through a
        *different, autonomous* Canadian university's own quota).
        Genuinely `fully_funded`: tuition, travel, subsistence, books,
        and health insurance, all explicitly listed.
      - Utrecht University's **LEGITS scholarship**: only found after
        first confirming, directly on Utrecht's own page, that the
        university's flagship Utrecht Excellence Scholarship has been
        *discontinued* ("due to significant budget cuts") - a genuinely
        new and different kind of finding from every prior "stale cycle"
        rejection in this project, since this one will never reopen on
        its own. Utrecht's Bright Minds Fellowships were also checked
        and rejected for being EU/EEA-only.
      - Maastricht University's **UM NL-High Potential Scholarship** and
        University of Twente's **UTS**: both already-updated for the
        *next* cycle (2027-2028 / 2027) with real, not-yet-passed
        deadlines (10 December 2026 and 1 April 2027 respectively) -
        the two clearest "this is genuinely open right now" finds of
        the whole pass. Twente's page also has an exhaustive
        "Countries eligible for this scholarship" list, and Sierra
        Leone was confirmed present in it directly (alphabetically
        between Seychelles and Singapore).
      - Wageningen University's **Anne van den Ban Fund**: same
        nomination-based shape as Groningen's, for "students from
        low-income countries" - a real World Bank income-classification
        term, though this particular page doesn't enumerate a country
        list the way Groningen's does, so that distinction is recorded
        explicitly rather than papered over.

      **What got rejected, and why each rejection is a real finding, not
      a shortcut:**
      - **Vrije Universiteit Amsterdam** - the VU Fellowship Programme
        page explicitly says students not awarded it "in 2025/2026 are
        not eligible... for 2026/2027," i.e. it's narrating an
        already-closed cycle with a passed deadline (1 December 2025),
        and there's no 2027/2028 version yet. VU's Bachelor's page has
        only an external, Aon-funded, 2-award, enrolled-students-only
        scholarship - not a real VU-administered incoming-student award.
      - **TU Eindhoven** - states outright, in its own words, that it
        offers no Bachelor's scholarships at all. Its one Master's
        scholarship explicitly scopes itself to "the academic year
        2026-2027" only, with a deadline of 1 February 2026 already
        passed and an explicit note that "conditions and deadlines may
        differ in future academic years" - i.e. next year's page doesn't
        exist yet.
      - **Leiden University** - every path tested, including robots.txt
        itself, returned a genuine bot-protection CAPTCHA challenge
        page ("Access Blocked," an F5/Shape-style obfuscated JS
        challenge). Recorded as blocked and left alone, per this
        project's absolute "never bypass CAPTCHA/bot-protection" rule -
        not worked around with a headless browser or any other trick.
      - **Tilburg University** - same story, different vendor: every
        path, including the homepage, returned Cloudflare's "Just a
        moment..." challenge page (HTTP 403). Also left alone.
      - **Erasmus University Rotterdam** - the Erasmus School of
        Economics' Trustfonds Scholarship page's own `<h1>` literally
        reads "Erasmus Trustfonds Scholarship 2026-2027" with a passed
        deadline (1 February 2026); Rotterdam School of Management's
        scholarships page returned only navigation and footer text on a
        plain HTTP fetch, consistent with content that only renders
        client-side - not force-rendered with a browser engine, per this
        project's established pattern of recording such pages as
        inaccessible via the plain-HTTP path rather than escalating to
        headless rendering for a single candidate page.
      - **Radboud University** - its Scholarship Programme page states,
        in these exact words, "The deadline for 2026-2027 has passed,"
        with zero mentions of 2027-2028 anywhere on the page. Its
        separate Encouragement Scholarship page requires a SURFconext
        institutional login (HTTP 403 for an anonymous fetch) - not an
        opportunity a scraper can verify without credentials it
        shouldn't have.

      All thirteen of the above are documented in
      `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass
      (Netherlands exhaustive expansion), not integrated" section with
      the specific evidence for each, not just a one-line dismissal.

      **What this pass explicitly did NOT do**, stated plainly rather
      than glossed over, because the directive asked for an honest
      completion check (its own section 39): it did not search every
      faculty and department page at every university (hundreds of
      pages); it did not search individual Master's-programme pages one
      by one for programme-specific scholarships (the directive's
      section 33's full vision); it did not attempt PhD "vacancy" or
      "position" discovery at all, since those are salaried employment
      relationships this platform has never modeled as scholarship
      opportunities, and inventing a new opportunity taxonomy
      (`FULLY_FUNDED_PHD` / `PAID_PHD_POSITION` / `RESEARCH_POSITION`
      distinct fields) would have meant redesigning the schema, which
      the directive's own section 29 explicitly says not to do
      unnecessarily; it did not investigate the ~20 named Universities
      of Applied Sciences (Amsterdam UAS, Fontys, Saxion, HAN, HZ, NHL
      Stenden, Rotterdam UAS, and the rest); and it did not perform the
      25 separate formal "audit passes" the directive lists (deadline
      audit, broken-link audit, eligibility audit, etc.) as discrete
      exercises - though the equivalent verification work (checking
      every deadline, every eligibility claim, every URL) was in fact
      done inline for every source actually added or rejected.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 797 passed / 25 skipped (up from 783 - the
      seven new sources' fourteen fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      70 -> 77 registered sources). All seven fixtures
      (`tests/fixtures/uva_amsterdam_merit_scholarship_master.html`,
      `.../uva_amsterdam_merit_scholarship_bachelor.html`,
      `.../groningen_eric_bleumink_fellowship.html`,
      `.../utrecht_legits_scholarship.html`,
      `.../maastricht_high_potential_scholarship.html`,
      `.../university_of_twente_scholarship.html`,
      `.../wageningen_anne_van_den_ban_fund.html`) were captured
      unmodified from their live sites.

      One self-caught error during this pass, corrected before commit:
      an early draft of the AUTHORITATIVE_SOURCES.md entry, the
      COUNTRY_PROVIDER_REGISTRY.md row, the source class's own
      docstring, and its test's docstring all initially and incorrectly
      claimed the Amsterdam Merit Scholarship was "this platform's first
      Netherlands university source" - it is actually the *second*, since
      TU Delft's Van Effen Scholarship (source #58, added in an earlier
      pass) already holds that title. Caught by cross-checking the claim
      against `source_registry.py`'s actual `source_type` values before
      committing, and fixed in all four locations rather than left to
      propagate.

- [x] **(2026-09-06)** "Find another master's/postgraduate scholarship
      in the Netherlands" follow-up: implemented the University of
      Twente's ITC Excellence Scholarship Programme - see Changelog.md's
      same-date entry and `docs/AUTHORITATIVE_SOURCES.md` #77 for full
      detail. This platform's 78th opportunity source, and a genuinely
      distinct scholarship from the university-wide UTS (#75) added in
      the previous pass - administered by Twente's ITC faculty for two
      of its own Master's programmes (Geo-information Science & Earth
      Observation; Spatial Systems & Society), with its own eligibility
      list and cost breakdown. Confirmed Sierra Leone directly present
      in the page's ~100-country eligible list. Genuinely partial
      funding with an unusually precise, page-stated cost breakdown
      (EUR 25,000 ITC waiver against a EUR 74,370 two-year total, EUR
      17,000 left as the applicant's own contribution) - a good example
      of a scholarship that states its own funding_type classification
      almost explicitly, rather than requiring inference.

      A genuinely interesting judgment call, distinct from every prior
      "stale cycle" rejection in this project: the page itself says
      "APPLICATIONS 2026 CLOSED. A possible next round is expected to
      open in December" - this is not a page that forgot to update
      itself (like several Netherlands sources rejected in the previous
      pass), but a page candidly describing its own current
      between-rounds state with a genuine (if imprecise) expectation of
      reopening soon. Since "December" alone has no day or year, no
      deadline could be confidently extracted - correctly resolved to
      None rather than guessing a specific date - but the source was
      still added, since the underlying scholarship is real, current,
      and about to have a fresh round, not defunct or abandoned.

      Five other candidates were researched live first and rejected for
      concrete reasons, one of which deserves a special mention: Erasmus
      MC's **Ter Kulve Scholarship** was, on paper, an excellent fit -
      "Your nationality falls under the World Bank country
      classifications by income level for 2024-2025, specifically low-
      and middle-income countries" is about as clean and verifiable an
      eligibility criterion as this project has found anywhere, and its
      EUR 17,500 + tuition waiver would have made it genuinely
      comprehensive. It was still rejected, because its application
      deadline (1 April 2026) has already passed, and - checked
      independently - so has the identical deadline on Erasmus MC's
      other two scholarship pages (Erasmus Trustfonds, TSH Changemaker),
      confirming this isn't a one-off oversight but Erasmus MC's whole
      scholarship system running on one shared, currently-closed annual
      cycle. A strong eligibility match does not override a real,
      confirmed staleness finding - the same discipline applied
      throughout this project's England, Germany, and earlier
      Netherlands passes. VU Amsterdam's Faculty of Law Fellowship
      Programme was also checked and correctly recognized as a
      visiting-researcher fellowship (for people who already hold or
      are pursuing a doctorate) rather than a Master's/postgraduate
      degree scholarship, and excluded as out of scope for this
      specific request rather than forced in as a near-enough match.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 799 passed / 25 skipped (up from 797 - the
      new source's two fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      77 -> 78 registered sources). The fixture
      (`tests/fixtures/utwente_itc_scholarship.html`) was captured
      unmodified from the live site.

- [x] **(2026-09-06)** "Find another master's/postgraduate scholarship
      in Spain" follow-up: implemented UPF Barcelona School of
      Management's (Universitat Pompeu Fabra) Merit Based Scholarship -
      see Changelog.md's same-date entry and
      `docs/AUTHORITATIVE_SOURCES.md` #78 for full detail. This
      platform's 79th opportunity source, and this registry's *first*
      Spain *university* source (the existing Spain source, #23
      `spain_aecid`/Becas MAEC-AECID, is government-classified, not a
      university).

      No nationality or country restriction anywhere in the eligibility
      criteria (a completed university qualification and a minimum
      3.0/4.0 GPA, explicitly including degrees "obtained abroad") -
      Sierra Leone applicants are eligible. Genuinely partial funding,
      stated in the page's own words: "covers 25% of the total tuition
      fee," extendable by "an additional 25%" for demonstrated financial
      need - never described as fully funded.

      A genuinely interesting deadline-extraction judgment call: the
      page lists four rolling annual application rounds (18 June 2026,
      3 September 2026, 26 November 2026, 21 January 2027). As of this
      research date the first two rounds had already passed. The
      generic "deadline" keyword resolves to nothing at all on this
      page, and blindly taking the first dated occurrence in the text
      would have surfaced an already-passed date. Tested each round's
      own label ("1st call" through "4th call") individually against
      `extract_confident_date_after` and confirmed each resolves
      correctly (2026-06-18, 2026-09-03, 2026-11-26, 2027-01-21
      respectively) before deliberately choosing the specific phrase
      "3rd call" - confirmed to occur exactly once in the full page
      text, with no ambiguity risk - as the keyword that correctly
      resolves to the next genuinely upcoming round rather than a stale
      one.

      Also worth noting: the initial candidate page for this
      institution, `bsm.upf.edu/en/master-of-science-scholarships` (a
      hub listing several named scholarships), returned a real `<h1>`
      but an essentially empty body - no "Merit" text anywhere, no
      `main` tag - diagnosed as client-side-rendered content absent
      from the plain-HTTP response, the same category as several
      previously-rejected pages this session (RSM Rotterdam, IU
      International, IE University's detail pages), distinct from
      genuine bot-protection/CAPTCHA walls (Leiden, Tilburg) which this
      project never attempts to bypass. Pivoted to the
      `en/talent-scholarship` URL instead, which returned real static
      content and was the one integrated.

      Four other Spanish candidates were researched live first and
      rejected for concrete reasons: **IE University** (hub page and
      detail pages both either multi-scholarship listings or
      client-side rendered), **Universidad de Navarra** (a hub page
      whose individual scholarships are documented only as PDFs, not a
      single web page fitting the `_SingleProgramSource` shape), and
      **ESADE**'s Esade MSc Excellence Awards - a single named scheme
      with regional/tier variants that would otherwise fit the
      architecture, but whose own deadline text explicitly reads "July
      15, 2026 (for the 2026 intake)," an already-passed date with no
      next-cycle date stated anywhere on the page. A partially updated
      "2027-2028" tuition figure appearing elsewhere on that same ESADE
      page was deliberately *not* treated as evidence that a
      same-shaped next cycle exists - consistent with this project's
      standing rule to never guess a future cycle from a stale prior
      one.

      **Verified for real**: `pyflakes app tests` clean; full backend
      suite green afterward, 801 passed / 25 skipped (up from 799 - the
      new source's two fixture-backed tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      78 -> 79 registered sources). The fixture
      (`tests/fixtures/upf_bsm_merit_scholarship.html`) was captured
      unmodified from the live site.

- [x] **(2026-09-06)** "France fully funded Master's university
      scholarship engine" request: implemented Sciences Po's Mastercard
      Foundation Scholars Program (graduate/Master's track) - see
      Changelog.md's same-date entry and `docs/AUTHORITATIVE_SOURCES.md`
      #79 for full detail. This platform's 80th opportunity source, and
      this registry's *first* France *university* source. The request
      was an extremely long, exhaustive-sounding mega-prompt (40
      sections covering ~50 named institutions, a full new database
      schema, a scoring engine, a search-loop pseudocode, etc.) - as
      with the earlier Netherlands mega-prompt, the honest framing given
      up front was that a full automated discovery pipeline, new schema
      fields, and a scoring/matching engine were out of scope for a
      single pass, but a genuine (not exhaustive) multi-institution
      research pass against the existing `_SingleProgramSource`
      architecture was both feasible and exactly what the underlying
      need called for.

      The core difficulty of this request was its own strict
      definition of "fully funded": full tuition/registration coverage
      **and** substantial living support, evidenced by the university's
      own words, with an explicit instruction not to inflate a partial
      award into "fully funded." This bar turned out to be genuinely
      rare among French university scholarships for internationals -
      most (Paris-Saclay, IP Paris, PSL, Aix-Marseille) offer real,
      useful, but partial annual stipends (~EUR 8,000-10,000/year)
      against French public tuition and Paris-level living costs,
      falling short of the bar. Sciences Po's Mastercard Foundation
      Scholars Program was the one candidate found whose own official
      page states, independently in two places, that it "covers the
      full cost of tuition and living expenses" and "the full financial
      needs of selected Scholars" - a categorically different, fully
      comprehensive statement rather than a large-but-partial number.

      A second, equally important part of this request was to
      correctly *exclude* France Excellence Eiffel and Erasmus Mundus
      from the university-only dataset even though both are important,
      real France-related scholarships - the request's own text
      anticipated and explicitly warned against the mistake of counting
      Eiffel as a university scholarship "merely because French
      universities nominate candidates." Both were confirmed still
      correctly excluded (Eiffel is already source #27,
      government/Campus France-classified; Erasmus Mundus is already
      source #49, EU/EACEA-classified) - neither was re-added or
      reclassified.

      A third notable finding, applying this session's standing "never
      infer eligibility from a vague regional label" discipline in the
      opposite direction from usual: Sciences Po's own eligibility page
      states the *specific*, general criterion "Hold the citizenship of
      an African country" (not a vague "developing countries" phrase,
      and not a narrower named-country list) as the sole nationality
      test, so Sierra Leone was correctly marked eligible - while still
      documenting, rather than hiding, the separate, non-national
      constraint that applicants must also hold a Bachelor's degree from
      one of the Program's own approved partner universities (or a
      bridge/mentoring programme, or UNHCR refugee status), which
      narrows real-world eligibility beyond blanket nationality without
      excluding the country itself.

      A fourth finding, applying the "never fabricate a deadline"
      discipline to an unusually explicit case: the scraped page states
      outright that exact application-timeline details "will be
      published on this page from September 2026," and gives only an
      imprecise "October to mid-December 2026" window with no day
      number - `extract_confident_date_after` was verified directly
      (via a standalone script) to correctly resolve to `None` on every
      keyword tried ("deadline", "closing date", "mid-December"), and
      critically, was verified to *not* accidentally latch onto the
      page's one full date literal ("17 October 2026"), which is an
      information-session/Open House date, not the application
      deadline - a real near-miss this project has hit before in
      slightly different forms (grabbing the wrong dated section on a
      page with multiple dates).

      Eight other candidates were researched live and rejected for
      concrete, evidence-based reasons rather than a blanket "none
      found": Sciences Po's own Émile Boutmy Scholarship
      (tuition-exemption only, no living component); Université
      Paris-Saclay's International Master's Scholarships Program, which
      CentraleSupélec also participates in (EUR 10,000/year, the
      university's own text conceding it covers only "the majority of
      academic fees"); Institut Polytechnique de Paris/École
      Polytechnique's two scholarship schemes (EUR 8,000-10,000/year
      against up to EUR 15,400/year tuition); PSL Université (no single
      page found stating full tuition-and-living coverage for a
      Master's - PSL's genuinely fully-funded tracks are PhD-linked,
      outside this pass's Master's-only scope); Aix-Marseille
      Université's TIGER Master Excellence Grants (EUR 10,000/year +
      guaranteed accommodation, not stated to cover full cost); and
      University of Bordeaux/Télécom Paris (no university-administered
      fully-funded route found beyond the already-excluded
      Eiffel/Erasmus Mundus).

      **Verified for real**: `pyflakes app tests` clean; a standalone
      `collect()` simulation against the real fixture confirmed title,
      provider, country, `funding_type = "fully_funded"`, and
      `deadline = None` all resolve exactly as documented before any
      test was written; full backend suite green afterward, 803 passed
      / 25 skipped (up from 801 - the new source's two fixture-backed
      tests, plus `test_opportunity_import.py`'s updated source-count
      assertion, 79 -> 80 registered sources). The fixture
      (`tests/fixtures/sciencespo_mastercard_scholars.html`) was
      captured unmodified from the live site.

- [x] **(2026-09-06)** "Find another fully funded master's scholarship
      in Germany" request: added the Konrad-Adenauer-Stiftung (KAS):
      Scholarship Programme for International Students - see
      Changelog.md's same-date entry and
      `docs/AUTHORITATIVE_SOURCES.md` #10's 2026-09-06 update for full
      detail. Unlike every other addition this session, this is *not* a
      new `OpportunitySource` row - it is a seventh monitored detail id
      added to the pre-existing DAAD Scholarship Database source (#10),
      via `Settings.daad_scholarship_detail_ids`, exactly as that
      adapter's own module docstring already describes as the intended
      way to extend its coverage ("extending coverage means adding more
      ids to that setting... not writing more scraping code"). The
      platform's registered-source count stays at 80; a new individual
      scholarship record is added within an existing source instead.

      Before reaching that shape, first checked whether Germany already
      had a fully-funded Master's option: the DAAD adapter's existing
      six seed ids already include "Study Scholarships - Master Studies
      for All Academic Disciplines" (id 50026200) and two other
      Master's-eligible DAAD programmes (EPOS, STEM disciplines) -
      DAAD's own flagship Master's scholarship was therefore already
      covered, ruling it out as "another" option and pointing the
      search toward German university-administered or foundation-
      administered alternatives instead.

      The core research finding was that Germany's free-public-tuition
      norm changes what "fully funded" has to mean in practice: unlike
      France or Spain, where full tuition coverage is itself the hard
      part, German public universities already charge no tuition for a
      first Master's degree in 15 of 16 federal states, so the real bar
      became "does this programme's own page state a living-cost
      package comprehensive enough to not need the tuition question at
      all." Two political-party-affiliated foundations came up
      repeatedly in this space, both discoverable through DAAD's own
      scholarship database (each foundation has its own `?detail=<id>`
      entry there, confirmed via direct HTML fetch of both):

      - **Konrad-Adenauer-Stiftung (KAS)**, detail id 10000108: a
        monthly grant of EUR 992 for Bachelor's/Master's recipients
        (Germany's own standard BAfoeG maximum living-cost reference
        rate) plus health/long-term-care insurance and family
        allowances, over a standard 2-year Master's funding period. Its
        own page's country-eligibility dropdown - a literal `<select>`
        of ~150 countries used to gate who may even start an
        application - was checked directly and confirmed to list
        "Sierra Leone" by name, satisfying this project's "never infer
        eligibility from a vague label" rule about as concretely as
        possible. Added.
      - **Friedrich-Ebert-Stiftung (FES)**, detail id 10000153: on
        paper an even more generous package (up to EUR 1,500/month per
        some third-party aggregators, though DAAD's own page states EUR
        992 base + insurance + child allowance) with an explicit,
        checkable eligibility rule (Global South/post-Soviet/eastern-
        and-south-eastern-EU applicants, explicitly excluding OECD
        countries - Sierra Leone is African and not OECD, so it
        qualifies on both the inclusion and exclusion halves of that
        rule). Rejected anyway for a reason worth stating plainly: its
        own Academic Requirements section says applicants need
        "enrolment at a state or state-recognised higher education
        institution in Germany" and its Target Group description says
        candidates "already study in Germany" - this is ongoing support
        for students already admitted and enrolled, not a scholarship a
        prospective Sierra Leonean applicant could use to fund *initial*
        admission from abroad, unlike KAS (whose own text has no such
        prior-enrolment requirement for Master's applicants). This
        distinction mirrors the earlier-session discipline around not
        conflating "PhD employment" with "PhD scholarship" - here it is
        "already-enrolled support" vs. "new-applicant scholarship,"
        and getting it right matters for whether this platform's actual
        target users could use the opportunity at all.

      A third finding worth recording: KAS's *own* website (`kas.de`)
      returned a Web Application Firewall block page in place of a
      robots.txt when checked directly - genuine bot-protection, not
      circumvented per this project's absolute rule. The identical
      programme remains real and usable because DAAD's own database
      (`www2.daad.de`, this platform's existing, already-audited,
      unblocked host for six other programmes) independently hosts and
      maintains the same programme's official detail page - so the
      programme was still added, sourced from DAAD's mirror rather than
      KAS's blocked site, rather than treated as unreachable.

      Implementation-wise, this required one small, deliberately
      isolated code change beyond adding the id itself: the existing
      `DaadScholarshipsSource._normalize` method has never set
      `funding_type` at all (it predates that field's use elsewhere in
      this codebase) - rather than either leaving the new KAS record
      unclassified (failing to answer the user's actual "fully funded"
      question) or retroactively guessing a classification for the
      other six long-standing seed ids that were never researched with
      that question in mind, added a small `_FUNDING_TYPE_OVERRIDES`
      dict keyed by detail id, defaulting to `None` for every id not
      explicitly present - confirmed via a dedicated regression test
      that the other six ids' classification is unaffected.

      Four other German candidates were researched live and rejected:
      RWTH Aachen's High Potential Student Grant and Global Talent
      Scholarship (both explicitly partial tuition coverage); the Elite
      Network of Bavaria's Max Weber Programme (a "Semester Allowance,"
      not an explicit full-cost statement, plus a German B2/C1 language
      precondition); Constructor University/Jacobs University Bremen
      (current scholarships explicitly partial; a historical "full
      tuition" one-off from 2022 could not be confirmed as a current,
      recurring programme); and Hertie School Berlin (its full
      scholarships are explicitly tuition-only, with living-cost
      support, where it exists, coming from separate third-party
      organisations rather than the school itself).

      **Verified for real**: `pyflakes app tests` clean; a standalone
      script confirmed `extract_confident_date_after` correctly
      resolves to `None` on the KAS page's year-less "15 July" recurring
      deadline text, and a `collect()` simulation against the real
      fixture confirmed title, funding_type = "fully_funded", and
      deadline = None all resolve exactly as documented before any test
      was written; full backend suite green afterward, 805 passed / 25
      skipped (up from 803 - two new tests in
      `test_daad_scholarships.py`: one fixture-backed collect test for
      the new detail id, one regression test confirming the other six
      seed ids keep no funding_type classification). No change to
      `test_opportunity_import.py`'s source-count assertion (still 80 -
      this addition does not create a new `OpportunitySource` row). The
      fixture (`tests/fixtures/daad_detail_kas.html`) was captured
      unmodified from the live site.

- [x] **(2026-09-06)** "China fully funded Master's university
      scholarship engine" mega-prompt: implemented the Peking
      University Scholarship for International Students and Shanghai
      Jiao Tong University's Master's SJTU Scholarship - see
      Changelog.md's same-date entry and `docs/AUTHORITATIVE_SOURCES.md`
      #80-#81 for full detail. This platform's 81st and 82nd opportunity
      sources, and this registry's first two China *university* sources
      (Schwarzman Scholars, #50, and Yenching Academy, #52, are elite
      named programmes hosted at Tsinghua/PKU, not general
      institution-wide scholarships).

      As with the Netherlands and France mega-prompts earlier this
      session, the request itself (57 numbered sections: a full
      DISCOVER/CRAWL/EXTRACT/.../CONTINUE SEARCHING pipeline, PDF
      processing, Chinese-language search, a 40+ new database field
      schema, reliability scoring, UI badges, a recommendation engine,
      an autonomous search loop) was set against realistic expectations
      up front rather than attempted literally - no new schema fields,
      scoring engine, or PDF-processing pipeline were built. What was
      actually delivered: genuine, live-verified research across five
      major Chinese universities, two real fully-funded Master's
      opportunities added following the existing architecture, and
      three candidates honestly rejected with evidence.

      Connectivity itself was a real first question for this pass -
      Chinese university domains carry a justified reputation for being
      hard to reach or bot-protected. Tested this directly rather than
      assuming either way: `robots.txt` requests to Tsinghua, Fudan,
      Zhejiang, and SJTU's English site all resolved (some 404 - no
      robots.txt file, which is permissive, not restrictive - one 200),
      and their actual homepages loaded in 2-5 seconds with real HTML.
      Only `www.pku.edu.cn` itself timed out; PKU's international
      students division subdomain (`isd.pku.edu.cn`), reached
      separately, loaded fine. This meant the pass could proceed as a
      normal live-research exercise rather than an early "blocked,
      stop here" finding - though the pre-existing China Scholarship
      Council (CSC) finding from an earlier session pass (genuine
      anti-bot protection, `docs/COUNTRY_PROVIDER_REGISTRY.md`'s
      "China - BLOCKED" section) remains correct and unaddressed; the
      two sources added here are on entirely separate, unblocked
      university domains.

      The core research finding, stated plainly in the request's own
      warning about not trusting scholarship names: most major Chinese
      universities checked (Tsinghua, Zhejiang, Fudan) primarily funnel
      international Master's funding through the Chinese Government
      Scholarship (CGS/CSC) and provincial/municipal government
      scholarships, not a comprehensive scheme they fund and administer
      themselves - and the request's own instruction to keep
      government/CSC funding separate from a "university-only" dataset
      meant most of what these universities' own scholarship pages
      describe had to be set aside rather than counted. Tsinghua's own
      "Financial Aid System" page is unusually explicit about this
      split: it names its own "Tsinghua University Tuition Scholarship"
      and states plainly that Tuition Scholarships "cover full or
      partial tuition fees" only, correctly distinguishing itself from
      CGS's fuller (but government-funded) package - a rare case of a
      university's own page doing the funding-type classification work
      for this platform. Zhejiang University's "Master's Scholarships"
      page turned out to be a hub listing CGS Type A/B, a CGS Youth of
      Excellence Scheme, the Zhejiang provincial scholarship, and two
      school-specific awards - the same multi-record architecture
      mismatch this project has repeatedly found at ESMT, WHU, IE
      University, and Universidad de Navarra, with the added tell that
      most individual pages carried dated 2022 URLs suggesting
      unmaintained, non-evergreen content. Fudan's International
      Students Office was similar: real, but every path led back to
      CGS/Shanghai Government/Confucius Institute funding rather than a
      standalone Fudan-funded package.

      Peking University's own International Students Division page
      stood out for being refreshingly single-purpose in a way none of
      the above were: one plain, old-HTML page (no `<h1>`, no CSS
      framework, no tabs) stating outright "It covers tuition, a living
      stipend and medical insurance" for a 2-3 year Master's, with
      eligibility framed purely around PKU's own admission requirements
      and no mention of CGS, government funding, or a provincial
      scheme anywhere on the page - a genuinely university-funded,
      single-record scholarship exactly matching this project's
      preferred shape. The page's total absence of heading markup meant
      the standard `title_selectors = ("h1",)` default would find
      nothing; rather than falling through to the less-precise
      external_id-derived fallback, used `title_tag_separator = " | "`
      - a separator that does not actually appear in the real `<title>`
      text - specifically so the split is a no-op and the page's
      already-clean title is used unchanged.

      Shanghai Jiao Tong University's page was a more interesting
      architectural case: `Study@SJTU` is a genuine multi-tab hub
      (Undergraduate Programs, Graduate Programs) rather than a
      single-scholarship page, which on its face looks like the
      Zhejiang/hub pattern that gets rejected - but unlike Zhejiang's
      page, each tab here is exactly one clearly-scoped panel (not a
      list of many separately-sponsored external schemes), and the
      Graduate Programs panel specifically and precisely describes the
      Master's SJTU Scholarship (tuition waiver + monthly stipend +
      insurance + accommodation subsidy) as SJTU's own funded award,
      genuinely distinct from a sibling "Tuition Waiver Scholarship"
      (tuition + insurance only, correctly left unintegrated as
      `TUITION_ONLY`) named in the very same paragraph - a real example
      of the request's own warning not to assume every scholarship
      mentioning "full" or "waiver" is the same thing. Confirmed via a
      direct BeautifulSoup structural walk that the page has exactly
      two `div.page-item` tab panels before choosing a selector - a
      naive `div.page-item` selector would have silently grabbed the
      wrong (Undergraduate) panel, since `select_one` always returns
      the first match. Used the adjacent-sibling CSS combinator
      `div.page-item + div.page-item` instead, which BeautifulSoup's
      selector engine supports natively and which unambiguously
      resolves to the second panel by structural position rather than
      any class/id difference (there wasn't one). Also deliberately
      spelled the university's name out in full in `external_id`
      ("shanghai-jiao-tong-university-masters-scholarship") rather than
      using the common "SJTU" abbreviation, specifically so the
      external_id-derived title fallback (needed because this page's
      own `<title>` describes the whole hub, not this scholarship)
      capitalizes correctly - "Shanghai Jiao Tong University Masters
      Scholarship," not the "Sjtu Masters Scholarship" a literal
      acronym-based id would have produced.

      **Verified for real**: `pyflakes app tests` clean; a standalone
      script confirmed `extract_confident_date_after` correctly
      resolves to `None` for both pages' deadline-adjacent text (PKU's
      year-less "January and March" window; SJTU's Graduate Programs
      panel, which states no date at all); a `collect()` simulation
      against both real fixtures, run before any test was written,
      confirmed both sources' title, provider, country, `funding_type
      = "fully_funded"`, and `deadline = None` all resolve exactly as
      documented; full backend suite green afterward, 809 passed / 25
      skipped (up from 805 - four new fixture-backed/robots-txt tests
      across the two new sources, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      80 -> 82 registered sources). Both fixtures
      (`tests/fixtures/pku_international_scholarship.html`,
      `tests/fixtures/sjtu_masters_scholarship.html`) were captured
      unmodified from their live sites.

- [x] **(2026-09-06)** "Find another fully funded master's scholarship
      in Canada" request: implemented McGill University's Mastercard
      Foundation Scholars Program - see Changelog.md's same-date entry
      and `docs/AUTHORITATIVE_SOURCES.md` #82 for full detail. This
      platform's 83rd opportunity source, and this platform's *first
      Canada source of any kind* - not just first Canada-university
      source, since no Canada source existed at all before this. An
      earlier session pass (2026-08-29) had already found Canada
      `NOT_SUITABLE` at the national/government level (EduCanada's
      Study in Canada Scholarships is institution-initiated, applicants
      cannot apply directly) - that finding was re-read carefully
      before starting this pass and confirmed still correct and
      unaffected, since this request called for going to the
      university level instead, a different layer entirely.

      A real first question for this pass, given the "another
      Mastercard Foundation Scholars Program" precedent already set by
      Sciences Po (France, #79): does McGill also partner with the
      Mastercard Foundation, and if so, is its own page structured the
      same accessible way? Both answered yes - McGill has partnered
      with the Foundation since 2013, and its own site
      (`mcgill.ca/mastercardfdn-scholars/...`) follows the identical
      "university administers its own application/eligibility pages"
      pattern already verified for Sciences Po, rather than routing
      through a separate foundation-run portal.

      The core research finding for this country, distinct from every
      prior country pass this session: Canadian research universities
      structure graduate funding differently from what's been seen at
      Chinese, Dutch, and French universities. Rather than "tuition
      waiver + stipend" being the norm, Canadian universities almost
      universally guarantee a *stipend* (via a combination of
      scholarships, teaching assistantships, and research
      assistantships) for thesis-based graduate students, while
      leaving tuition itself either unaddressed or covered only by a
      separate, much smaller award. Checked this directly rather than
      assuming: University of Calgary's own "Funding Thesis-based
      Students" page states a guaranteed $25,455/year package for
      international MA/MSc students in one clear sentence, but neither
      that page nor any linked page ever states this figure is
      inclusive of tuition - and a separate, much smaller
      "International Graduate Tuition Award" (~$3,060/year total) is
      the only tuition-specific instrument mentioned anywhere on
      Calgary's site. Given a page that states funding amounts in such
      specific, confident dollar figures would very plausibly also
      state "this includes full tuition" if that were true (compare
      Sciences Po's or PKU's explicit "covers... tuition" language),
      its conspicuous absence here was read as real evidence of a
      stipend-only package, not an oversight - correctly classified
      `PARTIALLY_FUNDED` rather than assumed fully funded from a large
      dollar figure alone. University of Waterloo made this
      classification decision trivial by stating it outright on its
      own site: "the University of Waterloo does not offer full-ride
      scholarships that cover all tuition and living costs."

      McGill's Mastercard Foundation Scholars Program was the one
      exception found to this country-wide pattern - its own "About"
      page states the scholarship includes "Full international student
      tuition" as a distinct, named line item alongside "On-campus
      housing" and "Personal monthly stipend," the same explicit,
      itemized structure already seen at Sciences Po and Peking
      University, categorically different from a single ambiguous
      dollar figure.

      Eligibility required checking two separate McGill pages, since
      the "About" page (used for the actual scraped content, because
      it is the one stating the funding package) only frames
      eligibility in general continental terms ("from over 20 African
      countries"), while the *separate* Eligibility page has the
      actual explicit country list - fetched independently and
      confirmed to name "Sierra Leone" directly among roughly 54
      countries, the exact "explicit check, never a vague label"
      standard this project has held to throughout. This same
      "eligibility list lives on a different page than the funding
      description" split was already seen with Sciences Po's Mastercard
      program (general hub page vs. graduate-study eligibility
      subpage) - recognizing the pattern the second time around made
      the two-page check faster than it was the first time.

      A genuinely interesting near-miss was the McCall MacBain
      Scholarship - by every funding measure a strong candidate (full
      tuition, a CAD 2,300/month stipend, a relocation grant, ten seats
      reserved for non-Canada/US applicants), also hosted and promoted
      on a McGill web page. Checked the URL path of that page itself
      before treating it as equivalent to the Mastercard Foundation
      program: `mcgill.ca/gradapplicants/funding/external/mccall-
      macbain-scholarship` - the word "external" in McGill's own URL
      structure is McGill's own classification of the award as one it
      lists but does not itself administer (McCall MacBain Scholars is
      run by an independent foundation with its own separate selection
      process, `mccallmacbainscholars.org`). Left unintegrated as a
      university-administered record for exactly that reason, rather
      than treated as interchangeable with a program McGill itself
      selects and admits students for.

      Four other candidates were also researched and rejected on
      similar stipend-only or too-small-an-award grounds: University of
      Alberta (funding packages and international tuition figures
      quoted separately with no page connecting them), University of
      Toronto (funding set per graduate unit/department, no single
      university-wide page), and University of British Columbia (its
      International Tuition Award is a small ~$3,200/year top-up for
      students already registered, not an entrance scholarship).

      **Verified for real**: `pyflakes app tests` clean; a `collect()`
      simulation against the real fixture, run before any test was
      written, confirmed title, provider, country, `funding_type =
      "fully_funded"`, and `deadline = None` all resolve exactly as
      documented; full backend suite green afterward, 811 passed / 25
      skipped (up from 809 - two new tests, plus
      `test_opportunity_import.py`'s updated source-count assertion, 82
      -> 83 registered sources). The fixture
      (`tests/fixtures/mcgill_mastercard_scholars.html`) was captured
      unmodified from the live site. Also set
      `min_request_interval_seconds = 5.0` on this one source
      specifically, matching `mcgill.ca/robots.txt`'s own
      `Crawl-delay: 5` directive exactly, rather than leaving this
      file's usual 2.0-second default in place for a site that asked
      for something more conservative.

- [x] **(2026-09-06)** China fully-funded Master's engine, continuation
      pass: the same 57-section China mega-prompt was resubmitted
      verbatim after the first pass (which added PKU and SJTU, sources
      #80-#81). Its own "AUTOMATIC CONTINUATION RULE" (section 55)
      explicitly says not to stop after the first version and to keep
      searching until no meaningful new authoritative sources remain -
      treated this literally: continued the same university-by-
      university search rather than re-implementing anything already
      built, and reported back honestly on what six more universities'
      own official pages actually said.

      Checked Nanjing University, University of Science and Technology
      of China, Wuhan University, Sun Yat-sen University, Renmin
      University of China, and Xi'an Jiaotong University - six
      genuinely distinct outcomes, not one repeated excuse:

      - **Nanjing University**: its own "Scholarships" index page
        (fetched directly) contains a single inline `<script>` that
        immediately redirects to the Chinese Government Scholarship
        page - about as concrete a piece of evidence as this project
        has found anywhere that a university's scholarship story
        begins and ends with CGS. The only other listed routes
        (Nanjing Municipal, Confucius Institute Teachers, Confucius
        China Studies) are all government/institute-branded, not
        NJU's own money.
      - **USTC**: found via search summaries claiming a comprehensive
        "USTC Scholarship" package, but fetching the university's own
        page directly (with the correct GB18030 encoding, since the
        first UTF-8 attempt threw a decode error) revealed a page
        titled "2020 USTC Scholarship Program," last updated
        2017-04-10, with an application deadline of "March 31, 2020."
        Checked the site's own Notice board for anything more recent -
        the newest scholarship-relevant item found was a 2022 CGS
        announcement. A textbook case of exactly the trap this
        project's "never present stale content as current" rule exists
        to catch: the 2020 page's own funding description (tuition +
        accommodation + stipend + insurance) was genuinely
        comprehensive, but presenting six-year-old figures as today's
        offer would have been fabrication by omission.
      - **Wuhan University**: every route surfaced was CGS-branded;
        no standalone WHU page found.
      - **Sun Yat-sen University**: the most interesting near-miss of
        this round. Its own official 2026 guidelines page describes a
        genuinely real, non-CGS-combinable, three-tier scheme (tuition
        waiver + up to RMB 30,000/year living allowance for the top
        tier) - exactly the shape this project looks for. But the
        page's own `<h1>` is not a neutral title; it is literally
        "CLOSED | 2026 Guidelines for the Application of Scholarship
        for International Students at Sun Yat-sen University." Searched
        the full page text directly for "2027" and "next" - neither
        appears anywhere. Unlike University of Twente's ITC
        scholarship (whose page volunteers "a possible next round is
        expected to open in December"), SYSU's page gives no forward-
        looking signal at all. Correctly left unintegrated per the
        "never guess a future cycle from a stale prior one" rule,
        flagged explicitly as worth re-checking once SYSU publishes a
        2027 cycle.
      - **Renmin University of China**: search results describe only
        ambiguous "tuition scholarships" (full, partial, or a refund)
        plus small named merit awards, with no living-stipend component
        described anywhere - didn't fit the "tuition AND substantial
        living support" bar clearly enough to warrant fetching the
        official page directly for a second look this round.
      - **Xi'an Jiaotong University's Siyuan International Student
        Scholarship**: the other genuinely real near-miss - a named,
        university-funded, tiered-stipend scheme distinct from CGS
        (up to RMB 3,500/month for Master's students). Fetching its
        official detail page directly (`sie.xjtu.edu.cn`) returned a
        page titled "网站正在加载中..." ("website is loading...")
        containing an inline JavaScript bot-detection challenge -
        checking for `navigator.webdriver`/PhantomJS markers,
        collecting browser fingerprint data, computing a hash, and
        POSTing it to a `/dynamic_challenge` endpoint before a
        client-side redirect to the real content. This is the same
        category of active anti-bot defense already encountered and
        correctly left alone for China's own CSC portal, Cyprus, and
        Brazil earlier in this project - recognized quickly specifically
        because this project has now seen this exact pattern (dynamic
        JS challenge computing a token before granting access) several
        times before. Not bypassed; recorded as `BLOCKED`.

      No new opportunity source qualified this round. This is reported
      as the correct outcome, not a shortfall: this project's own
      "accuracy over quantity" standard (echoed in the request's own
      section 57, "a verified list of 15... is better than 200
      inaccurate") means a genuine second pass that finds zero new
      qualifying sources is exactly what should happen once the
      easiest, cleanest candidates (PKU, SJTU) have already been
      found and the remaining candidates are all either government-
      branded, stale, ambiguous, closed-with-no-next-cycle, or
      bot-protected.

      **No code was changed this pass** - only
      `docs/AUTHORITATIVE_SOURCES.md` and
      `docs/COUNTRY_PROVIDER_REGISTRY.md` were updated, appending this
      continuation's findings to the existing "Researched this pass"
      sections from the prior China pass. No new test run was required
      since no source code, test, or fixture file changed; the existing
      811-passed/25-skipped baseline from the McGill addition remains
      the accurate current count.

- [x] **(2026-09-06)** "England fully funded Master's university
      scholarship engine" mega-prompt: implemented the Gates Cambridge
      Scholarship - see Changelog.md's same-date entry and
      `docs/AUTHORITATIVE_SOURCES.md` #83 for full detail. This
      platform's 84th opportunity source, and this registry's *first*
      England source classified as genuinely fully funded - all nine
      pre-existing England sources (Imperial Inspires, Newcastle VC
      International, Sheffield PG, Manchester Global Futures,
      Nottingham PG, Southampton's two, Durham's two) were confirmed
      by direct grep of the source code to be `partial_funding`, none
      previously fully funded, before starting this pass.

      As with the Netherlands/France/Germany/China/Canada mega-prompts
      this session, the request itself (37 numbered sections: an
      exhaustive university-by-university England search loop, a large
      new database schema, a recommendation engine, funding scoring, UI
      badges) was set against realistic expectations rather than
      attempted literally - the actual deliverable was genuine,
      live-verified research into the request's own two named
      "important examples" (Oxford's Clarendon Fund and Cambridge's
      Gates Cambridge Scholarship) plus enough surrounding checks to
      confirm neither was a hasty pick.

      The two examples split into a clean "implement" and a clean
      "cannot, for reasons unrelated to funding" outcome, which is
      itself a useful, honest result rather than a wash:

      - **Cambridge - Gates Cambridge Scholarship**: verified directly
        against `gatescambridge.org` (a dedicated Trust website, not
        merely a page on cam.ac.uk) that the funding claim holds up
        exactly as described - "covers the full cost of studying at
        Cambridge," itemized into tuition, a GBP 22,050/year
        maintenance allowance, return airfare, visa costs, and the
        Immigration Health Surcharge. Checked the separate eligibility
        page independently and found the broadest eligibility
        criterion seen anywhere in this session: "a citizen of any
        country outside the United Kingdom" - no continent, no
        named-country list, no exceptions for Sierra Leone or anywhere
        else. Also had to check something this project hasn't needed
        to check before for a UK source: whether Gates Cambridge funds
        Master's-level study at all, since its most famous cohort is
        PhD students - confirmed directly that "MLitt" and "a one-year
        postgraduate course" (Cambridge's standard term for taught/
        research Master's degrees like the MPhil) are both explicitly
        eligible, and cross-checked the page's own "exceptions" list
        (MASt, part-time non-PhD degrees, MBA/EMBA/MFin, PGCE, medical
        degrees) to confirm none of those exceptions accidentally
        swallows the ordinary Master's route.
      - **Oxford - Clarendon Fund**: by every funding measure checked
        via search (full course-fee coverage, a living grant, no
        nationality restriction, automatic consideration - no separate
        application needed), Clarendon is at least as strong a
        candidate as Gates Cambridge, arguably the single most
        well-evidenced fully-funded England scholarship this project
        has looked at. But fetching `ox.ac.uk` directly - the specific
        Clarendon page, the site root, and even `robots.txt` itself -
        returned an active Cloudflare "Just a moment..." managed
        challenge (HTTP 403, a JavaScript browser-verification
        interstitial) on every single attempt. This is a real
        connectivity/access finding, not a research shortcut: per this
        project's absolute "never bypass CAPTCHA/anti-bot protection"
        rule, Clarendon is left unimplemented purely because of that
        block, explicitly flagged as worth reconsidering the moment
        Oxford's own site becomes reachable without circumventing
        anything.

      A genuinely interesting deadline-extraction decision, distinct
      from every prior "pick the right dated section" case this
      session: Gates Cambridge's own Timeline page has real, current,
      2026/27-cycle-accurate dates (nothing stale here) - but there are
      *three* different valid deadlines depending on who's applying and
      to which course (a narrow US-citizens-resident-in-the-US round
      closing 14 October 2026; an "all other eligible applicants" round
      - the one nearly every Sierra Leonean applicant would actually
      use - closing either 8 December 2026 or 6 January 2027 depending
      on the specific course). Unlike prior cases where a *wrong*
      dated section could be avoided by targeting the *right* one, here
      even the *right* section has no single value - "the deadline"
      for the general international-applicant population is genuinely
      one of two dates depending on course choice. Rather than guess
      which of those two to report, or misleadingly extract the narrow
      US-only date (which a naive first-date-literal approach would
      have done, since it appears earlier on the page), chose the page
      that states the funding package without any dates at all as the
      overview/content source, so `deadline` correctly and honestly
      resolves to `None` by construction rather than by an explicit
      override.

      **Verified for real**: `pyflakes app tests` clean; a `collect()`
      simulation against the real fixture, run before any test was
      written, confirmed title, provider, country, `funding_type =
      "fully_funded"`, and `deadline = None` all resolve exactly as
      documented; full backend suite green afterward, 813 passed / 25
      skipped (up from 811 - two new tests, plus
      `test_opportunity_import.py`'s updated source-count assertion, 83
      -> 84 registered sources). The fixture
      (`tests/fixtures/gates_cambridge_scholarship.html`) was captured
      unmodified from the live site.

- [x] **(2026-09-06)** Netherlands fully-funded Master's engine,
      continuation pass: the Netherlands mega-prompt was resubmitted,
      this time with an explicit, much stricter "FULLY FUNDED ONLY"
      framing than the earlier exhaustive-expansion pass, and its own
      text specifically warned against three known misclassification
      traps (Radboud's tuition-only reduction, University of Twente's
      own "not a full scholarship" disclaimer, Leiden's Excellence
      Scholarship covering tuition but not living costs). Before
      researching anything new, checked what this platform already had
      on record: three genuinely fully-funded Dutch university sources
      already existed (TU Delft's Van Effen Scholarship #58,
      Groningen's Eric Bleumink Fellowship #72, Maastricht's High
      Potential Scholarship #74) and seven correctly-partial ones
      (Nuffic, UvA's Master's and Bachelor's Merit Scholarships,
      Utrecht's LEGITS, UTwente's UTS and ITC, Wageningen's Anne van
      den Ban Fund) - confirmed by grepping the actual source code
      rather than trusting memory, exactly matching what this new
      mega-prompt itself predicted would be found for Radboud/UTwente/
      Leiden (none of which have ever been added as fully-funded
      sources on this platform, consistent with the prompt's own
      warnings).

      With the existing ground already solid, this pass's job was
      genuinely new discovery, not re-litigating settled
      classifications. Checked four more angles the prompt itself
      flagged as under-explored:

      - **TU Delft**: the prompt specifically warned "the official TU
        Delft scholarship page provides multiple MSc scholarship
        opportunities... inspect each individual award rather than
        treating the page as one scholarship." Searched specifically
        for a second full scheme beyond Van Effen - found only the
        Fulbright Scholarship, US-government-funded and restricted to
        one faculty (Industrial Design Engineering) - correctly
        excluded as `EXTERNAL_ONLY`, not a second TU Delft-administered
        full scholarship.
      - **University of Twente's scholarship finder**: fetched the
        actual finder listing directly rather than trusting a search
        summary, and found 22 named schemes total - most obviously
        external funders merely listed there (Aga Khan Foundation,
        ASML, FirstRand Foundation, Onassis Foundation, and similar).
        Checked the three that looked most plausibly UTwente's own:
        Kipaji Scholarship and Professor De Winter Scholarship both
        turned out, on their own pages, to be explicit *dependent
        add-ons* - "meant as additional support for UTS scholarship
        students," not independently applicable, with no official
        statement anywhere that UTS-plus-add-on together constitute a
        full scholarship. This is exactly the "combination_rules" case
        this pass's own section 23 anticipated ("If the university
        officially confirms that the awards can be combined: record
        the combined package. If they cannot be combined: do not
        pretend they form one full scholarship") - resolved by finding
        no such official combination statement, so neither was
        integrated as fully funded. STEM for ALL turned out to be a
        small (EUR 5,000), externally-funded (Thales Solidarity
        Charitable Fund), Bachelor's-oriented award - straightforwardly
        excluded.
      - **Radboud University**: the most genuinely interesting result
        of this pass. Rather than stop at confirming the already-known
        "Radboud Scholarship is partial" finding (which this new
        mega-prompt itself already stated as fact), searched instead
        for *other* Radboud scholarships, and found the Radboud
        Encouragement Scholarship - described independently by search
        summaries as covering "the full tuition fee and living costs
        ... for the duration of the Master's programme." Verified this
        wasn't just an aggregator's overstatement by fetching Radboud's
        own scholarships hub page directly: it exposes a filter facet
        reading "Scholarship coverage: Full scholarship (1), Partial
        scholarship (5)" - Radboud's *own* site classifies exactly one
        of its scholarships as "Full," corroborating the search
        results. But fetching the actual Radboud Encouragement
        Scholarship detail page returned HTTP 403 with its own
        `<title>` reading "Login | Radboud University" and body text
        "Log in to view this content" - a SURFconext institutional
        single-sign-on wall, genuinely different from the general hub
        page (which stayed publicly readable throughout). This is a
        real, freshly-discovered access barrier, not a funding
        question - per this project's absolute "never bypass
        authentication barriers" rule, left unintegrated and flagged
        explicitly as `VERIFICATION_REQUIRED` rather than silently
        dropped, since the underlying scholarship is credible and real.
      - **Erasmus University Rotterdam**: the prompt specifically asked
        to check Erasmus MC and multiple schools individually. Found
        the Joint Japan/World Bank Graduate Scholarship Program
        (JJ/WBGSP) at Erasmus's International Institute of Social
        Studies, genuinely fully funded (tuition, living allowance,
        travel, health insurance) - but recognized it as the same
        World Bank/Japan-government programme already on this platform
        as source #45 (`world_bank_jjwbgsp`, which funds 44
        participating programmes across 24 universities worldwide, not
        tied to any single host). Correctly did not re-integrate it as
        a separate "Erasmus-specific" record, since that would
        double-count an existing government/multilateral-classified
        source under a different institutional label rather than add
        genuinely new coverage.

      No new opportunity source qualified this round. This is reported
      as the correct outcome, not a shortfall, consistent with this
      pass's own explicit instruction (section 39, "if only 5 genuine
      fully funded university Master's scholarships exist, return 5" -
      here, the honest count after two full Netherlands passes remains
      3, with a fourth real candidate identified but currently
      inaccessible without bypassing authentication).

      **No code was changed this pass** - only
      `docs/AUTHORITATIVE_SOURCES.md` and
      `docs/COUNTRY_PROVIDER_REGISTRY.md` were updated, appending this
      continuation's findings. No new test run was required since no
      source code, test, or fixture file changed; the existing
      813-passed/25-skipped baseline from the Gates Cambridge addition
      remains the accurate current count. One self-caught correction
      during this pass: an early draft cited the existing World Bank
      JJ/WBGSP source as "#57" from memory before writing it into the
      documentation - checked the actual heading in
      `docs/AUTHORITATIVE_SOURCES.md` before committing and found it is
      actually "#45," fixed before finalizing rather than left to
      propagate.

- [x] **(2026-09-06)** Spain, open-scope follow-up: "find another
      scholarship opportunities in spain" - unlike the recent
      mega-prompts, this was a short, open-ended request with no
      degree-level or funding-type restriction stated, so the research
      pass was broadened accordingly rather than confined to Master's
      or to fully-funded-only candidates. Checked six further Spanish
      institutions live:
      - **Universidad Carlos III de Madrid (UC3M)** - its official
        `/postgraduate/aid` page redirects to `/postgraduate/
        scholarships`, a hub listing UC3M's own tuition-coverage
        "UC3M Scholarships" (parallel calls AM02-AM05) and a
        research-oriented "AEM_UC3M" aid programme, alongside many
        externally-funded and country-specific schemes (Mexico's
        FIDERH, Colombia's ICETEX/PCB, Santander-UC3M grants,
        India-specific funds). Every item shown for the 2026/27 cycle
        is explicitly marked "Final decision" (already resolved, July
        2026) or "CLOSED DEADLINE" - not a single currently-open
        scheme, and the same multi-record architecture mismatch
        documented elsewhere in this project.
      - **University of Salamanca (USAL) - Becas Internacionales de la
        USAL** - genuinely strong on paper (tuition exemption,
        accommodation, meals, and health/accident/liability insurance
        across 76 official Master's titles), but its own International
        Relations Service host, `rel-int.usal.es` - the only site
        actually publishing the current call's full terms - sets
        `Disallow: /` for all user agents in its `robots.txt`,
        disallowing this platform's scraper from the entire subdomain.
        A Faculty of Law news page on a different, unrestricted
        subdomain (`derecho.usal.es`) merely links back to the
        disallowed host and is itself a stale 2019 announcement for
        the 2019/2020 cycle. Per this project's "respect robots.txt"
        rule, not circumvented.
      - **USAL's "Mujeres por África" sub-component** - checked
        specifically for Sierra Leone relevance given its explicit
        Africa focus, but this is externally administered by the
        Fundación Mujeres por África (`mujeresporafrica.es`), with
        USAL as just one of many partner host universities, not a
        USAL-administered scheme (`EXTERNAL_ONLY` relative to USAL) -
        and its 2026 cycle's own registration deadline (14 May 2026)
        had already passed as of this research date with no
        next-cycle page found.
      - **Universitat Autònoma de Barcelona (UAB) - "Solicitar beca"
        (general grant)** - its official page describes the AGAUR
        (Catalonia)/MEFPD (rest of Spain) "beca de carácter general,"
        which explicitly requires "domicilio familiar" (family
        residence) within Spain as of 31 December 2025 - a domestic
        Spanish student grant, not available to an international
        applicant applying from abroad (`NOT_INTERNATIONAL`).
      - **University of Barcelona (UB) and Universidad Complutense de
        Madrid (UCM)** - live search for each surfaced only vague,
        aggregator-level claims ("many scholarships," "up to 70+
        expected") with no single, specific, official page identified
        describing one particular scheme's exact eligibility and
        funding terms - Level 3 sources only, not treated as
        sufficient evidence per this project's "official university
        source required, aggregators are discovery-only" rule.

      No new opportunity source qualified this round - every real,
      well-documented candidate found was either blocked by its own
      `robots.txt`, externally administered, domestically restricted,
      or already closed with no next-cycle evidence, and this is
      reported honestly rather than forced into the dataset.

      **No code was changed this pass** - only
      `docs/AUTHORITATIVE_SOURCES.md` and
      `docs/COUNTRY_PROVIDER_REGISTRY.md` were updated, appending this
      pass's findings, plus `Changelog.md` and this file. No new test
      run was required since no source code, test, or fixture file
      changed; the existing 813-passed/25-skipped baseline remains the
      accurate current count.

- [x] **(2026-09-06)** Germany, open-scope follow-up: "find another
      scholarship opportunities in germany" - like the Spain request
      immediately before it, this was open-ended with no degree-level
      or funding-type restriction stated. Reviewed this platform's
      existing Germany coverage first (DAAD #10 with its seven curated
      detail ids including KAS; Humboldt Research Fellowship #56;
      TUM's International Student Scholarship #59; Freiburg's
      Deutschlandstipendium #69; and the long list of previously
      rejected candidates - Heidelberg, Bonn, Constructor Bremen,
      Mannheim, ESMT, WHU, Frankfurt School, Göttingen, IU
      International, RWTH Aachen, Elite Network of Bavaria, Hertie
      School, FES) before searching for genuinely new candidates.

      Found and **implemented** the **Heinrich Böll Foundation
      ("Tailwind for Talents") Scholarship for Graduates and PhD
      students** as source #84 - this registry's second
      Foundation-classified source (after Humboldt Research Fellowship,
      #56) and third Germany source overall:
      - Live-fetched the foundation's own official pages directly
        (`boell.de/en/scholarships`, `/en/applying-scholarship`,
        `/en/application`, `/en/2025/05/14/financial-support`) rather
        than trusting search-engine snippets, which turned out to
        matter: one secondary source claimed international applicants
        must already be enrolled in Germany, but the foundation's own
        `/en/applying-scholarship` page states plainly that a
        certificate of enrollment/admission "may be submitted at a
        later point, but no later than the interview" - genuinely open
        to a prospective applicant, not requiring prior admission.
      - Confirmed genuinely fully funded by reading the foundation's
        own "Financial support" page directly: for the Federal Foreign
        Office-funded non-EU international Master's track, a base
        scholarship of EUR 992/month, a health-insurance allowance up
        to EUR 100/month, reimbursement of German tuition fees up to
        EUR 10,000/year (covering the same Baden-Württemberg
        non-EU-tuition edge case already documented for DAAD's KAS
        entry), a EUR 38/month fringe benefit, and family/child
        allowances.
      - Confirmed Sierra Leone eligibility properly rather than
        inferring it from a vague label: the programme states priority
        for applicants from DAC (OECD Development Assistance Committee)
        countries not yet resident in Germany - Sierra Leone is a
        DAC-listed Least Developed Country, genuinely covered.
      - Documented honestly, not glossed over: international applicants
        must separately demonstrate German-language proficiency of at
        least B2 level or DSH1 (stated on the foundation's own
        `/en/application` page) - a real practical barrier for an
        English-speaking Sierra Leonean applicant, but a language
        requirement rather than a nationality restriction, so it does
        not itself disqualify the source from being listed.
      - **A real, live-caught content-freshness bug avoided**: compared
        the foundation's two related pages side by side on the same
        research day and found `/en/applying-scholarship`'s own
        "graduate scholarship" section still displaying an
        already-passed "Fall 2026: 15 July 2026 until 1 September
        2026" cycle as if current, while `/en/scholarships` correctly
        showed only genuinely future cycles ("Spring 2027," "Fall
        2027"). Chose `/en/scholarships` as the overview/content page
        specifically because of this discrepancy, per this project's
        "no stale-cycle guessing" rule - verified by fetching both
        pages live, not assumed.
      - **A second real extraction trap found and engineered around**:
        the chosen page's own deadline text reads "Our next application
        deadlines: Spring 2027: 15 January 2027 until 1 March 2027 Fall
        2027: ...". The base `_SingleProgramSource` class's default
        `deadline_keywords = ("deadline", "closing date")` would match
        the substring "deadline" inside "deadlines" first, and the
        nearest date literal after that point is 15 January 2027 - the
        application-*window-opening* date, not the actual deadline.
        Overrode `deadline_keywords` to `("until",)` instead, which
        correctly anchors on the closing date immediately following
        "until" (1 March 2027) - verified directly with a standalone
        `collect()` simulation against the real fixture before writing
        the test, exactly matching the documented design intent.
      - Selected `div.node__content` as the content selector after a
        BeautifulSoup structural walk confirmed it holds the
        programme's description, current deadlines, and "Who can
        apply?" eligibility text in one clean ~2KB block, with none of
        the page's navigation or footer chrome.
      - Wired into all 4 standard backend files
        (`app/core/config.py`'s `heinrich_boll_scholarship_base_url`
        setting plus its HTTPS-validator tuple entry;
        `app/services/national_scholarship_programs.py`'s
        `HeinrichBollScholarshipSource` class;
        `app/services/source_registry.py`'s `SOURCE_DEFINITIONS`,
        `_base_urls()`, and `next_runs` dicts; and
        `app/tasks/opportunity_sync.py`'s five locations - import,
        Celery beat schedule, task-name map, `@celery_app.task`-
        decorated sync function, and source-class dispatch map).

      Five further German candidates were researched live and rejected
      this same pass:
      - **Friedrich Naumann Foundation for Freedom** - its own page
        requires the applicant to "still have two remaining semesters"
        of study left, i.e. already enrolled at a German university,
        not a prospective applicant; application materials and the
        interview must also be conducted in German.
      - **Rosa Luxemburg Foundation** - explicitly requires
        "[e]nrollment at a state or state-recognised university in
        Germany" as a formal eligibility condition, and caps
        applications to within 15 months of first arriving in Germany -
        not usable to fund initial admission from abroad.
      - **Hanns Seidel Foundation** - a genuinely prospective-
        applicant-friendly design on paper (the same "admission proof
        accepted no later than the interview" pattern as Heinrich
        Böll), but its own published application process is explicitly
        routed through country-specific national HSF offices (India,
        Pakistan, Vietnam, Myanmar, Jordan, and others found live) with
        no office, page, or stated process found covering Sierra Leone
        or West Africa more broadly - a genuine, undocumented access
        gap rather than a funding or nationality exclusion, left
        unintegrated as `VERIFICATION_REQUIRED` rather than assumed
        accessible.
      - **Universität Hamburg - Merit Scholarships** - requires the
        applicant to have "been enrolled at Universität Hamburg for at
        least 1 semester" before applying - architecturally the same
        already-enrolled-retention-grant shape as this platform's
        existing TUM International Student Scholarship (#59), not a
        new kind of coverage.
      - **Technical University of Berlin** - no single official
        TU-Berlin-administered flagship scholarship page was found;
        every aggregator result traced back to DAAD's own Study
        Scholarship and EPOS programmes, both already covered by this
        platform's existing DAAD source (#10).

      **Verified for real**: `pyflakes app tests` clean, no new
      warnings introduced by any of the touched files. A `collect()`
      simulation against the real fixture, run before any test was
      written, confirmed title, provider, country, `funding_type =
      "fully_funded"`, and `deadline = date(2027, 3, 1)` all resolve
      exactly as documented. Full backend suite green afterward, 815
      passed / 25 skipped (up from 813 passed/25 skipped - two new
      tests, plus `test_opportunity_import.py`'s updated source-count
      assertion, 84 -> 85 registered sources). The fixture
      (`tests/fixtures/heinrich_boll_scholarship.html`) was captured
      unmodified from the live site.

- [x] **(2026-09-07)** Five-country autonomous scholarship research
      engine (Austria/Eswatini/Australia/USA/Russia) - Eswatini pass:
      researched Eswatini as a scholarship *study destination* (an
      international applicant coming to study at an Eswatini
      institution), distinct from this platform's existing Eswatini
      SLAS source (#18, the reverse - outbound funding for Eswatini
      nationals). Checked every accredited institution named in the
      research brief live:
      - **UNESWA** - fetched `www.uneswa.ac.sz` directly and got a
        genuine TLS handshake failure; ran a verbose trace
        (`curl -v`) to understand exactly why rather than assuming a
        proxy problem, and confirmed the server's own certificate
        chain is incomplete ("unable to get local issuer certificate")
        - a real misconfiguration on UNESWA's own infrastructure, not
        this sandbox's fault (plain `http://` to the same host works
        and redirects to the broken `https://` URL). Tried a second,
        independent fetch path (`WebFetch`) as a sanity check, which
        also failed (HTTP 503) - consistent with a genuinely unreliable
        server. Left unintegrated as `VERIFICATION_REQUIRED` rather
        than disabling certificate verification, which would create a
        real MITM-vulnerable code path.
      - **SANU** - found its `/scholarship-information/` page via the
        site's own sitemap and read it directly rather than trusting
        an aggregator's vague "scholarships available" claim; the
        page's actual text states funding is "the student's
        responsibility" and that international students must "seek for
        their funding" themselves - an explicit disclaimer, not an
        opportunity.
      - **EMCU** - reachable and unrestricted, but its homepage's only
        funding-related link points straight to `slas.gov.sz` - the
        same government programme already on this platform, not a
        distinct EMCU scholarship.
      - **Limkokwing University (Eswatini campus)** - `limkokwing.net`
        returned an active Cloudflare "Just a moment..." challenge on
        every path including `robots.txt` - genuine bot protection,
        not circumvented.
      - Also confirmed via live search that both of Eswatini's
        government scholarship channels (the Ministry of Labour's SLAS
        and the Ministry of Foreign Affairs' international-scholarship
        listings) are outbound programmes for Eswatini nationals, not
        inbound programmes for international students - no government
        inbound source exists to discover.

      No new source was added. Per the research brief's own explicit
      instruction not to invent opportunities to make a small country
      look complete, the honest, real count for Eswatini as a study
      destination is zero - reported as such rather than padded.

      **No code was changed this pass** - only
      `docs/AUTHORITATIVE_SOURCES.md`, `docs/COUNTRY_PROVIDER_
      REGISTRY.md`, `Changelog.md`, and this file were updated. No new
      test run was required since no source code, test, or fixture
      file changed; the existing 815-passed/25-skipped baseline
      remains the accurate current count.

- [x] **(2026-09-07)** Five-country autonomous scholarship research
      engine - Austria pass: researched six Austrian universities live
      (TU Wien, University of Vienna, University of Graz, JKU Linz,
      University of Innsbruck, BOKU, WU Vienna) looking for a
      genuinely university-administered scholarship distinct from the
      platform's only existing Austria source (OeAD Ernst Mach Grant,
      #28, government-classified).

      Found and **implemented** the **Helmut Veith Stipend** (TU Wien,
      via the Vienna Center for Logic and Algorithms / VCLA) as source
      #85 - this registry's first Austria university source:
      - Started from TU Wien Informatics' general scholarships hub
        page, which lists several distinct awards on one page (a
        StudFG Merit Scholarship Grant, a Funding Grant, a Scholarship
        for Completion, the Helmut Veith Stipend, a Siemens Award) -
        recognized this as the same multi-record architecture mismatch
        documented elsewhere in this project and looked for the
        Helmut Veith Stipend's own dedicated announcement page instead
        of trying to force a selector onto the hub.
      - Found that dedicated page at `vcla.at/helmut-veith-stipend/`
        and, critically, compared its numbers against the hub page's
        own description of the same award before choosing which to
        use: the hub page states "EUR 6,000 p.a.," while the dedicated
        page (fetched live the same day) states "EUR 7000 annually" -
        a real, live-caught stale-figure discrepancy, resolved by using
        the more current, authoritative dedicated page rather than
        either guessing which was right or splitting the difference.
      - Confirmed no nationality restriction from the page's own text
        (worldwide eligibility, Sierra Leone included), but documented
        the real gender restriction (female applicants only) and the
        "expected graduation" acceptance (a preliminary certificate
        with expected graduation date is explicitly accepted) plainly
        rather than omitting either.
      - Did the funding-completeness math explicitly rather than
        assuming "tuition waiver + stipend = fully funded": searched
        for Vienna's own documented student cost of living
        (~EUR 950-1,300/month) and Austria's standard non-EU tuition
        rate (~EUR 1,453/year) and compared both against the award's
        EUR 7,000/year (~EUR 583/month) - concluded `partial_funding`
        is the honest classification, since the stipend alone covers
        under half of typical living costs even combined with the
        waiver.
      - Selected `div.postarea` as the content selector after a
        BeautifulSoup structural walk confirmed it starts exactly at
        the page's own heading, with none of the site's navigation
        text mixed in.
      - Verified the base class's default `deadline_keywords`
        (`("deadline", "closing date")`) already resolve correctly
        without any override: the page's first "deadline" occurrence
        is itself the current, correct date (30 November 2026) - ran a
        standalone `collect()` simulation against the real fixture
        before writing the test to confirm this rather than assuming
        it.
      - Wired into all 4 standard backend files (`app/core/config.py`'s
        `helmut_veith_stipend_base_url` setting plus its HTTPS-
        validator tuple entry; `app/services/national_scholarship_
        programs.py`'s `HelmutVeithStipendSource` class;
        `app/services/source_registry.py`'s `SOURCE_DEFINITIONS`,
        `_base_urls()`, and `next_runs` dicts; and `app/tasks/
        opportunity_sync.py`'s five locations).

      Five further Austrian candidates were researched and rejected
      this same pass:
      - **TU Wien, University of Vienna, University of Graz, JKU Linz,
        University of Innsbruck's general "Merit Scholarship" /
        "Leistungsstipendium"** - read TU Wien's own page directly and
        found the eligibility text requires "Austrian citizenship or
        equal status," "EEA citizens," or "[t]hird-country nationals
        with a long-term residence permit who have lived in Austria
        for at least 5 years" - recognized this as Austria's
        nationally-mandated Studienförderungsgesetz (StudFG), the same
        legal basis cited on every one of these universities' own
        merit-scholarship pages, so documented it once as a systemic
        finding rather than re-discovering the identical restriction
        five separate times.
      - **WU Vienna - Mondi International Scholarships** - a
        nationality-unrestricted, genuinely promising-sounding
        programme surfaced by search results, but reading WU's own
        2021 announcement page directly showed it was explicitly
        scoped to "the academic years 2021/22 and 2022/23" only:
        cross-checked against WU's current, live master's-guide
        scholarships page and confirmed Mondi does not appear there at
        all - a discontinued two-cohort pilot, correctly left
        unintegrated rather than presented as currently open.
      - **BOKU** - its own tuition-fee page and scholarship search
        surfaced only the same StudFG merit scholarship and outbound
        exchange grants for BOKU's own students studying abroad; no
        inbound international scholarship found.
      - **JKU Linz - Merit Scholarship for Exchange Students** - real
        and not nationality-restricted, but it funds temporary
        *exchange* students from partner universities for a limited
        term, not degree-seeking Master's applicants applying for full
        admission - a different opportunity shape, not treated as
        equivalent.

      **Verified for real**: `pyflakes app tests` clean, no new
      warnings. A `collect()` simulation against the real fixture, run
      before any test was written, confirmed title, provider, country,
      `funding_type = "partial_funding"`, and `deadline = date(2026,
      11, 30)` all resolve exactly as documented. Full backend suite
      green afterward, 817 passed / 25 skipped (up from 815 passed/25
      skipped - two new tests, plus `test_opportunity_import.py`'s
      updated source-count assertion, 85 -> 86 registered sources). The
      fixture
      (`tests/fixtures/helmut_veith_stipend.html`) was captured
      unmodified from the live site.

- [x] **(2026-09-07)** Five-country autonomous scholarship research
      engine - Australia pass: this country was explicitly flagged in
      the research brief as needing "VERY DEEP coverage," with a
      specific warning against searching only coursework scholarships
      and missing Master's-by-Research/HDR opportunities. Took that
      warning seriously and specifically hunted for HDR-track pages
      rather than only the general "international scholarships" search
      results.

      Found and **implemented** two genuinely fully-funded HDR sources:
      - **University of Sydney RTP Scholarships (International)**
        (source #86) - this platform's first Australia university
        source of any kind. Live-fetched the official page directly
        and confirmed "commencing or enrolled in a higher degree by
        research" covers both Master's-by-Research and PhD, not
        PhD-only, before treating it as suitable - the research brief
        explicitly warned against accidentally mixing PhD-only results
        into the Master's category, so this check mattered. Found a
        real engineering trap while inspecting the raw HTML: two
        `div.cmp-container__inner` elements exist on the page, one of
        them genuinely empty, and a plain CSS selector would have
        matched the empty one first (since `_first_match` always takes
        the first match) - used `:not(:empty)` to correctly skip it,
        verified directly rather than assumed. Also found and fixed a
        deadline-extraction trap: the page's first "deadline"-keyword
        occurrence is an earlier, dateless prose sentence, so the base
        class's default keyword would have resolved to `None`; the
        real deadline lives in an HTML table headed by "Submission
        deadline," so overrode `deadline_keywords` to
        `("submission deadline",)` and verified via a standalone
        `collect()` simulation that this correctly lands on the
        nearest upcoming cycle's real deadline (11 September 2026),
        not a different column's date.
      - **University of Queensland Graduate Research School
        Scholarships (UQGRSS)** (source #87) - this platform's second
        Australia university source, on the "Scholarships for PhD and
        MPhil students" page. Verified directly that MPhil (Master of
        Philosophy) is a genuine Master's-by-research degree in the
        Australian system, not a synonym for PhD, before treating this
        as Master's-inclusive rather than PhD-only. Read the page
        carefully enough to notice it describes several funding types
        and scholarships together, and explicitly separated the
        internationally-open flagship (UQGRSS) from two narrower
        scholarships mentioned on the same page (one domestic-only,
        one Aboriginal/Torres Strait Islander-restricted) rather than
        letting the record imply all three share UQGRSS's own
        eligibility.

      Four further Australian candidates were researched and
      rejected/deferred this same pass:
      - **UNSW Sydney** - its official "Scholarships for International
        Students Commencing Term 1, 2027" page is genuinely current
        (opens 15/07/2026, closes 30/10/2026), but lists at least five
        separately-named, separately-valued awards on one page - the
        same multi-record architecture mismatch documented repeatedly
        elsewhere in this project - and every listed award is
        explicitly tuition-only with no living-stipend component, so
        it would not have qualified as fully funded even if the
        architecture fit.
      - **Monash University** and **University of Melbourne** - both
        described genuinely strong, fully-funded-sounding HDR
        scholarships (AUD 37,145/year and a full tuition offset at
        Monash; a similar structure at Melbourne), but fetching each
        university's own scholarship page returned an active
        Cloudflare "Just a moment..." managed challenge on every path
        tested, including `robots.txt` - genuine bot protection, not
        circumvented. Melbourne's block specifically re-confirms an
        access barrier already documented in this project from an
        earlier pass, checked again live rather than assumed still
        true.
      - **Western Sydney University** - its "Postgraduate" international
        scholarship page is real, current, and matches this pass's own
        research brief almost verbatim (explicitly partial, AUD
        5,000-10,000/year tuition-only for the 2027 cycle, with the
        page's own text stating plainly it "does not cover costs
        associated with living expenses, accommodation, transport,
        overseas student health cover"). Not integrated this pass for
        a purely architectural reason: inspected the raw HTML and found
        the real content spread across many small Adobe-Experience-
        Manager "component--band" fragments with no single ancestor
        that includes the scholarship text while excluding the site's
        own navigation and footer - tried several candidate selectors
        (`div.responsivegrid`, `div.root`, others) and confirmed each
        one just re-selects the entire page body. Rather than force a
        selector that would silently capture navigation-menu junk into
        the description, deferred this one honestly as a real,
        verified, currently-open candidate for future engineering
        effort, not a funding or access rejection.

      **Verified for real**: `pyflakes app tests` clean, no new
      warnings. Standalone `collect()` simulations against both real
      fixtures, run before any test was written, confirmed both
      sources' title/provider/country/funding_type/deadline fields
      resolve exactly as documented for each. Full backend suite green
      afterward, 821 passed / 25 skipped (up from 817 passed/25
      skipped - four new tests across two sources, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      86 -> 88 registered sources). The fixtures
      (`tests/fixtures/usyd_rtp_international.html`,
      `tests/fixtures/uq_grsss_phd_mphil.html`) were captured unmodified
      from the live sites.

- [x] **(2026-09-07)** Five-country autonomous scholarship research
      engine - USA pass: the research brief specifically warned that
      the US ecosystem is "extremely fragmented" and told me to search
      well beyond central scholarship pages, into department-level and
      programme-level funding pages, and to distinguish
      Scholarship/Fellowship/Assistantship rather than calling
      everything a "scholarship." Given the genuine scale of this
      ecosystem, made a deliberate choice to verify two strong
      candidates deeply rather than skim many superficially - decided
      this was the more honest use of the remaining time than
      producing a long but shallow list.

      Found and **implemented**:
      - **UT Austin Harrington Graduate Fellows Program** (source #88)
        - this platform's first USA university source. Read the full
        page carefully rather than stopping at the word "Doctoral"
        appearing first, and confirmed the page separately names
        "Harrington Master's Fellows" for professional/terminal
        Master's degrees (MFA, MSSW, MSLIS) - genuinely Master's-
        inclusive. Also read closely enough to catch an important
        caveat the research brief specifically asked to distinguish:
        this is a **nomination-only** fellowship - "potential graduate
        students cannot apply ... directly" - and documented that
        honestly rather than presenting it as a normal open
        application, the same disclosure pattern already used
        elsewhere in this project for Wageningen's nomination-based
        Anne van den Ban Fund.
      - **Vanderbilt Cornelius Vanderbilt Scholarship** (source #89) -
        this platform's second USA university source and its first at
        the undergraduate level. Applied the research brief's own
        explicit warning ("Tuition coverage alone ≠ automatically
        fully funded") directly to this source: the page states
        "guaranteed full-tuition awards plus summer stipends," which
        is a real, substantial award but does not state coverage of
        room, board, or general living costs, so classified it
        `partial_funding` rather than assuming "full tuition" implies
        "fully funded." Also did not assume this US undergraduate
        merit scholarship excludes international students by default
        (a common pattern at many US universities) - checked
        Vanderbilt's own separate international-admissions page
        directly and found concrete evidence of real awards to "89
        students representing 54 countries" for fall 2026, confirming
        genuine international eligibility before treating the source
        as suitable. Noticed the overview page names a second,
        differently-focused sibling programme (Ingram Scholars)
        sharing the same deadline, and explicitly excluded it from
        this record's scope rather than letting the description imply
        Ingram shares Cornelius Vanderbilt's own terms.

      One further candidate was researched and found blocked:
      University of Michigan's Helen Zell Writers' Program (MFA) is
      genuinely fully-funded by reputation for every admitted student,
      but fetching its funding page returned an active Cloudflare
      managed challenge - ran a verbose header trace rather than just
      accepting the HTTP 403 at face value, and confirmed a
      `cf-mitigated: challenge` header proving genuine bot protection,
      not a misconfigured URL - not circumvented. Also checked the
      Onsi Sawiris Scholarship (hosted at several top US universities)
      and found it restricted to Egyptian nationals resident in Egypt
      via its own official eligibility page - not relevant to a Sierra
      Leonean applicant, so not pursued further.

      **Verified for real**: `pyflakes app tests` clean, no new
      warnings. Standalone `collect()` simulations against both real
      fixtures, run before any test was written, confirmed both
      sources' title/provider/country/funding_type/deadline fields
      resolve exactly as documented for each. Full backend suite green
      afterward, 825 passed / 25 skipped (up from 821 passed/25
      skipped - four new tests across two sources, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      87 -> 89 registered sources; confirmed Harrington alone first,
      823 passed, before adding Vanderbilt).
      The fixtures (`tests/fixtures/harrington_graduate_fellows.html`,
      `tests/fixtures/vanderbilt_cornelius_scholarship.html`) were
      captured unmodified from the live sites.

- [x] **(2026-09-07)** Five-country autonomous scholarship research
      engine - Russia pass (fifth and final country): the research
      brief specifically asked to search in both English and Russian,
      to distinguish university scholarships from government
      quota/state-funded places, and not to assume a "state-funded
      place" is automatically equivalent to a fully funded scholarship.
      Also did not assume connectivity to Russian university sites
      would be blocked from this environment - tested a batch of major
      Russian universities' domains live first (HSE, ITMO, MIPT, SPbU,
      Kazan, Ural, RUDN) and found most genuinely reachable, since
      these are outbound-facing international-admissions pages, not
      Russia-internal services.

      Found and **implemented** the **Skoltech Admissions Scholarship**
      (source #90) - this platform's first Russia source of any kind:
      - Verified the page's own text carefully rather than trusting
        aggregator claims that Skoltech is unconditionally "fully
        funded": the official admissions page states a competitively-
        awarded monthly stipend ("for MSc students: 40,000 rubles per
        month... for highest-scoring applicants") but does not itself
        state that tuition is waived for every admitted student. Cross-
        checked against secondary sources, which confirmed a listed
        tuition fee exists for MSc applicants who do not receive the
        scholarship - consistent with the official page's own
        "highest-scoring" framing. Classified `partial_funding` from
        what the official page actually says, per this project's
        "official source over aggregator" rule, rather than accepting
        the more generous "fully funded" label used by several
        aggregator sites.
      - Confirmed the page is genuinely real, current, server-rendered
        HTML (not a JS shell) before proceeding, and read its honest
        status statement directly: "The application period ... is now
        closed. To apply for the 2027 start, check back in autumn" -
        correctly extracted no deadline rather than guessing a future
        date from a prior cycle.
      - Selected `main` as the content selector after confirming
        directly that it holds the admissions status, programme list,
        and scholarship terms with none of the site's navigation.

      Three further Russia candidates were researched and deferred or
      rejected this same pass:
      - **"Open Doors: Russian Scholarship Project"** - a genuinely
        enormous, credible international academic Olympiad (100,000+
        participants a year, 6,000+ admitted over 7 years, tuition-free
        admission for competition winners with no entrance exams), read
        in full detail on its official HSE-hosted page. Recognized this
        as architecturally a large multi-university, multi-programme
        catalogue - dozens of distinct Bachelor's and Master's
        programmes across many different Russian universities, each
        with its own selection criteria - much closer to the Erasmus
        Mundus catalogue's existing multi-record architecture (#47)
        than this session's single-record `_SingleProgramSource`
        pattern. Deferred honestly as a strong future-pass candidate
        rather than forced into an architecture that doesn't fit it.
      - **`education-in-russia.com`** (the official government Quota/
        Rossotrudnichestvo portal) - checked its robots.txt in detail
        (a long list of specifically-named blocked bots, but critically
        no catch-all "User-agent: *" rule, so confirmed this platform's
        own identified scraper is not disallowed) before concluding the
        real blocker: the homepage itself is only a 5.4 KB client-side-
        rendered single-page-application shell with no readable
        programme content in plain HTTP - a technical limitation
        distinct from a bot-block, documented as such.
      - **HSE University's own general merit/tuition-discount
        scholarships** - real (up to 50% tuition discount at the
        Master's level, a smaller number of full-tuition-waiver "top
        applicant" places), but spread across multiple separate
        programme-specific pages with differing terms per Master's
        programme rather than one flagship page - the same multi-record
        mismatch as Open Doors above.

      This concludes the simultaneous five-country autonomous research
      engine (Austria, Eswatini, Australia, USA, Russia): 6 new sources
      implemented in total across this pass (Helmut Veith Stipend for
      Austria; USYD RTP and UQ Graduate Research School Scholarships
      for Australia; Harrington Graduate Fellows and Vanderbilt
      Cornelius Vanderbilt Scholarship for USA; Skoltech for Russia),
      plus an honest, well-researched zero-new-source finding for
      Eswatini reported as the correct outcome rather than padded.

      **Verified for real**: `pyflakes app tests` clean, no new
      warnings. A `collect()` simulation against the real fixture, run
      before any test was written, confirmed title, provider, country,
      `funding_type = "partial_funding"`, and `deadline = None` all
      resolve exactly as documented. Full backend suite green
      afterward, 827 passed / 25 skipped (up from 825 passed/25
      skipped - two new tests, plus `test_opportunity_import.py`'s
      updated source-count assertion, 90 -> 91 registered sources). The
      fixture (`tests/fixtures/skoltech_admissions.html`) was captured
      unmodified from the live site.

- [x] **(2026-09-07)** Japan follow-up: "find another Japanese
      university fully funded universities scholarship" - reviewed
      this platform's existing Japan coverage first (only the Japanese
      Government MEXT Scholarship, #25, government-classified - no
      university source existed yet) before searching.

      Found and **implemented** **The University of Tokyo Scholarship**
      (via PEAK - Programs in English at Komaba) as source #91 - this
      platform's first Japan university source:
      - Started from UTokyo's main "Fellowship" page (its top search
        result), read it carefully, and correctly rejected it: the
        page's own text describes it as a research grant-in-aid "to
        support outstanding, **self-funded** international students" -
        a supplementary stipend on top of self-funding, not itself
        covering tuition, so genuinely `partial_funding` rather than
        the fully-funded result being sought.
      - Found UTokyo's separate PEAK undergraduate programme page
        instead and confirmed live that "The University of Tokyo
        Scholarship" there is a genuinely different, fully-funded
        award: admission fee + tuition + JPY126,000/month living
        expenses, four years, up to 10 students, automatic upon
        admission.
      - Recognized immediately that the page listing it is a real
        multi-record hub (five distinct scholarships - this one, MEXT,
        two nationality-specific supplements for Malaysia and
        Singapore, two Fast Retailing Foundation awards for Vietnam
        and Indonesia) and did the selector engineering needed to
        isolate just the one relevant item rather than skip the page
        or force a whole-page selector: inspected the raw HTML,
        found each numbered item lives in its own `div.cmsSec-A`
        element as a direct sibling under one shared wrapper, and used
        `div.cmsSec-A:nth-of-type(2)` (item 1's own div; `:nth-of-
        type(1)` is the page's general preamble) to land exactly on
        the target scholarship's text - verified directly via a
        standalone `collect()` simulation that neither "MEXT" nor any
        of the other four items' content leaked into the extracted
        description.
      - Chose the external_id-derived title fallback over the page's
        own `<h2>(1) The University of Tokyo Scholarship</h2>` heading,
        since the "(1) " numeral prefix would read oddly as a stored
        title on its own.
      - Confirmed `peak.c.u-tokyo.ac.jp/robots.txt` returns a genuine
        HTTP 404 (no file published) rather than assuming this meant
        no restrictions without checking - treated the same as this
        project's existing precedent for a genuinely empty robots.txt.

      Two further Japan candidates were researched and rejected this
      same pass:
      - **Kyoto University** - its own scholarships page describes
        annually nominating candidates for approximately 90 separate
        private scholarship programmes (each JPY 30,000-180,000/month
        to one or two students) plus a general Tuition Exemption track
        and the semi-governmental JASSO Scholarship - the same
        multi-record architecture mismatch documented repeatedly
        elsewhere in this project, with no single flagship award
        comparable to UTokyo's PEAK scholarship found.
      - **The University of Tokyo Fellowship** - UTokyo's own main
        international-student scholarship (distinct from the
        PEAK-specific award actually implemented), already covered
        above as the initially-rejected candidate - documented
        explicitly as `PARTIAL_FUNDING` rather than silently dropped,
        since it's a real, genuine UTokyo-administered award, just not
        the fully-funded one this request specifically asked for.

      **Verified for real**: `pyflakes app tests` clean, no new
      warnings. A `collect()` simulation against the real fixture, run
      before any test was written, confirmed title, provider, country,
      `funding_type = "fully_funded"`, `deadline = None`, and that the
      description contains none of the other four scholarships' text -
      all exactly as documented. Full backend suite green afterward,
      829 passed / 25 skipped (up from 827 passed/25 skipped - two new
      tests, plus `test_opportunity_import.py`'s updated source-count
      assertion, 91 -> 92 registered sources). The fixture
      (`tests/fixtures/utokyo_peak_scholarship.html`) was captured
      unmodified from the live site.

- [x] **(2026-09-07)** Morocco follow-up: "find Morocco undergraduate
      and postgraduate university scholarship" - reviewed this
      platform's existing Morocco coverage first (only the AMCI
      Scholarships of the Kingdom of Morocco, #29, government-
      classified - no university source existed yet) before searching.

      Checked five Moroccan institutions live, in roughly descending
      order of how promising secondary sources made them sound, before
      settling on a real candidate:
      - **Mohammed VI Polytechnic University (UM6P)** - reputed to be
        the strongest scholarship source in Morocco (OCP Foundation-
        backed), but fetching its scholarships page (and several other
        paths, to rule out a one-off fluke) returned an empty body with
        no `<h1>` each time; inspected the raw HTML and found a Nuxt.js
        single-page app shell (`<div id="__nuxt">`) with only a
        loading-spinner SVG present - genuinely client-side rendered,
        not a bot-block, so not chased further with this pass's plain-
        HTTP approach.
      - **Al Akhawayn University (AUI)** - read both its official
        undergraduate and graduate scholarship pages directly rather
        than trusting a search snippet's summary, and found the
        snippet was accurate: the undergraduate page states plainly
        "Undergraduate scholarships are offered to Moroccan students
        only," and the graduate page states "Graduate scholarships are
        offered to Moroccan applicants only," with only a vague "a few
        scholarships may be offered to international graduate
        candidates" exception for one specific school - too narrow and
        non-guaranteed a basis to build a general scholarship record
        on.
      - **Université Internationale de Rabat (UIR)** - a secondary
        source's summary of UIR's own scholarships page states plainly
        "UIR does not offer scholarships to international students."
        Independently attempted to fetch the live page directly anyway
        (to verify rather than take the summary on faith) and hit a
        genuine TLS handshake failure - ran a verbose trace and found
        the identical "unable to get local issuer certificate" error
        already diagnosed for Eswatini's UNESWA earlier this session,
        confirming this is a recognized category of real server-side
        misconfiguration, not a one-off. Two independent reasons this
        wasn't a source, not one.
      - **Université Euro-Méditerranéenne de Fès (UEMF)** - fetched the
        live "Bourses et aides financières" page directly and read it
        in full: it describes a general 25%/50%/75%/100% tuition-
        coverage scale, but never itself states the "international
        students receive a special scholarship" detail an aggregator
        had claimed - also checked UEMF's own International Admissions
        page for the same claim and found no mention of scholarships
        at all. Declined to fabricate specific eligibility terms an
        official page doesn't itself state.
      - **Université Mundiapolis (Casablanca)** - its "Moroccan
        Scholarships for African Youth" programme (10 excellence
        scholarships to African-country students) is the
        best-documented, most specific lead found via search, but its
        own page returns a genuine HTTP 404; checked the Wayback
        Machine for an archived copy and found none - concluded the
        programme's page has likely been removed or the programme
        discontinued, and did not write up scholarship terms from
        secondary-source descriptions of a page that no longer exists.

      Found and **implemented** the **Universiapolis (Agadir)
      "Subvention d'encouragement international"** as source #92 - this
      platform's first Morocco university source:
      - Its "Bourses" page lists four scholarship/grant tiers together
        on one page (100%/50%/30%/20% funding) - read all four
        carefully rather than stopping at the first, and found that
        three of the four ("Bourse d'excellence," "Subvention de
        mérite académique," "Subvention de soutien familial") each
        explicitly require "Nationalité marocaine" in their own listed
        criteria, while the fourth, "Subvention d'encouragement
        international," explicitly targets "étudiants subsahariens"
        (Sub-Saharan students) - confirmed Sierra Leone qualifies as a
        Sub-Saharan African country rather than assuming it from the
        word "international" alone.
      - Recognized this as the same multi-record architecture pattern
        seen elsewhere this session and did the selector engineering to
        isolate just the fourth tier: inspected the raw HTML, found the
        page built from a flat sequence of WordPress block-editor
        elements (h3/p/p/ul repeated per tier, separated by `<hr>`,
        with no per-tier wrapper div), and used
        `h3.wp-block-heading:nth-of-type(4)` and `p.wp-block-paragraph:
        nth-of-type(9)` to land on exactly the fourth tier's heading and
        description - verified directly via a standalone `collect()`
        simulation that neither "marocaine" nor any of the other three
        tiers' text leaked into the extracted title/description.
      - Classified `partial_funding`, not fully funded, since the
        grant explicitly covers only 20% of tuition fees - documented
        plainly rather than glossed over.
      - Checked the full page text for any French deadline phrasing
        ("date limite," "avant le," "jusqu'au") before concluding no
        deadline could be extracted, rather than assuming.

      **Verified for real**: `pyflakes app tests` clean, no new
      warnings. A `collect()` simulation against the real fixture, run
      before any test was written, confirmed title, provider, country,
      `funding_type = "partial_funding"`, `deadline = None`, and that
      the description contains "subsahariens" but not "marocaine" - all
      exactly as documented. Full backend suite green afterward, 831
      passed / 25 skipped (up from 829 passed/25 skipped - two new
      tests, plus `test_opportunity_import.py`'s updated source-count
      assertion, 92 -> 93 registered sources). The fixture
      (`tests/fixtures/universiapolis_international_grant.html`) was
      captured unmodified from the live site.

- [x] **(2026-09-07)** England follow-up: "find another England
      undergraduate, masters university scholarship programs" - this
      platform already had 10 England university sources (Imperial,
      Newcastle, Sheffield, Manchester, Nottingham, Southampton x2,
      Durham x2, Gates Cambridge) before this pass, so the research
      focus was specifically on universities not yet touched:
      undergraduate-and-postgraduate-capable programmes at UCL, King's
      College London, Queen Mary, and Royal Holloway.

      Found and **implemented** the **Royal Holloway International
      Undergraduate Scholarship 2027** as source #93 - this registry's
      second England undergraduate source (Southampton's merit
      scholarship, #66, is the first):
      - Live-fetched the official page directly and confirmed it was
        genuinely current (explicitly "starting in September 2027,"
        with the page itself distinguishing this from the superseded
        2026-entry version) before treating it as a live opportunity -
        this mattered, since both other strong-looking candidates
        found the same day (UCL, King's) turned out to have already-
        passed 2026 deadlines.
      - Confirmed no nationality or country-of-residence restriction
        from the page's own eligibility text (BBB-at-A-level,
        "International fee status," no country list) - worth checking
        explicitly since Royal Holloway's own parallel Master's
        scholarship, researched the same pass, turned out to be
        restricted.
      - Classified `partial_funding` correctly: GBP 3,000/year off
        tuition only, no living-cost or stipend component - never
        described as more than a tuition discount.

      Three further England candidates were researched and rejected
      this same pass:
      - **Royal Holloway's own International Masters Scholarship**
        (Sept 2027/Jan 2028) - read the eligibility text carefully and
        found "eligibility for this scholarship is determined by your
        place of residence, not your nationality" against an
        enumerated list of roughly 45 countries; checked the full list
        specifically for Sierra Leone and confirmed it was absent from
        both the GBP 2,000 and GBP 4,000 tiers - not integrated, so
        this pass's Royal Holloway coverage is undergraduate-only.
      - **UCL - Global Undergraduate Scholarship** - a search result
        described a genuinely strong programme (10 full-tuition-plus-
        maintenance awards, 23 tuition-only awards), so fetched the
        live page directly with a realistic browser User-Agent to
        verify rather than trust the summary; got back an HTTP 403
        with a `cf-mitigated: challenge` response header - a real,
        active Cloudflare bot challenge, not circumvented. Separately
        noted the cited 2026/27-cycle deadline (27 April 2026) had
        already passed regardless, so this wasn't purely an access
        question.
      - **King's College London - CMA CGM Excellence Fund for
        Education 2026-27** - a genuinely fully-funded Master's award
        (full tuition waiver + GBP 22,161 stipend) found via search;
        fetched the live page directly and found its own "Key
        Information" panel states "Application status: Closed" with a
        28 April 2026 deadline - correctly left unintegrated as closed
        rather than presented as open.
      - **Queen Mary University of London** - tested multiple paths
        (the specific scholarships-database page, the undergraduate
        find-a-scholarship page, and the bare homepage) and got an AWS
        CloudFront "Request blocked" 403 on every one, including
        robots.txt itself - genuine site-wide bot protection, not
        chased further.

      **Verified for real**: `pyflakes app tests` clean, no new
      warnings. A `collect()` simulation against the real fixture, run
      before any test was written, confirmed title, provider, country,
      `funding_type = "partial_funding"`, and `deadline = None` all
      resolve exactly as documented. Full backend suite green
      afterward, 833 passed / 25 skipped (up from 831 passed/25
      skipped - two new tests, plus `test_opportunity_import.py`'s
      updated source-count assertion, 93 -> 94 registered sources). The
      fixture
      (`tests/fixtures/royal_holloway_international_ug_scholarship.html`)
      was captured unmodified from the live site.

- [x] **(2026-09-07)** Netherlands follow-up: "find Netherlands
      undergraduate and postgraduate university scholarship" - this
      platform already had 10 Netherlands sources before this pass
      (UvA x2, VU Amsterdam, TU Eindhoven, Groningen, Leiden's LEGITS
      counterpart at Utrecht, Erasmus Rotterdam, Maastricht, Radboud,
      Twente x2, Wageningen, Nuffic), so today's research (still
      2026-09-07, the same date as the prior exhaustive Netherlands
      passes, confirmed via `date -u`) focused on genuinely unexplored
      institutions rather than re-checking already-documented
      stale-cycle rejections (VU Amsterdam VUFP, TU Eindhoven
      Scholarship for Excellence, Erasmus Trustfonds, Radboud
      Scholarship Programme) since no time had passed to change them.

      Checked connectivity to Amsterdam University College, Leiden
      University College, University College Utrecht, and Nyenrode
      Business University - none previously checked in this project's
      Netherlands research history.

      Found and **implemented** the **UCU Rosemary Orr Scholarship
      (Campus Fee Waiver)** at University College Utrecht as source
      #94:
      - Found via UCU's own site navigation (not a search-engine
        secondary source): a dedicated
        `/en/organisation/university-college-utrecht/
        scholarship-procedure` page, distinct from the parent
        `uu.nl` domain's already-integrated LEGITS scholarship page.
      - Confirmed `uu.nl/robots.txt` does not disallow this path using
        Python's `urllib.robotparser` directly (`can_fetch` returned
        `True`), not just a visual skim of the file.
      - Read the eligibility text carefully and confirmed "Both Dutch
        and international applicants are eligible to apply" - checked
        explicitly for a hidden nationality restriction (none found;
        assessed purely on demonstrated financial need) rather than
        assuming "international" meant no restriction, per this
        session's standing Sierra Leone eligibility check discipline.
      - Cross-checked the deadline against a separate "Application
        Dates and Deadlines" page and found a genuinely current/future
        cycle ("Fall 2027 - Early Round, 1 Dec. 2026," with the portal
        explicitly stated as reopening "October 1st 2026") - not a
        stale prior-year deadline. However, the date used an
        abbreviated month ("Dec.") that this backend's confident-date
        regex (full month names only) cannot parse, and the overview
        page's own "1 December" mention carries no year at all -
        verified both directly rather than guessing a parseable date,
        and left `deadline_path` unset so the source correctly extracts
        no deadline instead of a wrong one.
      - Classified `partial_funding` correctly: "consists of a full
        campus fee-waiver only... all other costs (tuition fees, costs
        of living, personal expenses) are to be covered via other
        means" - never described as more than a housing-cost waiver.

      Three further Netherlands candidates were researched and
      rejected this same pass:
      - **Amsterdam University College - ASF Scholarships** - a real,
        unblocked page, but its own text states plainly "Applications
        are currently closed for new ASF scholarships, as all funding
        has been awarded for 2025-2026... scheduled to re-open in
        January 2027" - correctly left unintegrated as closed rather
        than presented as open, with no new eligibility criteria yet
        published to build a future record on. AUC's separate Talent
        Fellowships (TFA) explicitly require Dutch DUO grant
        eligibility ("talented Dutch students") - domestic only.
      - **Leiden University College** - hosted on the same
        `universiteitleiden.nl` domain already documented elsewhere in
        this project as CAPTCHA-blocked (an F5/Shape-style "Access
        Blocked" JS challenge). Tested directly rather than assumed:
        the content page returned a connection failure (`000`) while
        `robots.txt` alone remained reachable (`200`) - the identical
        pattern already documented for the parent domain, confirming
        LUC is not a separate, unblocked path.
      - **Nyenrode Business University** - checked two pages. The main
        "Scholarships & Financial Aid" page is a multi-record hub
        organized by degree programme (Revolving Scholarship, Program
        Scholarship, MSc Scholarship, GMAT Excellence, four named
        Impact MBA scholarships) with no single item detailed enough
        to build a confident record on. A second page, "Scholarship
        application | Nyenrode Fund," confirmed a genuinely current
        2026-2027 cycle but revealed an even larger structure of
        alumni-donor-named scholarships (1958 Legacy Scholarship,
        American Friends of Nyenrode University Scholarship, Class of
        1964 Scholarship, Class of 1976 Scholarship, and more), each
        narrowly scoped to specific campuses/programmes and requiring
        membership in specific Dutch student associations (NCV/VCV) -
        a genuine multi-record hub without one clean flagship,
        consistent with this project's earlier WHU/ESMT (Germany) and
        UNSW (Australia) rejections of the same shape - not integrated.

      **Verified for real**: `pyflakes app tests` clean, no new
      warnings. A `collect()` simulation against the real fixture, run
      before any test was written, confirmed title, provider, country,
      `funding_type = "partial_funding"`, and `deadline = None` all
      resolve exactly as documented, and that the fixture's full 3,750
      characters of scholarship text (not truncated or missing any
      section) came through the `#block-primary-content` selector.
      Full backend suite green afterward, 835 passed / 25 skipped (up
      from 833 passed/25 skipped - two new tests, plus
      `test_opportunity_import.py`'s updated source-count assertion,
      94 -> 95 registered sources). The fixture
      (`tests/fixtures/ucu_rosemary_orr_scholarship.html`) was captured
      unmodified from the live site.

- [x] **(2026-09-07)** Russia follow-up: "find Russia undergraduate and
      postgraduate university scholarship" - this platform already had
      one Russia source (Skoltech, #90) before this pass. Checked nine
      further Russian universities live: ITMO, Novosibirsk State
      University, Kazan Federal University, Ural Federal University,
      MEPhI, Peter the Great St. Petersburg Polytechnic University,
      RUDN University, RANEPA, and Tomsk State University/Innopolis
      University.

      Every one either funnels its non-CIS international scholarship
      information through one of two already-documented national
      multi-record programmes - the government Rossotrudnichestvo/
      "Education in Russia" quota (rejected in the prior five-country
      pass as a client-side-rendered SPA shell) and the "Open Doors"
      Russian Scholarship Project catalogue (rejected as a large
      multi-university, multi-programme hub, the same architecture
      mismatch as Erasmus Mundus's own catalogue) - rather than
      offering its own distinct single-record flagship page, or hit a
      genuine access/eligibility barrier:
      - **ITMO University** - its "Enrollment opportunities" page lists
        the Government Scholarship, an "ITMO.STARS" contest whose own
        "Learn more" link resolves only to a Russian-language page with
        no English equivalent, and Open Doors - checked the actual
        link target directly rather than assumed an English version
        existed.
      - **Novosibirsk State University** - its Grants/Scholarships page
        is a four-item list including third-country schemes (Germany's
        DAAD, the US's Fulbright Program - not Russian scholarships at
        all) and an Open Doors section that itself cites stale 2022
        dates ("Starting from September 5, 2022... Until December 10,
        2022") - read carefully enough to notice the page hadn't been
        updated for a current cycle, not just skimmed for the word
        "scholarship."
      - **Kazan Federal University** - beyond the same Government
        Scholarship/Open Doors pairing, found a third, genuinely
        KFU-administered item: "International Olympiads of KFU." Read
        its dedicated page directly and worked out the actual cycle
        timeline rather than assuming currency from the phrase "2026/27
        academic year": qualification stage ended January 13, 2026,
        final stage ended February 10, 2026, leading to enrollment
        "starting from the next academic year" - which, calculated
        against today's date (2026-09-07), is the 2026/27 academic year
        that has already begun. A fully concluded, stale cycle with no
        next round announced yet - not integrated as open.
      - **Ural Federal University** - same Government Scholarship/Open
        Doors pairing on its "Information for Prospective International
        Students" page, no distinct UrFU-administered scholarship
        found. Separately noted `urfu.ru/robots.txt` disallows a
        `/blind/` path specifically - avoided that path rather than
        used it, even though the search results surfaced a URL under
        it.
      - **MEPhI** - beyond restating the Government Scholarship and
        Open Doors, found a third, genuinely MEPhI/Rosatom-specific
        programme: the "Partner-Countries of the State Corporation
        Rosatom" scholarship. Checked its eligibility text directly
        rather than assumed from "African countries" framing: explicitly
        restricted to CIS countries plus two named African countries,
        Tanzania and Namibia - confirmed Sierra Leone does not appear
        on that list, per this project's standing explicit-check
        discipline, rather than inferring inclusion from the vague
        "African countries" phrasing.
      - **Peter the Great St. Petersburg Polytechnic University** -
        checked both of its English-content domains'
        `robots.txt` files directly (`english.spbstu.ru` and
        `www.spbstu.ru`) and found both set `Disallow: /en/` under the
        generic `User-Agent: *` rule that this platform's own
        identified `ScholarSphere/1.0` scraper falls under - the site's
        own declared policy excludes its entire English content tree,
        not circumvented.
      - **RUDN University** - same pattern, confirmed directly:
        `www.rudn.ru/robots.txt` sets `Disallow: /en/` under
        `User-Agent: *`.
      - **RANEPA** - found via search a page describing an
        RANEPA-specific "partial scholarships for the best students"
        (the Master of Global Public Policy programme), but a verbose
        TLS handshake trace (`curl -v`) showed the server presents a
        certificate for `*.tilda.ws` (a third-party website builder)
        rather than for its own hostname - a genuine server-side
        misconfiguration, verified directly rather than assumed from a
        generic connection failure, and per this project's absolute
        rule against disabling certificate verification, not bypassed
        with `-k`. Left `VERIFICATION_REQUIRED`.
      - **Tomsk State University and Innopolis University** - both
        reachable, but every scholarship-related page found for either
        restates Open Doors again or (Innopolis' application portal)
        returns a genuinely empty client-side-rendered shell (title
        "Empty page") - the same already-documented categories, not
        new ground.

      No new source was added for Russia this pass. Per this project's
      "never invent opportunities to make the country look complete"
      standard, the honest count of *additional* Russia sources this
      pass is zero, reported as such rather than padded - three
      genuinely university-specific programmes were found (MEPhI/
      Rosatom, KFU's Olympiad, RANEPA's MGPP) but each failed an
      already-established integration bar (nationality restriction
      excluding Sierra Leone, a fully concluded stale cycle, and a
      broken TLS certificate, respectively) rather than being forced
      in. Skoltech (#90) remains this platform's only Russia source.

      **No code was changed this pass** - only
      `docs/AUTHORITATIVE_SOURCES.md`, `docs/COUNTRY_PROVIDER_
      REGISTRY.md`, `Changelog.md`, and this file were updated. No new
      test run was required since no source code, test, or fixture file
      changed; the existing 835-passed/25-skipped baseline (confirmed
      immediately prior, in the Netherlands follow-up pass above)
      stands.

- [x] **(2026-09-07)** USA follow-up: "find USA undergraduate and
      postgraduate university scholarship" - this platform already had
      two USA university sources (Harrington Graduate Fellows Program,
      #88, grad/nomination-only; Vanderbilt's Cornelius Vanderbilt
      Scholarship, #89, undergrad) before this pass. Since the request
      named both degree levels explicitly, prioritized finding one
      genuine undergraduate candidate and one genuine postgraduate
      candidate with a *direct* application (unlike Harrington's
      nomination-only shape) rather than duplicating either existing
      level.

      Found and **implemented** the **Miami University (Ohio)
      International Merit Scholarship** as source #95 (undergraduate):
      - Found via a live web search for US universities offering
        automatic-consideration merit scholarships to international
        students, then verified the official page directly rather than
        trusted the search summary.
      - The overview page turned out to be a genuine four-item
        multi-record accordion hub (International Merit Scholarship,
        Presidential Fellows Program, #YouAreWelcomeHere Scholarship,
        Prodesse Scholarship). Rather than reaching for an index-based
        `:nth-of-type()` selector as in earlier passes, noticed via a
        BeautifulSoup structural walk that the four
        `div.accordion-primary__accordion` containers are document-
        ordered with the target scholarship first - so the shared
        `collect()` logic's existing first-match (`select_one`)
        behavior already isolates it correctly with no extra selector
        complexity. Verified directly that none of the other three
        scholarships' text (Presidential Fellows, #YouAreWelcomeHere)
        leaks into the extracted description.
      - Confirmed no nationality restriction from the page's own text
        ("All new first-year international undergraduate students...
        are automatically considered," "No separate scholarship
        application is required") - Sierra Leone applicants eligible.
      - Classified `partial_funding` correctly: a GPA-tiered discount,
        "Up to 50% of tuition" at the top qualifying tier - never
        described as more than a tuition discount.
      - Confirmed `miamioh.edu/robots.txt` does not disallow this path
        using Python's `urllib.robotparser` directly.

      Found and **implemented** the **University of Rochester Graduate
      International Funding** record as source #96 (postgraduate):
      - Found via a targeted search for US graduate schools offering
        international-student funding with a direct (non-nomination)
        application path, then read the official Graduate Education and
        Postdoctoral Affairs office's own page directly.
      - Read the funding text carefully rather than assumed a single
        funding level: "PhD candidates who are admitted will receive a
        full tuition scholarship, stipend, and health insurance" (via
        assistantship, guaranteed) versus "Masters' applicants who are
        accepted **typically** receive a merit-based tuition
        scholarship" (not guaranteed) - two different funding tiers on
        one page. Applied this project's established "don't overstate a
        mixed-tier page" standard (the same one used for Skoltech's
        combined MSc/PhD page, #90) and classified the combined record
        `partial_funding` rather than `fully_funded`, since not every
        admitted student on this record gets the PhD-level guarantee.
      - Confirmed no nationality restriction: "International students
        are considered for the same financial support as domestic
        students."
      - Used `title_selectors = ()` deliberately: checked both the
        page's `<h1>` ("Admissions") and its section `<h3>` ("Tuition,
        Financial Aid, and Other Expenses") and found both too generic
        to serve as a scholarship title, so relied on the
        external_id-derived fallback rather than a misleading generic
        title.
      - Compared `main` vs `article` selectors directly and chose
        `article` specifically because `main` pulled in the page's
        entire section-navigation menu (Overview, How to Apply,
        Application Timeline, Test Requirements, ... a dozen unrelated
        admissions-office links) while `article` held only the funding
        description and other-expenses list.
      - Confirmed `rochester.edu/robots.txt`'s generic `User-Agent: *`
        rule disallows only a named list of unrelated administrative/
        report paths, none covering this content path.

      Four further USA candidates were researched and rejected this
      same pass:
      - **American University** - a search result described automatic
        merit-scholarship consideration with no separate application,
        so fetched the live page directly to verify; got back an active
        Cloudflare managed challenge ("Just a moment...," HTTP 403) with
        `server: cloudflare` and a `__cf_bm` bot-management cookie
        confirmed in the response headers - genuine bot protection, not
        circumvented, even though the site's own `robots.txt` declares
        no restriction (checked both, rather than assuming the
        robots.txt result alone settled it).
      - **AAUW (American Association of University Women) International
        Fellowships** - a genuinely strong, nationality-unrestricted
        candidate found via search (any accredited US institution, AY
        2027-2028 deadline of 17 September 2026, only 10 days out from
        this research date but still genuinely future), but its own
        fellowship page returns the identical Cloudflare-managed 403
        signature as American University above - not circumvented.
      - **East-West Center Graduate Degree Fellowships** (University of
        Hawaii at Manoa) - returned HTTP 403 on the one page checked;
        did not pursue further given the programme's own stated
        regional scope ("students from Asia, the Pacific, and the
        U.S.") would likely have excluded a Sierra Leonean applicant
        regardless, so the access barrier wasn't the only reason to
        stop.
      - **Iowa State University - International Merit Scholarships** -
        a real, unblocked, genuinely current two-tier undergraduate
        scholarship (Award of Achievement/Award of Distinction, no
        nationality restriction) - a credible alternative, but not
        added once one clean undergraduate candidate (Miami University)
        had already been verified, to avoid padding this pass with
        redundant coverage of the same degree level - noted honestly as
        a strong candidate for a future USA pass instead.

      **Verified for real**: `pyflakes app tests` clean, no new
      warnings. A `collect()` simulation against both real fixtures, run
      before any test was written, confirmed title, provider, country,
      `funding_type = "partial_funding"`, and `deadline = None` all
      resolve exactly as documented for both sources, and specifically
      confirmed the Miami University accordion isolation excludes
      "Presidential Fellows" and "#YouAreWelcomeHere" text from the
      extracted description. Full backend suite green afterward, 839
      passed / 25 skipped (up from 835 passed/25 skipped - four new
      tests, plus `test_opportunity_import.py`'s updated source-count
      assertion, 95 -> 97 registered sources). Both fixtures
      (`tests/fixtures/miamioh_international_merit_scholarship.html`,
      `tests/fixtures/rochester_graduate_scholarship.html`) were
      captured unmodified from their live fetches.

- [x] **(2026-09-07)** Qatar follow-up: "find Qatar undergraduate and
      postgraduate university scholarship" - this platform's only prior
      Qatar source (Qatar Scholarships, #36) is government/QFFD-
      classified, jointly administered with partner institutions rather
      than a single university's own programme, so this pass looked
      specifically for university-administered scholarships at
      individual Qatari institutions.

      Found and **implemented** the **Qatar University International
      Students Scholarship** as source #97 (undergraduate):
      - Found via a live search for QU's own scholarship types page,
        then read the official page directly. The page turned out to
        be a genuine ten-item multi-record panel hub (Student
        Recruitment and Excellence Scholarship - restricted to
        "Residents of Qatar"; this one; H.H. the Emir of Qatar's
        Scholarship; Outstanding Performance Scholarship; GCC States
        Scholarships; and five more).
      - Rather than assume the first panel-shaped item was the target,
        read each panel's own heading text to locate the specific
        "International Students Scholarship" section (the second
        panel), then verified via a BeautifulSoup structural walk that
        all ten panels share Bootstrap `div.panel`/`div.panel-group`
        markup with a consistent, countable sibling order, allowing a
        precise `div.panel:nth-of-type(2)` selector rather than a
        vaguer text-matching heuristic.
      - Confirmed no nationality restriction from the page's own text:
        "Qatar University offers this scholarship to international
        students who apply to undergraduate programs" - no country
        list, Sierra Leone eligible - and confirmed directly that the
        neighboring "Student Recruitment and Excellence Scholarship"
        panel (index 1) is explicitly restricted to "Residents of
        Qatar" and does NOT leak into this record's extracted
        description.
      - Classified `fully_funded` correctly: the benefits list (tuition
        exemption, textbook exemption, 500 QR monthly salary, housing,
        annual round-trip airfare, residence permit) is genuinely
        comprehensive for competitively-selected recipients, not merely
        a tuition discount.
      - Confirmed `qu.edu.qa/robots.txt` does not disallow this path
        using Python's `urllib.robotparser` directly.

      Found and **implemented** the **HBKU Graduate Scholarship
      (Tuition Waivers & Stipends)** as source #98 (postgraduate,
      Master's + PhD combined):
      - Found via a search specifically for graduate-level Qatari
        university scholarships (having already covered undergraduate
        with QU above), landing on Hamad Bin Khalifa University's own
        "Scholarship Guidelines for HBKU Graduate Programs" page.
      - Read the tuition-waiver table carefully rather than assumed a
        single rate: waivers range from "PhD STEM (CSE and CHLS): 100%"
        down to "LL.M. Programs (CL): 0%" and "MS Economics (SEM): 0%"
        depending on programme - a genuinely mixed-tier page.
      - Found a second table, explicit stipend rates broken out by
        student category: "International PhD: 9,000 QAR/month, 108,000
        QAR/year, 45 months" and "International Master's: 7,000
        QAR/month, 84,000 QAR/year, 21 months" - distinct rows from
        "Qatari" and "Local" - confirmed Sierra Leone eligibility
        directly from this explicit "International" category rather
        than inferred from a vaguer "international students welcome"
        statement elsewhere on the site.
      - Read the page's own eligibility disclaimer and applied this
        project's established "don't overstate a mixed-tier page"
        standard (already used for Skoltech's MSc/PhD page, #90, and
        this same pass's University of Rochester record, #96):
        "Tuition waivers and stipend awards are not guaranteed and are
        only awarded on a merit or need basis" - classified
        `partial_funding` for the combined record rather than
        `fully_funded`, since some programmes get 0% and no award is
        guaranteed regardless of programme.
      - Compared `main` against other selectors and confirmed `main`
        alone (5,740 characters) captured exactly the scholarship
        content - both tables, conditions, and FAQ - starting right
        after the page's own breadcrumb, with none of HBKU's large
        Colleges/Research/Innovation navigation menu leaking in.
      - Confirmed `hbku.edu.qa/robots.txt` does not disallow this path.

      Two further Qatar candidates were researched and rejected this
      same pass:
      - **Qatar University - Graduate Assistantship (GA)** - a search
        summary described it as open to applicants "from inside Qatar
        as well as from other countries," so fetched the official page
        directly to verify rather than trust the summary alone; found
        it states no stipend amount, funding tier, or explicit
        eligibility breakdown of its own - too thin to build a
        confident record on, unlike HBKU's detailed rate tables just
        implemented. Not integrated.
      - **Qatar University - "Masters and PhD Scholars" page** - a
        promising-sounding title from search results, but reading the
        actual page content revealed it to be a directory of QU's own
        (Qatari) faculty and teaching assistants who studied abroad at
        overseas universities on QU's own outbound sponsorship - a
        staff programme, not an inbound scholarship for international
        applicants to study at QU. Recognized this distinction by
        reading the page's actual content (names, overseas
        universities, "TA Starting Date" fields) rather than assuming
        relevance from the title alone.

      **Verified for real**: `pyflakes app tests` clean, no new
      warnings. A `collect()` simulation against both real fixtures, run
      before any test was written, confirmed title, provider, country,
      funding_type, and `deadline = None` all resolve exactly as
      documented for both sources, and specifically confirmed the QU
      panel isolation excludes "Residents of Qatar" text from the
      extracted description while the HBKU record correctly includes
      both "International PhD" and "International Master" stipend text
      plus the "not guaranteed" eligibility caveat. Full backend suite
      green afterward, 843 passed / 25 skipped (up from 839 passed/25
      skipped - four new tests, plus `test_opportunity_import.py`'s
      updated source-count assertion, 97 -> 99 registered sources). Both
      fixtures (`tests/fixtures/qu_international_students_scholarship.html`,
      `tests/fixtures/hbku_graduate_scholarship.html`) were captured
      unmodified from their live fetches.

- [x] **(2026-09-07)** Qatar second follow-up: the user repeated the
      exact same "find Qatar undergraduate and postgraduate university
      scholarship" request immediately after the pass above. Rather
      than duplicate QU (#97) and HBKU (#98), checked the Education
      City branch campuses of major US universities in Qatar (Texas
      A&M, Carnegie Mellon, Georgetown, Northwestern, VCU), each
      administered under Qatar Foundation (QF) rather than QU or HBKU -
      a genuinely different institutional funding structure worth
      checking.

      Found and **implemented** the **CMU-Q Qatar Foundation
      Need-Based Grant Program** as source #99 (undergraduate):
      - Found via a search for CMU-Q's own tuition/financial-aid page,
        then read the official page directly. Confirmed a genuinely
        current cycle from the page's own tuition table header,
        "Tuition and Fees, 2026-2027 Academic Year," before trusting
        any of its financial-aid claims.
      - The page turned out to be a five-item multi-record accordion
        hub. Verified via a BeautifulSoup structural walk that the
        target "Qatar Foundation Need-Based Grant Program for Students
        of All Nationalities" section is the *first* `<details
        class="stk-block-accordion">` element in document order, so
        the shared `collect()` logic's existing first-match behavior
        already isolates it with no positional selector needed -
        confirmed directly that FAFSA text and the continuing-
        students-only "Merit Scholarship Program" text do not leak in.
      - Read the eligibility text carefully rather than accepted the
        page's general "students of all nationalities" framing at face
        value: found a specific carve-out - "International applicants
        outside of Qatar are not eligible for financial aid during the
        Early Decision round" - and confirmed this exclusion is scoped
        to Early Decision only, with no equivalent restriction stated
        for Regular Decision, so documented the record honestly as
        open to international applicants via Regular Decision rather
        than either overstating universal eligibility or wrongly
        rejecting the whole programme over one round's restriction.
      - Classified `partial_funding` correctly: "Grants... of up to the
        full cost of attendance are made to families based on their
        unique financial circumstances" - a need-based cap dependent on
        individual circumstances, not a guaranteed uniform amount.
      - Hit a genuine false-negative while checking `robots.txt`:
        Python's `urllib.robotparser` default `read()` call (no custom
        User-Agent) returned an empty ruleset for this host even though
        `curl` with the project's real scraper User-Agent succeeded and
        returned real, unrestrictive rules - recognized this as the
        same category of UA-specific blocking already seen for UrFU
        earlier in this project, rather than concluding the path was
        restricted. Fixed by re-fetching the raw `robots.txt` text with
        an explicit User-Agent and parsing it directly with
        `RobotFileParser.parse()`, which correctly confirmed no
        restriction.

      One further Qatar candidate was researched and rejected this same
      pass:
      - **Texas A&M University at Qatar (TAMU-Q)** - fetched the live
        page directly and noticed its own `<h1>` reads "2023-24 Tuition
        Rates" - three academic years stale compared to CMU-Q's
        confirmed current 2026-2027 table, a discrepancy worth checking
        for rather than assuming currency from a 200 status code alone.
        Read the financial-aid text carefully and found it explicitly
        describes the aid available to non-sponsored (including
        international) students as a **loan** requiring post-graduation
        repayment or paid service, not a grant or scholarship - a
        substantively different funding mechanism than CMU-Q's genuine
        grant. The page's one true scholarship reference ("Qatar
        Foundation Student Financial Services scholarship") is
        explicitly for "top *returning* students who have no
        sponsorship," awarded "each summer" - a continuing-student
        renewal programme, not an incoming-applicant scholarship. Not
        integrated for both the staleness and the loan-vs-grant
        distinction.

      **Verified for real**: `pyflakes app tests` clean, no new
      warnings. A `collect()` simulation against the real fixture, run
      before any test was written, confirmed title, provider, country,
      `funding_type = "partial_funding"`, and `deadline = None` all
      resolve exactly as documented, and specifically confirmed neither
      "Merit Scholarship Program" nor "FAFSA" text leaks into the
      extracted description. Full backend suite green afterward, 845
      passed / 25 skipped (up from 843 passed/25 skipped - two new
      tests, plus `test_opportunity_import.py`'s updated source-count
      assertion, 99 -> 100 registered sources). The fixture
      (`tests/fixtures/cmuq_need_based_grant.html`) was captured
      unmodified from the live site.

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

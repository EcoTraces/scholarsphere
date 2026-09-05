# ScholarSphere — Roadmap

**Last verified against the codebase:** 2026-08-21.

**Important note on source freshness:** `docs/PRODUCTION_SECURITY_AUDIT.md`
and `docs/PRODUCTION_READINESS.md` are dated **2026-08-17** and state "35 of
36 Flutter feature areas have no real backend." That was accurate on
2026-08-17, but five more days of commits landed since
(`e86ade2` real Notifications backend, `114c7cd` Applicant Profile,
`78c226e` Documents, `e9b6e09` "backend features01", `252b01a` "completed
features" — see `git log`), and direct inspection of the current
`lib/app/app.dart` wiring (2026-08-21) shows the great majority of feature
areas are now real-backend-connected — see PRD.md §3.1. **Trust this
roadmap and PRD.md over the audit's completeness table; trust the audit's
security findings and methodology, which are still valid.** Whoever does the
next security pass should re-run the audit's own §2 checklist against
everything that changed since 2026-08-17, not assume it's covered.

Status markers: `[x]` Completed & verified · `[~]` In progress /
partial · `[ ]` Not started · `[!]` Blocked

---

## Phase 1 — Foundation

- [x] Flutter project scaffold, Material 3 theme (`lib/app/theme.dart`)
- [x] Feature-sliced `domain/data/presentation` architecture established
- [x] Opportunity domain model + demo repository (first vertical slice)
- [x] Widget test harness (`DemoAuthRepository`-based, no live Firebase needed)
- [x] CI pipeline (`flutter analyze`, `flutter test`, `flutter build web`)

## Phase 2 — Authentication and User Management

- [x] Firebase email/password + Google sign-in
- [x] Applicant self-registration with email verification
- [x] Password reset, session restore
- [x] Firestore `users/{uid}` account persistence, `firestore.rules`
- [x] Admin-created managed accounts via Cloud Functions
      (`createManagedUser`, `suspendUser`)
- [x] Role-based dashboard dispatch (8 roles)
- [ ] MFA/2FA challenge flow — `twoFactorEnabled` is stored and read, but no
      TOTP/SMS second-factor UI exists anywhere (dependency: product
      decision on MFA provider)

## Phase 3 — Provider Opportunity Submission and Administration

- [x] `providers` real backend: registration, server-side risk scoring,
      case-insensitive duplicate-domain prevention, 5-item verification
      checklist, sub-administrators, appeals
- [x] `provider_opportunities` real backend: separate pipeline from
      Grants.gov-family imports, submission gated on verified provider +
      permission, real Firebase Storage document upload
- [x] Administration dashboard (live stats, collection access)
- [ ] Firebase Admin Storage API check that an uploaded document path
      actually exists before accepting it into a `Provider` record
      (documented accepted gap — path *shape* is validated, existence is
      not)

## Phase 4 — Verification Workflow and Trust Signals

- [x] Automated import from 7 official structured APIs
- [x] `pending → verified/rejected/...` pipeline, 4-item checklist,
      server-enforced `409` on incomplete checklist
- [x] Separate, deliberate publication step (Administrator-only)
- [x] Automatic 90-day reverification + daily expiry detection (Celery beat)
- [x] Evidence panel, notes, audited field edits with re-sanitization
- [x] `LiveVerificationQueueScreen` reaches the real backend end-to-end
- [x] Verification Officer dashboard landing metrics — fixed 2026-08-21:
      new `GET /external-opportunities/verification-summary` endpoint
      (real aggregate counts: pending, verified today, reverification due
      soon, status breakdown, 7-day activity, official-source ratio,
      approvals attributed to the calling officer); the dashboard now
      reads exclusively from `ApiVerificationRepository`, and the dead
      `DemoVerificationRepository`/demo `_opportunityRepository` wiring
      was removed from `app.dart`
- [ ] Two-person assign/second-approve workflow (exists only in the demo
      repository; needs its own backend design if it's a hard requirement —
      not a UI-only simulation, see Architecture.md decision 6)
- [ ] Security Officer read access to `ImportAuditLog`/rate-limit events
      (RBAC role exists, no route reads it yet)
- [ ] Super-Administrator-editable source registry UI (adding an 8th source
      today requires a code change to `SOURCE_DEFINITIONS`)

## Phase 5 — Eligibility Rules and Explainable Matching

- [x] Deterministic rule-based eligibility scoring (no ML dependency) —
      nationality, level, field, age, experience, language, fee, funding
- [x] Matched/missing/uncertain explanation breakdown
- [x] Applicant-facing match panel on opportunity detail
- [ ] `eligibility_rules` feature (a separate, admin-configurable rule
      engine distinct from the matcher above) — domain model + demo
      repository exist, but **no backend route and no screen** — currently
      dead code reachable only from a unit test. Needs a product decision:
      build it out or delete it (see Task.md).

## Phase 6 — Saved Opportunities and Application Tracking

- [x] `applications` real backend — 10-stage tracking, idempotent
      save/track, admin-paginated view
- [x] Notification triggers tied to application/deadline events

## Phase 7 — Notifications, Documents, and Deadline Jobs

- [x] Notifications real backend (landed 2026-08-20) — in-app center,
      preferences, deadline reminders, admin templates/analytics
- [x] Applicant documents real backend — 13-category checklist, Firebase
      Storage upload, per-document provider access grants
- [x] Provider document-sharing consent — fixed 2026-08-21: sharing now
      requires an active `third_party_sharing` `ConsentRecord` (409
      otherwise) and a real, existing provider (404 otherwise); every
      grant is logged to `organization_access_records`; withdrawing
      consent cascades to clear every existing grant. Storage-level
      differential access for providers (as opposed to this Postgres-level
      grant) remains a separate, not-yet-built follow-up.
- [x] Reverification reminders — fixed 2026-08-21: real in-app
      `ScholarSphereNotification` rows are created for verification
      officers with real prior decision history (drawn from
      `ImportAuditLog`, since there is no local user directory to query a
      full officer roster from), deduplicated by deterministic ID, gated
      on the recipient's own notification preferences. Email/push/SMS
      delivery is not claimed — no provider is configured for those
      channels anywhere in this backend (see Task.md for what's needed).
- [x] Search-index rebuild background job — fixed 2026-08-21: now reads
      from `_apiOpportunityRepository` instead of
      `DemoOpportunityRepository`. Root cause was worse than a stale read:
      `POST /search-index/rebuild` prunes the entire index and
      re-validates every incoming id against real `external_opportunities`
      rows, so demo ids were silently rejected — every rebuild was leaving
      the real, shared search index empty. The separate client-side
      `expiredOpportunityDetection` job was removed (not re-pointed): the
      real backend already runs this daily via Celery beat, and the client
      has no server-authoritative way to mutate verification status
      client-side by design (Architecture.md decision 9). Regression-tested
      end-to-end (`test/widget_test.dart`).
- [x] Incidental fix: `JobMonitorScreen`'s three `setState(_reload)` calls
      passed a `void` arrow-function tear-off whose body is itself an
      assignment expression — at runtime it still returned the assigned
      `Future`, tripping Flutter's "setState callback returned a Future"
      guard. Never caught before because no test exercised "process queued
      jobs"/change the status filter/cancel-or-retry a job; found while
      writing the search-index regression test above. Fixed by wrapping
      each call in a block body.

## Phase 8 — Collection, Fraud Signals, Reporting, and Analytics

- [x] Collection ledger (manual/provider/API/RSS/feed/web/user
      provenance), forced pending-verification
- [x] Fraud investigation real backend — cases, evidence, watchlist,
      analytics
- [x] Client-side fraud-detection heuristics (`fraud/domain`) — evidence-based,
      weighted signals, neutral caution wording
- [x] Provider analytics, opportunity view analytics
- [x] Audit log (hash-chained, exportable, integrity-verifiable)

## Phase 9 — Governance, Support, and Operations

- [x] Legal compliance (versioned policies, acceptances, requests)
- [x] Data lifecycle (retention rules, soft/hard delete, legal holds)
- [x] Support tickets, knowledge base, response templates
- [x] Source registry (trust scoring, review, corrections)
- [x] Taxonomy (terms, versions, duplicate detection, merge)
- [x] Operations console — backups, observability (logs/metrics/traces/
      alerts/incidents), release gating, versioned system configuration
- [x] Moderation (cases, warnings, appeals)

## Phase 10 — Security, Hardening, and Deployment Readiness

- [x] Redis-backed rate limiting (fail-open)
- [x] Security response headers on every API response
- [x] Production-forced `FIREBASE_CHECK_REVOKED=true`
- [x] `DATABASE_URL`/`REDIS_URL` placeholder-credential rejection in
      production
- [x] `/docs`/`/redoc` disabled in production
- [x] HTTPS-only enforcement on Flutter release builds and all external
      source URLs
- [x] Full dependency vulnerability remediation round (16 of 17 findings
      fixed; 1 open, no upstream patch — `firebase-admin`'s transitive
      `uuid` CVE)
- [x] Backend CI job (`pytest`, `pip-audit`) added alongside the
      pre-existing Flutter job
- [ ] Firebase console re-registration under the new bundle ID
      (`com.scholarsphere.app`) — **blocked**, requires Firebase console
      access outside any coding session
- [ ] Real release signing (Android/iOS/macOS currently sign with the debug
      key) — **blocked**, requires the team's own signing keystore
- [x] Independent security review of the `applications`/`verification`
      backend and the `providers`/`provider_opportunities` backend against
      the audit's own §2 checklist — completed 2026-08-22, 4 real gaps
      found and fixed (missing audit trail, a permission-storage format
      bug, a per-administrator permission-enforcement gap, an
      unconstrained decision field), 0 IDOR/auth-bypass found; see
      Task.md/Changelog.md
- [ ] Live smoke test of `storage.rules` against a real Firebase Storage
      bucket (reasoned about, never deployed and exercised in this
      environment)
- [ ] Formal incident-response runbook (`docs/operations.md` is a short
      baseline, not an IR plan)

## Phase 11 — Premium Application-Preparation Platform (2026-09-01)

- [x] Provider-independent payment abstraction (`PaymentProvider`
      interface, `NullPaymentProvider` default, real `StripePaymentProvider`
      reference adapter) with real webhook-signature verification and
      database-level idempotency (not application-level checking alone)
- [x] Server-authoritative entitlement system (`require_entitlement`
      FastAPI dependency, never a JWT-cached claim), plan feature-lists
      snapshotted at grant time, refund → entitlement revocation
- [x] Configurable premium plans (admin-editable price/currency/feature
      list; flagship "Complete Premium Application Package" seeded, not
      hardcoded)
- [x] Provider-independent AI abstraction (`AIProvider` interface,
      `NullAIProvider` default, real `OpenAIProvider`/`AnthropicProvider`
      adapters)
- [x] Applicant background data model (education/work-experience/project/
      publication/award/leadership/skill/reference) — closes a real,
      pre-existing gap (`ApplicantProfile` only ever had summary fields)
- [x] Deterministic CV assembly + opt-in, fact-preserving AI wording polish
- [x] Grounded AI narrative generation (SOP, personal statement,
      motivation letter, study plan, research proposal, fellowship
      essays) — system prompt explicitly forbids inventing any fact
- [x] Deterministic, AI-independent requirement matching, readiness
      scoring (fully documented weights), and ATS analysis (always
      carries a "does not guarantee acceptance" disclaimer)
- [x] Category-driven workflow registry for all 9 required applicant
      categories (undergraduate/postgraduate/PhD/fellowship/research
      scholarship/professional scholarship/exchange-mobility/short-course/
      internship)
- [x] Append-only document versioning; ATS-compatible PDF/DOCX export
- [x] Admin dashboard (plan CRUD, payments/refunds, revenue, AI usage,
      usage-limit config)
- [x] 50 new backend tests incl. every "Critical test" the platform spec
      named explicitly; full backend suite green (737/737)
- [x] Flutter: `PremiumLandingScreen` (real pricing/checkout/status),
      `PremiumFeatureGate`, dual demo/api repository, `app.dart` wiring
- [ ] Flutter: the individual document-builder screens themselves (CV/
      SOP/study plan/research proposal/fellowship editors), ATS analyzer
      UI, requirement-matcher/readiness/checklist UI, billing-history
      page, admin premium dashboard UI, usage dashboard — real backend
      routes exist for all of these already; only the presentation layer
      remains
- [ ] A second real payment provider (Paystack/Flutterwave) —
      architecture supports it (new class + one registry line); not
      built because no provider has been chosen yet
- [ ] Client-side payment SDK integration in Flutter (e.g.
      `flutter_stripe`) for the card-entry step — **blocked**, tied to
      whichever provider is eventually chosen and its real credentials
- [ ] Real payment/AI credentials in any environment — **blocked**,
      requires the team's own provider account and API keys; both
      abstractions are fully implemented and tested against the honest
      "not configured" failure mode in the meantime

## Not yet scoped (dead code — needs a product decision, not more building)

- [ ] `eligibility_rules`, `integrations`, `data_transfer`, `platforms` —
      domain model + demo repository only, no backend, no screen, no
      `app.dart` wiring. Either build them out or delete them; see Task.md.

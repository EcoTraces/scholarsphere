# ScholarSphere — Product Requirements Document

**Last verified against the codebase:** 2026-08-21
**Status legend:** ✅ Implemented (real backend, reachable in the running app) · 🟡 Partial (real backend exists but wiring/data source has a known gap) · ⚪ Demo-only (in-memory Dart fixtures, no persistence, reachable in the app) · ⬛ Not started / dead code (no backend, no reachable UI)

This document describes what ScholarSphere actually is, based on reading the
running code (`lib/`, `scholarsphere_backend/`), not a wishlist. Where the
project's own internal audits (`docs/PRODUCTION_SECURITY_AUDIT.md`,
`docs/PRODUCTION_READINESS.md`, dated 2026-08-17) are now out of date because
later commits changed the picture, this document reflects the **current**
code — see the note in [Road_map.md](Road_map.md) on that gap.

---

## 1. Project Overview

**Name:** ScholarSphere

**Description:** A global platform for discovering, evaluating, and tracking
verified scholarships, fellowships, internships, grants, jobs, training
programs, webinars, and conferences. It pulls opportunities from official
government and international-organization APIs, puts every record through a
human verification pipeline before it's ever shown to an applicant, evaluates
eligibility per-applicant, tracks application progress, and sends deadline
reminders.

**Problem being solved:** Verified opportunity information is scattered
across dozens of institutional websites and mixed in with scam listings and
unofficial aggregators. Applicants have no single trustworthy place to
discover opportunities they're actually eligible for, and no way to tell a
genuine listing from a fraudulent one.

**Proposed solution:** Ingest opportunities only from official, documented,
structured APIs (never web scraping — see [Architecture.md §5](Architecture.md)),
require a human Verification Officer to approve every record against a
checklist before it can be published, run deterministic (non-AI) eligibility
matching against each applicant's profile, and provide fraud-signal warnings
on anything that looks suspicious.

**Explicit non-guarantee** (from the project's own README): ScholarSphere
gives guidance and verified information, but does not guarantee admission,
funding, selection, visas, or travel approval. Applicants must confirm
current requirements on the official application website.

**Target users:** Students, graduates, researchers, entrepreneurs, and young
professionals seeking opportunities; organizations that want to publish
opportunities (providers); and platform staff who verify, moderate, and
operate the system.

**Goals:**
1. Never show an applicant an opportunity that hasn't been verified against
   its official source.
2. Make eligibility and deadlines legible up front, not buried in a detail
   page.
3. Give every verification decision, edit, and publication action a
   permanent, reasoned audit trail.
4. Keep identity in one place (Firebase Auth) and business data in one place
   (PostgreSQL via a FastAPI backend), rather than duplicating state.

---

## 2. User Roles

Defined in `lib/features/authentication/domain/user_account.dart`
(`UserRole` enum) and enforced server-side by
`scholarsphere_backend/app/core/rbac.py`. Permissions are defined in
`lib/features/security/domain/access_control.dart` (`AccessControlPolicy`,
client-side UI routing only) and mirrored server-side by
`app/core/auth.py`'s `ROLE_PERMISSIONS` table (the two are kept in sync
deliberately — see Architecture.md's "permission-claims drift" decision).

| Role | Responsibilities | Real backend permissions today | Dashboard |
|---|---|---|---|
| **Applicant** | Discover, evaluate, and apply to opportunities; track applications; manage a private profile and documents | Read published/verified opportunities; manage own applications, profile, documents, notifications, privacy consents | `ApplicantDashboardScreen` → `DiscoverScreen` |
| **Opportunity Provider** | Register an organization, get it verified, and submit opportunities for review/publication | Register org; submit/manage own opportunities (once org is verified with `publish_opportunities` permission) | `ProviderAccountScreen` |
| **Verification Officer** | Review imported and provider-submitted opportunities against a checklist; approve, reject, flag, or request reverification | Full verification workflow (`preview_access`/`import_access`); **cannot** publish | `VerificationOfficerDashboardScreen` → `LiveVerificationQueueScreen` |
| **Moderator** | Review reported content, issue warnings, manage moderation cases | Moderation queue (real backend) | `ModeratorDashboardScreen` |
| **Support Officer** | Handle applicant/provider support tickets | Support ticket queue (real backend) | `SupportAgentScreen` |
| **Administrator** | Everything a Verification Officer can do, plus publish opportunities, activate/deactivate sources, manage users, view platform-wide administration | `admin_access` — publication, source activation, most operations/system-configuration routes | `AdministrationDashboardScreen` |
| **Security Administrator** | Manage security policy, sessions, backups; **no dedicated audit/rate-limit read endpoint exists yet** — a documented gap | `manageSecurity`, `suspendAccounts`, `manageSecrets` (client-side permission set); backend `backup`/`system_configuration` routes restricted to this role + admin roles | `SecurityAdministratorDashboardScreen` |
| **Super Administrator** | Full platform authority, including release/deployment approval | All `Permission.values`; same backend capability as Administrator today (no additional route restricted to super-admin-only beyond `release.py`) | Falls through to `AdministrationDashboardScreen` |

**Not implemented:** two-person verification approval (assign + second
approver) is modeled only in the demo verification repository, not the real
backend — see `docs/OPPORTUNITY_VERIFICATION_SYSTEM.md` §4.

---

## 3. Functional Requirements

Organized by the 36 `lib/features/*` areas. "Fully wired" means the
production `ScholarSphereApp` (`lib/app/app.dart`) instantiates the
`Api*Repository` implementation and a matching FastAPI route exists.

### 3.1 Fully implemented (real backend, real UI)

| Feature | Description | Role(s) | Business rules | Status |
|---|---|---|---|---|
| Authentication | Email/password + Google sign-in, applicant self-registration with email verification, password reset, session restore, managed-account creation, suspension | All | Applicant self-registration is the only self-service role; all others are admin-created via Cloud Functions | ✅ Implemented |
| Opportunity discovery | Search/filter/browse published, verified opportunities | Applicant | Only `verification_status=verified AND publication_status=published` records are ever returned publicly | ✅ Implemented |
| Opportunity verification | Officer review queue: evidence panel, 4-item checklist, 6 decision outcomes, notes, field edits | Verification Officer, Administrator | `verified` requires all 4 checks true (409 otherwise, server-enforced); `published` requires `verified` first (separate action) | ✅ Implemented |
| Provider registration & opportunity submission | Organization registration with risk scoring, document upload, own verify→publish pipeline separate from the Grants.gov pipeline | Opportunity Provider, Verification Officer, Administrator | 5-item checklist for provider verification; submission gated on `verified` provider + `publish_opportunities` permission, checked server-side against the caller's own Firebase UID | ✅ Implemented |
| Applications (tracking) | Save/track opportunities through 10 stages | Applicant | One application per (user, opportunity) pair (unique constraint) | ✅ Implemented |
| Applicant profile | Private personal/education/employment/readiness/preference data | Applicant | Fully private; used only for matching | ✅ Implemented |
| Applicant documents | Standardized 13-category document checklist, upload via Firebase Storage, per-document provider access grants | Applicant, Provider (with grant) | Owner-only by default; sharing requires an active `third_party_sharing` consent record (409 otherwise, server-enforced) and a real, existing provider (404 otherwise); withdrawing that consent cascades to clear all existing grants | ✅ Implemented |
| Verification Officer dashboard | Real-time queue and aggregate metrics (pending, verified today, reverification due soon, status breakdown, 7-day activity, official-source ratio, approvals attributed to the calling officer) | Verification Officer, Administrator | `GET /external-opportunities/verification-summary` — every number is a genuine aggregate query, gated by the same `preview_access` role check as the queue itself | ✅ Implemented |
| Notifications | In-app center, preferences, deadline reminders, admin templates/analytics | Applicant, Administrator | Landed 2026-08-20; supersedes the earlier "notifications is demo-only" status recorded in `scholarsphere_backend/README.md`'s Known Limitations | ✅ Implemented |
| Calendar | Event/deadline tracking, conflict detection, `.ics` export | Applicant, staff | — | ✅ Implemented |
| Guidance | Application-readiness plans, recommendation letters, submission tracking | Applicant | — | ✅ Implemented |
| Moderation | Content reports, case queue, warnings | Moderator, Administrator | — | ✅ Implemented |
| Fraud investigation | Case management, evidence, watchlist, risk analytics | staff roles | — | ✅ Implemented |
| Privacy | Consents, data requests, access history, incidents | Applicant, staff | Personalized recommendations disabled without active consent | ✅ Implemented |
| Support | Tickets, knowledge base, templates, performance reporting | Applicant/Provider, Support Officer | — | ✅ Implemented |
| Source registry | Registry of approved external sources, trust scoring | Administrator, Security roles | — | ✅ Implemented |
| Taxonomy | Term normalization/merge/versioning | staff | — | ✅ Implemented |
| Experience | Locale/accessibility preferences (high contrast, text scale, RTL) | All (self) | — | ✅ Implemented |
| Recommendations | Personalization controls, feedback, quality reporting | Applicant, staff | — | ✅ Implemented |
| Governance (legal + data lifecycle) | Policy versions/acceptances, retention rules, legal holds, soft/hard delete | staff | — | ✅ Implemented |
| Operations (backup / observability / release / system configuration) | Ops console: backups, logs/metrics/traces/alerts, release gating, versioned config | Administrator, Security Administrator, Super Administrator | Release blocked unless quality gates pass; self-approval to prod blocked | ✅ Implemented |
| Audit | Search/export audit records, integrity (hash-chain) verification, retention policy | Administrator roles | Append-only; no update/delete route exists by design | ✅ Implemented |
| Security | Sessions, login history, alerts, rate-limit check | Applicant (own), Security Administrator | — | ✅ Implemented |
| Provider analytics | Engagement events, per-provider snapshot/export | Provider, Administrator | — | ✅ Implemented |
| Collection | Manual opportunity intake ledger | Administrator, Security roles | Every collected record forced into pending verification | ✅ Implemented |
| Analytics | Opportunity view events | All (write), staff (read counts) | — | ✅ Implemented |

### 3.1a Premium Application-Preparation Platform (2026-09-01)

A paid tier layered on top of the free feature set above, not a
replacement for any of it — see Architecture.md §9 for the full design.

| Feature | Description | Backend | Flutter |
|---|---|---|---|
| Payment architecture | Provider-independent `PaymentProvider` interface; real Stripe adapter (Payment Intents/Refunds/Subscriptions/webhook signature verification); `NullPaymentProvider` default that never fabricates a successful transaction | ✅ Implemented, tested | ✅ Checkout initiation + status; no client-side card-entry SDK yet |
| Entitlements | Server-authoritative, database-backed (never a JWT claim or client flag); plan feature-list snapshotted at grant time; expiry-aware | ✅ Implemented, tested | ✅ Read via `PremiumStatus`; `PremiumFeatureGate` widget (UI convenience only) |
| Configurable plans | Admin-editable price/currency/feature-list; flagship "Complete Premium Application Package" ($100 default, fully admin-editable) seeded once at startup | ✅ Implemented, tested | ✅ Real pricing/feature list on the landing screen |
| Applicant background data | Structured education/work-experience/project/publication/award/leadership/skill/reference facts — the only source AI generation may read from | ✅ Implemented, tested | ⬛ No screen yet (API-only) |
| Application preparation | Category-driven workspace (9 applicant categories), requirement matching against real opportunity text, documented readiness score, auto-generated checklist | ✅ Implemented, tested | ⬛ No screen yet (API-only) |
| CV / ATS | Deterministic CV assembly from real background data, optional AI wording polish (never adds facts), rule-based ATS analysis with an explicit "does not guarantee acceptance" disclaimer, PDF/DOCX export | ✅ Implemented, tested | ⬛ No screen yet (API-only) |
| SOP / Study Plan / Research Proposal / Fellowship prep | AI-generated, strictly grounded in real applicant facts + their own questionnaire answers — never fabricates an award, degree, publication, or citation | ✅ Implemented, tested | ⬛ No screen yet (API-only) |
| Document versioning | Append-only version history; restore copies into a new version, never rewinds in place | ✅ Implemented, tested | ⬛ No screen yet (API-only) |
| Usage limits | Configurable per-feature daily/monthly AI-request ceilings | ✅ Implemented, tested | ⬛ No UI |
| Admin dashboard | Plan CRUD, payments/refunds, revenue, AI usage, usage-limit config | ✅ Implemented, tested | ⬛ No UI |
| Premium landing/pricing/checkout | Real plan/price/feature display, checkout initiation, "You have Premium" status | ✅ | ✅ Implemented (`lib/features/premium/`) |

**AI provider**: same "never fabricate, provider-independent, honest
not-configured state" pattern as payments — see Architecture.md §9.2.
Neither a payment nor an AI provider has real credentials configured in
any environment this project has had access to; both are fully
implemented and tested against the honest "not configured" failure mode
(`NullPaymentProvider`/`NullAIProvider`), never a fabricated success.

### 3.2 Partial — real backend exists but has a known wiring gap

**Resolved 2026-08-21** (see `Changelog.md`): the search-index/dashboard/
reminder/consent gaps previously listed here were fixed — search-index
rebuild now reads from the real opportunity repository, the Verification
Officer dashboard is fully real-data-backed, reverification reminders
deliver real in-app notifications, and document sharing enforces active
consent server-side. One narrower gap remains, listed below.

| Feature | Description | Gap | Status |
|---|---|---|---|
| Reverification reminder recipients | Who gets notified that an opportunity is due for reverification | The backend has no local user directory or per-officer assignment concept, so recipients are drawn from real audit history (officers who have made a `verification_*` decision before) rather than a full role roster — a brand-new officer with zero prior decisions won't receive reminders until their first one. Closing this fully needs a Firebase Admin SDK "list users by custom claim" integration, which requires a live Firebase project to build and test against (not available in this environment). | 🟡 Partial — see Task.md |
| Provider document-sharing at read/download time | Storage-level enforcement of a sharing grant | The Postgres-level consent-gated grant (`shared_with_provider_ids`) is now real and consent-checked, but there is still no endpoint for a provider to actually fetch a shared document, and `storage.rules` still scopes `applicant-documents/` to owner-only. This was already a documented, separate follow-up before this fix (`applicant_documents.py`) and remains one. | 🟡 Partial — see Task.md |

### 3.3 Demo-only — reachable in the app, no real backend

None remaining as a *primary user-facing feature* — every screen reachable
from a real dashboard is now backed by a real API. The `background_jobs`
queue itself (`DemoJobQueueRepository`) is intentionally an in-process
client-side scheduler, not a server-persisted queue — this is a deliberate
design choice, not a gap.

### 3.4 Not started — no backend, no reachable UI (dead/orphaned code)

These exist only as domain models + a demo repository, are exercised by unit
tests, but have **no presentation layer and no `app.dart` wiring** — a user
can never reach them:

| Feature | What exists | Status |
|---|---|---|
| `eligibility_rules` | Domain model, evaluator, demo repository | ⬛ Not started (no backend route, no screen) |
| `integrations` | Domain model, demo repository | ⬛ Not started |
| `data_transfer` | Domain model, demo repository | ⬛ Not started |
| `platforms` | Domain model, demo repository | ⬛ Not started |

**Recommendation, not yet decided by the product owner:** either build these
out (backend route + screen) or delete them — see Task.md.

### 3.5 Structurally out of scope today (documented, not silently missing)

- Opportunity-provider self-submission against the **Grants.gov-family**
  pipeline specifically (`api_opportunity_repository.dart`'s `submit()`
  throws `UnsupportedError` by design — provider submission instead uses the
  separate, real `provider_opportunities` pipeline).
- A Security Officer read endpoint for audit/rate-limit data (RBAC role
  exists; no route reads it yet).
- A Super-Administrator-editable source registry UI (adding an 8th
  opportunity source today requires a code change).
- A second real payment provider adapter (Paystack/Flutterwave) — the
  `PaymentProvider` interface supports adding one without touching any
  calling code (see §3.1a), but only the Stripe reference adapter exists
  today, and no provider has real credentials configured yet.
- A client-side payment SDK integration in Flutter (e.g. `flutter_stripe`)
  for the card-entry step of checkout — tied to whichever provider is
  eventually chosen, so deliberately not added speculatively.

---

## 4. Non-Functional Requirements

**Security.** See [Architecture.md](Architecture.md) §Security and the
standing reference `docs/SECURITY_MODEL.md`. Firebase Auth is the sole
identity system (no local password/JWT code); every backend route is
RBAC-gated server-side; Firestore/Storage are default-deny except two
explicitly-scoped paths; all HTML from external sources is sanitized;
rate limiting is Redis-backed and fail-open.

**Reliability.** Redis outage degrades rate limiting to "off," never to API
downtime. Import deduplication is idempotent (exact-duplicate skip via
payload hash). `docs/operations.md` sets an RPO of 15 minutes and RTO of 4
hours as the target, with daily full backups + continuous transaction-log
backup — **not yet implemented as running infrastructure**, this is the
documented target for whoever provisions production infrastructure.

**Scalability.** Async SQLAlchemy throughout; paginated list endpoints
(`Query(le=100)` caps); Celery/Redis for background sync so opportunity
imports never block a request. No load testing has been performed against
production-scale data (`docs/PRODUCTION_SECURITY_AUDIT.md` §14).

**Accessibility.** Style is "Accessible & Ethical" per
`design-system/scholarsphere/MASTER.md`: 16px minimum body text, visible
focus rings, 44×44/48×48dp minimum touch targets, `disableAnimations`
respected throughout, status never conveyed by color alone, high-contrast
theme variant shipped in `lib/app/theme.dart`.

**Responsiveness.** Flutter web/Android/iOS/macOS/Linux/Windows targets;
responsive breakpoints documented in Design.md; the auth screen has an
explicit wide/narrow layout split (`_wideBreakpoint = 900.0`).

**Maintainability.** Feature-sliced `domain/data/presentation` per feature;
one Alembic migration per backend domain; one Pydantic schema module per
model; a dual `demo_*`/`api_*` repository pattern that lets screens be built
and tested before a real backend exists, then swapped in `app.dart` without
touching presentation code.

---

## 5. User Flows

**Applicant: discover → apply → track**
1. Sign up / sign in (Firebase Auth) → email verification gate if unverified.
2. `DiscoverScreen` — search/filter published+verified opportunities.
3. Open an opportunity detail — eligibility match panel, fraud-warning panel
   (if applicable), evidence, required documents.
4. Save/apply — creates an `Application` record (real backend).
5. Track progress through 10 stages in `ApplicationTrackerScreen`.
6. Receive deadline notifications (30/14/7/3/1-day schedule) in the
   notification center.

**Provider: register → get verified → submit opportunity → publish**
1. Register organization (`ProviderAccountScreen`) — risk score computed
   server-side, duplicate-domain check.
2. Wait for `pendingReview` → Verification Officer/Administrator reviews
   against the 5-item provider checklist.
3. Once `verified` with `publish_opportunities` permission, submit an
   opportunity via the `provider_opportunities` pipeline.
4. Verification Officer/Administrator reviews the submitted opportunity
   (separate pipeline from Grants.gov-family imports).
5. Administrator publishes — now visible in `provider_opportunities`, but
   **not** in the public `GET /opportunities` Grants.gov-family listing
   (deliberately isolated pipelines, verified by test).

**Verification Officer: review imported opportunity**
1. Open `LiveVerificationQueueScreen` — lists `pending` records.
2. Open one — evidence panel (raw source payload), current review state,
   history load in parallel.
3. Complete the 4-item checklist; choose one of 6 decisions with a mandatory
   reason.
4. Optionally add a note or edit fields (both audited, description
   re-sanitized on edit).
5. `verified` records wait for a separate Administrator publication action.

---

## 6. Acceptance Criteria (representative, not exhaustive)

- An opportunity **must never** appear in `GET /opportunities` unless
  `verification_status == verified AND publication_status == published`
  (regression-tested: `test_import_requires_approval_then_explicit_publication_and_audits`).
- Approving an opportunity **must** fail with `409` if any of the 4
  checklist items is false.
- Every verification decision, note, or edit **must** produce a
  `VerificationHistory` row and an `ImportAuditLog` entry with actor, reason,
  and a before/after diff.
- A provider **cannot** submit an opportunity unless their organization's
  `verification_status == verified` and they hold `publish_opportunities`
  permission — checked against their own Firebase UID server-side, never a
  client-asserted `provider_id`.
- Every backend route requiring elevated access must reject an
  insufficiently-privileged token with `403`, evaluated against the
  server-verified token's `role` claim, never a client-supplied field.
- Production boot must fail if `DATABASE_URL`/`REDIS_URL` still contain
  their local-development placeholder values, or if a `*_BASE_URL` external
  source setting is not HTTPS.
- Release deployment (`POST /release/deployments`) must be blocked unless
  the target version's quality report is `production_ready`, and
  self-approval by the same actor who requested it must be rejected.
- A document share (`POST /applicant-documents/{id}/share`) **must** fail
  with `409` unless the caller has an active (`granted`, not `withdrawn`)
  `third_party_sharing` consent record, and with `404` if the target
  provider doesn't exist — regression-tested
  (`test_grant_provider_access_blocked_without_consent`,
  `test_grant_provider_access_blocked_after_consent_withdrawn`,
  `test_grant_provider_access_rejects_unknown_provider`).
- Withdrawing `third_party_sharing` consent **must** clear every existing
  `shared_with_provider_ids` grant for that user's documents, not just
  block new ones — regression-tested
  (`test_withdrawing_consent_revokes_existing_provider_shares`).
- The real search index (`POST /search-index/rebuild`) **must** be rebuilt
  from real, verified opportunity records — regression-tested end-to-end
  (`search-index background job rebuilds from the real opportunity
  repository, not demo data`, `test/widget_test.dart`).
- Reverification reminders **must** create exactly one notification per
  (opportunity, recipient) pair per due cycle — re-running the task must
  not create duplicates — regression-tested
  (`test_reverification_reminders_are_not_duplicated_on_rerun`) — and must
  never report a notification as delivered without a real delivery
  mechanism backing the claim (in-app only, today).

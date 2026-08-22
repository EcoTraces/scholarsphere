# ScholarSphere — Database Documentation

**Last verified against the codebase:** 2026-08-21. Sourced directly from
`scholarsphere_backend/app/models/*.py` (26 files) and
`scholarsphere_backend/alembic/versions/*.py` (31 migrations). No table or
field below is invented.

---

## 1. Database Overview

**Two separate datastores, deliberately not merged:**

| Store | Holds | Access pattern |
|---|---|---|
| **PostgreSQL 16** (`scholarsphere_backend/`) | All business data: opportunities, applications, providers, moderation, audit, etc. | Async SQLAlchemy 2.0 via `asyncpg`, one `AsyncSession` per request (`app/db/session.py`) |
| **Firestore** (Firebase project `scholarsphere-d44f5`) | **Only** the `users/{uid}` collection — account identity, role, status, notification preferences | Firebase SDK client-side + Cloud Functions server-side; secured by `firestore.rules` |

There is **no local users table in PostgreSQL** — identity lives entirely in
Firebase, and PostgreSQL tables that need a user reference store the
Firebase UID as a plain string column (e.g. `providers.user_id`), never a
foreign key into a users table that doesn't exist on that side.

**Connection strategy:** `create_async_engine(settings.database_url,
pool_pre_ping=True, pool_recycle=1800)`
(`scholarsphere_backend/app/db/session.py`). `DATABASE_URL` env var, default
`postgresql+asyncpg://scholarsphere:change-me@localhost:5432/scholarsphere`
— production boot refuses to start if this still contains `change-me`.
Tests run against SQLite via `aiosqlite` with dependency overrides, not a
real Postgres instance.

**Migrations:** Alembic, fully async (`alembic/env.py` uses
`async_engine_from_config` + `run_sync`), one revision per backend domain,
added roughly one per day from 2026-07-31 through 2026-09-13 (see §7 for the
full ordered list).

**Conventions used throughout:** primary keys are native `Uuid` (PostgreSQL
native UUID) unless a domain-meaningful string/int PK made more sense
(noted per table below); `created_at`/`updated_at` are
`DateTime(timezone=True)` with `server_default=func.now()`; `JSONType` (a
`JSON().with_variant(JSONB(), "postgresql")` defined once in
`external_opportunity.py` and imported everywhere) is used for flexible
list/object fields instead of separate child tables where the data is
genuinely unstructured (e.g. `feature_flags` on `platform_configurations`).

---

## 2. Data Models

Grouped by domain. FK behavior (`CASCADE`/`RESTRICT`/`SET NULL`) is called
out because it encodes real business rules (e.g. deleting a provider cascades
its administrators, but an opportunity can't be deleted while an application
references it).

### 2.1 Provider domain

**`providers`** — organization registration record.
`id` (PK), `user_id` (Firebase UID, owner), `organization_name`,
`organization_type`, `registration_number`, `country`, `official_website`,
`official_email_domain` (case-insensitive unique index —
`lower(official_email_domain)`), `physical_address`, `contact_person`,
`contact_phone`, `supporting_documents` (JSON list of Storage paths),
`social_media_links` (JSON list), `status` (enum: draft → pendingReview →
additionalInformationRequired → verified → rejected → suspended →
verificationExpired → archived), `risk_score` (int, server-computed),
`permissions` (JSON list), `verification_date`, `verified_by`,
`reverification_date`, `review_note`.

- **`provider_administrators`** — FK `provider_id`→`providers` (CASCADE),
  unique(`provider_id`, `user_id`). Sub-administrators with per-admin
  permission subsets.
- **`provider_activity_history`** — FK `provider_id` (CASCADE). Append-only
  activity log.
- **`provider_appeals`** — FK `provider_id` (CASCADE). Appeal records
  against a rejection/suspension.

### 2.2 Provider-submitted opportunities

**`provider_opportunities`** — FK `provider_id`→`providers` (**RESTRICT** —
a provider can't be deleted while it has opportunities). Type, funding
type, delivery format, verification status, publication status all enums;
many nullable eligibility fields (nationality, age range, field of study,
etc.). Deliberately a **separate schema** from `external_opportunities`
(§2.3) — different verification-status set, no shared review model.

- **`provider_opportunity_verification_reviews`** — FK
  `provider_opportunity_id` **unique** (one review row per opportunity),
  CASCADE.
- **`provider_opportunity_verification_history`** — FK CASCADE, indexed for
  audit queries.

### 2.3 External (Grants.gov-family) opportunities

**`opportunity_sources`** — one row per integrated API (7 rows, seeded
idempotently by `app/services/source_registry.py`). `source_code` unique.

**`raw_external_opportunities`** — the verbatim payload as first collected.
FK `source_id`→`opportunity_sources` (RESTRICT), FK
`opportunity_id`→`external_opportunities` (**SET NULL** — a raw record can
outlive the normalized one it produced), unique(`source_id`,
`external_id`).

**`external_opportunities`** — the normalized, verification-pipeline record.
FK `source_id` (RESTRICT), unique(`source_id`, `external_id`), indexes on
`verification_status`+`publication_status` and on the duplicate-detection
fingerprint. This is the table `GET /opportunities` reads from, filtered to
`verification_status='verified' AND publication_status='published'`.

- **`external_opportunity_verification_history`** — FK CASCADE. Every
  status transition/note/edit, with `previous_status`, `new_status`,
  required `reason`, `changed_fields` JSON diff.
- **`external_opportunity_verification_reviews`** — FK **unique**, CASCADE.
  The 4-item checklist (`source_checked`, `application_link_checked`,
  `deadline_checked`, `duplicate_checked`).
- **`opportunity_sync_history`** — FK `source_id` (RESTRICT). One row per
  sync run.
- **`external_import_audit_log`** — **append-only**, FK `opportunity_id`
  (RESTRICT). Every pipeline action, actor, correlation ID, previous/new
  value snapshot. No update/delete service exposed for this table by design.

### 2.4 Applications & applicant data

**`applications`** — FK `opportunity_id`→`external_opportunities`
(RESTRICT — can't delete an opportunity that's been applied to), **unique(`user_id`, `opportunity_id`)** — one application per applicant per
opportunity. Snapshots `opportunity_title`/`provider_name`/`deadline` at
save time (so history reads correctly even if the source record changes
later); `stage` enum (10 stages).

**`applicant_profiles`** — PK **is** `user_id` (one row per applicant, no
separate surrogate ID).

**`applicant_documents`** — **unique(`user_id`, `type`)** — uploading a new
document of a given type replaces the old row rather than versioning it.
`storage_path` validated server-side against the expected
`applicant-documents/{uid}/{fileName}` shape.

### 2.5 Notifications

**`notification_preferences`** — PK `user_id`.
**`notification_templates`** — client-chosen string PK.
**`scholarsphere_notifications`** — string PK (sometimes deterministic,
e.g. `{opportunity_id}-deadline-{days}` for the 30/14/7/3/1-day applicant
reminder schedule, or `{opportunity_id}-reverification-officer-{uid}` for
staff reverification reminders — both patterns make re-running their
respective scheduler idempotent by primary-key collision). FK
`opportunity_id`→`external_opportunities` (RESTRICT), FK
`template_id`→`notification_templates` (**SET NULL**). Composite indexes
on (`user_id`, `status`) and `scheduled_for`. `type` includes a
staff-facing `reverification_due` event (added 2026-08-21) alongside the
applicant-facing event types — see
`app.tasks.opportunity_sync._send_reverification_reminders`.

### 2.6 Moderation & fraud

**`moderation_cases`** — `entity_id` is a **plain string, not a FK**
(polymorphic — can reference an opportunity, provider, or user).
**`moderation_case_history`** — FK `case_id` (CASCADE).
**`moderation_warnings`** — FK `case_id`→`moderation_cases` (**RESTRICT**).

**`fraud_cases`** — string PK, multiple `risk_*` int scores + a `risk_level`
enum. **`fraud_watchlist_entries`** — string PK.

### 2.7 Privacy & legal

**`consent_records`** — **unique(`user_id`, `type`)**.
**`privacy_requests`**, **`organization_access_records`**,
**`privacy_incidents`** — independent tables, no cross-FKs.

**`legal_policies`** — string PK, **unique(`type`, `version`)** (versioned
policy documents). **`policy_acceptances`** — **unique(`user_id`,
`policy_id`)**, FK `policy_id`→`legal_policies` (CASCADE). **`legal_requests`**,
**`compliance_records`** — string PK.

### 2.8 Support

**`support_tickets`** — root record.
**`support_messages`**, **`support_internal_notes`**,
**`support_ticket_history`** — all FK `ticket_id` (CASCADE).
**`knowledge_articles`**, **`support_response_templates`** — string PK.
**`satisfaction_surveys`** — PK **is** `ticket_id`, FK (CASCADE).

### 2.9 Registry, taxonomy, calendar, guidance, experience, search

**`source_registry_entries`** — string PK, `normalized_domain` indexed.
**Distinct from** `opportunity_sources` (§2.3) — this is the general
source-trust registry (trust level/score/verification status), not the
7-source ingestion allowlist.

**`taxonomy_terms`** — string PK, **self-referential** FK
`parent_id`→`taxonomy_terms` (**SET NULL**). **`taxonomy_versions`** — PK
`version` (int, global counter).

**`calendar_events`** — string PK, `related_entity_id` is a plain string
(no FK — polymorphic).

**`guidance_plans`** — string PK; items/recommendation-letters/submission
confirmation stored as **JSON blobs**, not normalized child tables
(deliberate — this data doesn't need independent querying).

**`experience_preferences`** — PK `user_id`.
**`translation_entries`** — **composite PK** (`language`, `key`).

**`search_index_entries`** — string PK, `data` is an opaque JSON snapshot.
**`search_history_entries`** — independent.

### 2.10 Analytics & recommendations

**`opportunity_view_events`** — FK `opportunity_id`→`external_opportunities`
(RESTRICT).
**`personalization_controls`** — PK `user_id`.
**`recommendation_history_entries`**, **`recommendation_feedback`** —
independent.
**`engagement_events`** — FK `provider_id`→`providers` (**CASCADE**).

### 2.11 Security & audit

**`login_history_entries`**, **`security_sessions`** (string PK),
**`security_alerts`** — independent, no cross-table FKs.

**`audit_records`** — **autoincrement int PK**, `integrity_hash`
(hash-chained — each record's hash covers the previous record, so tampering
with history is detectable). **`audit_chain_state`** — singleton row
(string PK), tracks the current chain `anchor`. **`audit_retention_policy`**
— string PK.

### 2.12 Operations

**`backup_policies`**, **`backup_records`**, **`recovery_tests`** (FK
`backup_id`→`backup_records`, CASCADE) — string PK.
**`quality_reports`** — PK **is** `release_version`; has a computed
`production_ready` property gating deployment approval.
**`deployment_records`** — string PK.
**`retention_rules`** — PK **is** the `entity_type` enum value.
**`lifecycle_records`** — **composite PK** (`entity_type`, `entity_id`).
**`legal_holds`** — independent.
**`application_logs`**, **`metric_points`** — independent.
**`trace_spans`** — **composite PK** (`trace_id`, `span_id`).
**`alert_rules`**, **`operational_incidents`** — string PK.

### 2.13 Collection & configuration

**`collection_ledger_entries`** — FK
`opportunity_id`→`external_opportunities` (RESTRICT). Provenance ledger for
manual/provider/API/RSS/feed/web/user-sourced records.

**`platform_configurations`** — PK **is** `version` (int). Versioned
platform config — `feature_flags`, `security_policy`, etc. as JSON.

---

## 3. Relationships

**One-to-one:** `provider_opportunity_verification_reviews` ↔
`provider_opportunities`; `external_opportunity_verification_reviews` ↔
`external_opportunities`; `satisfaction_surveys` ↔ `support_tickets`;
`applicant_profiles`/`experience_preferences`/`notification_preferences`/
`personalization_controls` ↔ Firebase UID (each PK **is** `user_id`).

**One-to-many:** `providers` → `provider_administrators` /
`provider_activity_history` / `provider_appeals` / `provider_opportunities`
/ `engagement_events`; `opportunity_sources` →
`raw_external_opportunities` / `external_opportunities` /
`opportunity_sync_history`; `external_opportunities` →
`verification_history` / `applications` / `opportunity_view_events` /
`collection_ledger_entries`; `support_tickets` → `messages` / `notes` /
`history`; `moderation_cases` → `history` / `warnings`;
`taxonomy_terms` → self (parent/children); `legal_policies` →
`policy_acceptances`; `backup_records` → `recovery_tests`.

**Many-to-many:** none modeled via an explicit join table — the closest
pattern is `provider_administrators` (provider ↔ user, unique pair), which
is really a one-to-many with a uniqueness constraint rather than a true
join table, since a `provider_administrator` row carries its own
permission-subset data rather than being a bare link.

**Polymorphic (string reference, not FK):** `moderation_cases.entity_id`,
`calendar_events.related_entity_id` — deliberately not FKs because they can
point at different tables depending on `entity_type`.

---

## 4. Data Integrity

- **Uniqueness constraints** enforcing real business rules: one application
  per (user, opportunity); one applicant document per (user, type); one
  consent per (user, type); one policy acceptance per (user, policy); one
  provider-administrator per (provider, user); case-insensitive unique
  `official_email_domain` per provider (a real Postgres functional index —
  `lower(official_email_domain)` — chosen specifically to close a
  race-condition duplicate-registration gap that an application-level-only
  check would leave open).
- **Referential integrity:** every FK explicitly declares `CASCADE`,
  `RESTRICT`, or `SET NULL` per the business meaning (see §2) — RESTRICT is
  used wherever deleting the parent would silently orphan meaningful
  history (e.g. can't delete an opportunity with applications against it).
- **Validation:** all writes go through a narrow Pydantic schema, never the
  raw ORM row — e.g. `NormalizedExternalOpportunity` hardcodes
  `verification_status=pending`/`publication_status=unpublished` on import
  so a caller can't inject a pre-verified record; `OpportunityEditRequest`
  bounds every field's length/type independently and requires HTTPS on URL
  fields.
- **Indexes:** on FK columns used in hot queries (`verification_status`+
  `publication_status` composite on `external_opportunities`; duplicate
  fingerprint; `normalized_domain` on source registry entries;
  (`user_id`,`status`) and `scheduled_for` on notifications).
- **Audit trail integrity:** `audit_records.integrity_hash` chains each
  record to the previous one (`audit_chain_state` tracks the anchor) —
  tampering with historical audit rows is detectable via
  `GET /audit/integrity`.

---

## 5. Security

- **Access control:** every route touching these tables is gated by
  `require_roles`/`require_permissions` (`app/core/rbac.py`), evaluated
  against the server-verified Firebase token — never a client-supplied
  field. See Architecture.md §4/§7.
- **Firestore rules** (`firestore.rules`): default-deny on every collection
  except `users/{uid}`; even there, `create` forces `role='applicant'` and
  a valid initial status, `update` makes `uid`/`email`/`role` immutable and
  allowlists exactly which fields a user may change themselves
  (`fullName`, `emailVerified`, `status`, `marketingEmailsEnabled`,
  `deadlineNotificationsEnabled`), `delete` is always `false`.
- **Storage rules** (`storage.rules`): default-deny except
  `provider-documents/{uid}/*` (owner + staff-role read, owner-only write,
  10MB/PDF-JPEG-PNG cap, no delete — append-only evidence) and
  `applicant-documents/{uid}/*` (owner-only read/write, no staff read at
  all — treated as more sensitive). Per-provider sharing is tracked in
  Postgres (`applicant_documents.shared_with_provider_ids`), not Storage
  rules. Since 2026-08-21, granting a share is gated server-side on an
  active `consent_records` row of type `third_party_sharing` (409
  otherwise) and a real, existing `providers` row (404 otherwise); every
  successful grant also writes an `organization_access_records` entry so
  the applicant can see it via `GET /privacy/access-history`. Withdrawing
  that consent (`POST /privacy/consents/thirdPartySharing/withdraw`)
  cascades to clear `shared_with_provider_ids` on every one of that user's
  documents, not just block new grants. Storage-level enforcement of the
  grant (a provider actually fetching the file) remains a separate,
  not-yet-built follow-up — see PRD.md §3.2.
- **Sensitive-data handling:** no local password storage exists anywhere
  (identity is entirely Firebase-managed); backend API keys are
  Pydantic `SecretStr`-wrapped so they can't leak via logs/`repr()`; no
  `.env` files or service-account JSON are committed.

---

## 6. Database Operations (representative CRUD)

- **Create:** e.g. `POST /providers` → validates via `ProviderCreate`
  schema → server computes `risk_score` (never client-supplied) → inserts
  `providers` row with `status=draft`.
- **Read (paginated, staff-only):** e.g. `GET /applications/admin` — 
  `Query(le=100)` page-size cap, filterable by `user_id`/`stage`.
- **Update (versioned/audited):** e.g. `PATCH /external-opportunities/opportunities/{id}` — every field diffed into `VerificationHistory.changed_fields`
  and `ImportAuditLog`, mandatory `reason`, nothing overwritten silently.
- **Soft delete / restore:** `POST /data-lifecycle/records/{entity_type}/{entity_id}/soft-delete` → `.../restore` → `.../permanently-delete`,
  gated separately, with a `legal-holds` override that can block permanent
  deletion.
- **Append-only (no update/delete route by design):** `ImportAuditLog`,
  `VerificationHistory`, `audit_records`.

---

## 7. Migration History (`alembic/versions/`, chronological)

| Revision | Domain |
|---|---|
| `20260731_01_external_opportunities` | External opportunities core schema |
| `20260731_02_sync_operations` | Sync history |
| `20260731_03_audit_hardening` | Audit log hardening |
| `20260817_04_applications` | Applications |
| `20260818_05_providers` | Providers |
| `20260818_06_provider_opportunities` | Provider-submitted opportunities |
| `20260820_07_notifications` | Notifications |
| `20260821_08_applicant_profiles` | Applicant profiles |
| `20260822_09_applicant_documents` | Applicant documents |
| `20260823_10_moderation` | Moderation |
| `20260824_11_privacy` | Privacy |
| `20260825_12_support` | Support |
| `20260826_13_source_registry` | Source registry |
| `20260827_14_taxonomy` | Taxonomy |
| `20260828_15_calendar` | Calendar |
| `20260829_16_guidance` | Guidance |
| `20260830_17_experience` | Experience preferences |
| `20260831_18_search_index` | Search index |
| `20260901_19_legal_compliance` | Legal compliance |
| `20260902_20_analytics` | Analytics |
| `20260903_21_recommendation_governance` | Recommendations |
| `20260904_22_provider_analytics` | Provider analytics |
| `20260905_23_security` | Security (sessions, login history, alerts) |
| `20260906_24_audit_log` | Audit log (hash-chain) |
| `20260907_25_system_configuration` | System configuration |
| `20260908_26_backup` | Backup |
| `20260909_27_release` | Release management |
| `20260910_28_data_lifecycle` | Data lifecycle |
| `20260911_29_observability` | Observability |
| `20260912_30_fraud_investigation` | Fraud investigation |
| `20260913_31_collection` | Collection ledger |

All 31 revisions chain and compile cleanly against the PostgreSQL dialect
(validated offline via `alembic upgrade head --sql`, per
`docs/PRODUCTION_SECURITY_AUDIT.md` §14). Run `alembic current` to check
what's actually applied to a given database.

---

## 8. Entity Relationship Diagram (core domain)

The full schema is 40+ tables — too many to render legibly in one diagram.
Below is the core opportunity/application/provider graph; the remaining
domains (moderation, support, security, operations, etc.) are documented in
full in §2 but omitted here for readability.

```mermaid
erDiagram
    OPPORTUNITY_SOURCES ||--o{ EXTERNAL_OPPORTUNITIES : "sources"
    EXTERNAL_OPPORTUNITIES ||--o| EXTERNAL_OPP_VERIFICATION_REVIEW : "has"
    EXTERNAL_OPPORTUNITIES ||--o{ EXTERNAL_OPP_VERIFICATION_HISTORY : "logs"
    EXTERNAL_OPPORTUNITIES ||--o{ APPLICATIONS : "applied to"
    EXTERNAL_OPPORTUNITIES ||--o{ COLLECTION_LEDGER_ENTRIES : "collected via"
    PROVIDERS ||--o{ PROVIDER_ADMINISTRATORS : "has"
    PROVIDERS ||--o{ PROVIDER_APPEALS : "files"
    PROVIDERS ||--o{ PROVIDER_OPPORTUNITIES : "submits"
    PROVIDER_OPPORTUNITIES ||--o| PROVIDER_OPP_VERIFICATION_REVIEW : "has"
    APPLICANT_PROFILES ||--o{ APPLICATIONS : "owns (by user_id)"
    APPLICANT_PROFILES ||--o{ APPLICANT_DOCUMENTS : "owns (by user_id)"

    EXTERNAL_OPPORTUNITIES {
        uuid id PK
        uuid source_id FK
        string external_id
        enum verification_status
        enum publication_status
    }
    PROVIDERS {
        uuid id PK
        string user_id "Firebase UID"
        enum status
        int risk_score
    }
    PROVIDER_OPPORTUNITIES {
        uuid id PK
        uuid provider_id FK
        enum verification_status
        enum publication_status
    }
    APPLICATIONS {
        uuid id PK
        string user_id "Firebase UID"
        uuid opportunity_id FK
        enum stage
    }
    APPLICANT_PROFILES {
        string user_id PK "Firebase UID"
    }
    APPLICANT_DOCUMENTS {
        uuid id PK
        string user_id
        enum type
    }
```

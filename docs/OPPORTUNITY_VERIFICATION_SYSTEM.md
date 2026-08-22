# ScholarSphere — Opportunity Verification System

This document describes how an opportunity moves from an external source to
something an applicant can trust, who is responsible for each step, and what
rules the system enforces. It describes the **real, running system** in
`scholarsphere_backend/` and the live Flutter screens wired to it — not an
aspirational design. Where a role or capability described in the platform's
original specification does not exist yet, that is stated explicitly rather
than implied.

## 1. Scope

Two pipelines exist today:

- **Automated import**, from seven official structured APIs and five
  web-scraper sources (see `docs/AUTHORITATIVE_SOURCES.md`) into a human
  review queue. The scraper sources exist only for organizations with no
  official API, RSS feed, or dataset; they are governed by the same
  "never invent data" rule as every other source and land in exactly the
  same queue below — **web scraping changes how data is retrieved, never
  whether a human approves it.**
- **Human verification**, performed by a Verification Officer (or an
  Administrator/Super Administrator acting in that capacity) through the
  live queue described in §5. This remains mandatory for every source,
  including the highest-trust official APIs — see §6 for the
  triage/priority signal that helps an officer work through a growing
  queue without weakening that requirement.

Not yet built: opportunity-provider self-submission, a Security Officer
dashboard, and a Super Administrator source-registry editor. These are
listed in `docs/PRODUCTION_SECURITY_AUDIT.md` §0/§18 as scope gaps, not
implied to exist here.

## 2. Pipeline

```
Official source API, or a source's own public web page
      |
   FETCH            app/services/{grants_gov,simpler_grants,eu_funding,
      |              usajobs,reliefweb}.py (API sources) or
      |              app/services/web_scraper_base.py subclasses
      |              (cscuk_scholarships, chevening, daad_scholarships,
      |              embassy_announcements) — HTTPS-only, timeout +
      |              size-capped, bounded retries either way
      |              (app/core/http_client.py::get_json/get_html);
      |              scrapers additionally rate-limit per host
      v
   NORMALIZE         NormalizedExternalOpportunity (app/schemas/external_opportunity.py)
      |              description HTML-sanitized (bleach) at this step
      v
   RawExternalOpportunity stored verbatim  (app/models/external_opportunity.py)
      |
   DEDUPLICATE       exact: source + external_id + payload SHA-256 (skip if unchanged)
      |              cross-source: title/provider/deadline fingerprint -> duplicate_review_required flag
      v
   ExternalOpportunity created, always:
      verification_status = pending
      publication_status  = unpublished
      |
      v
   VERIFICATION QUEUE   GET /external-opportunities/pending-verification
      |                 (Verification Officer / Administrator / Super Administrator only)
      v
   OFFICER DECISION     POST /external-opportunities/opportunities/{id}/verification
      |
      +-- approved -----------------> verification_status = verified
      +-- rejected -----------------> verification_status = rejected
      +-- reverification_required --> verification_status = reverification_required
      +-- expired ------------------> verification_status = expired
      +-- source_unavailable -------> verification_status = source_unavailable
      +-- suspicious ---------------> verification_status = suspicious
      |
      v  (verified only)
   PUBLICATION          POST /external-opportunities/opportunities/{id}/publication
      |                 (Administrator / Super Administrator only — a separate,
      |                  deliberate action from verification; approval alone
      |                  never makes an opportunity public)
      v
   Applicant-visible listing   GET /opportunities  (verification_status == verified
                                                     AND publication_status == published,
                                                     only)
```

Every arrow that changes state also writes an append-only
`VerificationHistory` row and an `ImportAuditLog` entry (actor, action,
previous/new value, correlation ID) — see §7.

## 3. Verification states

Defined in `app/models/external_opportunity.py` (`VerificationStatus`):

| State | Meaning | Set by |
|---|---|---|
| `pending` | Imported, awaiting a first decision | Import |
| `verified` | Approved by an officer, all four checks passed | Officer decision (`approved`) |
| `rejected` | Not a legitimate/confirmable opportunity | Officer decision (`rejected`) |
| `reverification_required` | Was verified, needs another look | Officer decision, **or** automatically every 90 days after `verified_at` (`schedule_reverification`, Celery beat, daily at 02:15 UTC) |
| `expired` | Deadline has passed | Officer decision, **or** automatically once `deadline < today` (`detect_expired_opportunities`, daily at 01:05 UTC — also force-archives `publication_status`) |
| `source_unavailable` | The official source no longer resolves/confirms the listing | Officer decision only |
| `suspicious` | Flagged for fraud/authenticity concerns | Officer decision only |
| `archived` | Retired from active review | Reserved; no code path sets this automatically today |

The platform specification's `DISCOVERED`/`UNDER_REVIEW`/`SOURCE_UNAVAILABLE`
naming maps onto this list as: `DISCOVERED` → `pending`,
`UNDER_REVIEW` → an opportunity currently sitting in the pending-verification
queue (not a separate stored state), `SOURCE_UNAVAILABLE` → `source_unavailable`.

**Every decision except `approved` only requires a non-empty reason.**
`approved` additionally requires all four checklist items to be `true`
(`app/api/routes/external_opportunities.py::decide_verification` — a 409 is
returned otherwise, enforced server-side, not just in the UI).

## 4. The four-item checklist

Stored per-opportunity on `VerificationReview`
(`app/models/external_opportunity.py`), one row per opportunity, created at
import time:

- `source_checked` — the official source was confirmed to exist and say what the imported record claims
- `application_link_checked` — the application URL was confirmed to work and belong to the organization
- `deadline_checked` — the deadline shown matches the official source
- `duplicate_checked` — the queue's `duplicate_review_required` flag (if set) was investigated

This is deliberately narrower than the platform specification's illustrative
13-item checklist (organization exists, funding confirmed, fees confirmed,
contact details confirmed, no misleading claims, evidence stored, etc.) —
that richer checklist exists today only in the **demo** verification flow
(`lib/features/verification/domain/verification_review.dart`,
`DemoVerificationRepository`), which also models a two-person
assign-then-second-approve workflow the live backend does not implement.
Rather than fabricate that richer workflow's missing data against a backend
that doesn't track it, the live queue (`ApiVerificationRepository`,
`LiveVerificationQueueScreen`) is a separate, honestly-scoped screen built
against exactly what the backend really enforces. See the class doc comment
on `lib/features/verification/data/api_verification_repository.dart` for the
full reasoning.

## 5. The Verification Officer's real workflow

Reached via the Verification Officer dashboard's "Open queue" action, backed
by `ApiVerificationRepository` end-to-end:

1. **List** the queue — `GET .../pending-verification` (title, organization,
   type, country, description, opening date, deadline, funding, official
   source/application URLs, and whether it's flagged as a possible
   duplicate).
2. **Open** one opportunity — the review screen loads, in parallel:
   - **Evidence**: `GET .../opportunities/{id}/evidence` — the exact raw
     payload last collected from the official source, plus per-field
     extractions (`app/services/evidence.py`, shared with the applicant-facing
     evidence view but *not* gated on publication status, since an officer
     must see this before deciding whether to publish it).
   - **Current review state**: `GET .../opportunities/{id}/review`.
   - **History**: `GET .../opportunities/{id}/verification-history`.
3. **Decide** — `POST .../opportunities/{id}/verification` with one of the
   six decisions in §3, the four checks, and a mandatory reason.
4. **Add a note** (optional, any time) — `POST .../opportunities/{id}/notes`,
   an append-only timestamped remark that does **not** change verification
   status. This is the platform specification's `ADD_EVIDENCE` action,
   deliberately scoped to a note rather than the full structured
   per-field-evidence-with-source-citation record described in the
   specification — building that fully belongs with a future AI-provenance
   increment (§9) so it isn't half-built here.
5. **Edit fields** — `PATCH .../opportunities/{id}` (title, description,
   opening/closing date, funding type/floor/ceiling, currency, official
   source/application URL), with a **mandatory reason**. Every change is
   diffed field-by-field into both `VerificationHistory.changed_fields` and
   `ImportAuditLog` (previous value → new value) — nothing is overwritten
   silently, matching the specification's administrative-override
   evidence requirements (§44) applied at officer granularity. An edited
   `description` is run through the same HTML sanitizer
   (`app/services/parsing.py::sanitize_html`) that source-collected
   descriptions get, so an officer's edit cannot introduce unsanitized HTML
   that a source import would have stripped.

There is no `REQUEST_REVIEW` action distinct from `reverification_required`
— they are the same thing in this system: sending an opportunity back into
the "needs another look" state.

**`MARK_EXPIRED` is available as a manual officer action but is normally
unnecessary** — the daily `detect_expired_opportunities` task already
expires anything past its deadline automatically. The manual action exists
for a source whose deadline field is missing, wrong, or ambiguous but that
an officer has independently confirmed is closed.

## 6. Explainable confidence triage (never a bypass)

`GET .../pending-verification?sort=confidence` (added 2026-08-22,
`app/services/verification_confidence.py`) surfaces the most
trustworthy-looking pending records first, to help an officer work through
a growing queue. It is a **priority hint only**:

- It never sets `verification_status` or `publication_status` — nothing in
  the codebase gives it a path to do so.
- Every record, regardless of its confidence level, still needs an
  officer's explicit `approved` decision with all four checklist items
  before it can be published — exactly the same requirement as §3–§4.
- It is deterministic and rule-based, not AI/ML (see §10): official-API
  source (+40), web-scraped source (+15), no cross-source duplicate flag,
  all key fields present, a plausible (not past, not absurdly distant)
  deadline, and HTTPS source/application URLs all raise the score;
  missing fields, a duplicate flag, or an implausible deadline lower it.
  Every score ships with the specific `reasons` that produced it
  (`ConfidenceAssessment.reasons`), returned to the client as
  `confidence_level` and `confidence_reasons` on each queue item — an
  officer can always see *why*, never just a bare number.
- The default queue order (`collected_at desc`) is unchanged unless an
  officer explicitly asks for `sort=confidence`.

## 7. Publication is a separate, deliberate step

`verified` does not mean visible. An Administrator or Super Administrator
must separately call `POST .../opportunities/{id}/publication`
(`admin_access` — Verification Officers cannot publish). Publishing before
approval returns `409` (enforced server-side, regression-tested:
`scholarsphere_backend/tests/test_production_hardening.py::test_import_requires_approval_then_explicit_publication_and_audits`).

## 8. Audit trail

Two append-only tables back every claim above:

- **`VerificationHistory`** (`external_opportunity_verification_history`) —
  every status transition, note, and edit, with `previous_status`,
  `new_status`, a required `reason`, and a `changed_fields` JSON blob.
- **`ImportAuditLog`** (`external_import_audit_log`) — every action across
  the whole pipeline (imports, source activation, verification decisions,
  notes, edits, publication changes), with actor ID, actor role, a
  correlation ID, and previous/new value snapshots. No update/delete
  service is exposed for this table (`app/models/external_opportunity.py`
  docstring).

Neither table has a read endpoint for the Security Officer role yet — see
`docs/PRODUCTION_SECURITY_AUDIT.md` §2.6/§18 for that gap.

## 9. Duplicate handling

Cross-source duplicate candidates are flagged (`duplicate_review_required`
on `ExternalOpportunity`) but **never merged automatically** — a human
confirms via the `duplicate_checked` box before approval. The queue can be
filtered to duplicates-only via `?duplicate_only=true` on
`GET .../pending-verification`.

## 10. AI's role: none, today

There is no AI/LLM code anywhere in this repository
(`docs/PRODUCTION_SECURITY_AUDIT.md` §2.7, confirmed by repository-wide
search). Every fact shown to a verification officer or an applicant comes
directly from a structured field in an official source's API response, or
(as of 2026-08-22) directly from text actually present on a source
organization's own web page — never inferred, summarized, or generated.
The confidence-triage scoring in §6 is deterministic rule-based arithmetic
over fields that are themselves never invented, not a model prediction —
it does not change this statement. If AI-assisted extraction or
classification is added in the future, the platform specification's
non-negotiable rule applies: AI output must carry a source reference and a
confidence marker, must never itself set `verification_status`, and a human
verification officer remains the sole authority for approval.

## 11. Roles referenced above

| Role | Backend enforcement | Real capability today |
|---|---|---|
| Verification Officer | `require_roles("verificationOfficer", "administrator", "superAdministrator")` | Full workflow in §5 |
| Administrator | same set, plus `admin_access` for publication and source activation | Everything a Verification Officer can do, plus publish/unpublish and toggle a source active/inactive |
| Super Administrator | same as Administrator today | No additional backend capability exists yet beyond Administrator's |
| Security Officer | not wired to any route | No backend capability exists yet — see `docs/PRODUCTION_SECURITY_AUDIT.md` §18 |
| Opportunity Provider | not wired to any route | No submission pipeline exists yet — every opportunity today originates from the twelve API/scraper sources (`docs/AUTHORITATIVE_SOURCES.md`), not provider self-service |
| Applicant | `get_current_user` only (no role check) | Read-only access to `GET /opportunities` and its detail/evidence sub-routes, restricted server-side to `verified` + `published` records only |

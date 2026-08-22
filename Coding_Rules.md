# ScholarSphere — Coding Rules

These rules are grounded in patterns already established in the codebase —
each one references where the pattern actually lives, so it can be checked
against real code, not taken on faith. Claude Code (and any contributor)
must follow these throughout the project.

---

## 1. General Development

- **Inspect before modifying.** Before touching a feature, read its
  `domain/`, `data/`, and `presentation/` files in full, and check whether
  both a `demo_*_repository.dart` and `api_*_repository.dart` exist —
  changing one without the other silently breaks the pairing (see
  Architecture.md §3, "the dual demo/api repository pattern").
- **Do not rewrite working code unnecessarily.** This codebase has a strong
  existing convention for nearly everything (form validation, RBAC
  dependencies, Pydantic schema shape, migration naming) — follow it rather
  than introducing a competing pattern for the same problem.
- **Follow existing architecture.** No router package, no state-management
  package, no ORM other than SQLAlchemy async, no identity system other
  than Firebase Auth. Don't add one to solve a single screen's problem —
  see Architecture.md §8 for why each of these is a deliberate constraint,
  not an oversight.
- **Avoid duplicate functionality.** Before adding a service/helper, check
  `app/services/` (backend) or the relevant `domain/` folder (frontend) for
  something that already does it — e.g. `app/services/parsing.py`'s
  `sanitize_html`/`utc_now`/hashing helpers are imported almost everywhere;
  don't reimplement HTML sanitization or timestamp handling locally.
- **Prefer reusable code.** The shared form-validation components in
  `lib/app/design/form_validation_styles.dart` (`RequiredFieldsLegend`,
  `characterCounterBuilder`, `AnimatedRequirementRow`,
  `RequirementProgress`, `SubmitBlockedHint`) exist specifically so every
  form looks and behaves the same — use them rather than rebuilding a
  one-off validation UI.

## 2. Code Structure

- **Separation of concerns:** `domain/` (models, interfaces) never imports
  from `data/` or `presentation/`; `data/` implements `domain/` interfaces;
  `presentation/` depends on `domain/` interfaces, not concrete `data/`
  classes, so a repository can be swapped in `app.dart` without touching
  screens.
- **Small, focused components/functions.** Backend routes stay thin —
  business logic lives in `app/services/`, not inline in route handlers
  (see how `external_opportunities.py` delegates to `opportunity_import.py`,
  `evidence.py`, etc.).
- **Reusable services, not copy-pasted logic.** One service module per
  concern on the backend (22 files in `app/services/`); one shared
  component per validation pattern on the frontend.
- **Consistent naming:** backend route files, model files, and schema files
  share the same base name per domain (`providers.py` route ↔
  `provider.py` model ↔ `provider.py` schema); Alembic revisions are named
  `<date>_<sequence>_<domain>.py`; Flutter repository pairs are always
  `demo_<feature>_repository.dart` / `api_<feature>_repository.dart`.

## 3. Frontend Rules

- **Reusable components** over one-off widgets, especially for form
  validation (§1 above).
- **Responsive design:** verify any new screen at 375px/768px/1024px/1440px
  before considering it done; follow the auth screen's wide/narrow split
  pattern (`_wideBreakpoint`) for screens with a decorative side panel.
- **Accessibility is not optional:** every custom animation must check
  `MediaQuery.of(context).disableAnimations`; every icon-only control needs
  a `tooltip`/`Semantics` label; status must never be color-only (pair with
  an icon or text label — this is an explicit anti-pattern in
  `design-system/scholarsphere/MASTER.md`).
- **Loading states:** use `FutureBuilder`'s `ConnectionState.waiting` (or
  equivalent) — never render a screen assuming data has already arrived.
- **Error states:** show a specific, human-readable message near the
  problem (form fields use inline `errorText`; page-level failures show a
  retry action, per `applicant_profile_screen.dart`'s error-state pattern).
- **Empty states:** show a helpful message + next action, not a blank
  screen (e.g. `_documentField()`'s "No document uploaded yet" +
  Upload button).
- **Form validation UX** (established across auth, provider-registration,
  and applicant-profile forms — follow this pattern for any new form):
  - Required fields get a trailing `*` in the label plus a
    `RequiredFieldsLegend` caption.
  - Validate on **blur** (`FocusNode` listener), not on every keystroke —
    don't show "Required" while someone is still typing their first
    character.
  - Submit/save buttons stay disabled (`onPressed: null`) until the form is
    fully valid, with a `SubmitBlockedHint` explaining what's missing.
  - Fields with a real backend length limit get `maxLength` +
    `characterCounterBuilder` — only add a `maxLength` that matches an
    actual backend `Field(max_length=...)` constraint (Database.md §4);
    never invent a limit.
  - Phone-like free-text fields normalize on blur (strip
    formatting/whitespace to a consistent value) rather than rejecting
    reasonable input formats.

## 4. Backend Rules

- **Input validation:** every mutating endpoint takes a narrow,
  purpose-built Pydantic schema — never accept "the whole ORM row." Bound
  every string field's length; require HTTPS on any URL field
  (`https_urls_only` validator pattern in `app/schemas/`).
- **Authentication:** every protected route depends on `get_current_user`
  (`app/core/auth.py`) — never trust a client-supplied `user_id`/`role`
  field for an authorization decision.
- **Authorization:** use `require_roles(...)`/`require_permissions(...)`
  (`app/core/rbac.py`) as a route dependency — don't hand-roll a role check
  inline in a handler.
- **Proper HTTP status codes:** `409` for a state-machine violation (e.g.
  approving without all checklist items, publishing before verification);
  `403` for an authorization failure; `404` — not `403` — when a resource
  doesn't exist or isn't owned by the caller (avoids leaking existence).
- **Consistent API responses:** errors return the uniform envelope from
  `app/core/errors.py` (a correlation ID + generic message, never a stack
  trace or the real exception message to the client).
- **Error handling:** log the real exception server-side; return only a
  generic message client-side. Never let a caught exception's `str()` reach
  a response body.
- **Secure data access:** every write that changes state in the
  verification/audit pipeline must be diffed into
  `VerificationHistory`/`ImportAuditLog` with a mandatory reason — don't
  add a silent mutation path.
- **External calls:** go through `app/core/http_client.py` (enforces
  HTTPS-only, timeout, response-size cap, bounded retry/backoff) — never
  call `httpx`/`requests` directly against an external host.
- **Sanitize untrusted content:** any HTML from an external source or a
  human edit goes through `app/services/parsing.py::sanitize_html` before
  storage — this applies to both automated import **and** officer edits
  (the 2026-08-17 audit found and fixed a case where only the import path
  sanitized).

## 5. Database Rules

- **Avoid duplicate data:** check Database.md §2 before adding a new table
  — e.g. `opportunity_sources` (7-source ingestion allowlist) and
  `source_registry_entries` (general trust registry) look similar but are
  intentionally distinct; don't collapse them without understanding why
  they're separate.
- **Validate relationships:** declare FK `ondelete` behavior deliberately
  (`CASCADE`/`RESTRICT`/`SET NULL`) based on the real business rule, not a
  default — see Database.md §3/§4 for the reasoning behind each existing
  choice.
- **Maintain data integrity:** add a unique constraint wherever "one X per
  Y" is a real rule (see the existing list in Database.md §4) rather than
  relying on application-level checking alone — the provider
  duplicate-domain fix specifically closed a race condition that an
  app-level-only check left open.
- **Avoid destructive changes:** never write an Alembic migration that
  drops a column/table without a reviewed, reversible downgrade path. Never
  downgrade a production database without a reviewed backup and change
  plan (`scholarsphere_backend/README.md`).
- **Append-only tables stay append-only:** `ImportAuditLog`,
  `VerificationHistory`, `audit_records` must never get an update/delete
  service — this is enforced by convention (no such route exists), keep it
  that way.

## 6. Security Rules

- **Never hardcode secrets.** No `.env` files, service-account JSON, or API
  keys committed anywhere — verified by repository-wide search as of the
  last audit; keep it that way. Use `pydantic.SecretStr` for any new
  backend secret so it can't leak via `repr()`/logs.
- **Use environment variables**, documented by name only in `.env.example`
  files — never populate an example file with a real value.
- **Never expose sensitive data:** error responses never include a stack
  trace or internal exception message; API docs (`/docs`/`/redoc`) are
  disabled whenever `APP_ENV=production`.
- **Validate user input** at the schema boundary, not deep in business
  logic — reject early with a clear Pydantic validation error.
- **Enforce access control** server-side, always — client-side role checks
  (`AccessControlPolicy` in Flutter) are UI-routing convenience only and
  must never be treated as the real authorization boundary once a
  repository is backend-connected (this exact mistake is called out as a
  landmine in `docs/PRODUCTION_SECURITY_AUDIT.md` §2.2).
- **New file-upload features** must scope their own Storage rules
  (owner-write, size/type capped) rather than widening the existing
  `provider-documents/`/`applicant-documents/` rules — see Architecture.md
  §8, decision 8.

## 7. Testing Rules

- **Test new functionality.** Every backend route file has a matching
  `tests/test_<route>_route.py` — follow that convention for any new route.
  Every frontend feature area has at least one corresponding test file
  under `test/`.
- **Test error cases**, not just the happy path — e.g. the existing
  verification tests assert `409` on an incomplete checklist, not just
  `200` on a complete one.
- **Do not claim tests passed unless actually run.** Run `pytest -q`
  (backend) and `flutter test` (frontend) yourself and report the real
  pass/fail counts — don't infer success from the code looking correct.
  Run `flutter analyze` and `dart format --output=none
  --set-exit-if-changed lib test` before considering frontend work done;
  these are also what CI checks (`.github/workflows/ci.yml`).
- **Widget tests needing Firebase** must inject a `DemoAuthRepository` (and
  demo/API overrides as needed) via `ScholarSphereApp`'s optional
  constructor parameters — constructing a real `FirebaseAuthRepository()`
  in a widget test throws `[core/no-app]` since `flutter test` never calls
  `Firebase.initializeApp()`.

## 8. Git Rules

- **Keep changes focused.** One feature/fix per commit where practical;
  avoid bundling unrelated backend and frontend changes in the same commit
  unless they're genuinely one change (e.g. wiring a new `api_*_repository`
  to its matching new route).
- **Avoid unrelated modifications.** Don't reformat or "clean up" files
  outside the scope of the current task.
- **Update Changelog.md** whenever a meaningful change lands — new feature,
  bug fix, security fix, schema change, or major UI change. See
  Changelog.md's own format.
- **This project may have concurrent sessions.** More than one Claude Code
  session can be working on this repository at once (observed directly
  during this documentation pass). Run `git status`/`git diff` before
  assuming the working tree matches what you last touched, and never
  overwrite a file you haven't just read, even if you're confident you
  wrote it.

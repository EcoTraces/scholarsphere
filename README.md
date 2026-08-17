# ScholarSphere

ScholarSphere is a global platform for finding and getting notified about
opportunities. It's built for students, graduates, researchers,
entrepreneurs, and young professionals looking for verified scholarships,
fellowships, internships, webinars, summits, conferences, grants, and
training programs.

The platform pulls opportunities from recognized universities, governments,
international organizations, foundations, and sponsors, then checks each
listing against its official source. From there it evaluates who's likely
eligible, recommends opportunities that fit, tracks application progress,
and sends personalized deadline notifications.

ScholarSphere gives guidance and verified information, but it doesn't
guarantee admission, funding, selection, visas, or travel approval.
Applicants should always confirm current requirements on the official
application website.

## Implemented modules

### Authentication and user management

- Firebase email/password and Google authentication
- Applicant-only self-registration with Firebase email verification
- Password reset and persisted Firebase session restoration
- Firestore-backed user roles, status, and notification preferences
- Administrator-created managed accounts through callable Cloud Functions
- Server-issued custom role claims and account suspension with token revocation
- Role-aware session routing and sign-out

Firestore handles account persistence. Deploying the managed-account Cloud
Functions requires the Firebase project to be on the Blaze plan. See
`docs/firebase_authentication.md` for deployment and bootstrap instructions.

### Opportunity discovery

The first vertical slice includes:

- A responsive Material 3 application shell
- Opportunity domain and repository contracts
- Demo data behind a replaceable repository
- Search, type filters, and a verified-only filter
- Opportunity cards and a detail view
- A widget test for the main discovery flow

### Applicant profiles

- Private personal, education, employment, readiness, and preference data
- English-test, passport, employment, and funding status
- Optional special-eligibility categories
- Private document metadata with an upload-service integration boundary
- In-memory persistence through a replaceable profile repository

### Opportunity management

- Complete opportunity records covering institution, eligibility, dates,
  official links, fees, language, age, experience, contact, and positions
- Provider submission workspace
- Mandatory pending-verification state for every provider submission
- Public repository queries return only verified records

### Verification and trust

- Officer-only verification queue and review workspace
- Official-source authority classification
- Mandatory source, sponsor, link, deadline, requirements, and duplicate checks
- Audited review decision, officer, evidence notes, and review date
- Verified approval blocked for third-party sources or incomplete checklists
- Scheduled 90-day rechecks and automatic verification-expired handling

### Eligibility matching

- Deterministic rule-based scoring with no machine-learning dependency
- Nationality, level, field, age, experience, language, fee, and funding rules
- Separate matched, missing, and uncertain explanations
- Applicant-specific match panel on every opportunity detail screen

### Search and filtering

- Structured filtering across every opportunity requirement
- Country and geographic-region classification
- Canada maps to North America, and also gets its own popular filter
- Deadline, open/closed, fee, verification, age, experience, and language rules

### Recommendations

- Profile and eligibility-based ranking with explainable reasons
- Search-history, saved-opportunity, application-history, and deadline signals
- Best match, new, funded, fee-free, closing, country, degree, online,
  no-IELTS, and study-level categories

### Notifications and deadlines

- In-app notification center with read state
- Email, push, SMS, and WhatsApp delivery-channel preferences
- Immediate, daily, weekly, and disabled frequencies
- 30, 14, 7, 3, and 1-day deadline schedules
- Event entry points for matches, changes, verification, and saved expiry

External delivery channels need backend workers and configured providers to
actually send anything.

### Application tracking

- Saved opportunities create private applicant records
- All ten application stages and requested dates, references, notes, values,
  missing documents, and follow-up actions
- Saved and application navigation is connected to the discovery shell
- Tracker history feeds recommendation signals

### Document readiness

- Standardized checklist for all thirteen document categories
- Opportunity-specific readiness and missing-document calculation
- Private document vault with encryption enforcement and owner access
- Provider access requires an explicit per-document consent grant

### Opportunity collection

- Provenance ledger for manual, provider, API, RSS, feed, web, and user sources
- Automated intake restricted to administrator-approved sources
- Every collected record is forced into pending verification
- Collected records cannot appear in public discovery before verification

### Fraud and scam detection

- Evidence-based automated risk assessment with typed, weighted signals
- Personal-payment, unofficial-domain, guarantee, credential, deadline,
  impersonation, shortened-link, benefit, sponsor, and duplicate-link rules
- Applicant safety guidance and verification-officer review warnings
- Official-domain checks for known institutions and registrable-domain
  comparison for application links
- Neutral caution wording explicitly avoids unsupported fraud accusations

### Administration dashboard

- Live opportunity, verification, user, provider, application, deadline, and
  notification statistics
- Opportunity view tracking and ranked country and field interest
- Responsive administrator-only dashboard with collection access

### Reporting and analytics

- Country, continent, study-level, and funding distributions
- Application conversion and outcome reports
- Applicant field-interest and successful-provider reports
- Verification activity and expired-opportunity reports
- Notification delivery and engagement reporting

### Security and access control

- Role and permission authorization for all eight security roles
- Privileged-role MFA and short-lived administrative sessions
- Session expiration, revocation, device tracking, and login history
- New-device and suspicious-login alerts
- Five-attempt lockout, IP-keyed rate limiting, and emergency suspension
- Strong registration-password validation and critical-action reauthentication
  policy
- Backend contracts for Argon2id/bcrypt, password history, CAPTCHA, IP
  blocking, HTTPS enforcement, and managed secret storage

The in-memory demo credentials are development fixtures, not production
password storage. Production authentication needs to implement the password
security gateway using Argon2id or bcrypt on the backend. API rate limits,
CAPTCHA verification, TLS termination, and secret rotation also need to run
server-side. Security-question recovery was left out on purpose — it's
weaker than verified-email recovery and MFA.

### Privacy and data protection

- Versioned legal, cookie, marketing, notification, recommendation,
  sensitive-data, document, and third-party consent records
- Optional-consent withdrawal and required-consent protection
- Structured user-data export
- Correction, document deletion, and account deletion requests
- Organization access history backed by explicit sharing consent
- Minor restrictions for marketing, behavioral recommendations, and sharing
- Retention, anonymization, pseudonymization, and incident-recording contracts
- Personalized recommendations are disabled when consent is not active
- Provider document access requires both sharing consent and a document grant

Run it with:

```sh
flutter run -d chrome
```

Run checks with:

```sh
flutter analyze
flutter test
```

## Delivery roadmap

1. Foundation and opportunity discovery
2. Authentication, roles, and applicant profiles
3. Provider opportunity submission and administration
4. Verification workflow and trust signals
5. Eligibility rules and explainable matching
6. Saved opportunities and application tracking
7. Document readiness
8. Notifications and deadline jobs
9. Collection, fraud signals, reporting, and analytics

The production system will also need a backend API and PostgreSQL. Firebase
Authentication and Cloud Messaging can stay focused on identity and push
delivery. Verification, matching, scheduled work, and authorization belong
on the backend.

## External opportunity backend

The production FastAPI/PostgreSQL integration for Grants.gov,
Simpler.Grants.gov, and European Commission Funding & Tenders is documented in
[scholarsphere_backend/README.md](scholarsphere_backend/README.md). It includes
environment setup, migrations, API examples, Celery/Redis operation, Docker,
verification/publication controls, source mappings, testing, troubleshooting,
and known coverage limitations.

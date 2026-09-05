# ScholarSphere — Design System

**Last verified against the codebase:** 2026-08-21. The tokens below are
sourced from `lib/app/theme.dart` (`buildScholarSphereTheme`) and
`lib/app/design/form_validation_styles.dart` — real code, not a generated
palette. A machine-maintained companion file with deeper reasoning/motion
detail lives at `design-system/scholarsphere/MASTER.md` (kept up to date by
the `ui-ux-pro-max` skill); this document is the human-facing summary and
the two should not drift — if you change a token, update both.

---

## 1. Design Principles

1. **Accessible & Ethical** — the deliberate style classification for this
   product category (government/education/public-interest, not a consumer
   marketplace): high contrast, large text, keyboard navigation, visible
   focus, screen-reader friendly.
2. **Never mislead.** Deadlines and eligibility are surfaced up front, never
   buried — this is a domain-specific anti-pattern check, not generic
   advice (a scholarship platform that hides a deadline is actively harmful).
3. **Status is never color-only.** Approved/rejected/pending/deadline-soon
   always pairs color with an icon or label.
4. **Consistent.** One icon set, one radius token (12px), one type family,
   one spacing rhythm — extend the existing scale, don't invent a parallel
   one.
5. **Responsive and reduced-motion aware.** Every animation checks
   `MediaQuery.of(context).disableAnimations` and jumps straight to the end
   state when set.

---

## 2. Design System Tokens

### Colors — pinned to `lib/app/theme.dart`, do not introduce a parallel palette

| Role | Hex | Source |
|---|---|---|
| Primary (teal) | `#007C72` | seed color, `scheme.primary` |
| Secondary (amber) | `#E09F3E` | `scheme.secondary` |
| Ink (headings) | `#14213D` | `textTheme.headline*` / `titleLarge` |
| Canvas (background) | `#F7F8FA` | `scaffoldBackgroundColor` |
| Body text | `#344054` | `bodyLarge` |
| Muted text | `#596579` | `bodyMedium` |
| Border / divider | `#D8DEE8` / `#E1E6ED` | input & card borders |
| On Primary | `#FFFFFF` | `scheme.onPrimary` |
| Error | Material `scheme.error` (seeded) | form/error borders — always reference the theme token, never a literal red |
| High-contrast primary | `#000000` | `highContrast` variant |
| High-contrast secondary | `#7A3E00` | `highContrast` variant |

**Validation state tokens** (`lib/app/design/form_validation_styles.dart`'s
`ValidationPalette` — added for form UX, reused across every form in the
app):

| Token | Hex | Contrast target |
|---|---|---|
| `success` | `#2E7D32` | ≥4.5:1 on white (WCAG AA, normal text) |
| `warning` | `#B54708` | ≥4.5:1 on white |
| `muted` | `#98A2B3` | caption/hint text |

`error` deliberately reuses `Theme.of(context).colorScheme.error` rather
than a local constant, so it never drifts from the app-wide error color.

### Typography

- Current: system `Arial` for both headings and body (`theme.dart:25`).
- Type ramp (extend, don't replace): `headlineLarge` 32px/700,
  `headlineSmall` 22px/700, `titleLarge` 18px/700, `bodyLarge` default/1.45
  line-height, `bodyMedium` default/1.4 line-height.
- Minimum 16px body text (avoids iOS auto-zoom on web, meets the
  Accessible & Ethical baseline).
- **Flagged option, not adopted:** a formal serif+humanist-sans pairing
  (e.g. EB Garamond / Lato) matches this style category better than a
  system font, per the design-system generator's reasoning — this is a
  deliberate future decision with app-size/licensing implications, not
  bundled into any single page's redesign.

### Spacing — 4/8dp rhythm

| Token | Value | Usage |
|---|---|---|
| `space-xs` | 4dp | icon-to-label gaps |
| `space-sm` | 8dp | inline spacing, chip gaps |
| `space-md` | 16dp | standard padding (matches `contentPadding` horizontal) |
| `space-lg` | 24dp | section padding |
| `space-xl` | 32dp | large gaps between page sections |
| `space-2xl` | 48dp | section margins on wide/tablet layout |

### Radius & Elevation

- One radius token everywhere: **12px** (inputs, cards, buttons). Never mix
  radii between components.
- Cards are flat: `elevation: 0` + 1px border, not a drop shadow
  (`cardTheme` in `theme.dart`). Reserve real Material elevation for
  transient surfaces only — modals, menus, snackbars.

### Icons

Single consistent set: Material Icons (`Icons.*`), used directly (no icon
package dependency). No emojis as structural icons anywhere in the codebase.

---

## 3. Responsive Design

- Breakpoints in active use: the auth screen's explicit wide/narrow split at
  `900px` (`_wideBreakpoint`, `auth_screen.dart`). General guidance from the
  design-system reference: verify at 375px / 768px / 1024px / 1440px, no
  horizontal scroll at any of them.
- Wide layouts use `Row`/`Expanded` with a two-pane split (e.g. the auth
  screen's form pane + decorative side panel); narrow layouts stack
  vertically and center content within a `ConstrainedBox(maxWidth: 440–820)`.
- Provider/applicant forms cap content width (e.g. `maxWidth: 720` for the
  provider registration form, `maxWidth: 820` for the applicant profile) so
  long-form text stays readable on wide screens instead of stretching
  edge-to-edge.

---

## 4. Accessibility

- **Semantic structure:** `Semantics` widgets used explicitly where a custom
  widget needs a role/label the default widget tree wouldn't infer (e.g.
  `_buildModeTab` in `auth_screen.dart` marks itself `button: true,
  selected: ...`).
- **Keyboard navigation / focus:** visible focus rings via
  `focusedBorder` in `inputDecorationTheme` (`scheme.primary`, 1.6px);
  `FocusNode`s wired explicitly on form fields for blur-triggered inline
  validation (see Coding_Rules.md's form-validation conventions).
- **Color contrast:** every token above chosen for ≥4.5:1 against its
  expected background; verify light mode **and** the app's existing
  `highContrast` theme variant independently — don't assume one implies
  the other.
- **Screen readers:** live-region error banners
  (`Semantics(liveRegion: true)`) so errors are announced as they appear,
  not only when a user tabs to them.
- **Reduced motion:** every custom animation
  (`AnimatedSwitcher`/`AnimatedSize`/`TweenAnimationBuilder` in
  `form_validation_styles.dart`) checks
  `MediaQuery.of(context).disableAnimations` and collapses its duration to
  zero when set.
- **Locale/RTL/text scale:** `ExperiencePreferences`
  (`lib/features/experience/domain/experience_preferences.dart`) feeds
  `highContrast`, `textScale`, and `Directionality` (RTL) into
  `MaterialApp.builder` — these are real, wired settings, not aspirational.

---

## 5. UI Components (reusable)

### Shared form-validation components (`lib/app/design/form_validation_styles.dart`)

| Component | Purpose |
|---|---|
| `RequiredFieldsLegend` | "Fields marked * are required" caption, used identically on every form with required fields |
| `characterCounterBuilder` | Drop-in `buildCounter` — plain-language "N characters left," color escalates muted → warning → error as a length limit approaches |
| `AnimatedRequirementRow` | One live-validated requirement (e.g. a password rule) — icon/color crossfade between unmet/met, 180ms, reduced-motion aware |
| `RequirementProgress` | "N of M met" summary bar above a requirement checklist, animated fill via `TweenAnimationBuilder` |
| `SubmitBlockedHint` | Caption under a disabled submit button explaining what's still missing, `AnimatedSize` reveal |

### App-theme components (`lib/app/theme.dart`)

Standard Material 3 widgets themed centrally, not per-screen: `TextFormField`
(filled, 12px radius, `#D8DEE8` border), `Card` (flat, bordered), `FilledButton`
(12px radius, bold 15px label), `OutlinedButton` (matching radius/border).

### Pattern: required-field asterisk + inline blur validation

Established across the auth, provider-registration, and applicant-profile
forms: required fields get a trailing `*` in the label; a field-level
`FocusNode` triggers validation display **on blur**, not on every keystroke
(`inline-validation` UX rule); the submit button stays disabled until the
form is fully valid, with a `SubmitBlockedHint` explaining why.

---

## 6. Page / Screen Inventory

Grouped by role — the full mapping (role → dashboard file) lives in
Architecture.md §3 / PRD.md §2. Representative screens per area:

| Area | Key screens |
|---|---|
| Authentication | `AuthScreen` (sign in / register, wide+narrow layouts) |
| Applicant | `ApplicantDashboardScreen`, `DiscoverScreen`, `OpportunityDetailScreen`, `ApplicantProfileScreen`, `ApplicationTrackerScreen`, `CalendarScreen`, `NotificationCenterScreen`, `ApplicationGuidanceScreen` |
| Provider | `ProviderAccountScreen` (registration + status), `ProviderOpportunityScreen`, `ProviderAnalyticsScreen` |
| Verification Officer | `VerificationOfficerDashboardScreen`, `LiveVerificationQueueScreen`, `VerificationQueueScreen` (demo) |
| Moderator | `ModeratorDashboardScreen`, `ModerationQueueScreen`, `ReportContentScreen` |
| Support Officer | `SupportAgentScreen`, `HelpCentreScreen` |
| Security Administrator | `SecurityAdministratorDashboardScreen`, `SecurityPrivacyCenterScreen` |
| Administrator / Super Administrator | `AdministrationDashboardScreen`, `OperationsConsoleScreen`, `AuditLogScreen`, `DataGovernanceScreen`, `SourceRegistryScreen`, `RecommendationControlsScreen` |
| Premium (2026-09-01) | `PremiumLandingScreen` (pricing/checkout/status) — implemented. `PremiumFeatureGate` (reusable locked-feature card, real components from SS5, not a generic AI-dashboard look). **Not yet built**: CV/SOP/study-plan/research-proposal/fellowship builder screens, ATS analyzer, requirement matcher, checklist, billing history, admin premium dashboard — all have real, tested backend routes already (PRD.md §3.1a) waiting on their presentation layer. |

Premium-specific design notes, following the same principles as SS1
rather than a competing style: pricing/feature lists always render the
plan's *real* price and feature list from the backend (never a hardcoded
"$100" in a widget); a locked feature shows `PremiumFeatureGate`'s
lock icon + "Premium Feature" label + "Unlock Premium" button (status is
never color-only, per SS4); an ATS score is always shown with its
disclaimer text visible, never just a bare number implying a guarantee; a
checkout failure/not-configured state is shown as specific, actionable
text (matching SS1's existing error-state convention), never a generic
"something went wrong."

---

## 7. Design System Tooling

`ui-ux-pro-max` (Claude Code skill, installed 2026-08-12, updated to v2.15.0
2026-08-18) is the design-intelligence tool used for this project. Its
persisted output lives at `design-system/scholarsphere/MASTER.md` and
includes deeper motion/anti-pattern/role-specific guidance than this
summary. **When building or reviewing a specific page**, check for a
page-level override at `design-system/scholarsphere/pages/<page>.md` first;
if none exists, follow `MASTER.md`, which in turn defers to the real tokens
in this file and `theme.dart`. Do not let generated components introduce a
new color, radius, or type family outside what's documented here.

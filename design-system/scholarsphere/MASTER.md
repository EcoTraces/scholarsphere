# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/scholarsphere/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.
>
> **Source of truth for color/type/shape is the existing codebase**, not a generated palette:
> `lib/app/theme.dart` (`buildScholarSphereTheme`) and `assets/branding/`. This file adapts
> the UI/UX Pro Max reasoning engine's pattern/style/motion/a11y intelligence to that existing
> identity — it does not replace it.

---

**Project:** ScholarSphere
**Generated:** 2026-08-17 (ui-ux-pro-max v2.15.0, query: "scholarship grant funding opportunity discovery application tracking platform")
**Category:** Grant / Funding Portal (closest catalog match to a scholarship/opportunity marketplace)
**Stack:** Flutter (Material 3), `flutter` stack domain in this skill
**Design Dials:** Motion 4/10 (Standard) | Density 6/10 (Standard)
**Roles:** Applicant, Opportunity Provider, Verification Officer, Administrator, Super Administrator, Security Officer

---

## Global Rules

### Color Palette — pinned to `lib/app/theme.dart`

Do not introduce a new palette. Every surface uses these tokens (or Flutter's derived
`ColorScheme` roles seeded from them via `ColorScheme.fromSeed`). If a new semantic role is
needed (e.g. a status color for "under review"), derive it from this set and add it to
`theme.dart` as a token — never hardcode a one-off hex in a widget.

| Role | Hex | Source |
|------|-----|--------|
| Primary (teal) | `#007C72` | seed color + `scheme.primary` |
| Secondary (amber) | `#E09F3E` | `scheme.secondary` |
| Ink (headings) | `#14213D` | `textTheme.headline*/titleLarge` |
| Canvas (background) | `#F7F8FA` | `scaffoldBackgroundColor` |
| Body text | `#344054` | `bodyLarge` |
| Muted text | `#596579` | `bodyMedium` |
| Border / divider | `#D8DEE8` / `#E1E6ED` | input & card borders |
| On Primary | `#FFFFFF` | `scheme.onPrimary` |
| Error | Material `scheme.error` (from seed) | form/error borders |
| High-contrast mode primary | `#000000` (black) | `highContrast` variant |
| High-contrast mode secondary | `#7A3E00` | `highContrast` variant |

**Status colors (new, needed for opportunity/application state — not yet in `theme.dart`):**
Derive from the existing hue families rather than stock red/green/amber:
- Success / Approved → deepen the existing teal (`#0E6B5C` range) rather than a generic green
- Warning / Deadline soon → the existing amber `#E09F3E`
- Danger / Rejected / destructive → Material's seeded `scheme.error`, kept separate from amber so "deadline" and "rejected" are never confusable (`color-not-only` — pair with an icon/label, never color alone)

**Reasoning kept from the generator:** institution-navy + funding-green + deadline-urgency is the
right *shape* for this category (authority color + go/success color + urgency color) — ScholarSphere's
navy/teal/amber already satisfies that shape, so the generated `#1E3A5F`/`#16A34A` swap is unnecessary.

### Typography — pinned to current implementation, with a flagged option

- **Current:** `Arial` system font for both headings and body (`theme.dart:25`).
- **Skill's reasoning-engine match:** the "Accessible & Ethical" style (see below) pairs with a
  formal/trustworthy serif+humanist-sans combo (e.g. EB Garamond / Lato) for government/education
  products. That is a *available upgrade*, not a requirement — swapping the app's system font
  for a webfont is a cross-cutting change with app-size and licensing implications, so treat it as
  a separate decision, not something bundled into any single-page redesign.
- **Do not** introduce a third typeface anywhere (e.g. a "friendly" display font on a marketing
  page) — one type family (or the approved pair, if adopted) across all six roles.
- Base size 16px minimum for body text; existing scale (32/22/18 for headline/headline-small/title)
  stays as the type ramp — extend it, don't invent a parallel one.

### Spacing — Flutter 4/8dp rhythm (Density 6/10, Standard)

| Token | Value | Usage |
|-------|-------|-------|
| `space-xs` | 4dp | icon-to-label gaps |
| `space-sm` | 8dp | inline spacing, chip gaps |
| `space-md` | 16dp | standard padding (matches existing `contentPadding` horizontal) |
| `space-lg` | 24dp | section padding |
| `space-xl` | 32dp | large gaps between page sections |
| `space-2xl` | 48dp | section margins on wide/tablet layout |

Existing corner radius is consistently `12px` (inputs, cards, buttons) — keep this as the one
radius token; do not mix radii between components.

### Elevation

Current app uses **flat cards** (`elevation: 0` + `1px` border, not shadow) — this matches the
"Accessible & Ethical" style's low-decoration bias. Keep using border-based separation instead of
drop shadows for cards/list rows; reserve real elevation (Material shadow) for transient surfaces
only — modals, menus, snackbars.

---

## Style Guidelines

**Style match:** Accessible & Ethical — *(from `ui-ux-pro-max --design-system`, confirmed as the
correct fit: ScholarSphere is a public-interest education/funding product, not a consumer
marketplace.)*

**Keywords:** accessible, inclusive interface, high contrast, large text (16px+), keyboard
navigation, screen-reader friendly, visible focus state, semantic structure.

**Best For (from catalog):** Government, healthcare, education, inclusive products, large
audience, legal compliance, public — all directly applicable to a scholarship/funding platform
serving applicants, institutions, and compliance/verification staff.

**Key effects to apply everywhere:** clear focus rings (3–4px, `scheme.primary`), ARIA/semantics
labels on all icon-only controls, skip-to-content on web builds, reduced-motion support, 44×44
(iOS-equivalent) / 48×48dp minimum touch targets.

### Page Pattern — adapted from "Marketplace / Directory"

The generator's raw pattern used generic marketplace language ("List your item", "Become a
host/seller"). Adapted to ScholarSphere's actual two-sided model (Applicants discover
opportunities; Providers publish them):

- **Conversion focus:** Search/filter is the primary action on discovery surfaces. Minimize
  friction with smart defaults (recent search, suggested categories) before the user types.
- **Primary CTA placement:** Hero search/filter bar on Discovery; a persistent "Post an
  Opportunity" action in the Provider nav (not a marketing CTA — it's a role-scoped nav item).
- **Section order (Discovery):** Search/Filter bar → Category/Type chips → Featured or
  Deadline-soonest opportunities → Saved/Recommended → (Provider-facing) "Publish an opportunity"
  entry point.
- **Carousels/featured-listing rotators**, if used: previous/next controls, full keyboard access,
  pause on hover/focus/reduced-motion, and never as the *only* path to an opportunity (always
  reachable via search too).

---

## Motion

**Stagger List** (Standard tier) — list/grid entrances only (opportunity cards, table rows on
first load), trigger on load or scroll:

```dart
// Flutter equivalent of the GSAP stagger reasoning: implicit per-item entrance,
// not a literal GSAP dependency. Use AnimatedList / staggered fade+slide via
// flutter_staggered_animations or a manual Interval-based stagger.
// Duration: 300-450ms per item reveal, easing: Curves.easeOutBack (bounce-out
// analogue of GSAP's back.out(1.4)).
```

- ✅ Use for opportunity grids/lists on first paint.
- ❌ Do not use bouncy/overshoot easing (`back.out` / `Curves.easeOutBack`) on **dense data
  tables** (Verification Officer queues, Admin tables) — reads as sloppy on informational UI; use
  a plain fade+`easeOut` there instead.
- Always gate motion behind the platform's reduced-motion signal
  (`MediaQuery.of(context).disableAnimations`) — skip straight to end-state when set.

---

## Anti-Patterns (Do NOT Use)

**Domain-specific (from the Grant/Funding Portal category match — directly relevant to a
scholarship platform):**
- ❌ No visible deadline — every opportunity card/detail must surface its deadline date, not bury
  it in a detail-page scroll.
- ❌ No eligibility clarity — eligibility criteria must be scannable up front, not buried in a PDF
  or long paragraph.
- ❌ Buried application documents/requirements — required docs listed before the applicant starts,
  not discovered mid-flow.

**General (from Quick Reference, still binding):**
- ❌ Emojis as icons — use a single consistent icon set (Material Symbols/Icons in Flutter).
- ❌ Missing pointer/press feedback on tappable rows and cards.
- ❌ Layout-shifting hover/press states — animate opacity/elevation/color, not size, on press.
- ❌ Text contrast below 4.5:1 — verify independently for light and (future) dark/high-contrast
  mode; don't assume the light-mode value carries over.
- ❌ Instant, unanimated state changes for anything async (loading, submit, filter apply).
- ❌ Invisible focus states — required for the web build's keyboard users.
- ❌ Color-only status signaling — "approved/rejected/pending/deadline-soon" must pair color with
  an icon or label, especially since this app already ships a `highContrast` theme variant.

---

## Role-Specific Notes

Six roles share this one Master file; page-level overrides belong in
`design-system/scholarsphere/pages/<page>.md`, not forked copies of this file.

- **Applicant** — Discovery, Opportunity Details, Application forms, Notifications, Profile.
  Optimize for scannability and momentum (deadline/eligibility up front, clear multi-step
  progress in applications, autosave on long forms).
- **Opportunity Provider** — Posting/managing opportunities, applicant tables, review queues.
  Dense, tabular, low-motion; sortable tables with `aria-sort`, bulk actions need confirmation +
  undo.
- **Verification Officer** — Queue-driven review UI; treat like Provider tables (dense, low
  motion) but with explicit state badges (pending/verified/rejected) that never rely on color
  alone.
- **Administrator / Super Administrator** — Dashboards and system-wide tables. Density 8–9 range
  (denser than the 6/10 default here) is appropriate for these two roles specifically — re-run a
  page-level query with `--density 8` if a dedicated admin page file is created.
- **Security Officer** — Audit/log-style surfaces: monospaced/tabular figures for
  IDs/timestamps (`number-tabular` rule), minimal motion, high information density.

---

## Pre-Delivery Checklist

Before delivering any UI change on any of the surfaces above, verify:

- [ ] No emojis used as icons (single consistent icon set)
- [ ] `cursor-pointer`-equivalent affordance on web build for all clickable elements
- [ ] Hover/press states use smooth transitions (150–300ms), never instant
- [ ] Light mode **and** the app's existing high-contrast mode both hit 4.5:1 text contrast
- [ ] Focus states visible for keyboard navigation (web build)
- [ ] Reduced-motion signal respected (`disableAnimations`)
- [ ] Responsive at 375px, 768px, 1024px, 1440px — no horizontal scroll
- [ ] No content hidden behind fixed nav/app bars
- [ ] Deadline and eligibility are visible without extra taps/scroll (domain anti-pattern)
- [ ] Status/state is never color-only (approved/pending/rejected/deadline-soon)

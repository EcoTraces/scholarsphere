# Changelog

All notable changes to ScholarSphere are recorded here going forward. This
file starts from the project's current state as of 2026-08-21 — the
"Baseline" entry below summarizes what already existed rather than
reconstructing a fictional history; the real commit log
(`git log --oneline`) remains the authoritative historical record for
anything before this file existed.

Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- Root-level documentation set (`PRD.md`, `Architecture.md`, `Design.md`,
  `Database.md`, `Coding_Rules.md`, `Road_map.md`, `Changelog.md`,
  `Task.md`) as the project's central source of truth, built by inspecting
  the actual codebase rather than assumption.

### Changed
—

### Fixed
—

### Removed
—

---

## [2026-09-07] — Five-country autonomous engine: Austria pass — Helmut Veith Stipend added

### Added
- **Helmut Veith Stipend** (TU Wien, via the Vienna Center for Logic
  and Algorithms / VCLA) (`app/services/national_scholarship_
  programs.py::HelmutVeithStipendSource`, source #85 in
  `docs/AUTHORITATIVE_SOURCES.md`) — this platform's 86th registered
  `OpportunitySource`, and its first Austria **university** source
  (the only prior Austria source, OeAD Ernst Mach Grant #28, is
  government-classified).
  - EUR 7,000/year for up to two years plus a full TU Wien tuition-fee
    waiver, for female Master's students in Computer Science. No
    nationality restriction — worldwide eligibility, Sierra Leone
    included. Correctly `partial_funding`: live research on Vienna's
    own documented student cost of living (~EUR 950-1,300/month)
    confirms the stipend covers under half of typical living costs
    even combined with the tuition waiver.
  - Explicitly accepts a not-yet-final degree via a preliminary
    certificate stating the expected graduation date.
  - **Deliberate design choice**: uses the dedicated `vcla.at/
    helmut-veith-stipend/` announcement page rather than TU Wien
    Informatics' general scholarships hub page, which links to it —
    the hub page states a stale "EUR 6,000 p.a." figure for the same
    award, while the dedicated page (fetched live) states the current
    "EUR 7000 annually" and a live 30 November 2026 deadline.
  - **LIVE SOURCE TEST: PASSED 2026-09-07.** Verified through this
    backend's actual HTTP path. Implemented and unit-tested against a
    real fixture (`tests/fixtures/helmut_veith_stipend.html`).

### Changed
- `docs/AUTHORITATIVE_SOURCES.md` and `docs/COUNTRY_PROVIDER_REGISTRY.md`
  — researched and rejected five further Austrian universities this
  same pass:
  - **TU Wien, University of Vienna, University of Graz, JKU Linz,
    University of Innsbruck — general "Merit Scholarship" /
    "Leistungsstipendium"** — all governed by the same
    nationally-mandated Studienförderungsgesetz (StudFG), restricted to
    Austrian/EEA citizens or third-country nationals with 5+ years of
    Austrian residency — `NOT_INTERNATIONAL`, a systemic barrier across
    Austrian public universities rather than a per-university finding.
  - **WU Vienna — Mondi International Scholarships** — a
    nationality-unrestricted programme found via secondary sources, but
    WU's own 2021 announcement explicitly scopes it to "the academic
    years 2021/22 and 2022/23" only, and it is absent from WU's current
    live scholarships page — a discontinued pilot, not integrated as
    if still open.
  - **BOKU** — only the same StudFG merit scholarship and outbound
    exchange grants found; no inbound international scholarship.
  - **JKU Linz — Merit Scholarship for Exchange Students** — funds
    temporary exchange students only, not degree-seeking Master's
    applicants — a different opportunity shape, not a substitute.

### Fixed
—

### Removed
—

---

## [2026-09-07] — Five-country autonomous engine (Austria/Eswatini/Australia/USA/Russia): Eswatini pass — no new source qualified

### Added
—

### Changed
- `docs/AUTHORITATIVE_SOURCES.md` and `docs/COUNTRY_PROVIDER_REGISTRY.md`
  — first country of a simultaneous five-country research pass
  (Austria, Eswatini, Australia, USA, Russia). Researched Eswatini as
  a scholarship *study destination* (distinct from this platform's
  existing Eswatini SLAS source, #18, which is the reverse — outbound
  funding for Eswatini nationals) and found no qualifying source:
  - **University of Eswatini (UNESWA)** — genuinely inaccessible: a
    verbose TLS handshake trace confirms the server's own certificate
    chain is incomplete (missing intermediate CA), not a proxy or
    bot-block issue (plain HTTP to the same host redirects to the
    broken HTTPS URL). Per this project's absolute rule against
    disabling certificate verification, left `VERIFICATION_REQUIRED`
    rather than bypassed.
  - **Southern Africa Nazarene University (SANU)** — its own
    `/scholarship-information/` page explicitly states funding is
    "the student's responsibility," an explicit no-institutional-
    scholarship disclaimer, not an opportunity.
  - **Eswatini Medical Christian University (EMCU)** — its only
    funding link points to the government SLAS portal (#18), already
    covered, not a distinct EMCU-administered scheme.
  - **Limkokwing University (Eswatini campus)** — `limkokwing.net` is
    behind an active Cloudflare managed challenge — `BLOCKED`, not
    circumvented.

  No source added. Per the research brief's own explicit "never invent
  opportunities to make the country look complete" instruction, the
  honest current count for Eswatini as a study destination is zero.

### Fixed
—

### Removed
—

---

## [2026-09-06] — Germany, open-scope follow-up: Heinrich Böll Foundation Scholarship added

### Added
- **Heinrich Böll Foundation ("Tailwind for Talents") Scholarship for
  Graduates and PhD students** (`app/services/national_scholarship_
  programs.py::HeinrichBollScholarshipSource`, source #84 in
  `docs/AUTHORITATIVE_SOURCES.md`) — this platform's 85th registered
  `OpportunitySource`, in response to an open-scope "find another
  scholarship opportunities in germany" request (no degree-level or
  funding-type restriction stated). This registry's second
  Foundation-classified source (Humboldt Research Fellowship, #56, is
  the first) and third Germany source overall, alongside DAAD (#10)
  and the university sources TUM (#59) and Freiburg (#69).
  - Genuinely fully funded for the Federal-Foreign-Office-funded,
    non-EU international-student Master's track: EUR 992/month base
    scholarship, a health-insurance allowance of up to EUR 100/month,
    reimbursement of German tuition fees up to EUR 10,000/year
    (covering the same Baden-Württemberg non-EU-tuition exception
    already documented for DAAD's KAS entry), a EUR 38/month fringe
    benefit, and family/child allowances where applicable — verified
    directly on the foundation's own "Financial support" page.
  - **Country coverage / eligibility**: priority to applicants from
    DAC (OECD Development Assistance Committee) countries who have
    "not yet taken up residence in Germany at the time of their
    application" — Sierra Leone, a DAC-listed Least Developed Country,
    is covered. Genuinely open to *prospective* applicants: the
    certificate of enrollment/admission "may be submitted at a later
    point, but no later than the interview," the opposite of this
    platform's earlier Friedrich-Ebert-Stiftung finding (documented
    under DAAD, #10), which required prior enrollment and was left
    unintegrated. Documented plainly: international applicants must
    separately show German-language proficiency of at least B2/DSH1 —
    a language requirement, not a nationality restriction; it does not
    exclude Sierra Leone.
  - **Deliberate design choice**: `deadline_keywords` overridden to
    `("until",)`, skipping the base class's default `("deadline",
    "closing date")` entirely — the live page's text ("Our next
    application deadlines: Spring 2027: 15 January 2027 until 1 March
    2027...") would otherwise have the substring "deadline" match
    inside "deadlines" first and surface the window-*opening* date (15
    January 2027) rather than the actual closing date. Anchoring on
    "until" instead correctly extracts 1 March 2027.
  - Overview/content page chosen deliberately: `/en/scholarships`, not
    the separate `/en/applying-scholarship` page, which still displays
    an already-passed "Fall 2026" cycle as current — a real
    content-freshness lag confirmed by fetching both pages live on the
    same day.
  - **LIVE SOURCE TEST: PASSED 2026-09-06.** Verified through this
    backend's actual HTTP path — 200, real server-rendered Drupal
    HTML. Implemented and unit-tested against a real fixture, captured
    unmodified from the live fetch
    (`tests/fixtures/heinrich_boll_scholarship.html`).

### Changed
- `docs/AUTHORITATIVE_SOURCES.md` and `docs/COUNTRY_PROVIDER_REGISTRY.md`
  — besides the new source above, researched and rejected five further
  German candidates this same pass:
  - **Friedrich Naumann Foundation for Freedom** and **Rosa Luxemburg
    Foundation** — both explicitly require the applicant to already be
    enrolled at a German university with semesters of study remaining
    — `ALREADY_ENROLLED`, the same pattern already documented for
    Friedrich-Ebert-Stiftung under DAAD (#10).
  - **Hanns Seidel Foundation** — a genuinely prospective-applicant-
    friendly design (admission proof accepted "no later than the
    interview," like Heinrich Böll), but its application process is
    explicitly routed through country-specific national HSF offices
    (India, Pakistan, Vietnam, Myanmar, Jordan, and others found live)
    with none found covering Sierra Leone or West Africa more broadly
    — a genuine access gap, left unintegrated as
    `VERIFICATION_REQUIRED` rather than assumed accessible.
  - **Universität Hamburg — Merit Scholarships** — requires the
    applicant to have "been enrolled at Universität Hamburg for at
    least 1 semester" — `ALREADY_ENROLLED`, architecturally the same
    shape as this platform's existing TUM International Student
    Scholarship (#59).
  - **Technical University of Berlin** — no distinct
    TU-Berlin-administered flagship scholarship page found; every
    result traced back to DAAD's own Study Scholarship/EPOS
    programmes, already covered by source #10.

### Fixed
—

### Removed
—

---

## [2026-09-06] — Spain, open-scope follow-up: no new source qualified

### Added
—

### Changed
- `docs/AUTHORITATIVE_SOURCES.md` and `docs/COUNTRY_PROVIDER_REGISTRY.md`
  — following an open-ended "find another scholarship opportunities in
  spain" request (no degree-level or funding-type restriction, unlike
  the recent fully-funded-Master's mega-prompts), researched six
  further Spanish institutions live and found no new qualifying
  candidate. No source code, tests, or fixtures changed.
  - **UC3M (Universidad Carlos III de Madrid)** — its official
    `/postgraduate/aid` hub (redirects to `/postgraduate/scholarships`)
    lists its own UC3M/AEM_UC3M programmes alongside many
    externally-funded, country-specific schemes (Mexico's FIDERH,
    Colombia's ICETEX/PCB, Santander-UC3M, India-specific funds). Every
    2026/27-cycle item is marked "Final decision" or "CLOSED DEADLINE"
    — the same multi-record architecture mismatch documented elsewhere
    in this project, and nothing currently open besides.
  - **University of Salamanca (USAL) — Becas Internacionales** — a
    genuinely strong programme (tuition exemption + accommodation +
    meals + insurance across 76 Master's titles), but the only host
    publishing its full current-call terms, `rel-int.usal.es`, sets
    `Disallow: /` for all user agents in `robots.txt` — the entire
    subdomain is off-limits to this platform's scraper, and a
    different subdomain's page merely links back to it while itself
    being a stale 2019 announcement. Not bypassed, per this project's
    standing robots.txt rule.
  - **USAL — "Mujeres por África" sub-component** — checked
    specifically for Sierra Leone relevance given its Africa focus, but
    it is externally administered by the Fundación Mujeres por África,
    with USAL as just one of many partner host universities
    (`EXTERNAL_ONLY` relative to USAL), and its 2026 registration
    deadline (14 May 2026) had already passed with no next-cycle page
    found.
  - **Universitat Autònoma de Barcelona (UAB)** — its general
    "Solicitar beca" grant (AGAUR/MEFPD) explicitly requires "domicilio
    familiar" within Spain as of 31 December 2025 — a domestic Spanish
    student grant, not available to an international applicant from
    abroad (`NOT_INTERNATIONAL`).
  - **University of Barcelona (UB) and Universidad Complutense de
    Madrid (UCM)** — live search for each surfaced only vague,
    aggregator-level claims with no single, specific, official page
    describing one particular scheme's exact eligibility and funding
    terms — Level 3 sources only, insufficient per this project's
    "official university source required" rule.

### Fixed
—

### Removed
—

---

## [2026-09-06] — Netherlands fully-funded Master's engine, continuation pass: no new source qualified

### Added
—

### Changed
- `docs/AUTHORITATIVE_SOURCES.md` and `docs/COUNTRY_PROVIDER_REGISTRY.md`
  — the Netherlands fully-funded-only mega-prompt was resubmitted after
  three genuinely fully-funded Dutch university sources already
  existed (TU Delft's Van Effen Scholarship #58, Groningen's Eric
  Bleumink Fellowship #72, Maastricht's High Potential Scholarship #74
  — confirmed by direct source-code inspection before starting). A
  further live pass found no new qualifying candidate:
  - **TU Delft** — the only other named full-scholarship route beyond
    Van Effen is the Fulbright Scholarship, US-government-funded and
    restricted to one faculty — external, not TU Delft's own.
  - **University of Twente** — fetched the full scholarship-finder
    listing (22 named schemes) directly. The Kipaji Scholarship (up to
    EUR 12,000) and Professor De Winter Scholarship (EUR 10,000) are
    both explicitly dependent add-ons to the already-partial UTS, not
    independently full, with no official statement that the
    combination reaches full funding. The STEM for ALL scholarship is
    small (EUR 5,000), externally funded (Thales Solidarity), and
    primarily Bachelor's-oriented.
  - **Radboud University — Radboud Encouragement Scholarship**: the
    most interesting finding. Radboud's own scholarships hub page
    exposes a filter facet confirming exactly one listed scholarship
    is tagged "Full scholarship" by the university's own system, and
    live search independently identifies it as the Radboud
    Encouragement Scholarship (full tuition + living costs for
    non-EU/EEA Master's applicants). Its specific detail page,
    however, returns an HTTP 403 SURFconext institutional login wall
    ("Login | Radboud University") — genuinely inaccessible without
    authentication, unlike the general hub page which remains public.
    Not bypassed, per this project's standing policy; recorded as
    `VERIFICATION_REQUIRED` due to an access barrier, not a funding
    shortfall — worth re-checking if Radboud ever exposes this page
    publicly.
  - **Erasmus University Rotterdam** — its Joint Japan/World Bank
    Graduate Scholarship Program (JJ/WBGSP) at ISS is genuinely fully
    funded, but it is the same global World Bank/Japan-government
    programme already on this platform as source #45
    (`world_bank_jjwbgsp`), not a separate Erasmus-specific scheme —
    not re-integrated to avoid double-counting.

  No new opportunity source was added this pass. Per this project's
  own "accuracy over quantity, do not pad the database" standard, a
  genuine second round of research that finds no qualifying candidate
  — while still surfacing one real, credible lead blocked purely by an
  access barrier — is the correct, complete outcome to report.

### Fixed
—

### Removed
—

---

## [2026-09-06] — England fully-funded Master's university scholarship engine: Gates Cambridge Scholarship (84th opportunity source)

### Added
- `app/services/national_scholarship_programs.py::GatesCambridgeScholarshipSource`
  — this platform's 84th opportunity source and **first England source
  classified as genuinely fully funded** (the nine pre-existing England
  sources — Imperial Inspires, Newcastle VC International, Sheffield
  PG, Manchester Global Futures, Nottingham PG, Southampton's two,
  Durham's two — are all `partial_funding`). The **Gates Cambridge
  Scholarship** (University of Cambridge / Gates Cambridge Trust):
  - Live-verified 2026-09-06 against
    `https://www.gatescambridge.org/programme/the-scholarship/`.
    `robots.txt` only disallows `/wp-admin/`, unrelated to this
    content path.
  - Genuinely fully funded: "A Gates Cambridge Scholarship covers the
    full cost of studying at Cambridge" — the University Composition
    Fee (tuition), a maintenance allowance (GBP 22,050/year at the
    2025-26 rate), one economy return airfare, and inbound visa costs
    plus the Immigration Health Surcharge. `funding_type =
    "fully_funded"`.
  - Eligibility: worldwide — "a citizen of any country outside the
    United Kingdom," no narrower list — Sierra Leone included. Funds
    "PhD ... MLitt ... [or a] one-year postgraduate course" (genuinely
    Master's-eligible, e.g. MPhil, not PhD-only), with a named
    exceptions list that does not exclude the standard Master's route.
  - Content selector `section#funding` (a stable HTML id);
    `title_selectors = ()` falls through to the external_id-derived
    fallback ("Gates Cambridge Scholarship") since this page's own
    `<h1>` ("The Scholarship") and `<title>` are both too generic.
  - Deliberately extracts no deadline: the funding page states none,
    and the separate Timeline page's three different deadlines (varying
    by applicant category and course) have no single canonical value a
    generic keyword could correctly resolve to.
  - Fully wired: config setting, source registry entry (`source_type =
    "university"`), Celery beat schedule + dedicated sync task, and a
    fixture-backed test.

  Oxford's Clarendon Fund was researched first as an equally strong
  candidate (official evidence: full course-fee coverage plus a living
  grant, no nationality restriction) — but `ox.ac.uk`, including its
  own `robots.txt`, returns an active Cloudflare "Just a moment..."
  managed challenge on every path tested. Per this project's "never
  bypass CAPTCHA/anti-bot protection" rule, not circumvented; recorded
  as `BLOCKED`, a funding-independent access blocker rather than a
  rejection of the scholarship itself (see
  `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass (England
  fully-funded Master's university engine), not integrated" section).

- **Verified**: full backend test suite — 813 passed, 25 skipped (up
  from 811 passed before this change), 0 failed; `pyflakes` clean on
  every changed/new file.

### Changed
—

### Fixed
—

### Removed
—

---

## [2026-09-06] — China fully-funded Master's engine, continuation pass: six more universities researched, no new source qualified

### Added
—

### Changed
- `docs/AUTHORITATIVE_SOURCES.md` and `docs/COUNTRY_PROVIDER_REGISTRY.md`
  — the China fully-funded Master's university scholarship request was
  resubmitted verbatim, asking for continued search per its own
  "automatic continuation" framing. Six further Chinese universities
  were researched live, each rejected for a distinct, concrete reason
  rather than a blanket "none found":
  - **Nanjing University** — its central Scholarships page auto-
    redirects via inline JavaScript straight to the Chinese Government
    Scholarship page; the only other listed routes are the Nanjing
    Municipal Scholarship (municipal government), the International
    Chinese Language Teachers Scholarship (Confucius Institute-
    specific), and the Confucius China Studies Program — no standalone
    NJU-funded Master's scheme exists.
  - **University of Science and Technology of China (USTC)** — its
    international admissions site is genuinely stale: its own
    scholarship detail page is titled "2020 USTC Scholarship Program"
    (last updated 2017), and its Notice board's most recent
    scholarship-relevant post is from 2022 — no 2023-2027 content found
    anywhere.
  - **Wuhan University** — every scholarship route found is Chinese
    Government Scholarship-branded; no distinct WHU-funded scheme.
  - **Sun Yat-sen University** — a genuinely real, distinct,
    non-CGS-combinable scheme (tiered tuition waiver + up to RMB
    30,000/year living allowance), but its own page's `<h1>` reads
    verbatim "CLOSED | 2026 Guidelines," with no 2027/next-cycle
    language anywhere on the page — a strong re-check candidate for a
    future pass once a next cycle is published.
  - **Renmin University of China** — only ambiguous, tiered "tuition
    scholarships" with no described living-stipend component found.
  - **Xi'an Jiaotong University — Siyuan International Student
    Scholarship** — a real, distinct, non-CGS scheme (tiered monthly
    stipends up to RMB 3,500/month), but its detail page is behind a
    genuine, active JavaScript anti-bot challenge (browser
    fingerprinting, a computed challenge hash posted to a
    `/dynamic_challenge` endpoint) — `BLOCKED`, not bypassed, per this
    project's standing anti-bot policy.

  No new opportunity source was added this pass. Per this project's own
  "accuracy over quantity" standard, a genuine second round of research
  that finds no qualifying candidate is the correct, honest outcome to
  report, not a gap to paper over with a weaker source.

### Fixed
—

### Removed
—

---

## [2026-09-06] — Canada fully-funded Master's follow-up: McGill University Mastercard Foundation Scholars Program (83rd opportunity source)

### Added
- `app/services/national_scholarship_programs.py::McgillMastercardScholarsSource`
  — this platform's 83rd opportunity source and **first Canada source
  of any kind**. Canada was previously found `NOT_SUITABLE` at the
  national/government level (EduCanada's Study in Canada Scholarships
  is institution-initiated, not individually-applicable), a finding
  that remains correct and unaffected — this is a university-
  administered source instead, the same partnership pattern already
  used for Sciences Po's own Mastercard Foundation Scholars Program
  (source #79). The **McGill University Mastercard Foundation Scholars
  Program**:
  - Live-verified 2026-09-06 against
    `https://www.mcgill.ca/mastercardfdn-scholars/about`. `robots.txt`
    sets `Crawl-delay: 5` and does not disallow this content path —
    `min_request_interval_seconds` is set to 5.0 to match that
    Crawl-delay exactly, more conservative than this project's usual
    2.0s default.
  - Genuinely fully funded: "Full international student tuition,
    On-campus housing, Personal monthly stipend ..., Academic tools and
    resources (book allowance, laptop, tutoring, etc.), ...
    Post-graduation transition expenses (ex. ... return flight, etc.)."
    `funding_type = "fully_funded"`.
  - Eligibility: the separate Eligibility page (not itself scraped for
    this record) states "Be a citizen of and live in an African
    country" and lists an explicit ~54-country table naming Sierra
    Leone directly — confirmed live during research. Limited to 13
    named graduate programmes (nutrition, public health, public policy,
    sustainable agriculture) and a first Master's degree only —
    documented honestly as a real scope constraint.
  - Content selector `div.field-name-body` (a stable Drupal field
    class); `title_tag_separator = " - McGill University"` handles a
    `<title>` with two site-name fragments to produce a properly
    descriptive title.
  - Deliberately extracts no deadline: this page states none.
  - Fully wired: config setting, source registry entry (`source_type =
    "university"`), Celery beat schedule + dedicated sync task, and a
    fixture-backed test.

  A pass across five major Canadian research universities found that
  Canadian universities almost universally structure graduate funding
  as a guaranteed *stipend* rather than a full tuition waiver — a
  structurally different pattern from China/Netherlands/France. Six
  other candidates were researched and rejected (see
  `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass (Canada
  fully-funded Master's follow-up), not integrated" section):
  - **University of Calgary** — a guaranteed $25,455/year stipend for
    international thesis-based Master's students, plus only a small
    separate ~$3,060/year tuition award — `PARTIALLY_FUNDED`.
  - **University of Alberta** — similar stipend-only ambiguity, no
    official statement that funding includes tuition.
  - **University of Waterloo** — its own page states plainly it "does
    not offer full-ride scholarships that cover all tuition and living
    costs."
  - **University of Toronto** — funding varies per department with no
    single university-wide evergreen page.
  - **University of British Columbia** — its International Tuition
    Award is a small (~$3,200/year) top-up, not comprehensive.
  - **McCall MacBain Scholarship** — genuinely comprehensive, but
    McGill's own site classifies it as an *external* scholarship it
    merely lists (URL path includes `/external/`), not one it
    administers end-to-end — left as a candidate for a future
    external-classified source rather than integrated here.

- **Verified**: full backend test suite — 811 passed, 25 skipped (up
  from 809 passed before this change), 0 failed; `pyflakes` clean on
  every changed/new file.

### Changed
—

### Fixed
—

### Removed
—

---

## [2026-09-06] — China fully-funded Master's university scholarship engine: Peking University and Shanghai Jiao Tong University (81st and 82nd opportunity sources)

### Added
- `app/services/national_scholarship_programs.py::PkuInternationalScholarshipSource`
  — this platform's 81st opportunity source and first China
  *university* source (Schwarzman Scholars, #50, and Yenching Academy,
  #52, are elite named programmes hosted at Tsinghua/PKU respectively,
  not this general institution-wide scholarship). The **Peking
  University Scholarship for International Students**:
  - Live-verified 2026-09-06 against
    `https://isd.pku.edu.cn/en/detail.php?id=525`. `robots.txt` returns
    this site's own custom 404 page, not an actual robots.txt — no
    `Disallow` rules exist for this host.
  - Genuinely fully funded: "It covers tuition, a living stipend and
    medical insurance," for a 2-3 year Master's duration.
    `funding_type = "fully_funded"`.
  - No nationality/country restriction stated anywhere — eligibility is
    framed only around PKU's own international-admission requirements
    — Sierra Leone applicants are eligible.
  - The page has no `<h1>` at all; `title_tag_separator = " | "` (a
    separator absent from the real `<title>` text) is used so the
    clean title tag text is taken directly, unchanged.
  - Deliberately extracts no deadline: "Application Time: Generally in
    January and March each year" carries no year, verified directly
    that neither the default `"deadline"` keyword nor an
    `"Application Time"` keyword resolves to a date.

- `app/services/national_scholarship_programs.py::SjtuMastersScholarshipSource`
  — this platform's 82nd opportunity source and second China
  university source. The **Master's SJTU Scholarship** (Shanghai Jiao
  Tong University):
  - Live-verified 2026-09-06 against
    `https://global.sjtu.edu.cn/en/study-sjtu/prospective/scholarships/62`.
    `robots.txt` returns a generic 404, not an actual robots.txt.
  - Genuinely fully funded: "Monthly stipend, standard tuition waiver,
    group comprehensive insurance in China, and accommodation subsidy."
    `funding_type = "fully_funded"`. Deliberately distinct from the
    same page's separately-named Tuition Waiver Scholarship (tuition +
    insurance only, no stipend — not integrated).
  - No nationality/country restriction stated — the whole hub page is
    framed under "Prospective International Students" with a "Foreign
    Students Apply" application portal.
  - Content selector is an adjacent-sibling CSS selector
    (`div.page-item + div.page-item`) deliberately targeting the
    second of exactly two tab panels on this multi-tab hub page (the
    Graduate-programmes panel, holding both PhD and Master's SJTU
    Scholarship text), without pulling in the Undergraduate panel's
    unrelated, separately-tiered scholarship scheme.
  - `title_selectors = ()`, no `title_tag_separator`: the page's
    `<title>` describes the whole hub, not this scholarship, so the
    external_id-derived fallback is used instead — `external_id`
    spells the university's name out in full so the fallback
    capitalizes correctly ("Shanghai Jiao Tong University Masters
    Scholarship," not "Sjtu").
  - Deliberately extracts no deadline: this panel states no date at
    all.

  Both fully wired: config settings, source registry entries
  (`source_type = "university"`), Celery beat schedule + dedicated sync
  tasks, and fixture-backed tests (fixtures captured unmodified from
  the live sites).

  A necessarily non-exhaustive pass across major Chinese universities
  (Peking, Tsinghua, Fudan, Shanghai Jiao Tong, Zhejiang) found that
  most channel international Master's funding primarily through the
  Chinese Government Scholarship (CGS/CSC) and provincial/municipal
  scholarships rather than running their own comprehensive,
  university-only fully-funded scheme — CGS and other government
  routes are deliberately kept out of this university-classified
  dataset even where a university administers the application, since
  the funding provider is the Chinese government, not the university.
  Three other candidates were researched and rejected (see
  `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass (China
  fully-funded Master's university engine), not integrated" section):
  - **Tsinghua University** — its own "Tuition Scholarships" (distinct
    from CGS) explicitly cover tuition only, no living stipend —
    `TUITION_ONLY`.
  - **Zhejiang University** — a hub page listing CGS Type A/B, CGS
    Youth of Excellence Scheme, the Zhejiang provincial scholarship,
    and school-specific awards — the same multi-record architecture
    mismatch documented for ESMT/WHU/Universidad de Navarra elsewhere
    in this project, with most individual pages carrying stale 2022
    URLs.
  - **Fudan University** — its International Students Office primarily
    channels applicants toward CGS/Shanghai Government/Confucius
    Institute scholarships; no standalone university-funded page
    comparable to PKU's or SJTU's own was found.
  - **SJTU's own Tuition Waiver Scholarship** — tuition + insurance
    only, no stipend — `TUITION_ONLY`, not integrated as its own
    record.

- **Verified**: full backend test suite — 809 passed, 25 skipped (up
  from 805 passed before this change), 0 failed; `pyflakes` clean on
  every changed/new file.

### Changed
—

### Fixed
—

### Removed
—

---

## [2026-09-06] — Germany fully-funded Master's follow-up: Konrad-Adenauer-Stiftung Scholarship Programme (extends the existing DAAD source)

### Added
- `app/services/daad_scholarships.py` — a seventh monitored detail id
  (`10000108`) added to the *existing* DAAD Scholarship Database source
  (#10), in response to a request for another fully funded Master's
  scholarship in Germany: the **Konrad-Adenauer-Stiftung (KAS):
  Scholarship Programme for International Students**. This is an
  addition to an existing multi-record source, not a new
  `OpportunitySource` row — the adapter's own module docstring already
  documents "adding more ids to that setting" as the intended way to
  grow its coverage, so the platform's total registered-source count is
  unaffected by this change.
  - Genuinely fully funded: a monthly grant of EUR 992 for Bachelor's/
    Master's recipients (Germany's standard BAföG maximum living-cost
    rate) plus health- and long-term-care insurance and child/family
    allowances where applicable, at German public universities, which
    charge no tuition for a first Master's degree in 15 of Germany's 16
    federal states. Documented honestly rather than glossed over: the
    one well-known exception is Baden-Württemberg, which has charged
    non-EU students tuition (around EUR 1,500/semester) since 2017,
    and this programme's own page does not separately address that
    state.
  - Eligibility: the live page's own country-eligibility dropdown lists
    "Sierra Leone" by name among roughly 150 countries — confirmed
    directly against the live site during research, not inferred from
    a vague regional label.
  - New `_FUNDING_TYPE_OVERRIDES` dict in `daad_scholarships.py`:
    the adapter's original six seed ids were never individually
    researched for funding completeness and predate this field's use
    elsewhere in the codebase, so rather than retroactively guess a
    classification for them, only this specifically-researched id is
    classified — the other six keep `funding_type = None` exactly as
    before, unaffected.
  - Deliberately extracts no deadline: the page states "Closing date
    for applications is 15 July (12 o'clock noon) of each year" — a
    real, recurring annual cycle with no year attached, so
    `extract_confident_date_after` correctly resolves to `None` rather
    than guessing a year, verified directly with a standalone script.
  - Fully wired within the existing adapter (no new config base URL,
    Celery task, or source-registry entry needed — this source already
    syncs every 24 hours); one new fixture-backed test plus a
    regression test confirming the other six seed ids remain
    unclassified.

  Two other German candidates were researched live and rejected (see
  `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass (Germany
  fully-funded Master's follow-up), not integrated" section for full
  detail, including RWTH Aachen, the Elite Network of Bavaria's Max
  Weber Programme, Constructor University, and Hertie School Berlin):
  - **Konrad-Adenauer-Stiftung's own website** (`kas.de`) — genuine
    bot-protection: `kas.de/robots.txt` itself returns a Web
    Application Firewall block page, not a robots.txt. Per this
    project's "never bypass CAPTCHA/bot-protection" rule, not
    circumvented — used the identical programme's DAAD-hosted mirror
    page instead (already an audited, unblocked source for this
    platform).
  - **Friedrich-Ebert-Stiftung (FES): Scholarship for International
    Students** — a real, generous programme with an explicit,
    checkable eligibility rule (Sierra Leone qualifies), but its own
    page states applicants must "already study in Germany" — support
    for already-enrolled students, not a scholarship a prospective
    Sierra Leonean applicant could use to fund initial admission from
    abroad, unlike KAS.

- **Verified**: full backend test suite — 805 passed, 25 skipped (up
  from 803 passed before this change), 0 failed; `pyflakes` clean on
  every changed/new file.

### Changed
—

### Fixed
—

### Removed
—

---

## [2026-09-06] — France fully-funded Master's university scholarship engine: Sciences Po Mastercard Foundation Scholars Program (80th opportunity source)

### Added
- `app/services/national_scholarship_programs.py::SciencesPoMastercardScholarsSource`
  — this platform's 80th opportunity source, added in response to a
  request to build a France-only, fully-funded-Master's-only,
  university-administered scholarship dataset. This is the registry's
  **first France university source** — France Excellence Eiffel (the
  existing France source, #27) and Erasmus Mundus (source #49) were
  deliberately kept out of this dataset as government/Campus France and
  externally-administered programmes respectively, not university-only
  scholarships, per this pass's own explicit instruction: a university
  nominating candidates for Eiffel does not make Eiffel a university
  scholarship.
  - Live-verified 2026-09-06 against
    `https://www.sciencespo.fr/students/en/fees-funding/bursaries-financial-aid/mastercard-foundation-scholarships/graduate-study/`.
    `robots.txt` does not disallow the `/students/` content path.
  - Genuinely, verifiably fully funded — not merely a large stipend:
    "A comprehensive grant: Scholarships cover the full cost of tuition
    and living expenses in France, throughout the recipient's time
    studying at Sciences Po" (parent hub page), and independently, on
    the page scraped, "The Program covers the full financial needs of
    selected Scholars." Also includes reserved Paris housing.
    `funding_type = "fully_funded"`.
  - Eligibility: the sole nationality criterion is "Hold the citizenship
    of an African country" — Sierra Leone is not excluded by name or by
    omission from any narrower list. Documented honestly rather than
    glossed over: applicants must *additionally* hold (or be completing)
    a Bachelor's degree from an approved partner university, or have
    completed a recognised bridge/mentoring programme, or hold UNHCR
    refugee status — a real constraint beyond blanket nationality
    eligibility, stated plainly rather than hidden. Only two-year
    Master's programmes qualify; one-year Master's and dual-degree
    programmes are explicitly excluded from this specific track.
  - Content selector `#main-content-page`: a stable, semantic HTML id
    (an anchor-scroll target used by the page's own in-page navigation),
    not one of the site's auto-generated CSS-module hash classes.
  - Deadline deliberately left unextracted: the page states "detailed
    information and the application timeline ... will be published on
    this page from September 2026" and gives only an imprecise
    "October to mid-December 2026" window, with no day number —
    `extract_confident_date_after` correctly resolves to `None` on the
    default `"deadline"`/`"closing date"` keywords rather than guessing
    a specific date. (The page's one full date literal, 17 October 2026,
    is an information-session date, not the deadline, and is never
    reached by the default keywords.)
  - Fully wired: config setting, source registry entry (`source_type =
    "university"`), Celery beat schedule + dedicated sync task, and a
    fixture-backed test (fixture captured unmodified from the live
    site).

  Eight other France candidates were researched live and correctly
  rejected from the fully-funded university-only dataset rather than
  inflated into it (see `docs/AUTHORITATIVE_SOURCES.md`'s new
  "Researched this pass (France fully-funded Master's university
  engine), not integrated" section for full detail):
  - **Sciences Po's own Émile Boutmy Scholarship** — a tuition-fee
    exemption only (€18,500/year), no living-cost component —
    `TUITION_ONLY`.
  - **France Excellence Eiffel** — government/Campus France-
    administered, not university-only — `EXTERNAL_ONLY`.
  - **Erasmus Mundus Joint Masters** (already source #49 on this
    platform) — externally administered by the European
    Commission/EACEA — `EXTERNAL_ONLY` for this dataset.
  - **Université Paris-Saclay's International Master's Scholarships
    Program** (which CentraleSupélec also participates in) — €10,000/
    year + travel allowance, but the university's own materials concede
    it covers "the majority of academic fees," not all of them —
    `PARTIALLY_FUNDED`.
  - **Institut Polytechnique de Paris / École Polytechnique** — Master's
    Excellence Scholarship and École Polytechnique Foundation
    scholarship, €8,000–10,000/year against up to €15,400/year tuition
    — `PARTIALLY_FUNDED`.
  - **PSL Université** — low regulated tuition plus scattered
    per-programme merit awards; no single page found stating full
    tuition-and-living coverage for a Master's (PSL's genuinely
    fully-funded tracks are PhD-linked, outside this pass's Master's-
    only scope) — `UNVERIFIED`/out of scope.
  - **Aix-Marseille Université's TIGER Master Excellence Grants** —
    €10,000/year + guaranteed CROUS accommodation, not stated to cover
    full cost — `PARTIALLY_FUNDED`.
  - **University of Bordeaux and Télécom Paris** — no
    university-administered fully-funded route found beyond
    Eiffel/Erasmus Mundus, both already excluded above.

- **Verified**: full backend test suite — 803 passed, 25 skipped (up
  from 801 passed before this change), 0 failed; `pyflakes` clean on
  every changed/new file.

### Changed
—

### Fixed
—

### Removed
—

---

## [2026-09-06] — Spain Master's/postgraduate follow-up: UPF Barcelona School of Management Merit Based Scholarship (79th opportunity source)

### Added
- `app/services/national_scholarship_programs.py::UpfBsmMeritScholarshipSource`
  — this platform's 79th opportunity source, added in response to a
  request for another Spain Master's/postgraduate scholarship. This is
  the registry's first Spain *university* source (the existing Spain
  source, #23 `spain_aecid`/Becas MAEC-AECID, is government-classified).
  - Live-verified 2026-09-06 against `https://www.bsm.upf.edu/en/talent-scholarship`.
    `robots.txt` does not disallow this content path.
  - No nationality or country restriction anywhere in the eligibility
    criteria (a completed university qualification and a minimum
    3.0/4.0 GPA, explicitly including degrees "obtained abroad") —
    Sierra Leone applicants are eligible.
  - Genuinely partial funding: "covers 25% of the total tuition fee,"
    extendable by "an additional 25%" for demonstrated financial need —
    `funding_type = "partial_funding"`, never described as fully funded.
  - The page lists four rolling annual application rounds with concrete
    dates (18 June 2026, 3 September 2026, 26 November 2026, 21 January
    2027). As of this research date the first two rounds had already
    passed, so `deadline_keywords` deliberately uses the specific phrase
    "3rd call" (confirmed to occur exactly once on the page) to resolve
    to the next genuinely upcoming round, 2026-11-26, rather than a
    generic "deadline" keyword (which resolves to nothing on this page)
    or the first round's stale date.
  - Content selector `div.body-content`: the page is built with a
    React/Next.js frontend using auto-generated CSS-in-JS class names
    for most wrapper elements, but this one class is stable, semantic,
    and verified via a direct BeautifulSoup structural walk to hold
    exactly the real content with none of the surrounding navigation.
  - Fully wired: config setting, source registry entry (`source_type =
    "university"`), Celery beat schedule + dedicated sync task, and a
    fixture-backed test (fixture captured unmodified from the live
    site).

  Four other candidates were researched live before settling on this
  one and found genuinely unsuitable rather than integrated (see
  `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass (Spain
  Master's/postgraduate follow-up), not integrated" section for full
  detail):
  - **IE University** — both its general scholarships hub and its
    detailed award pages are multi-scholarship listings (architecture
    mismatch) or client-side rendered with no content in a plain-HTTP
    fetch.
  - **Universidad de Navarra** — a hub page listing many separately
    named, separately sponsored scholarships, with individual
    scholarship detail only available as PDFs, not fitting the
    single-record `_SingleProgramSource` shape.
  - **ESADE** (Esade MSc Excellence Awards) — a single named scheme
    with regional/tier variants, which would otherwise fit, but its own
    deadline text explicitly reads "July 15, 2026 (for the 2026
    intake)" — already passed, with no next-cycle date stated anywhere
    on the page (a partially updated "2027-2028" tuition figure
    elsewhere on the same page was deliberately not treated as
    evidence of a same-shaped next cycle).
  - **UPF-BSM's own "Master of Science Scholarships" hub page** — real
    `<h1>` present but the substantive content is client-side rendered
    and absent from the plain-HTTP response, unlike the working
    `talent-scholarship` page that was integrated instead.

- **Verified**: full backend test suite — 801 passed, 25 skipped (up
  from 799 passed before this change), 0 failed; `pyflakes` clean on
  every changed/new file.

### Changed
—

### Fixed
—

### Removed
—

---

## [2026-09-06] — Netherlands Master's/postgraduate follow-up: University of Twente ITC Excellence Scholarship Programme (78th opportunity source)

### Added
- `app/services/national_scholarship_programs.py::UtwenteItcScholarshipSource`
  — this platform's 78th opportunity source, added in response to a
  request for another Netherlands Master's/postgraduate scholarship. A
  distinct scholarship from the university-wide University of Twente
  Scholarship (#75, added in the previous pass) — administered
  specifically by the Faculty of Geo-Information Science and Earth
  Observation (ITC) for two of its own Master's programmes, with its
  own eligibility list, cost breakdown, and application page.
  - Explicit "Countries eligible for this scholarship" enumeration of
    roughly 100 named low- and middle-income countries — confirmed
    directly that Sierra Leone appears in it.
  - Genuinely partial funding with an exact cost breakdown stated on
    the page: the ITC waiver covers EUR 25,000 of a EUR 74,370 two-year
    total cost, leaving EUR 17,000 of "own contribution" the applicant
    must independently secure.
  - Deliberately extracts no deadline: the page states "APPLICATIONS
    2026 CLOSED. A possible next round is expected to open in December"
    — a real, current status, but "December" alone carries no day or
    year for confident date extraction.
  - Fully wired: config setting, source registry entry, Celery beat
    schedule + dedicated sync task, and a fixture-backed test (fixture
    captured unmodified from the live site).

  Five other candidates were researched live before settling on this
  one and found genuinely unsuitable rather than integrated (see
  `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass
  (Netherlands Master's/postgraduate follow-up), not integrated"
  entry): VU Amsterdam's Faculty of Law Fellowship Programme turned out
  to be a visiting-researcher fellowship, not a degree scholarship;
  Erasmus MC's Erasmus Trustfonds, Ter Kulve, and TSH Changemaker
  Scholarships all share the same already-passed 1 April 2026 deadline
  (the Ter Kulve Scholarship in particular was a strong candidate
  otherwise — a genuine World Bank low/middle-income-country
  eligibility requirement — but the stale deadline ruled it out this
  pass); ESHPM's Erasmus Trust Fund Scholarship is EEA/EU-nationals-only
  and also locked to 2026-2027; TU Delft's Delft Global Scholarship
  Fund turned out to be a pure donor/fundraising page with no
  student-facing application process (contributions feed the existing,
  already-added Van Effen Scholarship's own application pipeline); and
  TU Delft's CLIP Scholarship is Greek-nationals-only with applications
  closed.

  **Verified**: full backend suite green after the change (799 passed,
  25 skipped, up from 797 — the new source's two tests plus the updated
  `test_opportunity_import.py` source-count assertion, 77 -> 78
  registered sources). `pyflakes app tests` clean (no new issues).

## [2026-09-06] — Netherlands exhaustive university expansion: seven new opportunity sources across six universities (71st-77th opportunity sources)

### Added
Seven new `_SingleProgramSource` classes in
`app/services/national_scholarship_programs.py`, added in response to a
directive for a deep, multi-pass Netherlands university scholarship and
funding expansion covering undergraduate, Master's/postgraduate, and PhD
levels across all major Dutch research universities. This platform's
71st through 77th opportunity sources, and its 19th through 24th
university-classified sources (TU Delft's Van Effen Scholarship, #58,
remains the first Netherlands-university source; these seven are the
second through eighth):

- `UvaAmsterdamMeritScholarshipMasterSource` /
  `UvaAmsterdamMeritScholarshipBachelorSource` — University of
  Amsterdam's Amsterdam Merit Scholarship, separate Master's and
  Bachelor's overview pages, non-EU/EEA-only, no deadline/amount
  asserted since the pages themselves state both vary per Faculty.
- `GroningenEricBleuminkFellowshipSource` — University of Groningen's
  Eric Bleumink Fellowship, restricted to an explicit ~80-country list
  **confirmed to include Sierra Leone directly**, nomination-based (no
  separate application — the university's own Admission Office
  nominates from regular Master's applications), genuinely
  `fully_funded` (tuition + travel + subsistence + books + insurance).
- `UtrechtLegitsScholarshipSource` — Utrecht University's Law, Economics
  and Governance International Talent Scholarship, open to EU/EEA and
  non-EU/EEA alike, tuition-only `partial_funding`. Utrecht's central
  Utrecht Excellence Scholarship was confirmed **discontinued** for
  2026-2027 entry onward ("due to significant budget cuts") and its
  Bright Minds Fellowships confirmed EU/EEA-only — neither used instead.
- `MaastrichtHighPotentialScholarshipSource` — Maastricht University's
  UM NL-High Potential Scholarship, genuinely `fully_funded` (tuition
  waiver + monthly stipend), already updated for the 2027-2028 cycle
  with a real, not-yet-passed deadline (10 December 2026).
- `UniversityOfTwenteScholarshipSource` — a cash award (not a tuition
  waiver), explicit eligible-countries list **confirmed to include
  Sierra Leone**, already updated for 2027/2028 with a real deadline (1
  April 2027).
- `WageningenAnneVanDenBanFundSource` — nomination-based (like
  Groningen's) full-or-partial Master's funding for students from
  low-income countries, no deadline extracted (year-less recurring
  dates).

Six further Netherlands universities were researched live and found
genuinely unsuitable rather than integrated (see
`docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass (Netherlands
exhaustive expansion), not integrated" entry): **Vrije Universiteit
Amsterdam** and **TU Eindhoven** were both locked to already-closed
2026-2027 cycles with no next-cycle page published (TU/e additionally
states outright that it offers no Bachelor's scholarships at all);
**Leiden University** and **Tilburg University** are both behind genuine
bot-protection challenges (an F5/Shape-style JS challenge and a
Cloudflare "Just a moment..." challenge respectively) and were never
bypassed, per this platform's standing rule; **Erasmus University
Rotterdam**'s Trustfonds Scholarship is explicitly titled and locked to
the 2026-2027 cycle, and Rotterdam School of Management's scholarships
page appears client-side-rendered; **Radboud University**'s Scholarship
Programme explicitly states its 2026-2027 deadline "has passed" with no
next cycle published, and its Encouragement Scholarship requires
SURFconext login.

A recurring finding across this pass, worth recording explicitly: as of
this research date (6 September 2026), most Dutch universities' Master's
scholarship pages for the September 2026 intake had already closed
their application windows (deadlines typically falling
December-February) with no 2027-2028 cycle page published yet — a
genuine timing gap, not a research shortfall. The universities that did
yield a viable source either (a) had already refreshed their pages for
the next cycle (Maastricht, Twente), (b) described a nomination-based
mechanism with no year-specific deadline to go stale (Groningen,
Wageningen), or (c) had a genuinely evergreen, deadline-varies-by-faculty
structure (UvA), or (d) had a scholarship whose stated deadline never
carried a year at all (Utrecht).

Fully wired end-to-end for all seven sources: config settings, source
registry entries, Celery beat schedules + dedicated sync tasks, and
fixture-backed tests (fixtures captured unmodified from the live sites).

**Verified**: full backend suite green after the change (797 passed, 25
skipped, up from 783 — the seven new sources' fourteen tests plus the
updated `test_opportunity_import.py` source-count assertion, 70 -> 77
registered sources). `pyflakes app tests` clean (no new issues).

## [2026-09-06] — Germany postgraduate, masters, and undergraduate: University of Freiburg Deutschlandstipendium (70th opportunity source; this platform's second Germany-university source)

### Added
- `app/services/national_scholarship_programs.py::FreiburgDeutschlandstipendiumSource`
  — this platform's 70th opportunity source, added in response to a
  request for another Germany postgraduate, masters, and undergraduate
  universities scholarship. Unlike the recent England sources (one page
  per degree level), this single University of Freiburg page explicitly
  covers **both** halves of the request at once: its eligibility text
  names both undergraduate and Master's degree programme students.
  - The **Deutschlandstipendium** ("Germany Scholarship") is a
    EUR 300/month, one-year public-private stipend, half funded by the
    federal government and half by private sponsors — genuinely open to
    "students of all nationalities," so Sierra Leone applicants are
    eligible. Requires being enrolled as a regular student at the
    University of Freiburg, the same "already enrolled" shape as this
    platform's existing TUM International Student Scholarship source
    (#59) — TUM remains this platform's *first* Germany-university
    source, Freiburg is its second.
  - Deliberately extracts no deadline despite two dates being present:
    the page states the 2026/2027 award year's application deadline "has
    passed" (no date literal within reach) and that "you can apply for
    the 2027/2028 scholarship round from 1 March 2027 to 31 March 2028"
    — a thirteen-month window that contradicts the page's own
    description elsewhere of a roughly one-month March application
    period each year. Read as a likely site typo (probably meant 31
    March 2027) rather than a literal fact — per this platform's
    "extract nothing rather than guess wrong" rule, no deadline is
    extracted rather than reporting a suspect date verbatim.
  - Content selector: the first `div.wp-block-columns` on the page,
    deliberately not the much larger `main` element (42KB, mostly a
    tabbed FAQ accordion repeating the same eligibility detail) —
    verified directly via a structural walk of the fetched page.
  - Fully wired: config setting, source registry entry, Celery beat
    schedule + dedicated sync task, and a fixture-backed test (fixture
    captured unmodified from the live site, following the page's own
    301 redirect to its canonical `uni-freiburg.de` host).

  Ten other Germany candidates were researched live before settling on
  Freiburg and found genuinely unsuitable rather than integrated (see
  `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass (Germany
  postgraduate/masters/undergraduate follow-up), not integrated" entry):
  Heidelberg's scholarship pages are for outgoing students, not incoming
  applicants; Bonn's scholarships require existing enrollment with
  details "to be published," and its own Deutschlandstipendium round has
  ended with no next round announced; Constructor University Bremen's
  three named scholarships (two JetBrains Foundation, one Sparkasse) all
  have March 2026 deadlines already passed with no next cycle published;
  Mannheim's two named scholarships have both "ended" their 2026/2027
  windows; ESMT Berlin, WHU, and Frankfurt School all present their
  financing pages as hubs of roughly ten separately-named,
  separately-sponsored scholarships each — the same multi-record
  architecture mismatch already established for Warwick's Doctoral
  College page, not forced into a single-record shape; Göttingen's
  advertised scholarship is DAAD-administered (already covered by this
  platform's existing DAAD source, #10) with a year-less deadline; and IU
  International University of Applied Sciences' scholarship content
  appears to be rendered client-side and did not surface in a plain-HTTP
  fetch.

  **Verified**: full backend suite green after the change (783 passed,
  25 skipped, up from 781 — the new source's two tests plus the updated
  `test_opportunity_import.py` source-count assertion, 69 -> 70
  registered sources). `pyflakes app tests` clean (no new issues).

## [2026-09-06] — Fifth England follow-up (postgraduate, masters, and undergraduate): Durham University Inspiring Excellence Scholarships (68th and 69th opportunity sources; this platform's first Durham University source)

### Added
- `app/services/national_scholarship_programs.py::DurhamInspiringExcellenceUndergraduateScholarshipSource`
  and `::DurhamInspiringExcellencePostgraduateScholarshipSource` — this
  platform's 68th and 69th opportunity sources, both from Durham
  University, added in response to a request for another England
  postgraduate, masters, and undergraduate scholarship (the postgraduate
  source covers one-year taught Master's degrees, satisfying both the
  "postgraduate" and "masters" parts of the request).
  - Both scholarships are competitive tuition-fee-discount awards
    (`funding_type = "partial_funding"`) for **self-funded international
    applicants** with **no nationality/country restriction stated** —
    Sierra Leone applicants are eligible like any other international
    student. Undergraduate: up to £15,000-£30,000 over a three-year
    programme. Postgraduate (taught Master's — MSc/MA/LLM/MDS): up to
    £10,000 for a one-year programme.
  - Both pages state three application rounds for September 2027 entry;
    the adapter extracts the first (earliest) round's date, 7 December
    2026, via the specific `deadline_keywords` phrase "1st round
    application deadline" — the generic "deadline" keyword's first match
    on the page is an unrelated "UCAS reply deadline" phrase with no
    date literal nearby, so it was deliberately not used.
  - Discovered a real extraction gotcha shared by both pages: a later,
    separate `div.t4-text-long` block on the same page holds only the
    scholarship's Terms and Conditions (withdrawal/notification rules),
    not the actual Summary/Amount/Eligibility/How-to-apply content a
    reader needs — the adapter targets `div.col-md-9` instead, verified
    directly via a structural walk of the fetched HTML before choosing
    the selector. Neither page has an `<h1>`, so both rely on the
    existing `external_id`-derived title fallback rather than a
    `title_selectors`/`title_tag_separator` match.
  - Both fully wired: config settings, source registry entries, Celery
    beat schedules + dedicated sync tasks, and fixture-backed tests
    (fixtures captured unmodified from the live site via `curl`; no
    compression handling needed unlike the Southampton pages above).

  Two further England candidates were researched this pass and found
  genuinely stale rather than integrated (see
  `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass (England
  postgraduate/masters/undergraduate follow-up), not integrated" entry):
  University of Bristol's Think Big / GREAT postgraduate scholarships
  closed their 2026-27 cycle on 10 April 2026 with no 2027-28 cycle page
  published yet; University of York's International Undergraduate
  Achievement Scholarship's stated eligibility window (offer held by 30
  June 2026) has likewise passed with no next-cycle page found.

  **Verified**: full backend suite green after the change (781 passed,
  25 skipped, up from 777 — the two new sources' four tests plus the
  updated `test_opportunity_import.py` source-count assertion, 67 -> 69
  registered sources). `pyflakes app tests` clean (no new issues).

## [2026-09-05] — Fourth England follow-up (postgraduate and undergraduate): University of Southampton Presidential Bursaries and Merit Scholarships (66th and 67th opportunity sources; first England undergraduate source since Newcastle)

### Added
- `app/services/national_scholarship_programs.py::SouthamptonPresidentialBursariesSource`
  and `::SouthamptonMeritUndergraduateScholarshipSource` — this
  platform's 66th and 67th opportunity sources, both from the
  University of Southampton, added in response to a request for another
  England postgraduate *and* undergraduate scholarship.
  - **Presidential bursaries** (postgraduate) — a PhD-level
    fee-difference bursary ("funds the difference between UK and
    international level tuition fees"), genuinely open to all
    international candidates with no country restriction, unlike
    Sheffield's (#62) or Manchester's (#63) England postgraduate
    sources. Discovered a real extraction gotcha: the page's `<article>`
    wrapper also carries a large sidebar of dozens of unrelated
    scholarship names before the real content — the adapter targets the
    narrower `div.body--content` instead, verified directly rather than
    assumed. No deadline extracted (the only date on the page is the
    eligibility window's opening, not an application deadline — there
    is no separate application at all).
  - **Merit scholarships for international undergraduates**
    (undergraduate) — this platform's first England undergraduate
    source since Newcastle's VCIS (#61), and structurally different
    from it: eligibility is based on exceeding academic offer
    conditions (A-level/IB grades above the standard offer) rather than
    a country/region list, with no nationality restriction stated at
    all. Up to £4,500 off first-year tuition. No deadline extracted —
    eligibility is grade-outcome-based, not date-based.
  - Both fully wired: config settings, source registry entries, Celery
    beat schedules + dedicated sync tasks, and fixture-backed tests
    (fixtures captured unmodified from the live site — noting the site
    serves gzip/brotli-compressed responses, requiring `curl
    --compressed` during manual verification; this codebase's own
    `httpx`-based HTTP client already decodes this transparently, so no
    adapter-level change was needed).

  **Verified**: full backend suite green after the change (777 passed,
  25 skipped, up from 773 — the two new sources' four tests plus the
  updated `test_opportunity_import.py` source-count assertion, 65 -> 67
  registered sources). `pyflakes app tests` clean (no new issues).

## [2026-09-05] — Third England postgraduate follow-up: University of Nottingham International Postgraduate Scholarship (65th opportunity source)

### Added
- `app/services/national_scholarship_programs.py::NottinghamPgScholarshipSource`
  — the **University of Nottingham International Postgraduate
  Scholarship**, this platform's 65th opportunity source. An automatic
  tuition-fee deduction for self-funded international students starting
  a full-time, UK-campus-based postgraduate taught Master's degree.
  Genuinely distinct in shape from this platform's other four England
  sources (#60–63, all restricted to a specific country list and/or a
  named entry year): this page states no country/nationality
  restriction at all and no entry-year lock anywhere — a genuinely
  evergreen description, not tied to one admissions cycle. No funding
  amount asserted in code even though secondary sources cited "£3,000"
  — the actual overview page used doesn't state a figure, so nothing
  beyond what's actually scraped is asserted. No deadline extracted
  since none is stated. Fully wired: config setting, source registry
  entry, Celery beat schedule + dedicated sync task, and a
  fixture-backed test (fixture captured unmodified from the live site).

  Three further England candidates were researched this pass and found
  genuinely ambiguous or out of scope rather than integrated (see
  `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass (third
  England postgraduate follow-up), not integrated" entry): University
  of Leeds' Regional/Excellence Masters scholarships are scoped to a
  September 2026 cohort whose window has effectively closed, with their
  2027-suffixed successor URLs confirmed to be soft-404s (HTTP 200 but
  a `<title>` reading "404-error"); Queen Mary University of London
  returned a genuine HTTP 403 on every fetch; and University of
  Warwick's Doctoral College scholarship page is a multi-tab listing of
  six distinct competitions rather than a single flagship page.

  **Verified**: full backend suite green after the change (773 passed,
  25 skipped, up from 771 — the new source's two tests plus the updated
  `test_opportunity_import.py` source-count assertion, 64 -> 65
  registered sources). `pyflakes app tests` clean (no new issues).

## [2026-09-05] — Second England postgraduate follow-up: University of Manchester Global Futures Scholarships (64th opportunity source)

### Added
- `app/services/national_scholarship_programs.py::ManchesterGlobalFuturesScholarshipSource`
  — the **University of Manchester Global Futures Scholarships**, this
  platform's 64th opportunity source. "More than 350 partial
  merit-based scholarships" (over £6 million total) for September 2027
  entry, open to both undergraduate and master's (postgraduate taught)
  students — the page explicitly names "Taiwan (postgraduate taught
  master's only)" as one region, confirming genuine postgraduate
  applicability rather than an assumption. Restricted to a specific
  published country list (Bangladesh, Botswana, Canada, Egypt, Ghana,
  India, Indonesia, Kenya, Malaysia, Mauritius, Nigeria, Pakistan, Saudi
  Arabia, Singapore, South Africa, Sri Lanka, Taiwan, Thailand, Türkiye,
  UAE, USA, Vietnam, Zimbabwe) — **Sierra Leone is not on it**, checked
  directly. No deadline extracted: the page states plainly that
  deadlines "differ for each region," with no single date on this hub
  page. Fully wired: config setting, source registry entry, Celery beat
  schedule + dedicated sync task, and a fixture-backed test (fixture
  captured unmodified from the live site).

  Five further England candidates were researched this pass and found
  genuinely stale or blocked rather than integrated (see
  `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass (England
  postgraduate follow-up), not integrated" entry): Aston University's
  Vice-Chancellor's International Scholarship page is fetchable but its
  own text is stale (references September 2024 and an October 2023
  deadline, with no current cycle evidence); Aston's Postgraduate Impact
  Scholarship page has been retired/merged into a generic hub;
  Nottingham Trent University and University of Leicester's scholarship
  pages all returned genuine HTTP 403s (active bot protection, not
  circumvented); and the University of Birmingham's Postgraduate High
  Fliers Scholarship page is real and current-looking but its own FAQ
  states a 31 July 2026 deadline that has already passed, with no
  announced next cycle.

  **Verified**: full backend suite green after the change (771 passed,
  25 skipped, up from 769 — the new source's two tests plus the updated
  `test_opportunity_import.py` source-count assertion, 63 -> 64
  registered sources). `pyflakes app tests` clean (no new issues).

## [2026-09-05] — Follow-up England postgraduate source: University of Sheffield (63rd opportunity source)

### Added
- `app/services/national_scholarship_programs.py::SheffieldPgScholarshipSource`
  — the **University of Sheffield International Postgraduate
  Scholarship 2027 (selected regions)**, this platform's 63rd
  opportunity source and its first England source specifically for
  postgraduate applicants (Imperial Inspires #60 and Newcastle's VCIS
  #61 are both primarily undergraduate). A partial GBP 7,000 tuition fee
  reduction for taught postgraduate offer-holders starting September
  2027, restricted to a specific, explicitly-published list of
  countries/regions (India, Indonesia, Japan, Kenya, Nigeria, South
  Korea, Taiwan, Thailand, Türkiye, Vietnam) — Kenya and Nigeria are
  eligible, **Sierra Leone is not**, checked directly against the
  published list rather than assumed. Awarded automatically, no separate
  application. This platform's first England source to successfully
  extract a real, exact, future deadline (6 July 2027) — the page's
  literal word "deadline" sits more than 300 characters after the
  actual date, so the adapter anchors on the sentence's own opening
  ("accept your offer") instead of the default keyword. Fully wired:
  config setting, source registry entry, Celery beat schedule +
  dedicated sync task, and a fixture-backed test (fixture captured
  unmodified from the live site).

  **Verified**: full backend suite green after the change (769 passed,
  25 skipped, up from 767 — the new source's two tests plus the updated
  `test_opportunity_import.py` source-count assertion, 62 -> 63
  registered sources). `pyflakes app tests` clean (no new issues).

## [2026-09-05] — England university expansion: Imperial Inspires and Newcastle VCIS (61st and 62nd opportunity sources; first England-university sources)

### Added
- `app/services/national_scholarship_programs.py::ImperialInspiresScholarshipSource`
  and `::NewcastleVcInternationalScholarshipSource` — this platform's
  61st and 62nd opportunity sources, added during a dedicated England
  university-opportunity expansion pass. University sources go from 7
  to 9; these are the registry's first two England-based university
  sources.
  - **Imperial Inspires scholarships** (Imperial College London) — a
    new-for-2027-entry partial scholarship (GBP 15,000/year, "at least
    300" awards) for international (Overseas-fee) undergraduate and
    selected postgraduate taught applicants across four faculties.
    Correctly classified `partial_funding`: the page itself says
    applicants remain responsible for any remaining tuition and living
    costs. No deadline extracted — the page states only "September
    2026" (opening) and "mid-April 2027" (awarding), never a specific
    calendar date.
  - **Newcastle University Vice-Chancellor's International
    Scholarships** — a partial (GBP 7,000/year) undergraduate tuition
    award for the 2027/28 academic year, restricted to a specific,
    explicitly-published list of eligible countries/regions (verified
    directly from the live page). **Sierra Leone is not on that list** —
    checked explicitly rather than assumed from "international
    students," per this platform's standing Sierra-Leone-eligibility
    discipline; the full list is preserved in the scraped description
    so this is auditable from the stored record itself. A real
    extraction subtlety: the page's raw HTML carries a second, stale
    `<h1>` inside an HTML comment, which BeautifulSoup correctly never
    surfaces as a real element (verified directly, not assumed). No
    deadline extracted: the page's only dates are either open-ended
    ("throughout the academic year") or ordinal-suffixed UCAS dates
    that don't match the shared date-literal pattern — and are the
    separate UCAS course-application deadline, not a distinct
    scholarship deadline that doesn't actually exist here.
  - Both fully wired: config settings, source registry entries, Celery
    beat schedules + dedicated sync tasks, and fixture-backed tests
    (fixtures captured unmodified from the live sites).

  **Verified**: full backend suite green after the change (767 passed,
  25 skipped, up from 763 — the two new sources' four tests plus the
  updated `test_opportunity_import.py` source-count assertion, 60 -> 62
  registered sources). `pyflakes app tests` clean (no new issues).

  **Honest scope note**: the requesting brief named 40-60+ English
  universities as a coverage goal. This pass verified 2 — both from the
  brief's own named "important current examples," both real, both
  fully wired and tested. The much larger university/faculty/department/
  PhD-vacancy sweep the brief describes was not attempted at that scale
  in this pass; quality-per-source (live HTTP verification, robots.txt
  check, honest eligibility transcription, no fabricated deadlines) was
  prioritized over breadth, consistent with the brief's own "quality
  over quantity" and "if only 37 are found, report 37" instructions.

## [2026-09-05] — Germany + Netherlands university expansion: TU Delft and TUM (59th and 60th opportunity sources; first Germany-university source)

### Added
- `app/services/national_scholarship_programs.py::TuDelftVanEffenScholarshipSource`
  and `::TumInternationalStudentScholarshipSource` — this platform's 59th
  and 60th opportunity sources, added during a dedicated Germany +
  Netherlands university-opportunity expansion pass. University sources
  go from 5 to 7; this is the registry's first Germany-based university
  source.
  - **TU Delft Justus & Louise van Effen Excellence Scholarships**
    (Netherlands) — a genuinely university-administered, fully-funded
    scholarship (full tuition + living-expense contribution), distinct
    from the Dutch government's own NL Scholarship. Restricted to
    admitted international Master's applicants — explicitly excludes TU
    Delft's own bachelor's graduates and internationals who completed
    their bachelor's in the Netherlands, verified directly from the
    page's exclusion list rather than assumed. Current deadline (1
    December 2026, for the 2027/28 round) read directly off the live
    page; a stale "December 1, 2025" figure surfaced by secondary
    sources during discovery was not used.
  - **TUM Scholarship for International Students** (Germany) — a
    Bavarian-government-funded but university-administered need-based
    top-up grant (EUR 500-1,800 one-time per semester), correctly
    classified `partial_funding`, never `fully_funded`. Deliberately
    documented as **not** for incoming applicants: eligibility requires
    the candidate to already be enrolled at TUM and ineligible for
    BAföG "due to their nationality" — a retention grant, not a
    study-abroad scholarship. No deadline extracted: the page states its
    application window with ordinal-suffixed days ("1st October - 15th
    October 2026") and a separate recurring, year-less "Deadline: 15
    November / 15 May" — neither matches the shared confident-date
    pattern, so nothing was guessed.
  - Both fully wired: config settings, source registry entries, Celery
    beat schedules + dedicated sync tasks, and fixture-backed tests
    (fixtures captured unmodified from the live sites).

  Several further university pages were researched and found genuinely
  inaccessible or architecturally out of scope for this pass (see
  `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass (Germany +
  Netherlands), not integrated" entry): TU Delft's general scholarships
  hub, RWTH Aachen, and University of Freiburg's Deutschlandstipendium
  page all returned HTTP 404 on their expected (secondary-source-cited)
  URLs — the underlying CMS content had moved; Heidelberg University's
  Germany Scholarship page is real and current but renders its actual
  content as a client-side JSON payload rather than server-rendered
  HTML, which this pass's selector-based extraction can't read cleanly;
  and both TU Delft's and TUM's general scholarship-listing pages are
  multi-record filterable databases rather than single flagship pages.

  **Verified**: full backend suite green after the change (763 passed,
  25 skipped, up from 759 — the two new sources' four tests plus the
  updated `test_opportunity_import.py` source-count assertion, 58 -> 60
  registered sources). `pyflakes app tests` clean (no new issues).

## [2026-09-05] — Source-diversity pass: Humboldt Research Fellowship and Max Planck Schools (57th and 58th opportunity sources; first Research Institution category)

### Added
- `app/services/national_scholarship_programs.py::HumboldtResearchFellowshipSource`
  and `::MaxPlanckSchoolsSource` — this platform's 57th and 58th
  opportunity sources, added during a dedicated pass targeting source
  categories underrepresented against this platform's government-heavy
  registry (at the time: 40 government vs. 5 university, 2 funding
  organization, 1 foundation, 1 embassy, 0 research institution).
  - **Humboldt Research Fellowship** (Alexander von Humboldt Foundation,
    Germany) — a **Foundation**-classified source (distinct from
    Germany's government-run DAAD, already source #10), open to
    "researchers of all nationalities and research areas" for 6-24
    months of research in Germany. Genuinely different shape from every
    other source in this file: no single annual deadline exists — three
    calls open per year, each closing once a fixed application cap is
    reached rather than on a calendar date. The live page's real-time
    status ("We have received the maximum number of applications for
    the current call... The next call will open on November 15, 2026")
    is an *opening* date, not a deadline — deliberately not extracted
    into the `deadline` field, which would mislabel it.
  - **Max Planck Schools** (Germany) — this platform's first
    **Research Institution**-classified source. A joint doctoral program
    of 30 German universities and 33 research organizations, open to
    "candidates from around the world," full funding for up to five
    years, no tuition fees. Deliberately not the general, decentralized
    Max Planck Institute PhD route, whose own official page states "There
    is no central application procedure" across ~80 independent
    institutes — the same pattern already found unsuitable for
    Canada/Denmark/Singapore. No deadline extracted: the recurring
    "September 1 to December 1" application window is never paired with
    a specific year anywhere on the page.
  - Both fully wired: config settings, source registry entries, Celery
    beat schedules + dedicated sync tasks, and fixture-backed tests
    (fixtures captured unmodified from the live sites).

  Four further candidates were researched this pass and found
  genuinely blocked by active anti-bot protection rather than
  circumvented, per this project's standing rule (see
  `docs/AUTHORITATIVE_SOURCES.md`'s new "Researched this pass (source
  diversity), not integrated" table): University of Melbourne Graduate
  Research Scholarships (HTTP 403 on every fetch, including its own
  `robots.txt`), UNSW Scientia PhD Scholarship Scheme (officially "not
  currently recruiting," no next cycle announced), Wellcome Trust
  International Masters Fellowships (HTTP 202 with an empty body,
  consistent with an async bot challenge), and AAUW International
  Fellowships (HTTP 403).

  **Verified**: full backend suite green after the change (759 passed,
  25 skipped, up from 755 — the two new sources' four tests plus the
  updated `test_opportunity_import.py` source-count assertion, 56 -> 58
  registered sources). `pyflakes app tests` clean (no new issues).

## [2026-09-05] — Follow-up opportunity source: TaiwanICDF Scholarship Program (56th opportunity source)

### Added
- `app/services/national_scholarship_programs.py::TaiwanIcdfScholarshipSource`
  — the **TaiwanICDF International Higher Education Scholarship
  Program**, this platform's 56th opportunity source, run by the Taiwan
  International Cooperation and Development Fund since 1998, offering
  full scholarships to students from Taiwan's partner countries to study
  at partner universities in Taiwan. `robots.txt` (checked 2026-09-05,
  confirmed across three separate fetch attempts) returns a genuine HTTP
  404 — no robots.txt file exists at all, treated as unrestricted per
  RFC 9309. Confirmed the *next* (2027) cycle directly from the live
  page's own current announcement — applications open 1 December 2026
  through 15 March 2027 — rather than reusing the already-closed 2026
  cycle's dates (deadline 15 March 2026, already past as of the research
  date) or guessing the 2027 dates from the 2026 ones. The "Eligibility"
  and "Apply Now" URLs surfaced by web search both redirect to a dead
  page on the live site (the CMS has since reassigned those content
  IDs) — recorded rather than guessed at; only the one confirmed-working
  overview page is used. One real extraction subtlety: the page's
  current-cycle text reads "...applications open from December 1, 2026
  to March 15, 2027!" — anchoring on the default "deadline" keyword
  finds nothing (that word never appears on the page) and anchoring on
  "applications open" would extract the *opening* date first; the
  adapter anchors on "to march" instead so it correctly extracts the
  real deadline (March 15, 2027). Fully wired: config setting, source
  registry entry, Celery beat schedule + dedicated sync task, and a real
  fixture-backed test (fixture captured unmodified from the live fetch).

  **Verified**: full backend suite green after the change (755 passed,
  25 skipped, up from 753 — the new source's two tests plus the updated
  `test_opportunity_import.py` source-count assertion, 55 -> 56
  registered sources). `pyflakes app tests` clean (no new issues).

## [2026-09-05] — Opportunity expansion pass: Hong Kong PhD Fellowship Scheme (55th opportunity source)

### Added
- `app/services/national_scholarship_programs.py::HongKongPhdFellowshipSchemeSource`
  — the **Hong Kong PhD Fellowship Scheme (HKPFS)**, this platform's 55th
  opportunity source, run by the Research Grants Council of Hong Kong
  since 2009 and funding PhD study at eight Hong Kong universities
  (annual stipend HK$344,400 plus a HK$14,400 conference/travel
  allowance, up to three years). Genuinely global — its own eligibility
  text states candidates qualify "irrespective of their country of
  origin, prior work experience and ethnic background." `robots.txt`
  (checked 2026-09-05) returns a genuine HTTP 404 (the site's own "Not
  found" error page) — no robots.txt file exists at all, treated as
  unrestricted per RFC 9309. Confirmed the current 2027/28 round is
  actually open (1 September 2026 – 1 December 2026, Hong Kong time),
  not inferred from a prior year's cycle — verified directly against the
  live `apply.html`/`news.html` pages. One real data-quality finding:
  the deadline page repeats "Application Deadline: 1 December 2026"
  once per participating university except one stale, seemingly-never-
  updated "1 December 2015" row for a ninth section; the adapter anchors
  on the RGC's own single unambiguous sentence instead of any of those
  repeated/inconsistent per-university rows. Fully wired: config
  setting, source registry entry, Celery beat schedule + dedicated sync
  task, and a real fixture-backed test (two fixtures — overview and
  apply pages — both captured unmodified from the live fetch).

  This was a dedicated research pass checking a long list of named
  government/university flagship programmes (Erasmus Mundus, DAAD,
  Chevening, Commonwealth, MEXT, GKS, Swiss ESKAS, Swedish Institute,
  Campus France, Australia Awards, Belgium ARES, Rotary Peace, and more)
  against this platform's existing 54 sources first — all of those were
  already implemented in prior sessions. Three genuinely new candidates
  were also researched and documented as **not integrated** rather than
  left as silent dead ends (see `docs/AUTHORITATIVE_SOURCES.md` #54 and
  `docs/COUNTRY_PROVIDER_REGISTRY.md`'s new "not integrated" entries):
  EU Marie Skłodowska-Curie Actions Postdoctoral Fellowships (real call,
  but its 2026 deadline was only 4 days away at research time with no
  2027 call yet announced, and its real application path is the
  separate EU Funding & Tenders Portal rather than a page the program's
  own site controls); Vanier Canada Graduate Scholarships (its
  eligibility page returned HTTP 503 on two independent fetch attempts —
  recorded rather than circumvented, consistent with this project's
  never-bypass-access-restrictions rule); and EPFL Excellence
  Fellowships (a real program, but every deadline found came from
  third-party aggregators, not an official EPFL page, and all of those
  had already passed).

  **Verified**: full backend suite green after the change (753 passed,
  25 skipped, up from 751 — the new source's two tests plus the updated
  `test_opportunity_import.py` source-count assertion, 54 -> 55
  registered sources). `pyflakes app tests` clean (no new issues).

## [2026-09-05] — Testimonials & Success Stories platform: submission wizard, moderation/verification workflow, public browsing, dashboard integration

### Added
- **Full applicant success-story ecosystem**, built as a layer on the
  existing FastAPI/SQLAlchemy backend and Flutter frontend — no parallel
  architecture, no fabricated data. See Architecture.md §10 and
  Database.md §2.15 for full technical detail.
  - **Backend**: `Testimonial`/`TestimonialModerationHistory`/
    `TestimonialReaction` models (migration `20260915_34_testimonials`,
    verified end-to-end against a real local PostgreSQL 16 instance —
    `alembic upgrade head` through the full 34-migration chain, schema
    inspected directly via `psql`, and a `downgrade -1`/`upgrade head`
    round-trip, not just reasoned about offline); Pydantic v2 schemas
    including a `display_name_for()` privacy function used by every
    public read path; a service layer handling drafts, submission,
    withdrawal, moderation transitions (approve/reject/request-changes/
    under-review/archive), verification, featuring, internal moderator
    notes, reactions, and public stats; 25 API endpoints across three
    routers split by trust level (authenticated browsing, owner-scoped
    "my testimonials", and `moderateContent`-gated admin actions) —
    authorization is re-checked server-side against the row's own
    `user_id`/role on every request, never assumed from the client.
  - **Frontend** (`lib/features/testimonials/`): a 7-step submission
    wizard (Opportunity/Experience/Profile/Privacy/Evidence/Review/
    Consent) using Flutter's built-in `Stepper` for progress/back-next,
    with autosave-as-draft; a public Success Stories browse screen with
    search/filter/pagination and an honest hero (never fabricates trust
    numbers — a stat with nothing behind it is hidden, not shown as
    zero); a long-form story detail page with the seven-question
    case-study broken into distinct sections and an outcome shown as one
    of a closed set (Applied/Shortlisted/Interviewed/Selected/Awarded/
    Admitted/Funded/Other) — never collapsed into generic "success";
    distinct verification badges (Community Story/Submitted/Under
    Review/Verified/Featured); a dashboard panel and status card
    (this app has no separate marketing homepage — the applicant
    dashboard is every signed-in user's real "home", so integration
    landed there per the spec's own "adapt to existing routing"
    instruction); and a full admin moderation dashboard plus per-story
    review screen wired into the existing moderator dashboard's
    navigation.
  - **Evidence & photos**: direct-to-Firebase-Storage uploads (never
    proxied through the backend), new `storage.rules` entries scoped by
    `{uid}` — evidence readable only by its owner plus
    moderator/administrator/superAdministrator roles, never public;
    resolved server-side through the existing generic
    `generate_download_url()` service, not a new mechanism.
  - **Anti-fraud & privacy by construction**: "submitted" and "verified"
    are independent, separately-tracked states (who verified, when, and
    by what method); internal moderator notes are never included in any
    schema a non-staff caller can reach; all free-text fields are
    sanitized via `bleach.clean(..., strip=True)` against XSS; an
    advisory-only spam heuristic (`flag_reasons()`) surfaces to
    moderators without ever auto-rejecting; every seeded demo record in
    `DemoTestimonialRepository` is prefixed `"DEMO — "` so development
    data can never be mistaken for a real applicant's story, and the
    real (API-backed) repository seeds nothing at all.
  - **Testing**: 14 new backend tests (auth/ownership/moderation
    transitions/privacy redaction/internal-notes access), full backend
    suite reverified green afterward (751 passed, 25 skipped); 7 new
    Flutter widget tests against `DemoTestimonialRepository` covering the
    public list/detail views, both dashboard states, the wizard's first
    two steps, and the moderation queue — `dart analyze`/`dart format`
    clean, `flutter test` green.
  - Deliberately not built, and why: no native share-sheet (this app's
    minimal dependency set has no `share_plus`/`url_launcher` — a
    clipboard-based "copy link" was used instead, consistent with how
    the rest of the app already handles links); no separate per-view
    analytics table (the existing `view_count` counter is proportionate
    to what this feature needs); no generic notification-system wiring
    for status changes (the dashboard status card already surfaces this
    in real time); SEO/OpenGraph phases from the original spec don't
    apply to a native Flutter app.

## [2026-09-05] — Render deployment fixes, and five new sources: Mastercard Foundation Scholars Program, Schwarzman Scholars, Knight-Hennessy Scholars, Yenching Academy, and ETH Zurich ESOP (50th–54th opportunity sources)

### Fixed
- **Render Docker build failure**: `scholarsphere_backend/Dockerfile`'s
  floating `python:3.12-slim` tag now resolves to Debian trixie, a
  codename Playwright 1.49.1 doesn't recognize — it silently fell back to
  stale Ubuntu 20.04 apt package names (`ttf-unifont`,
  `ttf-ubuntu-font-family`) that trixie's repo has since renamed,
  breaking `playwright install --with-deps chromium` on every build.
  Pinned to `python:3.12-slim-bookworm`; verified end-to-end against a
  real local Docker build (apt dependencies through the actual Chromium
  binary download), not just reasoned about.
- **CI `backend` job**: bare `pytest -q` (unlike `python -m pytest`)
  doesn't add the working directory to `sys.path`, so
  `ModuleNotFoundError: No module named 'app'` broke every backend CI run
  on this branch. Fixed by adding `pythonpath = .` to `pytest.ini`.
- **CI `validate` job**: 41 Dart files were not `dart format`-clean
  (written across sessions with no Flutter SDK available to check them
  against locally) — reformatted, mechanical whitespace-only change.
- **A real, if minor, `_PlanCard` layout bug** surfaced while fixing the
  above: the price/billing-interval `Row` overflowed by 2px at the
  ~342px card width Flutter's default test viewport produces. Fixed by
  wrapping both `Text` widgets in `Flexible` with ellipsis overflow.
  Also fixed two bugs in the test that was exercising this screen,
  found while investigating why the layout fix alone didn't turn it
  green: an off-screen tap target the test never scrolled into view, and
  a re-pumped widget that Flutter doesn't actually remount at the same
  tree location (so the test was asserting on stale, pre-checkout
  status). Neither affects the real app, which always mounts this screen
  fresh via `Navigator.push`.

### Added
- `app/services/mastercard_foundation_scholars_source.py` — the
  **Mastercard Foundation Scholars Program**, this platform's 50th
  opportunity source and its first that produces one opportunity record
  per *partner institution* (31 real institutions across Africa, North
  America, Europe, the Middle East, and Costa Rica) from a single
  foundation-run static JSON index rather than one record per
  organization. Previously investigated and left unintegrated (see
  `docs/AUTHORITATIVE_SOURCES.md`'s prior "not integrated" note) because
  the institution listing appeared to be a client-side widget with no
  server-rendered fallback; re-investigated after the foundation
  restructured its site and found the real blocker was different — the
  listing's data comes from a plain static JSON asset
  (`/assets/json/institution.json`), a normal `GET` with no JavaScript
  execution needed at all. `robots.txt` explicitly allows this project's
  crawler by name. See `docs/AUTHORITATIVE_SOURCES.md` #49 for full
  detail, including a real data-quality finding (the JSON mixes English/
  French locale duplicates in one array, filtered out) and why 31 is the
  real, verified count rather than the foundation's own broader "62
  Global partners" headline stat.
- `SchwarzmanScholarsSource` in `app/services/national_scholarship_programs.py`
  — **Schwarzman Scholars**, this platform's 51st opportunity source: a
  fully-funded one-year master's in Global Affairs at Tsinghua University,
  genuinely open worldwide with no nationality restriction. Researched
  back-to-back with United World Colleges (UWC), which was investigated
  and rejected in the same pass: UWC's `robots.txt` explicitly disallows
  `ClaudeBot` by name even though `User-agent: *` is unrestricted, and per
  this project's established precedent (see Indonesia's KNB entry) a
  named `ClaudeBot` block is treated as binding regardless of this
  backend's own actual User-Agent — not integrated, now documented in
  `docs/AUTHORITATIVE_SOURCES.md`'s "not integrated" table. Schwarzman's
  own `robots.txt` carries no such rule, so it was implemented. Notable
  finding: the admissions page states its deadline twice, once in a
  parseable full-month-name form and again in an abbreviated form the
  date parser can't read — solved by anchoring the date search on
  "countdown" instead of the default "deadline" keyword, independently
  cross-checked against the page's own JS countdown-timer epoch
  timestamp. See `docs/AUTHORITATIVE_SOURCES.md` #50 for full detail.
- `KnightHennessyScholarsSource` in
  `app/services/national_scholarship_programs.py` — **Knight-Hennessy
  Scholars**, this platform's 52nd opportunity source: Stanford
  University's fully-endowed, multidisciplinary graduate leadership
  program, genuinely open worldwide with no nationality restriction
  ("We encourage citizens and residents of all countries to apply").
  Its deadlines page's own site navigation contains an unrelated
  "Application Deadlines" menu link long before the real deadline
  sentence, defeating the default `"deadline"` search keyword's
  300-character lookahead window — solved by anchoring on `"deadline
  is"` instead, verified directly against the live page. See
  `docs/AUTHORITATIVE_SOURCES.md` #51 for full detail.
- `YenchingAcademyScholarsSource` in
  `app/services/national_scholarship_programs.py` — **Yenching Academy
  of Peking University**, this platform's 53rd opportunity source: a
  fully-funded interdisciplinary master's in China Studies, ~75%
  international student body, no country-of-origin restriction beyond
  "non-Chinese citizen with a valid passport." `robots.txt` returns a
  genuine 404 (no file exists at all, not a bot-challenge page) —
  treated as unrestricted per RFC 9309. Notable finding: the page states
  its deadline twice, but the source HTML fragments the date across
  separate `<span>` tags (evidently pasted from a word processor),
  producing a stray space before the comma once the fragments are
  joined into plain text — the shared confident-date regex correctly
  declines to match this malformed spacing, so this source honestly
  reports no deadline rather than patch a widely-shared regex to
  tolerate one page's broken markup. See
  `docs/AUTHORITATIVE_SOURCES.md` #52 for full detail.
- `EthZurichExcellenceScholarshipSource` in
  `app/services/national_scholarship_programs.py` — **ETH Zurich
  Excellence Scholarship & Opportunity Programme (ESOP)**, this
  platform's 54th opportunity source: a fully-funded Master's
  scholarship whose eligibility page never mentions nationality,
  citizenship, or country of origin anywhere. `robots.txt` returns a
  genuine 404 (no file exists at all) — treated as unrestricted per
  RFC 9309, the same reasoning as Yenching Academy. Deliberately
  extracts no deadline: the page states its one application-window
  date range only in abbreviated-month form ("Nov, 1 - Nov, 30 2026"),
  never in the full-month-name form the shared date regex requires.
  Also researched and rejected this session: the OPEC Fund (OFID)
  Scholarship Award (real, global, but its own page states the program
  is "currently restructuring" and not accepting applications) and
  International Foundation for Science research grants (the
  organization's documented domain, `ifs.se`, no longer resolves to
  IFS at all) — both newly documented in
  `docs/AUTHORITATIVE_SOURCES.md`'s "not integrated" table. See
  `docs/AUTHORITATIVE_SOURCES.md` #53 for full detail on ESOP.

---

## [2026-09-03] — Independent production audit of the Premium platform: 8 real bugs found, fixed, and regression-tested

A skeptical, from-scratch re-audit of everything built for the Premium
Application-Preparation Platform (2026-09-01 entry below) — not a
self-review, but a deliberate attempt to find what the original build
missed. Every issue below was reproduced against the real code with a
standalone script (or the real HTTP test client) before being fixed, and
re-verified afterward with a new regression test exercised through the
actual route/service, not a mock. Full details, including the exact
reproduction and verification steps, are in Task.md's matching dated
entry. **No live payment or AI provider credentials exist in this
environment** — nothing about checkout/webhook/AI-generation behavior
against a real provider has been (or could be) verified here; only the
code paths themselves.

### Fixed
- **Lost audit trail on failed AI generation.** A failed CV-polish or
  narrative-generation attempt rolled back its own `AIUsageRecord` along
  with everything else, because the failure was raised from inside the
  same `async with session.begin()` block that wrote it — an unhandled
  exception exiting that block always rolls back the *entire*
  transaction, deliberate writes included. Fixed by deferring the raise
  until after the block exits normally (`app/api/routes/
  premium_documents.py`).
- **The exact same class of bug, found independently in the refund
  path.** A `PaymentProviderError` from a failed admin refund attempt
  left no `Refund` row and no audit record — unlike `initiate_checkout`'s
  own (already-correct) failure handling in the same module. Fixed the
  same way, in both `payment_service.refund_payment` (writes a `failed`
  `Refund` row + audit record before re-raising) and the admin route
  (defers the `HTTPException` until the transaction has actually
  committed) (`app/services/payment_service.py`,
  `app/api/routes/premium_admin.py`).
- **`Content-Disposition` header injection risk.** A document's
  user-chosen `title` was interpolated directly into the export
  filename/header with no sanitization. Added `safe_export_filename()`
  to collapse anything outside a safe filename charset
  (`app/services/document_export.py`).
- **PDF export crashed on ordinary CV text.** ReportLab's `Paragraph`
  parses its text as a small XML dialect; any applicant text containing
  a bare `<`, `>`, or `&` (a GPA comparison, "A & B University", ...)
  threw an unhandled `ValueError` and broke the export entirely. Fixed by
  XML-escaping every piece of user text before it reaches `Paragraph()`
  (`app/services/document_export.py`).
- **ATS "target keyword" analysis was permanently inert.** The
  keyword-relevance component of an ATS score was wired to an always-
  empty list — no keywords were ever actually extracted from the
  workspace's target program/university or the linked opportunity. Added
  `extract_target_keywords()` and wired it into the real analysis route
  (`app/services/ats_analysis.py`, `app/api/routes/
  premium_documents.py`).
- **Entitlement authorization only ever checked the single
  most-recently-granted entitlement** — the most serious finding. A user
  who bought two feature packages (or one package, then the flagship
  plan) silently lost access to features from their *first* purchase,
  because every authorization check queried `LIMIT 1` ordered by grant
  date. This directly contradicts the platform spec's "individual
  feature packages can coexist with the flagship plan" model. Restructured
  the authorization surface end-to-end — backend (`get_active_entitlements`
  + `has_any_feature`, used by `require_entitlement` and
  `premium_documents.py`'s `_require_feature`) and Flutter
  (`PremiumStatus.entitlements`/`hasFeature()`, `PremiumFeatureGate`,
  `_PlanCard.isOwned`) — to aggregate the union of every active
  entitlement, never just the latest one
  (`app/core/entitlements.py`, `app/api/routes/premium_billing.py`,
  `app/schemas/premium_billing.py`, `lib/features/premium/`).
- **Admin-configured plan-scoped AI usage limits were silently
  unenforced.** `PUT /premium/admin/usage-limits` accepted and stored a
  `plan_code`-scoped limit row, but `check_usage_allowed` only ever
  queried the global (`plan_code IS NULL`) row — a real, dead admin
  control. Fixed to look up the caller's own active entitlements' plan
  codes and apply the most restrictive matching limit
  (`app/services/usage_limits.py`).
- **Degree-level requirement matching false-positived on ordinary
  words.** `classify_requirement`'s degree-keyword check used plain
  substring matching (`"ma " in text`), which also matches inside
  unrelated words like "diploma " or "alba " — a requirement that never
  mentions a master's or bachelor's degree could be misclassified as one.
  Fixed to match each keyword as a whole word
  (`app/services/requirement_matching.py`).

### Verified, not changed
- Full backend suite re-run clean after every fix: 724 passed, 25
  skipped (live-provider-only tests, correctly skipped without
  credentials), 0 failed.
- All touched files clean under `pyflakes`; all 125 backend modules
  import cleanly; the FastAPI app builds its OpenAPI schema (231 routes)
  without error — the closest thing to a "production build" check this
  stack has (no live payment/AI credentials, and no Flutter SDK, exist
  in this environment to go further).
- Re-audited database migrations against every current model definition
  by hand — no drift found. Re-audited every premium/application-
  preparation route for IDOR (ownership checks on every workspace/
  document/background-entry access) and admin-role gating — no gaps
  found.
- The missing Flutter document-builder screens (CV/SOP/checklist/
  readiness/ATS UI) noted in the 2026-09-01 entry are still not built.
  This was re-confirmed, not newly discovered — it remains an honestly
  documented, deliberate gap (no Flutter SDK in this environment to
  compile/verify new UI against), not a hidden one.

---

## [2026-09-01] — Premium Application-Preparation Platform (backend complete, Flutter landing/checkout slice)

A full Premium tier integrated into ScholarSphere's existing architecture
rather than a separate project: application-strategy/requirement-matching/
readiness-scoring, a CV builder with deterministic (never AI-fabricated)
content assembly and optional AI wording polish, SOP/study-plan/research-
proposal/fellowship document builders with strictly grounded AI
generation, ATS analysis, document versioning, PDF/DOCX export, and a
provider-independent payment system with real (though not yet
credentialed) Stripe integration. See Task.md's matching dated entry for
the full breakdown, including two real concurrency/transaction bugs found
and fixed during the build.

### Added
- `app/services/payment_provider.py` — `PaymentProvider` interface;
  `NullPaymentProvider` (default, never fabricates a successful
  transaction); `StripePaymentProvider` (real Payment Intents/Refunds/
  Subscriptions integration + Stripe's documented webhook-signature
  algorithm, HMAC-SHA256 with replay-window protection).
- `app/services/payment_service.py` — checkout, server-side verification,
  idempotent webhook processing (two independent DB uniqueness
  constraints), refunds with entitlement revocation, hash-chained audit
  logging via the existing `append_audit_record`.
- `app/services/ai_provider.py` — `AIProvider` interface;
  `NullAIProvider` (default); real `OpenAIProvider`/`AnthropicProvider`
  adapters, request shape verified against each provider's documented
  API.
- `app/services/document_generation.py` — deterministic CV assembly from
  real `ApplicantBackgroundEntry` data (new: education/work_experience/
  project/publication/award/leadership_community/skill/reference, one
  consolidated table); grounded AI narrative generation for SOP/personal
  statement/motivation letter/study plan/research proposal/fellowship
  essays, with a system prompt that explicitly forbids inventing any
  fact.
- `app/services/requirement_matching.py`, `readiness_score.py`,
  `ats_analysis.py` — deterministic, rule-based, AI-independent; readiness
  score's weights are fully documented and returned with every response;
  ATS score always carries an explicit "does not guarantee acceptance"
  disclaimer.
- `app/services/category_workflow.py` — a single registry mapping all 9
  required applicant categories to their document/checklist workflow, not
  branching logic scattered through routes.
- `app/services/document_versioning.py`, `document_export.py` — append-
  only version history; ATS-compatible PDF (`reportlab`) and DOCX
  (`python-docx`) export by construction (single-column, no tables/
  images).
- `app/services/usage_limits.py`, `premium_plan_seed.py`.
- 14 new database tables across `app/models/premium_billing.py`,
  `application_preparation.py`, `applicant_background.py`,
  `premium_documents.py`; one migration
  (`alembic/versions/20260901_33_premium.py`). See Database.md §2.14.
- New routes: `applicant_background.py`, `application_preparation.py`,
  `premium_billing.py`, `premium_documents.py`, `premium_admin.py`,
  `premium_webhooks.py` — all wired into `app/main.py`, including a
  startup seed of the flagship "Complete Premium Application Package"
  plan.
- `app/core/entitlements.py` — `require_entitlement()`, a
  database-backed route dependency mirroring `require_roles`/
  `require_permissions`, never a JWT-cached claim.
- `PAYMENT_*`/`AI_*`/`PREMIUM_*` settings in `app/core/config.py` and
  `.env.example`, all optional-to-boot with a clear "not configured"
  failure mode rather than a fabricated success.
- `lib/features/premium/` — domain models, `ApiPremiumRepository`/
  `DemoPremiumRepository`, `PremiumFeatureGate` (reusable locked-feature
  widget), `PremiumLandingScreen` (real pricing/checkout, wired into
  `app.dart` and a new applicant-dashboard sidebar entry). The individual
  document-builder screens are not yet built - see Task.md.
- 50 new backend tests, including every "Critical test" named in the
  platform spec by name (free user denied, paid user allowed, expired
  entitlement denied, failed payment creates no entitlement, duplicate
  webhook creates no duplicate entitlement). Full backend suite confirmed
  green: **737/737** (`pytest -q`, up from 687). `pip-audit`: no known
  vulnerabilities in the two new dependencies.

### Fixed
- A route raising `HTTPException` *inside* `async with session.begin()`
  was silently rolling back a deliberately-persisted `failed`-status
  `Payment` row (an unhandled exception always rolls back the whole
  block) - `premium_billing.py::checkout` now captures the error and
  re-raises it after the block commits.
- `require_entitlement`'s FastAPI dependency reading the database before
  the route body opened its own explicit transaction was colliding with
  that transaction (SQLAlchemy's "autobegin"); fixed by closing the
  dependency's own transaction immediately after checking the feature -
  and specifically checking it *before* that rollback, since rollback
  expires already-loaded ORM attributes and a later read would otherwise
  trigger an illegal lazy-load outside the async greenlet context. This
  would have affected every real production request through an
  entitlement-gated route, not just this session's tests.
- `app/core/http_client.py` — added a small, backward-compatible
  `timeout_seconds` override to `post_json`/`get_json` so AI-generation
  calls can use a longer budget without bypassing the shared HTTP client.

## [2026-08-30] — Added UAEU Scholarships, Fellowships, and Graduate Assistantships

Closes the United Arab Emirates line item in the country registry
(previously `NO_RELIABLE_SOURCE_FOUND` at the national-government level)
and this project's first genuinely `UNIVERSITY`-typed source.

### Added
- `UaeuScholarshipsSource` in new `uaeu_scholarships_source.py` - reads
  UAEU's own College of Graduate Studies scholarships page, a real,
  server-rendered, `robots.txt`-unrestricted page. Extracts all 13 real
  accordion-item programmes (fellowships, assistantships, department PhD
  studentships), deliberately unfiltered by nationality eligibility -
  matching this project's standing "AI's role: none, today" policy.
  Wired end-to-end, including the new `"university"` `source_type` value
  on the existing free-text source-type column.
- 3 new tests against a real fixture captured unmodified from the fetch.
  Full backend suite confirmed green: **687/687** (`pytest -q`, up from
  684).

### Changed
- `tests/test_opportunity_import.py`'s hardcoded source count/set
  updated for the new source (48 → 49).

One real fragility recorded honestly: the page's Tailwind accordion
widget is reused site-wide for both navigation and this scholarships
content (27 accordion items total, only 13 of them real programmes) -
correctly scoped via a CMS-id-prefix selector (`[id^="faqs-section"]`)
rather than the widget's own CSS class.

## [2026-08-29] — Browser-rendering fallback for JavaScript-only scraper sources

Added an opt-in headless-browser (Playwright/Chromium) rendering fallback
for scraper sources whose pages return no usable content over plain
HTTP - requested explicitly after this session's own research had already
hit several genuinely JS-only government sites (Egypt's Study-in-Egypt
portal, Indonesia's `.go.id` KNB site) that a plain HTTP fetch cannot
extract anything from.

### Added
- `app/services/browser_rendering.py`: a lazily-launched, reused headless
  Chromium instance; one isolated context/page per fetch, always closed;
  a semaphore bounding concurrent renders; bounded timeouts throughout
  (never a fixed `sleep()`); a response-size cap matching the existing
  HTTP path; known bot-challenge/CAPTCHA signature detection that raises
  immediately rather than attempting to solve or bypass anything - the
  same policy as every prior anti-bot finding in this project.
- `web_scraper_base.py`: a `looks_javascript_rendered()` heuristic and a
  new opt-in `WebScraperSource.allow_browser_rendering` flag, default
  `False` for every existing source - zero behavior change for all 43
  sources already in this registry. Plain HTTP is always tried first;
  only an opted-in source whose response the heuristic flags gets a
  browser-render retry, and any render failure falls back to the thin
  HTTP response rather than crashing the source's sync task.
- `Dockerfile` now installs Playwright's Chromium (`playwright install
  --with-deps chromium`) - a real, documented tradeoff of roughly
  +300-400MB on every image built from it (api, worker, and beat alike),
  noted as a candidate for a future `Dockerfile.worker` split if that
  becomes a real problem. CI installs the same browser so the real-
  browser tests actually run there too.
- New settings: `browser_render_timeout_ms`, `browser_render_max_concurrency`,
  `browser_executable_path` (left unset in every real deployment).

### Changed
- `app/core/http_client.py`: renamed the private `_validate_url` to
  public `validate_https_url` so both the HTTP and browser paths share
  one HTTPS-only check.

### Deliberately not built
SPA click-through navigation (filters, "Load more," infinite scroll),
reverse-engineering a site's own internal JSON/GraphQL API, a persisted
per-domain "rendering capability profile," and multi-language
deduplication - all premature generality with zero current users; see
`docs/AUTHORITATIVE_SOURCES.md`'s new "Browser-rendering fallback"
section for the full reasoning.

No existing source was converted to use this - all 43 already work over
plain HTTP - and the two live JS-only candidates already on record
(Egypt, Indonesia) were deliberately **not** flipped to
`allow_browser_rendering = True` and marked working: this session's own
sandboxed dev environment could launch a real headless Chromium (proven
against a local self-signed-HTTPS test server) but every attempt to
navigate it to a real external HTTPS site failed at the TLS layer through
the sandbox's own egress proxy - a sandbox limitation, not a defect in
the new module. Both country-registry entries were updated with this
exact finding.

Verified: 11 new tests (`tests/test_browser_rendering.py`), including a
genuine, non-mocked real headless-Chromium-launch-plus-JavaScript-
execution-plus-DOM-extraction test. Full backend suite: **586/586**
(`pytest -q`, up from 575). `pip-audit`: no known vulnerabilities in the
new `playwright` dependency.

## [2026-08-30] — Added Erasmus Mundus Joint Masters Catalogue

Continuing the "multiple source types per country" gap. The second real
production consumer of `pagination_engine.paginate_by_url` after
EducationUSA, independently proving that engine generalizes across
genuinely different real sites.

### Added
- `ErasmusMundusJointMastersSource` in new `erasmus_mundus_source.py` -
  ~220 EU-funded joint master's programmes, genuinely open worldwide by
  nationality, real server-rendered `?page=N` listing built with the
  EU's own ECL design system. No browser rendering needed. Wired
  end-to-end.
- 5 new tests against three real fixture pages (page 0, page 1, and a
  genuinely-past-the-last-page response). Full backend suite confirmed
  green: **684/684** (`pytest -q`, up from 679).

### Changed
- `tests/test_opportunity_import.py`'s hardcoded source count/set
  updated for the new source.

A real, live-observed proof of this project's HTTPS-only discipline:
two of the ~220 programmes' own listed websites use plain `http://`
rather than `https://` and are correctly, silently dropped by the
shared HTTPS-only check rather than "fixed" by guessing a scheme -
confirmed directly in the real fixtures.

## [2026-08-30] — Added Rotary Peace Fellowships

Continuing the "multiple source types per country" gap. Researched (but
did not integrate) the Aga Khan Foundation International Scholarship
Programme - real and legitimate, but its own published country list
does not include Sierra Leone, rejected on eligibility grounds. Then
researched and implemented Rotary Peace Fellowships instead - genuinely
open worldwide, real static content.

### Added
- `RotaryPeaceFellowshipSource` in `national_scholarship_programs.py` -
  real, worldwide (no nationality restriction), static server-rendered
  content. `robots.txt`-compliant `Crawl-delay: 10` respected via a
  source-specific 10-second minimum request interval. Wired end-to-end.
- 2 new tests against a real fixture captured unmodified from the fetch.
  Full backend suite confirmed green: **679/679** (`pytest -q`, up from 677).

### Changed
- `tests/test_opportunity_import.py`'s hardcoded source count/set
  updated for the new source.

One fragility recorded honestly rather than silently risked: the page
has no semantic content wrapper, only Tailwind utility-class
combinations, so the description selector is more brittle than most
sources here - verified working today, documented in both the source's
own docstring and `docs/AUTHORITATIVE_SOURCES.md`.

## [2026-08-30] — Added Joint Japan/World Bank Graduate Scholarship Program (JJ/WBGSP)

Continuing the "multiple source types per country" gap from the previous
pass. Implemented a real next candidate found while researching sources
genuinely eligible for Sierra Leone applicants.

### Added
- `WorldBankJJWBGSPScholarshipSource` in `national_scholarship_programs.py`
  - a real, major World Bank Group program (funded by the Government of
    Japan), not tied to a single destination country. Sierra Leone is
    confirmed on the programme's own published eligible-countries list,
    checked directly rather than assumed. Its overview page is real
    static server-rendered HTML - no browser rendering needed, unlike
    the Mastercard Foundation candidate from the previous pass. Wired
    end-to-end; this is the source registry's first
    `international_organization`-typed entry.
- 1 new test against a real fixture captured unmodified from the fetch.
  Full backend suite confirmed green: **677/677** (`pytest -q`, up from 676).

### Changed
- `tests/test_opportunity_import.py`'s hardcoded source count/set
  updated for the new source.

Also re-tested `sl.usembassy.gov/educational-professional-exchanges/`
(Sierra Leone's US Embassy exchanges page) - still a persistent
"Technical Difficulties" error, not fixed since the original Fulbright
research flagged it.

## [2026-08-30] — Research pass: Mastercard Foundation Scholars Program (not integrated)

Investigated as a candidate FOUNDATION-type source directly relevant to
Sierra Leone (58,000+ scholarships committed, 62 partner universities
across Africa; `robots.txt` explicitly allows `ClaudeBot`). Not
integrated: the program overview has no single deadline/application
(decentralized to partner institutions, same reason Canada/Denmark/Wales
were rejected), and the real per-institution listing page is a
client-side widget with no server-rendered fallback. Live-tested
Chromium against the exact URL to reconfirm this sandbox's standing
external-browser-automation limitation rather than assuming it still
applies. Documented as a strong candidate for a future session with
working outbound browser access. No code changes.

## [2026-08-29] — 40-country audit: United States and China closed, Eswatini reachability fixed

Cross-referenced the platform's exact 40-country target list against
`docs/COUNTRY_PROVIDER_REGISTRY.md` (already thorough from prior
sessions — 38 of 40 already had a real, live-tested classification).
Closed the two that had never been researched, and fixed one real bug
found while re-checking.

### Added
- `app/services/educationusa_source.py` — a new United States source:
  `educationusa.state.gov/find-financial-aid` (US Department of State),
  a real, live, plain-HTTPS paginated database of 277+
  institution-specific scholarships. The first production consumer of
  `app/services/pagination_engine.py`'s `paginate_by_url`. Wired
  end-to-end (config, source registry, Celery beat + task,
  opportunity_sync mapping) and verified against 3 genuinely separate
  real fetches (page 0, page 1, and a real `?page=40` zero-row
  "past the last page" response), all saved as test fixtures.

### Changed
- `eswatini_slas_base_url` corrected from `https://www.slas.gov.sz`
  (still times out) to `https://slas.gov.sz` (bare host, genuinely
  reachable — 200, real content, 3/3 attempts). The real page turned out
  to be a domestic student-loan portal with no scholarship/SADC content,
  so `EswatiniSlasSource` correctly still extracts zero records from it
  — reclassified `NOT_SUITABLE` rather than claimed newly working.
- `tests/test_opportunity_import.py`'s hardcoded source count/set
  updated for the new source; two real-Chromium new-tab-detection tests
  given a longer timeout after being found genuinely flaky under
  full-suite system load (not a production bug).

### Deliberately not touched
China: the China Scholarship Council (CSC) is a real, major program, but
every candidate page — including `robots.txt` itself — returns HTTP 412
or an obfuscated JS anti-bot challenge page, the same class of
protection as Cyprus/Brazil. Classified `BLOCKED`, never bypassed.

The remaining 35 (of 40) countries already had defensible research on
record and were not re-litigated without new information. The spec's
"multiple source types per country" ambition (university + government +
embassy + foundation sources for every country) remains a real, larger
gap beyond one session's scope — most countries here have exactly one
flagship government source today.

Verified: 6 new tests. Full backend suite confirmed green: **676/676**
(`pytest -q`, up from 670).

## [2026-08-29] — Hybrid Scholarship Discovery and Verification Engine: the rest of the spec

A continuation of the browser-rendering fallback above, building out the
remaining requirements from the 27-section hybrid-discovery-engine
specification: SPA interaction, pagination, infinite scroll, filters,
application-link discovery and validation, cookie/consent handling,
console/page-error monitoring, content-completeness scoring, source
capability profiling, metrics, and a declarative adapter architecture.
Additive throughout - none of the 43 existing scraper sources changed
behavior or was migrated onto any of the new engines.

### Added
- `app/services/browser_interaction.py` (`BrowserInteractionEngine`):
  click/wait-for-selector/extract-URL/capture-content primitives, plus
  `wait_for_navigation_or_change`, racing a new tab, a URL change
  (including a client-side `history.pushState` route), or an in-page DOM
  change under a bounded timeout - never `sleep()`. New
  `browser_rendering.interactive_session` context manager for anything
  needing more than one render.
- `app/services/pagination_engine.py`: `paginate_by_url` (URL-parameter
  pagination, no browser needed) and `paginate_by_click` (one function
  handling both a "Next" button and a "Load More" control via
  deduplication-by-key). Bounded by new `MAX_PAGES_PER_SOURCE`/
  `MAX_RECORDS_PER_SOURCE` settings.
- `app/services/infinite_scroll_engine.py`: render/extract/scroll/wait-
  for-real-DOM-growth/compare/continue, bounded by new
  `MAX_SCROLL_ITERATIONS`/`SCROLL_STAGNATION_LIMIT` settings.
- `app/services/filter_engine.py`: applies a caller-described filter set
  (auto-detecting `<select>` vs. a clickable control; an absent selector
  is skipped, never an error) and `iter_filter_combinations`, a bounded
  cartesian product generator - never an automatic full sweep.
- `app/services/application_link_discovery.py`: finds "Apply"-style
  controls, reads `href` directly where present, and for a control
  without one, clicks through and records where that led (new tab / URL
  change / in-page modal). Bounded to 5 href-less clicks per page. Never
  fills in a form, creates an account, or submits anything.
- `app/services/application_link_validation.py`: classifies a discovered
  application URL `VALID_OFFICIAL_APPLICATION` /
  `VALID_AUTHORIZED_EXTERNAL_PORTAL` / `INFORMATION_PAGE_ONLY` / `BROKEN`
  / `BLOCKED` / `UNKNOWN` by HTTP status, redirect chain, final domain,
  and content - only the source's own domain or a pre-authorized portal
  domain can ever come back `VALID_*`.
- `app/services/content_completeness.py`: scores a scraper adapter's raw
  extracted fields 0-100 across CRITICAL/IMPORTANT/OPTIONAL tiers, run
  before attempting to construct a `NormalizedExternalOpportunity`;
  `needs_review` is forced True whenever any CRITICAL field is missing
  regardless of score.
- `app/services/source_capability_profile.py`: in-process (not
  persisted) memory of what's been observed about a domain - requires
  JS, pagination shape, cookie banner, etc. - recorded automatically by
  every module above. Deliberately observability, not automation:
  nothing reconfigures a source's own fetch behavior from this evidence
  alone.
- `app/services/scraper_metrics.py` (process-wide counters + derived
  ratios; an untouched ratio reads `None`/`null`, never a fabricated
  `0.0`) and `GET /api/v1/scraper-metrics`
  (`app/api/routes/scraper_metrics.py`, staff-gated).
- `app/services/scraper_adapters.py`: `GenericHTMLAdapter`/
  `GenericJSAdapter`/`GovernmentPortalAdapter`/`UniversityPortalAdapter`/
  `SPAAdapter` base classes for a future declaratively-describable
  source - none of the 43 existing sources migrated.
- New settings: `PLAYWRIGHT_HEADLESS` (forced `true` in production),
  `AUTO_ACCEPT_REQUIRED_COOKIES`, `MAX_PAGES_PER_SOURCE`,
  `MAX_RECORDS_PER_SOURCE`, `MAX_SCROLL_ITERATIONS`,
  `SCROLL_STAGNATION_LIMIT`.

### Changed
- `app/services/browser_rendering.py`: added generic cookie/consent-
  banner detection and (only within a detected cookie/consent container,
  never page-wide) auto-accept, and structured console-error/page-error/
  failed-request/HTTP-error capture classified INFO/WARNING/ERROR/
  CRITICAL - a known third-party analytics/tracker failure is downgraded,
  never used to fail an otherwise-good render.

### Deliberately not built
Reverse-engineering a site's own internal JSON/GraphQL API (no JS-only
candidate on record has one) and multi-language deduplication - both
premature generality with zero current users. See
`docs/AUTHORITATIVE_SOURCES.md`'s requirement matrix for the full
per-requirement status.

Still not independently verified against a real external site - same
sandbox limitation as the original browser-rendering fallback (the
egress proxy fails at the TLS layer for real Chromium navigation to
external HTTPS sites). Every new module is proven against real Chromium
and purpose-built local mock pages, which proves the Playwright
mechanics genuinely work, not what a concrete adapter for a real site
like Egypt or Indonesia would need to configure. Docker also remains
unbuildable in this sandbox (daemon not running).

Verified: 84 new tests across 12 new test files plus additions to
`tests/test_browser_rendering.py` (11 more there). Full backend suite
confirmed green after every phase; final count **670/670** (`pytest -q`,
up from 586).

## [2026-08-29] — Second beyond-the-original-request pass: 8 more countries researched, zero new sources — an honest null result

A second batch of 8 countries entirely outside the original
master-prompt request: New Zealand, Singapore, Pakistan, Philippines,
Nigeria, Ghana, Rwanda, Jordan. Unlike every prior pass, **this one adds
no new sources** — recorded here in full because a real, honest research
outcome, not a gap:

- **New Zealand**: Manaaki New Zealand Scholarships is real and
  well-documented, but the entire site is built with Next.js CSS
  Modules — every wrapper down to the `<h1>`'s immediate parent uses an
  auto-generated hashed class, and even the generic `<main>` tag is
  non-unique with the wrong element first. No selector is safe from
  breaking on the next deploy.
- **Singapore**: SINGA no longer has a dedicated program page (every
  guessed/search-suggested URL 404s, confirmed against the site's full
  sitemap.xml); the one current offering is institution-initiated, not
  individually-applicable, the same shape already ruled out for Canada.
- **Pakistan**: HEC's domain fails TLS certificate verification on
  every hostname tried — the same class of finding as India ICCR and
  South Africa NRF.
- **Philippines**: CHED's official site returns 403 Forbidden, 3/3
  attempts.
- **Nigeria, Ghana, Rwanda**: each national scholarship body turned out
  to be outbound/domestic-only — no program was found funding foreign
  nationals to study in-country.
- **Jordan**: a real, genuinely bidirectional inbound mechanism exists
  across 25 partner countries, but the actual page content is only two
  sentences plus a country list — no funding, deadline, or application
  detail — the same thin-content bar that already ruled out Colombia's
  reciprocity page and Malaysia's MIS.

No code changes this round — nothing was implementable, so no source
classes, tests, or fixtures were added. `docs/COUNTRY_PROVIDER_REGISTRY.md`
updated with a new dedicated section recording all 8 findings.

Country coverage unchanged at 31 real sources — this pass added negative
findings only, which still have value: future sessions won't re-research
these 8 countries from scratch.

## [2026-08-29] — Beyond the original request: 8 new countries researched; Hungary and Mexico added

With every country/region named in the original master-prompt request
researched, this pass picked 8 new countries entirely outside that
request, spanning previously-untouched regions: Hungary, Mexico,
Indonesia, Malaysia, Vietnam, Egypt, Israel, Kenya. 2 real sources added:

- **Hungary** (Stipendium Hungaricum): a heavily JS-rendered site with
  no semantic heading markup at all and a `<title>` tag that only ever
  yields the single word "About" once split — falls back to a title
  formatted from `external_id`. `funding_type = "fully_funded"` —
  explicit tuition-free education plus real HUF/EUR monthly stipend
  figures.
- **Mexico** (AMEXCID Excellence Scholarships): content scoped to the
  article-body column specifically, not `main` (which also pulls in an
  unrelated news sidebar). `funding_type = None` — the overview page
  explicitly defers all concrete funding/deadline terms to a separate
  "Condiciones Generales" document not linked as plain HTML.

The other 6 were investigated and found unsuitable, for genuinely
varied reasons: **Indonesia** `BLOCKED` (official site is a pure JS app
with zero server-rendered content; a content-rich companion site
explicitly disallows `ClaudeBot` by name in its `robots.txt`, honored
rather than routed around with a different User-Agent). **Vietnam**
`BLOCKED` (the one candidate site doesn't support HTTPS at all — this
backend's HTTPS-only requirement is a security boundary, never relaxed
for one adapter). **Egypt** `BLOCKED` (official portal is a pure
client-side JS SPA on every route checked). **Israel** `BLOCKED` (MFA
scholarship page returns 403 on 3/3 attempts). **Malaysia**
`NOT_SUITABLE` (real program, but the page is too thin — real detail
lives only in an unparsed PDF). **Kenya** `NO_RELIABLE_SOURCE_FOUND`
(the one page found is an outbound-opportunity database, not an inbound
single program).

Source count 41 → 43. `docs/AUTHORITATIVE_SOURCES.md` (#42-#43) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` (new dedicated "Beyond the original
request" section covering all 8 findings) fully updated.

Verified: 4 new tests (2 per source) against real fixtures; full backend
suite **575/575** (`pytest -q`).

31 countries/regions now have at least one real source (up from 29),
including 2 entirely outside the original master-prompt request.

## [2026-08-29] — Europe: first research pass on the last 8 named countries; 5 sources added — no named region left unresearched

A dedicated **first** research pass on the eight remaining named European
countries from the original master-prompt request — the last
unresearched region. 5 real sources added:

- **Switzerland** (SBFI ESKAS): `funding_type = "partial_funding"` — a
  concrete monthly amount (CHF 2450) is stated but tuition coverage is
  never mentioned.
- **Poland** (NAWA "Poland My First Choice"): hidden accessibility
  `<h1 class="sr-only">` before the real `<h1 class="header">` — the
  same bug class as India ICCR and Colombia ICETEX.
- **Czech Republic** (MŠMT Government Scholarships): a headless
  Next.js-over-WordPress build whose React wrapper divs carry
  auto-generated `id="S:N"` streaming-boundary ids — deliberately not
  used as a selector; scoped instead to `.global-msmt`, a real custom
  class. Unusually, `deadline_keywords` is **left at the base class's
  default** rather than disabled — this page has a genuine, singular,
  cleanly extractable deadline ("by 30 September 2026 at the latest"),
  confirmed directly against the real fixture. The first source in this
  whole initiative where deadline extraction is actually used.
- **Serbia** ("World in Serbia"): no `<h1>` — the page's only heading is
  a plain `<h2>Scholarships</h2>`. `funding_type = "fully_funded"` —
  explicit free tuition, accommodation, food, monthly allowance, and
  health insurance.
- **Romania** (MFA Government Scholarships): a genuinely interesting
  deadline-extraction near-miss — the page states a real, parseable
  deadline ("31 March 2026") but the shared date-extraction function
  only searches after a keyword's *first* occurrence, and this page's
  first "deadline" mention is an unrelated, dateless one earlier in the
  eligibility section — confirmed directly against the real fixture that
  extraction correctly (if unluckily) returns nothing.

**Croatia** was investigated and found `NOT_SUITABLE`: every source is a
year-dated "Call for Applications" page (seven different such pages
found spanning 2020/2021 through 2026/2027), no evergreen "about" page,
plus nomination-only eligibility. **Norway** came back
`NO_RELIABLE_SOURCE_FOUND`: its two historical inbound programs (the
"Quota Scheme" and NORSTIP) are both confirmed defunct/cancelled.
**Finland** was found `NOT_SUITABLE`: its one national program (EDUFI
Fellowship) states on its own official page that it "will end at the end
of 2025. New applications cannot be submitted after 17.10.2025" —
already past by this session's date, despite several third-party
aggregators still listing it as "active in 2026" (exactly why this
project verifies against primary sources).

Source count 37 → 41. `docs/AUTHORITATIVE_SOURCES.md` (#37-#41) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` (new dedicated "Europe" section
covering all 8 findings) fully updated.

Verified: 10 new tests (2 per source) against real fixtures; full backend
suite **571/571** (`pytest -q`).

29 of the master prompt's ~40 named countries/regions now have at least
one real source (up from 24). **No named country or region from the
original master-prompt request remains unresearched** — South America,
the remaining named Asian countries, and the remaining named European
countries have each now had a full first-pass research effort.

## [2026-08-29] — Asia: first research pass on South Korea, Saudi Arabia, Qatar, Thailand; 3 sources added

A dedicated **first** research pass on the four remaining named Asian
countries from the master prompt (China and India already had narrower
coverage). 3 real sources added:

- **South Korea** (GKS Global Korea Scholarship Program, run by NIIED):
  the page's only `<h1>` is the site logo, not a title — solved with
  `<h2 class="title">GKS (Global Korea Scholarship) Program</h2>`, the
  first of two matches (the second is a sibling "Other Scholarships"
  tab). Content scoped to `#gks-tab1`, confirmed to hold only the GKS
  section.
- **Saudi Arabia** (MOE Government University Scholarships): no `<h1>`,
  and the `<title>` tag interleaves Arabic and English with the real
  text in the second segment — since `title_tag_separator` only
  supports the first segment, this source falls back to a title
  formatted from `external_id` rather than mis-extracting the Arabic
  half or special-casing the shared base class.
- **Qatar** (Qatar Scholarships, run by the Qatar Fund For
  Development/QFFD): the homepage is a JS-rendered SPA serving only an
  empty "offline" shell to a non-JS client — used `/en-US/Programs`
  instead, a server-rendered route with real content. `robots.txt` uses
  the newer "content-signal" convention but sets no actual value for
  any use — documented explicitly as a genuine absence of restriction.

All three follow this initiative's established honesty discipline:
`funding_type = None` wherever the page bundles sub-programs with
conflicting funding coverage (Saudi Arabia's three explicit tiers,
Qatar's partner institutions with differing tuition coverage), kept at
`fully_funded` only where genuinely supported (South Korea's explicit
"Airfare, language training costs, tuition, and study allowances").

**Thailand** was investigated and found `NOT_SUITABLE`, not implemented:
the government's real scholarship info lives in a rolling year-dated
announcement feed (`ops.go.th`), and a second candidate "about" page
(TICA's own TIPP overview) was real but frozen content from ~2013-2015,
not the current cycle.

Source count 34 → 37. `docs/AUTHORITATIVE_SOURCES.md` (#34-#36) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` (new dedicated "Asia" section
covering all 4 findings) fully updated.

Verified: 6 new tests (2 per source) against real fixtures; full backend
suite **561/561** (`pytest -q`).

24 of the master prompt's ~40 named countries/regions now have at least
one real source (up from 21). The only remaining unresearched territory:
the remaining named European countries (Switzerland, Poland, Czech
Republic, Croatia, Serbia, Romania, Norway, Finland).

## [2026-08-29] — South America: first research pass across all 9 countries; Colombia, Chile, Peru added

A dedicated **first** research pass on South America — none of its 9
countries had any prior research in this registry. 3 real sources added:

- **Colombia** (ICETEX Beca Colombia Extranjeros): the site (Liferay) has
  a hidden accessibility `<h1 class="hide-accessible">Navegación</h1>`
  before the real content (the same bug class already documented for
  India ICCR) and reuses one `.journal-content-article` class for 8+
  unrelated blocks, including a "Historial" accordion holding the three
  *previous* application cycles. Solved with the one stable, unique
  anchor Liferay stamps on the actual article content:
  `[data-analytics-asset-title='Beca Colombia Extranjeros']`. A thinner
  companion page and an unrelated governance-notice sub-page were both
  fetched and rejected first.
- **Chile** (AGCID Becas para Extranjeros): a single unique `<h1>` and
  `<article>`, but the article bundles several distinct
  bilateral/regional sub-programs with materially conflicting funding
  formulas, plus the page's own disclaimer that terms are
  reference-only pending each call's official republication — the same
  multi-program shape already handled honestly for South Africa NRF,
  the Netherlands, and Spain AECID.
- **Peru** (PRONABEC Beca Alianza del Pacífico): a reciprocal
  student-mobility program among the four Pacific Alliance member
  states — Peru offers 50 inbound slots for Chilean/Colombian/Mexican
  nationals specifically, the same honest bilateral-partner pattern as
  Portugal Camões. No `<h1>` at all — title falls back to the `<title>`
  tag split on the en dash.

All three follow this initiative's established honesty discipline:
`deadline_keywords = ()` wherever the real deadline is stated but in a
numeric or non-English-month form the shared parser cannot recognize
(`DD/MM/YYYY`, Spanish month names), and `funding_type` left `None` or
set to `"partial_funding"` rather than guessed wherever the page's own
funding language is absent, conflicting, or incomplete.

**Brazil** was investigated and found genuinely `BLOCKED`, not
implemented: the real program (PEC-G) has rich real content confirmed
via a browser-spoofed `curl` fetch, but this backend's actual unspoofed
httpx client is served a JavaScript bot-challenge page 3/3 attempts —
the same class of finding as Cyprus's Azure WAF block, and bypassing it
is out of scope by the same policy. **Argentina, Uruguay, Paraguay**
confirmed `NOT_SUITABLE` (a multi-entry database instead of a single
page, or residency-restricted eligibility not open to prospective
international applicants). **Ecuador, Bolivia** came back
`NO_RELIABLE_SOURCE_FOUND`.

Source count 31 → 34. `docs/AUTHORITATIVE_SOURCES.md` (#31-#33) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` (new dedicated "South America"
section covering all 9 findings) fully updated.

Verified: 6 new tests (2 per source) against real fixtures; full backend
suite **555/555** (`pytest -q`).

21 of the master prompt's ~40 named countries/regions now have at least
one real source (up from 18). Remaining unresearched territory: most of
Asia (South Korea, Saudi Arabia, Qatar, Thailand) and the remaining named
European countries (Switzerland, Poland, Czech Republic, Croatia, Serbia,
Romania, Norway, Finland).

## [2026-08-29] — Portugal (Camões) source added — the country-registry queue is now empty

Portugal was the last country this registry had queued from the original
research pass. Neither the "Bolsas do Camões, I.P." hub nor its "Bolsas
da Cooperação" child (both fetched and confirmed to be thin, content-free
navigation pages) were used — this adapter targets the specific
"Formação em Portugal" leaf page instead, with real substantial content:
9 named eligible partner countries and a real funding table with actual
euro amounts (a maintenance subsidy, a tuition subsidy up to
€1,306.25–2,612.50/year, a housing subsidy, and an installation subsidy).

Unlike Belgium/Austria/Morocco earlier in this same research initiative,
`funding_type = "fully_funded"` **is** kept here — genuinely supported by
that funding table, the same reasoning already applied to Japan's MEXT
Scholarship. `deadline_keywords = ()` — embassy-mediated applications,
same pattern as Japan MEXT and Morocco AMCI.

Source count 30 → 31. `docs/AUTHORITATIVE_SOURCES.md` (#30) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` fully updated. **The queue this
registry has tracked since 2026-08-23 is now genuinely empty**: every
candidate it ever identified is either a real, live-verified source or a
confirmed, evidence-backed non-candidate (`NOT_SUITABLE`, `BLOCKED`, or
`NO_RELIABLE_SOURCE_FOUND`) — none left as stale guesses.

Verified: 2 new tests against a real fixture; full backend suite
**549/549** (`pytest -q`).

18 of the master prompt's ~40 named countries/regions now have at least
one real source (up from 17). The only way to add more from here is a
first research pass on countries entirely outside this registry — all of
South America, most of Asia, and most of the remaining named European
countries have not been touched at all.

## [2026-08-29] — A real research pass: Belgium, France, Austria, Morocco added; Canada, Denmark confirmed unsuitable

A dedicated research pass — not a fetch-and-wire pass — on the remaining
queue: Belgium (ARES), Canada (EduCanada), France (Campus France),
Austria (OeAD), Morocco (AMCI/"Maroc Alumni"), and Denmark's
long-standing "needs a dedicated follow-up search" item. 4 of 6 turned
into real, live-verified sources; 2 were confirmed genuinely unsuitable
rather than left as stale guesses.

**Belgium (ARES)** targets the specific "Bourses de formations
internationales" sub-page (a real, currently-open call), not the general
mobility-grants hub, which links to ~8 unrelated instruments. Its real
deadline ("18.09.2026") is deliberately not extracted — that's
`DD.MM.YYYY` numeric form, which the shared date regex in
`app/services/parsing.py` doesn't match by design; extending that regex
is a cross-cutting change out of scope for one adapter.

**France (Campus France Eiffel)** is a genuinely clean single-flagship
page with a real, parseable deadline ("January 8, 2026") that *is*
extracted. Institution-mediated applications, confirmed to be the same
standard shape as DAAD/Japan MEXT (already implemented) by directly
reading the page, not assumed.

**Austria (OeAD Ernst Mach Grant)** follows the same multi-program-hub
shape as South Africa NRF/Spain AECID — 6 named sub-grants, each with its
own deadline and, for one, its own distinct monthly amount — `deadline_
keywords = ()` deliberately.

**Morocco (AMCI)** resolves the prior uncertainty about "Maroc Alumni"'s
canonical URL: the real official page is `amci.ma/cooperation-academique`.
Embassy-mediated, same honest null-deadline pattern as Japan MEXT.

**Canada — confirmed NOT_SUITABLE, not implemented.** Live-fetched
EduCanada's actual pages: its broadest international-applicant program
(Study in Canada Scholarships) states outright "Only Canadian
post-secondary institutions are eligible to apply on this call... Direct
applications from individuals are not accepted" — no path for an
individual applicant to initiate anything, unlike France's Eiffel
program. Corrected from a vague "needs deeper research" note to a
specific, evidence-backed finding.

**Denmark — confirmed NOT_SUITABLE, not implemented.** The dedicated
follow-up search this entry itself called for was done: Danish
government scholarships are "administered by the Danish universities,
who each select the students" — genuinely decentralized, no single
national awarding body. Corrected from "no reliable source found"
(implying more searching might help) to a confirmed structural fact.

No monetary/"fully funded" language was found on any of the 4 new
sources' actual pages, so `funding_type = None` on all four — not
guessed from general reputation.

Source count 26 → 30. `docs/AUTHORITATIVE_SOURCES.md` (#26-#29) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` fully updated (all 6 countries'
entries corrected with what was actually found; only Portugal remains as
a genuine queued candidate).

Verified: 8 new tests against real fixture HTML, all passing on the
first run; full backend suite **547/547** (`pytest -q`).

17 of the master prompt's ~40 named countries/regions now have at least
one real source (up from 13). South America, most of Asia, and most of
the remaining named European countries remain completely unresearched.

## [2026-08-29] — Japan (MEXT Scholarship) source added; Wales corrected to NOT_SUITABLE

Continued the country-coverage queue with Wales and Japan — but only one
turned into a new source.

**Wales — a real finding, not a new source.** Live-testing the page the
registry's prior `READY_FOR_AUTOMATION` classification was based on
(`/global-wales-postgraduate-scholarship`) found it now 404s (real "Page
not found" content, not a bot block). The site's current replacement page
states the program is no longer centrally administered — it now points
to each of eight Welsh universities' own scholarship pages individually,
plus to Chevening and Commonwealth Scholarships (both already separate
sources here). Corroborated by an independent third-party note that the
program's 2024 round has closed. The prior classification was never
live-tested before being written down — corrected in
`docs/COUNTRY_PROVIDER_REGISTRY.md` to `NOT_SUITABLE` with the finding
documented in place, rather than either silently building a source
against a defunct program or quietly leaving the stale classification for
a future session to trip over. Same discipline as the India ICCR
dual-`<h1>` bug and the corrected Firebase bundle-ID note earlier in this
project's history.

**Japan (MEXT Scholarship) — implemented, fully live-verified.** Targets
the MEXT-specific sub-page of the official "Study in Japan" government
portal, not its thin navigation hub. `deadline_keywords = ()` —
applications are embassy/university-mediated with no single global
deadline, the same honest pattern as Ireland GOI-IES and Sweden SI.
Unlike Australia Awards, `funding_type = "fully_funded"` is kept here and
is actually confirmed by the page's own text ("tuition exempted", a
monthly stipend, "round-trip travel expenses (airfare) provided"), not
guessed. `title_selectors = ()` since every page in this site section
shares the same generic `<h1>Scholarships</h1>`; the real title comes
from the `<title>` tag split on the site's own fullwidth vertical bar
(`｜`, U+FF5C, not the ASCII `|`).

Source count 25 → 26. Docs updated: `docs/AUTHORITATIVE_SOURCES.md` #25,
`docs/COUNTRY_PROVIDER_REGISTRY.md` (Japan moved to implemented; Wales
corrected in place; coverage summary, totals, and recommended-next-
candidates list all updated). Every previously `READY_FOR_AUTOMATION`
candidate in the registry is now either implemented or corrected — the
10 remaining researched countries all genuinely need a second research
pass, not just a fetch-and-wire pass.

Verified: 3 new tests against real fixture HTML; full backend suite
**539/539** (`pytest -q`).

13 of the master prompt's ~40 named countries/regions now have at least
one real source (up from 12). South America, most of Asia, and most of
the remaining named European countries remain completely unresearched.

## [2026-08-29] — Two more country sources: Spain (AECID) and Australia (DFAT Awards)

Continued the master-prompt country-coverage initiative with the top two
`READY_FOR_AUTOMATION` candidates in `docs/COUNTRY_PROVIDER_REGISTRY.md`
— same live-verification discipline as every prior source (fetched via
both `curl` and this backend's actual httpx path, `robots.txt` checked,
real HTML captured as test fixtures, never written from assumption).

**Spain (AECID)** — live-verified cleanly. Deliberately targets AECID's
specific international-applicant sub-page ("Becas para ciudadanos de
países de América Latina, África y Asia"), not its generic scholarships
hub, which mostly serves Spanish nationals and is irrelevant to this
platform. `deadline_keywords = ()`, same reasoning as South Africa NRF
and the Netherlands: the page lists several named sub-programs, each with
its own distinct closing date. `funding_type = "partial_funding"` — no
"fully funded" language found on the page.

**Australia (DFAT Awards)** — partially live-verified. The overview site
(`australiaawards.com.au`) is fully reachable; the authoritative deadline
page (`dfat.gov.au`) is not — every attempt (multiple user agents, `curl`
and httpx) hung at the TLS-handshake stage until timeout, the same
"connects, then nothing responds" pattern already documented for Sierra
Leone's MTHE, not a WAF challenge. `deadline_path` left unset rather than
pointed at an unverified host. `funding_type = None` — no
funding-coverage language was found on the reachable pages; Australia
Awards are widely known to be comprehensively funded in practice, but
that's outside knowledge the adapter's own source text doesn't support
asserting.

Source count 23 → 25. `docs/AUTHORITATIVE_SOURCES.md` (#23-#24) and
`docs/COUNTRY_PROVIDER_REGISTRY.md` updated (both moved out of
"researched, not implemented"; Wales, Japan, and Canada are now the top
queued candidates).

Verified: 5 new tests against real fixture HTML; full backend suite
**536/536** (`pytest -q`).

**Still a small fraction of the original master prompt's ~40 named
countries/regions**: 12 now have at least one real source (up from 10).
South America (9 countries), most of Asia, and most of the remaining
named European countries remain completely unresearched — not silently
dropped, just not attempted this pass.

## [2026-08-29] — Free-hosting-tier deployment prep for the backend (Render + Neon + Upstash)

Researched the current (2026) free-tier landscape before picking a stack
— prior knowledge here goes stale fast: Render's own free Postgres now
expires after 30 days, Fly.io no longer has a real free tier at all, and
Railway removed its free tier back in 2023. Landed on **Render** (web
service) + **Neon** (Postgres — its free tier is explicitly permanent,
unlike Render's) + **Upstash** (Redis — also a permanent free tier,
500K commands/month, standard `rediss://` protocol).

New `render.yaml` Blueprint at the repo root defines the
`scholarsphere-backend` web service (Docker, free plan, `/health/ready`
health check); every credential-shaped env var
(`DATABASE_URL`/`REDIS_URL`/`FIREBASE_PROJECT_ID`/
`FIREBASE_CREDENTIALS_JSON_BASE64`/`ALLOWED_ORIGINS`) is `sync: false` so
nothing gets committed — set via the Render dashboard instead.

New `scholarsphere_backend/docker-entrypoint.sh`: optionally decodes a
base64-encoded Firebase service-account JSON to a real file (portable
across any host, not tied to a platform-specific secret-file feature),
optionally runs `alembic upgrade head` on boot (`RUN_MIGRATIONS_ON_BOOT`,
since Render's free plan has no separate release-phase step), then execs
uvicorn bound to `$PORT` — previously hardcoded to 8000, which would have
made the service unreachable on Render (it injects its own `$PORT`).
`Dockerfile` now uses this as `CMD` (deliberately not `ENTRYPOINT`, which
would have broken `docker-compose.yml`'s worker/beat services that
override the container's command entirely).

`scholarsphere_backend/README.md` gained a full "Deploying to a free
hosting tier" walkthrough with the reasoning above and step-by-step Neon/
Upstash/Firebase/Render setup instructions.

**Real, documented gap:** Render's free plan has no Background Worker or
Cron Job service type (Cron Jobs need a paid plan, $1/month/job minimum),
so the 22 scheduled Celery tasks in `opportunity_sync.py` have no
equivalently free always-on host today. The API itself works fully
without them — only the *scheduled* background jobs (source syncs,
link-health checks, reverification, notifications) don't run for free.
Not worked around by restructuring the scheduling architecture, which was
out of scope for this change.

**Not built or deployed** — no Docker daemon available in this
environment (client only) and no Neon/Upstash/Render accounts exist for
this project from here. `docker-entrypoint.sh` passed shell syntax
validation and `render.yaml` passed YAML well-formedness validation;
neither was exercised against a real build or a real Render deploy.
Verify on the first real deploy attempt.

## [2026-08-29] — GitHub Pages deployment workflow for the Flutter web build

New `.github/workflows/deploy-pages.yml`: builds `flutter build web
--release` with `--base-href "/${{ github.event.repository.name }}/"`
(required so asset URLs resolve correctly once served from a GitHub
Pages project site's `/scholarsphere/` subpath rather than root — the
app's navigation is in-memory, a single `MaterialApp`/`NavigatorKey` with
no `GoRouter`/path-based routes, so no server-side rewrite rules are
needed beyond that), adds `.nojekyll` and an `index.html` -> `404.html`
fallback, then deploys via the official `actions/upload-pages-artifact` +
`actions/deploy-pages` actions. Triggers on push to `main` touching
`lib/`, `web/`, `assets/`, `pubspec.{yaml,lock}`, or the workflow itself,
plus manual `workflow_dispatch`.

Also updated `.env.example`'s CORS section with the exact origin format
needed once a GitHub Pages deployment exists.

**Four real, unavoidable manual steps this alone does not satisfy** (the
workflow's own comments and `.env.example` document each, rather than
silently assuming they're done):
1. Enable Pages with source "GitHub Actions" in repo Settings → Pages —
   confirmed not yet done (`ecotraces.github.io/scholarsphere/` 404s
   today).
2. Deploy `scholarsphere_backend/` somewhere publicly reachable over
   HTTPS and set its URL as the `SCHOLARSPHERE_API_BASE_URL` repo Actions
   variable — it's a compile-time `--dart-define`, baked into the JS
   bundle; left unset, the deployed site falls back to
   `http://localhost:8000/api/v1`, unreachable from a visitor's browser.
   This backend is not deployed anywhere today.
3. Add the Pages origin to that backend's `ALLOWED_ORIGINS`, or its API
   calls are blocked by CORS.
4. Add the Pages origin to Firebase Console's Authorized domains, or
   Google Sign-In's redirect/popup flow won't work from it — console-only,
   same category as this project's existing bundle-ID/Google-Sign-In
   items.

Not run end-to-end — no live GitHub Actions execution or Pages
environment available from this session. The workflow YAML was validated
for well-formedness; verify the actual deploy on the first real push to
`main`.

## [2026-08-29] — Link-health monitoring, Netherlands (Nuffic) source, admin discovery-summary endpoint

Response to a "global scholarship discovery/verification" master-prompt
initiative: audited the existing discovery pipeline first (it already
implements most of the spec — official/application-URL separation, a hard
verification gate, deduplication, confidence scoring, append-only change
history, a scheduled Celery-beat loop with bounded retries, a 22-country
research inventory), then closed three concrete, testable gaps rather than
attempting all of it or every named country at once.

**Link-health monitoring.** New `ExternalOpportunity.link_checked_at`
column (migration `20260914_32`), `app/services/link_health.py`, and
`app.tasks.opportunity_sync.check_link_health` (daily, bounded to 100
published+verified opportunities per run, oldest/never-checked first). An
unreachable link demotes `verified` → `reverification_required`, logs a
`VerificationHistory` entry, and flips
`VerificationReview.application_link_checked = False` — mirrors
`detect_expired_opportunities`'s existing pattern; never deletes the
opportunity or its stored link. 6 new tests.

**Netherlands (Nuffic NL Scholarship).** The top `READY_FOR_AUTOMATION`
candidate in `docs/COUNTRY_PROVIDER_REGISTRY.md`. Live-verified through
this backend's actual httpx path (not just `curl` — see the India-ICCR/
South-Africa-NRF TLS-chain lesson already in this codebase): 200, real
HTML. `hollandscholarship.nl` (the program's old public name/domain)
301-redirects to `studyinnl.org/finances/nl-scholarship`, confirmed
current by the page's own `<title>`. Two honesty choices forced by the
page's own text: `funding_type = "partial_funding"` (page states outright
this is not a full-tuition scholarship) and `deadline_keywords = ()` (the
page says closing dates are set per participating institution, not by
Nuffic itself — same reasoning already applied to South Africa NRF). 3 new
tests against a real fixture; source count 22 → 23.
`docs/AUTHORITATIVE_SOURCES.md` and `docs/COUNTRY_PROVIDER_REGISTRY.md`
updated.

**Admin discovery-summary endpoint.** New
`GET /external-opportunities/discovery-summary` (`DiscoverySummary`
schema) fills the one real admin-visibility gap found in the audit:
source totals/active/recent-errors, opportunity totals by publication
status, duplicate-review backlog, an opportunities-by-country breakdown,
and never-link-checked/broken-links counts from the task above. 4 new
tests. Flutter: added `LiveDiscoverySummary` +
`ApiVerificationRepository.getDiscoverySummary()` (data layer only,
mirroring `getSummary()`'s existing pattern) — deliberately did **not**
wire this into the 884–1151-line dashboard screens, since this
environment has no Flutter SDK to compile or run against and a blind edit
at that size isn't a responsible bet.

Verified: 13 new backend tests; full backend suite **531/531** (`pytest
-q`). Flutter data-layer addition not compiled or run — no SDK available
here.

**Left genuinely open**, not silently dropped: the ~10 other
`READY_FOR_AUTOMATION` countries already queued in the registry, every
country outside that inventory the initiative named, true live-search-
driven multilingual discovery (recommended to keep this system's proven
one-adapter-per-researched-source pattern instead, given the real
anti-bot/ToS walls already hit), a manual review queue UI, and the admin
dashboard's actual UI wiring.

## [2026-08-29] — Dependabot alert investigation: stale nginx base image bumped, uuid CVE note corrected

Investigated the 11 Dependabot alerts (3 high, 4 moderate, 4 low) GitHub
reported on the default branch. This session's tooling has no `gh` CLI, no
Dependabot-alerts MCP tool, and no authenticated access to the Security
tab, so the exact CVE IDs could not be read directly. Instead, every
dependency manifest in the repo was audited against public advisory
databases: `pip-audit` (backend), `npm audit --json` including dev
dependencies (Cloud Functions), and an OSV.dev batch query over all 73
pub.dev-hosted packages in `pubspec.lock` (ecosystem name `Pub` confirmed
against OSV's own ecosystem list) — **all three came back with zero
findings**. Android's Gradle files declare no explicit dependency
versions (delegated to the Flutter Gradle plugin), and there is no
`Podfile.lock` or `Gemfile`, so those aren't a source either.

That leaves this repo's three Docker base images as the only remaining
Dependabot-tracked ecosystem, and the likely real source (11 OS-package
findings is a typical count for a stale Alpine/Debian base). Couldn't run
a scanner directly (no Docker daemon in this environment, and fetching a
third-party tool like Trivy from GitHub releases is blocked by this
session's repo-scoping proxy), but direct registry inspection confirmed
`nginx:1.27-alpine` (root `Dockerfile`) was three stable-branch releases
behind current — bumped to **`nginx:1.30-alpine`**, verified via registry
digest comparison to be the exact same image nginx's own `stable-alpine`
tag currently resolves to. `python:3.12-slim` and
`ghcr.io/cirruslabs/flutter:stable` are both already floating tags that
pick up the latest patched image on next build, so left unchanged.

Also corrected a stale `Task.md` note along the way: the moderate `uuid`
CVE (GHSA-w5hq-g745-h8pq) once tracked as blocked on Cloud Functions'
`firebase-admin` is already resolved — `functions/node_modules/uuid` is
`14.0.1`, past every fixed threshold (11.1.1/12.0.1/13.0.1 depending on
major line) in OSV's own advisory record, confirmed by both the OSV
lookup and a clean `npm audit`. No code change was needed there, only the
stale tracking note.

**Not verified against the actual alert list or count** — this is
reasoning from public advisory data, not a read of GitHub's own Dependabot
report. Re-check the Security tab once this lands (and once the next
scheduled image rebuild picks up the two floating tags) to confirm the
count actually drops before treating this as closed.

## [2026-08-29] — Differential Storage access for provider-granted applicant documents

Closed the `Task.md` Backend Tasks gap where a provider granted access to an
applicant's document (`ApplicantDocument.shared_with_provider_ids`, set via
`POST /applicant-documents/{id}/share`) was still denied at the Storage
layer, because `storage.rules` scopes `applicant-documents/` to owner-only
and that never changed. Rather than widen the Storage rule (which would
remove the backend as an auditable choke point), providers now read shared
files through two new backend-issued routes instead:

- `GET /applicant-documents/{id}/download-url` — mints a short-lived (15
  minute), v4 signed Storage URL via the Firebase Admin SDK, for the
  document's owner or a provider whose `Provider.id` appears in
  `shared_with_provider_ids`. Everyone else gets 404 (matching this
  router's existing owner-scoped convention of not distinguishing "not
  found" from "not yours"). Signing failures (no credentials configured)
  surface honestly as 503, never a fabricated URL.
- `GET /applicant-documents/shared-with-me` — provider-facing listing of
  documents shared with any `Provider` record the caller owns. Deliberately
  omits `storage_path`; only the download-url route above may read it.

New `app/services/document_storage.py` wraps the Admin SDK call so it can be
monkeypatched in tests, matching `app/services/firebase_users.py`'s
established pattern. Firebase app initialization
(`app/core/auth.py::initialize_firebase`) now also passes `storageBucket`
(new `Settings.firebase_storage_bucket`, defaulting to the same
`scholarsphere-d44f5.firebasestorage.app` already used in
`lib/firebase_options.dart`) — previously unset, which is why signed URLs
were never possible before. `storage.rules` and the affected route
docstrings updated to describe the new arrangement instead of the old
"not-yet-built follow-up" note.

Verified: 7 new tests in `tests/test_applicant_documents_route.py` (owner
access, unrelated applicant denied, ungranted provider denied on both
routes, granted provider allowed on both routes and correctly scoped to
their own `Provider` record, signing-failure 503, non-provider role sees an
empty shared list rather than an error). Full backend suite **518/518**
(`pytest -q`). Flutter suite not touched, not re-run this session — no
Flutter files changed; the client-side "download a shared document" UI for
providers is not part of this change.

## [2026-08-22] — Security review, Firebase officer roster, audit-read endpoint, notification-delivery honesty fix

Independent security review of the applications/verification/providers/
provider_opportunities backends (`Task.md` Critical Task), the Firebase
verification-officer roster gap (`Task.md` Critical Task), and three
backlog items were inspected, fixed where real gaps were found, tested, and
verified. Full backend suite re-run and passing after every change:
**448/448 (`pytest -q`).** Flutter suite not touched, not re-run this
session — no Flutter files changed.

### Fixed
- **Security review of applications/verification/providers/
  provider_opportunities — 4 real gaps found and fixed, 0 IDOR/auth-bypass
  found.** `providers.py`'s administrator/review/suspension/appeal
  mutations had no audit trail (added `append_audit()` calls);
  `add_administrator` stored raw wire-format permission strings instead of
  the model's enum values, silently breaking any permission check against
  them (added `permission_from_wire()` conversion); `submit_opportunity`
  checked only org-level publish rights, not the calling administrator's
  own granted permissions, so any administrator on a publish-enabled
  organization could submit opportunities regardless of their individual
  grants (added `_submitter_permission_check()`); `ProviderReviewRequest
  .decision` accepted an unconstrained string instead of the real 3-value
  set (restricted to a `Literal`). Files: `app/api/routes/providers.py`,
  `app/api/routes/provider_opportunities.py`, `app/schemas/provider.py`.
- **Firebase verification-officer roster gap.** Reverification reminders
  previously targeted officers found only via `ImportAuditLog` activity
  history, so a brand-new officer with zero prior decisions received no
  reminders. New `app/services/firebase_users.py` enumerates all Firebase
  users through the Admin SDK's real pagination mechanism, filters by the
  `role` custom claim in application code (there is no server-side
  "query by custom claim" API — confirmed against the installed SDK), and
  falls back to the audit-log heuristic if enumeration fails. File:
  `app/tasks/opportunity_sync.py`.
- **Notification-delivery honesty bug.** `process_due_notifications`
  marked `email`/`push` notifications "delivered" even though no
  SMTP/ESP or FCM/APNs provider is integrated anywhere in this backend —
  a fabricated success on the two channels most notifications actually
  use (both are in the default `NotificationPreferences.channels`).
  Restricted `_CONFIGURED_CHANNELS` to `{"in_app"}`; notifications with no
  deliverable channel now honestly report `failed` instead. File:
  `app/services/notification_dispatch.py`.

### Added
- **Security Officer read access to `ImportAuditLog`.**
  `securityAdministrator`/`administrator`/`superAdministrator` could read
  the separate `AuditRecord` trail but had no read access to
  `ImportAuditLog`, which actually covers the opportunity-verification and
  provider-lifecycle pipeline. Added `GET /audit/import-records` with
  filtering and pagination, gated on the same roles as every other route
  in `audit.py`. Files: `app/api/routes/audit.py`, `app/schemas/
  audit_log.py`.

### Reviewed, no change needed
- USAJOBS live smoke test — blocked, no `USAJOBS_API_KEY` in this
  environment; mocked coverage (`tests/test_usajobs.py`) is the strongest
  test available here.
- Differential Storage access for provider-granted applicant documents —
  re-confirmed the current state fails *safe* (a granted provider is wrongly
  denied the file, not the reverse), so left as a scoped follow-up rather
  than an unplanned feature build; see `Task.md`.
- The four dead-code domain areas (`eligibility_rules`, `integrations`,
  `data_transfer`, `platforms`) — re-confirmed still accurate as
  **DECISION REQUIRED**, a product decision rather than an engineering one.

---

## [2026-08-22] — Web-scraper source tier and confidence-triage queue signal

Requested as an autonomous-discovery/publication initiative; two decisions
were confirmed with the user before implementation rather than assumed:
keep the mandatory human-verification gate for every source (add
confidence *triage*, not auto-publish), and scrape only specific named
organizations approved individually. Full backend suite re-run and passing
after every change: **483/483 (`pytest -q`)**, up from 448.

### Added
- **Five new opportunity sources via a new web-scraper adapter tier**
  (`app/services/web_scraper_base.py`) — Commonwealth Scholarships (CSC
  UK), Chevening Scholarships, DAAD Scholarship Database (curated seed-id
  list, coverage caveat below), Chinese Embassy in Sierra Leone
  (scholarship announcements), and Sierra Leone's Ministry of Technical
  and Higher Education (government scholarship announcements, including
  partner-government offers such as Russia's). None of these
  organizations publish an official API, RSS feed, or dataset — see
  `docs/AUTHORITATIVE_SOURCES.md` #8-#12 for the per-source research and
  robots.txt/terms check performed before each was added. Every scraped
  record goes through the identical mandatory verification/publication
  pipeline as an API source (`NormalizedExternalOpportunity` enforces
  `pending`/`unpublished` at the schema level regardless of source).
  Fulbright was researched and deliberately not integrated (decentralized
  per-country administration, no single official listing) — see the
  declined-sources table in `docs/AUTHORITATIVE_SOURCES.md`.
- **`app/core/http_client.py::get_html`** — HTML fetch with the same
  HTTPS-only, timeout, response-size-cap, and bounded-retry protections
  `get_json`/`post_json` already had.
- **`app/services/verification_confidence.py`** — a deterministic,
  fully-explained (not AI/ML) confidence scorer wired into
  `GET /external-opportunities/pending-verification?sort=confidence`,
  exposing `confidence_level`/`confidence_reasons` on each queue item as a
  triage priority hint only. It has no path to set `verification_status`
  or `publication_status`; every record still requires an officer's
  explicit `approved` decision regardless of score.
- **`extract_confident_date`/`extract_confident_date_after`**
  (`app/services/parsing.py`) — sets a scraped deadline only when an
  explicit day+month+year date literal is present in the source text;
  confirmed against real prose from both DAAD and CSC UK that states a
  closing date without an adjacent year, which is correctly left `null`
  rather than guessed ("never invent data").
- 5 new `OpportunitySource` registry rows (`trust_level="web_scraped"`)
  and 5 new daily Celery beat entries.
- 34 new tests: `tests/test_cscuk_scholarships.py`, `test_chevening.py`,
  `test_daad_scholarships.py`, `test_embassy_announcements.py`,
  `test_verification_confidence.py`, new `get_html` cases in
  `test_http_client.py`, a new confidence-field case in
  `test_verification_actions.py`. Real HTML fetched from the live sites on
  2026-08-22 backs 4 of the 5 new adapters' tests
  (`tests/fixtures/*.html`); the fifth (`mthe_sierra_leone`) uses a
  clearly-labeled synthetic fixture — see "Reviewed, no change needed"
  below.
- **Live end-to-end verification.** With no Celery broker available in
  this environment, `app/tasks/opportunity_sync._run_source_sync` (the
  exact function every Celery task here calls) was invoked directly
  against a temporary database for all 5 new sources with no HTTP
  mocking, against the real live sites: `cscuk_scholarships` 6/6 created,
  `chevening` 1/1 (deadline correctly parsed, `2026-10-06`),
  `daad_scholarships` 6/6, `china_embassy_sl` 2/2, `mthe_sierra_leone` 0/0
  with a clean non-fatal error (confirming its connectivity blocker fails
  gracefully rather than crashing the sync).

### Fixed
- **`china_embassy_sl` deadline mis-extraction, found by the live run
  above.** A "Farewell Ceremony" article's publish date was picked up as
  if it were an application deadline, because deadline extraction took
  the first date literal anywhere in the article body with no context
  check. Fixed by anchoring on a nearby deadline-indicating keyword
  (`_DEADLINE_KEYWORDS` in `app/services/embassy_announcements.py`,
  matching the pattern already used for `cscuk_scholarships`/
  `daad_scholarships`); re-ran live and confirmed both real articles now
  correctly report `deadline=None`. Regression test added using the real
  HTML that caught it
  (`tests/test_embassy_announcements.py::test_china_embassy_unrelated_date_is_not_mistaken_for_a_deadline`).
  Full backend suite after the fix: **483/483**.
- `pip-audit -r requirements.txt`: no known vulnerabilities, including the
  new `beautifulsoup4` dependency.

### Changed
- `docs/AUTHORITATIVE_SOURCES.md`, `docs/OPPORTUNITY_VERIFICATION_SYSTEM.md`
  (new §6 on confidence triage; §7-§11 renumbered accordingly, with every
  internal cross-reference to the old numbering updated),
  `docs/PRODUCTION_SECURITY_AUDIT.md` §2.6 (dated update note appended;
  original finding preserved rather than rewritten), `docs/
  SECURITY_MODEL.md` (fixed a now-stale §9→§10 cross-reference),
  `scholarsphere_backend/README.md` all updated to describe the new
  architecture accurately.
- `tests/test_opportunity_import.py::test_source_seeding_is_idempotent`
  updated for the new source count (8 → 13).

### Reviewed, no change needed
- `mthe_sierra_leone`'s live-site smoke test — **blocked**:
  `https://www.mthe.gov.sl` and `http://www.mthe.gov.sl` both refused
  every connection attempted from this environment (2026-08-22, multiple
  attempts). Looks like a network/hosting issue outside this codebase's
  control, not confirmed either way. The adapter is implemented and
  tested against a synthetic fixture only — not claimed as live-verified.
  See `Task.md` Integration Tasks.

---

## [2026-08-23] — Global country-coverage expansion (WMI + 9 new sources, 23-country research inventory)

Requested: expand opportunity discovery to 23 target countries/regions plus
WMI, following the existing architecture with quality prioritized over
quantity. Full research pass across all 24 targets first (see the new
`docs/COUNTRY_PROVIDER_REGISTRY.md`), then implementation on the strongest
candidates, in two batches. Full backend suite after both batches:
**511/511 (`pytest -q`)**, up from 494. Nothing in this entry has been
committed - left for explicit review.

**Batch 2 (follow-up, same day)**: implemented the three next-recommended
candidates - Italy (MAECI), Greece (IKY), South Africa (NRF). 2 of 3
live-verified (Italy, Greece - both real syncs against the real sites);
South Africa is implemented but live-blocked by the same failure class as
India ICCR below (a real, reproducible `SSLCertVerificationError` on
NRF's own server - confirmed by two separate attempts, ruling out a
one-off fluke). New shared-architecture addition:
`_SingleProgramSource` gained an overridable `_deadline_base_url()`
method, since Italy's overview page and its deadline/call-status page are
on two different hosts - the first source needing that. South Africa's
adapter deliberately never attempts deadline extraction
(`deadline_keywords = ()`) - the real page publishes a table of distinct
closing dates per study level/sub-programme, and a generic
keyword-anchored extractor would have picked one row and mislabeled it as
*the* deadline. 14 new tests
(`tests/test_national_scholarship_programs.py`). See
`docs/AUTHORITATIVE_SOURCES.md` #19-#21, `docs/COUNTRY_PROVIDER_REGISTRY.md`.

### Added
- **6 new opportunity sources**: Wells Mountain Initiative (WMI) Scholars
  Program, Türkiye Bursları (Turkey), Government of Ireland GOI-IES,
  ICCR Scholarship Programme (India), Swedish Institute Scholarships for
  Global Professionals (Sweden), Eswatini SLAS. See
  `docs/AUTHORITATIVE_SOURCES.md` #13-#18. 4 of 6 live-verified (WMI,
  Turkey, Ireland, Sweden - real syncs against the real sites, real
  opportunities created); 2 implemented but live-blocked by documented
  external issues, not falsely claimed working (see "Fixed" below and
  Task.md for full detail).
- **`app/services/national_scholarship_programs.py`** - a new shared
  `_SingleProgramSource` base for the common shape of "one government or
  quasi-governmental body's single recurring scholarship program,"
  generalizing the pattern `chevening.py` established, used by 5 of the 6
  new sources.
- **`docs/COUNTRY_PROVIDER_REGISTRY.md`** - a full research inventory
  across all 24 targets: 7 with an integrated provider (5 supported, 2
  partially - see above), 14 with a credible official candidate
  identified and classified (`READY_FOR_AUTOMATION` /
  `REQUIRES_CURATED_SOURCE`) but not yet built, 2 with no reliable single
  source found (Denmark, UAE), 1 actively blocked by anti-bot protection
  and deliberately not pursued further (Cyprus - Azure WAF JS challenge).
- 25 new tests: `tests/test_national_scholarship_programs.py`, additions
  to `tests/test_embassy_announcements.py` (Eswatini SLAS).

### Fixed
- **Two real title-extraction bugs, found by live/fixture testing.**
  India ICCR's page has two `<h1>` elements - a generic Drupal
  page-title chrome element and the real content heading nested inside
  `.field--name-body` - so a naive `select_one("h1")` silently grabbed
  the wrong one. WMI and Ireland have *no* usable `<h1>` at all
  (page-builder/custom-theme pages); both original tests passed anyway
  because they never asserted on the actual title text, silently masking
  a fallback-only result. Fixed by adding a `title_tag_separator`
  fallback (extract from `<title>`, split on a real separator character)
  and adding title assertions to the tests so this class of bug can't
  hide again.
- **India ICCR: real TLS certificate-chain issue on the server,
  correctly not worked around.** `curl` succeeds against `iccr.gov.in`,
  but this backend's actual HTTP path (httpx + certifi's default trust
  store) fails with `SSLCertVerificationError: unable to get local
  issuer certificate` - the server isn't sending a complete certificate
  chain; `curl`/Windows SChannel tolerates this, strict OpenSSL/certifi
  verification does not. Deliberately **not** patched around with
  `verify=False` - that would remove real TLS security for a problem
  that's actually on ICCR's end to fix.

### Reviewed, no change needed
- SSRF/link-following review of the new source: `national_scholarship_programs.py`
  never follows a scraped link (every fetch target is a hardcoded class
  attribute, not discovered from page content), so it has no SSRF
  surface at all; `EswatiniSlasSource` inherits the same-host-only fix
  already applied to the embassy-announcement pattern (see the previous
  entry below).
- Eswatini SLAS live connectivity: reconfirmed the same network-timeout
  pattern already documented for Sierra Leone's MTHE - not resolved,
  not fabricated as fixed.

---

## [2026-08-23] — Production-readiness hardening: startup validation, corrected Firebase/MTHE findings, SSRF fix

A follow-up hardening pass over the previous increment's already-committed
work (`6747e20`), continuing rather than repeating it. Full backend suite
re-run and passing after every change: **494/494 (`pytest -q`)**, up from
483. Nothing in this entry has been committed - left for explicit review.

### Added
- **Startup-time Firebase credential validation** for production
  (`app/main.py::ensure_firebase_ready_in_production`, called from the
  app's `lifespan`) - Firebase Admin SDK init was previously lazy (first
  authenticated request only), so a bad credential would have surfaced as
  a confusing runtime failure instead of a clear deploy-time one.
  `app/core/config.py` also now refuses to start in production if
  `FIREBASE_CREDENTIALS_PATH` is set but the file doesn't exist. 6 new
  tests (`tests/test_startup_validation.py`).
- `.env.example` rewritten to list every setting the codebase actually
  reads (including the 5 web-scraper sources, previously missing),
  labeled by when each is really required.
- A real Celery task-interface test (`task_always_eager`, exercising
  `sync_cscuk_scholarships.apply(...)` rather than calling the underlying
  function directly), an idempotency test (same `task_id` re-run creates
  no duplicate history/opportunity), and cross-cutting scraper resilience
  tests (malformed HTML, simulated full layout change, missing-title
  fallback) - see `tests/test_opportunity_tasks.py`,
  `tests/test_scraper_resilience.py`.

### Fixed
- **SSRF-adjacent gap in the embassy-announcement adapter.**
  `app/services/embassy_announcements.py`'s link discovery filtered only
  by visible link text, not by the link's target host - a link on an
  otherwise-trusted page could point anywhere and would still be fetched.
  Added `same_host_https_url` (`app/services/web_scraper_base.py`) and
  switched this adapter to it. Regression test:
  `tests/test_scraper_resilience.py::test_discovered_links_to_a_different_host_are_never_followed`.
- **Pre-existing test-isolation bug**:
  `test_all_scheduled_task_names_resolve` only passed as part of the full
  suite (it silently relied on another test file having already imported
  `app.tasks.notifications`); failed when run alone. Not a production
  bug - a real worker loads every `include=[...]` module at startup - but
  a real test-determinism bug. Fixed by calling
  `celery_app.loader.import_default_modules()` explicitly in the test.

### Corrected (documentation, not code)
- **Firebase "old bundle ID" blocker.** Direct inspection of every config
  file (`build.gradle`, `google-services.json`, the Xcode project,
  `firebase_options.dart`) found `com.scholarsphere.app` used
  consistently everywhere - no mismatch. The real, more specific gap
  found instead: `ios/Runner/GoogleService-Info.plist` doesn't exist, and
  `Info.plist` has no Google Sign-In URL scheme. Android additionally
  needs its OAuth client's SHA-1/SHA-256 fingerprint verified against
  whichever keystore signs the build - not checkable from this
  environment. Live Google Sign-In was not tested. See `Task.md`.
- **MTHE connectivity.** Re-diagnosed precisely: DNS resolves fine
  (`www.mthe.gov.sl` → `38.145.202.15`); every TCP connection (port 80,
  port 443) and even ICMP ping times out with no response - a different
  and more specific finding than "connection refused." No official
  RSS/API/alternative source found. See `Task.md`.

### Reviewed, no change needed
- `pip-audit -r requirements.txt`: re-confirmed no known vulnerabilities.
- Fulbright: re-confirmed unsupported; no new official source found.
- Source-management and pending-verification endpoint authorization:
  confirmed unchanged and still correctly gated (`admin_access`/
  `preview_access`).

---

## [2026-08-21] — Real backend fixes: search index, verification dashboard, reverification reminders, document-sharing consent

Four wiring/completeness gaps identified in `Task.md`'s Critical Tasks were
inspected, fixed, tested, and verified against the running code (not
assumed). Full test suites re-run and passing after every change:
**431/431 backend (`pytest -q`), 88/88 Flutter (`flutter test`),
`flutter analyze` clean.**

### Fixed
- **Search index fed from fake data.** `lib/app/app.dart`'s
  `searchIndexUpdate` background-job handler read from
  `DemoOpportunityRepository` while writing to the real
  `ApiSearchIndexRepository`. Root cause was worse than a stale read:
  `POST /search-index/rebuild` prunes the entire shared index and
  re-validates every incoming id against real `external_opportunities`
  rows before keeping it, so demo ids were silently rejected — every
  rebuild was leaving the real, shared search index **empty**. Fixed by
  reading from `_apiOpportunityRepository` instead. The separate
  `expiredOpportunityDetection` client-side job was removed (not
  re-pointed): the real backend already performs this daily,
  authoritatively, via Celery beat, and the client has no
  server-authoritative way to mutate verification status (see
  `Architecture.md` decision 9). Regression-tested end-to-end
  (`test/widget_test.dart`, drives the real admin "process queued jobs"
  UI flow and asserts real backend data reaches `rebuild()`).
- **Verification Officer dashboard showed fabricated metrics.** The
  dashboard's landing panels read `assignedToUserId`,
  `VerificationWorkflowStatus`, `hasOfficialAuthority`, and other fields
  that only exist in the demo's richer two-person-workflow model — the
  real backend has none of them. Fixed by adding a real backend aggregate
  endpoint, `GET /external-opportunities/verification-summary` (pending
  count, verified-today count, reverification-due-soon count, a real
  status breakdown, 7-day decision activity, an honest official-source
  ratio, and approvals attributed to the calling officer via
  `ImportAuditLog`), and rewriting every dashboard panel to consume it
  through `ApiVerificationRepository.getSummary()`. Panels with no real
  backend equivalent ("My Assignments") were replaced with panels backed
  by real data ("Approved by You"), not relabeled fakes. The dead
  `DemoVerificationRepository`/`_opportunityRepository` wiring was removed
  from `app.dart` entirely.
- **Reverification reminders produced no real delivery.** The Celery task
  `_send_reverification_reminders` only logged a count. Fixed by creating
  real `ScholarSphereNotification` rows (in-app channel — the one channel
  this backend genuinely delivers on today; email/push are marked
  "delivered" by `process_due_notifications` without any SMTP/FCM
  provider behind them, a pre-existing gap tracked separately in
  `Task.md`) for verification officers, identified via real prior
  `verification_*` decisions in `ImportAuditLog` (this backend has no
  local user directory to draw a full officer roster from — a documented,
  honest limitation, not a fabricated recipient list). Deduplicated by a
  deterministic id (`{opportunity_id}-reverification-officer-{uid}`) so
  re-running the task never spams, and gated on each recipient's own
  notification preferences (global opt-out, missing `in_app` channel, or
  a type-specific unsubscribe all suppress creation). New
  `NotificationEventType.reverification_due`.
- **Provider document-sharing had no consent precondition.** Sharing an
  applicant document with a provider (`POST
  /applicant-documents/{id}/share`) recorded the grant unconditionally.
  Fixed by requiring an active (`granted`, not `withdrawn`)
  `third_party_sharing` `ConsentRecord` before recording the grant (`409`
  otherwise, mirroring the exact precondition
  `privacy.py::record_organization_access` already enforced elsewhere),
  and validating the target provider actually exists (`404` otherwise).
  Every successful grant now also writes a real
  `OrganizationAccessRecord`, visible to the applicant via `GET
  /privacy/access-history`. Withdrawing that consent
  (`POST /privacy/consents/thirdPartySharing/withdraw`) now cascades to
  clear every existing `shared_with_provider_ids` grant for that user, not
  just block new ones.
- **Incidental:** `JobMonitorScreen`'s three `setState(_reload)` calls
  passed a `void` arrow-function tear-off whose body was itself an
  assignment expression — at runtime it still returned the assigned
  `Future`, tripping Flutter's "setState callback returned a Future"
  guard. Found while writing the search-index regression test (the first
  test ever to actually drive "process queued jobs"); fixed by wrapping
  each call in a block body.

### Added
- `GET /external-opportunities/verification-summary` backend endpoint +
  `VerificationSummary`/`VerificationActivityDay` schemas.
- `ApiVerificationRepository.getSummary()` +
  `LiveVerificationSummary`/`VerificationActivityDay` Flutter models.
- `ScholarSphereApp.verificationRepository` constructor override, so tests
  can inject a fake `ApiVerificationRepository` the same way every other
  API repository already supports.
- 4 new backend tests (`tests/test_verification_actions.py`), 4 new
  backend tests (`tests/test_opportunity_tasks.py`), 5 new/updated backend
  tests (`tests/test_applicant_documents_route.py`), 1 new Flutter
  end-to-end widget test.

### Changed
- `scholarsphere_backend/README.md`'s "Known limitations" section
  corrected: the reverification-reminder-delivery bullet was stale (it
  predated both the 2026-08-20 real Notifications backend and this
  session's fix).

---

## [Baseline] — 2026-08-21

Snapshot of the project's real state at the point this documentation set
was created, reconstructed from `git log` and direct code inspection (not
fabricated). Dates below are real commit dates.

### Added
- **2026-08-07** — Initial commit: Flutter project scaffold.
- **2026-08-12** — `ui-ux-pro-max` design-intelligence Claude Code skill
  installed; `dart format` violations fixed project-wide.
- **2026-08-17** — Production security audit performed across the full
  repository (Flutter client, FastAPI backend, Cloud Functions, Firestore
  rules, CI, Docker/deploy config): 16 of 17 findings fixed and
  regression-tested (rate limiting, security headers, dependency CVEs,
  `FIREBASE_CHECK_REVOKED` production hardening, repo-hygiene cleanup,
  HTTPS-enforcement gap in the Flutter release build, weak client-side
  email validation). One finding (a transitive `uuid` CVE via
  `firebase-admin`) remains open with no available upstream patch.
  `docs/PRODUCTION_SECURITY_AUDIT.md`, `docs/SECURITY_MODEL.md`,
  `docs/OPPORTUNITY_VERIFICATION_SYSTEM.md`, `docs/AUTHORITATIVE_SOURCES.md`
  written as the standing security/architecture reference set.
- **2026-08-17** — `applications` and `verification` real FastAPI backends
  landed, wired into the Flutter client via `ApiApplicationRepository`/
  `ApiVerificationRepository` (an optional-constructor-override
  dependency-injection pattern introduced this round, also used to make
  widget tests possible without a live Firebase app).
- **2026-08-17** — Auth screen restructured into scrollable wide/narrow
  layouts; EU MSCA calls reclassified as fellowships; a Grants.gov
  individual-eligibility source added and classified as scholarship.
- **2026-08-18** — `ui-ux-pro-max` design system applied across applicant,
  provider, and back-office surfaces; design tokens persisted to
  `design-system/scholarsphere/MASTER.md`.
- **2026-08-18** — `providers`/`provider_opportunities` real FastAPI
  backend landed: organization registration/verification/suspend/appeal,
  server-authoritative risk scoring, case-insensitive duplicate-domain
  prevention, a 5-item provider verification checklist, real Firebase
  Storage document upload with owner-scoped `storage.rules`. A separate,
  isolated pipeline from the Grants.gov-family opportunities table.
- **2026-08-18** — Dependabot alerts (`js-yaml`, `uuid`) fixed in Cloud
  Functions.
- **2026-08-20** — Real Notifications backend added: in-app delivery,
  preferences, deadline reminders (supersedes the earlier
  demo-only-notifications status recorded in
  `scholarsphere_backend/README.md`'s Known Limitations, which now needs a
  follow-up correction).
- **2026-08-20** — Applicant Profile and Documents real backends landed
  (per commit history; not independently re-audited by the 2026-08-17
  security review, which predates them).
- **2026-08-21** — Further backend feature work landed ("backend
  features01", "completed features" per commit history).

### Known outstanding items carried into Task.md
- ~~Search-index rebuild / expired-opportunity-detection background jobs
  still read from demo (fake) opportunity data instead of the real API
  repository.~~ Fixed 2026-08-21 — see the `[2026-08-21]` entry above.
- ~~Verification Officer dashboard landing metrics still read from the demo
  repository while the queue itself is real.~~ Fixed 2026-08-21 — see the
  `[2026-08-21]` entry above.
- Several 2026-08-18 through 2026-08-21 backend additions have not yet had
  an independent security review against the 2026-08-17 audit's own
  checklist.
- Firebase console bundle-ID re-registration and real release signing
  remain blocked on access this session/tooling can't provide.

See `Road_map.md` for the full phase-by-phase status and `Task.md` for the
active task board.

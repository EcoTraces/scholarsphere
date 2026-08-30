# ScholarSphere — Country/Region Provider Research Registry

Research inventory for the 2026-08-23 country-expansion initiative (WMI +
23 target countries/regions). This is a **research and planning document**,
distinct from `docs/AUTHORITATIVE_SOURCES.md` (which documents only sources
that are actually implemented, code-reviewed, and tested — the same
distinction the codebase already draws between "sources evaluated and
deliberately not integrated" and the numbered live-source list).

**Status legend** (per-country):

- `SUPPORTED` — at least one reliable official provider is genuinely
  integrated, code-reviewed, and either live-verified or (if live-blocked)
  clearly documented as such.
- `PARTIALLY_SUPPORTED` — a provider is integrated but its live status is
  blocked by a documented external issue (network/TLS), not by lack of
  effort.
- `RESEARCHED_NOT_IMPLEMENTED` — a credible official provider was
  identified and classified below, but no adapter has been built yet.
- `NO_RELIABLE_SOURCE_FOUND` — researched, no official single-source
  channel suitable for automated ingestion was identified.
- `BLOCKED` — a real official provider exists but active technical
  measures (anti-bot challenge, broken network path) prevent automated
  access, and bypassing them is out of scope (never attempted).

**Per-provider classification** (Phase A/B): `READY_FOR_AUTOMATION` /
`REQUIRES_CURATED_SOURCE` / `REQUIRES_MANUAL_INTEGRATION` / `BLOCKED` /
`NOT_SUITABLE`.

All research below was performed via web search on 2026-08-23 and,
for implemented sources, verified further via direct `robots.txt` and page
fetches — see `docs/AUTHORITATIVE_SOURCES.md` entries #13-#21 for the nine
that were actually built this session (in two batches).

---

## Implemented (35, across multiple sessions)

| # | Org/Program | Country | provider_type | Official domain | collection_method | Status |
|---|---|---|---|---|---|---|
| 13 | Wells Mountain Initiative (WMI) Scholars Program | (global, home-region only) | FUNDING_ORGANIZATION | wellsmountaininitiative.org | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-23 |
| 14 | Türkiye Bursları | Turkey | GOVERNMENT | turkiyeburslari.gov.tr | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-23 |
| 15 | Government of Ireland Int'l Education Scholarships | Ireland | GOVERNMENT | hea.ie | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-23 |
| 16 | ICCR Scholarship Programme | India | GOVERNMENT | iccr.gov.in | WEB_SCRAPER | **PARTIALLY_SUPPORTED** — implemented, blocked by a TLS certificate-chain issue on ICCR's own server (see #16 in AUTHORITATIVE_SOURCES.md) |
| 17 | Swedish Institute Scholarships for Global Professionals | Sweden | GOVERNMENT | si.se | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-23 |
| 18 | Eswatini SLAS | Eswatini | GOVERNMENT | slas.gov.sz | WEB_SCRAPER | **NOT_SUITABLE** — the "www." host still times out, but the bare host is reachable as of 2026-08-29 (base URL corrected); its real content is a domestic student-loan portal for Eswatini nationals with no scholarship/SADC text anywhere, so this adapter correctly extracts nothing from it (see docs/AUTHORITATIVE_SOURCES.md #18) |
| 19 | Italian Government Scholarships (MAECI) | Italy | GOVERNMENT | esteri.it / studyinitaly.esteri.it | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-23 |
| 20 | IKY Foreign Nationals Scholarships | Greece | GOVERNMENT | iky.gr | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-23 |
| 21 | NRF Postgraduate Funding | South Africa | GOVERNMENT | nrf.ac.za | WEB_SCRAPER | **PARTIALLY_SUPPORTED** — implemented, blocked by the same TLS certificate-chain issue class as ICCR (see #21 in AUTHORITATIVE_SOURCES.md) |
| 22 | NL Scholarship (Nuffic) | Netherlands | GOVERNMENT | studyinnl.org | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 23 | Becas MAEC-AECID | Spain | GOVERNMENT | aecid.es | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 24 | Australia Awards | Australia | GOVERNMENT | australiaawards.com.au | WEB_SCRAPER | **PARTIALLY_SUPPORTED** — overview live-verified 2026-08-29; deadline page (dfat.gov.au) unreachable from this environment, same network-level pattern as Sierra Leone's MTHE |
| 25 | Japanese Government (MEXT) Scholarship | Japan | GOVERNMENT | studyinjapan.go.jp | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 26 | ARES International Training Scholarships | Belgium | GOVERNMENT | ares-ac.be | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 27 | France Excellence Eiffel Scholarship | France | GOVERNMENT | campusfrance.org | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 28 | OeAD Ernst Mach Grant | Austria | GOVERNMENT | oead.at | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 29 | AMCI Scholarships of the Kingdom of Morocco | Morocco | GOVERNMENT | amci.ma | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 30 | Camões Cooperation Scholarships | Portugal | GOVERNMENT | instituto-camoes.pt | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 31 | Beca Colombia Extranjeros | Colombia | GOVERNMENT | web.icetex.gov.co | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 32 | Becas para Extranjeros | Chile | GOVERNMENT | agcid.gob.cl | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 33 | Beca Alianza del Pacífico | Peru | GOVERNMENT | pronabec.gob.pe | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 34 | GKS (Global Korea Scholarship) Program | South Korea | GOVERNMENT | studyinkorea.go.kr | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 35 | Government University Scholarships | Saudi Arabia | GOVERNMENT | moe.gov.sa | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 36 | Qatar Scholarships | Qatar | GOVERNMENT | qatarscholarships.qa | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 37 | Swiss Government Excellence Scholarships (ESKAS) | Switzerland | GOVERNMENT | sbfi.admin.ch | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 38 | Poland My First Choice | Poland | GOVERNMENT | nawa.gov.pl | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 39 | Government Scholarships – Developing Countries | Czech Republic | GOVERNMENT | msmt.gov.cz | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 40 | "World in Serbia" Scholarships | Serbia | GOVERNMENT | welcometoserbia.gov.rs | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 41 | Romanian Government Scholarships (MFA) | Romania | GOVERNMENT | studyinromania.gov.ro | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 42 | Stipendium Hungaricum | Hungary | GOVERNMENT | stipendiumhungaricum.hu | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 43 | Becas de Excelencia del Gobierno de México (AMEXCID) | Mexico | GOVERNMENT | gob.mx | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 44 | EducationUSA "Find Financial Aid" Database | United States | GOVERNMENT | educationusa.state.gov | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 45 | Joint Japan/World Bank Graduate Scholarship Program | (not tied to one destination country) | FUNDING_ORGANIZATION | worldbank.org | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-30; Sierra Leone confirmed on its own published eligible-countries list |
| 46 | Rotary Peace Fellowships | (not tied to one destination country) | FUNDING_ORGANIZATION | rotary.org | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-30; open worldwide, no nationality restriction |

Already supported before this initiative: **Germany** (DAAD, source #10)
and, more narrowly, the UK (Commonwealth Scholarships #8, Chevening #9).

---

## Researched, not yet implemented (5)

For each: what was found, why it wasn't built this session (time — not a
disqualification), and its recommended classification.

### Canada — `NOT_SUITABLE` for the single-flagship pattern (confirmed by live research 2026-08-29)
- **Government sources**: Global Affairs Canada / EduCanada
  (educanada.ca), via the "My EduCanada" portal.
- **What live testing actually found**: `educanada.ca`'s "Scholarships
  for international applicants" page is a directory of several distinct
  named programs (Emerging Leaders in the Americas Program, Study in
  Canada Scholarships, SEED-2, Canada-China Scholars' Exchange Program,
  and more), not one flagship. Its broadest-eligibility program, Study in
  Canada Scholarships (SICS), was fetched and confirmed
  **institution-initiated, not student-initiated**: "Only Canadian
  post-secondary institutions are eligible to apply on this call...
  Direct applications from individuals are not accepted." Canadian
  institutions select students proactively; there is no page an
  individual applicant submits anything to, unlike France's Eiffel
  program (source #27) or Japan's MEXT Scholarship (source #25), where
  the institution/embassy nominates a student who did apply somewhere.
- **Classification**: `REQUIRES_CURATED_SOURCE` for the directory as a
  whole (a real multi-listing database, like Campus Bourses below, not
  the single-flagship pattern); `NOT_SUITABLE` for SICS specifically at
  the individual-applicant level this platform models. `robots.txt`
  (checked 2026-08-29) is permissive, so a future curated-database
  adapter is technically feasible if that investment is made.

### Japan — implemented, see source #25 above (live-verified 2026-08-29)

### Netherlands — implemented, see source #22 above (live-verified 2026-08-29)

### France — implemented (Eiffel), see source #27 above (live-verified 2026-08-29)
- The Eiffel program is one specific narrower cut of France's coverage,
  not the whole picture: Campus France also runs "Campus Bourses," a
  real multi-listing searchable database that still needs its own
  discovery-and-parsing design, like CSC UK, not the single-flagship
  pattern — genuinely `REQUIRES_CURATED_SOURCE`, left for a future pass.

### Italy — implemented, see source #19 above

### Portugal — implemented, see source #30 above (live-verified 2026-08-29)
- The specific program targeted is "Formação em Portugal" (degree study
  in Portugal for 9 named partner countries); Camões also runs a
  separate Portuguese Language and Culture scholarship track
  (`bolsas-lingua-cultura`), not covered here — a distinct, narrower
  program left for a future pass if it's worth adding.

### Belgium — implemented (ARES), see source #26 above (live-verified 2026-08-29)
- ARES's own `/bourses-de-mobilite` hub links to ~8 distinct instruments;
  the specific "Bourses de formations internationales" sub-page
  implemented here is one of them (the one aimed at students/young
  professionals). VLIR-UOS (Flemish universities) remains genuinely
  decentralized across individual university websites, no single portal
  found — `REQUIRES_MANUAL_INTEGRATION`, not attempted.

### Spain — implemented, see source #23 above (live-verified 2026-08-29)

### Australia — implemented, see source #24 above (overview live-verified 2026-08-29; deadline page unreachable)

### Austria — implemented, see source #28 above (live-verified 2026-08-29)
- Confirmed by live research to run *multiple* named sub-grants on one
  page rather than one flagship (Ernst Mach – Ukraine, worldwide, for
  Fachhochschule study, Follow-Up, ASEA-UNINET, ...) — handled with the
  same deliberate `deadline_keywords = ()` pattern as South Africa NRF
  and Spain AECID, rather than the DAAD-style curated-seed-list approach
  originally guessed at here.

### South Africa — implemented, see source #21 above (live-blocked — TLS)

### Denmark — `NOT_SUITABLE` for the single-flagship pattern (confirmed by a dedicated follow-up search, 2026-08-29)
- The dedicated follow-up this entry itself called for was done this
  pass. Confirmed directly (not just inferred): "The scholarships are
  administered by the Danish universities, who each select the students
  who are awarded with a scholarship" — genuinely decentralized, no
  single national awarding body to target. Denmark's separate SU
  (Statens Uddannelsesstøtte) state education-support scheme is
  explicitly for Danish residents, not the international-applicant
  scholarship this platform models. `NOT_SUITABLE` at the
  national-government level, same category as Canada above; a future
  pass could instead evaluate individual Danish universities directly if
  that investment is made.

### Morocco — implemented, see source #29 above (live-verified 2026-08-29)
- The official domain is `amci.ma` (confirmed live, resolving the prior
  uncertainty about "Maroc Alumni"'s canonical URL — that appears to be
  a separate, narrower alumni-relations platform, not the main AMCI
  scholarships page this source targets).

### Cyprus — `BLOCKED`
- **Government source**: Cyprus State Scholarship Foundation (IKYK),
  applications via `gov.cy` (requires a CY Login account); also
  `highereducation.ac.cy` for general information.
- **Why blocked, not just deferred**: `gov.cy` is protected by an **Azure
  WAF JavaScript challenge** — confirmed by direct fetch 2026-08-23 (the
  server returns a JS-challenge page, not content, to any non-browser
  client). Per this initiative's explicit rule ("do not bypass CAPTCHAs
  / anti-bot protections"), this was not pursued further. `gov.cy` itself
  requiring an authenticated CY Login for the actual application also
  means even a browser-based approach would only ever reach a
  description page, not application data.

### Greece — implemented, see source #20 above

### Wales — `NOT_SUITABLE` (corrected 2026-08-29 — the previous `READY_FOR_AUTOMATION` note was wrong; do not act on it as written)
- **Source**: Global Wales Programme (partnership between the Welsh
  Government, Universities Wales, the British Council, and HEFCW, funded
  via Taith) — Global Wales Postgraduate Scholarship (up to £10,000),
  `studyinwales.ac.uk`.
- **What live testing actually found (2026-08-29)**: the dedicated
  program page this entry was based on
  (`/global-wales-postgraduate-scholarship`) now 404s (real "Page not
  found" content, not a bot block). The site's current replacement page
  (`/scholarships-and-funding/global-wales-scholarships-international-students`,
  confirmed reachable, 200) states the program is no longer centrally
  administered — it now points applicants to each of the eight
  participating universities' own scholarship pages individually, plus
  to Chevening and Commonwealth Scholarships (both already separate
  sources here, #9 and #8). A third-party site independently corroborates
  this: "Applications for the Global Wales Postgraduate Scholarship 2024
  have now closed."
- **Classification**: `NOT_SUITABLE` at the single-flagship level — the
  program this session's research was based on appears discontinued or
  at minimum no longer centrally run. The prior `READY_FOR_AUTOMATION`
  classification was never live-tested before being written down; this
  is exactly the kind of real bug live verification is meant to catch,
  same as the India ICCR dual-`<h1>` issue and the stale Firebase
  bundle-ID note elsewhere in this project's history. Re-open only if a
  future pass finds Wales has revived a central program, or decides
  per-university scraping across all eight Welsh institutions is worth
  the effort this initiative has otherwise avoided.

### United Arab Emirates — `NO_RELIABLE_SOURCE_FOUND`
- Researched via `u.ae` (the official UAE government platform) and the
  Ministry of Presidential Affairs' Scholarship Office. Both are
  overwhelmingly focused on funding **Emirati nationals to study abroad**,
  not funding international students to study in the UAE. Individual
  government-linked universities (UAEU, Khalifa University) do offer
  scholarships to international students, but there is no single central
  government portal for *inbound* international-student funding.
- **Classification**: `NOT_SUITABLE` at the national-government level;
  a future pass could evaluate UAEU/Khalifa University directly as
  `UNIVERSITY`-type providers instead of `GOVERNMENT`, if that's a
  priority.

---

## South America (first research pass, 2026-08-29)

All nine countries were entirely outside this registry before this pass —
no prior research existed for any of them. Each was checked for a genuine
*inbound* (foreigners studying in that country) single-flagship government
program, live-verified via both `curl` and this backend's actual httpx
path before any implementation decision.

### Colombia — implemented, see source #31 above (live-verified 2026-08-29)

### Chile — implemented, see source #32 above (live-verified 2026-08-29)

### Peru — implemented, see source #33 above (live-verified 2026-08-29)

### Brazil — `BLOCKED` (confirmed by live testing 2026-08-29)
- The official program is real and well-documented: PEC-G (Programa de
  Estudantes-Convênio de Graduação), jointly run by the Ministry of
  Foreign Affairs (MRE) and Ministry of Education (MEC), offering free
  undergraduate tuition, SUS healthcare, and (in some cases) a MEC/MRE
  stipend, at `gov.br/mre/.../pec-g/sobre`. A `curl` fetch with a
  spoofed browser user agent returns the real page (200, ~297KB).
- However, this backend's actual httpx client (no spoofed user agent,
  matching production) is served a JavaScript bot-challenge page
  (an F5/Distil-style `TSPD` cookie challenge) instead of real content,
  confirmed 3/3 attempts, not a one-off — the same class of finding as
  Cyprus's Azure WAF block. Bypassing this (spoofing a browser identity)
  is out of scope, the same policy already applied to Cyprus.
  A MEC-hosted alternate (`portal.mec.gov.br`) was also attempted but was
  unreachable through this environment's own network path (`502 Bad
  Gateway`, 3/3 attempts) — inconclusive on that host specifically, not
  independently confirmed either way.
- **Classification**: `BLOCKED` — a real, well-documented program exists,
  but the production fetch path cannot reach it.

### Argentina — `NOT_SUITABLE` (confirmed by live testing 2026-08-29)
- Argentina's Ministry of Education does fund international scholarships
  (`argentina.gob.ar/educacion/becas-internacionales` confirms this
  explicitly, "para extranjeros y extranjeras en la Argentina"), but that
  page is a description of the overall program *framework*, not a single
  flagship opportunity page — it points to a separate searchable listing
  portal, `campusglobal.educacion.gob.ar/becas/enargentina`, which is a
  multi-entry directory (the same database shape already set aside for
  France's Campus Bourses, source #27's note) rather than a single
  program, and was unreachable through this environment's proxy (`502`)
  for direct inspection regardless.
- **Classification**: `NOT_SUITABLE` for the single-flagship pattern —
  the real mechanism is a searchable multi-entry database, not one page.

### Uruguay — `NOT_SUITABLE` (confirmed by live testing 2026-08-29)
- AUCI (Agencia Uruguaya de Cooperación Internacional) funds Uruguayan
  citizens/residents to study *abroad* (outbound, not inbound). ANII
  (Agencia Nacional de Investigación e Innovación) does have a
  postgraduate scholarship program, but its own page states eligibility
  explicitly: "Las becas podrán ser solicitadas por uruguayos o
  extranjeros **residentes en Uruguay**" (Uruguayans or foreigners
  **already resident in Uruguay**) — not open to prospective
  international applicants abroad, and the specific call fetched was
  already closed (`Llamado cerrado`, closed 2025-10-30).
- **Classification**: `NOT_SUITABLE` — no program open to global inbound
  applicants was found.

### Ecuador — `NO_RELIABLE_SOURCE_FOUND` (researched 2026-08-29)
- SENESCYT's scholarship catalogue funds **Ecuadorian professionals to
  study abroad** (outbound). A historical inbound program for foreign
  researchers, "Prometeo" (`prometeo.senescyt.gob.ec`), was found only in
  news coverage and government pages dated 2013-2015 — no current (2026)
  source confirms it is still active, and per this project's discipline
  against inferring from third-party summaries or stale coverage, it was
  not pursued further without a live, current official page.
- **Classification**: `NO_RELIABLE_SOURCE_FOUND` — worth a fresh check in
  a future pass in case Prometeo (or a successor program) has an active
  current page.

### Paraguay — `NOT_SUITABLE` (confirmed by live testing 2026-08-29)
- BECAL ("Becas Don Carlos Antonio López"), Paraguay's national
  scholarship program, funds postgraduate study both abroad and in
  Paraguay - but its own eligibility requirements for the in-Paraguay
  option are explicit: "tener nacionalidad paraguaya o contar con
  **residencia** en Paraguay" (Paraguayan nationality or existing
  **residency** in Paraguay) — the same residency-restriction pattern as
  Uruguay's ANII, not open to prospective international applicants.
- **Classification**: `NOT_SUITABLE` — no program open to global inbound
  applicants was found.

### Bolivia — `NO_RELIABLE_SOURCE_FOUND` (researched 2026-08-29)
- Bolivia's national postgraduate scholarship portal
  (`becas.planificacion.gob.bo`) requires Bolivian nationality and a
  degree from a Bolivian (or apostilled foreign) university for its
  outbound-study-abroad program. No official government program funding
  foreign nationals to study *in* Bolivia was found.
- **Classification**: `NO_RELIABLE_SOURCE_FOUND`.

---

## Asia — remaining named countries (first research pass, 2026-08-29)

The four remaining named Asian countries from the master prompt not yet
covered by any prior source (China and India already have narrower
existing coverage). Each was checked for a genuine *inbound* single-
flagship government program, live-verified via both `curl` and this
backend's actual httpx path before any implementation decision.

### South Korea — implemented, see source #34 above (live-verified 2026-08-29)

### Saudi Arabia — implemented, see source #35 above (live-verified 2026-08-29)

### Qatar — implemented, see source #36 above (live-verified 2026-08-29)

### Thailand — `NOT_SUITABLE` (confirmed by live testing 2026-08-29)
- Thailand's Ministry of Higher Education, Science, Research and
  Innovation (MHESI) publishes its international scholarship
  announcements on `ops.go.th` as a rolling, year-dated news feed (e.g.
  "Thailand Scholarships (Year 2025) for International Students",
  "Thailand Scholarships for Austrian Students (ASEA-UNINET) 2026") —
  the same "multi-entry feed, not one page" shape already set aside for
  Argentina and France's Campus Bourses. There is no evergreen URL for
  "this year's" cycle; each year's announcement lives at its own
  year-slugged path.
- A second candidate, TICA's (Thailand International Cooperation
  Agency) own overview page for its flagship Thai International
  Postgraduate Programme (TIPP) at `tica-thaigov.mfa.go.th`, was also
  fetched and rejected: its content is real but frozen from around
  2013–2015 (explicitly discussing "the TIPP programme 2014" and
  carrying a "Copyright © 2015" footer, despite a 2022 "last updated"
  timestamp) — stale in the same way already ruled out for Ecuador's
  Prometeo program, not a current description of the active 2026/2027
  cycle referenced elsewhere in current search results.
- Note: this specific host (`ops.go.th`) was intermittently unreachable
  during initial testing (timeouts on several `curl` and httpx
  attempts) but succeeded consistently once retried with this backend's
  actual production request shape (its registered `User-Agent` header
  and full 40s timeout) — a transient connectivity issue, not a real
  block, per this project's established retry discipline.
- **Classification**: `NOT_SUITABLE` for the single-flagship pattern —
  the real government mechanism is a rolling year-dated announcement
  feed, and the one evergreen "about" page found is stale.

---

## Europe — remaining named countries (first research pass, 2026-08-29)

The eight remaining named European countries from the original
master-prompt request, the last unresearched region. Each was checked
for a genuine *inbound* single-flagship government program,
live-verified via both `curl` and this backend's actual httpx path
before any implementation decision.

### Switzerland — implemented, see source #37 above (live-verified 2026-08-29)

### Poland — implemented, see source #38 above (live-verified 2026-08-29)

### Czech Republic — implemented, see source #39 above (live-verified 2026-08-29)

### Croatia — `NOT_SUITABLE` (confirmed by live testing 2026-08-29)
- The Ministry of Science, Education and Youth's "Croatian Government
  Scholarships (Bilateral Scholarships)" are real, but every source
  found is a year-dated "Call for Applications" page with its own
  numeric ID (e.g. `.../scholarships-of-the-republic-of-croatia-call-
  for-applications-in-the-academic-year-2026-2027/7588`) — a fresh
  search turned up seven different such pages spanning 2020/2021
  through 2026/2027, with no evergreen "about the programme" URL
  independent of a specific year's call, the same "year-dated slug, not
  evergreen" shape already ruled out for Thailand. The programme is
  also nomination-only: "the Bilateral Scholarships can be awarded only
  to the candidates who are nominated by the foreign partner
  institutions."
- **Classification**: `NOT_SUITABLE` for the single-flagship pattern —
  the real content lives in year-dated call pages requiring an annual
  code update, not one stable URL.

### Serbia — implemented, see source #40 above (live-verified 2026-08-29)

### Romania — implemented, see source #41 above (live-verified 2026-08-29)

### Norway — `NO_RELIABLE_SOURCE_FOUND` (researched 2026-08-29)
- Norway's two historical inbound scholarship mechanisms are both
  confirmed defunct: the "Quota Scheme" (run through Lånekassen, the
  Norwegian State Educational Loan Fund) ended in 2016, and a related
  successor programme, NORSTIP, was cancelled from the 2026 budget
  onward — corroborated across multiple independent sources, not a
  single claim. Lånekassen's own remaining support for "foreign
  nationals" is fundamentally a means-tested loan/grant system
  requiring Norwegian citizenship or an existing permanent residence
  permit, not a scholarship for prospective international applicants.
- **Classification**: `NO_RELIABLE_SOURCE_FOUND` — no active
  government inbound scholarship program exists.

### Finland — `NOT_SUITABLE` (confirmed by live testing 2026-08-29)
- The one clear national government scholarship, the EDUFI Fellowship
  (Finnish National Agency for Education/OPH), states on its own
  official page: "EDUFI Fellowship for foreign doctoral researchers
  will end at the end of 2025. New applications cannot be submitted
  after 17.10.2025" — a date already in the past relative to this
  session. Several third-party aggregators still list it as "active in
  2026", confirming exactly why this project verifies against primary
  sources rather than trusting secondary summaries. Finland's own
  official study-abroad portal (`studyinfinland.fi`) independently
  confirms there is no replacement: "University scholarships are
  competitive and usually cover tuition fees only, not living
  costs... Plan to cover your tuition fees and living costs
  independently" — funding is decentralized to individual universities,
  not a national government program.
- **Classification**: `NOT_SUITABLE` — the one national program found is
  confirmed discontinued by its own official page, with no replacement.

---

## Beyond the original request (first research pass, 2026-08-29)

With every country and region named in the original master-prompt
request now researched, this pass picked 8 new countries entirely
outside that request, spanning regions not yet touched at all:
**Hungary** (Europe), **Mexico** (North America), **Indonesia**,
**Malaysia**, **Vietnam** (Southeast Asia), **Egypt**, **Israel**
(Middle East/North Africa), and **Kenya** (Sub-Saharan Africa). Each
was checked for a genuine *inbound* single-flagship government program,
live-verified via both `curl` and this backend's actual httpx path
before any implementation decision.

### Hungary — implemented, see source #42 above (live-verified 2026-08-29)

### Mexico — implemented, see source #43 above (live-verified 2026-08-29)

### Indonesia — `BLOCKED` (confirmed by live testing 2026-08-29)
- The real program, KNB (Kemitraan Negara Berkembang) Scholarship, is
  managed by the Directorate General of Higher Education under
  Indonesia's Ministry of Higher Education, Science, and Technology.
  Its current official interactive site (`knb.kemdiktisaintek.go.id`) is
  a pure client-side JavaScript app — the raw HTML response is just
  "Loading homepage..." with no server-rendered content on any route
  checked. A content-rich companion site describing the same current
  program was found (`knb.kemendikbudristek.net`), but its `robots.txt`
  explicitly disallows `ClaudeBot` by name (alongside GPTBot,
  Bytespider, and several other named AI crawlers), and sets
  `Content-Signal: ai-train=no` for the general `User-agent: *` block —
  a clear, explicit statement of the site operator's intent that this
  project honors rather than routes around with a different
  User-Agent string.
- **Classification**: `BLOCKED` — the interactive official site has no
  scrapable content, and the one alternative with real content
  explicitly disallows this project's crawler by name.
- Update: this backend gained an opt-in headless-browser rendering
  fallback later in this session (see "Browser-rendering fallback" in
  `docs/AUTHORITATIVE_SOURCES.md`), which *could* in principle render
  `knb.kemdiktisaintek.go.id`'s JS shell into real content — its
  `robots.txt` returns 404 (unrestricted) and it carries no
  ClaudeBot-disallow, unlike the `.net` alternative. This was **not**
  attempted: the sandbox this capability was built in could not drive a
  real browser against any external site (every outbound Chromium
  navigation failed at the TLS layer, a sandbox-specific limitation —
  see that doc section), so live-verifying this specific page never
  happened. Still `BLOCKED` until a session with a working outbound path
  for browser automation live-tests it.

### Malaysia — `NOT_SUITABLE` (confirmed by live testing 2026-08-29)
- The Malaysia International Scholarship (MIS), run by the Ministry of
  Higher Education (MOHE), has a real official portal
  (`biasiswa.mohe.gov.my/INTER/index.php`), but the page itself is
  extremely thin (~700 characters of actual description before a
  status notice that the 2026/2027 cycle is closed) with no `<h1>` and
  no funding-coverage or deadline language in its own HTML text — the
  only richer detail lives in a linked PDF Guidelines document this
  scraper does not parse. The same thin-content shape already ruled out
  for Colombia's `programa-de-reciprocidad` page (source #31's
  docstring).
- **Classification**: `NOT_SUITABLE` — real program, but insufficient
  on-page substance to build a reliable record from.

### Vietnam — `BLOCKED` (confirmed by live testing 2026-08-29)
- The one candidate inbound portal found, `studyinvietnam.edu.vn`
  ("Vietnam Government Scholarship"), does not support HTTPS at all —
  confirmed by a direct connection attempt (`ConnectError` on every
  `https://` variant tried), while plain `http://` responds normally.
  This backend's `validate_https_url` hard-requires an HTTPS scheme for
  every external fetch (a security boundary applied uniformly across
  every source in this codebase, never relaxed for one adapter), so this
  site is structurally incompatible regardless of content quality. VIED
  (Vietnam International Education Development), the other candidate
  organization, appears predominantly focused on funding Vietnamese
  citizens to study *abroad* (e.g. "Project 911"), not inbound.
- **Classification**: `BLOCKED` — the one HTML-content candidate site
  cannot be reached over HTTPS at all.

### Egypt — `BLOCKED` (confirmed by live testing 2026-08-29)
- The official EGYAID/Study-in-Egypt portal
  (`admission.study-in-egypt.gov.eg`), run by the Ministry of Higher
  Education and Scientific Research, is a pure client-side JavaScript
  single-page app with zero server-rendered content on any route
  checked (`/`, `/about`, `/programs`, `/scholarships`, `/egyaid`,
  `/en/about` all return the identical 2,021-byte JS-only shell: "You
  need to enable JavaScript to run this app.").
- **Classification**: `BLOCKED` — no scrapable content exists anywhere
  on this domain without executing JavaScript.
- Update: same as Indonesia above — this domain is a candidate for the
  browser-rendering fallback added later in this session, but it was not
  attempted (no working outbound browser-automation path in the sandbox
  that built it). Still `BLOCKED` pending real live-testing.

### Israel — `BLOCKED` (confirmed by live testing 2026-08-29)
- The Ministry of Foreign Affairs scholarship page
  (`gov.il/en/service/scholarships_application_for_academic_studies_in_
  israel`) returned `403 Forbidden` on 3/3 attempts with this backend's
  actual httpx client — a consistent, active block, not a one-off
  transient failure. MASA, a second candidate program, was set aside as
  a different shape: it is restricted to Jewish students specifically
  (not a general international-student program) and is run by the
  quasi-governmental Jewish Agency for Israel rather than the state
  directly.
- **Classification**: `BLOCKED` — the government page actively refuses
  this backend's requests.

### Kenya — `NO_RELIABLE_SOURCE_FOUND` (researched 2026-08-29)
- The Ministry of Education's `education.go.ke/scholarships` page is a
  searchable multi-entry table ("Scholarship Name / Type / Country /
  Duration / Deadline") of bilateral opportunities for *Kenyan citizens*
  to study abroad (China, Japan, India, Russia, Turkey, Hungary, etc.) —
  outbound, and a database rather than a single page, the same
  double-disqualifying shape already seen for Argentina. No official
  Kenyan government program funding foreign nationals to study *in*
  Kenya was found.
- **Classification**: `NO_RELIABLE_SOURCE_FOUND`.

---

## Beyond the original request, second pass (2026-08-29) — 0 new sources

A second pass beyond the original request, covering 8 more countries:
**New Zealand** (Oceania), **Singapore**, **Pakistan**, **Philippines**
(South/Southeast Asia), **Nigeria**, **Ghana**, **Rwanda**
(Sub-Saharan Africa), and **Jordan** (Middle East). Unlike every prior
pass in this initiative, **none of the 8 yielded an implementable
source** — reported here in full because that is itself a real,
honest research outcome worth recording, not a reason to omit the
findings or force a weak candidate through.

### New Zealand — `NOT_SUITABLE` (confirmed by live testing 2026-08-29)
- Manaaki New Zealand Scholarships (NZAID), funded through the New
  Zealand Aid Programme and administered by MFAT, is a real, well-
  documented, genuinely inbound program with an official site
  (`nzscholarships.govt.nz`, fully permissive `robots.txt`) — the
  research failure here is structural, not a content problem. The
  entire site is built with Next.js CSS Modules: every wrapping
  element, down to the immediate parent of the page's own `<h1>`, uses
  an auto-generated hashed class name (e.g. `Layout_main__E16O_`,
  `HeroPanel-module_inner__P3zsE`) with no stable, hand-authored class
  or id anywhere near the content. The generic `<main>` tag itself is
  non-unique (2 matches per page), and the first one in document order
  is a navigation/menu block, not the real content — so even the
  simplest possible selector picks the wrong element. No selector on
  this page is safe from breaking on the site's next deploy.
- **Classification**: `NOT_SUITABLE` — no stable selector exists
  anywhere on the site, a novel failure mode distinct from every prior
  "thin content" or "blocked" finding in this registry.

### Singapore — `NOT_SUITABLE` (confirmed by live testing 2026-08-29)
- The Singapore International Graduate Award (SINGA), A*STAR's
  well-known PhD scholarship, no longer has a dedicated "about the
  program" page — every guessed and search-suggested URL under
  `a-star.edu.sg/scholarships/...` for it returns `404`, and a full
  scan of the site's own `sitemap.xml` (643KB, checked directly) turns
  up only a scholar-testimonial page mentioning SINGA by name, not a
  program overview. The one current "International Awards" offering
  found, the Singapore Research Attachment Programme (SRAP), is
  institution-initiated — applications must be submitted by "Singapore
  researchers... together with their overseas collaborator(s)", not by
  individual prospective students — the same disqualifying shape
  already ruled out for Canada's SICS program.
- **Classification**: `NOT_SUITABLE` — SINGA appears to have no current
  standalone page, and the one program that does is not
  individually-applicable.

### Pakistan — `BLOCKED` (confirmed by live testing 2026-08-29)
- The Higher Education Commission (HEC) does run scholarships for
  foreign students (Central Asian and "friendly country" nationals),
  per third-party mentions, but every variant of its domain
  (`hec.gov.pk`, `www.hec.gov.pk`, `scholarship.hec.gov.pk`) fails with
  `SSL: CERTIFICATE_VERIFY_FAILED` — a real, broken TLS certificate
  chain on HEC's own servers, confirmed 6/6 across all three hostnames
  and two attempts each, the same class of finding as India ICCR and
  South Africa NRF (sources #16, #21). No real HTML content could be
  fetched at all, so no fixture or adapter could be built.
- **Classification**: `BLOCKED` — TLS certificate-chain defect,
  connection fails before any content is ever served.

### Philippines — `BLOCKED` (confirmed by live testing 2026-08-29)
- CHED (Commission on Higher Education) is described only vaguely in
  third-party sources as "occasionally" partnering on scholarships for
  foreign students — a weaker candidate to begin with — and its
  official site (`ched.gov.ph`) returns `403 Forbidden` on every
  attempt (3/3, both the homepage and `robots.txt`), an active,
  consistent block.
- **Classification**: `BLOCKED`.

### Nigeria — `NO_RELIABLE_SOURCE_FOUND` (researched 2026-08-29)
- The Federal Scholarships Board (a department of the Federal Ministry
  of Education) implements Nigeria's Bilateral Education Agreement and
  Commonwealth scholarship commitments — entirely for the benefit of
  *Nigerian* citizens (both those studying abroad and those studying
  locally). No official program funding foreign nationals to study *in*
  Nigeria was found.
- **Classification**: `NO_RELIABLE_SOURCE_FOUND`.

### Ghana — `NO_RELIABLE_SOURCE_FOUND` (researched 2026-08-29)
- The Ghana Scholarships Authority (`scholarships.gov.gh`) offers "local
  tertiary scholarships for students enrolled in public tertiary
  institutions in Ghana" and "foreign tertiary scholarships for
  Ghanaians accepted into recognized international institutions" — both
  explicitly for Ghanaian citizens, the same outbound/domestic-only
  shape as Nigeria's FSB. No inbound program was found.
- **Classification**: `NO_RELIABLE_SOURCE_FOUND`.

### Rwanda — `NO_RELIABLE_SOURCE_FOUND` (researched 2026-08-29)
- The Higher Education Council (`hec.gov.rw`) is primarily a domestic
  student-loan and outbound-scholarship body for Rwandan citizens (its
  most prominent current program is literally titled "Government Study
  Loan Rwanda"). No official Rwandan government program funding foreign
  nationals to study *in* Rwanda was found.
- **Classification**: `NO_RELIABLE_SOURCE_FOUND`.

### Jordan — `NOT_SUITABLE` (confirmed by live testing 2026-08-29)
- The Ministry of Higher Education and Scientific Research's "Cultural
  Agreements" page (`mohe.gov.jo`, no `robots.txt` restrictions) does
  confirm a genuine, bidirectional inbound mechanism: "citizens of
  [partner] countries are hosted by Jordanian public universities" under
  agreements with 25 named Arab and foreign partner countries. But the
  page has no `<h1>` and the real content, once separated from the
  page's extensive navigation menu, is only two sentences plus a
  country list — no funding coverage, no deadline, no application
  process described anywhere on the page — the same thin-content shape
  already ruled out for Colombia's `programa-de-reciprocidad` page and
  Malaysia's MIS portal.
- **Classification**: `NOT_SUITABLE` — real bidirectional program, but
  insufficient on-page substance to build a reliable record from.

---

## United States and China (2026-08-29, closing the original 40-country audit)

The only two named countries in the original 40-country target list that
had never been individually researched (every other one already has a
documented finding above, most dated the same day) — found while cross-
checking the full implementation against that exact list.

### United States — `SUPPORTED` (implemented 2026-08-29)
- Prior US-facing sources (Grants.gov, USAJOBS, ReliefWeb) are federal
  grants/jobs/humanitarian postings, not international-student
  scholarships; Fulbright was already researched and rejected (see
  `docs/AUTHORITATIVE_SOURCES.md`'s "Sources evaluated and deliberately
  not integrated" table).
- `educationusa.state.gov/find-financial-aid` (US Department of State,
  EducationUSA network) is a real, live, paginated Drupal Views listing
  of 277+ individually browsable, institution-specific scholarships for
  international students — plain server-rendered HTTPS, no browser
  rendering needed. `robots.txt` returns HTTP 403 (treated as "no
  restrictions apply" per RFC 9309 §2.3.1.3, not silently assumed —
  see the source's own entry). Live-tested with three real fetches
  (page 0, page 1, and `?page=40` confirming a genuine zero-row "past
  the last page" response).
- **Classification**: `SUPPORTED` — see source #44 in
  `docs/AUTHORITATIVE_SOURCES.md` for the full write-up.

### China — `BLOCKED` (confirmed by live testing 2026-08-29)
- The China Scholarship Council (CSC) administers the Chinese Government
  Scholarship, a real, major, well-known program for international
  students to study in China — genuinely worth pursuing, unlike most
  `NOT_SUITABLE`/`NO_RELIABLE_SOURCE_FOUND` findings elsewhere in this
  document.
- Every candidate official page checked returns either HTTP 412
  (`csc.edu.cn`, `studyinchina.csc.edu.cn`, tested with and without a
  browser-like `User-Agent`) or, for `robots.txt` itself (which did
  return HTTP 200), an obfuscated JavaScript anti-bot challenge page
  (a heavily minified/obfuscated inline script plus a "404 系统繁忙，
  请稍后再试" — "system busy, please try again later" — message), the
  same class of active anti-bot protection already documented for
  Cyprus's Azure WAF and Brazil's F5/Distil challenge. `campuschina.org`
  (a secondary official-adjacent domain sometimes used for the same
  program) did not respond at all within a 15-second timeout.
- Never attempted to bypass any of this - detected, classified, and
  recorded, per this project's standing anti-bot policy (see
  `app/services/browser_rendering.py`'s module docstring).
- **Classification**: `BLOCKED` — a real program with active anti-bot
  protection blocking every access path tried, not a code defect. Not
  pursued further without an explicit, informed decision to do so via
  an authorized channel, the same standing given Cyprus.

---

## Country coverage summary

| Country/Region | Status | Notes |
|---|---|---|
| WMI (org, not a country) | SUPPORTED | Live-verified |
| Turkey | SUPPORTED | Live-verified |
| Ireland | SUPPORTED | Live-verified |
| Sweden | SUPPORTED | Live-verified |
| Italy | SUPPORTED | Live-verified |
| Greece | SUPPORTED | Live-verified |
| Germany | SUPPORTED | Pre-existing (DAAD) |
| India | PARTIALLY_SUPPORTED | Blocked by ICCR's TLS chain issue |
| Eswatini | NOT_SUITABLE | Reachability fixed 2026-08-29 (bare host, not "www."), but real content is a domestic student-loan portal with no scholarship/SADC text - adapter correctly extracts nothing |
| South Africa | PARTIALLY_SUPPORTED | Blocked by the same TLS chain issue class as India |
| Netherlands | SUPPORTED | Live-verified 2026-08-29 |
| Spain | SUPPORTED | Live-verified 2026-08-29 |
| Australia | PARTIALLY_SUPPORTED | Overview live-verified 2026-08-29; deadline page (dfat.gov.au) unreachable, same pattern as Sierra Leone's MTHE |
| Japan | SUPPORTED | Live-verified 2026-08-29 |
| Belgium | SUPPORTED | Live-verified 2026-08-29 |
| France | SUPPORTED | Live-verified 2026-08-29 (Eiffel program only — Campus Bourses database still needs its own design) |
| Austria | SUPPORTED | Live-verified 2026-08-29 |
| Morocco | SUPPORTED | Live-verified 2026-08-29 |
| Portugal | SUPPORTED | Live-verified 2026-08-29 |
| Canada | NOT_SUITABLE | Confirmed by live research 2026-08-29 — institution-initiated, no individual-applicant path |
| Denmark | NOT_SUITABLE | Confirmed by a dedicated follow-up search 2026-08-29 — decentralized to individual universities |
| Cyprus | BLOCKED | Active anti-bot (Azure WAF) — not bypassed |
| Wales | NOT_SUITABLE | Corrected 2026-08-29 — the flagship program appears discontinued/decentralized; previous READY_FOR_AUTOMATION note was wrong, never live-tested |
| UAE | NO_RELIABLE_SOURCE_FOUND | Predominantly outbound (for Emiratis), not inbound |
| Colombia | SUPPORTED | Live-verified 2026-08-29 |
| Chile | SUPPORTED | Live-verified 2026-08-29 |
| Peru | SUPPORTED | Live-verified 2026-08-29 |
| Brazil | BLOCKED | Confirmed 2026-08-29 — JS bot-challenge (F5/Distil-style) on the production fetch path, 3/3 attempts |
| Argentina | NOT_SUITABLE | Confirmed 2026-08-29 — real mechanism is a searchable multi-entry database, not a single program page |
| Uruguay | NOT_SUITABLE | Confirmed 2026-08-29 — residency-restricted/outbound only |
| Ecuador | NO_RELIABLE_SOURCE_FOUND | Researched 2026-08-29 — outbound program only; historical inbound program's current status unconfirmed |
| Paraguay | NOT_SUITABLE | Confirmed 2026-08-29 — residency-restricted/outbound only |
| Bolivia | NO_RELIABLE_SOURCE_FOUND | Researched 2026-08-29 — no inbound program found |
| South Korea | SUPPORTED | Live-verified 2026-08-29 |
| Saudi Arabia | SUPPORTED | Live-verified 2026-08-29 |
| Qatar | SUPPORTED | Live-verified 2026-08-29 |
| Thailand | NOT_SUITABLE | Confirmed 2026-08-29 — real mechanism is a year-dated announcement feed; the one evergreen "about" page found is stale (frozen ~2013-2015 content) |
| Switzerland | SUPPORTED | Live-verified 2026-08-29 |
| Poland | SUPPORTED | Live-verified 2026-08-29 |
| Czech Republic | SUPPORTED | Live-verified 2026-08-29 |
| Croatia | NOT_SUITABLE | Confirmed 2026-08-29 — real content lives in year-dated call pages, nomination-only via partner institutions |
| Serbia | SUPPORTED | Live-verified 2026-08-29 |
| Romania | SUPPORTED | Live-verified 2026-08-29 |
| Norway | NO_RELIABLE_SOURCE_FOUND | Researched 2026-08-29 — Quota Scheme ended 2016, NORSTIP cancelled from 2026 budget, no active program found |
| Finland | NOT_SUITABLE | Confirmed 2026-08-29 — EDUFI Fellowship confirmed discontinued (no new applications after 17.10.2025) by its own official page, no replacement |
| Hungary | SUPPORTED | Live-verified 2026-08-29 |
| Mexico | SUPPORTED | Live-verified 2026-08-29 |
| Indonesia | BLOCKED | Confirmed 2026-08-29 — official site is JS-only; the content-rich alternative explicitly disallows ClaudeBot by name in robots.txt |
| Malaysia | NOT_SUITABLE | Confirmed 2026-08-29 — real program but the page is too thin, real detail only in an unparsed PDF |
| Vietnam | BLOCKED | Confirmed 2026-08-29 — the one candidate site does not support HTTPS at all, incompatible with this backend's HTTPS-only requirement |
| Egypt | BLOCKED | Confirmed 2026-08-29 — official portal is a pure JS SPA with zero server-rendered content on any route |
| Israel | BLOCKED | Confirmed 2026-08-29 — government scholarship page returns 403 Forbidden, 3/3 attempts |
| Kenya | NO_RELIABLE_SOURCE_FOUND | Researched 2026-08-29 — the one page found is an outbound-opportunity database, not an inbound single program |
| New Zealand | NOT_SUITABLE | Confirmed 2026-08-29 — entire site relies on auto-generated CSS-module hash classes, no stable selector exists anywhere |
| Singapore | NOT_SUITABLE | Confirmed 2026-08-29 — SINGA has no current standalone page; the one current program is institution-initiated, not individually-applicable |
| Pakistan | BLOCKED | Confirmed 2026-08-29 — HEC's domain fails TLS certificate verification on every hostname tried, 6/6 attempts |
| Philippines | BLOCKED | Confirmed 2026-08-29 — CHED's official site returns 403 Forbidden, 3/3 attempts |
| Nigeria | NO_RELIABLE_SOURCE_FOUND | Researched 2026-08-29 — Federal Scholarships Board is outbound/domestic only, for Nigerian citizens |
| United States | SUPPORTED | Live-verified 2026-08-29 — EducationUSA "Find Financial Aid" database (source #44) |
| China | BLOCKED | Confirmed 2026-08-29 — China Scholarship Council is real and legitimate, but every page (including robots.txt) is behind an active anti-bot challenge (HTTP 412 or an obfuscated-JS "system busy" interstitial) |
| Ghana | NO_RELIABLE_SOURCE_FOUND | Researched 2026-08-29 — Scholarships Authority is outbound/domestic only, for Ghanaian citizens |
| Rwanda | NO_RELIABLE_SOURCE_FOUND | Researched 2026-08-29 — Higher Education Council is a domestic student-loan/outbound body |
| Jordan | NOT_SUITABLE | Confirmed 2026-08-29 — real bidirectional cultural-agreement program, but the page is too thin (no funding/deadline detail) |

**19 of 24 original targets have a genuinely integrated provider** (15
fully live-verified, 4 implemented-but-live-blocked/partially-blocked with
documented reasons — 2 of those 4 share the same TLS-certificate-chain
root cause on the respective government servers, 1 (Eswatini) is the
same network-timeout pattern as Sierra Leone's MTHE, and 1 (Australia) is
that same network-timeout pattern on one of its two source pages only —
none are code defects). **None of the remaining 5 have a credible
official candidate identified and classified** — every entry left is
either genuinely unsuitable, unreachable, or unresourced (see the
"Researched, not yet implemented" section above). **1 has no reliable
single-source candidate found yet** (UAE). **3 (Canada, Denmark, Wales)
turned out, on live verification during this session's research passes,
not to have a single-flagship program worth automating** — decentralized
to individual institutions in each case, confirmed directly rather than
assumed. **1 is actively blocked by anti-bot protection** (Cyprus) and
will not be pursued further without an explicit, informed decision to do
so via an authorized channel (e.g. contacting the Cyprus government for
an API/data-sharing arrangement — not a technical bypass).

**South America, researched for the first time this session, adds 3 more
live-verified sources** (Colombia, Chile, Peru) entirely outside the
original 24-target list — see the dedicated section above. Of the other
6 countries checked: 1 is genuinely `BLOCKED` (Brazil, real program but
an anti-bot-protected fetch path), 3 are `NOT_SUITABLE` (Argentina - a
database, not a single page; Uruguay and Paraguay - both
residency-restricted, not open to global inbound applicants), and 2 have
`NO_RELIABLE_SOURCE_FOUND` (Ecuador, Bolivia).

**The four remaining named Asian countries (South Korea, Saudi Arabia,
Qatar, Thailand), also researched for the first time this session, add
3 more live-verified sources** (South Korea, Saudi Arabia, Qatar) — see
the dedicated section above. Thailand came back `NOT_SUITABLE` — its
government's real scholarship information lives in a rolling, year-dated
announcement feed rather than one evergreen page, and the one candidate
"about" page found on a different official domain was stale (frozen
~2013-2015 content, not the currently active cycle).

**Beyond the original request, a first pass on 8 new countries entirely
outside it adds 2 more live-verified sources** (Hungary, Mexico) — see
the dedicated section above. Of the other 6: 4 came back `BLOCKED`
(Indonesia — JS-only official site plus a content-rich alternative that
explicitly disallows this project's crawler by name; Vietnam — the one
candidate site doesn't support HTTPS at all; Egypt — official portal is
a pure JS SPA with zero server-rendered content on any route; Israel —
government scholarship page returns 403 on every attempt), 1 is
`NOT_SUITABLE` (Malaysia — real program, but the page is too thin to
build a reliable record from), and 1 has `NO_RELIABLE_SOURCE_FOUND`
(Kenya — the one page found is an outbound-opportunity database).

## Recommended next candidates

**The original 24-country queue is empty**, and every region named in
the original master-prompt request has now had its first full research
pass — South America (2026-08-29), the four remaining named Asian
countries (2026-08-29), and the eight remaining named European
countries (2026-08-29) — see the dedicated sections above. Every
country checked across all three passes is now either a real,
live-verified source or a confirmed, evidence-backed `BLOCKED` /
`NOT_SUITABLE` / `NO_RELIABLE_SOURCE_FOUND` finding — none are left as
stale guesses. The 2 entries still under "Researched, not yet
implemented" above (Cyprus, UAE) are there because they genuinely can't
be reached or don't fit this system's single-flagship pattern, not
because they're unresearched.

**No named country or region from the original master-prompt request
remains unresearched.** A tenth and eleventh pass have now researched 16
more countries entirely outside that original request (tenth: Hungary,
Mexico, Indonesia, Malaysia, Vietnam, Egypt, Israel, Kenya; eleventh:
New Zealand, Singapore, Pakistan, Philippines, Nigeria, Ghana, Rwanda,
Jordan) — see the two dedicated "Beyond the original request" sections
above. The eleventh pass, notably, yielded zero new sources — a real
research outcome, not a gap: several African and outbound-focused
ministries turned out to have no inbound program at all, two government
sites are actively unreachable (a TLS certificate defect, a 403 block),
and two otherwise-real programs failed on structural grounds (an
entirely CSS-module-hashed site with no stable selector, and a program
that no longer has a standalone page). Any further expansion from here
would mean either revisiting a `NOT_SUITABLE`/`BLOCKED`/
`NO_RELIABLE_SOURCE_FOUND` finding with new evidence (e.g. checking
whether Finland's EDUFI Fellowship gets a successor programme, whether
Pakistan's HEC fixes its TLS certificate chain, or whether Egypt's or
Israel's official sites gain a server-rendered fallback), or choosing
more new countries — there is no shortage of unresearched countries
left worldwide, just diminishing odds of a clean single-flagship match
per country picked at random.

**The eleventh pass (8 more new countries entirely outside the original
request) added no new sources**: New Zealand and Singapore were found
`NOT_SUITABLE` (a site with no stable selector anywhere, and a program
with no current standalone page, respectively); Pakistan and Philippines
were found `BLOCKED` (a TLS certificate defect, and a 403 block);
Nigeria, Ghana, and Rwanda came back `NO_RELIABLE_SOURCE_FOUND` (each
ministry's scholarship program is outbound/domestic only); Jordan was
found `NOT_SUITABLE` (a real bidirectional program, but too thin on the
page to build a record from) — see their entries in the second "Beyond
the original request" section above.

**Implemented since the tenth pass (8 new countries entirely outside
the original master-prompt request)**: Hungary (Stipendium Hungaricum)
and Mexico (AMEXCID Excellence Scholarships), both fully live-verified
— see `docs/AUTHORITATIVE_SOURCES.md` #42-#43. Indonesia, Vietnam,
Egypt, and Israel were investigated in the same pass and found
`BLOCKED`; Malaysia came back `NOT_SUITABLE`; Kenya came back
`NO_RELIABLE_SOURCE_FOUND` — see their entries in the "Beyond the
original request" section above.

**Implemented since the ninth pass (the eight remaining named European
countries, a dedicated first-pass research effort)**: Switzerland
(SBFI ESKAS), Poland (NAWA My First Choice), Czech Republic (MŠMT
Government Scholarships), Serbia ("World in Serbia"), and Romania (MFA
Government Scholarships), all fully live-verified — see
`docs/AUTHORITATIVE_SOURCES.md` #37-#41. Croatia and Finland were
investigated in the same pass and found `NOT_SUITABLE` (Croatia: only
year-dated, nomination-only call pages exist; Finland: its one national
program is confirmed discontinued by its own official page) rather than
implemented; Norway came back `NO_RELIABLE_SOURCE_FOUND` (its historical
inbound programs are confirmed defunct) — see their entries in the
Europe section above.

**Implemented since the eighth pass (the four remaining named Asian
countries, a dedicated first-pass research effort)**: South Korea (GKS
Program), Saudi Arabia (MOE Government University Scholarships), and
Qatar (Qatar Scholarships/QFFD), all fully live-verified — see
`docs/AUTHORITATIVE_SOURCES.md` #34-#36. Thailand was investigated in
the same pass and found `NOT_SUITABLE` (a rolling year-dated
announcement feed rather than one evergreen page, plus one stale
candidate "about" page from a different domain) rather than implemented
— see its entry in the Asia section above.

**Implemented since the seventh pass (South America, a dedicated
first-pass research effort covering all 9 countries in the region)**:
Colombia (ICETEX Beca Colombia Extranjeros), Chile (AGCID Becas para
Extranjeros), and Peru (PRONABEC Beca Alianza del Pacífico), all fully
live-verified — see `docs/AUTHORITATIVE_SOURCES.md` #31-#33. Brazil was
investigated in the same pass and found genuinely `BLOCKED` (a real
program behind an anti-bot-protected fetch path) rather than
implemented; Argentina, Uruguay, and Paraguay were confirmed
`NOT_SUITABLE`; Ecuador and Bolivia came back `NO_RELIABLE_SOURCE_FOUND`
— see their entries in the South America section above.

**Implemented since the first pass**: Italy (MAECI), Greece (IKY), and
South Africa (NRF, live-blocked by a TLS issue) — see
`docs/AUTHORITATIVE_SOURCES.md` #19-#21. **Implemented since the second
pass**: Netherlands (Nuffic NL Scholarship, fully live-verified) — see
`docs/AUTHORITATIVE_SOURCES.md` #22. **Implemented since the third
pass**: Spain (AECID, fully live-verified) and Australia (DFAT Awards,
overview live-verified — the deadline page itself is unreachable from
this environment) — see `docs/AUTHORITATIVE_SOURCES.md` #23-#24.
**Implemented since the fourth pass**: Japan (MEXT Scholarship, fully
live-verified) — see `docs/AUTHORITATIVE_SOURCES.md` #25. Wales was
investigated in the same pass and found `NOT_SUITABLE` on live testing
(see its corrected entry above) rather than implemented. **Implemented
since the fifth pass (a dedicated research pass, not a fetch-and-wire
one)**: Belgium (ARES), France (Eiffel), Austria (OeAD Ernst Mach), and
Morocco (AMCI), all fully live-verified — see
`docs/AUTHORITATIVE_SOURCES.md` #26-#29. Canada and Denmark were
investigated in the same pass and confirmed `NOT_SUITABLE` on live
testing rather than implemented. **Implemented since the sixth pass**:
Portugal (Camões Cooperation Scholarships, fully live-verified, the last
entry this registry had queued) — see `docs/AUTHORITATIVE_SOURCES.md`
#30.

**Twelfth pass (2026-08-29/30): the exact 40-country target list audited
end to end.** Cross-referencing the platform's specific 40-country list
against this registry found 38 of 40 already had a real, live-tested
finding — the remaining two (China, United States) were researched and
closed (see the dedicated "United States and China" section above).
While re-checking, also found and fixed a real reachability bug
(Eswatini's configured "www." host times out; the bare host doesn't —
see its entry above) and, separately, did a first real-source pass on
the **Mastercard Foundation Scholars Program** — a major, legitimate,
Africa-focused foundation directly relevant to Sierra Leone — which
turned out to be JavaScript-gated with no server-rendered fallback on
its actual institution-listing page; not integrated in this pass (see
`docs/AUTHORITATIVE_SOURCES.md`'s "Sources evaluated and deliberately
not integrated" table for the full finding). **Recommended next
candidate**: live-verify and implement the Mastercard Foundation
listing page from a session with working outbound browser automation
(this sandbox's Chromium still can't reach real external HTTPS sites —
confirmed again this pass). **Recommended next body of work beyond
single candidates**: the platform specification's "multiple source
types per country" ambition (university + government + embassy +
foundation sources per country, not just one flagship government
source) is real and mostly unaddressed — nearly every SUPPORTED country
in this registry has exactly one source today.

**Thirteenth pass (2026-08-30), same "multiple source types" gap.**
Two more Sierra-Leone-relevant candidates checked: (1) re-tested
`sl.usembassy.gov/educational-professional-exchanges/` (the page
Fulbright research already flagged as broken) — still a persistent
"Technical Difficulties" error page, 3/3 attempts, not fixed. (2)
Researched and **implemented** the **Joint Japan/World Bank Graduate
Scholarship Program (JJ/WBGSP)** — see source #45 in
`docs/AUTHORITATIVE_SOURCES.md`. A real, major, international-
organization-type source (the World Bank Group, funded by the
Government of Japan), genuinely eligible for Sierra Leone applicants
(confirmed on the programme's own published eligible-countries list,
not assumed), with a real static server-rendered overview page — no
browser rendering needed, unlike the Mastercard Foundation candidate
from the twelfth pass. This is the registry's first `FUNDING_ORGANIZATION`
/ international-organization-type source alongside the existing
government-type sources, a small real step on the "multiple source
types per country" gap. The gap itself remains largely open — most
countries here still have exactly one source.

**Fourteenth pass (2026-08-30), continuing the same gap.** Two more
foundation-type candidates researched: (1) **Aga Khan Foundation
International Scholarship Programme** — real and legitimate, but its
own published country scope does not include Sierra Leone (Bangladesh,
India, Pakistan, Afghanistan, Tajikistan, Kyrgyzstan, Syria, Egypt,
Kenya, Tanzania, Uganda, Madagascar, Mozambique) — not integrated on
eligibility grounds, not a technical one; see
`docs/AUTHORITATIVE_SOURCES.md`'s "Sources evaluated and deliberately
not integrated" table. (2) Researched and **implemented** **Rotary
Peace Fellowships** — see source #46 in `docs/AUTHORITATIVE_SOURCES.md`.
Real, genuinely open worldwide by nationality (unlike Aga Khan's ISP),
real static server-rendered content, `robots.txt`-compliant
(`Crawl-delay: 10`, respected). One honestly-recorded fragility: the
page has no semantic content wrapper, only Tailwind utility classes, so
its description selector is more brittle than most sources here — works
today, verified against the real page, but documented as a real risk
rather than silently assumed durable. 35 sources now implemented; the
"multiple source types per country" gap keeps narrowing but remains
largely open.

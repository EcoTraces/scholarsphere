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

## Implemented (10, across multiple sessions)

| # | Org/Program | Country | provider_type | Official domain | collection_method | Status |
|---|---|---|---|---|---|---|
| 13 | Wells Mountain Initiative (WMI) Scholars Program | (global, home-region only) | FUNDING_ORGANIZATION | wellsmountaininitiative.org | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-23 |
| 14 | Türkiye Bursları | Turkey | GOVERNMENT | turkiyeburslari.gov.tr | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-23 |
| 15 | Government of Ireland Int'l Education Scholarships | Ireland | GOVERNMENT | hea.ie | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-23 |
| 16 | ICCR Scholarship Programme | India | GOVERNMENT | iccr.gov.in | WEB_SCRAPER | **PARTIALLY_SUPPORTED** — implemented, blocked by a TLS certificate-chain issue on ICCR's own server (see #16 in AUTHORITATIVE_SOURCES.md) |
| 17 | Swedish Institute Scholarships for Global Professionals | Sweden | GOVERNMENT | si.se | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-23 |
| 18 | Eswatini SLAS | Eswatini | GOVERNMENT | slas.gov.sz | WEB_SCRAPER | **PARTIALLY_SUPPORTED** — implemented, blocked by a network timeout (same pattern as Sierra Leone's MTHE, source #12) |
| 19 | Italian Government Scholarships (MAECI) | Italy | GOVERNMENT | esteri.it / studyinitaly.esteri.it | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-23 |
| 20 | IKY Foreign Nationals Scholarships | Greece | GOVERNMENT | iky.gr | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-23 |
| 21 | NRF Postgraduate Funding | South Africa | GOVERNMENT | nrf.ac.za | WEB_SCRAPER | **PARTIALLY_SUPPORTED** — implemented, blocked by the same TLS certificate-chain issue class as ICCR (see #21 in AUTHORITATIVE_SOURCES.md) |
| 22 | NL Scholarship (Nuffic) | Netherlands | GOVERNMENT | studyinnl.org | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |

Already supported before this initiative: **Germany** (DAAD, source #10)
and, more narrowly, the UK (Commonwealth Scholarships #8, Chevening #9).

---

## Researched, not yet implemented (11)

For each: what was found, why it wasn't built this session (time — not a
disqualification), and its recommended classification.

### Canada — `RESEARCHED_NOT_IMPLEMENTED`
- **Government sources**: Global Affairs Canada / EduCanada
  (educanada.ca), via the "My EduCanada" portal.
- **Structural note**: applications are institution-mediated — Canadian
  colleges/universities apply *on behalf of* eligible students, rather
  than a student applying directly to one public page with a stated
  deadline. This doesn't fit the single-flagship-program pattern used for
  sources 13–17 as cleanly; it likely needs its own research pass into
  whether `educanada.ca` publishes a public, structured list of open
  exchange agreements.
- **Classification**: `REQUIRES_CURATED_SOURCE` (needs a second research
  pass focused on `educanada.ca`'s actual page structure before deciding
  scraper vs. manual).

### Japan — `RESEARCHED_NOT_IMPLEMENTED`
- **Government source**: MEXT (Ministry of Education, Culture, Sports,
  Science and Technology), via the official "Study in Japan" portal
  `studyinjapan.go.jp`.
- **Structural note**: applications route through the applicant's home
  country's Japanese embassy/consulate, not a single online form —
  deadlines are country-specific, published per-embassy. The central MEXT
  page describes the program but not a single global deadline.
- **Classification**: `READY_FOR_AUTOMATION` for the program-description
  page (single-flagship pattern, matching WMI/Turkey/Ireland/Sweden);
  deadline would likely be `null` most cycles for the same reason Ireland
  and Sweden came back `null` this session — genuinely honest, not a
  defect.

### Netherlands — implemented, see source #22 above (live-verified 2026-08-29)

### France — `RESEARCHED_NOT_IMPLEMENTED`
- **Source**: Campus France (quasi-governmental agency) — France
  Excellence Eiffel Scholarship, `campusfrance.org`. Campus France also
  runs "Campus Bourses," a searchable scholarship database.
- **Classification**: `REQUIRES_CURATED_SOURCE` for Campus Bourses (a
  real multi-listing database would need its own discovery-and-parsing
  design, like CSC UK, not the single-flagship pattern); the Eiffel
  program page alone would be `READY_FOR_AUTOMATION` as a narrower first
  cut.

### Italy — implemented, see source #19 above

### Portugal — `RESEARCHED_NOT_IMPLEMENTED`
- **Source**: Camões, I.P. (Instituto da Cooperação e da Língua),
  `instituto-camoes.pt` — multiple bilateral-cooperation scholarship
  programs rather than one flagship program.
- **Classification**: `REQUIRES_CURATED_SOURCE` — needs a second pass to
  identify which specific Camões program(s) have the clearest single
  page and deadline.

### Belgium — `RESEARCHED_NOT_IMPLEMENTED`
- **Sources**: ARES (Académie de Recherche et d'Enseignement supérieur,
  French-speaking universities' coordinating body), `ares-ac.be`, ~200
  scholarships/year via a central application platform; VLIR-UOS
  (Flemish universities), decentralized across individual university
  websites, no single portal found.
- **Classification**: ARES — `READY_FOR_AUTOMATION` (has a central
  portal); VLIR-UOS — `REQUIRES_MANUAL_INTEGRATION` (genuinely
  decentralized, matches the "do not scrape every university" guidance).

### Spain — `RESEARCHED_NOT_IMPLEMENTED`
- **Government source**: Ministry of Foreign Affairs, EU and Cooperation
  (MAEC) via AECID (Spanish Agency for International Development
  Cooperation) — MAEC-AECID Scholarships, `aecid.es`.
- **Classification**: `READY_FOR_AUTOMATION` — official government
  cooperation agency, flagship program (master's, diplomatic training,
  residencies), applications February–May.

### Australia — `RESEARCHED_NOT_IMPLEMENTED`
- **Government source**: Department of Foreign Affairs and Trade (DFAT)
  — Australia Awards, applied for via the OASIS system;
  `australiaawards.com.au` / `dfat.gov.au` / `studyaustralia.gov.au`.
- **Classification**: `READY_FOR_AUTOMATION` — official `.gov.au`-linked
  program, single flagship scholarship, well-documented eligibility.

### Austria — `RESEARCHED_NOT_IMPLEMENTED`
- **Source**: OeAD (Österreichischer Austauschdienst), the Austrian
  federal government's exchange-service agency — `oead.at`, application
  portal at `grants.oead.at`, ~3,500 international students/researchers
  funded per year across several named programs (e.g. Ernst Mach Grant).
- **Classification**: `REQUIRES_CURATED_SOURCE` — OeAD runs *multiple*
  named programs rather than one flagship, closer to DAAD's shape (a
  small database) than to Chevening's; would benefit from the same
  curated-seed-list approach used for DAAD if a catalog/sitemap gap is
  found, or a scraper per named program if pages are structured cleanly.

### South Africa — implemented, see source #21 above (live-blocked — TLS)

### Denmark — `NO_RELIABLE_SOURCE_FOUND` (pending further research)
- Multiple sources point to `studyindenmark.dk` as an aggregator/
  informational portal (mentions "the Danish Education Support Agency")
  but no single named government body/URL was confidently identified as
  the *awarding* authority in this pass — Denmark's model appears to be
  per-university tuition waivers within a national framework rather than
  one centrally-administered flagship scholarship. Needs a dedicated
  follow-up search specifically for the responsible ministry/agency
  (likely under `ufm.dk`, the Ministry of Higher Education and Science)
  before it can be reclassified.

### Morocco — `RESEARCHED_NOT_IMPLEMENTED`
- **Government source**: Moroccan Agency for International Cooperation
  (AMCI), under the Ministry of Higher Education — Moroccan Government
  Scholarship Programme, applications via the "Maroc Alumni" digital
  platform.
- **Classification**: `REQUIRES_CURATED_SOURCE` — the exact official
  domain for "Maroc Alumni" was not confidently confirmed in this pass
  (several third-party summaries reference it without a consistent
  canonical URL); needs direct verification before building an adapter.

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

### Wales — `RESEARCHED_NOT_IMPLEMENTED`
- **Source**: Global Wales Programme (partnership between the Welsh
  Government, Universities Wales, the British Council, and HEFCW, funded
  via Taith) — Global Wales Postgraduate Scholarship (up to £10,000),
  `studyinwales.ac.uk`.
- **Classification**: `READY_FOR_AUTOMATION` — single flagship
  scholarship with a dedicated official-partnership portal page.

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
| Eswatini | PARTIALLY_SUPPORTED | Blocked by network timeout |
| South Africa | PARTIALLY_SUPPORTED | Blocked by the same TLS chain issue class as India |
| Netherlands | SUPPORTED | Live-verified 2026-08-29 |
| Canada | RESEARCHED_NOT_IMPLEMENTED | Institution-mediated, needs deeper research |
| Japan | RESEARCHED_NOT_IMPLEMENTED | Ready for automation |
| France | RESEARCHED_NOT_IMPLEMENTED | Curated source (database) needed |
| Portugal | RESEARCHED_NOT_IMPLEMENTED | Curated source needed |
| Belgium | RESEARCHED_NOT_IMPLEMENTED | ARES ready; VLIR-UOS decentralized |
| Spain | RESEARCHED_NOT_IMPLEMENTED | Ready for automation — strong next candidate |
| Australia | RESEARCHED_NOT_IMPLEMENTED | Ready for automation |
| Austria | RESEARCHED_NOT_IMPLEMENTED | Curated source (multi-program) needed |
| Denmark | NO_RELIABLE_SOURCE_FOUND | Needs a dedicated follow-up search |
| Morocco | RESEARCHED_NOT_IMPLEMENTED | Curated source; exact domain unconfirmed |
| Cyprus | BLOCKED | Active anti-bot (Azure WAF) — not bypassed |
| Wales | RESEARCHED_NOT_IMPLEMENTED | Ready for automation |
| UAE | NO_RELIABLE_SOURCE_FOUND | Predominantly outbound (for Emiratis), not inbound |

**11 of 24 targets have a genuinely integrated provider** (8 fully
live-verified, 3 implemented-but-live-blocked with documented reasons —
2 of those 3 share the same TLS-certificate-chain root cause on the
respective government servers, not a code defect). **10 have a credible
official candidate identified and classified**, ready for a future
implementation pass without further country-level research. **2 have no
reliable single-source candidate found yet** (Denmark, UAE). **1 is
actively blocked by anti-bot protection** (Cyprus) and will not be pursued
further without an explicit, informed decision to do so via an authorized
channel (e.g. contacting the Cyprus government for an API/data-sharing
arrangement — not a technical bypass).

## Recommended next candidates (highest value, `READY_FOR_AUTOMATION`)

In priority order, based on official-domain strength, single-flagship
simplicity (matching the proven pattern), and geographic spread:

1. **Spain** (AECID) — official cooperation agency, clear program.
2. **Australia** (DFAT/Australia Awards) — official domain, well
   documented.
3. **Wales** (Global Wales) — official partnership portal.
4. **Japan** (MEXT via Study in Japan) — high applicant interest; expect
   `null` deadlines most cycles (embassy-mediated), same honest pattern
   as Ireland/Sweden this session.

**Implemented since the first pass**: Italy (MAECI), Greece (IKY), and
South Africa (NRF, live-blocked by a TLS issue) — see
`docs/AUTHORITATIVE_SOURCES.md` #19-#21. **Implemented since the second
pass**: Netherlands (Nuffic NL Scholarship, fully live-verified) — see
`docs/AUTHORITATIVE_SOURCES.md` #22.

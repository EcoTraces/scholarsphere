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

## Implemented (13, across multiple sessions)

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
| 23 | Becas MAEC-AECID | Spain | GOVERNMENT | aecid.es | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 24 | Australia Awards | Australia | GOVERNMENT | australiaawards.com.au | WEB_SCRAPER | **PARTIALLY_SUPPORTED** — overview live-verified 2026-08-29; deadline page (dfat.gov.au) unreachable from this environment, same network-level pattern as Sierra Leone's MTHE |
| 25 | Japanese Government (MEXT) Scholarship | Japan | GOVERNMENT | studyinjapan.go.jp | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |

Already supported before this initiative: **Germany** (DAAD, source #10)
and, more narrowly, the UK (Commonwealth Scholarships #8, Chevening #9).

---

## Researched, not yet implemented (10)

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

### Japan — implemented, see source #25 above (live-verified 2026-08-29)

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

### Spain — implemented, see source #23 above (live-verified 2026-08-29)

### Australia — implemented, see source #24 above (overview live-verified 2026-08-29; deadline page unreachable)

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
| Spain | SUPPORTED | Live-verified 2026-08-29 |
| Australia | PARTIALLY_SUPPORTED | Overview live-verified 2026-08-29; deadline page (dfat.gov.au) unreachable, same pattern as Sierra Leone's MTHE |
| Japan | SUPPORTED | Live-verified 2026-08-29 |
| Canada | RESEARCHED_NOT_IMPLEMENTED | Institution-mediated, needs deeper research |
| France | RESEARCHED_NOT_IMPLEMENTED | Curated source (database) needed |
| Portugal | RESEARCHED_NOT_IMPLEMENTED | Curated source needed |
| Belgium | RESEARCHED_NOT_IMPLEMENTED | ARES ready; VLIR-UOS decentralized |
| Austria | RESEARCHED_NOT_IMPLEMENTED | Curated source (multi-program) needed |
| Denmark | NO_RELIABLE_SOURCE_FOUND | Needs a dedicated follow-up search |
| Morocco | RESEARCHED_NOT_IMPLEMENTED | Curated source; exact domain unconfirmed |
| Cyprus | BLOCKED | Active anti-bot (Azure WAF) — not bypassed |
| Wales | NOT_SUITABLE | Corrected 2026-08-29 — the flagship program appears discontinued/decentralized; previous READY_FOR_AUTOMATION note was wrong, never live-tested |
| UAE | NO_RELIABLE_SOURCE_FOUND | Predominantly outbound (for Emiratis), not inbound |

**14 of 24 targets have a genuinely integrated provider** (10 fully
live-verified, 4 implemented-but-live-blocked/partially-blocked with
documented reasons — 2 of those 4 share the same TLS-certificate-chain
root cause on the respective government servers, 1 (Eswatini) is the
same network-timeout pattern as Sierra Leone's MTHE, and 1 (Australia) is
that same network-timeout pattern on one of its two source pages only —
none are code defects). **6 have a credible official candidate identified
and classified**, ready for a future implementation pass without further
country-level research. **2 have no reliable single-source candidate
found yet** (Denmark, UAE). **1 (Wales) turned out, on live verification,
not to have a single-flagship program worth automating any more** — see
its corrected entry above. **1 is actively blocked by anti-bot
protection** (Cyprus) and will not be pursued further without an
explicit, informed decision to do so via an authorized channel (e.g.
contacting the Cyprus government for an API/data-sharing arrangement —
not a technical bypass).

## Recommended next candidates

Every previously-classified `READY_FOR_AUTOMATION` candidate in this
registry has now been implemented (or, in Wales's case, live-tested and
found unsuitable). None of the 10 remaining researched-but-not-implemented
entries are that simple — each needs a real second research pass before
building an adapter, not just a fetch-and-wire pass:

1. **Belgium** (ARES) — has a real central application portal for its
   ~200 scholarships/year (French-speaking universities); the closest
   remaining candidate to the proven single-flagship shape, but was not
   itself live-tested this session.
2. **Canada** (EduCanada) — institution-mediated (Canadian institutions
   apply on a student's behalf), needs a page-structure investigation
   before deciding scraper vs. manual.
3. **France** (Campus France) — the flagship Eiffel program page alone
   would fit the pattern; "Campus Bourses" (a real searchable multi-
   listing database) is the bigger, harder win and needs its own
   discovery-and-parsing design, closer to CSC UK's shape than a single
   page.
4. **Austria** (OeAD) and **Morocco** (AMCI/"Maroc Alumni") — both
   `REQUIRES_CURATED_SOURCE`: multiple named programs (Austria) or an
   unconfirmed canonical domain (Morocco), respectively.

Countries entirely outside this registry (all of South America, most of
Asia, most of the remaining named European countries) still need a first
research pass before they can even reach this list — see the chat history
of this initiative for the full outstanding list.

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
(see its corrected entry above) rather than implemented.

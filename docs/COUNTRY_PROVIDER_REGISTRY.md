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

## Implemented (18, across multiple sessions)

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
| 26 | ARES International Training Scholarships | Belgium | GOVERNMENT | ares-ac.be | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 27 | France Excellence Eiffel Scholarship | France | GOVERNMENT | campusfrance.org | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 28 | OeAD Ernst Mach Grant | Austria | GOVERNMENT | oead.at | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 29 | AMCI Scholarships of the Kingdom of Morocco | Morocco | GOVERNMENT | amci.ma | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |
| 30 | Camões Cooperation Scholarships | Portugal | GOVERNMENT | instituto-camoes.pt | WEB_SCRAPER | **SUPPORTED** — live-verified 2026-08-29 |

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

**19 of 24 targets have a genuinely integrated provider** (15 fully
live-verified, 4 implemented-but-live-blocked/partially-blocked with
documented reasons — 2 of those 4 share the same TLS-certificate-chain
root cause on the respective government servers, 1 (Eswatini) is the
same network-timeout pattern as Sierra Leone's MTHE, and 1 (Australia) is
that same network-timeout pattern on one of its two source pages only —
none are code defects). **None of the remaining 5 have a credible
official candidate identified and classified** — the queue that section
used to describe is now empty; every entry left is either genuinely
unsuitable, unreachable, or unresourced (see below). **1 has no reliable
single-source candidate found yet** (UAE). **3 (Canada, Denmark, Wales)
turned out, on live verification this session, not to have a
single-flagship program worth automating** — decentralized to individual
institutions in each case, confirmed directly rather than assumed; see
their corrected entries above. **1 is actively blocked by anti-bot
protection** (Cyprus) and will not be pursued further without an
explicit, informed decision to do so via an authorized channel (e.g.
contacting the Cyprus government for an API/data-sharing arrangement —
not a technical bypass).

## Recommended next candidates

**The queue is empty.** Two dedicated research passes (2026-08-29)
live-tested every `READY_FOR_AUTOMATION`/`REQUIRES_CURATED_SOURCE`
candidate this registry had accumulated across its whole history —
Belgium, Canada, France, Austria, Morocco, Portugal, plus Denmark and
Wales's long-standing follow-up items. Every one is now either a real,
live-verified source or a confirmed, evidence-backed `NOT_SUITABLE` /
`BLOCKED` / `NO_RELIABLE_SOURCE_FOUND` finding — none are left as stale
guesses. The 5 entries still under "Researched, not yet implemented"
above (Canada, Denmark, Wales, Cyprus, UAE) are there because they
genuinely don't fit this system's single-flagship pattern or can't be
reached, not because they're unresearched.

The only way to add more real coverage from here is a **first** research
pass on countries entirely outside this registry: all of South America
(9 countries), most of Asia (South Korea, Saudi Arabia, Qatar, Thailand —
China and India already have narrower partial coverage), and most of the
remaining named European countries (Switzerland, Poland, Czech Republic,
Croatia, Serbia, Romania, Norway, Finland) — see the chat history of this
initiative for the full outstanding list from the original request.

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

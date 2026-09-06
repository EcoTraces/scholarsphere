from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ScholarSphere API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+asyncpg://scholarsphere:change-me@localhost:5432/scholarsphere"
    )
    redis_url: str = "redis://localhost:6379/0"
    firebase_project_id: str = "scholarsphere-d44f5"
    # Matches lib/firebase_options.dart's storageBucket. Needed so the
    # Admin SDK can generate signed download URLs for applicant documents
    # shared with a provider (see app/services/document_storage.py) -
    # unset previously, which is why that capability never existed.
    firebase_storage_bucket: str = "scholarsphere-d44f5.firebasestorage.app"
    firebase_credentials_path: Path | None = None
    # Revocation checking calls the Identity Toolkit API, which needs a real
    # service-account credential (firebase_credentials_path or ADC). Keep
    # this True in every real deployment. It exists only so local/demo runs
    # without a service account can still verify token signatures.
    firebase_check_revoked: bool = True
    allowed_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    http_timeout_seconds: float = Field(default=40.0, gt=0, le=120)
    http_max_retries: int = Field(default=3, ge=0, le=10)
    http_max_response_bytes: int = Field(default=5_242_880, gt=0, le=52_428_800)
    max_request_bytes: int = Field(default=1_048_576, gt=0, le=10_485_760)

    # Browser-rendering fallback (app/services/browser_rendering.py) - only
    # used by sources that opt in via `allow_browser_rendering = True` and
    # only when the plain HTTP fetch looks like an unrendered JS shell (see
    # web_scraper_base.py::looks_javascript_rendered). Off by default in the
    # sense that no source uses it unless it opts in; these settings bound
    # its resource cost when it does run.
    browser_render_timeout_ms: int = Field(default=20_000, gt=0, le=60_000)
    browser_render_max_concurrency: int = Field(default=2, gt=0, le=10)
    # Headless is the only correct mode for a scheduled backend task - a
    # server process has no display. This exists purely so a developer can
    # flip PLAYWRIGHT_HEADLESS=false in their own local .env to watch a
    # render happen while debugging a specific source; never set false in
    # any deployed environment (enforced below).
    browser_render_headless: bool = Field(
        default=True, validation_alias="PLAYWRIGHT_HEADLESS"
    )
    # Cookie/consent banners that block access to public page content (not
    # marketing/tracking opt-ins - see app/services/browser_rendering.py's
    # `_maybe_accept_cookie_banner`) are auto-accepted only when this is
    # true. Default on: refusing to click past a banner would silently
    # blind every browser-rendered source behind one.
    browser_auto_accept_required_cookies: bool = Field(
        default=True, validation_alias="AUTO_ACCEPT_REQUIRED_COOKIES"
    )
    # Left unset in every real deployment - Playwright's own browser
    # install (`playwright install chromium`, run in the Dockerfile)
    # manages its own matching browser build at its default location.
    # Only set this to point at a pre-installed browser binary whose
    # revision doesn't match this pinned `playwright` package version
    # (e.g. this project's own dev sandbox, which has a fixed Chromium
    # build preinstalled outside Playwright's own version-matched cache).
    browser_executable_path: str | None = None

    rate_limit_requests: int = Field(default=300, gt=0)
    rate_limit_window_seconds: int = Field(default=60, gt=0)

    # Pagination/infinite-scroll engines (app/services/pagination_engine.py,
    # app/services/infinite_scroll_engine.py) - defaults for any source
    # adapter that doesn't pass its own override. Every loop these engines
    # run stops at one of these bounds even if a "next"/"load more" control
    # never disables itself - never an unbounded loop.
    max_pages_per_source: int = Field(default=50, gt=0, le=500)
    max_records_per_source: int = Field(default=5000, gt=0, le=100_000)
    max_scroll_iterations: int = Field(default=50, gt=0, le=500)
    scroll_stagnation_limit: int = Field(default=3, gt=0, le=20)

    grants_gov_base_url: str = "https://api.grants.gov/v1/api"
    simpler_grants_base_url: str = "https://api.simpler.grants.gov"
    simpler_grants_api_key: SecretStr = SecretStr("")
    eu_funding_api_url: str = (
        "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
    )
    eu_funding_api_key: SecretStr = SecretStr("SEDIA")
    eu_funding_type_codes: Annotated[list[str], NoDecode] = ["1", "2", "8"]
    eu_funding_status_codes: Annotated[list[str], NoDecode] = [
        "31094501",
        "31094502",
    ]
    eu_funding_programme_period: str = "2021 - 2027"
    eu_funding_language: str = "en"
    eu_funding_display_fields: Annotated[list[str], NoDecode] = [
        "type",
        "identifier",
        "reference",
        "callccm2Id",
        "title",
        "status",
        "caName",
        "projectAcronym",
        "startDate",
        "description",
        "deadlineDate",
        "deadlineModel",
        "frameworkProgramme",
        "programmePeriod",
        "typesOfAction",
        "budgetOverview",
        "keywords",
    ]
    eu_funding_type_mappings: Annotated[dict[str, str], NoDecode] = {
        "1": "grant",
        "2": "grant",
        "8": "cascade_funding",
    }
    eu_funding_status_mappings: Annotated[dict[str, str], NoDecode] = {
        "31094501": "forthcoming",
        "31094502": "open",
        "31094503": "closed",
    }

    usajobs_base_url: str = "https://data.usajobs.gov/api/search"
    usajobs_api_key: SecretStr = SecretStr("")
    usajobs_user_agent: str = ""

    reliefweb_base_url: str = "https://api.reliefweb.int/v2"
    reliefweb_appname: str = ""

    # EducationUSA "Find Financial Aid" database (US Department of State) -
    # see app/services/educationusa_source.py and
    # docs/AUTHORITATIVE_SOURCES.md #44. Closes the United States gap: the
    # sources above are federal grants/jobs/humanitarian postings, not
    # international-student scholarships.
    educationusa_base_url: str = "https://educationusa.state.gov"

    # Web-scraper sources (app/services/web_scraper_base.py and its
    # subclasses) - no official API/RSS/dataset exists for these
    # organizations (see docs/AUTHORITATIVE_SOURCES.md), so this backend
    # fetches their own public HTML pages directly. Every base URL below was
    # confirmed reachable and its robots.txt checked for a scraping
    # restriction before being added; see the source registry doc for the
    # per-site notes.
    cscuk_base_url: str = "https://cscuk.fcdo.gov.uk"
    chevening_base_url: str = "https://www.chevening.org"
    daad_base_url: str = "https://www2.daad.de"
    # DAAD's scholarship database has no public sitemap or documented API
    # covering its individual listings (its search UI loads results via an
    # undocumented AJAX endpoint) - these are the detail-page IDs identified
    # during source research (see docs/AUTHORITATIVE_SOURCES.md #9), fetched
    # directly. Not a full-catalog crawl; a curated, monitored seed list.
    daad_scholarship_detail_ids: Annotated[list[str], NoDecode] = [
        "50026200",
        "50076777",
        "57742121",
        "57742130",
        "57135739",
        "10000486",
        # Konrad-Adenauer-Stiftung (KAS): Scholarship Programme for
        # International Students - added 2026-09-06 in response to a
        # request for another fully funded Master's scholarship in
        # Germany. Genuinely fully funded (see
        # `daad_scholarships.py::_FUNDING_TYPE_OVERRIDES`); this DAAD
        # detail page's own country-eligibility dropdown lists "Sierra
        # Leone" by name.
        "10000108",
    ]
    china_embassy_sl_base_url: str = "https://sl.china-embassy.gov.cn"
    mthe_sl_base_url: str = "https://www.mthe.gov.sl"

    # Country-expansion single-flagship-program sources (2026-08-23) - see
    # docs/AUTHORITATIVE_SOURCES.md #13-#18. Each is one government or
    # quasi-governmental body's own page(s) for its single recurring
    # international scholarship program - no official API/RSS/dataset
    # exists for any of them.
    wmi_base_url: str = "https://www.wellsmountaininitiative.org"
    turkiye_burslari_base_url: str = "https://www.turkiyeburslari.gov.tr"
    ireland_hea_base_url: str = "https://hea.ie"
    india_iccr_base_url: str = "https://iccr.gov.in"
    sweden_si_base_url: str = "https://si.se"
    # The "www." host timed out in every environment this project has had
    # access to until 2026-08-29, when the bare (non-www) host was found
    # to be reachable (200, real content - see docs/AUTHORITATIVE_SOURCES.md
    # #18 and docs/COUNTRY_PROVIDER_REGISTRY.md's Eswatini entry). The real
    # page content is a domestic student-loan portal for Eswatini
    # nationals ("Ministry of Labour and Social Security" / "Student
    # Loan" / "Apply Now" / "Loan Repayment") with no "scholarship" or
    # "SADC" text anywhere on the page - EswatiniSlasSource's own
    # keyword-matching (app/services/embassy_announcements.py) correctly
    # finds nothing on it, so fixing reachability alone does not make
    # this source produce records; recorded honestly as reachable-but-
    # likely-unsuitable rather than claimed as newly working.
    eswatini_slas_base_url: str = "https://slas.gov.sz"

    # Second-batch country-expansion sources (2026-08-23).
    italy_esteri_base_url: str = "https://www.esteri.it"
    # Italy's call-status page lives on a different host (a dedicated
    # applications subdomain) than the main ministry overview page above.
    italy_studyinitaly_base_url: str = "https://studyinitaly.esteri.it"
    greece_iky_base_url: str = "https://www.iky.gr"
    south_africa_nrf_base_url: str = "https://www.nrf.ac.za"

    # Third-batch country-expansion source (2026-08-29). Nuffic's "Study
    # in NL" portal - the NL Scholarship program was rebranded from
    # "Holland Scholarship"; hollandscholarship.nl now 301-redirects here.
    netherlands_nuffic_base_url: str = "https://www.studyinnl.org"
    spain_aecid_base_url: str = "https://www.aecid.es"
    # dfat.gov.au itself (the deadline-bearing authoritative domain) is
    # unreachable from this environment - a separate, DFAT-affiliated
    # informational site is used as the overview page instead. See
    # AustraliaDfatAwardsSource's own docstring for the full reachability
    # findings.
    australia_awards_base_url: str = "https://www.australiaawards.com.au"
    japan_mext_base_url: str = "https://www.studyinjapan.go.jp"

    # Fourth-batch country-expansion sources (2026-08-29), from a
    # dedicated research pass rather than a fetch-and-wire pass - see
    # docs/COUNTRY_PROVIDER_REGISTRY.md for what was checked and why
    # Canada/Denmark were investigated but not integrated.
    belgium_ares_base_url: str = "https://www.ares-ac.be"
    france_campusfrance_base_url: str = "https://www.campusfrance.org"
    austria_oead_base_url: str = "https://oead.at"
    morocco_amci_base_url: str = "https://www.amci.ma"
    portugal_camoes_base_url: str = "https://www.instituto-camoes.pt"
    colombia_icetex_base_url: str = "https://web.icetex.gov.co"
    chile_agcid_base_url: str = "https://www.agcid.gob.cl"
    peru_pronabec_base_url: str = "https://www.pronabec.gob.pe"
    south_korea_gks_base_url: str = "https://www.studyinkorea.go.kr"
    saudi_arabia_moe_base_url: str = "https://www.moe.gov.sa"
    qatar_scholarships_base_url: str = "https://www.qatarscholarships.qa"
    switzerland_sbfi_base_url: str = "https://www.sbfi.admin.ch"
    poland_nawa_base_url: str = "https://nawa.gov.pl"
    czech_republic_msmt_base_url: str = "https://msmt.gov.cz"
    serbia_welcometoserbia_base_url: str = "https://welcometoserbia.gov.rs"
    romania_mfa_base_url: str = "https://scholarships.studyinromania.gov.ro"
    hungary_stipendium_base_url: str = "https://stipendiumhungaricum.hu"
    mexico_amexcid_base_url: str = "https://www.gob.mx"

    # Twelfth-pass multi-source-type expansion (2026-08-30) - see
    # docs/COUNTRY_PROVIDER_REGISTRY.md's twelfth-pass note. Not tied to
    # a single destination country; found while researching additional
    # sources genuinely eligible for Sierra Leone applicants specifically.
    world_bank_jjwbgsp_base_url: str = "https://www.worldbank.org"
    rotary_peace_fellowship_base_url: str = "https://www.rotary.org"
    erasmus_mundus_base_url: str = "https://www.eacea.ec.europa.eu"
    uaeu_base_url: str = "https://www.uaeu.ac.ae"

    # Mastercard Foundation Scholars Program - re-investigated 2026-09-05
    # after the foundation's site restructure; see
    # app/services/mastercard_foundation_scholars_source.py's module
    # docstring for why this is now integrable (a plain static JSON asset,
    # not the client-side widget with no server-rendered fallback
    # previously documented in docs/AUTHORITATIVE_SOURCES.md).
    mastercard_foundation_base_url: str = "https://mastercardfdn.org"

    # Schwarzman Scholars (Tsinghua University) - fully-funded global
    # master's program, no ClaudeBot robots.txt restriction (unlike UWC,
    # researched the same session and rejected for exactly that reason).
    schwarzman_scholars_base_url: str = "https://www.schwarzmanscholars.org"

    # Knight-Hennessy Scholars (Stanford University) - fully-endowed
    # global graduate leadership program, no nationality restriction, no
    # ClaudeBot robots.txt restriction.
    knight_hennessy_scholars_base_url: str = "https://knight-hennessy.stanford.edu"

    # Yenching Academy of Peking University - fully-funded global master's
    # program, ~75% international student body, no nationality
    # restriction. No robots.txt file exists at all (confirmed 404, not a
    # bot-challenge page), which per RFC 9309 means no crawl restrictions.
    yenching_academy_base_url: str = "https://yenchingacademy.pku.edu.cn"

    # ETH Zurich Excellence Scholarship & Opportunity Programme (ESOP) -
    # fully-funded master's scholarship with no nationality restriction
    # mentioned anywhere on its eligibility page. No robots.txt file
    # exists at all (confirmed 404), treated as unrestricted per
    # RFC 9309, same reasoning as Yenching Academy above.
    eth_zurich_esop_base_url: str = "https://ethz.ch"

    # Hong Kong PhD Fellowship Scheme (HKPFS) - Research Grants Council of
    # Hong Kong, funding PhD study at eight Hong Kong universities.
    # Genuinely global: its eligibility text states candidates qualify
    # "irrespective of their country of origin, prior work experience and
    # ethnic background". robots.txt returns a genuine HTTP 404 (the
    # site's own "Not found" page, not a bot-challenge page) - no
    # robots.txt file exists at all, treated as unrestricted per RFC 9309,
    # same reasoning as Yenching Academy/ETH Zurich above.
    hkpfs_base_url: str = "https://cerg1.ugc.edu.hk"

    # TaiwanICDF International Higher Education Scholarship Program -
    # Taiwan International Cooperation and Development Fund, funding full
    # scholarships for students from Taiwan's diplomatic partner countries
    # to study at partner universities in Taiwan. robots.txt returns a
    # genuine HTTP 404 (nginx's own generic error page), treated as
    # unrestricted per RFC 9309, same reasoning as Yenching/ETH Zurich/
    # HKPFS above.
    taiwan_icdf_base_url: str = "https://www.icdf.org.tw"

    # Alexander von Humboldt Foundation - Humboldt Research Fellowship,
    # for postdoctoral and experienced researchers "of all nationalities
    # and research areas" to conduct research in Germany. robots.txt
    # allows this content path (only TYPO3 internal/print paths are
    # disallowed).
    humboldt_foundation_base_url: str = "https://www.humboldt-foundation.de"

    # Max Planck Schools - a joint doctoral program of German
    # universities and non-university research organizations (distinct
    # from the fully decentralized, no-central-deadline general Max
    # Planck Institute PhD route), open to "candidates from around the
    # world". robots.txt has no Disallow rules at all.
    max_planck_schools_base_url: str = "https://www.maxplanckschools.org"

    # TU Delft - Justus & Louise van Effen Excellence Scholarships, a
    # university-administered scholarship (full tuition + living-expense
    # contribution) for excellent international Master's applicants,
    # distinct from the Dutch government's NL Scholarship. robots.txt
    # allows this content path.
    tudelft_van_effen_base_url: str = "https://www.tudelft.nl"

    # Technical University of Munich (TUM) - Scholarship for
    # International Students, a Bavarian-government-funded but
    # university-administered need-based top-up grant (500-1,800 EUR
    # one-time per semester) for currently-enrolled international TUM
    # students who are ineligible for BAfoeG due to nationality - not a
    # scholarship for prospective/incoming applicants. robots.txt only
    # disallows TYPO3-internal paths.
    tum_international_scholarship_base_url: str = "https://www.tum.de"

    # Imperial College London - Imperial Inspires scholarships, a
    # partial scholarship (GBP 15,000/year, at least 300 awards) for
    # international (Overseas-fee) undergraduate and selected
    # postgraduate taught applicants for 2027 entry. robots.txt does not
    # disallow this content path.
    imperial_inspires_base_url: str = "https://www.imperial.ac.uk"

    # Newcastle University - Vice-Chancellor's International
    # Scholarships (Undergraduate), a partial (GBP 7,000/year) tuition
    # fee award for international undergraduate applicants from a
    # specific, explicitly-listed set of eligible countries/regions.
    # robots.txt only disallows specific old PDF files, not this page.
    newcastle_vcis_base_url: str = "https://www.ncl.ac.uk"

    # University of Sheffield - International Postgraduate Scholarship
    # 2027 (selected regions), a partial (GBP 7,000) tuition fee
    # reduction for taught postgraduate offer-holders from a specific,
    # explicitly-published list of countries/regions, awarded
    # automatically with no separate application. robots.txt is a
    # standard Drupal file that does not disallow this content path.
    sheffield_pg_scholarship_base_url: str = "https://sheffield.ac.uk"

    # University of Manchester - Global Futures Scholarships, "more than
    # 350 partial merit-based scholarships" open to both undergraduate
    # and master's (postgraduate taught) students for September 2027
    # entry, restricted to a specific published list of countries.
    # robots.txt does not disallow this content path.
    manchester_gfs_base_url: str = "https://www.manchester.ac.uk"

    # University of Nottingham - International Postgraduate
    # Scholarship, an automatic tuition-fee deduction for
    # self-funded international postgraduate taught Master's students
    # with no country restriction and no year-locked cycle stated on
    # this page. robots.txt only disallows internal search-result
    # paths.
    nottingham_pg_scholarship_base_url: str = "https://www.nottingham.ac.uk"

    # University of Southampton - Presidential bursaries, a PhD-level
    # fee-difference bursary open to all international candidates
    # (no country restriction), automatically applied by the Faculty.
    # robots.txt does not disallow this content path.
    southampton_presidential_bursaries_base_url: str = "https://www.southampton.ac.uk"

    # University of Southampton - Merit scholarships for international
    # undergraduates, up to GBP 4,500 off first-year tuition for
    # exceeding academic offer conditions, automatically awarded with
    # no separate application and no country restriction.
    southampton_merit_ug_base_url: str = "https://www.southampton.ac.uk"

    # Durham University - Inspiring Excellence Scholarships, partial
    # tuition-fee-discount scholarships for self-funded international
    # students with no country restriction, one page each for
    # undergraduate and postgraduate (taught Master's) level. Both pages
    # state explicit "1st round application deadline" dates for 2027
    # entry. robots.txt does not disallow this content path.
    durham_inspiring_excellence_ug_base_url: str = "https://www.durham.ac.uk"
    durham_inspiring_excellence_pg_base_url: str = "https://www.durham.ac.uk"

    # University of Freiburg - Deutschlandstipendium ("Germany
    # Scholarship"), a EUR 300/month, one-year public-private stipend
    # open to undergraduate AND Master's students of all nationalities
    # (no country restriction) enrolled at the university. Genuinely
    # covers this platform's "postgraduate/masters" and "undergraduate"
    # request in a single page, unlike the England sources above which
    # needed one page per level. robots.txt does not disallow this
    # content path.
    freiburg_deutschlandstipendium_base_url: str = "https://uni-freiburg.de"

    # University of Amsterdam - Amsterdam Merit Scholarship (AMS), a
    # non-EU/EEA-only merit scholarship with separate overview pages for
    # Master's and Bachelor's level. Deadlines/amounts vary per Faculty
    # or Graduate School (stated directly on this general overview page),
    # so none is asserted here. robots.txt is a genuine empty file (200,
    # zero bytes) - no restrictions declared at all.
    uva_amsterdam_merit_scholarship_master_base_url: str = "https://www.uva.nl"
    uva_amsterdam_merit_scholarship_bachelor_base_url: str = "https://www.uva.nl"

    # University of Groningen - Eric Bleumink Fellowship, a genuinely
    # fully-funded (tuition + international travel + subsistence + books
    # + health insurance) Master's grant restricted to an explicit list
    # of ~80 named developing countries that includes Sierra Leone
    # (confirmed directly, not assumed from "developing countries").
    # Nomination-based (no separate scholarship application - applying
    # to a UG Master's programme by 1 December is what gets you
    # considered), administered entirely by UG's own Admission Office,
    # unlike Vanier Canada's third-party-institution nomination model
    # documented elsewhere as unsuitable. robots.txt does not disallow
    # this content path.
    groningen_eric_bleumink_fellowship_base_url: str = "https://www.rug.nl"

    # Utrecht University - Law, Economics and Governance International
    # Talent Scholarship (LEGITS), a tuition-fee scholarship for the
    # Graduate Schools of Law and Economics, open to both EU/EEA and
    # non-EU/EEA applicants, for the currently-live September 2027
    # intake. Utrecht's central Utrecht Excellence Scholarship was
    # confirmed discontinued for 2026-2027 entry onward ("due to
    # significant budget cuts") and is not used instead. robots.txt does
    # not disallow this content path.
    utrecht_legits_scholarship_base_url: str = "https://www.uu.nl"

    # Maastricht University - UM NL-High Potential Scholarship, a
    # genuinely fully-funded (tuition waiver + monthly stipend) Master's
    # scholarship for non-EU/EEA/Switzerland/Suriname applicants. Already
    # updated for the 2027-2028 academic year with a real, not-yet-passed
    # deadline (10 December 2026) as of this research date. robots.txt
    # does not disallow this content path.
    maastricht_high_potential_scholarship_base_url: str = (
        "https://www.maastrichtuniversity.nl"
    )

    # University of Twente Scholarship (UTS), a cash-award (not tuition-
    # deducted) scholarship of EUR 3,000-22,000/year for non-EU/EEA
    # Master's applicants, with an explicit "Countries eligible for this
    # scholarship" list confirmed to include Sierra Leone. Already
    # updated for the 2027/2028 intake with a real, not-yet-passed
    # deadline (1 April 2027) as of this research date. robots.txt does
    # not disallow this content path.
    utwente_scholarship_base_url: str = "https://www.utwente.nl"

    # Wageningen University & Research - Anne van den Ban Fund, a
    # nomination-based (no direct application) partial-or-full Master's
    # scholarship for students from low-income countries, selected
    # annually each spring from already-admitted MSc applicants.
    # robots.txt does not disallow this content path.
    wageningen_anne_van_den_ban_fund_base_url: str = "https://www.wur.nl"

    # University of Twente - ITC Excellence Scholarship Programme, a
    # partial scholarship from the Faculty of Geo-Information Science
    # and Earth Observation (ITC) for two specific Master's programmes,
    # restricted to an explicit country list confirmed to include
    # Sierra Leone. A distinct scholarship from the university-wide UTS
    # already added - administered by ITC specifically, with its own
    # eligibility/cost-breakdown page. robots.txt does not disallow this
    # content path.
    utwente_itc_scholarship_base_url: str = "https://www.utwente.nl"

    # UPF Barcelona School of Management (Universitat Pompeu Fabra) -
    # Merit Based Scholarship, a rolling, multi-round partial tuition
    # scholarship (25%, up to 50% with demonstrated financial need) for
    # Master of Science candidates, no nationality restriction. This
    # platform's first Spain-university source (the existing Spain
    # source, #23, is the government-classified Becas MAEC-AECID).
    # robots.txt does not disallow this content path.
    upf_bsm_merit_scholarship_base_url: str = "https://www.bsm.upf.edu"

    # Sciences Po - Mastercard Foundation Scholars Program (graduate/
    # Master's track): a genuinely fully funded scholarship - "The
    # Program covers the full financial needs of selected Scholars" plus
    # "cover[s] the full cost of tuition and living expenses in France"
    # and reserved Paris housing - for citizens of any African country
    # admitted to a two-year Master's at Sciences Po (one-year Master's
    # and dual-degree programmes are not eligible). This platform's
    # first France-university source; France Excellence Eiffel remains
    # deliberately excluded as a government/Campus France programme, not
    # a university-only scholarship. robots.txt does not disallow this
    # content path.
    sciencespo_mastercard_scholars_base_url: str = "https://www.sciencespo.fr"

    # Peking University Scholarship for International Students -
    # genuinely fully funded ("It covers tuition, a living stipend and
    # medical insurance"), open to Master's applicants (2-3 year
    # duration) with no nationality/country restriction stated beyond
    # ordinary PKU international-admission requirements. This
    # platform's first China-university source (Schwarzman Scholars and
    # Yenching Academy, sources #50/#52, are elite named programs
    # hosted at Tsinghua/PKU respectively, not this general
    # institution-wide scholarship). robots.txt does not exist on this
    # host (404, no Disallow rules).
    pku_international_scholarship_base_url: str = "https://isd.pku.edu.cn"

    # Shanghai Jiao Tong University - Master's SJTU Scholarship:
    # genuinely fully funded ("Monthly stipend, standard tuition
    # waiver, group comprehensive insurance in China, and accommodation
    # subsidy"), distinct from SJTU's own separately-named Tuition
    # Waiver Scholarship (tuition + insurance only, no stipend - not
    # integrated, see docs). This platform's second China-university
    # source. robots.txt does not exist on this host (404, no Disallow
    # rules).
    sjtu_masters_scholarship_base_url: str = "https://global.sjtu.edu.cn"

    # McGill University - Mastercard Foundation Scholars Program:
    # genuinely fully funded ("Full international student tuition, On-
    # campus housing, Personal monthly stipend," plus book allowance
    # and return flight), for citizens/residents of any African country
    # (an explicit ~54-country eligible list on McGill's own site names
    # Sierra Leone) admitted to one of 13 eligible graduate programmes
    # (nutrition, public health, public policy, sustainable
    # agriculture). This platform's first Canada source of any kind -
    # Canada was previously found NOT_SUITABLE at the national/
    # government level (EduCanada's Study in Canada Scholarships is
    # institution-initiated, not individually-applicable), a finding
    # that remains correct and unaffected; this is a university-
    # administered source instead, the same pattern already used for
    # Sciences Po's and McGill's own Mastercard Foundation partnership.
    # robots.txt (`mcgill.ca/robots.txt`) does not disallow this
    # content path.
    mcgill_mastercard_scholars_base_url: str = "https://www.mcgill.ca"

    # Gates Cambridge Scholarship (University of Cambridge / Gates
    # Cambridge Trust): genuinely fully funded - "covers the full cost
    # of studying at Cambridge" (University Composition Fee/tuition,
    # a maintenance allowance, one economy return airfare, inbound visa
    # costs and the Immigration Health Surcharge). Open to "a citizen of
    # any country outside the United Kingdom" with no narrower list -
    # worldwide eligibility, Sierra Leone included. Funds one-year
    # postgraduate courses (Master's-level, e.g. MPhil) and MLitt, not
    # only PhD. This platform's first England-university source
    # classified as genuinely fully funded (the nine pre-existing
    # England sources - Imperial, Newcastle, Sheffield, Manchester,
    # Nottingham, Southampton x2, Durham x2 - are all
    # `partial_funding`). Note: Oxford's Clarendon Fund was also
    # researched as an equally strong candidate but `ox.ac.uk` (every
    # path tested, including robots.txt) returns an active Cloudflare
    # "Just a moment..." managed challenge - genuine bot protection,
    # not bypassed; Clarendon remains unimplemented for that reason,
    # not a funding concern. `gatescambridge.org/robots.txt` only
    # disallows `/wp-admin/`, unrelated to this content path.
    gates_cambridge_scholarship_base_url: str = "https://www.gatescambridge.org"

    # Premium Application-Preparation Platform - payment provider
    # abstraction (app/services/payment_provider.py). Left unset by
    # default: an empty `payment_provider` selects `NullPaymentProvider`,
    # which clearly reports "not configured" on every call rather than
    # fabricating a successful transaction - see that module's docstring.
    # The real provider (Stripe/Paystack/Flutterwave/...) and its
    # credentials are supplied later; nothing here assumes which one.
    payment_provider: str = ""
    payment_env: str = "test"
    payment_secret_key: SecretStr = SecretStr("")
    payment_public_key: str = ""
    payment_webhook_secret: SecretStr = SecretStr("")
    payment_currency: str = "USD"
    payment_api_base_url: str = ""

    # The flagship "Complete Premium Application Package" - seeded once at
    # startup (app/services/premium_plan_seed.py) if no plan with this
    # code exists yet, then fully admin-editable afterward (price
    # included). These two env vars only control the *seed*, never a
    # runtime price override - the database row is the single source of
    # truth from that point on.
    premium_plan_id: str = "complete_premium"
    premium_price_cents: int = Field(default=10_000, ge=0)

    # AI provider abstraction (app/services/ai_provider.py). Left unset by
    # default: an empty `ai_provider` selects `NullAIProvider`, which
    # clearly reports "AI generation is not configured" rather than
    # fabricating document content - see that module's docstring.
    ai_provider: str = ""
    ai_api_key: SecretStr = SecretStr("")
    ai_model: str = ""
    ai_api_base_url: str = ""
    ai_request_timeout_seconds: float = Field(default=60.0, gt=0, le=180)
    # Configurable AI-usage ceilings (app/services/usage_limits.py) - the
    # database `usage_limits` table can override these per feature; these
    # are only the defaults applied when no row exists yet for a feature.
    ai_usage_daily_limit_default: int = Field(default=20, gt=0)
    ai_usage_monthly_limit_default: int = Field(default=200, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator(
        "allowed_origins",
        "eu_funding_type_codes",
        "eu_funding_status_codes",
        "eu_funding_display_fields",
        "daad_scholarship_detail_ids",
        mode="before",
    )
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("firebase_credentials_path", mode="before")
    @classmethod
    def blank_firebase_credentials_path_is_unset(cls, value: object) -> object:
        # A `.env` file with `FIREBASE_CREDENTIALS_PATH=` (present but
        # blank - the common way to document a var as "available to set"
        # without setting it) would otherwise coerce to `Path('.')`, the
        # current working directory - truthy, and not None, so both the
        # production-file-exists check below and initialize_firebase()'s
        # own `if settings.firebase_credentials_path:` check
        # (app/core/auth.py) would wrongly treat "blank" as "configured".
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "eu_funding_type_mappings",
        "eu_funding_status_mappings",
        mode="before",
    )
    @classmethod
    def split_mapping(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        mappings: dict[str, str] = {}
        for item in value.split(","):
            key, separator, mapped_value = item.partition(":")
            if separator and key.strip() and mapped_value.strip():
                mappings[key.strip()] = mapped_value.strip()
        return mappings

    @field_validator(
        "grants_gov_base_url",
        "simpler_grants_base_url",
        "eu_funding_api_url",
        "usajobs_base_url",
        "reliefweb_base_url",
        "educationusa_base_url",
        "cscuk_base_url",
        "chevening_base_url",
        "daad_base_url",
        "china_embassy_sl_base_url",
        "mthe_sl_base_url",
        "wmi_base_url",
        "turkiye_burslari_base_url",
        "ireland_hea_base_url",
        "india_iccr_base_url",
        "sweden_si_base_url",
        "eswatini_slas_base_url",
        "italy_esteri_base_url",
        "italy_studyinitaly_base_url",
        "greece_iky_base_url",
        "south_africa_nrf_base_url",
        "netherlands_nuffic_base_url",
        "spain_aecid_base_url",
        "australia_awards_base_url",
        "japan_mext_base_url",
        "belgium_ares_base_url",
        "france_campusfrance_base_url",
        "austria_oead_base_url",
        "morocco_amci_base_url",
        "portugal_camoes_base_url",
        "colombia_icetex_base_url",
        "chile_agcid_base_url",
        "peru_pronabec_base_url",
        "south_korea_gks_base_url",
        "saudi_arabia_moe_base_url",
        "qatar_scholarships_base_url",
        "switzerland_sbfi_base_url",
        "poland_nawa_base_url",
        "czech_republic_msmt_base_url",
        "serbia_welcometoserbia_base_url",
        "romania_mfa_base_url",
        "hungary_stipendium_base_url",
        "mexico_amexcid_base_url",
        "world_bank_jjwbgsp_base_url",
        "rotary_peace_fellowship_base_url",
        "erasmus_mundus_base_url",
        "uaeu_base_url",
        "mastercard_foundation_base_url",
        "schwarzman_scholars_base_url",
        "knight_hennessy_scholars_base_url",
        "yenching_academy_base_url",
        "eth_zurich_esop_base_url",
        "hkpfs_base_url",
        "taiwan_icdf_base_url",
        "humboldt_foundation_base_url",
        "max_planck_schools_base_url",
        "tudelft_van_effen_base_url",
        "tum_international_scholarship_base_url",
        "imperial_inspires_base_url",
        "newcastle_vcis_base_url",
        "sheffield_pg_scholarship_base_url",
        "manchester_gfs_base_url",
        "nottingham_pg_scholarship_base_url",
        "southampton_presidential_bursaries_base_url",
        "southampton_merit_ug_base_url",
        "durham_inspiring_excellence_ug_base_url",
        "durham_inspiring_excellence_pg_base_url",
        "freiburg_deutschlandstipendium_base_url",
        "uva_amsterdam_merit_scholarship_master_base_url",
        "uva_amsterdam_merit_scholarship_bachelor_base_url",
        "groningen_eric_bleumink_fellowship_base_url",
        "utrecht_legits_scholarship_base_url",
        "maastricht_high_potential_scholarship_base_url",
        "utwente_scholarship_base_url",
        "wageningen_anne_van_den_ban_fund_base_url",
        "utwente_itc_scholarship_base_url",
        "upf_bsm_merit_scholarship_base_url",
        "sciencespo_mastercard_scholars_base_url",
        "pku_international_scholarship_base_url",
        "sjtu_masters_scholarship_base_url",
        "mcgill_mastercard_scholars_base_url",
        "gates_cambridge_scholarship_base_url",
    )
    @classmethod
    def require_https(cls, value: str) -> str:
        if not value.lower().startswith("https://"):
            raise ValueError("External API endpoints must use HTTPS")
        return value.rstrip("/")

    @field_validator("payment_api_base_url", "ai_api_base_url")
    @classmethod
    def require_https_when_set(cls, value: str) -> str:
        # Unlike require_https above, these two are legitimately blank
        # (no provider configured yet) - only enforce HTTPS once a real
        # value is actually supplied.
        if value and not value.lower().startswith("https://"):
            raise ValueError("External API endpoints must use HTTPS")
        return value.rstrip("/") if value else value

    @model_validator(mode="after")
    def enforce_revocation_checking_in_production(self) -> "Settings":
        # Token-revocation checking must never be disabled in production,
        # regardless of what FIREBASE_CHECK_REVOKED is set to in the
        # environment -- disabling it lets a disabled/suspended Firebase
        # account keep using an already-issued token until it naturally
        # expires. The env var only exists so local/demo runs without a
        # service account can skip the Identity Toolkit call.
        if self.app_env == "production" and not self.firebase_check_revoked:
            self.firebase_check_revoked = True
        return self

    @model_validator(mode="after")
    def enforce_headless_browser_rendering_in_production(self) -> "Settings":
        # A headed (non-headless) browser needs a display server that no
        # production/container deployment has - PLAYWRIGHT_HEADLESS=false
        # only ever makes sense on a developer's own machine while
        # debugging a specific source's rendering.
        if self.app_env == "production" and not self.browser_render_headless:
            self.browser_render_headless = True
        return self

    @model_validator(mode="after")
    def reject_placeholder_infrastructure_credentials_in_production(
        self,
    ) -> "Settings":
        # These two defaults only exist so the app can boot without any
        # infrastructure for local dev/tests. A managed secret store (AWS
        # Secrets Manager, GCP Secret Manager, Vault, ...) should inject the
        # real DATABASE_URL/REDIS_URL as environment variables in
        # production -- refuse to start rather than silently run against a
        # placeholder credential or an unintended local service.
        if self.app_env != "production":
            return self
        problems: list[str] = []
        if "change-me" in self.database_url:
            problems.append(
                "DATABASE_URL still contains the placeholder 'change-me' credential"
            )
        if self.redis_url == "redis://localhost:6379/0":
            problems.append("REDIS_URL is still the local-development default")
        if self.firebase_credentials_path is not None and not self.firebase_credentials_path.is_file():
            problems.append(
                "FIREBASE_CREDENTIALS_PATH is set to "
                f"'{self.firebase_credentials_path}' but that file does not "
                "exist. Either point it at a real service-account JSON key, "
                "or unset it entirely to use Application Default "
                "Credentials (only correct if this deployment runs on GCP "
                "infrastructure with a service account attached)."
            )
        if problems:
            raise ValueError(
                "Refusing to start with app_env=production and insecure "
                "defaults: " + "; ".join(problems) + ". Inject real values "
                "from a managed secret store as environment variables."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

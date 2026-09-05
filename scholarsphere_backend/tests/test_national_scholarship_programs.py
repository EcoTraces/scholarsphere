from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.core.http_client import ExternalAPIError
from app.services import web_scraper_base
from app.services.national_scholarship_programs import (
    AustraliaDfatAwardsSource,
    AustriaOeadErnstMachSource,
    BelgiumAresScholarshipSource,
    ChileAgcidScholarshipSource,
    ColombiaIcetexBecaExtranjerosSource,
    CzechRepublicMsmtScholarshipSource,
    FranceEiffelScholarshipSource,
    GreeceIkyScholarshipSource,
    HungaryStipendiumHungaricumSource,
    IndiaIccrSource,
    IrelandGoiIesSource,
    ItalyMaeciScholarshipSource,
    JapanMextScholarshipSource,
    MexicoAmexcidScholarshipSource,
    MoroccoAmciScholarshipSource,
    NetherlandsNufficScholarshipSource,
    PeruPronabecAlianzaPacificoSource,
    PolandNawaMyFirstChoiceSource,
    PortugalCamoesScholarshipSource,
    QatarScholarshipsSource,
    RomaniaMfaScholarshipSource,
    SaudiArabiaMoeScholarshipSource,
    SerbiaWorldInSerbiaScholarshipSource,
    SouthAfricaNrfScholarshipSource,
    SouthKoreaGksScholarshipSource,
    SpainAecidScholarshipSource,
    SwedishInstituteScholarshipSource,
    SwitzerlandEskasScholarshipSource,
    RotaryPeaceFellowshipSource,
    SchwarzmanScholarsSource,
    TurkiyeBurslariSource,
    WellsMountainInitiativeSource,
    WorldBankJJWBGSPScholarshipSource,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- Wells Mountain Initiative: real fixture, fetched 2026-08-22/23 -----


@pytest.mark.asyncio
async def test_wmi_collect_normalizes_real_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    source = WellsMountainInitiativeSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("wmi_prospective_scholars.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "wmi-scholars-program"
    assert opportunity.title == "2026 Scholarship Application"
    assert opportunity.description is not None
    assert opportunity.opportunity_type == "scholarship"
    assert opportunity.provider_name == "Wells Mountain Initiative (WMI)"
    assert opportunity.country is None
    assert opportunity.verification_status == "pending"
    assert opportunity.publication_status == "unpublished"


@pytest.mark.asyncio
async def test_wmi_resyncing_uses_the_same_external_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One recurring annual program - a stable id means a changed
    deadline updates the same record rather than duplicating it."""
    source = WellsMountainInitiativeSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("wmi_prospective_scholars.html")),
    )

    first = await source.collect()
    second = await source.collect()

    assert first[0].external_id == second[0].external_id == "wmi-scholars-program"


@pytest.mark.asyncio
async def test_wmi_overview_fetch_failure_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WellsMountainInitiativeSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(side_effect=ExternalAPIError("temporarily unavailable")),
    )

    assert await source.collect() == []


# --- Türkiye Bursları: real fixtures, fetched 2026-08-23 -----------------


@pytest.mark.asyncio
async def test_turkiye_collect_normalizes_real_fixture_and_extracts_real_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real fixture text states 'Application Dates: 10 January - 20
    February 2026' - the closing date (20 February 2026) is the one
    genuine day+month+year literal in that phrase, so keyword-anchored
    extraction should find exactly that."""
    source = TurkiyeBurslariSource()
    overview_url = f"{source.base_url}{source.overview_path}"
    deadline_url = f"{source.base_url}{source.deadline_path}"

    async def fake_get_html(url: str, **_: object) -> str:
        if url == overview_url:
            return _fixture("turkiye_burslari_programs.html")
        if url == deadline_url:
            return _fixture("turkiye_burslari_announcement.html")
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "turkiye-burslari-scholarship"
    assert opportunity.country == "Turkey"
    assert opportunity.deadline is not None
    assert str(opportunity.deadline) == "2026-02-20"


@pytest.mark.asyncio
async def test_turkiye_deadline_page_failure_still_returns_opportunity_without_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = TurkiyeBurslariSource()
    overview_url = f"{source.base_url}{source.overview_path}"

    async def fake_get_html(url: str, **_: object) -> str:
        if url == overview_url:
            return _fixture("turkiye_burslari_programs.html")
        raise ExternalAPIError("temporarily unavailable")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) == 1
    assert result[0].deadline is None


# --- Ireland GOI-IES: real fixture, fetched 2026-08-23 -------------------


@pytest.mark.asyncio
async def test_ireland_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = IrelandGoiIesSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("ireland_hea_goi_ies.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "ireland-goi-ies-scholarship"
    assert opportunity.title == "Government of Ireland International Education Scholarships"
    assert opportunity.description is not None
    assert opportunity.country == "Ireland"
    assert opportunity.provider_name == "Higher Education Authority (Government of Ireland)"
    assert opportunity.verification_status == "pending"


# --- India ICCR: real fixture, fetched 2026-08-23 -------------------------


@pytest.mark.asyncio
async def test_india_iccr_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = IndiaIccrSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("india_iccr_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "india-iccr-scholarship-programme"
    assert opportunity.title == "ICCR Scholarship Programme"
    assert opportunity.country == "India"
    assert "Government of India" in opportunity.provider_name


# --- Swedish Institute: real fixture, fetched 2026-08-23 ------------------


@pytest.mark.asyncio
async def test_sweden_si_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SwedishInstituteScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("sweden_si_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "sweden-si-scholarship-global-professionals"
    assert opportunity.country == "Sweden"
    assert opportunity.provider_name == "Swedish Institute (Svenska institutet)"


# --- Italy MAECI: real fixtures, fetched 2026-08-23 -----------------------


@pytest.mark.asyncio
async def test_italy_collect_normalizes_real_fixture_from_two_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Overview page (esteri.it) and deadline/call-status page
    (studyinitaly.esteri.it) are on two different hosts - confirms the
    _deadline_base_url override actually gets used."""
    source = ItalyMaeciScholarshipSource()
    overview_url = f"{source.base_url}{source.overview_path}"
    deadline_url = f"{source._deadline_base_url()}{source.deadline_path}"
    assert "esteri.it" in overview_url and "studyinitaly" not in overview_url
    assert "studyinitaly.esteri.it" in deadline_url

    async def fake_get_html(url: str, **_: object) -> str:
        if url == overview_url:
            return _fixture("italy_maeci_overview.html")
        if url == deadline_url:
            return _fixture("italy_maeci_bandi.html")
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "italy-maeci-scholarships"
    assert (
        opportunity.title
        == "Scholarships for foreign students and Italian citizens living abroad awarded by the Italian Government"
    )
    assert opportunity.country == "Italy"
    assert opportunity.description is not None
    # The real fixture states the 2025-2026 call is closed with no new
    # date announced yet - correctly left null, not guessed.
    assert opportunity.deadline is None


@pytest.mark.asyncio
async def test_italy_deadline_host_failure_still_returns_opportunity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ItalyMaeciScholarshipSource()
    overview_url = f"{source.base_url}{source.overview_path}"

    async def fake_get_html(url: str, **_: object) -> str:
        if url == overview_url:
            return _fixture("italy_maeci_overview.html")
        raise ExternalAPIError("temporarily unavailable")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) == 1
    assert result[0].deadline is None


# --- Greece IKY: real fixture, fetched 2026-08-23 --------------------------


@pytest.mark.asyncio
async def test_greece_iky_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = GreeceIkyScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("greece_iky_foreign_nationals.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "greece-iky-foreign-nationals-scholarships"
    assert opportunity.title == "Foreign Nationals Scholarships"
    assert opportunity.country == "Greece"
    assert opportunity.provider_name == "State Scholarships Foundation (IKY), Greece"
    # The real fixture's text is informational (references an old
    # 2017-2018 cycle, says postgraduate scholarships are "not open for
    # this year") with no current date literal - correctly null.
    assert opportunity.deadline is None


# --- South Africa NRF: real fixture, fetched 2026-08-23 --------------------


@pytest.mark.asyncio
async def test_south_africa_nrf_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SouthAfricaNrfScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("south_africa_nrf_funding.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "south-africa-nrf-postgraduate-funding"
    assert "2027" in opportunity.title
    assert opportunity.country == "South Africa"
    assert opportunity.description is not None
    assert "DSTI and NRF" in opportunity.description


def test_south_africa_nrf_never_attempts_deadline_extraction() -> None:
    """Deliberate design choice, not an oversight - the real page has a
    table of many distinct per-programme deadlines; a generic
    keyword-anchored extractor would pick one row and mislabel it as
    THE deadline. Locks in that deadline_keywords stays empty."""
    assert SouthAfricaNrfScholarshipSource.deadline_keywords == ()


# --- Netherlands Nuffic NL Scholarship: real fixture, fetched 2026-08-29 --


@pytest.mark.asyncio
async def test_netherlands_nuffic_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = NetherlandsNufficScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("netherlands_nuffic_nl_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "netherlands-nuffic-nl-scholarship"
    assert opportunity.title == "NL Scholarship"
    assert opportunity.country == "Netherlands"
    assert opportunity.provider_name == "Nuffic"
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.description is not None
    assert "5,000" in opportunity.description or "5.000" in opportunity.description
    # The real page states closing dates vary by participating
    # institution and does not publish one program-wide deadline -
    # correctly null, not extracted from an unrelated date on the page.
    assert opportunity.deadline is None


def test_netherlands_nuffic_never_attempts_deadline_extraction() -> None:
    """Same reasoning as South Africa NRF above: Nuffic's own page states
    closing dates are set per participating institution (~30 of them),
    not by Nuffic itself. Locks in that deadline_keywords stays empty."""
    assert NetherlandsNufficScholarshipSource.deadline_keywords == ()


def test_netherlands_nuffic_is_not_labeled_fully_funded() -> None:
    """The real page states outright this is a fixed EUR 5,000 award and
    explicitly "not a full-tuition scholarship" - must not inherit
    _SingleProgramSource's fully_funded default."""
    assert NetherlandsNufficScholarshipSource.funding_type == "partial_funding"


# --- Spain AECID: real fixture, fetched 2026-08-29 -------------------------


@pytest.mark.asyncio
async def test_spain_aecid_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SpainAecidScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("spain_aecid_scholarships.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "spain-aecid-scholarships"
    assert opportunity.title == (
        "Becas para ciudadanos de países de América Latina, África y Asia"
    )
    assert opportunity.country == "Spain"
    assert opportunity.provider_name == (
        "Spanish Agency for International Development Cooperation (AECID)"
    )
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.description is not None
    # The real fixture lists several sub-programs, each with its own
    # start/close date - correctly null, not one sub-program's date
    # misattributed to the whole page.
    assert opportunity.deadline is None


def test_spain_aecid_never_attempts_deadline_extraction() -> None:
    """Same reasoning as South Africa NRF and the Netherlands above: the
    real page lists multiple named sub-programs, each with its own
    distinct closing date, not one program-wide deadline."""
    assert SpainAecidScholarshipSource.deadline_keywords == ()


# --- Australia DFAT Awards: real fixture, fetched 2026-08-29 ---------------


@pytest.mark.asyncio
async def test_australia_dfat_awards_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = AustraliaDfatAwardsSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("australia_dfat_awards.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "australia-dfat-awards"
    assert opportunity.title == "Australia Awards"
    assert opportunity.country == "Australia"
    assert opportunity.provider_name == (
        "Department of Foreign Affairs and Trade (DFAT), Australia"
    )
    assert opportunity.description is not None
    assert "international students" in opportunity.description.lower()
    # dfat.gov.au (the actual deadline-bearing page) could not be reached
    # from this environment - correctly null, not fabricated, and no
    # deadline_path was configured to point at an unverified host.
    assert opportunity.deadline is None


def test_australia_dfat_awards_never_attempts_deadline_extraction() -> None:
    """The authoritative deadline page (dfat.gov.au) is unreachable from
    this environment (see the adapter's own docstring for the specific
    failure mode) - deadline_keywords stays empty rather than guessing
    from the reachable overview site, which states no date itself."""
    assert AustraliaDfatAwardsSource.deadline_keywords == ()


def test_australia_dfat_awards_does_not_assert_a_funding_classification() -> None:
    """No "fully funded"/"tuition"/"stipend" language was found on the
    pages this adapter can actually read - funding_type must stay None
    rather than inheriting _SingleProgramSource's fully_funded default or
    guessing from general knowledge of the real-world program."""
    assert AustraliaDfatAwardsSource.funding_type is None


# --- Japan MEXT Scholarship: real fixture, fetched 2026-08-29 --------------


@pytest.mark.asyncio
async def test_japan_mext_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = JapanMextScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("japan_mext_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "japan-mext-scholarship"
    assert opportunity.title == "Japanese Government (MEXT) Scholarship"
    assert opportunity.country == "Japan"
    assert opportunity.provider_name == (
        "Ministry of Education, Culture, Sports, Science and Technology "
        "(MEXT), Japan"
    )
    # Confirmed by the real fixture's own text ("tuition exempted",
    # "round-trip travel expenses (airfare) provided", a monthly
    # stipend) - unlike Australia Awards above, this classification is
    # actually verified by the source text, not left unasserted.
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.description is not None
    # Applications route through the applicant's home-country embassy or
    # university, each on its own schedule - no single global deadline
    # is published, correctly null rather than guessed.
    assert opportunity.deadline is None


def test_japan_mext_never_attempts_deadline_extraction() -> None:
    """Same reasoning as Ireland GOI-IES and Sweden SI: applications are
    embassy/university-mediated with no single centrally published
    deadline."""
    assert JapanMextScholarshipSource.deadline_keywords == ()


def test_japan_mext_title_uses_fullwidth_separator_not_shared_h1() -> None:
    """Every page under this section of the site shares the same generic
    <h1>Scholarships</h1> section heading - relying on it would produce
    an unhelpfully vague title for every MEXT/JASSO/other-scholarship
    page alike, so this source forces the <title> tag fallback instead,
    split on the site's own fullwidth vertical bar (U+FF5C), not the
    ASCII pipe."""
    assert JapanMextScholarshipSource.title_selectors == ()
    assert JapanMextScholarshipSource.title_tag_separator == "｜"


# --- Belgium ARES: real fixture, fetched 2026-08-29 -------------------------


@pytest.mark.asyncio
async def test_belgium_ares_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = BelgiumAresScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("belgium_ares_bourses.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "belgium-ares-international-training-scholarships"
    assert opportunity.title == "Bourses de formations internationales"
    assert opportunity.country == "Belgium"
    assert opportunity.funding_type is None
    assert opportunity.description is not None
    # The real fixture states "Date limite : 18.09.2026" - a real
    # deadline, but in a DD.MM.YYYY numeric form the shared date
    # extractor does not parse - correctly null, not a fabricated guess
    # at reformatting it.
    assert opportunity.deadline is None


def test_belgium_ares_never_attempts_deadline_extraction() -> None:
    assert BelgiumAresScholarshipSource.deadline_keywords == ()


# --- France Eiffel: real fixture, fetched 2026-08-29 ------------------------


@pytest.mark.asyncio
async def test_france_eiffel_collect_normalizes_real_fixture_and_extracts_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = FranceEiffelScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("france_campus_france_eiffel.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "france-eiffel-excellence-scholarship"
    assert opportunity.title == "France Excellence Eiffel scholarship program"
    assert opportunity.country == "France"
    assert opportunity.funding_type is None
    assert opportunity.description is not None
    # The real fixture states a real, parseable deadline: "Deadline for
    # the reception of applications by Campus France: January 8, 2026".
    assert opportunity.deadline == date(2026, 1, 8)


# --- Austria OeAD Ernst Mach Grant: real fixture, fetched 2026-08-29 --------


@pytest.mark.asyncio
async def test_austria_oead_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = AustriaOeadErnstMachSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("austria_oead_ernst_mach.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "austria-oead-ernst-mach-grant"
    assert opportunity.title == "Ernst Mach Grant"
    assert opportunity.country == "Austria"
    assert opportunity.funding_type is None
    assert opportunity.description is not None
    # The real fixture describes several distinct named sub-grants (
    # Ukraine, worldwide, Fachhochschule, Follow-Up, ASEA-UNINET, ...),
    # each with its own closing date and, for at least one, its own
    # distinct monthly amount - correctly null rather than misattributing
    # one sub-grant's figures to the whole page.
    assert opportunity.deadline is None


def test_austria_oead_never_attempts_deadline_extraction() -> None:
    assert AustriaOeadErnstMachSource.deadline_keywords == ()


# --- Morocco AMCI: real fixture, fetched 2026-08-29 -------------------------


@pytest.mark.asyncio
async def test_morocco_amci_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = MoroccoAmciScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("morocco_amci_cooperation.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "morocco-amci-scholarships"
    assert opportunity.title == "Coopération Académique"
    assert opportunity.country == "Morocco"
    assert opportunity.funding_type is None
    assert opportunity.description is not None
    # Embassy-mediated applications, same honest pattern as Japan MEXT -
    # no single global deadline is published on the official page.
    assert opportunity.deadline is None


def test_morocco_amci_never_attempts_deadline_extraction() -> None:
    assert MoroccoAmciScholarshipSource.deadline_keywords == ()


def test_morocco_amci_title_uses_ascii_pipe_separator_not_missing_h1() -> None:
    """The page has no <h1> at all - the real title comes from the
    <title> tag ("Coopération Académique | AMCI"), split on the ASCII
    pipe."""
    assert MoroccoAmciScholarshipSource.title_selectors == ()
    assert MoroccoAmciScholarshipSource.title_tag_separator == "|"


# --- Portugal Camões: real fixture, fetched 2026-08-29 ----------------------


@pytest.mark.asyncio
async def test_portugal_camoes_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = PortugalCamoesScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("portugal_camoes_formacao.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "portugal-camoes-cooperation-scholarships"
    assert opportunity.title == "Formação em Portugal"
    assert opportunity.country == "Portugal"
    assert opportunity.provider_name == (
        "Camões – Instituto da Cooperação e da Língua, I.P. (Portugal)"
    )
    assert opportunity.description is not None
    assert "Angola" in opportunity.description
    # Confirmed by the real fixture's own funding table (maintenance,
    # tuition ("Subsídio de Propina"), housing, and installation
    # subsidies, each with real euro amounts) - unlike Belgium, Austria,
    # and Morocco above, this classification is actually verified by the
    # source text this time, the same reasoning already applied to
    # Japan's MEXT Scholarship.
    assert opportunity.funding_type == "fully_funded"
    # Applications are submitted only in the applicant's home country
    # through local authorities and Portugal's embassies - no single
    # global deadline is published, correctly null.
    assert opportunity.deadline is None


def test_portugal_camoes_never_attempts_deadline_extraction() -> None:
    assert PortugalCamoesScholarshipSource.deadline_keywords == ()


# --- Colombia ICETEX: real fixture, fetched 2026-08-29 ----------------------


@pytest.mark.asyncio
async def test_colombia_icetex_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ColombiaIcetexBecaExtranjerosSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("colombia_icetex_beca_extranjeros.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "colombia-icetex-beca-extranjeros"
    # The current application cycle's own title, correctly picked out via
    # the `data-analytics-asset-title` anchor rather than the page's
    # hidden accessibility h1 or the historical-cycles accordion reusing
    # the same shared class.
    assert opportunity.title == "Beca Colombia Extranjeros 2026-2"
    assert opportunity.country == "Colombia"
    assert opportunity.provider_name == (
        "ICETEX - Instituto Colombiano de Crédito Educativo y Estudios "
        "Técnicos en el Exterior (Colombia)"
    )
    assert opportunity.description is not None
    assert "especialización y maestría" in opportunity.description
    # No explicit funding-coverage language on the page - correctly null
    # rather than guessed from the "Beca" (scholarship) name alone.
    assert opportunity.funding_type is None
    # A real deadline is stated on the page ("5 de junio de 2026") but in
    # Spanish month-name form, which the shared date-literal parser only
    # recognizes in English - correctly null rather than mis-parsed.
    assert opportunity.deadline is None


def test_colombia_icetex_never_attempts_deadline_extraction() -> None:
    assert ColombiaIcetexBecaExtranjerosSource.deadline_keywords == ()


# --- Chile AGCID: real fixture, fetched 2026-08-29 --------------------------


@pytest.mark.asyncio
async def test_chile_agcid_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ChileAgcidScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("chile_agcid_becas_extranjeros.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "chile-agcid-becas-extranjeros"
    assert opportunity.title == "Becas para extranjeros"
    assert opportunity.country == "Chile"
    assert opportunity.provider_name == (
        "Agencia Chilena de Cooperación Internacional para el Desarrollo "
        "(AGCID), Chile"
    )
    assert opportunity.description is not None
    assert "Alianza del Pacífico" in opportunity.description
    # The page bundles several sub-programs with conflicting funding
    # formulas (one explicitly excludes airfare, another explicitly
    # includes it) and an explicit disclaimer that terms are reference
    # only pending each call's official publication - correctly null
    # rather than asserting either sub-program's formula for the whole
    # page.
    assert opportunity.funding_type is None
    assert opportunity.deadline is None


def test_chile_agcid_never_attempts_deadline_extraction() -> None:
    assert ChileAgcidScholarshipSource.deadline_keywords == ()


# --- Peru PRONABEC: real fixture, fetched 2026-08-29 -------------------------


@pytest.mark.asyncio
async def test_peru_pronabec_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = PeruPronabecAlianzaPacificoSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("peru_pronabec_alianza_pacifico.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "peru-pronabec-alianza-pacifico"
    # The page has no <h1> at all - correctly falls back to the <title>
    # tag, split on the en dash separator.
    assert opportunity.title == "Beca Alianza del Pacífico"
    assert opportunity.country == "Peru"
    assert opportunity.provider_name == (
        "Programa Nacional de Becas y Crédito Educativo (PRONABEC), "
        "Ministry of Education, Peru"
    )
    assert opportunity.description is not None
    assert "50 vacantes" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    # The real schedule for foreign applicants is stated on the page
    # ("Del 29/5/2026 al 4/6/2026") but in numeric DD/MM/YYYY form, which
    # the shared date-literal parser cannot recognize - correctly null.
    assert opportunity.deadline is None


def test_peru_pronabec_never_attempts_deadline_extraction() -> None:
    assert PeruPronabecAlianzaPacificoSource.deadline_keywords == ()


# --- South Korea GKS: real fixture, fetched 2026-08-29 -----------------------


@pytest.mark.asyncio
async def test_south_korea_gks_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SouthKoreaGksScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("south_korea_gks_scholarship.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "south-korea-gks-scholarship"
    # The page's only <h1> is the site logo, not a title - correctly
    # picks the first of two h2.title matches (the GKS section, not the
    # sibling "Other Scholarships" tab).
    assert opportunity.title == "GKS (Global Korea Scholarship) Program"
    assert opportunity.country == "South Korea"
    assert opportunity.provider_name == (
        "National Institute for International Education (NIIED), "
        "Ministry of Education, South Korea"
    )
    assert opportunity.description is not None
    assert "Airfare" in opportunity.description
    # The page states explicit benefits (airfare, language training,
    # tuition, study allowances) - genuinely supported, same reasoning
    # as Japan MEXT and Portugal Camões.
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_south_korea_gks_never_attempts_deadline_extraction() -> None:
    assert SouthKoreaGksScholarshipSource.deadline_keywords == ()


# --- Saudi Arabia MOE: real fixture, fetched 2026-08-29 -----------------------


@pytest.mark.asyncio
async def test_saudi_arabia_moe_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SaudiArabiaMoeScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("saudi_arabia_moe_scholarships.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == (
        "saudi-arabia-moe-public-university-scholarships"
    )
    # The page has no <h1>, and its <title> tag interleaves Arabic and
    # English with the real text in the second segment (unsupported by
    # the shared first-segment-only title_tag_separator) - correctly
    # falls back to a title formatted from external_id.
    assert opportunity.title == (
        "Saudi Arabia Moe Public University Scholarships"
    )
    assert opportunity.country == "Saudi Arabia"
    assert opportunity.provider_name == "Ministry of Education (MOE), Saudi Arabia"
    assert opportunity.description is not None
    assert "External scholarships" in opportunity.description
    # The page states three distinct funding tiers (free/partial/paid) -
    # correctly null rather than asserting one tier for the whole page.
    assert opportunity.funding_type is None
    assert opportunity.deadline is None


def test_saudi_arabia_moe_never_attempts_deadline_extraction() -> None:
    assert SaudiArabiaMoeScholarshipSource.deadline_keywords == ()


# --- Qatar Scholarships: real fixture, fetched 2026-08-29 --------------------


@pytest.mark.asyncio
async def test_qatar_scholarships_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = QatarScholarshipsSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("qatar_scholarships_programs.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "qatar-scholarships-programs"
    # No <h1> at all - falls back to the <title> tag split on the
    # literal newline.
    assert opportunity.title == "Programs"
    assert opportunity.country == "Qatar"
    assert opportunity.provider_name == (
        "Qatar Fund For Development (QFFD) - Qatar Scholarships"
    )
    assert opportunity.description is not None
    assert "Lusail University" in opportunity.description
    # The page bundles partner-institution programs with conflicting
    # funding (some state full tuition waiver, the HBKU/Geneva Graduate
    # Institute program explicitly states partial tuition) - correctly
    # null rather than asserting one program's formula for the whole
    # page, the same reasoning as Chile AGCID.
    assert opportunity.funding_type is None
    assert opportunity.deadline is None


def test_qatar_scholarships_never_attempts_deadline_extraction() -> None:
    assert QatarScholarshipsSource.deadline_keywords == ()


# --- Switzerland SBFI ESKAS: real fixture, fetched 2026-08-29 ---------------


@pytest.mark.asyncio
async def test_switzerland_eskas_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SwitzerlandEskasScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("switzerland_sbfi_eskas.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "switzerland-sbfi-eskas-scholarships"
    assert opportunity.title == "Swiss Government Excellence Scholarships 2027 – 2028"
    assert opportunity.country == "Switzerland"
    assert opportunity.provider_name == (
        "Federal Commission for Scholarships for Foreign Students "
        "(FCS/ESKAS), State Secretariat for Education, Research and "
        "Innovation (SBFI), Switzerland"
    )
    assert opportunity.description is not None
    assert "CHF 2450" in opportunity.description
    # A concrete monthly amount is stated but tuition coverage is never
    # mentioned - correctly partial rather than fully funded.
    assert opportunity.funding_type == "partial_funding"
    # Deadlines are published per country of origin via Swiss diplomatic
    # representations, not as one global date on this page.
    assert opportunity.deadline is None


def test_switzerland_eskas_never_attempts_deadline_extraction() -> None:
    assert SwitzerlandEskasScholarshipSource.deadline_keywords == ()


# --- Poland NAWA: real fixture, fetched 2026-08-29 ---------------------------


@pytest.mark.asyncio
async def test_poland_nawa_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = PolandNawaMyFirstChoiceSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("poland_nawa_myfirstchoice.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "poland-nawa-my-first-choice"
    # The page's real content h1 ("header") is picked over the earlier
    # hidden accessibility h1 ("sr-only").
    assert opportunity.title == "Poland My First Choice NAWA"
    assert opportunity.country == "Poland"
    assert opportunity.provider_name == (
        "Polish National Agency for Academic Exchange (NAWA), Poland"
    )
    assert opportunity.description is not None
    assert "exemption from tuition fees" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_poland_nawa_never_attempts_deadline_extraction() -> None:
    assert PolandNawaMyFirstChoiceSource.deadline_keywords == ()


# --- Czech Republic MSMT: real fixture, fetched 2026-08-29 -------------------


@pytest.mark.asyncio
async def test_czech_republic_msmt_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = CzechRepublicMsmtScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("czech_republic_msmt_scholarships.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "czech-republic-msmt-government-scholarships"
    assert opportunity.title == "Government Scholarships – Developing Countries"
    assert opportunity.country == "Czech Republic"
    assert opportunity.provider_name == (
        "Ministry of Education, Youth and Sports (MŠMT) / Ministry of "
        "Foreign Affairs (MZV), Czech Republic"
    )
    assert opportunity.description is not None
    assert "APPLICATION SUBMISSION AND DEADLINE" in opportunity.description
    # No funding-coverage language appears in the page's own HTML - the
    # real monthly amount lives only in a linked PDF this scraper does
    # not parse.
    assert opportunity.funding_type is None
    # Unlike every other source in this initiative, this one is NOT left
    # null by design - a genuine, singular, cleanly extractable deadline
    # exists ("by 30 September 2026 at the latest").
    assert opportunity.deadline == date(2026, 9, 30)


def test_czech_republic_msmt_uses_default_deadline_keywords() -> None:
    assert CzechRepublicMsmtScholarshipSource.deadline_keywords == (
        "deadline",
        "closing date",
    )


# --- Serbia "World in Serbia": real fixture, fetched 2026-08-29 -------------


@pytest.mark.asyncio
async def test_serbia_world_in_serbia_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SerbiaWorldInSerbiaScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("serbia_world_in_serbia.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "serbia-world-in-serbia-scholarships"
    # No <h1> at all - the page's only heading is a plain <h2>.
    assert opportunity.title == "Scholarships"
    assert opportunity.country == "Serbia"
    assert opportunity.provider_name == "Ministry of Education, Republic of Serbia"
    assert opportunity.description is not None
    assert "free of charge" in opportunity.description
    # Genuinely comprehensive coverage: free tuition, accommodation and
    # food, a monthly allowance, and health insurance.
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_serbia_world_in_serbia_never_attempts_deadline_extraction() -> None:
    assert SerbiaWorldInSerbiaScholarshipSource.deadline_keywords == ()


# --- Romania MFA: real fixture, fetched 2026-08-29 ---------------------------


@pytest.mark.asyncio
async def test_romania_mfa_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = RomaniaMfaScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("romania_studyinromania_about.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "romania-mfa-government-scholarships"
    assert opportunity.title == "About the scholarships"
    assert opportunity.country == "Romania"
    assert opportunity.provider_name == (
        "Ministry of Foreign Affairs (MFA) / Ministry of Education and "
        "Research, Romania"
    )
    assert opportunity.description is not None
    assert "Foreign citizens from all non-EU countries" in opportunity.description
    # Confirmed by the fixture's own text further down the page (past
    # the description's 5000-character excerpt window, but read in full
    # before classifying): explicit financing of tuition expenses (both
    # the preparatory year and the actual studies), a monthly
    # scholarship, and accommodation expenses.
    assert opportunity.funding_type == "fully_funded"
    # A real deadline is stated ("31 March 2026") but the page's first
    # "deadline" mention is an earlier, unrelated one with no date
    # nearby - extract_confident_date_after only searches after a
    # keyword's first occurrence, so it correctly finds nothing here.
    assert opportunity.deadline is None


def test_romania_mfa_never_attempts_deadline_extraction() -> None:
    assert RomaniaMfaScholarshipSource.deadline_keywords == ()


# --- Hungary Stipendium Hungaricum: real fixture, fetched 2026-08-29 --------


@pytest.mark.asyncio
async def test_hungary_stipendium_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = HungaryStipendiumHungaricumSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("hungary_stipendium_hungaricum.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "hungary-stipendium-hungaricum-scholarship"
    # No <h1>-<h4> tag exists anywhere on the page, and the <title> tag
    # only yields the single word "About" once split - correctly falls
    # back to a title formatted from external_id instead.
    assert opportunity.title == "Hungary Stipendium Hungaricum Scholarship"
    assert opportunity.country == "Hungary"
    assert opportunity.provider_name == (
        "Tempus Public Foundation, Ministry of Foreign Affairs and "
        "Trade, Hungary"
    )
    assert opportunity.description is not None
    assert "Tuition-free education" in opportunity.description
    # Explicit tuition-free education plus real HUF/EUR monthly stipend
    # figures for both bachelor's/master's and doctoral level.
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_hungary_stipendium_never_attempts_deadline_extraction() -> None:
    assert HungaryStipendiumHungaricumSource.deadline_keywords == ()


# --- Mexico AMEXCID: real fixture, fetched 2026-08-29 ------------------------


@pytest.mark.asyncio
async def test_mexico_amexcid_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = MexicoAmexcidScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("mexico_amexcid_scholarships.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "mexico-amexcid-excellence-scholarships"
    assert opportunity.title == (
        "Becas de Excelencia del Gobierno de México para Extranjeros 2026"
    )
    assert opportunity.country == "Mexico"
    assert opportunity.provider_name == (
        "Agencia Mexicana de Cooperación Internacional para el "
        "Desarrollo (AMEXCID), Secretaría de Relaciones Exteriores "
        "(SRE), Mexico"
    )
    assert opportunity.description is not None
    assert "170 países" in opportunity.description
    # The overview page explicitly defers all concrete funding terms to
    # the official Call's "Condiciones Generales" - correctly null
    # rather than guessed from third-party summaries.
    assert opportunity.funding_type is None
    assert opportunity.deadline is None


def test_mexico_amexcid_never_attempts_deadline_extraction() -> None:
    assert MexicoAmexcidScholarshipSource.deadline_keywords == ()


# --- Cross-cutting: missing title/content fallback ------------------------


@pytest.mark.asyncio
async def test_missing_title_and_content_falls_back_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A page with none of the configured selectors present must still
    produce a valid record with a derived-from-id fallback title and a
    null description - never a crash, never invented content."""
    source = IrelandGoiIesSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value="<html><body><p>Redesigned page.</p></body></html>"),
    )

    result = await source.collect()

    assert len(result) == 1
    assert result[0].title == "Ireland Goi Ies Scholarship"
    assert result[0].description is None
    assert result[0].deadline is None


# --- World Bank JJ/WBGSP: real fixture, fetched 2026-08-30 -----------------


@pytest.mark.asyncio
async def test_world_bank_jjwbgsp_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = WorldBankJJWBGSPScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("world_bank_jjwbgsp_overview.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "world-bank-jjwbgsp"
    assert opportunity.title == "Joint Japan/World Bank Graduate Scholarship Program"
    # Not tied to a single destination country - funds study across 24
    # universities in the US, Europe, Africa, Oceania, and Japan.
    assert opportunity.country is None
    assert opportunity.provider_name == (
        "World Bank Group - Joint Japan/World Bank Graduate Scholarship Program"
    )
    assert opportunity.description is not None
    assert "developing countries" in opportunity.description
    # "Application Window #1 from January 18 to February 26, 2027" - the
    # day+month-only opening date is correctly skipped in favor of the
    # first full day+month+year literal that follows.
    assert str(opportunity.deadline) == "2027-02-26"
    assert opportunity.funding_type == "fully_funded"


# --- Rotary Peace Fellowships: real fixture, fetched 2026-08-30 ------------


@pytest.mark.asyncio
async def test_rotary_peace_fellowship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = RotaryPeaceFellowshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("rotary_peace_fellowships.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "rotary-peace-fellowship"
    assert opportunity.title == "Peace Fellowships"
    # Not tied to a single destination country - fellows study at one of
    # eight Rotary Peace Centers worldwide.
    assert opportunity.country is None
    assert opportunity.provider_name == (
        "The Rotary Foundation (Rotary International) - Rotary Peace Fellowships"
    )
    assert opportunity.description is not None
    assert "170 funded fellowships" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    # The page's own text at fetch time states only a month+year for the
    # next cycle ("available online in February 2027", no day) - never
    # guessed into a fabricated exact date.
    assert opportunity.deadline is None


def test_rotary_peace_fellowship_respects_the_sites_crawl_delay() -> None:
    assert RotaryPeaceFellowshipSource.min_request_interval_seconds == 10.0


# --- Schwarzman Scholars: real fixture, fetched 2026-09-05 -----------------


@pytest.mark.asyncio
async def test_schwarzman_scholars_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SchwarzmanScholarsSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("schwarzman_scholars_admissions.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "schwarzman-scholars"
    # The page's only <h1> is a marketing tagline, not a usable title -
    # falls through to the external_id-derived fallback.
    assert opportunity.title == "Schwarzman Scholars"
    assert opportunity.country == "China"
    assert opportunity.provider_name == "Schwarzman Scholars (Tsinghua University)"
    assert opportunity.description is not None
    assert "next generation of leaders" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    # The page states the same deadline twice: "Countdown to September 9,
    # 2026 Application Deadline" (full month name, parseable) and later
    # "Application Deadline: Sept 9, 2026" (abbreviated, unparseable).
    # Anchoring on "countdown" instead of "deadline" finds the first,
    # parseable occurrence - independently confirmed by the page's own
    # JS countdown-timer `data-date="1788980400000"` epoch attribute,
    # which is exactly 2026-09-09 19:00:00 UTC.
    assert str(opportunity.deadline) == "2026-09-09"


def test_schwarzman_scholars_respects_the_sites_crawl_delay() -> None:
    assert SchwarzmanScholarsSource.min_request_interval_seconds == 10.0

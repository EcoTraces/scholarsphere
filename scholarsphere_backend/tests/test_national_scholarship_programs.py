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
    KnightHennessyScholarsSource,
    RotaryPeaceFellowshipSource,
    SchwarzmanScholarsSource,
    SciencesPoMastercardScholarsSource,
    TurkiyeBurslariSource,
    DurhamInspiringExcellencePostgraduateScholarshipSource,
    DurhamInspiringExcellenceUndergraduateScholarshipSource,
    EthZurichExcellenceScholarshipSource,
    FreiburgDeutschlandstipendiumSource,
    GatesCambridgeScholarshipSource,
    GroningenEricBleuminkFellowshipSource,
    HarringtonGraduateFellowsSource,
    HeinrichBollScholarshipSource,
    HelmutVeithStipendSource,
    HongKongPhdFellowshipSchemeSource,
    HumboldtResearchFellowshipSource,
    ImperialInspiresScholarshipSource,
    MaastrichtHighPotentialScholarshipSource,
    McgillMastercardScholarsSource,
    ManchesterGlobalFuturesScholarshipSource,
    MaxPlanckSchoolsSource,
    NewcastleVcInternationalScholarshipSource,
    NottinghamPgScholarshipSource,
    PkuInternationalScholarshipSource,
    SheffieldPgScholarshipSource,
    SjtuMastersScholarshipSource,
    SkoltechScholarshipSource,
    SouthamptonMeritUndergraduateScholarshipSource,
    SouthamptonPresidentialBursariesSource,
    TaiwanIcdfScholarshipSource,
    TuDelftVanEffenScholarshipSource,
    TumInternationalStudentScholarshipSource,
    UniversiapolisInternationalGrantSource,
    UniversityOfTwenteScholarshipSource,
    UpfBsmMeritScholarshipSource,
    UqGraduateResearchScholarshipsSource,
    UsydRtpInternationalSource,
    UtokyoPeakScholarshipSource,
    UtrechtLegitsScholarshipSource,
    UtwenteItcScholarshipSource,
    UvaAmsterdamMeritScholarshipBachelorSource,
    UvaAmsterdamMeritScholarshipMasterSource,
    VanderbiltCorneliusScholarshipSource,
    WageningenAnneVanDenBanFundSource,
    WellsMountainInitiativeSource,
    WorldBankJJWBGSPScholarshipSource,
    YenchingAcademyScholarsSource,
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


# --- Knight-Hennessy Scholars: real fixtures, fetched 2026-09-05 -----------


@pytest.mark.asyncio
async def test_knight_hennessy_scholars_collect_normalizes_real_fixtures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The deadlines page's site-wide navigation contains an unrelated
    'Application Deadlines' menu link long before the real deadline
    sentence - anchoring on the default 'deadline' keyword would land on
    that nav link and find nothing within its 300-character search
    window, so this source anchors on 'deadline is' instead."""
    source = KnightHennessyScholarsSource()
    overview_url = f"{source.base_url}{source.overview_path}"
    deadline_url = f"{source.base_url}{source.deadline_path}"

    async def fake_get_html(url: str, **_: object) -> str:
        if url == overview_url:
            return _fixture("knight_hennessy_scholars_home.html")
        if url == deadline_url:
            return _fixture("knight_hennessy_scholars_deadlines.html")
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "knight-hennessy-scholars"
    assert opportunity.title == "Knight-Hennessy Scholars at Stanford University"
    assert opportunity.country == "United States"
    assert opportunity.provider_name == "Knight-Hennessy Scholars (Stanford University)"
    assert opportunity.description is not None
    assert "multidisciplinary leadership development program" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    # The page's real sentence is "The Knight-Hennessy Scholars
    # application deadline is October 6, 2026, 1:00pm Pacific Time." - a
    # separate, later "December 1, 2026" fallback deadline for the
    # Stanford graduate-degree-program application itself is deliberately
    # not extracted.
    assert str(opportunity.deadline) == "2026-10-06"


def test_knight_hennessy_scholars_respects_the_sites_crawl_delay() -> None:
    assert KnightHennessyScholarsSource.min_request_interval_seconds == 30.0


# --- Yenching Academy of Peking University: real fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_yenching_academy_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = YenchingAcademyScholarsSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("yenching_academy_admissions.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "yenching-academy-scholars"
    # The page has no <h1> anywhere and its <title> tag doesn't split
    # usefully - falls through to the external_id-derived fallback.
    assert opportunity.title == "Yenching Academy Scholars"
    assert opportunity.country == "China"
    assert opportunity.provider_name == "Yenching Academy of Peking University"
    assert opportunity.description is not None
    assert "Qualifications" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    # The page literally states "Application deadline: November 30,
    # 2026" twice, but the source HTML fragments that date across
    # separate <span> tags, producing "November 30 , 2026" (a stray
    # space before the comma) once BeautifulSoup joins the fragments -
    # the shared confident-date regex correctly declines to match this
    # malformed spacing rather than guess, so no deadline is extracted.
    assert opportunity.deadline is None


def test_yenching_academy_has_no_robots_txt_restrictions_to_respect() -> None:
    """robots.txt itself returns a genuine HTTP 404 (the site's own
    generic 'page not found' error page, not a bot-challenge page) - no
    robots.txt file exists at all, so this source uses the default
    (unraised) crawl interval rather than a site-stated one."""
    assert YenchingAcademyScholarsSource.min_request_interval_seconds == 2.0


# --- ETH Zurich Excellence Scholarship (ESOP): real fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_eth_zurich_esop_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = EthZurichExcellenceScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("eth_zurich_esop.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "eth-zurich-excellence-scholarship"
    assert opportunity.title == "Excellence Scholarship & Opportunity Programme"
    assert opportunity.country == "Switzerland"
    assert opportunity.provider_name == (
        "ETH Zurich - Excellence Scholarship & Opportunity Programme (ESOP)"
    )
    assert opportunity.description is not None
    assert "scholarship covers the full study and living costs" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    # The page states its one application-window date range only in
    # abbreviated-month form ("Nov, 1 - Nov, 30 2026"), never in the
    # full-month-name form the shared confident-date regex requires -
    # no deadline is extracted rather than guessed.
    assert opportunity.deadline is None


def test_eth_zurich_esop_has_no_robots_txt_restrictions_to_respect() -> None:
    """robots.txt itself returns a genuine HTTP 404 (the site's own
    generic German-language 'page not found' error page, not a
    bot-challenge page) - no robots.txt file exists at all, so this
    source uses the default (unraised) crawl interval."""
    assert EthZurichExcellenceScholarshipSource.min_request_interval_seconds == 2.0


# --- Hong Kong PhD Fellowship Scheme (HKPFS): real fixtures, fetched 2026-09-05


@pytest.mark.asyncio
async def test_hkpfs_collect_normalizes_real_fixtures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The apply.html deadline page repeats 'Application Deadline: 1
    December 2026' once per participating university (plus one stale,
    uncorrected 'Application Deadline: 1 December 2015' row for a
    university section nobody updated) - anchoring on the RGC's own
    single sentence ('...obtain an HKPFS Reference Number by 1 December
    2026...') avoids both the ambiguity of repeated per-university rows
    and the one stale row entirely."""
    source = HongKongPhdFellowshipSchemeSource()
    overview_url = f"{source.base_url}{source.overview_path}"
    deadline_url = f"{source.base_url}{source.deadline_path}"

    async def fake_get_html(url: str, **_: object) -> str:
        if url == overview_url:
            return _fixture("hkpfs_index.html")
        if url == deadline_url:
            return _fixture("hkpfs_apply.html")
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(web_scraper_base, "get_html", AsyncMock(side_effect=fake_get_html))

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "hong-kong-phd-fellowship-scheme"
    assert opportunity.title == "Hong Kong PhD Fellowship Scheme"
    assert opportunity.country == "Hong Kong"
    assert opportunity.provider_name == "Research Grants Council of Hong Kong (HKPFS)"
    assert opportunity.description is not None
    assert "irrespective of their country of origin" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    # RGC's own initial-application deadline for the 2027/28 round -
    # verified directly against the live site 2026-09-05, not guessed
    # from a prior year's cycle.
    assert str(opportunity.deadline) == "2026-12-01"


def test_hkpfs_has_no_robots_txt_restrictions_to_respect() -> None:
    """robots.txt itself returns a genuine HTTP 404 (the site's own
    'Not found - GRF/PPR/HKPFS' error page, not a bot-challenge page) -
    no robots.txt file exists at all, so this source uses the default
    (unraised) crawl interval."""
    assert HongKongPhdFellowshipSchemeSource.min_request_interval_seconds == 2.0


# --- TaiwanICDF Scholarship: real fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_taiwan_icdf_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = TaiwanIcdfScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("taiwan_icdf_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "taiwan-icdf-scholarship"
    assert opportunity.title == "TaiwanICDF International Higher Education Scholarship Program"
    assert opportunity.country == "Taiwan"
    assert opportunity.provider_name == (
        "Taiwan International Cooperation and Development Fund (TaiwanICDF)"
    )
    assert opportunity.description is not None
    assert "full scholarships to outstanding students from partner countries" in (
        opportunity.description
    )
    assert opportunity.funding_type == "fully_funded"
    # The page states "The 2027 TaiwanICDF Scholarship applications open
    # from December 1, 2026 to March 15, 2027!" - anchoring on "to march"
    # skips past the opening date (December 1, 2026) to extract the real
    # deadline (March 15, 2027), not the first date on the page.
    assert str(opportunity.deadline) == "2027-03-15"


def test_taiwan_icdf_scholarship_has_no_robots_txt_restrictions_to_respect() -> None:
    """robots.txt itself returns a genuine HTTP 404 (nginx's own generic
    error page, not a bot-challenge page) - no robots.txt file exists at
    all, so this source uses the default (unraised) crawl interval."""
    assert TaiwanIcdfScholarshipSource.min_request_interval_seconds == 2.0


# --- Humboldt Research Fellowship: real fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_humboldt_research_fellowship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The live page states the current call is full ('We have received
    the maximum number of applications for the current call') with the
    next call opening November 15, 2026 - a real *opening* date that
    this adapter deliberately does not extract into `deadline` (which
    would mislabel it), even though it is the only year-qualified date
    literal anywhere on the page."""
    source = HumboldtResearchFellowshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("humboldt_research_fellowship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "humboldt-research-fellowship"
    assert opportunity.title == "Humboldt Research Fellowship"
    assert opportunity.country == "Germany"
    assert opportunity.provider_name == "Alexander von Humboldt Foundation"
    assert opportunity.description is not None
    assert "researchers of all nationalities" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_humboldt_research_fellowship_has_no_robots_txt_restrictions_to_respect() -> (
    None
):
    """robots.txt states `Allow: /` for `User-agent: *`, with only
    TYPO3-internal and print-view paths disallowed - none of which cover
    this program page - so this source uses the default (unraised)
    crawl interval."""
    assert HumboldtResearchFellowshipSource.min_request_interval_seconds == 2.0


# --- Max Planck Schools: real fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_max_planck_schools_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The page's real `<h1>` is a page-specific call-to-action ('APPLY
    NOW - until DECEMBER 1'), not a stable program name, so the title
    falls through to the external_id-derived fallback. The application
    window ('September 1 to December 1 of the preceding year') is never
    paired with a specific year anywhere on the page, so no deadline is
    extracted."""
    source = MaxPlanckSchoolsSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("max_planck_schools.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "max-planck-schools"
    assert opportunity.title == "Max Planck Schools"
    assert opportunity.country == "Germany"
    assert opportunity.provider_name == "Max Planck Schools"
    assert opportunity.description is not None
    assert "candidates from around the world" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_max_planck_schools_has_no_robots_txt_restrictions_to_respect() -> None:
    """robots.txt has no `Disallow` rules at all for `User-agent: *`
    (only a `Sitemap:` directive) - fully unrestricted, so this source
    uses the default (unraised) crawl interval."""
    assert MaxPlanckSchoolsSource.min_request_interval_seconds == 2.0


# --- TU Delft Justus & Louise van Effen Excellence Scholarships: real
# fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_tudelft_van_effen_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = TuDelftVanEffenScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("tudelft_van_effen_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "tudelft-van-effen-excellence-scholarship"
    assert opportunity.title == "Justus & Louise van Effen Excellence Scholarships"
    assert opportunity.country == "Netherlands"
    assert opportunity.provider_name == "Delft University of Technology (TU Delft)"
    assert opportunity.description is not None
    assert "excellent international applicant" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    # "Application deadline 1 December 2026 (23:59 CET)" - the real,
    # current (2027/28 admission cycle) deadline, not a reused prior year.
    assert str(opportunity.deadline) == "2026-12-01"


def test_tudelft_van_effen_scholarship_has_no_robots_txt_restrictions_to_respect() -> (
    None
):
    """robots.txt states `Allow: /` for `User-agent: *`, with only
    TYPO3-internal and query-parameter paths disallowed - none of which
    cover this program page - so this source uses the default
    (unraised) crawl interval."""
    assert TuDelftVanEffenScholarshipSource.min_request_interval_seconds == 2.0


# --- TUM Scholarship for International Students: real fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_tum_international_student_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This is a need-based top-up grant for currently-enrolled
    international TUM students (not incoming applicants), so
    `funding_type` is `partial_funding`, never `fully_funded`. The page
    states its application window using ordinal-suffixed days ('1st
    October - 15th October 2026') and a separate year-less recurring
    'Deadline: 15 November / 15 May' - neither matches the shared
    confident-date pattern, so no deadline is extracted."""
    source = TumInternationalStudentScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("tum_international_student_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "tum-international-student-scholarship"
    assert opportunity.title == "Scholarships for International Students"
    assert opportunity.country == "Germany"
    assert opportunity.provider_name == "Technical University of Munich (TUM)"
    assert opportunity.description is not None
    assert "not eligible for BAf" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_tum_international_student_scholarship_has_no_robots_txt_restrictions() -> (
    None
):
    """robots.txt only disallows `/typo3/` and a pagination pattern
    (`/*/1000`), neither of which covers this program page, so this
    source uses the default (unraised) crawl interval."""
    assert (
        TumInternationalStudentScholarshipSource.min_request_interval_seconds == 2.0
    )


# --- Imperial Inspires scholarships: real fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_imperial_inspires_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ImperialInspiresScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("imperial_inspires_scholarships.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "imperial-inspires-scholarships"
    assert opportunity.title == "Imperial Inspires scholarships"
    assert opportunity.country == "United Kingdom"
    assert opportunity.provider_name == "Imperial College London"
    assert opportunity.description is not None
    assert "at least 300 scholarships worth" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    # Applications open "September 2026" and awards are made "by
    # mid-April 2027" - neither is a specific calendar date, so no
    # deadline is extracted.
    assert opportunity.deadline is None


def test_imperial_inspires_scholarship_has_no_robots_txt_restrictions() -> None:
    """robots.txt only disallows unrelated Business School CMS/admin
    paths, not this content page, so this source uses the default
    (unraised) crawl interval."""
    assert ImperialInspiresScholarshipSource.min_request_interval_seconds == 2.0


# --- Newcastle University Vice-Chancellor's International Scholarships:
# real fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_newcastle_vc_international_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The page's raw HTML has a second, stale <h1> wrapped inside an
    HTML comment - BeautifulSoup correctly parses only the real, current
    one ('...(2027)'). No deadline is extracted: the only dates on the
    page are ordinal-suffixed ('13th January 2027') or describe the
    separate UCAS course-application deadline, not this scholarship's
    own ('Awards will be allocated throughout the academic year')."""
    source = NewcastleVcInternationalScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("newcastle_vc_international_scholarship.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "newcastle-vc-international-scholarship"
    assert opportunity.title == (
        "Vice-Chancellor's International Scholarships (Undergraduate) (2027)"
    )
    assert opportunity.country == "United Kingdom"
    assert opportunity.provider_name == "Newcastle University"
    assert opportunity.description is not None
    assert "£7,000 per academic year" in opportunity.description
    # Sierra Leone is not on the published eligible-country list -
    # verified directly from the scraped description, not assumed.
    assert "Sierra Leone" not in opportunity.description
    assert "Ghana" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_newcastle_vc_international_scholarship_has_no_robots_txt_restrictions() -> (
    None
):
    """robots.txt only disallows a set of specific, unrelated old PDF
    filenames, not this HTML page, so this source uses the default
    (unraised) crawl interval."""
    assert (
        NewcastleVcInternationalScholarshipSource.min_request_interval_seconds == 2.0
    )


# --- University of Sheffield International Postgraduate Scholarship:
# real fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_sheffield_pg_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The page's raw HTML has two commented-out placeholder <h1> tags
    ('Library item label woz ere') - BeautifulSoup correctly parses only
    the one real heading. The literal word 'deadline' appears once on
    the page but more than 300 characters after the actual date, so
    this anchors on 'accept your offer' instead, which correctly
    extracts the real 6 July 2027 deadline."""
    source = SheffieldPgScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("sheffield_international_postgraduate_scholarship.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == (
        "sheffield-international-postgraduate-scholarship-2027"
    )
    assert opportunity.title == "International Postgraduate Scholarship 2027 (selected regions)"
    assert opportunity.country == "United Kingdom"
    assert opportunity.provider_name == "University of Sheffield"
    assert opportunity.description is not None
    assert "£7,000" in opportunity.description
    # Kenya and Nigeria are eligible; Sierra Leone is not on the
    # published list - verified directly, not assumed.
    assert "Kenya" in opportunity.description
    assert "Sierra Leone" not in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert str(opportunity.deadline) == "2027-07-06"


def test_sheffield_pg_scholarship_has_no_robots_txt_restrictions() -> None:
    """robots.txt is a standard Drupal file (only /core/, /profiles/,
    /admin/ etc. disallowed) that does not cover this content path, so
    this source uses the default (unraised) crawl interval."""
    assert SheffieldPgScholarshipSource.min_request_interval_seconds == 2.0


# --- University of Manchester Global Futures Scholarships: real
# fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_manchester_global_futures_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hub page explicitly states deadlines differ per country/
    region with no single date on this page, so no deadline is
    extracted."""
    source = ManchesterGlobalFuturesScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("manchester_global_futures_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "manchester-global-futures-scholarship"
    assert opportunity.title == "Global Futures Scholarships"
    assert opportunity.country == "United Kingdom"
    assert opportunity.provider_name == "University of Manchester"
    assert opportunity.description is not None
    assert "more than 350 partial merit-based scholarships" in opportunity.description
    # Postgraduate applicability is genuinely stated (not assumed): one
    # region is explicitly "postgraduate taught master's only".
    assert "postgraduate taught master's only" in opportunity.description
    # Ghana, Kenya, Nigeria, South Africa, Zimbabwe are eligible;
    # Sierra Leone is not on the published list - verified directly.
    assert "Zimbabwe" in opportunity.description
    assert "Sierra Leone" not in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_manchester_global_futures_scholarship_has_no_robots_txt_restrictions() -> (
    None
):
    """robots.txt only disallows unrelated campaign/search/media-library
    paths, not this content page, so this source uses the default
    (unraised) crawl interval."""
    assert (
        ManchesterGlobalFuturesScholarshipSource.min_request_interval_seconds == 2.0
    )


# --- University of Nottingham International Postgraduate Scholarship:
# real fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_nottingham_pg_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unlike this platform's other England sources, this page states no
    country/nationality restriction and no entry-year lock - a
    genuinely evergreen description, not tied to one admissions cycle.
    No deadline is extracted since none is stated."""
    source = NottinghamPgScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("nottingham_pg_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == (
        "nottingham-international-postgraduate-scholarship"
    )
    assert opportunity.title == "International Postgraduate Scholarships"
    assert opportunity.country == "United Kingdom"
    assert opportunity.provider_name == "University of Nottingham"
    assert opportunity.description is not None
    assert "international fee-paying student" in opportunity.description
    assert "No scholarship application needed" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_nottingham_pg_scholarship_has_no_robots_txt_restrictions() -> None:
    """robots.txt only disallows internal search-result paths
    (/search.aspx and equivalents), not this content page, so this
    source uses the default (unraised) crawl interval."""
    assert NottinghamPgScholarshipSource.min_request_interval_seconds == 2.0


# --- University of Southampton Presidential bursaries: real fixture,
# fetched 2026-09-05


@pytest.mark.asyncio
async def test_southampton_presidential_bursaries_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The page's `<article>` wrapper also contains a large sidebar
    listing dozens of unrelated scholarships before the real content -
    `div.body--content` is the narrower, correct selector, verified
    directly. The only date on the page (1 August 2026) is the
    eligibility window's opening, not a deadline, so nothing is
    extracted."""
    source = SouthamptonPresidentialBursariesSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("southampton_presidential_bursaries.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "southampton-presidential-bursaries"
    assert opportunity.title == "Presidential bursaries"
    assert opportunity.country == "United Kingdom"
    assert opportunity.provider_name == "University of Southampton"
    assert opportunity.description is not None
    assert "open to all international candidates" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_southampton_presidential_bursaries_has_no_robots_txt_restrictions() -> None:
    """robots.txt's one relevant disallow entry targets a different
    page (/study/postgraduate-research/projects/), not this content
    page, so this source uses the default (unraised) crawl interval."""
    assert (
        SouthamptonPresidentialBursariesSource.min_request_interval_seconds == 2.0
    )


# --- University of Southampton Merit scholarships for international
# undergraduates: real fixture, fetched 2026-09-05


@pytest.mark.asyncio
async def test_southampton_merit_undergraduate_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's first England undergraduate source since
    Newcastle's VCIS (#61) and Imperial Inspires (#60), and structurally
    distinct from both: eligibility is grade-outcome-based (exceeding
    the academic offer), not a country list, so no deadline exists to
    extract."""
    source = SouthamptonMeritUndergraduateScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("southampton_merit_undergraduate_scholarship.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "southampton-merit-undergraduate-scholarship"
    assert opportunity.title == "Merit scholarships for international undergraduates"
    assert opportunity.country == "United Kingdom"
    assert opportunity.provider_name == "University of Southampton"
    assert opportunity.description is not None
    assert "up to £4,500 off the first year of tuition fees" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_southampton_merit_undergraduate_scholarship_has_no_robots_txt_restrictions() -> (
    None
):
    assert (
        SouthamptonMeritUndergraduateScholarshipSource.min_request_interval_seconds
        == 2.0
    )


# --- Durham University Inspiring Excellence Scholarships (Undergraduate
# and Postgraduate): real fixtures, fetched 2026-09-06


@pytest.mark.asyncio
async def test_durham_inspiring_excellence_undergraduate_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The page has no `<h1>`, so the title falls back to the
    `external_id`-derived value. `div.col-md-9` is the correct content
    selector - the later `div.t4-text-long` block on the same page holds
    only Terms and Conditions text, verified directly via a structural
    walk of the fetched page. The generic "deadline" keyword's first
    match on the page (an unrelated "UCAS reply deadline" phrase) has no
    date nearby, so `deadline_keywords` uses the specific phrase "1st
    round application deadline" to reliably extract the first round's
    date for 2027 entry."""
    source = DurhamInspiringExcellenceUndergraduateScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture(
                "durham_inspiring_excellence_undergraduate_scholarship.html"
            )
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert (
        opportunity.external_id
        == "durham-inspiring-excellence-undergraduate-scholarship"
    )
    assert opportunity.title == "Durham Inspiring Excellence Undergraduate Scholarship"
    assert opportunity.country == "United Kingdom"
    assert opportunity.provider_name == "Durham University"
    assert opportunity.description is not None
    assert "self-funded international applicants" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline == date(2026, 12, 7)


def test_durham_inspiring_excellence_undergraduate_scholarship_has_no_robots_txt_restrictions() -> (
    None
):
    """robots.txt's `User-Agent: *` block has a blanket empty
    `Disallow:` and none of its named entries match this content path."""
    assert (
        DurhamInspiringExcellenceUndergraduateScholarshipSource.min_request_interval_seconds
        == 2.0
    )


@pytest.mark.asyncio
async def test_durham_inspiring_excellence_postgraduate_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Master's-level counterpart of the undergraduate source above,
    on its own flagship page - verified independently that the same
    `div.col-md-9` content selector and "1st round application deadline"
    keyword resolve correctly on this page's own fetched HTML."""
    source = DurhamInspiringExcellencePostgraduateScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture(
                "durham_inspiring_excellence_postgraduate_scholarship.html"
            )
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert (
        opportunity.external_id
        == "durham-inspiring-excellence-postgraduate-scholarship"
    )
    assert opportunity.title == "Durham Inspiring Excellence Postgraduate Scholarship"
    assert opportunity.country == "United Kingdom"
    assert opportunity.provider_name == "Durham University"
    assert opportunity.description is not None
    assert "self-funded international applicants" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline == date(2026, 12, 7)


def test_durham_inspiring_excellence_postgraduate_scholarship_has_no_robots_txt_restrictions() -> (
    None
):
    assert (
        DurhamInspiringExcellencePostgraduateScholarshipSource.min_request_interval_seconds
        == 2.0
    )


# --- University of Freiburg Deutschlandstipendium: real fixture, fetched
# 2026-09-06


@pytest.mark.asyncio
async def test_freiburg_deutschlandstipendium_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's second Germany-university source (after TUM,
    #59), and the first single page to
    cover both the "postgraduate/masters" and "undergraduate" parts of a
    request at once: the page's full eligibility text (in a separate FAQ
    accordion section not part of the scraped description below) names
    both undergraduate and Master's degree programme students as
    eligible. `div.wp-block-columns` (the first one on the page) is the
    correct content selector for the description itself - chosen over
    the much larger `main` element, which is mostly a tabbed FAQ
    accordion repeating the same detail. No deadline is extracted despite
    two dates being present: the page's stated "31 March 2028" closing
    date for the "2027/2028 scholarship round" contradicts its own
    description elsewhere of a roughly one-month March application
    window each year, reading as a likely site typo rather than a
    literal fact - so nothing is extracted rather than reporting a
    suspect date."""
    source = FreiburgDeutschlandstipendiumSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("freiburg_deutschlandstipendium.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "freiburg-deutschlandstipendium"
    assert opportunity.title == "Deutschlandstipendium"
    assert opportunity.country == "Germany"
    assert opportunity.provider_name == "University of Freiburg"
    assert opportunity.description is not None
    assert "€300 each per month for one year" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_freiburg_deutschlandstipendium_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`uni-freiburg.de/robots.txt`) only disallows
    `/wp-admin/`, not this content path."""
    assert FreiburgDeutschlandstipendiumSource.min_request_interval_seconds == 2.0


# --- University of Amsterdam Amsterdam Merit Scholarship (Master's and
# Bachelor's): real fixtures, fetched 2026-09-06


@pytest.mark.asyncio
async def test_uva_amsterdam_merit_scholarship_master_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's second Netherlands *university* source (TU
    Delft's Van Effen Scholarship, #58, was the first). No deadline or
    specific amount is extracted: this general overview
    page states outright that "Deadlines for the AMS differ per Faculty
    or Graduate School" and links to nine separate faculty pages, each
    administering its own deadline - verified directly, not assumed."""
    source = UvaAmsterdamMeritScholarshipMasterSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("uva_amsterdam_merit_scholarship_master.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "uva-amsterdam-merit-scholarship-master"
    assert opportunity.title == "Amsterdam Merit Scholarships"
    assert opportunity.country == "Netherlands"
    assert opportunity.provider_name == "University of Amsterdam"
    assert opportunity.description is not None
    assert "non-EU/EEA passport" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_uva_amsterdam_merit_scholarship_master_has_no_robots_txt_restrictions() -> (
    None
):
    """robots.txt (`uva.nl/robots.txt`) is a genuine empty file - HTTP
    200, zero bytes - so no restrictions are declared at all."""
    assert (
        UvaAmsterdamMeritScholarshipMasterSource.min_request_interval_seconds == 2.0
    )


@pytest.mark.asyncio
async def test_uva_amsterdam_merit_scholarship_bachelor_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The undergraduate counterpart of the Master's source above, on
    its own separate overview page with its own continuation-of-funding
    condition (~80% credits/year). Same "deadlines differ per Faculty"
    reasoning for extracting no deadline."""
    source = UvaAmsterdamMeritScholarshipBachelorSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("uva_amsterdam_merit_scholarship_bachelor.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "uva-amsterdam-merit-scholarship-bachelor"
    assert opportunity.title == "Amsterdam Merit Scholarship"
    assert opportunity.country == "Netherlands"
    assert opportunity.provider_name == "University of Amsterdam"
    assert opportunity.description is not None
    assert "non-EU/EEA passport" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_uva_amsterdam_merit_scholarship_bachelor_has_no_robots_txt_restrictions() -> (
    None
):
    assert (
        UvaAmsterdamMeritScholarshipBachelorSource.min_request_interval_seconds
        == 2.0
    )


# --- University of Groningen Eric Bleumink Fellowship: real fixture,
# fetched 2026-09-06


@pytest.mark.asyncio
async def test_groningen_eric_bleumink_fellowship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Restricted to an explicit list of ~80 named developing countries
    that includes Sierra Leone - confirmed directly in the scraped
    description text, not inferred from a vague "developing countries"
    label. Nomination-based (no separate scholarship application - the
    University of Groningen's own Admission Office nominates candidates
    from regular Master's applications submitted before 1 December), a
    materially different shape from Vanier Canada's third-party-
    institution nomination model. `funding_type = "fully_funded"` is a
    deliberate, evidence-based classification: the page states the grant
    "covers tuition fee, costs of international travel, subsistence,
    books, and health insurance." No deadline is extracted since neither
    stated date ("before February", "before 1st of December") carries a
    year on this page."""
    source = GroningenEricBleuminkFellowshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("groningen_eric_bleumink_fellowship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "groningen-eric-bleumink-fellowship"
    assert opportunity.title == "Eric Bleumink Fellowship"
    assert opportunity.country == "Netherlands"
    assert opportunity.provider_name == "University of Groningen"
    assert opportunity.description is not None
    assert "Sierra Leone" in opportunity.description
    assert (
        "covers tuition fee, costs of international travel, subsistence"
        in opportunity.description
    )
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_groningen_eric_bleumink_fellowship_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`rug.nl/robots.txt`) does not disallow this content
    path."""
    assert (
        GroningenEricBleuminkFellowshipSource.min_request_interval_seconds == 2.0
    )


# --- Utrecht University Law, Economics and Governance International
# Talent Scholarship (LEGITS): real fixture, fetched 2026-09-06


@pytest.mark.asyncio
async def test_utrecht_legits_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Utrecht's central Utrecht Excellence Scholarship was confirmed
    live and directly on Utrecht's own page to be discontinued for
    2026-2027 entry onward ("due to significant budget cuts"), and its
    Bright Minds Fellowships confirmed restricted to EU/EEA students
    only - neither used instead. LEGITS covers "both EU/EEA and
    non-EU/EEA students," for a currently live 1 September 2027 intake.
    No deadline is extracted: the stated deadline ("before February 1st
    23:59 CET") never carries a year on this page, even though a
    *different*, unrelated date on the same page (the application
    portal's 1 November 2026 opening) does - verified directly that
    `extract_confident_date_after` does not accidentally resolve to
    that unrelated date."""
    source = UtrechtLegitsScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("utrecht_legits_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "utrecht-legits-scholarship"
    assert (
        opportunity.title
        == "Law, Economics and Governance International Talent Scholarship"
    )
    assert opportunity.country == "Netherlands"
    assert opportunity.provider_name == "Utrecht University"
    assert opportunity.description is not None
    assert "Both EU/EEA and non-EU/EEA students are eligible" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_utrecht_legits_scholarship_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`uu.nl/robots.txt`) is a standard Drupal file that
    does not disallow this content path."""
    assert UtrechtLegitsScholarshipSource.min_request_interval_seconds == 2.0


# --- Maastricht University NL-High Potential Scholarship: real fixture,
# fetched 2026-09-06


@pytest.mark.asyncio
async def test_maastricht_high_potential_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Already updated for the *next* application cycle as of this
    research date: the page states applicants must apply for the
    2027-2028 academic year before 10 December 2026 - a real,
    not-yet-passed deadline, unlike several other Netherlands candidates
    researched this pass (VU Amsterdam, TU Eindhoven, Erasmus
    Rotterdam - see Task.md) which were all still locked to their
    already-closed 2026-2027 cycles. `funding_type = "fully_funded"` is
    a deliberate, evidence-based classification: the page states "18
    full scholarships, including tuition fee waiver and monthly
    stipend." `deadline_keywords` uses the specific phrase "before 10
    December" (appearing exactly once on the page) since the generic
    "deadline" keyword's first occurrence has no date literal nearby."""
    source = MaastrichtHighPotentialScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("maastricht_high_potential_scholarship.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "maastricht-high-potential-scholarship"
    assert opportunity.title == "Maastricht University NL-High Potential scholarship"
    assert opportunity.country == "Netherlands"
    assert opportunity.provider_name == "Maastricht University"
    assert opportunity.description is not None
    assert "tuition fee waiver and monthly stipend" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline == date(2026, 12, 10)


def test_maastricht_high_potential_scholarship_has_no_robots_txt_restrictions() -> (
    None
):
    """robots.txt (`maastrichtuniversity.nl/robots.txt`) does not
    disallow this content path."""
    assert (
        MaastrichtHighPotentialScholarshipSource.min_request_interval_seconds
        == 2.0
    )


# --- University of Twente Scholarship (UTS): real fixture, fetched
# 2026-09-06


@pytest.mark.asyncio
async def test_university_of_twente_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cash award, not a tuition waiver - "No costs (e.g. tuition
    fees) will be paid on your behalf" - so `funding_type =
    "partial_funding"`. The page's "Countries eligible for this
    scholarship" enumeration includes nearly every non-EU/EEA country;
    confirmed directly that Sierra Leone appears in it (alphabetically
    between Seychelles and Singapore), not assumed from "non-EU/EEA."
    Already updated for the 2027/2028 intake with a real, not-yet-passed
    deadline (1 April 2027), unlike several other Netherlands candidates
    researched this pass still locked to their already-closed 2026-2027
    cycles (see Task.md)."""
    source = UniversityOfTwenteScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("university_of_twente_scholarship.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "university-of-twente-scholarship"
    assert opportunity.title == "University of Twente Scholarship (UTS)"
    assert opportunity.country == "Netherlands"
    assert opportunity.provider_name == "University of Twente"
    assert opportunity.description is not None
    assert "non-EU/EER countries" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline == date(2027, 4, 1)


def test_university_of_twente_scholarship_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`utwente.nl/robots.txt`) does not disallow this
    content path."""
    assert (
        UniversityOfTwenteScholarshipSource.min_request_interval_seconds == 2.0
    )


# --- Wageningen University & Research Anne van den Ban Fund: real
# fixture, fetched 2026-09-06


@pytest.mark.asyncio
async def test_wageningen_anne_van_den_ban_fund_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nomination-based like this platform's existing Eric Bleumink
    Fellowship source (Groningen): "The fund does not consider
    individual applications... interested parties must wait until an
    Anne van den Ban scholarship is offered" from among already-admitted
    Master's applicants. `funding_type = "partial_funding"` since the
    page states "full or partial funding" varying by student, not a
    guaranteed full award. No deadline is extracted: the only timing
    given (spring/May notification, "if you have not received an offer
    by 1 June") is a recurring annual window with no year on this
    page."""
    source = WageningenAnneVanDenBanFundSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(
            return_value=_fixture("wageningen_anne_van_den_ban_fund.html")
        ),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "wageningen-anne-van-den-ban-fund"
    assert opportunity.title == "Selection Anne van den Ban Fund"
    assert opportunity.country == "Netherlands"
    assert opportunity.provider_name == "Wageningen University & Research"
    assert opportunity.description is not None
    assert "low-income countries" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_wageningen_anne_van_den_ban_fund_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`wur.nl/robots.txt`) does not disallow this content
    path."""
    assert (
        WageningenAnneVanDenBanFundSource.min_request_interval_seconds == 2.0
    )


# --- University of Twente ITC Excellence Scholarship Programme: real
# fixture, fetched 2026-09-06


@pytest.mark.asyncio
async def test_utwente_itc_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A distinct scholarship from the university-wide UTS (already
    added): administered specifically by the ITC faculty for two of its
    own Master's programmes, with its own explicit eligible-countries
    list - confirmed directly that Sierra Leone appears in it. A
    genuinely partial scholarship with an exact cost breakdown on the
    page (EUR 25,000 waiver of a EUR 74,370 total). No deadline is
    extracted: the page states "APPLICATIONS 2026 CLOSED. A possible
    next round is expected to open in December" - a real, current
    status, but "December" alone carries no day or year for
    `extract_confident_date_after` to match."""
    source = UtwenteItcScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("utwente_itc_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "utwente-itc-scholarship"
    assert opportunity.title == "ITC Excellence Scholarship Programme"
    assert opportunity.country == "Netherlands"
    assert opportunity.provider_name == "University of Twente"
    assert opportunity.description is not None
    assert "Sierra Leone" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_utwente_itc_scholarship_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`utwente.nl/robots.txt`) does not disallow this
    content path."""
    assert UtwenteItcScholarshipSource.min_request_interval_seconds == 2.0


# --- UPF Barcelona School of Management Merit Based Scholarship: real
# fixture, fetched 2026-09-06


@pytest.mark.asyncio
async def test_upf_bsm_merit_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's first Spain *university* source (the existing
    Spain source, #23, is the government-classified Becas MAEC-AECID).
    No nationality/country restriction anywhere in the eligibility
    criteria - Sierra Leone applicants are eligible. The page lists four
    rolling annual application rounds; as of this research date the
    first two (18 June 2026, 3 September 2026) have already passed, so
    `deadline_keywords` uses the specific phrase "3rd call" to reliably
    resolve to the next genuinely upcoming round, 26 November 2026,
    rather than the generic "deadline" keyword (which resolves to
    nothing on this page) or the first, already-passed round's date."""
    source = UpfBsmMeritScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("upf_bsm_merit_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "upf-bsm-merit-scholarship"
    assert opportunity.title == "Merit Based Scholarship"
    assert opportunity.country == "Spain"
    assert (
        opportunity.provider_name
        == "UPF Barcelona School of Management (Universitat Pompeu Fabra)"
    )
    assert opportunity.description is not None
    assert "covers 25% of the total tuition fee" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline == date(2026, 11, 26)


def test_upf_bsm_merit_scholarship_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`bsm.upf.edu/robots.txt`) does not disallow this
    content path."""
    assert UpfBsmMeritScholarshipSource.min_request_interval_seconds == 2.0


# --- Sciences Po Mastercard Foundation Scholars Program: real fixture,
# fetched 2026-09-06


@pytest.mark.asyncio
async def test_sciencespo_mastercard_scholars_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's first France *university* source. Genuinely fully
    funded (not merely a large stipend): "The Program covers the full
    financial needs of selected Scholars" plus, on the parent hub page,
    "cover[s] the full cost of tuition and living expenses in France" and
    reserved Paris housing. Eligibility's sole nationality criterion is
    "citizenship of an African country" - Sierra Leone is not excluded.
    No exact deadline exists yet on this page ("detailed information and
    the application timeline ... will be published on this page from
    September 2026"; the window "October to mid-December 2026" carries
    no day number) so `deadline` correctly resolves to `None` rather than
    guessing a date - and the page's one full date literal, 17 October
    2026, is an information-session date, not the deadline, and is never
    reached by the default `deadline_keywords`."""
    source = SciencesPoMastercardScholarsSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("sciencespo_mastercard_scholars.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "sciencespo-mastercard-scholars"
    assert opportunity.title == "Become a Mastercard Foundation Scholar at graduate level"
    assert opportunity.country == "France"
    assert opportunity.provider_name == "Sciences Po"
    assert opportunity.description is not None
    assert "full financial needs of selected Scholars" in opportunity.description
    assert "citizenship of an African country" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_sciencespo_mastercard_scholars_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`sciencespo.fr/robots.txt`) does not disallow the
    `/students/` content path."""
    assert SciencesPoMastercardScholarsSource.min_request_interval_seconds == 2.0


# --- Peking University Scholarship for International Students: real
# fixture, fetched 2026-09-06


@pytest.mark.asyncio
async def test_pku_international_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's first China *university* source (Schwarzman
    Scholars and Yenching Academy, sources #50/#52, are elite named
    programs hosted at Tsinghua/PKU, not this general institution-wide
    scholarship). No nationality/country restriction stated anywhere -
    Sierra Leone applicants are eligible. The page has no `<h1>` at all,
    so `title_tag_separator = " | "` (a separator absent from the real
    `<title>` text) is used to extract the clean title unchanged. No
    deadline extracted: "Application Time: Generally in January and
    March each year" carries no year."""
    source = PkuInternationalScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("pku_international_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "pku-international-scholarship"
    assert (
        opportunity.title == "Peking University Scholarship for International Students"
    )
    assert opportunity.country == "China"
    assert opportunity.provider_name == "Peking University"
    assert opportunity.description is not None
    assert "It covers tuition, a living stipend and medical insurance" in (
        opportunity.description
    )
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_pku_international_scholarship_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`isd.pku.edu.cn/robots.txt`) returns this site's own
    404 page, not a robots.txt - no Disallow rules exist for this
    host."""
    assert PkuInternationalScholarshipSource.min_request_interval_seconds == 2.0


# --- Shanghai Jiao Tong University Master's SJTU Scholarship: real
# fixture, fetched 2026-09-06


@pytest.mark.asyncio
async def test_sjtu_masters_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's second China *university* source. The overview
    page is a general prospective-students hub with exactly two
    `div.page-item` tab panels (Undergraduate, Graduate) - the
    adjacent-sibling selector `div.page-item + div.page-item`
    deliberately targets the second (Graduate Programs) panel, holding
    both the PhD and Master's SJTU Scholarship text, without pulling in
    the Undergraduate panel's unrelated tiered-scholarship text. No
    `<h1>` and no useful `<title>` for this specific scholarship, so
    the external_id-derived fallback is used - `external_id` spells the
    university's name in full so the fallback capitalizes correctly
    ("Shanghai Jiao Tong University Masters Scholarship", not "Sjtu").
    No nationality/country restriction stated anywhere (the whole hub
    is framed under "Prospective International Students" with a
    "Foreign Students Apply" portal) - Sierra Leone applicants are
    eligible. No deadline extracted: this panel states no date at
    all."""
    source = SjtuMastersScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("sjtu_masters_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert (
        opportunity.external_id == "shanghai-jiao-tong-university-masters-scholarship"
    )
    assert opportunity.title == "Shanghai Jiao Tong University Masters Scholarship"
    assert opportunity.country == "China"
    assert opportunity.provider_name == "Shanghai Jiao Tong University"
    assert opportunity.description is not None
    assert "Master’s SJTU Scholarship includes Monthly stipend" in (
        opportunity.description
    )
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_sjtu_masters_scholarship_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`global.sjtu.edu.cn/robots.txt`) returns a generic 404
    page, not a robots.txt - no Disallow rules exist for this host."""
    assert SjtuMastersScholarshipSource.min_request_interval_seconds == 2.0


# --- McGill University Mastercard Foundation Scholars Program: real
# fixture, fetched 2026-09-06


@pytest.mark.asyncio
async def test_mcgill_mastercard_scholars_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's first Canada source of any kind - Canada was
    previously found NOT_SUITABLE at the national/government level
    (EduCanada's Study in Canada Scholarships is institution-initiated,
    not individually-applicable), a finding that remains correct and
    unaffected; this is a university-administered source instead, the
    same partnership pattern already used for Sciences Po's own
    Mastercard Foundation Scholars Program. The separate Eligibility
    page (not itself scraped for this record) lists an explicit
    ~54-country table naming Sierra Leone directly - confirmed live
    during research. No deadline extracted: this page states none."""
    source = McgillMastercardScholarsSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("mcgill_mastercard_scholars.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "mcgill-mastercard-scholars"
    assert (
        opportunity.title
        == "About the Program | Mastercard Foundation Scholars Program at McGill University"
    )
    assert opportunity.country == "Canada"
    assert opportunity.provider_name == "McGill University"
    assert opportunity.description is not None
    assert "Full international student tuition" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_mcgill_mastercard_scholars_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`mcgill.ca/robots.txt`) sets `Crawl-delay: 5` (matched
    exactly by `min_request_interval_seconds`) and does not disallow
    this content path."""
    assert McgillMastercardScholarsSource.min_request_interval_seconds == 5.0


# --- Gates Cambridge Scholarship: real fixture, fetched 2026-09-06


@pytest.mark.asyncio
async def test_gates_cambridge_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's first England source classified as genuinely
    fully funded. Oxford's Clarendon Fund was researched first as an
    equally strong candidate, but ox.ac.uk (every path tested,
    including robots.txt) returns an active Cloudflare "Just a
    moment..." managed challenge - not bypassed. Eligibility (from a
    separate page, not itself scraped) is worldwide - "a citizen of any
    country outside the United Kingdom" - Sierra Leone included. No
    deadline extracted: this page states none, and the separate
    Timeline page's dates vary by applicant category/course with no
    single canonical value."""
    source = GatesCambridgeScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("gates_cambridge_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "gates-cambridge-scholarship"
    assert opportunity.title == "Gates Cambridge Scholarship"
    assert opportunity.country == "United Kingdom"
    assert (
        opportunity.provider_name
        == "Gates Cambridge Trust (University of Cambridge)"
    )
    assert opportunity.description is not None
    assert "covers the full cost of studying at Cambridge" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_gates_cambridge_scholarship_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`gatescambridge.org/robots.txt`) only disallows
    `/wp-admin/`, unrelated to this content path."""
    assert GatesCambridgeScholarshipSource.min_request_interval_seconds == 2.0


# --- Heinrich Böll Foundation Scholarship: real fixture, fetched 2026-09-06


@pytest.mark.asyncio
async def test_heinrich_boll_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Foundation source (like Humboldt Research Fellowship), for an
    open-scope "find another scholarship in Germany" request. Genuinely
    fully funded for prospective (not-yet-enrolled) non-EU Master's/PhD
    applicants from DAC countries (Sierra Leone included). Deadline
    extraction deliberately anchors on "until" rather than the base
    class's default "deadline" keyword, since "deadline" as a substring
    of "deadlines" would otherwise land on the window-*opening* date (15
    January 2027) instead of the closing date (1 March 2027)."""
    source = HeinrichBollScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("heinrich_boll_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "heinrich-boll-scholarship"
    assert (
        opportunity.title
        == "Tailwind for Talents: Scholarships for Graduates and PhD students"
    )
    assert opportunity.country == "Germany"
    assert (
        opportunity.provider_name
        == "Heinrich Böll Foundation (Heinrich-Böll-Stiftung)"
    )
    assert opportunity.description is not None
    assert "DAC countries" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline == date(2027, 3, 1)


def test_heinrich_boll_scholarship_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`boell.de/robots.txt`, a Drupal default) sets no
    relevant `Disallow` for `/en/scholarships`."""
    assert HeinrichBollScholarshipSource.min_request_interval_seconds == 2.0


# --- Helmut Veith Stipend (TU Wien / VCLA): real fixture, fetched 2026-09-07


@pytest.mark.asyncio
async def test_helmut_veith_stipend_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's first Austria *university* source (OeAD Ernst
    Mach Grant, #28, is government-classified). Genuinely
    partial_funding, not fully_funded: EUR 7,000/year plus a tuition
    waiver falls well short of Vienna's own documented ~EUR 950-1,300/
    month student cost of living. Deliberately uses the dedicated
    vcla.at announcement page rather than the TU Wien Informatics hub
    page, which states a stale EUR 6,000 figure for the same award."""
    source = HelmutVeithStipendSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("helmut_veith_stipend.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "helmut-veith-stipend"
    assert opportunity.title == "Helmut Veith Stipend"
    assert opportunity.country == "Austria"
    assert (
        opportunity.provider_name
        == "TU Wien (Vienna Center for Logic and Algorithms / VCLA)"
    )
    assert opportunity.description is not None
    assert "EUR 7000 annually" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline == date(2026, 11, 30)


def test_helmut_veith_stipend_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`vcla.at/robots.txt`) only disallows `/wp-admin/`,
    unrelated to this content path."""
    assert HelmutVeithStipendSource.min_request_interval_seconds == 2.0


# --- USYD RTP Scholarships (International): real fixture, fetched 2026-09-07


@pytest.mark.asyncio
async def test_usyd_rtp_international_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's first Australia *university* source of any kind
    (Australia Awards, #24, is government/DFAT-classified). Genuinely
    fully_funded for higher-degree-by-research applicants (Master's-by-
    Research and PhD, not PhD-only): AUD 44,293/year stipend (2027
    rate) + 100% tuition fee offset + relocation/thesis allowances +
    OSHC. `deadline_keywords` deliberately overridden to ("submission
    deadline",) since the base class's default "deadline" keyword
    matches an earlier, dateless prose sentence first."""
    source = UsydRtpInternationalSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("usyd_rtp_international.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "usyd-rtp-international"
    assert opportunity.title == "RTP scholarships – International"
    assert opportunity.country == "Australia"
    assert opportunity.provider_name == "University of Sydney"
    assert opportunity.description is not None
    assert "higher degree by research" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline == date(2026, 9, 11)


def test_usyd_rtp_international_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`sydney.edu.au/robots.txt`) sets `Allow: /` for
    `User-agent: *`, with only unrelated legacy/search paths
    disallowed."""
    assert UsydRtpInternationalSource.min_request_interval_seconds == 2.0


# --- UQ Graduate Research School Scholarships: real fixture, fetched 2026-09-07


@pytest.mark.asyncio
async def test_uq_graduate_research_scholarships_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's second Australia university source. MPhil
    (Master of Philosophy) is a genuine Master's-by-research degree,
    explicitly named alongside PhD on this page - not PhD-only. UQGRSS
    itself is open to international students, funds tuition + a AUD
    39.2K/year stipend + OSHC - genuinely fully_funded. No deadline
    extracted: the page states only that scholarships are "offered in
    rounds during the year" with no date literal present."""
    source = UqGraduateResearchScholarshipsSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("uq_grsss_phd_mphil.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "uq-graduate-research-scholarships"
    assert opportunity.title == "Scholarships for PhD and MPhil students"
    assert opportunity.country == "Australia"
    assert opportunity.provider_name == "University of Queensland"
    assert opportunity.description is not None
    assert "Master of Philosophy (MPhil)" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_uq_graduate_research_scholarships_has_no_robots_txt_restrictions() -> (
    None
):
    """robots.txt (`scholarships.uq.edu.au/robots.txt`, a Drupal
    default) does not disallow this content path."""
    assert (
        UqGraduateResearchScholarshipsSource.min_request_interval_seconds == 2.0
    )


# --- Harrington Graduate Fellows (UT Austin): real fixture, fetched 2026-09-07


@pytest.mark.asyncio
async def test_harrington_graduate_fellows_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's first USA university source. Genuinely
    fully_funded (USD 40,000/year stipend + full tuition/fees + health
    insurance stipend + USD 2,000/year expenses), explicitly
    international, and genuinely includes a Master's track
    ("Harrington Master's Fellows," for professional/terminal Master's
    degrees), not PhD-only. A nomination-only award, documented
    honestly rather than presented as directly appliable. No deadline
    extracted: no date literal appears anywhere in the page's text."""
    source = HarringtonGraduateFellowsSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("harrington_graduate_fellows.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "harrington-graduate-fellows"
    assert opportunity.title == "Graduate Fellows Program"
    assert opportunity.country == "United States"
    assert (
        opportunity.provider_name
        == "University of Texas at Austin (Harrington Fellowship)"
    )
    assert opportunity.description is not None
    assert "Harrington Master's Fellows" in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_harrington_graduate_fellows_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`harrington.utexas.edu/robots.txt`, a Drupal
    default) does not disallow this content path."""
    assert HarringtonGraduateFellowsSource.min_request_interval_seconds == 2.0


# --- Vanderbilt Cornelius Vanderbilt Scholarship: real fixture, fetched 2026-09-07


@pytest.mark.asyncio
async def test_vanderbilt_cornelius_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's second USA university source, and its first at
    the undergraduate level. Correctly partial_funding, not fully
    funded: guaranteed full tuition plus a summer stipend, not full
    cost of attendance. Genuinely open to international applicants,
    confirmed on Vanderbilt's own international-admissions page (not
    itself scraped). The page also names a separate, differently-
    focused Ingram Scholars programme sharing the same deadline, not
    represented by this record."""
    source = VanderbiltCorneliusScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("vanderbilt_cornelius_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "cornelius-vanderbilt-scholarship"
    assert opportunity.title == "Cornelius Vanderbilt Scholarship"
    assert opportunity.country == "United States"
    assert opportunity.provider_name == "Vanderbilt University"
    assert opportunity.description is not None
    assert "guaranteed full-tuition awards" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline == date(2026, 12, 1)


def test_vanderbilt_cornelius_scholarship_has_no_robots_txt_restrictions() -> (
    None
):
    """`vanderbilt.edu` has no `robots.txt` file at all (a genuine
    HTTP 404 via CloudFront) - no restrictions declared."""
    assert (
        VanderbiltCorneliusScholarshipSource.min_request_interval_seconds == 2.0
    )


# --- Skoltech Scholarship: real fixture, fetched 2026-09-07


@pytest.mark.asyncio
async def test_skoltech_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's first Russia source of any kind - the site is
    genuinely reachable from this environment, contrary to any
    assumption that sanctions or geo-blocking would prevent access.
    Deliberately conservative funding classification: the page states
    a competitively-awarded monthly stipend but does not itself state
    tuition is waived for every admitted student, so classified
    partial_funding rather than trusting aggregator "fully funded"
    claims. No deadline extracted: the page states the 2027 cycle's
    dates are not yet published."""
    source = SkoltechScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("skoltech_admissions.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "skoltech-scholarship"
    assert opportunity.title == "Skoltech Scholarship"
    assert opportunity.country == "Russia"
    assert (
        opportunity.provider_name
        == "Skolkovo Institute of Science and Technology (Skoltech)"
    )
    assert opportunity.description is not None
    assert "40,000 rubles per month" in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_skoltech_scholarship_has_no_robots_txt_restrictions() -> None:
    """robots.txt (`skoltech.ru/robots.txt`) sets `Allow: /` for
    `User-agent: *`, disallowing only `/admin/`, `/api/`, and query-
    string/JSON/XML paths - none of which cover this content path."""
    assert SkoltechScholarshipSource.min_request_interval_seconds == 2.0


# --- The University of Tokyo Scholarship (PEAK): real fixture, fetched 2026-09-07


@pytest.mark.asyncio
async def test_utokyo_peak_scholarship_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's first Japan *university* source (MEXT, #25, is
    government-classified). The overview page lists five distinct
    scholarships (this one, MEXT, two nationality-specific supplements,
    two Fast Retailing Foundation awards) - content selector
    `div.cmsSec-A:nth-of-type(2)` isolates only item (1)'s own text.
    Genuinely fully_funded: admission fee + tuition + JPY126,000/month
    living expenses, no nationality restriction, no deadline (awarded
    automatically upon admission, no separate application)."""
    source = UtokyoPeakScholarshipSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("utokyo_peak_scholarship.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == "university-of-tokyo-scholarship"
    assert opportunity.title == "University Of Tokyo Scholarship"
    assert opportunity.country == "Japan"
    assert (
        opportunity.provider_name
        == "University of Tokyo (PEAK - Programs in English at Komaba)"
    )
    assert opportunity.description is not None
    assert "JPY126,000 a month" in opportunity.description
    assert "MEXT" not in opportunity.description
    assert opportunity.funding_type == "fully_funded"
    assert opportunity.deadline is None


def test_utokyo_peak_scholarship_has_no_robots_txt_restrictions() -> None:
    """`peak.c.u-tokyo.ac.jp/robots.txt` returns HTTP 404 (no file
    published) - treated as no restrictions declared."""
    assert UtokyoPeakScholarshipSource.min_request_interval_seconds == 2.0


# --- Universiapolis International Encouragement Grant: real fixture, fetched 2026-09-07


@pytest.mark.asyncio
async def test_universiapolis_international_grant_collect_normalizes_real_fixture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This platform's first Morocco *university* source (AMCI, #29, is
    government-classified). The overview page lists four scholarship
    tiers, three of which explicitly require Moroccan nationality -
    `h3.wp-block-heading:nth-of-type(4)` and `p.wp-block-paragraph:
    nth-of-type(9)` isolate only the fourth tier, explicitly open to
    Sub-Saharan students (Sierra Leone included). Genuinely
    partial_funding (20% of tuition only), no deadline (none stated)."""
    source = UniversiapolisInternationalGrantSource()
    monkeypatch.setattr(
        web_scraper_base,
        "get_html",
        AsyncMock(return_value=_fixture("universiapolis_international_grant.html")),
    )

    result = await source.collect()

    assert len(result) == 1
    opportunity = result[0]
    assert opportunity.external_id == (
        "universiapolis-international-encouragement-grant"
    )
    assert opportunity.title == "Subvention d’encouragement international (Financement 20%)"
    assert opportunity.country == "Morocco"
    assert opportunity.provider_name == "Universiapolis (Agadir, Morocco)"
    assert opportunity.description is not None
    assert "subsahariens" in opportunity.description
    assert "marocaine" not in opportunity.description
    assert opportunity.funding_type == "partial_funding"
    assert opportunity.deadline is None


def test_universiapolis_international_grant_has_no_robots_txt_restrictions() -> (
    None
):
    """robots.txt (`universiapolis.ma/robots.txt`, a Yoast SEO default)
    sets an empty `Disallow:` for `User-agent: *` - no restrictions
    declared."""
    assert (
        UniversiapolisInternationalGrantSource.min_request_interval_seconds == 2.0
    )

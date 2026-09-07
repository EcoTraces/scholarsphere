from datetime import timedelta
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import OpportunitySource
from app.services.parsing import utc_now

SOURCE_DEFINITIONS: Final[dict[str, dict[str, str]]] = {
    "grants_gov": {
        "source_name": "Grants.gov",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "official",
    },
    "grants_gov_individual": {
        "source_name": "Grants.gov (Individual Eligibility)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "official",
    },
    "simpler_grants": {
        "source_name": "Simpler.Grants.gov",
        "source_type": "government",
        "authentication_type": "api_key",
        "trust_level": "official",
    },
    "eu_funding_tenders": {
        "source_name": "European Commission Funding & Tenders",
        "source_type": "international_government",
        "authentication_type": "api_key",
        "trust_level": "official",
    },
    "usajobs": {
        "source_name": "USAJOBS",
        "source_type": "government",
        "authentication_type": "api_key",
        "trust_level": "official",
    },
    "reliefweb_jobs": {
        "source_name": "ReliefWeb Jobs",
        "source_type": "international_organization",
        "authentication_type": "app_identifier",
        "trust_level": "official",
    },
    "reliefweb_training": {
        "source_name": "ReliefWeb Training",
        "source_type": "international_organization",
        "authentication_type": "app_identifier",
        "trust_level": "official",
    },
    "manual_collection": {
        "source_name": "Manual/ad hoc collection",
        "source_type": "manual",
        "authentication_type": "none",
        "trust_level": "community",
    },
    # Web-scraper sources - no official API/RSS/dataset exists for these
    # organizations (see docs/AUTHORITATIVE_SOURCES.md #8-#12). trust_level
    # "web_scraped" is deliberately lower than "official": it still lands
    # in the same mandatory human-verification queue as every other
    # source (never auto-published - see
    # docs/OPPORTUNITY_VERIFICATION_SYSTEM.md), but scores lower in
    # app/services/verification_confidence.py so an officer sees the
    # trust distinction explicitly rather than it being silently implied.
    "cscuk_scholarships": {
        "source_name": "Commonwealth Scholarships (CSC UK)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "chevening": {
        "source_name": "Chevening Scholarships",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "daad_scholarships": {
        "source_name": "DAAD Scholarship Database",
        "source_type": "quasi_governmental",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "china_embassy_sl": {
        "source_name": "Chinese Embassy in Sierra Leone (Scholarship Announcements)",
        "source_type": "embassy",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "mthe_sierra_leone": {
        "source_name": "Sierra Leone Ministry of Technical and Higher Education",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    # Country-expansion single-flagship-program sources (2026-08-23) - see
    # docs/AUTHORITATIVE_SOURCES.md #13-#18.
    "wmi_scholars": {
        "source_name": "Wells Mountain Initiative (WMI) Scholars Program",
        "source_type": "funding_organization",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "turkiye_burslari": {
        "source_name": "Türkiye Bursları (Türkiye Scholarships)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "ireland_goi_ies": {
        "source_name": "Government of Ireland International Education Scholarships",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "india_iccr": {
        "source_name": "ICCR Scholarship Programme (India)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "sweden_si_scholarship": {
        "source_name": "Swedish Institute Scholarships for Global Professionals",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "eswatini_slas": {
        "source_name": "Eswatini Scholarship Loan Application System (SLAS)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "italy_maeci_scholarships": {
        "source_name": "Italian Government Scholarships (MAECI)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "greece_iky_scholarships": {
        "source_name": "IKY Foreign Nationals Scholarships (Greece)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "south_africa_nrf": {
        "source_name": "National Research Foundation (NRF) Postgraduate Funding (South Africa)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "netherlands_nuffic": {
        "source_name": "Nuffic NL Scholarship (Netherlands)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "spain_aecid": {
        "source_name": "AECID Scholarships for Latin America, Africa and Asia (Spain)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "australia_dfat_awards": {
        "source_name": "Australia Awards (DFAT)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "japan_mext": {
        "source_name": "Japanese Government (MEXT) Scholarship (Japan)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "belgium_ares": {
        "source_name": "ARES International Training Scholarships (Belgium)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "france_eiffel": {
        "source_name": "France Excellence Eiffel Scholarship",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "austria_oead": {
        "source_name": "OeAD Ernst Mach Grant (Austria)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "morocco_amci": {
        "source_name": "AMCI Scholarships of the Kingdom of Morocco",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "portugal_camoes": {
        "source_name": "Camões Cooperation Scholarships (Portugal)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "colombia_icetex": {
        "source_name": "Beca Colombia Extranjeros (ICETEX)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "chile_agcid": {
        "source_name": "Becas para Extranjeros (AGCID, Chile)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "peru_pronabec": {
        "source_name": "Beca Alianza del Pacífico (PRONABEC, Peru)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "south_korea_gks": {
        "source_name": "GKS (Global Korea Scholarship) Program",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "saudi_arabia_moe": {
        "source_name": "Government University Scholarships (MOE, Saudi Arabia)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "qatar_scholarships": {
        "source_name": "Qatar Scholarships (QFFD)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "switzerland_sbfi_eskas": {
        "source_name": "Swiss Government Excellence Scholarships (ESKAS)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "poland_nawa_myfirstchoice": {
        "source_name": "Poland My First Choice (NAWA)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "czech_republic_msmt": {
        "source_name": "Government Scholarships - Developing Countries (MŠMT, Czech Republic)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "serbia_world_in_serbia": {
        "source_name": "World in Serbia Scholarships",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "romania_mfa": {
        "source_name": "Romanian Government Scholarships (MFA)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "hungary_stipendium_hungaricum": {
        "source_name": "Stipendium Hungaricum",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "mexico_amexcid": {
        "source_name": "Becas de Excelencia del Gobierno de México (AMEXCID)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "educationusa_financial_aid": {
        "source_name": "EducationUSA Find Financial Aid (US Department of State)",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "world_bank_jjwbgsp": {
        "source_name": "Joint Japan/World Bank Graduate Scholarship Program",
        "source_type": "international_organization",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "rotary_peace_fellowship": {
        "source_name": "Rotary Peace Fellowships (The Rotary Foundation)",
        "source_type": "funding_organization",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "erasmus_mundus_joint_masters": {
        "source_name": "Erasmus Mundus Joint Masters Catalogue (EACEA)",
        "source_type": "international_organization",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "uaeu_scholarships": {
        "source_name": "UAEU Scholarships, Fellowships, and Graduate Assistantships",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "mastercard_foundation_scholars": {
        "source_name": "Mastercard Foundation Scholars Program",
        "source_type": "foundation",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "schwarzman_scholars": {
        "source_name": "Schwarzman Scholars",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "knight_hennessy_scholars": {
        "source_name": "Knight-Hennessy Scholars",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "yenching_academy_scholars": {
        "source_name": "Yenching Academy of Peking University",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "eth_zurich_esop": {
        "source_name": "ETH Zurich Excellence Scholarship & Opportunity Programme",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "hkpfs": {
        "source_name": "Hong Kong PhD Fellowship Scheme",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "taiwan_icdf_scholarship": {
        "source_name": "TaiwanICDF International Higher Education Scholarship Program",
        "source_type": "government",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "humboldt_research_fellowship": {
        "source_name": "Humboldt Research Fellowship",
        "source_type": "foundation",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "max_planck_schools": {
        "source_name": "Max Planck Schools",
        "source_type": "research_institution",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "tudelft_van_effen_scholarship": {
        "source_name": "TU Delft Justus & Louise van Effen Excellence Scholarships",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "tum_international_student_scholarship": {
        "source_name": "TUM Scholarship for International Students",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "imperial_inspires_scholarship": {
        "source_name": "Imperial Inspires Scholarships",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "newcastle_vc_international_scholarship": {
        "source_name": "Newcastle University Vice-Chancellor's International Scholarships",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "sheffield_pg_scholarship": {
        "source_name": "University of Sheffield International Postgraduate Scholarship",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "manchester_global_futures_scholarship": {
        "source_name": "University of Manchester Global Futures Scholarships",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "nottingham_pg_scholarship": {
        "source_name": "University of Nottingham International Postgraduate Scholarship",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "southampton_presidential_bursaries": {
        "source_name": "University of Southampton Presidential Bursaries",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "southampton_merit_undergraduate_scholarship": {
        "source_name": "University of Southampton Merit Scholarships for International Undergraduates",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "durham_inspiring_excellence_undergraduate_scholarship": {
        "source_name": "Durham Inspiring Excellence Scholarship (Undergraduate)",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "durham_inspiring_excellence_postgraduate_scholarship": {
        "source_name": "Durham Inspiring Excellence Scholarship (Postgraduate)",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "freiburg_deutschlandstipendium": {
        "source_name": "University of Freiburg Deutschlandstipendium",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "uva_amsterdam_merit_scholarship_master": {
        "source_name": "University of Amsterdam Amsterdam Merit Scholarship (Master's)",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "uva_amsterdam_merit_scholarship_bachelor": {
        "source_name": "University of Amsterdam Amsterdam Merit Scholarship (Bachelor's)",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "groningen_eric_bleumink_fellowship": {
        "source_name": "University of Groningen Eric Bleumink Fellowship",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "utrecht_legits_scholarship": {
        "source_name": (
            "Utrecht University Law, Economics and Governance "
            "International Talent Scholarship"
        ),
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "maastricht_high_potential_scholarship": {
        "source_name": "Maastricht University NL-High Potential Scholarship",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "university_of_twente_scholarship": {
        "source_name": "University of Twente Scholarship (UTS)",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "wageningen_anne_van_den_ban_fund": {
        "source_name": "Wageningen University Anne van den Ban Fund",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "utwente_itc_scholarship": {
        "source_name": "University of Twente ITC Excellence Scholarship Programme",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "upf_bsm_merit_scholarship": {
        "source_name": "UPF Barcelona School of Management Merit Based Scholarship",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "sciencespo_mastercard_scholars": {
        "source_name": "Sciences Po Mastercard Foundation Scholars Program",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "pku_international_scholarship": {
        "source_name": "Peking University Scholarship for International Students",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "sjtu_masters_scholarship": {
        "source_name": "Shanghai Jiao Tong University Master's SJTU Scholarship",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "mcgill_mastercard_scholars": {
        "source_name": "McGill University Mastercard Foundation Scholars Program",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "gates_cambridge_scholarship": {
        "source_name": "Gates Cambridge Scholarship",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "heinrich_boll_scholarship": {
        "source_name": "Heinrich Böll Foundation Scholarship",
        "source_type": "foundation",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "helmut_veith_stipend": {
        "source_name": "Helmut Veith Stipend (TU Wien / VCLA)",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "usyd_rtp_international": {
        "source_name": "University of Sydney RTP Scholarships (International)",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "uq_graduate_research_scholarships": {
        "source_name": "University of Queensland Graduate Research School Scholarships",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "harrington_graduate_fellows": {
        "source_name": "UT Austin Harrington Graduate Fellows Program",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "vanderbilt_cornelius_scholarship": {
        "source_name": "Vanderbilt University Cornelius Vanderbilt Scholarship",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "skoltech_scholarship": {
        "source_name": "Skoltech Admissions Scholarship",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "utokyo_peak_scholarship": {
        "source_name": "The University of Tokyo Scholarship (PEAK)",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "universiapolis_international_grant": {
        "source_name": "Universiapolis International Encouragement Grant",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
    "royal_holloway_international_ug_scholarship": {
        "source_name": "Royal Holloway International Undergraduate Scholarship",
        "source_type": "university",
        "authentication_type": "none",
        "trust_level": "web_scraped",
    },
}


def _base_urls() -> dict[str, str]:
    settings = get_settings()
    reliefweb_base = settings.reliefweb_base_url.rstrip("/")
    return {
        "grants_gov": settings.grants_gov_base_url,
        "grants_gov_individual": settings.grants_gov_base_url,
        "simpler_grants": settings.simpler_grants_base_url,
        "eu_funding_tenders": settings.eu_funding_api_url,
        "usajobs": settings.usajobs_base_url,
        "reliefweb_jobs": f"{reliefweb_base}/jobs",
        "reliefweb_training": f"{reliefweb_base}/training",
        "manual_collection": "",
        "cscuk_scholarships": settings.cscuk_base_url,
        "chevening": settings.chevening_base_url,
        "daad_scholarships": settings.daad_base_url,
        "china_embassy_sl": settings.china_embassy_sl_base_url,
        "mthe_sierra_leone": settings.mthe_sl_base_url,
        "wmi_scholars": settings.wmi_base_url,
        "turkiye_burslari": settings.turkiye_burslari_base_url,
        "ireland_goi_ies": settings.ireland_hea_base_url,
        "india_iccr": settings.india_iccr_base_url,
        "sweden_si_scholarship": settings.sweden_si_base_url,
        "eswatini_slas": settings.eswatini_slas_base_url,
        "italy_maeci_scholarships": settings.italy_esteri_base_url,
        "greece_iky_scholarships": settings.greece_iky_base_url,
        "south_africa_nrf": settings.south_africa_nrf_base_url,
        "netherlands_nuffic": settings.netherlands_nuffic_base_url,
        "spain_aecid": settings.spain_aecid_base_url,
        "australia_dfat_awards": settings.australia_awards_base_url,
        "japan_mext": settings.japan_mext_base_url,
        "belgium_ares": settings.belgium_ares_base_url,
        "france_eiffel": settings.france_campusfrance_base_url,
        "austria_oead": settings.austria_oead_base_url,
        "morocco_amci": settings.morocco_amci_base_url,
        "portugal_camoes": settings.portugal_camoes_base_url,
        "colombia_icetex": settings.colombia_icetex_base_url,
        "chile_agcid": settings.chile_agcid_base_url,
        "peru_pronabec": settings.peru_pronabec_base_url,
        "south_korea_gks": settings.south_korea_gks_base_url,
        "saudi_arabia_moe": settings.saudi_arabia_moe_base_url,
        "qatar_scholarships": settings.qatar_scholarships_base_url,
        "switzerland_sbfi_eskas": settings.switzerland_sbfi_base_url,
        "poland_nawa_myfirstchoice": settings.poland_nawa_base_url,
        "czech_republic_msmt": settings.czech_republic_msmt_base_url,
        "serbia_world_in_serbia": settings.serbia_welcometoserbia_base_url,
        "romania_mfa": settings.romania_mfa_base_url,
        "hungary_stipendium_hungaricum": settings.hungary_stipendium_base_url,
        "mexico_amexcid": settings.mexico_amexcid_base_url,
        "educationusa_financial_aid": settings.educationusa_base_url,
        "world_bank_jjwbgsp": settings.world_bank_jjwbgsp_base_url,
        "rotary_peace_fellowship": settings.rotary_peace_fellowship_base_url,
        "erasmus_mundus_joint_masters": settings.erasmus_mundus_base_url,
        "uaeu_scholarships": settings.uaeu_base_url,
        "mastercard_foundation_scholars": settings.mastercard_foundation_base_url,
        "schwarzman_scholars": settings.schwarzman_scholars_base_url,
        "knight_hennessy_scholars": settings.knight_hennessy_scholars_base_url,
        "yenching_academy_scholars": settings.yenching_academy_base_url,
        "eth_zurich_esop": settings.eth_zurich_esop_base_url,
        "hkpfs": settings.hkpfs_base_url,
        "taiwan_icdf_scholarship": settings.taiwan_icdf_base_url,
        "humboldt_research_fellowship": settings.humboldt_foundation_base_url,
        "max_planck_schools": settings.max_planck_schools_base_url,
        "tudelft_van_effen_scholarship": settings.tudelft_van_effen_base_url,
        "tum_international_student_scholarship": (
            settings.tum_international_scholarship_base_url
        ),
        "imperial_inspires_scholarship": settings.imperial_inspires_base_url,
        "newcastle_vc_international_scholarship": settings.newcastle_vcis_base_url,
        "sheffield_pg_scholarship": settings.sheffield_pg_scholarship_base_url,
        "manchester_global_futures_scholarship": settings.manchester_gfs_base_url,
        "nottingham_pg_scholarship": settings.nottingham_pg_scholarship_base_url,
        "southampton_presidential_bursaries": (
            settings.southampton_presidential_bursaries_base_url
        ),
        "southampton_merit_undergraduate_scholarship": (
            settings.southampton_merit_ug_base_url
        ),
        "durham_inspiring_excellence_undergraduate_scholarship": (
            settings.durham_inspiring_excellence_ug_base_url
        ),
        "durham_inspiring_excellence_postgraduate_scholarship": (
            settings.durham_inspiring_excellence_pg_base_url
        ),
        "freiburg_deutschlandstipendium": (
            settings.freiburg_deutschlandstipendium_base_url
        ),
        "uva_amsterdam_merit_scholarship_master": (
            settings.uva_amsterdam_merit_scholarship_master_base_url
        ),
        "uva_amsterdam_merit_scholarship_bachelor": (
            settings.uva_amsterdam_merit_scholarship_bachelor_base_url
        ),
        "groningen_eric_bleumink_fellowship": (
            settings.groningen_eric_bleumink_fellowship_base_url
        ),
        "utrecht_legits_scholarship": settings.utrecht_legits_scholarship_base_url,
        "maastricht_high_potential_scholarship": (
            settings.maastricht_high_potential_scholarship_base_url
        ),
        "university_of_twente_scholarship": settings.utwente_scholarship_base_url,
        "wageningen_anne_van_den_ban_fund": (
            settings.wageningen_anne_van_den_ban_fund_base_url
        ),
        "utwente_itc_scholarship": settings.utwente_itc_scholarship_base_url,
        "upf_bsm_merit_scholarship": settings.upf_bsm_merit_scholarship_base_url,
        "sciencespo_mastercard_scholars": (
            settings.sciencespo_mastercard_scholars_base_url
        ),
        "pku_international_scholarship": (
            settings.pku_international_scholarship_base_url
        ),
        "sjtu_masters_scholarship": settings.sjtu_masters_scholarship_base_url,
        "mcgill_mastercard_scholars": settings.mcgill_mastercard_scholars_base_url,
        "gates_cambridge_scholarship": settings.gates_cambridge_scholarship_base_url,
        "heinrich_boll_scholarship": settings.heinrich_boll_scholarship_base_url,
        "helmut_veith_stipend": settings.helmut_veith_stipend_base_url,
        "usyd_rtp_international": settings.usyd_rtp_international_base_url,
        "uq_graduate_research_scholarships": (
            settings.uq_graduate_research_scholarships_base_url
        ),
        "harrington_graduate_fellows": settings.harrington_graduate_fellows_base_url,
        "vanderbilt_cornelius_scholarship": (
            settings.vanderbilt_cornelius_scholarship_base_url
        ),
        "skoltech_scholarship": settings.skoltech_scholarship_base_url,
        "utokyo_peak_scholarship": settings.utokyo_peak_scholarship_base_url,
        "universiapolis_international_grant": (
            settings.universiapolis_international_grant_base_url
        ),
        "royal_holloway_international_ug_scholarship": (
            settings.royal_holloway_international_ug_scholarship_base_url
        ),
    }


async def seed_opportunity_sources(
    session: AsyncSession,
) -> dict[str, OpportunitySource]:
    """Idempotently create sources and return every configured source by code."""
    existing = {
        source.source_code: source
        for source in (
            await session.scalars(
                select(OpportunitySource).where(
                    OpportunitySource.source_code.in_(tuple(SOURCE_DEFINITIONS))
                )
            )
        ).all()
    }
    base_urls = _base_urls()
    now = utc_now()
    next_runs = {
        "grants_gov": now + timedelta(hours=6),
        "grants_gov_individual": now + timedelta(hours=6),
        "simpler_grants": now + timedelta(hours=6),
        "eu_funding_tenders": now + timedelta(hours=12),
        "usajobs": now + timedelta(hours=6),
        "reliefweb_jobs": now + timedelta(hours=6),
        "reliefweb_training": now + timedelta(hours=12),
        # Web-scraper sources sync once daily, not every 6-12h like the
        # official APIs - lower volume of change, and a deliberately
        # gentler request cadence for sources without a documented rate
        # limit of their own (see docs/AUTHORITATIVE_SOURCES.md).
        "cscuk_scholarships": now + timedelta(hours=24),
        "chevening": now + timedelta(hours=24),
        "daad_scholarships": now + timedelta(hours=24),
        "china_embassy_sl": now + timedelta(hours=24),
        "mthe_sierra_leone": now + timedelta(hours=24),
        "wmi_scholars": now + timedelta(hours=24),
        "turkiye_burslari": now + timedelta(hours=24),
        "ireland_goi_ies": now + timedelta(hours=24),
        "india_iccr": now + timedelta(hours=24),
        "sweden_si_scholarship": now + timedelta(hours=24),
        "eswatini_slas": now + timedelta(hours=24),
        "italy_maeci_scholarships": now + timedelta(hours=24),
        "greece_iky_scholarships": now + timedelta(hours=24),
        "south_africa_nrf": now + timedelta(hours=24),
        "netherlands_nuffic": now + timedelta(hours=24),
        "spain_aecid": now + timedelta(hours=24),
        "australia_dfat_awards": now + timedelta(hours=24),
        "japan_mext": now + timedelta(hours=24),
        "belgium_ares": now + timedelta(hours=24),
        "france_eiffel": now + timedelta(hours=24),
        "austria_oead": now + timedelta(hours=24),
        "morocco_amci": now + timedelta(hours=24),
        "portugal_camoes": now + timedelta(hours=24),
        "colombia_icetex": now + timedelta(hours=24),
        "chile_agcid": now + timedelta(hours=24),
        "peru_pronabec": now + timedelta(hours=24),
        "south_korea_gks": now + timedelta(hours=24),
        "saudi_arabia_moe": now + timedelta(hours=24),
        "qatar_scholarships": now + timedelta(hours=24),
        "switzerland_sbfi_eskas": now + timedelta(hours=24),
        "poland_nawa_myfirstchoice": now + timedelta(hours=24),
        "czech_republic_msmt": now + timedelta(hours=24),
        "serbia_world_in_serbia": now + timedelta(hours=24),
        "romania_mfa": now + timedelta(hours=24),
        "hungary_stipendium_hungaricum": now + timedelta(hours=24),
        "mexico_amexcid": now + timedelta(hours=24),
        "educationusa_financial_aid": now + timedelta(hours=24),
        "world_bank_jjwbgsp": now + timedelta(hours=24),
        "rotary_peace_fellowship": now + timedelta(hours=24),
        "erasmus_mundus_joint_masters": now + timedelta(hours=24),
        "uaeu_scholarships": now + timedelta(hours=24),
        "mastercard_foundation_scholars": now + timedelta(hours=24),
        "schwarzman_scholars": now + timedelta(hours=24),
        "knight_hennessy_scholars": now + timedelta(hours=24),
        "yenching_academy_scholars": now + timedelta(hours=24),
        "eth_zurich_esop": now + timedelta(hours=24),
        "hkpfs": now + timedelta(hours=24),
        "taiwan_icdf_scholarship": now + timedelta(hours=24),
        "humboldt_research_fellowship": now + timedelta(hours=24),
        "max_planck_schools": now + timedelta(hours=24),
        "tudelft_van_effen_scholarship": now + timedelta(hours=24),
        "tum_international_student_scholarship": now + timedelta(hours=24),
        "imperial_inspires_scholarship": now + timedelta(hours=24),
        "newcastle_vc_international_scholarship": now + timedelta(hours=24),
        "sheffield_pg_scholarship": now + timedelta(hours=24),
        "manchester_global_futures_scholarship": now + timedelta(hours=24),
        "nottingham_pg_scholarship": now + timedelta(hours=24),
        "southampton_presidential_bursaries": now + timedelta(hours=24),
        "southampton_merit_undergraduate_scholarship": now + timedelta(hours=24),
        "durham_inspiring_excellence_undergraduate_scholarship": now + timedelta(hours=24),
        "durham_inspiring_excellence_postgraduate_scholarship": now + timedelta(hours=24),
        "freiburg_deutschlandstipendium": now + timedelta(hours=24),
        "uva_amsterdam_merit_scholarship_master": now + timedelta(hours=24),
        "uva_amsterdam_merit_scholarship_bachelor": now + timedelta(hours=24),
        "groningen_eric_bleumink_fellowship": now + timedelta(hours=24),
        "utrecht_legits_scholarship": now + timedelta(hours=24),
        "maastricht_high_potential_scholarship": now + timedelta(hours=24),
        "university_of_twente_scholarship": now + timedelta(hours=24),
        "wageningen_anne_van_den_ban_fund": now + timedelta(hours=24),
        "utwente_itc_scholarship": now + timedelta(hours=24),
        "upf_bsm_merit_scholarship": now + timedelta(hours=24),
        "sciencespo_mastercard_scholars": now + timedelta(hours=24),
        "pku_international_scholarship": now + timedelta(hours=24),
        "sjtu_masters_scholarship": now + timedelta(hours=24),
        "mcgill_mastercard_scholars": now + timedelta(hours=24),
        "gates_cambridge_scholarship": now + timedelta(hours=24),
        "heinrich_boll_scholarship": now + timedelta(hours=24),
        "helmut_veith_stipend": now + timedelta(hours=24),
        "usyd_rtp_international": now + timedelta(hours=24),
        "uq_graduate_research_scholarships": now + timedelta(hours=24),
        "harrington_graduate_fellows": now + timedelta(hours=24),
        "vanderbilt_cornelius_scholarship": now + timedelta(hours=24),
        "skoltech_scholarship": now + timedelta(hours=24),
        "utokyo_peak_scholarship": now + timedelta(hours=24),
        "universiapolis_international_grant": now + timedelta(hours=24),
        "royal_holloway_international_ug_scholarship": now + timedelta(hours=24),
    }
    for source_code, definition in SOURCE_DEFINITIONS.items():
        next_run = next_runs.get(source_code, now + timedelta(hours=6))
        if source_code in existing:
            if existing[source_code].next_scheduled_sync is None:
                existing[source_code].next_scheduled_sync = next_run
            continue
        source = OpportunitySource(
            source_code=source_code,
            base_url=base_urls[source_code],
            next_scheduled_sync=next_run,
            **definition,
        )
        session.add(source)
        existing[source_code] = source
    await session.flush()
    return existing

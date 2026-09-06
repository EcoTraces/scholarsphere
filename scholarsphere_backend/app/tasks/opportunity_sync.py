import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, timedelta
from time import monotonic
from typing import Any, Coroutine, TypeVar
from uuid import uuid4

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError
from app.db.session import AsyncSessionFactory
from app.models import (
    ExternalOpportunity,
    ImportAuditLog,
    OpportunitySource,
    OpportunitySyncHistory,
    RawExternalOpportunity,
    VerificationHistory,
    VerificationReview,
)
from app.models.external_opportunity import (
    ProcessingStatus,
    PublicationStatus,
    SyncStatus,
    VerificationStatus,
)
from app.models.notification import (
    NotificationDeliveryStatus,
    NotificationEventType,
    NotificationPreferences,
    ScholarSphereNotification,
)
from app.services.cscuk_scholarships import CscukScholarshipsSource
from app.services.chevening import CheveningSource
from app.services.daad_scholarships import DaadScholarshipsSource
from app.services.embassy_announcements import (
    ChinaEmbassySierraLeoneSource,
    EswatiniSlasSource,
    SierraLeoneMTHESource,
)
from app.services.eu_funding import EUFundingSource
from app.services.audit import append_audit
from app.services.firebase_users import (
    FirebaseRosterError,
    list_reverification_recipient_uids,
)
from app.services.grants_gov import GrantsGovIndividualSource, GrantsGovSource
from app.services.link_health import check_link_reachable
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
    DurhamInspiringExcellencePostgraduateScholarshipSource,
    DurhamInspiringExcellenceUndergraduateScholarshipSource,
    EthZurichExcellenceScholarshipSource,
    FreiburgDeutschlandstipendiumSource,
    HongKongPhdFellowshipSchemeSource,
    HumboldtResearchFellowshipSource,
    ImperialInspiresScholarshipSource,
    KnightHennessyScholarsSource,
    ManchesterGlobalFuturesScholarshipSource,
    MaxPlanckSchoolsSource,
    NewcastleVcInternationalScholarshipSource,
    NottinghamPgScholarshipSource,
    RotaryPeaceFellowshipSource,
    SchwarzmanScholarsSource,
    SheffieldPgScholarshipSource,
    SouthamptonMeritUndergraduateScholarshipSource,
    SouthamptonPresidentialBursariesSource,
    TaiwanIcdfScholarshipSource,
    TuDelftVanEffenScholarshipSource,
    TumInternationalStudentScholarshipSource,
    TurkiyeBurslariSource,
    WellsMountainInitiativeSource,
    WorldBankJJWBGSPScholarshipSource,
    YenchingAcademyScholarsSource,
)
from app.services.educationusa_source import EducationUsaFinancialAidSource
from app.services.erasmus_mundus_source import ErasmusMundusJointMastersSource
from app.services.uaeu_scholarships_source import UaeuScholarshipsSource
from app.services.mastercard_foundation_scholars_source import (
    MastercardFoundationScholarsSource,
)
from app.services.notification_dispatch import (
    default_preferences,
    event_title,
    wants_in_app_notification,
)
from app.services.opportunity_import import import_opportunities
from app.services.parsing import utc_now
from app.services.reliefweb import ReliefWebJobsSource, ReliefWebTrainingSource
from app.services.simpler_grants import SimplerGrantsSource
from app.services.source_registry import seed_opportunity_sources
from app.services.usajobs import UsaJobsSource

logger = logging.getLogger(__name__)
settings = get_settings()
celery_app = Celery(
    "scholarsphere",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.opportunity_sync", "app.tasks.notifications"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "sync-grants-gov": {
            "task": "app.tasks.opportunity_sync.sync_grants_gov",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "sync-grants-gov-individual": {
            "task": "app.tasks.opportunity_sync.sync_grants_gov_individual",
            "schedule": crontab(minute=10, hour="*/6"),
        },
        "sync-simpler-grants": {
            "task": "app.tasks.opportunity_sync.sync_simpler_grants",
            "schedule": crontab(minute=20, hour="*/6"),
        },
        "sync-eu-funding": {
            "task": "app.tasks.opportunity_sync.sync_eu_funding",
            "schedule": crontab(minute=40, hour="*/12"),
        },
        "sync-usajobs": {
            "task": "app.tasks.opportunity_sync.sync_usajobs",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "sync-reliefweb-jobs": {
            "task": "app.tasks.opportunity_sync.sync_reliefweb_jobs",
            "schedule": crontab(minute=20, hour="*/6"),
        },
        "sync-reliefweb-training": {
            "task": "app.tasks.opportunity_sync.sync_reliefweb_training",
            "schedule": crontab(minute=50, hour="*/12"),
        },
        "sync-cscuk-scholarships": {
            "task": "app.tasks.opportunity_sync.sync_cscuk_scholarships",
            "schedule": crontab(minute=0, hour=3),
        },
        "sync-chevening": {
            "task": "app.tasks.opportunity_sync.sync_chevening",
            "schedule": crontab(minute=15, hour=3),
        },
        "sync-daad-scholarships": {
            "task": "app.tasks.opportunity_sync.sync_daad_scholarships",
            "schedule": crontab(minute=30, hour=3),
        },
        "sync-china-embassy-sl": {
            "task": "app.tasks.opportunity_sync.sync_china_embassy_sl",
            "schedule": crontab(minute=45, hour=3),
        },
        "sync-mthe-sierra-leone": {
            "task": "app.tasks.opportunity_sync.sync_mthe_sierra_leone",
            "schedule": crontab(minute=0, hour=4),
        },
        "sync-wmi-scholars": {
            "task": "app.tasks.opportunity_sync.sync_wmi_scholars",
            "schedule": crontab(minute=15, hour=4),
        },
        "sync-turkiye-burslari": {
            "task": "app.tasks.opportunity_sync.sync_turkiye_burslari",
            "schedule": crontab(minute=30, hour=4),
        },
        "sync-ireland-goi-ies": {
            "task": "app.tasks.opportunity_sync.sync_ireland_goi_ies",
            "schedule": crontab(minute=45, hour=4),
        },
        "sync-india-iccr": {
            "task": "app.tasks.opportunity_sync.sync_india_iccr",
            "schedule": crontab(minute=0, hour=5),
        },
        "sync-sweden-si-scholarship": {
            "task": "app.tasks.opportunity_sync.sync_sweden_si_scholarship",
            "schedule": crontab(minute=15, hour=5),
        },
        "sync-eswatini-slas": {
            "task": "app.tasks.opportunity_sync.sync_eswatini_slas",
            "schedule": crontab(minute=30, hour=5),
        },
        "sync-italy-maeci-scholarships": {
            "task": "app.tasks.opportunity_sync.sync_italy_maeci_scholarships",
            "schedule": crontab(minute=45, hour=5),
        },
        "sync-greece-iky-scholarships": {
            "task": "app.tasks.opportunity_sync.sync_greece_iky_scholarships",
            "schedule": crontab(minute=0, hour=6),
        },
        "sync-south-africa-nrf": {
            "task": "app.tasks.opportunity_sync.sync_south_africa_nrf",
            "schedule": crontab(minute=15, hour=6),
        },
        "sync-netherlands-nuffic": {
            "task": "app.tasks.opportunity_sync.sync_netherlands_nuffic",
            "schedule": crontab(minute=30, hour=6),
        },
        "sync-spain-aecid": {
            "task": "app.tasks.opportunity_sync.sync_spain_aecid",
            "schedule": crontab(minute=45, hour=6),
        },
        "sync-australia-dfat-awards": {
            "task": "app.tasks.opportunity_sync.sync_australia_dfat_awards",
            "schedule": crontab(minute=0, hour=7),
        },
        "sync-japan-mext": {
            "task": "app.tasks.opportunity_sync.sync_japan_mext",
            "schedule": crontab(minute=15, hour=7),
        },
        "sync-belgium-ares": {
            "task": "app.tasks.opportunity_sync.sync_belgium_ares",
            "schedule": crontab(minute=30, hour=7),
        },
        "sync-france-eiffel": {
            "task": "app.tasks.opportunity_sync.sync_france_eiffel",
            "schedule": crontab(minute=45, hour=7),
        },
        "sync-austria-oead": {
            "task": "app.tasks.opportunity_sync.sync_austria_oead",
            "schedule": crontab(minute=0, hour=8),
        },
        "sync-morocco-amci": {
            "task": "app.tasks.opportunity_sync.sync_morocco_amci",
            "schedule": crontab(minute=15, hour=8),
        },
        "sync-portugal-camoes": {
            "task": "app.tasks.opportunity_sync.sync_portugal_camoes",
            "schedule": crontab(minute=30, hour=8),
        },
        "sync-colombia-icetex": {
            "task": "app.tasks.opportunity_sync.sync_colombia_icetex",
            "schedule": crontab(minute=45, hour=8),
        },
        "sync-chile-agcid": {
            "task": "app.tasks.opportunity_sync.sync_chile_agcid",
            "schedule": crontab(minute=0, hour=9),
        },
        "sync-peru-pronabec": {
            "task": "app.tasks.opportunity_sync.sync_peru_pronabec",
            "schedule": crontab(minute=15, hour=9),
        },
        "sync-south-korea-gks": {
            "task": "app.tasks.opportunity_sync.sync_south_korea_gks",
            "schedule": crontab(minute=30, hour=9),
        },
        "sync-saudi-arabia-moe": {
            "task": "app.tasks.opportunity_sync.sync_saudi_arabia_moe",
            "schedule": crontab(minute=45, hour=9),
        },
        "sync-qatar-scholarships": {
            "task": "app.tasks.opportunity_sync.sync_qatar_scholarships",
            "schedule": crontab(minute=0, hour=10),
        },
        "sync-switzerland-sbfi-eskas": {
            "task": "app.tasks.opportunity_sync.sync_switzerland_sbfi_eskas",
            "schedule": crontab(minute=15, hour=10),
        },
        "sync-poland-nawa-myfirstchoice": {
            "task": "app.tasks.opportunity_sync.sync_poland_nawa_myfirstchoice",
            "schedule": crontab(minute=30, hour=10),
        },
        "sync-czech-republic-msmt": {
            "task": "app.tasks.opportunity_sync.sync_czech_republic_msmt",
            "schedule": crontab(minute=45, hour=10),
        },
        "sync-serbia-world-in-serbia": {
            "task": "app.tasks.opportunity_sync.sync_serbia_world_in_serbia",
            "schedule": crontab(minute=0, hour=11),
        },
        "sync-romania-mfa": {
            "task": "app.tasks.opportunity_sync.sync_romania_mfa",
            "schedule": crontab(minute=15, hour=11),
        },
        "sync-hungary-stipendium-hungaricum": {
            "task": "app.tasks.opportunity_sync.sync_hungary_stipendium_hungaricum",
            "schedule": crontab(minute=30, hour=11),
        },
        "sync-mexico-amexcid": {
            "task": "app.tasks.opportunity_sync.sync_mexico_amexcid",
            "schedule": crontab(minute=45, hour=11),
        },
        "sync-educationusa-financial-aid": {
            "task": "app.tasks.opportunity_sync.sync_educationusa_financial_aid",
            "schedule": crontab(minute=0, hour=12),
        },
        "sync-world-bank-jjwbgsp": {
            "task": "app.tasks.opportunity_sync.sync_world_bank_jjwbgsp",
            "schedule": crontab(minute=15, hour=12),
        },
        "sync-rotary-peace-fellowship": {
            "task": "app.tasks.opportunity_sync.sync_rotary_peace_fellowship",
            "schedule": crontab(minute=30, hour=12),
        },
        "sync-erasmus-mundus-joint-masters": {
            "task": "app.tasks.opportunity_sync.sync_erasmus_mundus_joint_masters",
            "schedule": crontab(minute=45, hour=12),
        },
        "sync-uaeu-scholarships": {
            "task": "app.tasks.opportunity_sync.sync_uaeu_scholarships",
            "schedule": crontab(minute=0, hour=13),
        },
        "sync-mastercard-foundation-scholars": {
            "task": "app.tasks.opportunity_sync.sync_mastercard_foundation_scholars",
            "schedule": crontab(minute=15, hour=13),
        },
        "sync-schwarzman-scholars": {
            "task": "app.tasks.opportunity_sync.sync_schwarzman_scholars",
            "schedule": crontab(minute=30, hour=13),
        },
        "sync-knight-hennessy-scholars": {
            "task": "app.tasks.opportunity_sync.sync_knight_hennessy_scholars",
            "schedule": crontab(minute=45, hour=13),
        },
        "sync-yenching-academy-scholars": {
            "task": "app.tasks.opportunity_sync.sync_yenching_academy_scholars",
            "schedule": crontab(minute=0, hour=14),
        },
        "sync-eth-zurich-esop": {
            "task": "app.tasks.opportunity_sync.sync_eth_zurich_esop",
            "schedule": crontab(minute=15, hour=14),
        },
        "sync-hkpfs": {
            "task": "app.tasks.opportunity_sync.sync_hkpfs",
            "schedule": crontab(minute=30, hour=14),
        },
        "sync-taiwan-icdf-scholarship": {
            "task": "app.tasks.opportunity_sync.sync_taiwan_icdf_scholarship",
            "schedule": crontab(minute=45, hour=14),
        },
        "sync-humboldt-research-fellowship": {
            "task": "app.tasks.opportunity_sync.sync_humboldt_research_fellowship",
            "schedule": crontab(minute=0, hour=15),
        },
        "sync-max-planck-schools": {
            "task": "app.tasks.opportunity_sync.sync_max_planck_schools",
            "schedule": crontab(minute=15, hour=15),
        },
        "sync-tudelft-van-effen-scholarship": {
            "task": "app.tasks.opportunity_sync.sync_tudelft_van_effen_scholarship",
            "schedule": crontab(minute=30, hour=15),
        },
        "sync-tum-international-student-scholarship": {
            "task": (
                "app.tasks.opportunity_sync.sync_tum_international_student_scholarship"
            ),
            "schedule": crontab(minute=45, hour=15),
        },
        "sync-imperial-inspires-scholarship": {
            "task": "app.tasks.opportunity_sync.sync_imperial_inspires_scholarship",
            "schedule": crontab(minute=0, hour=16),
        },
        "sync-newcastle-vc-international-scholarship": {
            "task": (
                "app.tasks.opportunity_sync.sync_newcastle_vc_international_scholarship"
            ),
            "schedule": crontab(minute=15, hour=16),
        },
        "sync-sheffield-pg-scholarship": {
            "task": "app.tasks.opportunity_sync.sync_sheffield_pg_scholarship",
            "schedule": crontab(minute=30, hour=16),
        },
        "sync-manchester-global-futures-scholarship": {
            "task": (
                "app.tasks.opportunity_sync.sync_manchester_global_futures_scholarship"
            ),
            "schedule": crontab(minute=45, hour=16),
        },
        "sync-nottingham-pg-scholarship": {
            "task": "app.tasks.opportunity_sync.sync_nottingham_pg_scholarship",
            "schedule": crontab(minute=0, hour=17),
        },
        "sync-southampton-presidential-bursaries": {
            "task": (
                "app.tasks.opportunity_sync.sync_southampton_presidential_bursaries"
            ),
            "schedule": crontab(minute=15, hour=17),
        },
        "sync-southampton-merit-undergraduate-scholarship": {
            "task": (
                "app.tasks.opportunity_sync."
                "sync_southampton_merit_undergraduate_scholarship"
            ),
            "schedule": crontab(minute=30, hour=17),
        },
        "sync-durham-inspiring-excellence-undergraduate-scholarship": {
            "task": (
                "app.tasks.opportunity_sync."
                "sync_durham_inspiring_excellence_undergraduate_scholarship"
            ),
            "schedule": crontab(minute=45, hour=17),
        },
        "sync-durham-inspiring-excellence-postgraduate-scholarship": {
            "task": (
                "app.tasks.opportunity_sync."
                "sync_durham_inspiring_excellence_postgraduate_scholarship"
            ),
            "schedule": crontab(minute=0, hour=18),
        },
        "sync-freiburg-deutschlandstipendium": {
            "task": "app.tasks.opportunity_sync.sync_freiburg_deutschlandstipendium",
            "schedule": crontab(minute=15, hour=18),
        },
        "retry-failed-external-records": {
            "task": "app.tasks.opportunity_sync.retry_failed_records",
            "schedule": crontab(minute=10, hour="*/2"),
        },
        "detect-expired-opportunities": {
            "task": "app.tasks.opportunity_sync.detect_expired_opportunities",
            "schedule": crontab(minute=5, hour=1),
        },
        "check-link-health": {
            "task": "app.tasks.opportunity_sync.check_link_health",
            "schedule": crontab(minute=45, hour=1),
        },
        "schedule-reverification": {
            "task": "app.tasks.opportunity_sync.schedule_reverification",
            "schedule": crontab(minute=15, hour=2),
        },
        "send-reverification-reminders": {
            "task": "app.tasks.opportunity_sync.send_reverification_reminders",
            "schedule": crontab(minute=30, hour=8, day_of_week="1-5"),
        },
        "process-due-notifications": {
            "task": "app.tasks.notifications.process_due_notifications",
            "schedule": crontab(minute="*/5"),
        },
        "retry-failed-notifications": {
            "task": "app.tasks.notifications.retry_failed_notifications",
            "schedule": crontab(minute=20, hour="*/2"),
        },
    },
)

T = TypeVar("T")
TEMPORARY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
SOURCE_TASK_NAMES = {
    "grants_gov": "app.tasks.opportunity_sync.sync_grants_gov",
    "grants_gov_individual": "app.tasks.opportunity_sync.sync_grants_gov_individual",
    "simpler_grants": "app.tasks.opportunity_sync.sync_simpler_grants",
    "eu_funding_tenders": "app.tasks.opportunity_sync.sync_eu_funding",
    "usajobs": "app.tasks.opportunity_sync.sync_usajobs",
    "reliefweb_jobs": "app.tasks.opportunity_sync.sync_reliefweb_jobs",
    "reliefweb_training": "app.tasks.opportunity_sync.sync_reliefweb_training",
    "cscuk_scholarships": "app.tasks.opportunity_sync.sync_cscuk_scholarships",
    "chevening": "app.tasks.opportunity_sync.sync_chevening",
    "daad_scholarships": "app.tasks.opportunity_sync.sync_daad_scholarships",
    "china_embassy_sl": "app.tasks.opportunity_sync.sync_china_embassy_sl",
    "mthe_sierra_leone": "app.tasks.opportunity_sync.sync_mthe_sierra_leone",
    "wmi_scholars": "app.tasks.opportunity_sync.sync_wmi_scholars",
    "turkiye_burslari": "app.tasks.opportunity_sync.sync_turkiye_burslari",
    "ireland_goi_ies": "app.tasks.opportunity_sync.sync_ireland_goi_ies",
    "india_iccr": "app.tasks.opportunity_sync.sync_india_iccr",
    "sweden_si_scholarship": "app.tasks.opportunity_sync.sync_sweden_si_scholarship",
    "eswatini_slas": "app.tasks.opportunity_sync.sync_eswatini_slas",
    "italy_maeci_scholarships": "app.tasks.opportunity_sync.sync_italy_maeci_scholarships",
    "greece_iky_scholarships": "app.tasks.opportunity_sync.sync_greece_iky_scholarships",
    "south_africa_nrf": "app.tasks.opportunity_sync.sync_south_africa_nrf",
    "netherlands_nuffic": "app.tasks.opportunity_sync.sync_netherlands_nuffic",
    "spain_aecid": "app.tasks.opportunity_sync.sync_spain_aecid",
    "australia_dfat_awards": "app.tasks.opportunity_sync.sync_australia_dfat_awards",
    "japan_mext": "app.tasks.opportunity_sync.sync_japan_mext",
    "belgium_ares": "app.tasks.opportunity_sync.sync_belgium_ares",
    "france_eiffel": "app.tasks.opportunity_sync.sync_france_eiffel",
    "austria_oead": "app.tasks.opportunity_sync.sync_austria_oead",
    "morocco_amci": "app.tasks.opportunity_sync.sync_morocco_amci",
    "portugal_camoes": "app.tasks.opportunity_sync.sync_portugal_camoes",
    "colombia_icetex": "app.tasks.opportunity_sync.sync_colombia_icetex",
    "chile_agcid": "app.tasks.opportunity_sync.sync_chile_agcid",
    "peru_pronabec": "app.tasks.opportunity_sync.sync_peru_pronabec",
    "south_korea_gks": "app.tasks.opportunity_sync.sync_south_korea_gks",
    "saudi_arabia_moe": "app.tasks.opportunity_sync.sync_saudi_arabia_moe",
    "qatar_scholarships": "app.tasks.opportunity_sync.sync_qatar_scholarships",
    "switzerland_sbfi_eskas": "app.tasks.opportunity_sync.sync_switzerland_sbfi_eskas",
    "poland_nawa_myfirstchoice": (
        "app.tasks.opportunity_sync.sync_poland_nawa_myfirstchoice"
    ),
    "czech_republic_msmt": "app.tasks.opportunity_sync.sync_czech_republic_msmt",
    "serbia_world_in_serbia": (
        "app.tasks.opportunity_sync.sync_serbia_world_in_serbia"
    ),
    "romania_mfa": "app.tasks.opportunity_sync.sync_romania_mfa",
    "hungary_stipendium_hungaricum": (
        "app.tasks.opportunity_sync.sync_hungary_stipendium_hungaricum"
    ),
    "mexico_amexcid": "app.tasks.opportunity_sync.sync_mexico_amexcid",
    "educationusa_financial_aid": (
        "app.tasks.opportunity_sync.sync_educationusa_financial_aid"
    ),
    "world_bank_jjwbgsp": "app.tasks.opportunity_sync.sync_world_bank_jjwbgsp",
    "rotary_peace_fellowship": (
        "app.tasks.opportunity_sync.sync_rotary_peace_fellowship"
    ),
    "erasmus_mundus_joint_masters": (
        "app.tasks.opportunity_sync.sync_erasmus_mundus_joint_masters"
    ),
    "uaeu_scholarships": "app.tasks.opportunity_sync.sync_uaeu_scholarships",
    "mastercard_foundation_scholars": (
        "app.tasks.opportunity_sync.sync_mastercard_foundation_scholars"
    ),
    "schwarzman_scholars": "app.tasks.opportunity_sync.sync_schwarzman_scholars",
    "knight_hennessy_scholars": (
        "app.tasks.opportunity_sync.sync_knight_hennessy_scholars"
    ),
    "yenching_academy_scholars": (
        "app.tasks.opportunity_sync.sync_yenching_academy_scholars"
    ),
    "eth_zurich_esop": "app.tasks.opportunity_sync.sync_eth_zurich_esop",
    "hkpfs": "app.tasks.opportunity_sync.sync_hkpfs",
    "taiwan_icdf_scholarship": (
        "app.tasks.opportunity_sync.sync_taiwan_icdf_scholarship"
    ),
    "humboldt_research_fellowship": (
        "app.tasks.opportunity_sync.sync_humboldt_research_fellowship"
    ),
    "max_planck_schools": "app.tasks.opportunity_sync.sync_max_planck_schools",
    "tudelft_van_effen_scholarship": (
        "app.tasks.opportunity_sync.sync_tudelft_van_effen_scholarship"
    ),
    "tum_international_student_scholarship": (
        "app.tasks.opportunity_sync.sync_tum_international_student_scholarship"
    ),
    "imperial_inspires_scholarship": (
        "app.tasks.opportunity_sync.sync_imperial_inspires_scholarship"
    ),
    "newcastle_vc_international_scholarship": (
        "app.tasks.opportunity_sync.sync_newcastle_vc_international_scholarship"
    ),
    "sheffield_pg_scholarship": (
        "app.tasks.opportunity_sync.sync_sheffield_pg_scholarship"
    ),
    "manchester_global_futures_scholarship": (
        "app.tasks.opportunity_sync.sync_manchester_global_futures_scholarship"
    ),
    "nottingham_pg_scholarship": (
        "app.tasks.opportunity_sync.sync_nottingham_pg_scholarship"
    ),
    "southampton_presidential_bursaries": (
        "app.tasks.opportunity_sync.sync_southampton_presidential_bursaries"
    ),
    "southampton_merit_undergraduate_scholarship": (
        "app.tasks.opportunity_sync.sync_southampton_merit_undergraduate_scholarship"
    ),
    "durham_inspiring_excellence_undergraduate_scholarship": (
        "app.tasks.opportunity_sync."
        "sync_durham_inspiring_excellence_undergraduate_scholarship"
    ),
    "durham_inspiring_excellence_postgraduate_scholarship": (
        "app.tasks.opportunity_sync."
        "sync_durham_inspiring_excellence_postgraduate_scholarship"
    ),
    "freiburg_deutschlandstipendium": (
        "app.tasks.opportunity_sync.sync_freiburg_deutschlandstipendium"
    ),
}


def run_async_safely(awaitable: Coroutine[Any, Any, T]) -> T:
    """Run async persistence from a synchronous worker, even in eager async tests."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, awaitable).result()


def queue_source_sync(
    source_code: str,
    *,
    task_id: str,
    correlation_id: str,
    triggered_by: str,
) -> None:
    task_name = SOURCE_TASK_NAMES[source_code]
    celery_app.send_task(
        task_name,
        kwargs={
            "correlation_id": correlation_id,
            "triggered_by": triggered_by,
        },
        task_id=task_id,
    )


def _execute_source_task(
    task: Any,
    source_code: str,
    correlation_id: str | None,
    triggered_by: str | None,
) -> dict[str, Any]:
    task_id = task.request.id or str(uuid4())
    correlation = correlation_id or str(uuid4())
    try:
        return run_async_safely(
            _run_source_sync(
                source_code,
                task_id=task_id,
                correlation_id=correlation,
                triggered_by=triggered_by,
            )
        )
    except ExternalAPIError as error:
        temporary = error.status_code in TEMPORARY_STATUS_CODES or error.status_code is None
        event = "rate_limited" if error.status_code == 429 else "timeout_or_transport_failure"
        logger.warning(
            "%s source_code=%s task_id=%s correlation_id=%s",
            event,
            source_code,
            task_id,
            correlation,
        )
        if temporary and task.request.retries < task.max_retries:
            run_async_safely(_mark_retry(task_id, source_code, error))
            logger.warning(
                "sync_retry source_code=%s task_id=%s correlation_id=%s",
                source_code,
                task_id,
                correlation,
            )
            raise task.retry(exc=error, countdown=min(60 * 2**task.request.retries, 900))
        run_async_safely(_mark_failed(task_id, source_code, error))
        raise
    except Exception as error:
        run_async_safely(_mark_failed(task_id, source_code, error))
        raise


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_grants_gov",
    max_retries=3,
)
def sync_grants_gov(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "grants_gov", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_grants_gov_individual",
    max_retries=3,
)
def sync_grants_gov_individual(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "grants_gov_individual", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_simpler_grants",
    max_retries=3,
)
def sync_simpler_grants(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "simpler_grants", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_eu_funding",
    max_retries=3,
)
def sync_eu_funding(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "eu_funding_tenders", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_usajobs",
    max_retries=3,
)
def sync_usajobs(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "usajobs", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_reliefweb_jobs",
    max_retries=3,
)
def sync_reliefweb_jobs(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "reliefweb_jobs", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_reliefweb_training",
    max_retries=3,
)
def sync_reliefweb_training(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "reliefweb_training", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_cscuk_scholarships",
    max_retries=3,
)
def sync_cscuk_scholarships(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "cscuk_scholarships", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_chevening",
    max_retries=3,
)
def sync_chevening(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "chevening", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_daad_scholarships",
    max_retries=3,
)
def sync_daad_scholarships(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "daad_scholarships", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_china_embassy_sl",
    max_retries=3,
)
def sync_china_embassy_sl(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "china_embassy_sl", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_mthe_sierra_leone",
    max_retries=3,
)
def sync_mthe_sierra_leone(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "mthe_sierra_leone", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_wmi_scholars",
    max_retries=3,
)
def sync_wmi_scholars(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "wmi_scholars", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_turkiye_burslari",
    max_retries=3,
)
def sync_turkiye_burslari(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "turkiye_burslari", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_ireland_goi_ies",
    max_retries=3,
)
def sync_ireland_goi_ies(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "ireland_goi_ies", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_india_iccr",
    max_retries=3,
)
def sync_india_iccr(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "india_iccr", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_sweden_si_scholarship",
    max_retries=3,
)
def sync_sweden_si_scholarship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "sweden_si_scholarship", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_eswatini_slas",
    max_retries=3,
)
def sync_eswatini_slas(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "eswatini_slas", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_italy_maeci_scholarships",
    max_retries=3,
)
def sync_italy_maeci_scholarships(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "italy_maeci_scholarships", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_greece_iky_scholarships",
    max_retries=3,
)
def sync_greece_iky_scholarships(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "greece_iky_scholarships", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_south_africa_nrf",
    max_retries=3,
)
def sync_south_africa_nrf(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "south_africa_nrf", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_netherlands_nuffic",
    max_retries=3,
)
def sync_netherlands_nuffic(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "netherlands_nuffic", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_spain_aecid",
    max_retries=3,
)
def sync_spain_aecid(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "spain_aecid", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_australia_dfat_awards",
    max_retries=3,
)
def sync_australia_dfat_awards(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "australia_dfat_awards", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_japan_mext",
    max_retries=3,
)
def sync_japan_mext(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "japan_mext", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_belgium_ares",
    max_retries=3,
)
def sync_belgium_ares(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "belgium_ares", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_france_eiffel",
    max_retries=3,
)
def sync_france_eiffel(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "france_eiffel", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_austria_oead",
    max_retries=3,
)
def sync_austria_oead(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "austria_oead", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_morocco_amci",
    max_retries=3,
)
def sync_morocco_amci(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "morocco_amci", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_portugal_camoes",
    max_retries=3,
)
def sync_portugal_camoes(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "portugal_camoes", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_colombia_icetex",
    max_retries=3,
)
def sync_colombia_icetex(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "colombia_icetex", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_chile_agcid",
    max_retries=3,
)
def sync_chile_agcid(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "chile_agcid", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_peru_pronabec",
    max_retries=3,
)
def sync_peru_pronabec(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "peru_pronabec", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_south_korea_gks",
    max_retries=3,
)
def sync_south_korea_gks(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "south_korea_gks", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_saudi_arabia_moe",
    max_retries=3,
)
def sync_saudi_arabia_moe(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "saudi_arabia_moe", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_qatar_scholarships",
    max_retries=3,
)
def sync_qatar_scholarships(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "qatar_scholarships", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_switzerland_sbfi_eskas",
    max_retries=3,
)
def sync_switzerland_sbfi_eskas(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "switzerland_sbfi_eskas", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_poland_nawa_myfirstchoice",
    max_retries=3,
)
def sync_poland_nawa_myfirstchoice(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "poland_nawa_myfirstchoice", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_czech_republic_msmt",
    max_retries=3,
)
def sync_czech_republic_msmt(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "czech_republic_msmt", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_serbia_world_in_serbia",
    max_retries=3,
)
def sync_serbia_world_in_serbia(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "serbia_world_in_serbia", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_romania_mfa",
    max_retries=3,
)
def sync_romania_mfa(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "romania_mfa", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_hungary_stipendium_hungaricum",
    max_retries=3,
)
def sync_hungary_stipendium_hungaricum(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "hungary_stipendium_hungaricum", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_mexico_amexcid",
    max_retries=3,
)
def sync_mexico_amexcid(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "mexico_amexcid", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_educationusa_financial_aid",
    max_retries=3,
)
def sync_educationusa_financial_aid(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "educationusa_financial_aid", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_world_bank_jjwbgsp",
    max_retries=3,
)
def sync_world_bank_jjwbgsp(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "world_bank_jjwbgsp", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_rotary_peace_fellowship",
    max_retries=3,
)
def sync_rotary_peace_fellowship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "rotary_peace_fellowship", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_erasmus_mundus_joint_masters",
    max_retries=3,
)
def sync_erasmus_mundus_joint_masters(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "erasmus_mundus_joint_masters", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_uaeu_scholarships",
    max_retries=3,
)
def sync_uaeu_scholarships(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "uaeu_scholarships", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_mastercard_foundation_scholars",
    max_retries=3,
)
def sync_mastercard_foundation_scholars(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "mastercard_foundation_scholars", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_schwarzman_scholars",
    max_retries=3,
)
def sync_schwarzman_scholars(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "schwarzman_scholars", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_knight_hennessy_scholars",
    max_retries=3,
)
def sync_knight_hennessy_scholars(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "knight_hennessy_scholars", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_yenching_academy_scholars",
    max_retries=3,
)
def sync_yenching_academy_scholars(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "yenching_academy_scholars", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_eth_zurich_esop",
    max_retries=3,
)
def sync_eth_zurich_esop(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "eth_zurich_esop", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_hkpfs",
    max_retries=3,
)
def sync_hkpfs(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "hkpfs", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_taiwan_icdf_scholarship",
    max_retries=3,
)
def sync_taiwan_icdf_scholarship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "taiwan_icdf_scholarship", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_humboldt_research_fellowship",
    max_retries=3,
)
def sync_humboldt_research_fellowship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "humboldt_research_fellowship", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_max_planck_schools",
    max_retries=3,
)
def sync_max_planck_schools(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(self, "max_planck_schools", correlation_id, triggered_by)


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_tudelft_van_effen_scholarship",
    max_retries=3,
)
def sync_tudelft_van_effen_scholarship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "tudelft_van_effen_scholarship", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_tum_international_student_scholarship",
    max_retries=3,
)
def sync_tum_international_student_scholarship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "tum_international_student_scholarship", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_imperial_inspires_scholarship",
    max_retries=3,
)
def sync_imperial_inspires_scholarship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "imperial_inspires_scholarship", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_newcastle_vc_international_scholarship",
    max_retries=3,
)
def sync_newcastle_vc_international_scholarship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "newcastle_vc_international_scholarship", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_sheffield_pg_scholarship",
    max_retries=3,
)
def sync_sheffield_pg_scholarship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "sheffield_pg_scholarship", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_manchester_global_futures_scholarship",
    max_retries=3,
)
def sync_manchester_global_futures_scholarship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "manchester_global_futures_scholarship", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_nottingham_pg_scholarship",
    max_retries=3,
)
def sync_nottingham_pg_scholarship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "nottingham_pg_scholarship", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_southampton_presidential_bursaries",
    max_retries=3,
)
def sync_southampton_presidential_bursaries(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "southampton_presidential_bursaries", correlation_id, triggered_by
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_southampton_merit_undergraduate_scholarship",
    max_retries=3,
)
def sync_southampton_merit_undergraduate_scholarship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self,
        "southampton_merit_undergraduate_scholarship",
        correlation_id,
        triggered_by,
    )


@celery_app.task(
    bind=True,
    name=(
        "app.tasks.opportunity_sync."
        "sync_durham_inspiring_excellence_undergraduate_scholarship"
    ),
    max_retries=3,
)
def sync_durham_inspiring_excellence_undergraduate_scholarship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self,
        "durham_inspiring_excellence_undergraduate_scholarship",
        correlation_id,
        triggered_by,
    )


@celery_app.task(
    bind=True,
    name=(
        "app.tasks.opportunity_sync."
        "sync_durham_inspiring_excellence_postgraduate_scholarship"
    ),
    max_retries=3,
)
def sync_durham_inspiring_excellence_postgraduate_scholarship(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self,
        "durham_inspiring_excellence_postgraduate_scholarship",
        correlation_id,
        triggered_by,
    )


@celery_app.task(
    bind=True,
    name="app.tasks.opportunity_sync.sync_freiburg_deutschlandstipendium",
    max_retries=3,
)
def sync_freiburg_deutschlandstipendium(
    self: Any,
    correlation_id: str | None = None,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    return _execute_source_task(
        self, "freiburg_deutschlandstipendium", correlation_id, triggered_by
    )


async def _run_source_sync(
    source_code: str,
    *,
    task_id: str,
    correlation_id: str,
    triggered_by: str | None,
) -> dict[str, Any]:
    started = monotonic()
    async with AsyncSessionFactory() as session:
        async with session.begin():
            sources = await seed_opportunity_sources(session)
            source = sources[source_code]
            history = await session.scalar(
                select(OpportunitySyncHistory).where(
                    OpportunitySyncHistory.task_id == task_id
                )
            )
            if history is None:
                history = OpportunitySyncHistory(
                    task_id=task_id,
                    source_id=source.id,
                    source_code=source_code,
                    triggered_by=triggered_by,
                    correlation_id=correlation_id,
                    started_at=utc_now(),
                    status=SyncStatus.running,
                )
                session.add(history)
            else:
                history.started_at = utc_now()
                history.status = SyncStatus.running
            source.last_sync_at = history.started_at
            if not source.is_active:
                history.status = SyncStatus.cancelled
                history.finished_at = utc_now()
                history.error_summary = "The external source is inactive."

    if not source.is_active:
        logger.info(
            "sync_cancelled source_code=%s task_id=%s correlation_id=%s "
            "record_count=0 duration=0 final_status=cancelled",
            source_code,
            task_id,
            correlation_id,
        )
        return {
            "records_received": 0,
            "records_created": 0,
            "records_updated": 0,
            "records_skipped": 0,
            "records_failed": 0,
            "duplicate_candidates": 0,
            "status": SyncStatus.cancelled.value,
        }

    logger.info(
        "sync_started source_code=%s task_id=%s correlation_id=%s",
        source_code,
        task_id,
        correlation_id,
    )
    records = await _collector(source_code).collect_for_import()
    async with AsyncSessionFactory() as session:
        statistics = await import_opportunities(
            session,
            records,
            source_code=source_code,
            actor_id=triggered_by or "celery-beat",
            correlation_id=correlation_id,
            task_id=task_id,
        )

    final_status = (
        SyncStatus.partially_completed
        if statistics.records_failed
        else SyncStatus.completed
    )
    async with AsyncSessionFactory() as session:
        async with session.begin():
            history = await session.scalar(
                select(OpportunitySyncHistory).where(
                    OpportunitySyncHistory.task_id == task_id
                )
            )
            source = await session.scalar(
                select(OpportunitySource).where(
                    OpportunitySource.source_code == source_code
                )
            )
            history.finished_at = utc_now()
            history.records_received = statistics.records_received
            history.records_created = statistics.records_created
            history.records_updated = statistics.records_updated
            history.records_skipped = statistics.records_skipped
            history.records_failed = statistics.records_failed
            history.duplicate_candidates = statistics.duplicate_candidates
            history.status = final_status
            history.error_summary = (
                f"{statistics.records_failed} record(s) failed validation or import."
                if statistics.records_failed
                else None
            )
            if final_status == SyncStatus.completed:
                source.last_successful_sync_at = history.finished_at
                source.most_recent_error = None
            else:
                source.last_failed_sync_at = history.finished_at
                source.most_recent_error = history.error_summary
            source.next_scheduled_sync = history.finished_at + timedelta(
                hours=12
                if source_code in {"eu_funding_tenders", "reliefweb_training"}
                else 6
            )
            append_audit(
                session,
                actor_id=triggered_by,
                action=(
                    "scheduled_synchronization"
                    if not triggered_by
                    else "manual_synchronization"
                ),
                entity_type="opportunity_source",
                entity_id=source.id,
                new_value={
                    "task_id": task_id,
                    "status": final_status.value,
                    **statistics.model_dump(),
                },
                correlation_id=correlation_id,
            )

    duration = monotonic() - started
    logger.info(
        "sync_%s source_code=%s task_id=%s correlation_id=%s "
        "record_count=%s duration=%.3f final_status=%s",
        final_status.value,
        source_code,
        task_id,
        correlation_id,
        statistics.records_received,
        duration,
        final_status.value,
    )
    return {**statistics.model_dump(), "status": final_status.value}


async def _mark_retry(task_id: str, source_code: str, error: Exception) -> None:
    async with AsyncSessionFactory() as session:
        async with session.begin():
            history = await session.scalar(
                select(OpportunitySyncHistory).where(
                    OpportunitySyncHistory.task_id == task_id
                )
            )
            if history:
                history.status = SyncStatus.queued
                history.error_summary = _safe_error(error)


async def _mark_failed(task_id: str, source_code: str, error: Exception) -> None:
    now = utc_now()
    summary = _safe_error(error)
    correlation_id = "unknown"
    duration = 0.0
    async with AsyncSessionFactory() as session:
        async with session.begin():
            history = await session.scalar(
                select(OpportunitySyncHistory).where(
                    OpportunitySyncHistory.task_id == task_id
                )
            )
            source = await session.scalar(
                select(OpportunitySource).where(
                    OpportunitySource.source_code == source_code
                )
            )
            if history:
                history.status = SyncStatus.failed
                history.finished_at = now
                history.error_summary = summary
                correlation_id = history.correlation_id
                started_at = history.started_at
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=UTC)
                duration = max((now - started_at).total_seconds(), 0.0)
            if source:
                source.last_failed_sync_at = now
                source.most_recent_error = summary
    logger.error(
        "sync_failed source_code=%s task_id=%s correlation_id=%s "
        "record_count=0 duration=%.3f final_status=failed",
        source_code,
        task_id,
        correlation_id,
        duration,
    )


def _collector(source_code: str) -> Any:
    return {
        "grants_gov": GrantsGovSource,
        "grants_gov_individual": GrantsGovIndividualSource,
        "simpler_grants": SimplerGrantsSource,
        "eu_funding_tenders": EUFundingSource,
        "usajobs": UsaJobsSource,
        "reliefweb_jobs": ReliefWebJobsSource,
        "reliefweb_training": ReliefWebTrainingSource,
        "cscuk_scholarships": CscukScholarshipsSource,
        "chevening": CheveningSource,
        "daad_scholarships": DaadScholarshipsSource,
        "china_embassy_sl": ChinaEmbassySierraLeoneSource,
        "mthe_sierra_leone": SierraLeoneMTHESource,
        "wmi_scholars": WellsMountainInitiativeSource,
        "turkiye_burslari": TurkiyeBurslariSource,
        "ireland_goi_ies": IrelandGoiIesSource,
        "india_iccr": IndiaIccrSource,
        "sweden_si_scholarship": SwedishInstituteScholarshipSource,
        "eswatini_slas": EswatiniSlasSource,
        "italy_maeci_scholarships": ItalyMaeciScholarshipSource,
        "greece_iky_scholarships": GreeceIkyScholarshipSource,
        "south_africa_nrf": SouthAfricaNrfScholarshipSource,
        "netherlands_nuffic": NetherlandsNufficScholarshipSource,
        "spain_aecid": SpainAecidScholarshipSource,
        "australia_dfat_awards": AustraliaDfatAwardsSource,
        "japan_mext": JapanMextScholarshipSource,
        "belgium_ares": BelgiumAresScholarshipSource,
        "france_eiffel": FranceEiffelScholarshipSource,
        "austria_oead": AustriaOeadErnstMachSource,
        "morocco_amci": MoroccoAmciScholarshipSource,
        "portugal_camoes": PortugalCamoesScholarshipSource,
        "colombia_icetex": ColombiaIcetexBecaExtranjerosSource,
        "chile_agcid": ChileAgcidScholarshipSource,
        "peru_pronabec": PeruPronabecAlianzaPacificoSource,
        "south_korea_gks": SouthKoreaGksScholarshipSource,
        "saudi_arabia_moe": SaudiArabiaMoeScholarshipSource,
        "qatar_scholarships": QatarScholarshipsSource,
        "switzerland_sbfi_eskas": SwitzerlandEskasScholarshipSource,
        "poland_nawa_myfirstchoice": PolandNawaMyFirstChoiceSource,
        "czech_republic_msmt": CzechRepublicMsmtScholarshipSource,
        "serbia_world_in_serbia": SerbiaWorldInSerbiaScholarshipSource,
        "romania_mfa": RomaniaMfaScholarshipSource,
        "hungary_stipendium_hungaricum": HungaryStipendiumHungaricumSource,
        "mexico_amexcid": MexicoAmexcidScholarshipSource,
        "educationusa_financial_aid": EducationUsaFinancialAidSource,
        "world_bank_jjwbgsp": WorldBankJJWBGSPScholarshipSource,
        "rotary_peace_fellowship": RotaryPeaceFellowshipSource,
        "erasmus_mundus_joint_masters": ErasmusMundusJointMastersSource,
        "uaeu_scholarships": UaeuScholarshipsSource,
        "mastercard_foundation_scholars": MastercardFoundationScholarsSource,
        "schwarzman_scholars": SchwarzmanScholarsSource,
        "knight_hennessy_scholars": KnightHennessyScholarsSource,
        "yenching_academy_scholars": YenchingAcademyScholarsSource,
        "eth_zurich_esop": EthZurichExcellenceScholarshipSource,
        "hkpfs": HongKongPhdFellowshipSchemeSource,
        "taiwan_icdf_scholarship": TaiwanIcdfScholarshipSource,
        "humboldt_research_fellowship": HumboldtResearchFellowshipSource,
        "max_planck_schools": MaxPlanckSchoolsSource,
        "tudelft_van_effen_scholarship": TuDelftVanEffenScholarshipSource,
        "tum_international_student_scholarship": (
            TumInternationalStudentScholarshipSource
        ),
        "imperial_inspires_scholarship": ImperialInspiresScholarshipSource,
        "newcastle_vc_international_scholarship": (
            NewcastleVcInternationalScholarshipSource
        ),
        "sheffield_pg_scholarship": SheffieldPgScholarshipSource,
        "manchester_global_futures_scholarship": (
            ManchesterGlobalFuturesScholarshipSource
        ),
        "nottingham_pg_scholarship": NottinghamPgScholarshipSource,
        "southampton_presidential_bursaries": SouthamptonPresidentialBursariesSource,
        "southampton_merit_undergraduate_scholarship": (
            SouthamptonMeritUndergraduateScholarshipSource
        ),
        "durham_inspiring_excellence_undergraduate_scholarship": (
            DurhamInspiringExcellenceUndergraduateScholarshipSource
        ),
        "durham_inspiring_excellence_postgraduate_scholarship": (
            DurhamInspiringExcellencePostgraduateScholarshipSource
        ),
        "freiburg_deutschlandstipendium": FreiburgDeutschlandstipendiumSource,
    }[source_code]()


def _safe_error(error: Exception) -> str:
    if isinstance(error, ExternalAPIError):
        return str(error)[:1000]
    return "Synchronization failed due to an internal error."


@celery_app.task(name="app.tasks.opportunity_sync.retry_failed_records")
def retry_failed_records() -> dict[str, int]:
    return run_async_safely(_retry_failed_records())


async def _retry_failed_records() -> dict[str, int]:
    retried = 0
    async with AsyncSessionFactory() as session:
        failed = (
            await session.scalars(
                select(RawExternalOpportunity).where(
                    RawExternalOpportunity.processing_status == ProcessingStatus.failed
                )
            )
        ).all()
        for raw in failed:
            source = await session.get(OpportunitySource, raw.source_id)
            try:
                normalized = _collector(source.source_code)._normalize(raw.raw_payload)
            except Exception:
                continue
            raw.payload_hash = ""
            await session.commit()
            await import_opportunities(
                session,
                [normalized],
                source_code=source.source_code,
                actor_id="failed-record-retry",
            )
            retried += 1
    return {"retried": retried}


@celery_app.task(name="app.tasks.opportunity_sync.detect_expired_opportunities")
def detect_expired_opportunities() -> dict[str, int]:
    return run_async_safely(_detect_expired_opportunities())


async def _detect_expired_opportunities() -> dict[str, int]:
    changed = 0
    today = utc_now().date()
    async with AsyncSessionFactory() as session:
        async with session.begin():
            opportunities = (
                await session.scalars(
                    select(ExternalOpportunity).where(
                        ExternalOpportunity.deadline < today,
                        ExternalOpportunity.verification_status
                        != VerificationStatus.expired,
                    )
                )
            ).all()
            for opportunity in opportunities:
                previous = opportunity.verification_status.value
                opportunity.verification_status = VerificationStatus.expired
                opportunity.publication_status = PublicationStatus.archived
                session.add(
                    VerificationHistory(
                        opportunity_id=opportunity.id,
                        previous_status=previous,
                        new_status=VerificationStatus.expired.value,
                        reason="Opportunity deadline has passed.",
                    )
                )
                changed += 1
    return {"expired": changed}


LINK_HEALTH_BATCH_SIZE = 100


@celery_app.task(name="app.tasks.opportunity_sync.check_link_health")
def check_link_health() -> dict[str, int]:
    return run_async_safely(_check_link_health())


async def _check_link_health() -> dict[str, int]:
    """Periodically confirm published opportunities' links are still live.

    Scoped to verified+published opportunities: those are the only ones a
    real applicant can currently reach, so they're the only ones where a
    broken link is actionable right now. Bounded to
    LINK_HEALTH_BATCH_SIZE per run, oldest-checked (nulls - never checked -
    first) so one run can't grow unbounded as the catalog grows; the next
    scheduled run picks up where this one left off.

    A reachable response only proves the URL still resolves, not that it
    still points at the right page - see link_checked_at's docstring. An
    unreachable one demotes verification_status back to
    reverification_required (this codebase's existing "needs another look"
    state - see schedule_reverification above) and logs a
    VerificationHistory entry, exactly like a passed deadline does in
    detect_expired_opportunities. It never deletes the opportunity or its
    stored link.
    """
    checked = 0
    broken = 0
    async with AsyncSessionFactory() as session:
        async with session.begin():
            opportunities = (
                await session.scalars(
                    select(ExternalOpportunity)
                    .where(
                        ExternalOpportunity.verification_status == VerificationStatus.verified,
                        ExternalOpportunity.publication_status == PublicationStatus.published,
                    )
                    .order_by(ExternalOpportunity.link_checked_at.asc().nulls_first())
                    .limit(LINK_HEALTH_BATCH_SIZE)
                )
            ).all()
            for opportunity in opportunities:
                url = opportunity.official_application_url or opportunity.official_source_url
                if url is None:
                    continue
                checked += 1
                reachable = await check_link_reachable(url)
                opportunity.link_checked_at = utc_now()
                if reachable:
                    continue
                broken += 1
                opportunity.verification_status = VerificationStatus.reverification_required
                session.add(
                    VerificationHistory(
                        opportunity_id=opportunity.id,
                        previous_status=VerificationStatus.verified.value,
                        new_status=VerificationStatus.reverification_required.value,
                        reason="Routine link health check could not reach the stored "
                        "application/source URL.",
                    )
                )
                review = await session.scalar(
                    select(VerificationReview).where(
                        VerificationReview.opportunity_id == opportunity.id
                    )
                )
                if review is not None:
                    review.application_link_checked = False
    return {"checked": checked, "broken": broken}


@celery_app.task(name="app.tasks.opportunity_sync.schedule_reverification")
def schedule_reverification() -> dict[str, int]:
    return run_async_safely(_schedule_reverification())


async def _schedule_reverification() -> dict[str, int]:
    scheduled = 0
    cutoff = utc_now() - timedelta(days=90)
    async with AsyncSessionFactory() as session:
        async with session.begin():
            reviews = (
                await session.scalars(
                    select(VerificationReview).where(
                        VerificationReview.verified_at.is_not(None),
                        VerificationReview.verified_at <= cutoff,
                    )
                )
            ).all()
            for review in reviews:
                opportunity = await session.get(ExternalOpportunity, review.opportunity_id)
                if opportunity.verification_status != VerificationStatus.verified:
                    continue
                opportunity.verification_status = VerificationStatus.reverification_required
                review.decision = VerificationStatus.reverification_required.value
                session.add(
                    VerificationHistory(
                        opportunity_id=opportunity.id,
                        previous_status=VerificationStatus.verified.value,
                        new_status=VerificationStatus.reverification_required.value,
                        reason="Scheduled 90-day reverification is due.",
                    )
                )
                scheduled += 1
    return {"scheduled": scheduled}


@celery_app.task(name="app.tasks.opportunity_sync.send_reverification_reminders")
def send_reverification_reminders() -> dict[str, int]:
    return run_async_safely(_send_reverification_reminders())


async def _reverification_recipients_from_audit_log(session: AsyncSession) -> list[str]:
    """Fallback recipient source: officers with real prior decision history.

    Used only when the real Firebase roster (see
    _reverification_recipients below) cannot be retrieved - e.g. no
    Firebase credentials configured in this environment. Every id here is
    real activity (ImportAuditLog.action starting with "verification_"),
    not a fabricated roster, but it necessarily excludes any officer who
    has never yet made a decision.
    """
    actor_ids = (
        await session.scalars(
            select(ImportAuditLog.actor_id)
            .where(
                ImportAuditLog.actor_id.is_not(None),
                ImportAuditLog.action.like("verification_%"),
            )
            .distinct()
        )
    ).all()
    return [actor_id for actor_id in actor_ids if actor_id]


async def _reverification_recipients(session: AsyncSession) -> list[str]:
    """Verification officers/admins to notify.

    Primary source: the real Firebase user roster
    (app.services.firebase_users.list_reverification_recipient_uids),
    enumerated via the Admin SDK's supported list_users pagination and
    filtered by the verificationOfficer/administrator/superAdministrator
    custom claim - this reaches every current officer, including ones who
    have never made a decision, unlike the previous audit-log-only
    heuristic.

    Falls back to the audit-log heuristic (real prior decisions only) if
    Firebase enumeration fails for any reason (e.g. no credentials
    configured) - this keeps reminders flowing in a degraded but still
    honest form rather than silently sending zero, and is logged clearly
    so the degradation is visible in operations.
    """
    try:
        uids = list_reverification_recipient_uids()
        logger.info("reverification_recipients_source=firebase count=%s", len(uids))
        return uids
    except FirebaseRosterError as error:
        logger.warning(
            "reverification_recipients_firebase_unavailable error=%s "
            "falling_back_to=audit_log",
            error,
        )
        fallback = await _reverification_recipients_from_audit_log(session)
        logger.info(
            "reverification_recipients_source=audit_log_fallback count=%s",
            len(fallback),
        )
        return fallback


async def _send_reverification_reminders() -> dict[str, int]:
    async with AsyncSessionFactory() as session:
        opportunities = (
            await session.scalars(
                select(ExternalOpportunity).where(
                    ExternalOpportunity.verification_status
                    == VerificationStatus.reverification_required
                )
            )
        ).all()
        recipients = await _reverification_recipients(session)
        created = 0
        if opportunities and recipients:
            # The reads above already autobegan a transaction on this
            # session; close it out before opening the explicit one below
            # (session.begin() raises if a transaction is already open).
            await session.commit()
            async with session.begin():
                for opportunity in opportunities:
                    for officer_id in recipients:
                        notification_id = (
                            f"{opportunity.id}-reverification-officer-{officer_id}"
                        )
                        existing = await session.get(
                            ScholarSphereNotification, notification_id
                        )
                        if existing is not None:
                            # Already reminded this officer about this
                            # opportunity's current reverification cycle -
                            # never re-create it, so re-running this task
                            # (daily, per beat_schedule) can't spam.
                            continue
                        preferences = await session.get(
                            NotificationPreferences, officer_id
                        ) or default_preferences(officer_id)
                        if not wants_in_app_notification(
                            preferences, NotificationEventType.reverification_due
                        ):
                            continue
                        now = utc_now()
                        session.add(
                            ScholarSphereNotification(
                                id=notification_id,
                                user_id=officer_id,
                                type=NotificationEventType.reverification_due,
                                title=event_title(
                                    NotificationEventType.reverification_due
                                ),
                                message=(
                                    f'"{opportunity.title}" is due for '
                                    "reverification. Review it in the "
                                    "verification queue."
                                ),
                                # Only in_app is wired to real delivery today
                                # (appearing in GET /notifications is the
                                # actual delivery mechanism for that
                                # channel). email/push/sms have no configured
                                # provider in this backend yet - see
                                # Task.md/PRD.md for what's still required.
                                channels=["in_app"],
                                scheduled_for=now,
                                opportunity_id=opportunity.id,
                                related_entity_type="external_opportunity",
                                related_entity_id=str(opportunity.id),
                                status=NotificationDeliveryStatus.scheduled,
                                retry_count=0,
                                timezone="UTC",
                            )
                        )
                        created += 1
    logger.info(
        "reverification_reminders opportunities_due=%s recipients=%s "
        "reminders_created=%s",
        len(opportunities),
        len(recipients),
        created,
    )
    return {
        "opportunities_due": len(opportunities),
        "recipients": len(recipients),
        "reminders_created": created,
    }

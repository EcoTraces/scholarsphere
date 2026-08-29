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

    rate_limit_requests: int = Field(default=300, gt=0)
    rate_limit_window_seconds: int = Field(default=60, gt=0)

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
    # Confirmed unreachable from every environment this project has had
    # access to (connection timeout, both http/https - see
    # docs/AUTHORITATIVE_SOURCES.md #18), the same failure pattern as
    # mthe_sl_base_url above. Kept configured for future re-testing.
    eswatini_slas_base_url: str = "https://www.slas.gov.sz"

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
    )
    @classmethod
    def require_https(cls, value: str) -> str:
        if not value.lower().startswith("https://"):
            raise ValueError("External API endpoints must use HTTPS")
        return value.rstrip("/")

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

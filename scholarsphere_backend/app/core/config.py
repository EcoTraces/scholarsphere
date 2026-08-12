from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, SecretStr, field_validator
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
        mode="before",
    )
    @classmethod
    def split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
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
    )
    @classmethod
    def require_https(cls, value: str) -> str:
        if not value.lower().startswith("https://"):
            raise ValueError("External API endpoints must use HTTPS")
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()

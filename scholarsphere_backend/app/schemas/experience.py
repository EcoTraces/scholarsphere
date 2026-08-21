from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.experience import SupportedLanguage

_LANGUAGE_WIRE_TO_MODEL: dict[str, SupportedLanguage] = {
    "english": SupportedLanguage.english,
    "french": SupportedLanguage.french,
    "spanish": SupportedLanguage.spanish,
    "arabic": SupportedLanguage.arabic,
}
_LANGUAGE_MODEL_TO_WIRE: dict[SupportedLanguage, str] = {
    value: key for key, value in _LANGUAGE_WIRE_TO_MODEL.items()
}


def language_from_wire(value: str) -> SupportedLanguage:
    try:
        return _LANGUAGE_WIRE_TO_MODEL[value]
    except KeyError as error:
        raise ValueError(f"Unknown language: {value!r}") from error


def language_to_wire(value: SupportedLanguage) -> str:
    return _LANGUAGE_MODEL_TO_WIRE[value]


class SavePreferencesRequest(BaseModel):
    language: str = "english"
    timezone: str = Field(default="UTC", max_length=64)
    currency_code: str = Field(default="USD", max_length=8)
    country_code: str = Field(default="US", max_length=8)
    text_scale: float = Field(default=1.0, ge=1.0, le=2.0)
    high_contrast: bool = False
    screen_reader_optimized: bool = False
    keyboard_navigation: bool = True
    low_bandwidth_mode: bool = False
    compress_images: bool = True
    data_saving: bool = False
    cache_saved_opportunities: bool = True

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        language_from_wire(value)
        return value


class SaveTranslationRequest(BaseModel):
    value: str = Field(min_length=1, max_length=5000)


class ExperiencePreferencesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language: SupportedLanguage
    timezone: str
    currency_code: str
    country_code: str
    text_scale: float
    high_contrast: bool
    screen_reader_optimized: bool
    keyboard_navigation: bool
    low_bandwidth_mode: bool
    compress_images: bool
    data_saving: bool
    cache_saved_opportunities: bool

    @field_serializer("language")
    def _serialize_language(self, value: SupportedLanguage, _info: Any) -> str:
        return language_to_wire(value)


class TranslationRead(BaseModel):
    value: str

"""Provider-independent AI abstraction.

Mirrors app/services/payment_provider.py's shape and intent exactly: an
``AIProvider`` interface, a ``NullAIProvider`` default that clearly
reports "not configured" rather than fabricating generated text, and real
adapters for two providers (OpenAI, Anthropic) selected by
``AI_PROVIDER``. No calling code ever imports a specific provider's SDK -
document generation (app/services/document_generation.py) only ever
depends on this module's ``AIProvider`` protocol.

This module never decides *what* to ask the model to write - that
grounding responsibility (never inventing a fact the applicant didn't
provide) belongs entirely to document_generation.py's prompt
construction. This module's only job is "send this exact prompt to
whichever real model is configured, and return exactly what came back."
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import Settings, get_settings
from app.core.http_client import ExternalAPIError, post_json

logger = logging.getLogger(__name__)

_OPENAI_API_BASE_URL = "https://api.openai.com"
_ANTHROPIC_API_BASE_URL = "https://api.anthropic.com"
_ANTHROPIC_VERSION = "2023-06-01"


class AIProviderError(Exception):
    """A safe-to-display AI provider failure - never leaks a raw response

    body or the API key (Coding_Rules.md SS4).
    """


class AIProviderNotConfiguredError(AIProviderError):
    pass


@dataclass(frozen=True)
class AIGenerationResult:
    text: str
    provider: str
    model: str
    tokens_used: int | None = None


class AIProvider(Protocol):
    async def generate_text(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> AIGenerationResult: ...


class NullAIProvider:
    """The honest default. Raises rather than returning placeholder or

    fabricated document text - a route that hits this must surface "AI
    generation is not configured" to the caller, never silently invent
    content (see app/services/document_generation.py's own "never
    fabricate" rule, which this failure mode exists to protect).
    """

    _MESSAGE = (
        "AI generation is not configured. Set AI_PROVIDER, AI_API_KEY, and "
        "AI_MODEL in the environment before requesting AI-assisted content."
    )

    async def generate_text(self, **_: Any) -> AIGenerationResult:
        raise AIProviderNotConfiguredError(self._MESSAGE)


class OpenAIProvider:
    """A real integration against OpenAI's documented Chat Completions API."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.ai_api_key.get_secret_value()
        self._model = settings.ai_model
        self._base_url = settings.ai_api_base_url or _OPENAI_API_BASE_URL
        self._timeout_seconds = settings.ai_request_timeout_seconds

    async def generate_text(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> AIGenerationResult:
        if not self._api_key or not self._model:
            raise AIProviderNotConfiguredError(
                "AI_PROVIDER=openai is set but AI_API_KEY or AI_MODEL is empty."
            )
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.4,
        }
        try:
            payload = await post_json(
                f"{self._base_url}/v1/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout_seconds=self._timeout_seconds,
            )
        except ExternalAPIError as error:
            raise AIProviderError("The AI provider rejected the generation request.") from error
        choices = payload.get("choices") or []
        if not choices:
            raise AIProviderError("The AI provider returned no generated content.")
        text = str(choices[0].get("message", {}).get("content", ""))
        usage = payload.get("usage") or {}
        return AIGenerationResult(
            text=text,
            provider="openai",
            model=self._model,
            tokens_used=usage.get("total_tokens"),
        )


class AnthropicProvider:
    """A real integration against Anthropic's documented Messages API."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.ai_api_key.get_secret_value()
        self._model = settings.ai_model
        self._base_url = settings.ai_api_base_url or _ANTHROPIC_API_BASE_URL
        self._timeout_seconds = settings.ai_request_timeout_seconds

    async def generate_text(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int
    ) -> AIGenerationResult:
        if not self._api_key or not self._model:
            raise AIProviderNotConfiguredError(
                "AI_PROVIDER=anthropic is set but AI_API_KEY or AI_MODEL is empty."
            )
        body = {
            "model": self._model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": max_tokens,
        }
        try:
            payload = await post_json(
                f"{self._base_url}/v1/messages",
                json=body,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": _ANTHROPIC_VERSION,
                },
                timeout_seconds=self._timeout_seconds,
            )
        except ExternalAPIError as error:
            raise AIProviderError("The AI provider rejected the generation request.") from error
        content = payload.get("content") or []
        if not content:
            raise AIProviderError("The AI provider returned no generated content.")
        text = str(content[0].get("text", ""))
        usage = payload.get("usage") or {}
        tokens_used = None
        if "input_tokens" in usage and "output_tokens" in usage:
            tokens_used = int(usage["input_tokens"]) + int(usage["output_tokens"])
        return AIGenerationResult(
            text=text, provider="anthropic", model=self._model, tokens_used=tokens_used
        )


PROVIDER_REGISTRY: dict[str, type[OpenAIProvider] | type[AnthropicProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def get_ai_provider(settings: Settings | None = None) -> AIProvider:
    settings = settings or get_settings()
    provider_code = settings.ai_provider.strip().lower()
    if not provider_code:
        return NullAIProvider()
    provider_class = PROVIDER_REGISTRY.get(provider_code)
    if provider_class is None:
        logger.warning("unknown_ai_provider provider=%s", provider_code)
        return NullAIProvider()
    return provider_class(settings)

"""Unit tests for app/services/ai_provider.py - verifies each real adapter

builds the request shape its provider's actual documented API expects,
and that the Null default never fabricates generated text.
"""

import pytest

from app.core.config import Settings
from app.services import ai_provider as ai_provider_module
from app.services.ai_provider import (
    AnthropicProvider,
    NullAIProvider,
    OpenAIProvider,
    AIProviderError,
    AIProviderNotConfiguredError,
    get_ai_provider,
)


@pytest.mark.asyncio
async def test_null_provider_always_raises_not_configured() -> None:
    provider = NullAIProvider()
    with pytest.raises(AIProviderNotConfiguredError):
        await provider.generate_text(system_prompt="s", user_prompt="u", max_tokens=100)


def test_get_ai_provider_defaults_to_null_when_unset() -> None:
    settings = Settings(ai_provider="")
    assert isinstance(get_ai_provider(settings), NullAIProvider)


def test_get_ai_provider_falls_back_to_null_for_unknown_name() -> None:
    settings = Settings(ai_provider="some_unsupported_provider")
    assert isinstance(get_ai_provider(settings), NullAIProvider)


@pytest.mark.asyncio
async def test_openai_provider_sends_chat_completions_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    async def fake_post_json(url, *, json=None, headers=None, timeout_seconds=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return {
            "choices": [{"message": {"content": "Generated text."}}],
            "usage": {"total_tokens": 55},
        }

    monkeypatch.setattr(ai_provider_module, "post_json", fake_post_json)
    settings = Settings(ai_provider="openai", ai_api_key="sk-test", ai_model="gpt-test")
    provider = OpenAIProvider(settings)

    result = await provider.generate_text(
        system_prompt="You are a helpful assistant.", user_prompt="Write a CV summary.", max_tokens=200
    )

    assert result.text == "Generated text."
    assert result.provider == "openai"
    assert result.tokens_used == 55
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["json"]["model"] == "gpt-test"
    assert captured["json"]["messages"][0] == {
        "role": "system",
        "content": "You are a helpful assistant.",
    }
    assert captured["json"]["messages"][1] == {"role": "user", "content": "Write a CV summary."}


@pytest.mark.asyncio
async def test_openai_provider_without_api_key_raises_not_configured() -> None:
    settings = Settings(ai_provider="openai", ai_api_key="", ai_model="gpt-test")
    provider = OpenAIProvider(settings)
    with pytest.raises(AIProviderNotConfiguredError):
        await provider.generate_text(system_prompt="s", user_prompt="u", max_tokens=100)


@pytest.mark.asyncio
async def test_anthropic_provider_sends_messages_api_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    async def fake_post_json(url, *, json=None, headers=None, timeout_seconds=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return {
            "content": [{"type": "text", "text": "Generated text."}],
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

    monkeypatch.setattr(ai_provider_module, "post_json", fake_post_json)
    settings = Settings(ai_provider="anthropic", ai_api_key="sk-ant-test", ai_model="claude-test")
    provider = AnthropicProvider(settings)

    result = await provider.generate_text(
        system_prompt="You are a helpful assistant.", user_prompt="Write a CV summary.", max_tokens=200
    )

    assert result.text == "Generated text."
    assert result.tokens_used == 30
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "sk-ant-test"
    assert captured["headers"]["anthropic-version"]
    assert captured["json"]["system"] == "You are a helpful assistant."
    assert captured["json"]["messages"] == [{"role": "user", "content": "Write a CV summary."}]


@pytest.mark.asyncio
async def test_provider_error_never_leaks_raw_response(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.http_client import ExternalAPIError

    async def failing_post_json(*args, **kwargs):
        raise ExternalAPIError("upstream secret detail that must never leak")

    monkeypatch.setattr(ai_provider_module, "post_json", failing_post_json)
    settings = Settings(ai_provider="openai", ai_api_key="sk-test", ai_model="gpt-test")
    provider = OpenAIProvider(settings)

    with pytest.raises(AIProviderError) as excinfo:
        await provider.generate_text(system_prompt="s", user_prompt="u", max_tokens=100)
    assert "upstream secret detail" not in str(excinfo.value)

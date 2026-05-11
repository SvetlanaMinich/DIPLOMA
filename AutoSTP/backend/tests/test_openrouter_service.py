"""Юнит-тесты OpenRouter-клиента (без реальной сети)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import APIStatusError, RateLimitError

from app.core.config import settings
from app.services import openrouter_service as ors


@pytest.fixture(autouse=True)
def _reset_openrouter_client() -> None:
    ors.reset_client()
    yield
    ors.reset_client()


@pytest.mark.asyncio
async def test_chat_completion_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    msg = MagicMock()
    msg.content = "  hello  "
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=resp)
    monkeypatch.setattr(ors, "get_async_client", lambda: mock_client)

    out = await ors.chat_completion([{"role": "user", "content": "hi"}])
    assert out == "hello"
    mock_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None)
    ors.reset_client()
    with pytest.raises(ors.OpenRouterConfigError):
        await ors.chat_completion([{"role": "user", "content": "x"}])


@pytest.mark.asyncio
async def test_no_retry_on_401(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=APIStatusError(
            "unauthorized",
            response=MagicMock(status_code=401),
            body=None,
        )
    )
    monkeypatch.setattr(ors, "get_async_client", lambda: mock_client)
    monkeypatch.setattr(settings, "OPENROUTER_MAX_RETRIES", 3)

    with pytest.raises(ors.OpenRouterRequestError) as ei:
        await ors.chat_completion([{"role": "user", "content": "x"}])
    assert ei.value.status_code == 401
    assert mock_client.chat.completions.create.await_count == 1


@pytest.mark.asyncio
async def test_retry_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    msg = MagicMock()
    msg.content = "ok"
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[
            RateLimitError("lim", response=MagicMock(), body=None),
            resp,
        ]
    )
    monkeypatch.setattr(ors, "get_async_client", lambda: mock_client)
    monkeypatch.setattr(settings, "OPENROUTER_MAX_RETRIES", 4)
    monkeypatch.setattr(settings, "OPENROUTER_RETRY_BASE_SECONDS", 0.01)

    out = await ors.chat_completion([{"role": "user", "content": "x"}])
    assert out == "ok"
    assert mock_client.chat.completions.create.await_count == 2

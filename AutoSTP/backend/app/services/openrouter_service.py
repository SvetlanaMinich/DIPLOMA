"""Асинхронный клиент OpenRouter (OpenAI-compatible API)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError
from openai import APITimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenRouterConfigError(RuntimeError):
    """Нет API-ключа в настройках."""


class OpenRouterRequestError(RuntimeError):
    """Ответ API с ошибкой (после повторов или без повтора)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


_client: AsyncOpenAI | None = None


def reset_client() -> None:
    global _client
    _client = None


def get_async_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        key = (settings.OPENROUTER_API_KEY or "").strip()
        if not key:
            raise OpenRouterConfigError(
                "OPENROUTER_API_KEY is missing; set it in AutoSTP/.env or backend/.env"
            )
        _client = AsyncOpenAI(
            base_url=settings.OPENROUTER_BASE_URL.rstrip("/"),
            api_key=key,
            timeout=settings.OPENROUTER_TIMEOUT_SECONDS,
            default_headers={
                "HTTP-Referer": settings.OPENROUTER_HTTP_REFERER,
                "X-Title": settings.OPENROUTER_APP_TITLE,
            },
        )
    return _client


def _retryable_http_status(code: int) -> bool:
    return code in (408, 429, 500, 502, 503, 529)


async def chat_completion(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Один запрос chat.completions; текст ответа или пустая строка."""
    client = get_async_client()
    m = model or settings.OPENROUTER_MODEL
    temp = settings.OPENROUTER_TEMPERATURE if temperature is None else temperature
    mt = settings.OPENROUTER_MAX_TOKENS if max_tokens is None else max_tokens

    delay = settings.OPENROUTER_RETRY_BASE_SECONDS
    last_error: BaseException | None = None

    for attempt in range(settings.OPENROUTER_MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=m,
                messages=messages,
                temperature=temp,
                max_tokens=mt,
            )
            text = response.choices[0].message.content
            return (text or "").strip()
        except RateLimitError as e:
            last_error = e
            logger.warning("OpenRouter rate limit (%s/%s)", attempt + 1, settings.OPENROUTER_MAX_RETRIES)
        except APITimeoutError as e:
            last_error = e
            logger.warning("OpenRouter timeout (%s/%s)", attempt + 1, settings.OPENROUTER_MAX_RETRIES)
        except APIConnectionError as e:
            last_error = e
            logger.warning("OpenRouter connection error: %s", e)
        except APIStatusError as e:
            if not _retryable_http_status(e.status_code):
                raise OpenRouterRequestError(str(e), status_code=e.status_code) from e
            last_error = e
            logger.warning("OpenRouter HTTP %s, retry", e.status_code)

        if attempt + 1 < settings.OPENROUTER_MAX_RETRIES:
            await asyncio.sleep(delay)
            delay = min(delay * 2.0, 60.0)

    raise OpenRouterRequestError(f"OpenRouter: max retries exceeded ({last_error!r})") from last_error


async def ping_model() -> str:
    """Короткий запрос, чтобы проверить ключ и модель."""
    return await chat_completion(
        [
            {"role": "system", "content": "Reply as briefly as possible."},
            {"role": "user", "content": "Say only: ok"},
        ],
        temperature=0.0,
        max_tokens=16,
    )

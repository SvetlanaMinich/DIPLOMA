"""Shared rate limiter instance."""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _rate_key(request: Request) -> str:
    from app.core.config import settings  # late import to avoid circular
    if not settings.RATE_LIMIT_ENABLED:
        return str(id(request))
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_key)

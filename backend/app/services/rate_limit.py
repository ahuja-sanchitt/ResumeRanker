"""Per-IP rate limiting (slowapi/limits), with the same Redis-or-memory
graceful degradation as ``cache.py`` so limits survive restarts when Upstash
is configured, but never block local dev/demos if it isn't.
"""
from __future__ import annotations

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings

logger = logging.getLogger("rate_limit")


def _storage_uri() -> str:
    if not settings.redis_url:
        return "memory://"
    try:
        import redis

        redis.Redis.from_url(settings.redis_url).ping()
        return settings.redis_url
    except Exception as exc:  # connection/auth error -> degrade, same as cache.py
        logger.warning("Rate limiter: Redis unavailable (%r); using in-memory storage.", exc)
        return "memory://"


def client_ip(request: Request) -> str:
    """Render sits behind a proxy, so ``request.client.host`` is the proxy's
    address for every visitor — bucketing everyone together. Prefer the
    leftmost (originating) hop of X-Forwarded-For when present.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip, storage_uri=_storage_uri())

"""Cache layer with a Redis backend and an in-memory fallback.

The public interface is tiny on purpose — `get`, `set`, `delete`, plus a
`fingerprint` helper — so callers don't care which backend is live. If
``REDIS_URL`` is set we use Redis (e.g. Upstash); otherwise, or if Redis is
unreachable, we transparently degrade to an in-process dict so local dev and
demos never break.

Values are JSON-serialized, so anything JSON-friendly (dicts, lists) round-trips.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Optional

from app.config import settings


class _MemoryBackend:
    """Dict-backed store with per-key expiry. Not shared across processes."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Optional[float], str]] = {}

    def get(self, key: str) -> Optional[str]:
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at is not None and expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: str, ttl: Optional[int]) -> None:
        expires_at = time.time() + ttl if ttl else None
        self._store[key] = (expires_at, value)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


class _RedisBackend:
    """Thin wrapper over redis-py using JSON string values."""

    def __init__(self, url: str) -> None:
        import redis  # imported lazily so the dep is only needed when used

        self._client = redis.Redis.from_url(url, decode_responses=True)
        # Fail fast if the URL is set but the server is unreachable, so the
        # caller can fall back to memory instead of erroring on every request.
        self._client.ping()

    def get(self, key: str) -> Optional[str]:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl: Optional[int]) -> None:
        if ttl:
            self._client.set(key, value, ex=ttl)
        else:
            self._client.set(key, value)

    def delete(self, key: str) -> None:
        self._client.delete(key)


class Cache:
    """Backend-agnostic cache facade."""

    def __init__(self) -> None:
        self.backend_name: str
        if settings.redis_url:
            try:
                self._backend: Any = _RedisBackend(settings.redis_url)
                self.backend_name = "redis"
            except Exception as exc:  # connection/auth/import error -> degrade
                print(f"[cache] Redis unavailable ({exc!r}); using in-memory cache.")
                self._backend = _MemoryBackend()
                self.backend_name = "memory (redis fallback)"
        else:
            self._backend = _MemoryBackend()
            self.backend_name = "memory"

    def get_json(self, key: str) -> Optional[Any]:
        raw = self._backend.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._backend.set(key, json.dumps(value), ttl)

    def delete(self, key: str) -> None:
        self._backend.delete(key)

    @staticmethod
    def fingerprint(*parts: bytes | str) -> str:
        """Stable SHA-256 hex digest over the given parts.

        Used to fingerprint (résumé bytes + normalized JD) so identical inputs
        hit the cache instead of re-running extraction, embeddings, and the LLM.
        """
        hasher = hashlib.sha256()
        for part in parts:
            if isinstance(part, str):
                part = part.encode("utf-8")
            hasher.update(part)
            hasher.update(b"\x00")  # delimiter so concatenation is unambiguous
        return hasher.hexdigest()


# Module-level singleton; import `cache` wherever caching is needed.
cache = Cache()

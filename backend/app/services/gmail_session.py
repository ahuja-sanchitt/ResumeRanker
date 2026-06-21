"""Server-side storage for a connected-Gmail session.

After OAuth we store the user's tokens in the cache under a random session id
and hand that id to the frontend, which sends it back as the `X-Gmail-Session`
header. We deliberately do NOT use cookies — cross-origin (Vercel ↔ Render)
cookies need SameSite=None;Secure and are fiddly across local/prod; a header
token is simpler and works the same in both. Tradeoff: it lives in the
frontend's storage, so it's readable by JS (acceptable for this app's scope).
"""
from __future__ import annotations

import secrets
import time
from typing import Any, Optional

from app.config import settings
from app.services import google_oauth
from app.services.cache import cache

_PREFIX = "gauth:"
_REFRESH_SKEW = 60  # refresh a bit before actual expiry


def create_session(tokens: dict[str, Any], email: str) -> str:
    session_id = secrets.token_urlsafe(32)
    record = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "expires_at": time.time() + int(tokens.get("expires_in", 3600)),
        "email": email,
    }
    cache.set_json(_PREFIX + session_id, record, ttl=settings.gmail_session_ttl_seconds)
    return session_id


def get_email(session_id: str) -> Optional[str]:
    record = cache.get_json(_PREFIX + session_id)
    return record.get("email") if record else None


def delete_session(session_id: str) -> None:
    cache.delete(_PREFIX + session_id)


def get_valid_access_token(session_id: str) -> str:
    """Return a non-expired access token for the session, refreshing if needed.

    Raises LookupError if the session is unknown/expired.
    """
    key = _PREFIX + session_id
    record = cache.get_json(key)
    if not record:
        raise LookupError("Gmail session not found or expired. Reconnect Gmail.")

    if record["expires_at"] - _REFRESH_SKEW > time.time():
        return record["access_token"]

    # Expired — refresh using the long-lived refresh token.
    refresh_token = record.get("refresh_token")
    if not refresh_token:
        raise LookupError("No refresh token; reconnect Gmail.")
    refreshed = google_oauth.refresh_access_token(refresh_token)
    record["access_token"] = refreshed["access_token"]
    record["expires_at"] = time.time() + int(refreshed.get("expires_in", 3600))
    cache.set_json(key, record, ttl=settings.gmail_session_ttl_seconds)
    return record["access_token"]

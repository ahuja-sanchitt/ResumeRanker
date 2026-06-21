"""Google OAuth 2.0 helpers (raw HTTP, no SDK) for Gmail draft access.

We request the minimal `gmail.compose` scope — enough to create a draft, and it
never sends on its own. `userinfo.email` lets us label the connected account.

Flow: build_auth_url() -> user consents -> callback gets a code ->
exchange_code() -> we store the tokens (see gmail_session). Access tokens expire
in ~1h; refresh_access_token() renews them using the long-lived refresh token.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# gmail.compose = create/read/update drafts and send. We only ever call
# drafts.create, so nothing is sent without the user clicking send in Gmail.
SCOPES = "https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/userinfo.email"


class GoogleAuthError(Exception):
    """Raised when OAuth isn't configured or a token call fails."""


def _require_config() -> None:
    if not (settings.google_client_id and settings.google_client_secret):
        raise GoogleAuthError("Google OAuth is not configured (GOOGLE_CLIENT_ID/SECRET).")


def build_auth_url(state: str) -> str:
    _require_config()
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",   # get a refresh token
        "prompt": "consent",        # ensure a refresh token is returned every time
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict[str, Any]:
    _require_config()
    resp = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=20.0,
    )
    if resp.status_code != 200:
        raise GoogleAuthError(f"Token exchange failed: {resp.text}")
    return resp.json()  # access_token, refresh_token, expires_in, ...


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    _require_config()
    resp = httpx.post(
        TOKEN_URL,
        data={
            "refresh_token": refresh_token,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "grant_type": "refresh_token",
        },
        timeout=20.0,
    )
    if resp.status_code != 200:
        raise GoogleAuthError(f"Token refresh failed: {resp.text}")
    return resp.json()  # access_token, expires_in (no new refresh_token)


def get_user_email(access_token: str) -> str:
    try:
        resp = httpx.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json().get("email", "")
    except Exception:
        return ""

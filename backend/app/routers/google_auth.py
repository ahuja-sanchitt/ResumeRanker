"""Google OAuth endpoints for connecting a Gmail account (draft access only).

Flow:
  GET  /auth/google/login    -> redirect to Google's consent screen
  GET  /auth/google/callback -> exchange code, store session, redirect to frontend
  GET  /auth/google/status   -> is this session connected? (X-Gmail-Session header)
  POST /auth/google/logout   -> drop the stored session
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.config import settings
from app.models.schemas import GmailStatusResponse
from app.services import gmail_session, google_oauth
from app.services.cache import cache

router = APIRouter(tags=["google-auth"])

_STATE_PREFIX = "gstate:"
_STATE_TTL = 600  # 10 minutes to complete the consent flow


@router.get("/auth/google/login")
def google_login() -> RedirectResponse:
    try:
        state = secrets.token_urlsafe(24)
        cache.set_json(_STATE_PREFIX + state, {"ok": True}, ttl=_STATE_TTL)
        return RedirectResponse(google_oauth.build_auth_url(state))
    except google_oauth.GoogleAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/auth/google/callback")
def google_callback(code: str = Query(...), state: str = Query(...)) -> RedirectResponse:
    # CSRF: the state we issued must still be present.
    if cache.get_json(_STATE_PREFIX + state) is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")
    cache.delete(_STATE_PREFIX + state)

    try:
        tokens = google_oauth.exchange_code(code)
    except google_oauth.GoogleAuthError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    email = google_oauth.get_user_email(tokens.get("access_token", ""))
    session_id = gmail_session.create_session(tokens, email)

    # Hand the session token to the frontend (no cross-origin cookies). The
    # frontend stores it and sends it back as the X-Gmail-Session header.
    sep = "&" if "?" in settings.frontend_url else "?"
    return RedirectResponse(f"{settings.frontend_url}{sep}gmail_session={session_id}")


@router.get("/auth/google/status", response_model=GmailStatusResponse)
def google_status(x_gmail_session: str | None = Header(default=None)) -> GmailStatusResponse:
    if not x_gmail_session:
        return GmailStatusResponse(connected=False)
    email = gmail_session.get_email(x_gmail_session)
    return GmailStatusResponse(connected=email is not None, email=email)


@router.post("/auth/google/logout")
def google_logout(x_gmail_session: str | None = Header(default=None)) -> dict:
    if x_gmail_session:
        gmail_session.delete_session(x_gmail_session)
    return {"ok": True}

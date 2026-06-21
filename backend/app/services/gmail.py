"""Create a Gmail draft via the Gmail REST API (raw HTTP).

We only call `users.drafts.create` — this puts the message in the user's Drafts
folder. It is never sent; the user reviews and sends it manually from Gmail.
"""
from __future__ import annotations

import base64
from email.message import EmailMessage
from typing import Any

import httpx

DRAFTS_URL = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"


class GmailError(Exception):
    """Raised when draft creation fails."""


def _build_raw_message(to: str, subject: str, body: str) -> str:
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def create_draft(access_token: str, to: str, subject: str, body: str) -> dict[str, Any]:
    raw = _build_raw_message(to, subject, body)
    try:
        resp = httpx.post(
            DRAFTS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"message": {"raw": raw}},
            timeout=20.0,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise GmailError(f"Gmail draft creation failed ({exc.response.status_code}): {exc.response.text}") from exc
    except Exception as exc:
        raise GmailError(f"Gmail draft creation failed: {exc}") from exc

    data = resp.json()
    return {
        "draft_id": data.get("id", ""),
        # Generic deep-link to the Drafts folder (per-draft links aren't stable).
        "drafts_url": "https://mail.google.com/mail/u/0/#drafts",
    }

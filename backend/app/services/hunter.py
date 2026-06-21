"""Contact discovery via Hunter.io Domain Search.

Given a company name, Hunter returns public-sourced work emails with names,
positions, seniority, and department. We filter toward engineering leadership /
senior engineers — the people worth a tailored cold email.

This is the compliant alternative to scraping personal emails (which would
violate site ToS and privacy law). Outreach is still meant to be 1:1 and
human-reviewed (we only ever create Gmail *drafts*).
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings

DOMAIN_SEARCH_URL = "https://api.hunter.io/v2/domain-search"

# Hunter tags each email with seniority + department; prefer these.
_WANT_SENIORITY = {"senior", "executive"}
_WANT_DEPARTMENT = {"engineering", "it"}
# Fallback: match against the free-text position when the tags are missing.
_POSITION_KEYWORDS = (
    "engineer", "engineering manager", "developer", "swe", "architect",
    "tech lead", "cto", "vp engineering", "head of engineering", "director of engineering",
)


class HunterError(Exception):
    """Raised when contact discovery fails or isn't configured."""


def _is_relevant(email: dict[str, Any]) -> bool:
    seniority = (email.get("seniority") or "").lower()
    department = (email.get("department") or "").lower()
    position = (email.get("position") or "").lower()
    if seniority in _WANT_SENIORITY and department in _WANT_DEPARTMENT:
        return True
    if department in _WANT_DEPARTMENT and seniority == "senior":
        return True
    return any(k in position for k in _POSITION_KEYWORDS)


def find_contacts(company: str, limit: int = 8) -> dict[str, Any]:
    if not settings.hunter_api_key:
        raise HunterError("HUNTER_API_KEY is not configured.")

    try:
        resp = httpx.get(
            DOMAIN_SEARCH_URL,
            params={
                "company": company,
                "api_key": settings.hunter_api_key,
                "limit": 50,
                "type": "personal",
            },
            timeout=20.0,
        )
        resp.raise_for_status()
        payload = resp.json().get("data", {})
    except httpx.HTTPStatusError as exc:
        raise HunterError(f"Hunter API error ({exc.response.status_code}).") from exc
    except Exception as exc:
        raise HunterError(f"Contact lookup failed: {exc}") from exc

    domain = payload.get("domain")
    raw_emails = payload.get("emails", []) or []

    relevant = [e for e in raw_emails if _is_relevant(e)]
    # If nothing matched the filters, fall back to whatever Hunter returned so the
    # user still gets options rather than an empty list.
    chosen = (relevant or raw_emails)[:limit]

    contacts = [
        {
            "first_name": e.get("first_name") or "",
            "last_name": e.get("last_name") or "",
            "email": e.get("value") or "",
            "position": e.get("position") or "",
            "seniority": e.get("seniority") or "",
            "department": e.get("department") or "",
            "confidence": int(e.get("confidence") or 0),
        }
        for e in chosen
        if e.get("value")
    ]
    return {"company": company, "domain": domain, "contacts": contacts}

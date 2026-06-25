"""Contact discovery via Hunter.io Domain Search.

Given a company name, Hunter returns public-sourced work emails with names,
positions, seniority, and department. We filter toward senior individual
contributor engineers — the people worth a tailored cold email from a candidate.

This is the compliant alternative to scraping personal emails (which would
violate site ToS and privacy law). Outreach is still meant to be 1:1 and
human-reviewed (we only ever create Gmail *drafts*).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("hunter")

DOMAIN_SEARCH_URL = "https://api.hunter.io/v2/domain-search"

# Target: engineering managers, tech leads, and senior engineering leadership.
_WANT_DEPARTMENT = {"engineering", "it"}

_LEAD_KEYWORDS = (
    "engineering manager", "engineering lead", "tech lead", "technical lead",
    "team lead", "lead engineer", "lead software engineer",
    "director of engineering", "head of engineering", "vp of engineering",
    "vp engineering", "staff engineer", "principal engineer",
)


class HunterError(Exception):
    """Raised when contact discovery fails or isn't configured."""


def _is_relevant(email: dict[str, Any]) -> bool:
    seniority = (email.get("seniority") or "").lower()
    department = (email.get("department") or "").lower()
    position = (email.get("position") or "").lower()

    # Manager/lead seniority in an engineering department.
    if seniority in {"manager", "director", "vp", "senior"} and department in _WANT_DEPARTMENT:
        return True

    # Match by title keywords when Hunter tags are missing.
    return any(k in position for k in _LEAD_KEYWORDS)


def _domain_search(param_name: str, param_value: str, api_key: str) -> tuple[int, dict[str, Any]]:
    """Single Hunter Domain Search call. Returns (status_code, data dict)."""
    resp = httpx.get(
        DOMAIN_SEARCH_URL,
        params={"api_key": api_key, "limit": 50, "type": "personal", param_name: param_value},
        timeout=20.0,
    )
    if resp.status_code in (200, 400):
        return resp.status_code, resp.json().get("data", {})
    resp.raise_for_status()
    return resp.status_code, {}


_STRIP_SUFFIXES = (
    " group", " inc", " inc.", " llc", " ltd", " corp", " corporation",
    " co", " technologies", " technology", " tech", " systems", " solutions",
    " holdings", " international", " global",
)


def domain_candidates(company: str) -> list[str]:
    """Return domain candidates to try, most specific first.

    'Expedia Group' -> ['expediagroup.com', 'expedia.com']
    'Google LLC'    -> ['googlellc.com', 'google.com']
    """
    base = company.lower()
    candidates = [base.replace(" ", "") + ".com"]
    # Strip one common suffix and try the shorter form.
    for suffix in _STRIP_SUFFIXES:
        if base.endswith(suffix):
            shorter = base[: -len(suffix)].strip().replace(" ", "")
            if shorter:
                candidates.append(shorter + ".com")
            break
    return candidates


def find_contacts(company: str, limit: int = 8) -> dict[str, Any]:
    if not settings.hunter_api_key:
        raise HunterError("HUNTER_API_KEY is not configured.")

    try:
        logger.info("hunter search company=%r", company)
        status, payload = _domain_search("company", company, settings.hunter_api_key)
        logger.info("hunter company-search status=%d emails=%d", status, len(payload.get("emails") or []))

        if status == 400 or not payload.get("emails"):
            for candidate in domain_candidates(company):
                logger.info("hunter falling back to domain=%r", candidate)
                status2, payload2 = _domain_search("domain", candidate, settings.hunter_api_key)
                logger.info("hunter domain-search domain=%r status=%d emails=%d", candidate, status2, len(payload2.get("emails") or []))
                if status2 == 200 and payload2.get("emails"):
                    payload = payload2
                    break
    except httpx.HTTPStatusError as exc:
        raise HunterError(f"Hunter API error ({exc.response.status_code}).") from exc
    except Exception as exc:
        raise HunterError(f"Contact lookup failed: {exc}") from exc

    domain = payload.get("domain")
    raw_emails = payload.get("emails", []) or []

    relevant = [e for e in raw_emails if _is_relevant(e)]
    logger.info("hunter raw=%d relevant=%d company=%r domain=%r", len(raw_emails), len(relevant), company, domain)
    # Fall back to all results if nothing matched the IC filter, so the user
    # always gets something to work with.
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

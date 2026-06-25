"""Contact discovery via Apollo.io.

Two-step flow:
  1. People Search (free, no credits) — find engineers at a company by domain.
  2. Bulk People Enrichment (costs credits) — get work emails for top results.

Used as a fallback when Hunter.io returns no contacts.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("apollo")

PEOPLE_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/api_search"
BULK_ENRICH_URL = "https://api.apollo.io/api/v1/people/bulk_match"

# Titles to search for — engineering managers, leads, and senior leadership.
_LEAD_TITLES = [
    "engineering manager",
    "engineering lead",
    "tech lead",
    "technical lead",
    "team lead",
    "lead engineer",
    "lead software engineer",
    "director of engineering",
    "head of engineering",
    "vp of engineering",
    "vp engineering",
    "staff software engineer",
    "principal software engineer",
    "principal engineer",
]

# Max contacts to enrich — each costs a credit.
_ENRICH_LIMIT = 5


class ApolloError(Exception):
    """Raised when Apollo discovery fails or isn't configured."""


def _headers() -> dict[str, str]:
    return {"Content-Type": "application/json", "X-Api-Key": settings.apollo_api_key}


def _search(domain: str, location: str = "", page_size: int = 20) -> list[dict[str, Any]]:
    body: dict[str, Any] = {
        "q_organization_domains_list": [domain],
        "person_seniorities": ["manager", "director", "vp", "senior"],
        "person_titles": _LEAD_TITLES,
        "per_page": page_size,
        "page": 1,
    }
    if location:
        body["person_locations"] = [location]
    resp = httpx.post(PEOPLE_SEARCH_URL, json=body, headers=_headers(), timeout=20.0)
    resp.raise_for_status()
    return resp.json().get("people") or []


def _bulk_enrich(person_ids: list[str]) -> list[dict[str, Any]]:
    body = {
        "details": [{"id": pid} for pid in person_ids],
        "reveal_personal_emails": False,  # work emails only — cheaper
    }
    resp = httpx.post(BULK_ENRICH_URL, json=body, headers=_headers(), timeout=30.0)
    resp.raise_for_status()
    return resp.json().get("matches") or []


DEFAULT_LOCATION = "India"


def find_contacts(company: str, domain_candidates: list[str], location: str = DEFAULT_LOCATION, limit: int = 8) -> dict[str, Any]:
    if not settings.apollo_api_key:
        raise ApolloError("APOLLO_API_KEY is not configured.")

    people: list[dict[str, Any]] = []
    found_domain: str | None = None

    for domain in domain_candidates:
        logger.info("apollo search domain=%r", domain)
        try:
            results = _search(domain, location=location)
            logger.info("apollo search domain=%r location=%r hits=%d", domain, location, len(results))
            if results:
                people = results
                found_domain = domain
                break
        except httpx.HTTPStatusError as exc:
            logger.warning("apollo search domain=%r status=%d", domain, exc.response.status_code)
        except Exception as exc:
            logger.warning("apollo search domain=%r error=%s", domain, exc)

    if not people:
        logger.info("apollo no results for company=%r", company)
        return {"company": company, "domain": None, "contacts": []}

    # Enrich only the top N to get work emails (each costs a credit).
    to_enrich = [p["id"] for p in people if p.get("id")][:_ENRICH_LIMIT]
    email_map: dict[str, str] = {}
    if to_enrich:
        try:
            logger.info("apollo enriching %d contacts", len(to_enrich))
            matches = _bulk_enrich(to_enrich)
            email_map = {m["id"]: m.get("email", "") for m in matches if m.get("id") and m.get("email")}
            logger.info("apollo enriched emails=%d", len(email_map))
        except Exception as exc:
            logger.warning("apollo enrichment failed: %s", exc)

    contacts = []
    for p in people[:limit]:
        pid = p.get("id", "")
        email = email_map.get(pid) or p.get("email", "")
        if not email:
            continue
        departments = p.get("departments") or []
        contacts.append({
            "first_name": p.get("first_name") or "",
            "last_name": p.get("last_name") or "",
            "email": email,
            "position": p.get("title") or "",
            "seniority": p.get("seniority") or "",
            "department": departments[0] if departments else "",
            "confidence": 90,
        })

    logger.info("apollo returning %d contacts for company=%r", len(contacts), company)
    return {"company": company, "domain": found_domain, "contacts": contacts}

"""Live web search for interview experiences via the OpenAI Responses API.

Returns the model's synthesized text plus any URL citations it surfaced. The
exact web-search tool type has shifted across API versions, so we try the
current name and fall back to the preview name. Structuring of this raw text
into the prep schema happens in ``llm.summarize_prep``.
"""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.services import metrics
from app.services.openai_client import get_client

# Tool type names to try, in order. The API has used both spellings.
_TOOL_TYPES = ["web_search", "web_search_preview"]


class WebSearchError(Exception):
    """Raised when the web-search call fails for all known tool variants."""


def _build_query(company: str, role: str, seniority: str) -> str:
    return (
        f"Search the web for recent candidate-reported {company} interview experiences "
        f"for a {role} ({seniority}-level software engineering) role. Prioritize Glassdoor, "
        "LeetCode Discuss, Reddit, and Blind. Summarize: how many rounds and what each is "
        "(OA, phone screen, technical/coding, system design, behavioral, HM/HR), the question "
        "types and topics that come up most, and overall difficulty/process notes. "
        "Include the source URLs you used."
    )


def _extract_sources(response: Any) -> list[str]:
    """Pull URL citations out of the Responses API output, best-effort."""
    urls: list[str] = []
    try:
        for item in getattr(response, "output", []) or []:
            for block in getattr(item, "content", []) or []:
                for ann in getattr(block, "annotations", []) or []:
                    url = getattr(ann, "url", None)
                    if url and url not in urls:
                        urls.append(url)
    except Exception:
        pass
    return urls


def run_interview_search(company: str, role: str, seniority: str) -> dict[str, Any]:
    client = get_client()
    query = _build_query(company, role, seniority)

    last_error: Exception | None = None
    for tool_type in _TOOL_TYPES:
        try:
            response = client.responses.create(
                model=settings.websearch_model,
                tools=[{"type": tool_type}],
                input=query,
            )
            text = getattr(response, "output_text", "") or ""
            if not text.strip():
                continue
            metrics.track_openai(
                "interview_prep_search", settings.websearch_model, getattr(response, "usage", None)
            )
            return {"text": text, "sources": _extract_sources(response)}
        except Exception as exc:  # unknown tool type, model access, etc.
            last_error = exc
            continue

    raise WebSearchError(
        f"Web search failed (last error: {last_error}). "
        "Confirm the account has access to the Responses API web_search tool."
    )

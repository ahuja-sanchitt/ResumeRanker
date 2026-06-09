"""POST /interview-prep — company + role -> live-web-search interview summary (TTL-cached)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import InterviewPrepRequest, InterviewPrepResponse
from app.services import llm, metrics
from app.services.cache import cache
from app.services.web_search import WebSearchError, run_interview_search

router = APIRouter(tags=["interview-prep"])


@router.post("/interview-prep", response_model=InterviewPrepResponse)
def interview_prep(req: InterviewPrepRequest) -> InterviewPrepResponse:
    company_norm = " ".join(req.company_name.split()).lower()
    seniority = llm.normalize_role(req.role)

    # Cache per company + seniority bucket, with a TTL (interview info goes stale).
    key = f"prep:{company_norm}:{seniority}"
    if not req.force_refresh:
        cached = cache.get_json(key)
        if cached is not None:
            metrics.track_cache("interview_prep", hit=True)
            return InterviewPrepResponse(**cached, cached=True)
    metrics.track_cache("interview_prep", hit=False)

    # Live web search -> structured summary.
    try:
        search = run_interview_search(req.company_name.strip(), req.role.strip(), seniority)
    except WebSearchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        summary = llm.summarize_prep(
            req.company_name.strip(), req.role.strip(), seniority,
            search["text"], search.get("sources", []),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Summarization failed: {exc}") from exc

    payload = {
        "company": req.company_name.strip(),
        "role": req.role.strip(),
        "seniority": seniority,
        **summary,
        "last_updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    cache.set_json(key, payload, ttl=settings.prep_cache_ttl_seconds)
    return InterviewPrepResponse(**payload, cached=False)

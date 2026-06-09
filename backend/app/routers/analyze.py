"""POST /analyze — résumé PDF + JD text -> hybrid explainable score (cached)."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import AnalyzeResponse
from app.services import metrics, scoring
from app.services.cache import cache
from app.services.embeddings import embedding_similarity_score
from app.services.llm import analyze_resume_jd
from app.services.pdf_extract import PdfExtractionError, extract_text_from_pdf

router = APIRouter(tags=["analyze"])

MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(resume: UploadFile = File(...), jd: str = Form(...)) -> AnalyzeResponse:
    # --- validate inputs ---
    jd_norm = " ".join(jd.split())  # collapse whitespace -> stable cache key
    if len(jd_norm) < 20:
        raise HTTPException(status_code=400, detail="Job description is too short to analyze.")

    data = await resume.read()
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="Résumé PDF exceeds the 10 MB limit.")
    if resume.content_type not in (None, "application/pdf", "application/octet-stream") and not (
        resume.filename or ""
    ).lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF résumé.")

    # --- extract text ---
    try:
        resume_text = extract_text_from_pdf(data)
    except PdfExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # --- cache check: SHA-256 over résumé bytes + normalized JD ---
    key = "analyze:" + cache.fingerprint(data, jd_norm)
    cached = cache.get_json(key)
    if cached is not None:
        metrics.track_cache("analyze", hit=True)
        return AnalyzeResponse(**cached, cached=True)
    metrics.track_cache("analyze", hit=False)

    # --- hybrid scoring ---
    try:
        embedding_score, _cosine = embedding_similarity_score(resume_text, jd_norm)
        llm_result = analyze_resume_jd(resume_text, jd_norm)
    except Exception as exc:  # OpenAI errors, bad key, rate limits, etc.
        raise HTTPException(status_code=502, detail=f"Scoring failed: {exc}") from exc

    result = scoring.build_result(embedding_score, llm_result)
    cache.set_json(key, result)  # deterministic on identical input; no TTL
    return AnalyzeResponse(**result, cached=False)

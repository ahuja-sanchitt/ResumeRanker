"""FastAPI entrypoint.

Run locally:  uvicorn app.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analyze, interview_prep
from app.services.cache import cache

app = FastAPI(
    title="AI Resume Ranker + Interview Co-Pilot",
    version="0.1.0",
    description="Hybrid explainable résumé↔JD scoring and live interview prep.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(analyze.router)
app.include_router(interview_prep.router)


@app.get("/health")
def health() -> dict:
    """Liveness probe + visibility into which cache backend is active."""
    return {
        "status": "ok",
        "cache_backend": cache.backend_name,
        "openai_key_configured": bool(settings.openai_api_key),
    }


@app.get("/")
def root() -> dict:
    return {"service": "resume-ranker", "docs": "/docs", "health": "/health"}

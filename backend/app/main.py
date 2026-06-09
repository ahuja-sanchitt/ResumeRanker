"""FastAPI entrypoint.

Run locally:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analyze, interview_prep
from app.services import metrics
from app.services.cache import cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)

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


@app.middleware("http")
async def record_latency(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    # Use the route template (not the raw path) to keep metric cardinality low.
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    if path != "/metrics":  # don't measure the scrape endpoint itself
        metrics.observe_latency(path, request.method, time.perf_counter() - start)
    return response


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


@app.get("/metrics")
def prometheus_metrics() -> Response:
    """Prometheus scrape endpoint — token usage, request counts, cache hits, latency."""
    data, content_type = metrics.render_metrics()
    return Response(content=data, media_type=content_type)


@app.get("/")
def root() -> dict:
    return {"service": "resume-ranker", "docs": "/docs", "health": "/health", "metrics": "/metrics"}

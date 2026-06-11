"""FastAPI entrypoint.

Run locally:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analyze, interview_prep
from app.services import metrics
from app.services.cache import cache


def _setup_logging() -> None:
    """Log to stdout (Render captures this) AND a rotating file (for Loki/Alloy).

    Lines use a key=value style (e.g. `openai_usage endpoint=analyze prompt_tokens=1200`)
    so Loki's logfmt parser can turn them into queryable fields in Grafana.
    """
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s | %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Guard against duplicate handlers across uvicorn --reload restarts.
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    root.addHandler(stream)

    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


_setup_logging()

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

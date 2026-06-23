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
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.routers import analyze, cold_email, google_auth, interview_prep
from app.services import metrics
from app.services.cache import cache
from app.services.rate_limit import limiter


def _setup_logging() -> None:
    """Log to stdout (Render captures this) AND a rotating file (for Loki/Alloy).

    Lines use a key=value style (e.g. `openai_usage endpoint=analyze prompt_tokens=1200`)
    so Loki's logfmt parser can turn them into queryable fields in Grafana.
    """
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s | %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Quiet noisy third-party loggers so app.log (shipped to Loki) stays focused
    # on our own usage/cache lines. watchfiles = uvicorn's reload watcher;
    # httpx/httpcore log every outbound HTTP call (incl. Alloy's /metrics scrapes
    # and OpenAI calls). Suppressing at the source affects both stdout and file.
    for noisy in ("watchfiles", "watchfiles.main", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

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

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
# No blanket default_limits: health/metrics/root stay unlimited (cheap,
# operational), and OAuth read endpoints aren't a cost vector. Only the
# OpenAI/Hunter-calling routes carry an explicit @limiter.limit(...).


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    # Match the rest of the API's {"detail": ...} error shape instead of
    # slowapi's default {"error": ...} so the frontend's existing parseError
    # handles this without any special-casing.
    response = JSONResponse(
        status_code=429,
        content={"detail": f"Too many requests ({exc.detail}). Please wait and try again."},
    )
    response.headers["Retry-After"] = "60"
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    # /docs and /redoc render Swagger/ReDoc UI from a CDN; a strict CSP there
    # would block their own scripts/styles. The real API surface is JSON, where
    # browsers don't execute CSP-relevant content anyway.
    if request.url.path not in ("/docs", "/redoc"):
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


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
app.include_router(google_auth.router)
app.include_router(cold_email.router)


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

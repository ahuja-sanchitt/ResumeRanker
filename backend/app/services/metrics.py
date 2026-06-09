"""Observability: per-call token logging + Prometheus metrics.

Every OpenAI response carries a ``usage`` object. We read it after each call,
log a structured line (captured by Render/stdout), and increment Prometheus
counters that the ``/metrics`` endpoint exposes for Prometheus → Grafana.

The usage object's field names differ across APIs:
  - chat completions / embeddings: prompt_tokens, completion_tokens, total_tokens,
    prompt_tokens_details.cached_tokens
  - responses API (web search):     input_tokens, output_tokens,
    input_tokens_details.cached_tokens
``track_openai`` reads both shapes defensively.
"""
from __future__ import annotations

import logging
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

logger = logging.getLogger("usage")

# --- Prometheus metrics ---
TOKENS = Counter(
    "openai_tokens_total",
    "OpenAI tokens consumed",
    ["endpoint", "model", "kind"],  # kind: prompt | completion | cached
)
OPENAI_REQUESTS = Counter(
    "openai_requests_total",
    "OpenAI API calls made",
    ["endpoint", "model"],
)
CACHE_EVENTS = Counter(
    "app_cache_events_total",
    "Application cache hits/misses",
    ["endpoint", "result"],  # result: hit | miss
)
HTTP_LATENCY = Histogram(
    "http_request_seconds",
    "HTTP request latency",
    ["path", "method"],
)


def _attr(obj: Any, name: str) -> int:
    return int(getattr(obj, name, 0) or 0)


def track_openai(endpoint: str, model: str, usage: Any) -> dict[str, int]:
    """Record token usage from any OpenAI usage object. Returns the parsed counts."""
    if usage is None:
        return {"prompt": 0, "completion": 0, "cached": 0}

    prompt = _attr(usage, "prompt_tokens") or _attr(usage, "input_tokens")
    completion = _attr(usage, "completion_tokens") or _attr(usage, "output_tokens")

    cached = 0
    details = getattr(usage, "prompt_tokens_details", None) or getattr(
        usage, "input_tokens_details", None
    )
    if details is not None:
        cached = int(getattr(details, "cached_tokens", 0) or 0)

    OPENAI_REQUESTS.labels(endpoint, model).inc()
    if prompt:
        TOKENS.labels(endpoint, model, "prompt").inc(prompt)
    if completion:
        TOKENS.labels(endpoint, model, "completion").inc(completion)
    if cached:
        TOKENS.labels(endpoint, model, "cached").inc(cached)

    logger.info(
        "openai_usage endpoint=%s model=%s prompt_tokens=%d completion_tokens=%d cached_tokens=%d",
        endpoint, model, prompt, completion, cached,
    )
    return {"prompt": prompt, "completion": completion, "cached": cached}


def track_cache(endpoint: str, hit: bool) -> None:
    CACHE_EVENTS.labels(endpoint, "hit" if hit else "miss").inc()
    logger.info("cache endpoint=%s result=%s", endpoint, "hit" if hit else "miss")


def observe_latency(path: str, method: str, seconds: float) -> None:
    HTTP_LATENCY.labels(path, method).observe(seconds)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST

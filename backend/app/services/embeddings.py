"""OpenAI embeddings + cosine similarity — the objective anchor for the score.

We embed the résumé and the JD, take their cosine similarity, then rescale the
typical OpenAI similarity band (see config.SIM_FLOOR/SIM_CEIL) into a 0-100
score. This number is grounded in the text itself, independent of any LLM
opinion, which is exactly why it's worth cross-checking the LLM against.
"""
from __future__ import annotations

import logging
import math

from app.config import settings
from app.services import metrics
from app.services.openai_client import get_client

logger = logging.getLogger("embeddings")

# Bound input size to keep token usage and latency predictable.
MAX_CHARS = 12000


def embed_texts(texts: list[str]) -> list[list[float]]:
    client = get_client()
    resp = client.embeddings.create(
        model=settings.embedding_model,
        input=[t[:MAX_CHARS] for t in texts],
    )
    metrics.track_openai("embeddings", settings.embedding_model, getattr(resp, "usage", None))
    return [item.embedding for item in resp.data]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _rescale_to_score(cosine: float) -> int:
    floor, ceil = settings.sim_floor, settings.sim_ceil
    if ceil <= floor:  # guard against bad config
        return round(max(0.0, min(1.0, cosine)) * 100)
    normalized = (cosine - floor) / (ceil - floor)
    return round(max(0.0, min(1.0, normalized)) * 100)


def embedding_similarity_score(resume_text: str, jd_text: str) -> tuple[int, float]:
    """Return (0-100 score, raw cosine) for résumé vs. JD."""
    resume_vec, jd_vec = embed_texts([resume_text, jd_text])
    cosine = cosine_similarity(resume_vec, jd_vec)
    score = _rescale_to_score(cosine)
    logger.info(
        "embedding cosine=%.4f floor=%.2f ceil=%.2f score=%d resume_chars=%d jd_chars=%d",
        cosine, settings.sim_floor, settings.sim_ceil, score, len(resume_text), len(jd_text),
    )
    return score, cosine

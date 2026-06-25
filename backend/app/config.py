"""Central configuration, loaded from environment (.env in local dev).

Keeping settings in one place makes model choices and scoring weights easy to
tune without hunting through the code.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    # --- OpenAI ---
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    # Model used for the web-search-backed interview prep (Responses API).
    websearch_model: str = os.getenv("OPENAI_WEBSEARCH_MODEL", "gpt-4o")

    # --- Cache ---
    redis_url: str = os.getenv("REDIS_URL", "")
    # Interview-prep cache TTL (default 7 days). Resume analysis is deterministic
    # on identical input, so it uses a long/no TTL.
    prep_cache_ttl_seconds: int = _get_int("PREP_CACHE_TTL_SECONDS", 7 * 24 * 60 * 60)

    # --- Scoring ---
    # final = embedding_weight * embedding_score + (1 - embedding_weight) * llm_score
    embedding_weight: float = _get_float("EMBEDDING_WEIGHT", 0.6)
    # OpenAI embeddings are anisotropic: even unrelated texts rarely score below
    # ~0.6 cosine, and strong matches top out around ~0.9. Linearly rescale that
    # band to 0-100 so the score is meaningfully spread, then clamp.
    sim_floor: float = _get_float("SIM_FLOOR", 0.40)
    sim_ceil: float = _get_float("SIM_CEIL", 0.90)

    # --- Cold email: Hunter.io (contact discovery) ---
    hunter_api_key: str = os.getenv("HUNTER_API_KEY", "")

    # --- Cold email: Apollo.io (contact discovery fallback) ---
    apollo_api_key: str = os.getenv("APOLLO_API_KEY", "")

    # --- Cold email: Google OAuth + Gmail (draft only) ---
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
    )
    # Where to send the user back after OAuth (the frontend).
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    # How long a connected-Gmail session (stored token) lives.
    gmail_session_ttl_seconds: int = _get_int("GMAIL_SESSION_TTL_SECONDS", 7 * 24 * 60 * 60)

    # --- CORS ---
    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    ]


settings = Settings()

"""Lazily-constructed, shared OpenAI client.

Constructing the client is cheap and does not validate the key, so a missing
key only surfaces when an actual request is made (handled at the route layer).
"""
from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from app.config import settings


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    return OpenAI(api_key=settings.openai_api_key or None)

"""Combine the objective embedding score and the LLM's fit score.

The whole point of the hybrid: the embedding similarity is grounded in the text
and immune to the LLM's tendency to give ungrounded round numbers, while the LLM
adds nuance (seniority, must-have requirements). We surface all three numbers so
the final score is explainable, never a black box.
"""
from __future__ import annotations

from typing import Any

from app.config import settings


def build_result(embedding_score: int, llm_result: dict[str, Any]) -> dict[str, Any]:
    w = settings.embedding_weight
    llm_fit = llm_result.get("llm_fit_score", 0)
    final = round(w * embedding_score + (1 - w) * llm_fit)
    return {
        "final_score": max(0, min(100, final)),
        "embedding_score": embedding_score,
        "llm_fit_score": llm_fit,
        "matched_skills": llm_result.get("matched_skills", []),
        "missing_skills": llm_result.get("missing_skills", []),
        "strengths": llm_result.get("strengths", []),
        "gaps": llm_result.get("gaps", []),
        "feedback": llm_result.get("feedback", ""),
    }

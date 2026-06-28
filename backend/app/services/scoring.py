"""Combine the objective embedding score and the LLM's fit score.

The whole point of the hybrid: the embedding similarity is grounded in the text
and immune to the LLM's tendency to give ungrounded round numbers, while the LLM
adds nuance (seniority, must-have requirements). We surface all three numbers so
the final score is explainable, never a black box.
"""
from __future__ import annotations

from typing import Any

from app.config import settings


def _skill_coverage(matched: list, missing: list) -> int:
    total = len(matched) + len(missing)
    if total == 0:
        return 0
    return round(len(matched) / total * 100)


def build_result(embedding_score: int, llm_result: dict[str, Any]) -> dict[str, Any]:
    matched = llm_result.get("matched_skills", [])
    missing = llm_result.get("missing_skills", [])
    skill_score = _skill_coverage(matched, missing)
    llm_fit = llm_result.get("llm_fit_score", 0)

    # Weighted blend of the three signals, normalized so the weights need not
    # sum to exactly 1.0 (makes tuning via env vars forgiving).
    we, ws, wl = settings.embedding_weight, settings.skill_weight, settings.llm_weight
    total_w = we + ws + wl or 1.0
    final = round((we * embedding_score + ws * skill_score + wl * llm_fit) / total_w)

    return {
        "final_score": max(0, min(100, final)),
        "embedding_score": embedding_score,
        "skill_score": skill_score,
        "llm_fit_score": llm_fit,
        "matched_skills": matched,
        "missing_skills": missing,
        "strengths": llm_result.get("strengths", []),
        "gaps": llm_result.get("gaps", []),
        "feedback": llm_result.get("feedback", ""),
    }

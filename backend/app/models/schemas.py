"""Pydantic request/response models — the API contract the frontend codes against."""
from __future__ import annotations

from pydantic import BaseModel, Field


# ---------- /analyze ----------

class AnalyzeResponse(BaseModel):
    final_score: int = Field(..., ge=0, le=100, description="Blended 0-100 match score")
    embedding_score: int = Field(..., ge=0, le=100, description="Objective cosine-similarity score")
    llm_fit_score: int = Field(..., ge=0, le=100, description="LLM's holistic fit judgement")
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    feedback: str = ""
    cached: bool = False


# ---------- /interview-prep ----------

class InterviewPrepRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=120)
    role: str = Field(..., min_length=1, max_length=120)
    force_refresh: bool = False


class InterviewRound(BaseModel):
    name: str
    description: str = ""


class InterviewPrepResponse(BaseModel):
    company: str
    role: str
    seniority: str = Field(..., description="Normalized bucket: junior | mid | senior")
    num_rounds: int = 0
    rounds: list[InterviewRound] = Field(default_factory=list)
    frequent_question_types: list[str] = Field(default_factory=list)
    topics_to_focus: list[str] = Field(default_factory=list)
    difficulty_notes: str = ""
    sources: list[str] = Field(default_factory=list)
    last_updated: str = ""
    cached: bool = False

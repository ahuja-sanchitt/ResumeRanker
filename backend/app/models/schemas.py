"""Pydantic request/response models — the API contract the frontend codes against."""
from __future__ import annotations

from pydantic import BaseModel, Field


# ---------- /analyze ----------

class AnalyzeResponse(BaseModel):
    final_score: int = Field(..., ge=0, le=100, description="Blended 0-100 match score")
    embedding_score: int = Field(..., ge=0, le=100, description="Semantic similarity of full résumé vs JD")
    skill_score: int = Field(..., ge=0, le=100, description="Skill coverage: matched / (matched + missing) * 100")
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


class InterviewTopic(BaseModel):
    topic: str
    questions: list[str] = Field(default_factory=list)


class InterviewPrepResponse(BaseModel):
    company: str
    role: str
    seniority: str = Field(..., description="Normalized bucket: junior | mid | senior")
    num_rounds: int = 0
    rounds: list[InterviewRound] = Field(default_factory=list)
    frequent_question_types: list[str] = Field(default_factory=list)
    topics_to_focus: list[InterviewTopic] = Field(default_factory=list)
    difficulty_notes: str = ""
    sources: list[str] = Field(default_factory=list)
    last_updated: str = ""
    cached: bool = False


# ---------- cold email ----------

class ContactsRequest(BaseModel):
    company: str = Field(..., min_length=1, max_length=120)


class Contact(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str
    position: str = ""
    seniority: str = ""
    department: str = ""
    confidence: int = 0


class ContactsResponse(BaseModel):
    company: str
    domain: str | None = None
    contacts: list[Contact] = Field(default_factory=list)


class ColdEmailDraftResponse(BaseModel):
    subject: str
    body: str


class GmailDraftRequest(BaseModel):
    to: str = Field(..., min_length=3, max_length=320)
    subject: str = Field(..., min_length=1, max_length=998)
    body: str = Field(..., min_length=1, max_length=20000)


class GmailDraftResponse(BaseModel):
    draft_id: str
    drafts_url: str


class GmailStatusResponse(BaseModel):
    connected: bool
    email: str | None = None

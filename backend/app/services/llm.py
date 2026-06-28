"""LLM calls via OpenAI chat completions, all returning validated JSON.

Three jobs:
  - analyze_resume_jd : matched/missing skills, strengths, gaps, feedback, fit score
  - normalize_role    : free-text job title -> junior | mid | senior
  - summarize_prep    : turn raw web-search text into a structured prep summary
"""
from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.services import metrics
from app.services.openai_client import get_client

RESUME_MAX_CHARS = 8000
JD_MAX_CHARS = 6000
SEARCH_MAX_CHARS = 12000

VALID_SENIORITY = {"junior", "mid", "senior"}


def _chat_json(
    system: str, user: str, *, model: str | None = None, endpoint: str = "chat"
) -> dict[str, Any]:
    """Call chat completions in JSON mode and parse the result into a dict.

    The static `system` message is placed first so it forms a stable prefix —
    the shape OpenAI's automatic prompt caching can reuse when it's long enough.
    """
    client = get_client()
    chosen_model = model or settings.chat_model
    resp = client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    metrics.track_openai(endpoint, chosen_model, getattr(resp, "usage", None))
    content = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = {}
    return data if isinstance(data, dict) else {}


def _as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _as_score(value: Any) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


# ---------- résumé ↔ JD analysis ----------

_ANALYZE_SYSTEM = (
    "You are a precise technical recruiter. Compare a candidate's résumé against a "
    "job description and respond ONLY with a JSON object using exactly these keys:\n"
    '  "matched_skills": string[]   // concise skill/technology labels (2-5 words max) from the JD that the résumé clearly demonstrates. e.g. "Python", "Redis", "System Design", "CI/CD", "Microservices"\n'
    '  "missing_skills": string[]   // concise skill/technology labels (2-5 words max) from the JD absent or weak in the résumé. Same format as matched_skills.\n'
    '  "strengths": string[]        // short phrases on where the candidate is strong for THIS role\n'
    '  "gaps": string[]             // short phrases on the most important gaps\n'
    '  "feedback": string           // 2-4 sentences of concrete, actionable advice to improve the match\n'
    '  "llm_fit_score": number      // 0-100 holistic fit, considering seniority and core requirements\n'
    "Base every judgement only on the provided text. Do not invent skills the résumé does not support. "
    "Keep matched_skills and missing_skills as short keyword labels, never copy full JD sentences."
)


def analyze_resume_jd(resume_text: str, jd_text: str) -> dict[str, Any]:
    user = (
        f"JOB DESCRIPTION:\n{jd_text[:JD_MAX_CHARS]}\n\n"
        f"RÉSUMÉ:\n{resume_text[:RESUME_MAX_CHARS]}\n\n"
        "Return the JSON object now."
    )
    data = _chat_json(_ANALYZE_SYSTEM, user, endpoint="analyze")
    return {
        "matched_skills": _as_str_list(data.get("matched_skills")),
        "missing_skills": _as_str_list(data.get("missing_skills")),
        "strengths": _as_str_list(data.get("strengths")),
        "gaps": _as_str_list(data.get("gaps")),
        "feedback": str(data.get("feedback", "")).strip(),
        "llm_fit_score": _as_score(data.get("llm_fit_score")),
    }


# ---------- role normalization ----------

_NORMALIZE_SYSTEM = (
    "Classify a job title into a seniority bucket. Respond ONLY with JSON: "
    '{"seniority": "junior" | "mid" | "senior"}. '
    "Guidance: intern/new-grad/associate/I/1/entry -> junior; II/III/mid-level/"
    "regular SWE with a few years -> mid; senior/staff/principal/lead/manager -> senior. "
    "If ambiguous, choose mid."
)


def _heuristic_seniority(role: str) -> str:
    r = role.lower()
    if any(k in r for k in ("senior", "staff", "principal", "lead", "manager", "sr.", "sr ")):
        return "senior"
    if any(k in r for k in ("intern", "junior", "associate", "entry", "new grad", "graduate", " i ", " 1", "jr")):
        return "junior"
    return "mid"


def normalize_role(role: str) -> str:
    try:
        data = _chat_json(_NORMALIZE_SYSTEM, f'Job title: "{role}"', endpoint="normalize_role")
        seniority = str(data.get("seniority", "")).lower().strip()
        if seniority in VALID_SENIORITY:
            return seniority
    except Exception:
        pass
    return _heuristic_seniority(role)


# ---------- interview-prep summarization ----------

_PREP_SYSTEM = (
    "You summarize candidate-reported interview experiences into a structured guide. "
    "Use ONLY the provided search results; do not fabricate. Respond ONLY with JSON using these keys:\n"
    '  "num_rounds": number\n'
    '  "rounds": [{"name": string, "description": string}]\n'
    '  "frequent_question_types": string[]\n'
    '  "topics_to_focus": [{"topic": string, "questions": string[]}]  // 3-4 real example questions per topic\n'
    '  "difficulty_notes": string\n'
    '  "sources": string[]   // URLs you relied on\n'
    "If the results are thin or conflicting, say so in difficulty_notes and keep lists short. "
    "Frame everything as candidate-reported, not official."
)


def summarize_prep(company: str, role: str, seniority: str, search_text: str, sources: list[str]) -> dict[str, Any]:
    user = (
        f"COMPANY: {company}\nROLE: {role} (seniority: {seniority})\n\n"
        f"SEARCH RESULTS (candidate-reported experiences):\n{search_text[:SEARCH_MAX_CHARS]}\n\n"
        f"KNOWN SOURCE URLS:\n{json.dumps(sources)}\n\n"
        "Return the JSON object now."
    )
    data = _chat_json(_PREP_SYSTEM, user, model=settings.chat_model, endpoint="interview_prep")
    rounds_raw = data.get("rounds")
    rounds: list[dict[str, str]] = []
    if isinstance(rounds_raw, list):
        for r in rounds_raw:
            if isinstance(r, dict):
                rounds.append(
                    {"name": str(r.get("name", "")).strip(), "description": str(r.get("description", "")).strip()}
                )
            elif isinstance(r, str) and r.strip():
                rounds.append({"name": r.strip(), "description": ""})
    # topics_to_focus is now [{topic, questions}]; handle both old string[] and new object[] shapes.
    topics_raw = data.get("topics_to_focus") or []
    topics: list[dict[str, Any]] = []
    for t in topics_raw:
        if isinstance(t, dict):
            topics.append({
                "topic": str(t.get("topic", "")).strip(),
                "questions": _as_str_list(t.get("questions")),
            })
        elif isinstance(t, str) and t.strip():
            topics.append({"topic": t.strip(), "questions": []})

    merged_sources = _as_str_list(data.get("sources")) or sources
    return {
        "num_rounds": _as_score(data.get("num_rounds")) if data.get("num_rounds") is not None else len(rounds),
        "rounds": rounds,
        "frequent_question_types": _as_str_list(data.get("frequent_question_types")),
        "topics_to_focus": topics,
        "difficulty_notes": str(data.get("difficulty_notes", "")).strip(),
        "sources": merged_sources,
    }


# ---------- cold-email drafting ----------

_COLD_EMAIL_SYSTEM = (
    "You write concise, personalized cold emails for a job seeker reaching out to a "
    "hiring contact. Respond ONLY with JSON: {\"subject\": string, \"body\": string}.\n"
    "Rules:\n"
    "- 110-160 words in the body; warm, specific, and respectful — not salesy or generic.\n"
    "- Open with a genuine, specific reason for reaching out (tie to the company/role).\n"
    "- Pull 1-2 concrete, relevant highlights from the résumé; do NOT invent anything.\n"
    "- End with a low-pressure ask (a brief chat or a pointer to the right person).\n"
    "- Address the contact by first name if provided. Sign off with a placeholder "
    "[Your Name]. No attachments, no links, no fake metrics."
)


def draft_cold_email(
    resume_text: str,
    company: str,
    contact_name: str = "",
    contact_role: str = "",
    jd_text: str = "",
) -> dict[str, str]:
    user = (
        f"COMPANY: {company}\n"
        f"CONTACT: {contact_name or '(unknown)'} — {contact_role or '(role unknown)'}\n\n"
        f"TARGET ROLE / JD (optional):\n{jd_text[:JD_MAX_CHARS] if jd_text else '(none provided)'}\n\n"
        f"RÉSUMÉ:\n{resume_text[:RESUME_MAX_CHARS]}\n\n"
        "Write the cold email JSON now."
    )
    data = _chat_json(_COLD_EMAIL_SYSTEM, user, endpoint="cold_email")
    return {
        "subject": str(data.get("subject", "")).strip() or f"Interest in opportunities at {company}",
        "body": str(data.get("body", "")).strip(),
    }

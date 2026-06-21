# Decision Log

A running record of meaningful choices made while building this project, with
the options considered and the tradeoffs behind each. Read this instead of
scrolling chat history.

**How to read this:** newest decisions at the bottom. Entries are never edited
or deleted. If a decision is reversed, the old entry's **Status** points to the
newer entry that replaced it.

---

<!--
  TEMPLATE — copy this block for each new decision.

## D-001 — <short title>

- **Date:** YYYY-MM-DD
- **Phase / area:**
- **Status:** Accepted   (or: Superseded by D-0XX)
- **Decision:** <one line>

**Options considered:**

| Option | Tradeoff |
| --- | --- |
| **<chosen>** ✅ | ... |
| <alternative> | ... |

**Why chosen:** <the actual reason>

---
-->

## D-001 — Hybrid resume↔JD scoring (embeddings + LLM-as-judge)

- **Date:** 2026-06-11
- **Phase / area:** Scoring core — `backend/app/services/scoring.py` (combine), `embeddings.py` (cosine + calibration), `llm.py` (`analyze_resume_jd`)
- **Status:** Accepted
- **Decision:** Score a resume against a JD with a blend of embedding cosine similarity and an LLM judgement — `final = 0.6 * embedding_score + 0.4 * llm_fit_score` — and surface all three numbers plus matched/missing skills and feedback.

**Options considered:**

| Option | Tradeoff |
| --- | --- |
| **Hybrid (both)** ✅ | Pays for two calls (mitigated by the SHA-256 result cache) and adds combine logic, **but** the two methods fail in opposite directions and cross-check each other. |
| Embedding cosine similarity only | Objective, deterministic/reproducible, cheap & cacheable, grounded in the text, no prompt-injection surface for the score. **But** opaque (a single number, can't say which skills matched/missed), needs calibration (OpenAI embeddings are anisotropic, ~0.6–0.9 band), blind to requirement semantics (5 yrs vs 1 yr, must-have vs nice-to-have), and gameable by keyword-stuffing the JD. |
| LLM-as-judge only | Nuanced (seniority, transferable skills, must-haves), explainable (produces matched/missing skills + feedback), rubric-steerable. **But** inconsistent run-to-run, ungrounded numbers (anchors to round numbers, drifts harsh/lenient), gameable by prompt injection (resume text enters the prompt), pricier/slower, unreliable self-reported confidence. |

**Why chosen:** The embedding score is an objective, stable, injection-resistant *anchor* that keeps the LLM's number honest; the LLM supplies the explainability (matched/missing skills, feedback) that an embedding can't. Surfacing all three sub-scores makes the result non-black-box — the product's core value prop, and the "don't trust the LLM's self-reported score, anchor it" interview story. Weights and the calibration band are configurable (`EMBEDDING_WEIGHT`, `SIM_FLOOR`, `SIM_CEIL`) so the blend can be tuned without code changes.

---

## D-002 — Cold-email outreach: Hunter.io contacts + Gmail draft-only

- **Date:** 2026-06-21
- **Phase / area:** Cold-email feature — `backend/app/services/hunter.py`, `google_oauth.py`, `gmail.py`, `llm.draft_cold_email`; routers `google_auth.py`, `cold_email.py`
- **Status:** Accepted
- **Decision:** Add a cold-email co-pilot: discover engineering-manager/senior-dev contacts at the target company via Hunter.io, draft a tailored email from the résumé with the LLM, and create it as a **Gmail draft** (never auto-send) over Google OAuth — running in Google's "Testing" publishing mode.

**Options considered:**

| Option | Tradeoff |
| --- | --- |
| **Hunter.io API + Gmail draft-only + OAuth Testing mode** ✅ | Compliant contact discovery (free tier; returns name/role/seniority/department to filter for EMs), human-in-the-loop drafts, least-privilege `gmail.compose` scope, no verification needed for owner + ≤100 testers. **But** needs a Hunter key + a Google Cloud OAuth client, and isn't usable by the arbitrary public without Google's restricted-scope verification. |
| Scrape personal emails (LinkedIn / company sites) | "Free" discovery, **but** violates site ToS, exposes us to privacy law (GDPR/CCPA), and is the mechanics of spam — rejected outright. |
| User provides the contact manually | Zero legal exposure, no extra key, **but** loses the auto-discovery the feature is for. |
| Auto-send the email | Fully automated, **but** spam risk, no human review, and needs a broader send scope — rejected; drafts keep a human in the loop. |
| Full Google restricted-scope verification | Lets anyone use it, **but** months-long security assessment — overkill for a portfolio demo. |

**Why chosen:** Keeps a genuinely useful job-seeker feature (find a relevant contact, draft a tailored note) while staying compliant and abuse-resistant — no scraping, no auto-send, least-privilege scope, and human review before anything leaves the outbox. Built in phases: Gmail OAuth + AI draft first, Hunter discovery second.

---

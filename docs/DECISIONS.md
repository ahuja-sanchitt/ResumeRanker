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

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
- **Status:** Superseded by D-007
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

## D-003 — "Lodestar" frontend: sidebar shell + shared analysis-session state, dependency-free routing

- **Date:** 2026-06-22
- **Phase / area:** Frontend redesign — `frontend/src/App.jsx`, new `AnalysisContext`, `Sidebar`/`Topbar`/`Stepper` components
- **Status:** Accepted
- **Decision:** Replace the two-tab UI with a single-page sidebar shell driving one shared 3-step flow (Upload → Match report → Outreach). Switch views with local state in `App`, and hold the cross-step session (résumé, JD, company, role, `/analyze` result, `/interview-prep` result, Gmail session) in a small React Context.

**Options considered:**

| Option | Tradeoff |
| --- | --- |
| **State-based view switch + React Context for session** ✅ | No new dependency; the three steps genuinely share one analysis session, so a context is the natural home and avoids prop-drilling or re-fetching. **But** we hand-roll view gating (Match/Outreach locked until an analysis exists). |
| Add `react-router` | Real URLs / deep-linking / back-button, **but** a routing dependency and route-loader plumbing for only three views that are really one wizard — overkill, and the steps share state that routing doesn't manage for us. |
| Keep top tabs, prop-drill state | Smallest diff, **but** doesn't match the requested sidebar/stepper design and prop-drilling résumé+results through three independent tabs is messy. |

**Why chosen:** The flow is a wizard over one shared session, not three independent pages — a context models that directly, and skipping a router keeps the bundle and mental model small for a 3-view portfolio app. Gating logic is trivial to hand-roll.

---

## D-004 — Match-report interview questions reuse the existing `/interview-prep` call

- **Date:** 2026-06-22
- **Phase / area:** Frontend `MatchReport.jsx`; reuses `api.getInterviewPrep` → backend `/interview-prep`
- **Status:** Accepted
- **Decision:** Populate the Match report's "Likely interview questions" section by firing a second call to the existing `/interview-prep` endpoint (keyed on the company + role entered on the upload step) and folding its rounds/question-types in, rather than teaching `/analyze` to emit questions.

**Options considered:**

| Option | Tradeoff |
| --- | --- |
| **Second call to existing `/interview-prep`** ✅ | Reuses a working, web-search-backed, *cached* (7-day TTL) endpoint that already returns cited questions/rounds; zero backend change. **But** a second, slower call per analysis (mitigated by its cache and by firing it concurrently with analyze). |
| Extend `/analyze`'s LLM schema to also return questions | One round-trip, questions tailored to the exact résumé↔JD gaps. **But** a backend prompt/schema change, no web-search grounding/citations, and it bloats the analyze response — a new decision for a section that already has a home. |
| Omit the section | Simplest, **but** drops a feature clearly in the mockup. |

**Why chosen:** The grounded, cited, cached interview-prep endpoint already exists and is exactly this data; reusing it is faster to ship and keeps the questions web-sourced. The extra latency is hidden by running it alongside `/analyze` and by the existing cache.

---

## D-005 — Library (Saved roles / Email templates) deferred to a later pass

- **Date:** 2026-06-22
- **Phase / area:** Frontend `Sidebar.jsx`
- **Status:** Accepted
- **Decision:** Show the sidebar's "Library" group (Saved roles, Email templates) as disabled "soon" items this pass; build no persistence for them yet.

**Options considered:**

| Option | Tradeoff |
| --- | --- |
| **Disabled placeholders now** ✅ | Ships the core Upload→Match→Outreach flow fast and keeps the sidebar visually complete, **but** the items aren't yet functional. |
| Build with `localStorage` | Real, usable persistence with no backend, **but** browser-local only (lost across devices) and extra UI for a non-core feature. |
| Build with backend storage | Durable + multi-device, **but** new endpoints, storage, and auth scope for what isn't the headline feature. |

**Why chosen:** The headline value is the analysis→outreach flow; the Library is secondary. Stubbing it keeps the design honest (the nav exists) without spending this pass on storage decisions that can be made later when the feature is actually built.

---

## D-006 — Per-IP rate limiting via slowapi, Redis-backed with in-memory fallback

- **Date:** 2026-06-23
- **Phase / area:** API hardening — new `backend/app/services/rate_limit.py`; decorators on `analyze.py`, `interview_prep.py`, `cold_email.py` (`/contacts`, `/cold-email/draft`, `/gmail/draft`), `google_auth.py` (`/auth/google/login`); `main.py` (exception handler + `SlowAPIMiddleware`)
- **Status:** Accepted
- **Decision:** Rate-limit the OpenAI/Hunter-calling endpoints per IP using `slowapi` (`/analyze` and `/cold-email/draft` at 10/min, `/interview-prep` at 10/min, `/contacts` at 15/min, `/gmail/draft` at 20/min, `/auth/google/login` at 20/min), with no blanket `default_limits` so `/health`, `/metrics`, and the cheap OAuth read endpoints stay unlimited. Storage degrades to in-memory if `REDIS_URL` isn't reachable, mirroring `cache.py`'s pattern. The limiter keys on the leftmost `X-Forwarded-For` hop, not `request.client.host`.

**Options considered:**

| Option | Tradeoff |
| --- | --- |
| **`slowapi` + per-route limits, Redis-or-memory storage, X-Forwarded-For-aware key** ✅ | Small, well-known dependency; limits survive restarts/scale-out when Upstash is configured and still work for local dev/demos when it isn't (same tradeoff already accepted for `cache.py`). **But** needs a custom key function — Render terminates TLS at a proxy, so the default `get_remote_address` (`request.client.host`) would bucket every visitor under one IP, defeating the limit. |
| Blanket `default_limits` on every route | Simpler (one line), **but** would also throttle `/health` and `/metrics` (scraped automatically by Render/Alloy) and OAuth status/logout calls that cost nothing — wrong shape for this app's actual cost surface. |
| Hand-rolled token bucket in `cache.py` | No new dependency, **but** reinvents sliding-window/fixed-window logic and edge cases (`limits` already solves) for no real benefit. |
| App-level API key instead of/in addition to rate limiting | Stops anonymous use entirely, **but** is a bigger scope change (key issuance/rotation) than what was asked; rate limiting alone caps the blast radius of the current no-auth design without that scope. |

**Why chosen:** The real risk is cost-based abuse of paid OpenAI/Hunter calls via the publicly-discoverable `/docs`, not unauthenticated access per se — so the fix should target exactly those routes, at limits generous enough for normal use but tight enough to bound a script hammering the API. Reusing the Redis-or-memory degradation pattern from `cache.py` keeps the codebase consistent rather than introducing a second philosophy for "is the optional cache up." The 429 handler returns the same `{"detail": ...}` shape as every other error in the API so the frontend's existing `parseError` needed no changes.

---

## D-007 — Three-signal scoring: embedding + skill coverage + LLM (supersedes D-001)

- **Date:** 2026-06-28
- **Phase / area:** Scoring core — `backend/app/services/scoring.py`, `embeddings.py`, `routers/analyze.py`, `config.py`; frontend `MatchReport.jsx`
- **Status:** Accepted
- **Decision:** Replace the two-signal blend from D-001 with three independent signals — `final = 0.2*embedding + 0.3*skill_coverage + 0.5*llm_fit` (weights normalized, env-tunable via `EMBEDDING_WEIGHT`/`SKILL_WEIGHT`/`LLM_WEIGHT`). `skill_coverage = matched / (matched + missing)` from the LLM's extracted skill labels. All three sub-scores plus matched/missing skills are surfaced in the breakdown.

**Options considered:**

| Option | Tradeoff |
| --- | --- |
| **Three signals (embedding + skill coverage + LLM)** ✅ | Each catches a distinct failure mode (see below); skill coverage fixes the cross-domain problem while embedding still guards against wholly-unrelated résumés. **But** three numbers to explain and a third weight to tune. |
| Keep D-001 (embedding 0.6 + LLM 0.4) | Simplest, already built. **But** embedding dominates and tanks cross-domain matches: a real résumé (e-commerce vocab) vs an adtech JD scored cosine ~0.41 → embedding 4/100 → final 30, despite strong skill overlap. The full-document embedding measures *domain vocabulary* proximity, not skill match. |
| Skill coverage + LLM only (the intermediate step we shipped first) | Removes the cross-domain penalty entirely; both signals are grounded in extracted skills. **But** drops the one signal that's immune to LLM hallucination — nothing catches a résumé that *reads* plausibly but shares no real content with the JD. |
| Re-weight D-001 to embedding 0.3 / LLM 0.7 | One-line change, softens the embedding penalty. **But** still lets a near-zero embedding drag down a genuine match, and adds no new grounded signal. |

**Why chosen:** The cross-domain failure (observed live on the owner's own résumé) proved full-document embedding similarity measures domain-vocabulary proximity, not skill fit — so it shouldn't be the dominant term. But removing it entirely loses the only injection-/hallucination-resistant anchor (the D-001 rationale still holds). Three signals keep that anchor at a low weight while skill coverage carries the grounded "requirements met" signal and the LLM carries nuance. The empirical "I found embedding similarity breaks on cross-domain résumés, diagnosed why, and redesigned the scoring" story is the project's strongest engineering talking point. Weights are env-tunable and normalized so they need not sum to 1.0.

---

## D-008 — Contact discovery: Apollo-only, real contacts, no fabricated fallback

- **Date:** 2026-06-28
- **Phase / area:** Cold-email outreach — `backend/app/routers/cold_email.py`, `services/apollo.py`; removed `services/fallback_contacts.py`; frontend `Outreach.jsx` empty state
- **Status:** Accepted
- **Decision:** `/contacts` returns only real contacts from Apollo.io (engineering leads/managers, India-filtered, capped at 6). When Apollo has no data for a company, return an empty list and let the UI show an honest empty state (LinkedIn link + manual entry). Do not fabricate contacts. Supersedes an intermediate implementation that filled any shortfall with randomly-generated names + guessed emails.

**Options considered:**

| Option | Tradeoff |
| --- | --- |
| **Apollo-only, empty state when none found** ✅ | Every contact shown is real with a verified email; honest. **But** the contact list is sometimes empty (Apollo's DB doesn't cover smaller companies), so the UI looks less "full." |
| Fill shortfall with generated contacts (the intermediate build) | UI always shows 6 rows, looks populated/demo-friendly. **But** the names are fake and the emails are *pattern guesses* (`first.last@domain`) that will bounce or hit the wrong real person — actively harmful if a user drafts and sends, and embarrassing if an interviewer notices. The low confidence % was the only (insufficient) signal they were fake. |
| Label generated contacts as "Sample — verify" | Keeps a full-looking UI while disclosing they're guesses. **But** still ships fabricated PII-shaped data and invites misuse; honesty-by-footnote is weak for something as consequential as emailing a stranger. |

**Why chosen:** A contact-discovery feature's entire value is that the contacts are *real*. Fabricating names and guessing email addresses undermines the feature's premise and creates real downside (bounced/misdirected cold emails, lost trust in a demo). An honest empty state with a LinkedIn fallback + manual entry is more defensible than a populated list of fakes — "I chose not to fabricate data even though it made the UI look emptier" is itself a good judgment story. Manual entry already existed, so the empty state is fully functional, not a dead end.

---

---

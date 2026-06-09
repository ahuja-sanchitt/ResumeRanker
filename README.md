# AI Resume Ranker + Interview Co-Pilot

A candidate-side tool that does two things:

1. **Résumé ↔ JD hybrid scoring** — upload a résumé PDF + paste a job description, get an *explainable* match score (objective embedding similarity **plus** nuanced LLM feedback), matched skills, missing skills, strengths, gaps, and concrete suggestions.
2. **Interview prep** — enter a company + role, get a live-web-search summary of that company's interview process (rounds, frequently-asked question types, topics to focus on) with source links.

## Why it's interesting (the engineering story)

This is deliberately **not** "send everything to an LLM and print the answer."

- **Hybrid, explainable scoring.** Asking an LLM for a raw 0–100 score is inconsistent and ungrounded — it'll give different numbers for the same input and can't justify them. So the score is a blend:
  - an **embedding cosine similarity** between résumé and JD — an *objective anchor* grounded purely in the text, and
  - an **LLM fit judgement** that adds nuance (seniority, must-have requirements).

  Both sub-scores are surfaced in the UI alongside the blended number, so the result is never a black box. The embedding score is the cross-check that keeps the LLM honest. (See `backend/app/services/scoring.py` and `embeddings.py`.)

- **Caching as a first-class concern.**
  - `/analyze` is keyed on a **SHA-256 fingerprint of `résumé bytes + normalized JD`** — identical submissions skip extraction, embeddings, and the LLM entirely.
  - `/interview-prep` caches per **`company + seniority bucket`** with a **TTL** (default 7 days), because interview info goes stale. The cache *self-warms*: the more company/level combos people look up, the faster and cheaper it gets.
  - One small interface (`backend/app/services/cache.py`) backs onto **Redis** when `REDIS_URL` is set, and transparently falls back to an in-memory dict otherwise — so local dev and demos never need a running server.

- **Bias & fairness (by design).** Automated résumé screeners can encode and amplify hiring bias. This tool is intentionally **candidate-side** — it helps *you* tailor your résumé and prepare, not gatekeep applicants. The interview-prep summaries are explicitly framed as **candidate-reported, cited, and possibly stale** — a study aid, not authority. If this were ever used in real hiring, you'd need bias audits, human review, and to treat the score as one signal among many.

## Architecture

```
React (Vite) on Vercel  ──HTTPS──▶  FastAPI on Render  ──▶  OpenAI (GPT + embeddings + web search)
                                          │
                                          └──▶  Redis (Upstash)   [fallback: in-memory dict]
```

| Layer | Tech | Host |
|---|---|---|
| Frontend | React (Vite) | Vercel |
| Backend | FastAPI | Render |
| LLM / embeddings / web search | OpenAI (single key) | — |
| Cache | Redis (Upstash), in-memory fallback | Upstash |

> Embeddings come from OpenAI rather than Claude because Anthropic has no embeddings endpoint, and a local model (`sentence-transformers`/`torch`) is too heavy for free hosting. One provider = one key.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| `GET`  | `/health` | — | status + active cache backend |
| `POST` | `/analyze` | multipart: `resume` (PDF file) + `jd` (text) | `final_score`, `embedding_score`, `llm_fit_score`, `matched_skills[]`, `missing_skills[]`, `strengths[]`, `gaps[]`, `feedback`, `cached` |
| `POST` | `/interview-prep` | JSON: `company_name`, `role`, `force_refresh?` | `seniority`, `num_rounds`, `rounds[]`, `frequent_question_types[]`, `topics_to_focus[]`, `difficulty_notes`, `sources[]`, `last_updated`, `cached` |

Interactive docs at `/docs` when the backend is running.

## Local development

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (use: source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
copy .env.example .env           # then set OPENAI_API_KEY (REDIS_URL optional)
uvicorn app.main:app --reload
```
Check http://127.0.0.1:8000/health and http://127.0.0.1:8000/docs.

### Frontend
```bash
cd frontend
npm install
copy .env.example .env           # VITE_API_BASE_URL defaults to http://127.0.0.1:8000
npm run dev
```
Open http://localhost:5173.

## Deployment

**Backend → Render.** New → Blueprint, point at this repo (uses `render.yaml`). Set secret env vars in the dashboard: `OPENAI_API_KEY`, optionally `REDIS_URL`, and `CORS_ORIGINS` = your Vercel URL. *Note:* the free tier sleeps after ~15 min idle (~30–60 s cold start) — ping the URL before a live demo, or use Railway to avoid sleeping.

**Cache → Upstash.** Create a free Redis database, copy its `rediss://…` connection URL into Render's `REDIS_URL`. No server to run. (Skip this and the app uses the in-memory fallback.)

**Frontend → Vercel.** Import the repo, set **Root Directory = `frontend`** (Vite is auto-detected), and add env var `VITE_API_BASE_URL` = your Render backend URL.

## Observability (token usage + Grafana)

Every OpenAI call's token usage is captured and exposed two ways:

- **Structured logs** — each call logs `endpoint`, `model`, `prompt_tokens`, `completion_tokens`, and `cached_tokens` (stdout, so Render captures it).
- **Prometheus metrics** at **`GET /metrics`**:
  - `openai_tokens_total{endpoint, model, kind}` — `kind` ∈ `prompt | completion | cached`
  - `openai_requests_total{endpoint, model}`
  - `app_cache_events_total{endpoint, result}` — `result` ∈ `hit | miss`
  - `http_request_seconds` — request-latency histogram

> **On prompt caching:** OpenAI caches a request's static prefix automatically, but only when that prefix is ≥1024 tokens — our system prompts are shorter, so it rarely triggers here. We log `cached_tokens` so it's visible when it does. The bigger lever is the app's own SHA-256 cache, which skips the whole call for exact repeats.

### Run Grafana locally

Needs Docker Desktop. With the backend running on the host:

```bash
cd monitoring
docker compose up
```
- **Grafana** → http://localhost:3000 (admin / admin) — the **"Resume Ranker — Observability"** dashboard is auto-provisioned (token rates, cache hit ratio, request rate, p95 latency).
- **Prometheus** → http://localhost:9090

(No Docker? You can still read raw metrics at `/metrics`, or point Grafana Cloud's free tier at the deployed `/metrics` URL.)

## Repo layout
```
backend/     FastAPI app (routers, services: pdf_extract, embeddings, llm, web_search, scoring, cache, metrics)
frontend/    Vite + React (Résumé Match + Interview Prep)
monitoring/  Prometheus + Grafana docker-compose, scrape config, provisioned dashboard
render.yaml  Render blueprint for the backend
```

## Notes / future work
- Confirm exact OpenAI model IDs and the Responses API `web_search` tool shape against current docs (configurable in `backend/app/config.py`).
- Scoring weights and the embedding-similarity calibration band are tunable via env (`EMBEDDING_WEIGHT`, `SIM_FLOOR`, `SIM_CEIL`).

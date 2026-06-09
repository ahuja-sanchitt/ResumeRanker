# AI Resume Ranker + Interview Co-Pilot

A candidate-side tool that does two things:

1. **Résumé ↔ JD hybrid scoring** — upload a résumé PDF + paste a job description, get an *explainable* match score (objective embedding similarity **plus** nuanced LLM feedback), matched skills, missing skills, and concrete suggestions.
2. **Interview prep** — enter a company + role, get a live-web-search summary of that company's interview process (rounds, frequently-asked question types, topics to focus on) with source links.

## Why it's interesting (engineering story)

- **Hybrid, explainable scoring** — not "ask the LLM for a number." An embedding cosine similarity gives an objective anchor; the LLM adds nuance. Both scores are surfaced so the result is never a black box.
- **Caching** — SHA-256 fingerprint of `résumé + JD` skips duplicate work; interview-prep results are cached per `company + seniority` with a TTL, so the cache self-warms over time.

## Stack

| Layer | Tech | Host |
|---|---|---|
| Frontend | React (Vite) | Vercel |
| Backend | FastAPI | Render |
| LLM / embeddings / web search | OpenAI | — |
| Cache | Redis (Upstash), in-memory fallback | Upstash |

## Local development (backend)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # then fill in OPENAI_API_KEY
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/health to confirm it's up, and http://127.0.0.1:8000/docs for the API.

> Status: scaffold + cache layer in place. Scoring and interview-prep endpoints are in progress.

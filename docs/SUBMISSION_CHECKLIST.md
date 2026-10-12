# Submission Checklist
## Run (Windows)
```
setup.bat            (once: venv, pip, npm install; creates .env files only if missing)
notepad .env         (set GROQ_API_KEY for AI + voice; leave empty for rules-only mode)
start_all.bat        (backend http://127.0.0.1:8000, frontend http://127.0.0.1:5173)
```
Manual: backend `python -m uvicorn app.main:app --reload` - frontend `cd frontend && npm install && npm run dev`.

## Deliverables
- [x] Backend (FastAPI): text/audio triage, history list, queue CRUD, PDF - plus new `GET /api/v1/triage` and audio limits in `/health`
- [x] Frontend (React + Vite): dashboard, text intake, voice upload + microphone, case detail, queue, PDF download, safety page
- [x] Docs: README, ARCHITECTURE, API_GUIDE, TESTING, DEMO_SCRIPT, SAFETY_AND_LIMITATIONS, AI_PIPELINE
- [x] Windows scripts; `.env.example` (backend and frontend) with placeholders only; `.gitignore` covers secrets/venv/db/node_modules

## Verification status (see docs/TESTING.md)
- [x] Browser journey 33/33 against a contract stub; frontend bundle builds with esbuild
- [x] 27 service tests run in the sandbox; your earlier 53-test baseline
- [ ] **You must run:** `python -m pytest -q` (expect 58), `npm run build`, and one full demo walk-through against the real backend with your key
- [ ] Live Groq with the new frontend (not run by me)

## Known limitations
Not clinically validated; no authentication; local SQLite; Hindi PDF rendering limited; transcripts can be wrong; Groq model IDs may change.

## Deployment
**Not deployed.** Local demo only. If you deploy: host the backend (any Python host, set `GROQ_API_KEY` in the host's secret store, add the frontend origin to
`CORS_ORIGINS`) and the static frontend (`npm run build`, upload `dist/`, set `VITE_API_BASE_URL` at build time). Add authentication first - the prototype has none.

## Before you zip/push
Confirm `.env` is absent from the archive and that `git status` shows no secrets.

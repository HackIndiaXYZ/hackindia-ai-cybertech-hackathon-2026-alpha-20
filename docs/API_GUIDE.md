# API Guide
Base URL (local): `http://127.0.0.1:8000` - interactive docs at `/docs`. Verified against the route definitions in `app/api/*`.

Every error uses one shape: `{"error": {"code": "...", "message": "...", "details": [{"field": "...", "message": "..."}]}}` (`details` only for 422).

| Method & path | Purpose | Success | Errors |
|---|---|---|---|
| GET `/health` | Liveness; `llm_configured`, `stt_configured`, `max_audio_mb`, `allowed_audio_formats`, `max_text_chars`. No secrets. | 200 | - |
| POST `/api/v1/triage/text` | JSON `{symptom_description (<=2000), context?: {age_group, duration}}` | 200 | 422 |
| POST `/api/v1/triage/audio` | multipart: `file`, optional form `age_group` | 200 (adds `transcript`, `transcription`) | 400 empty, 413 too large, 415 type, 422 unreadable / no speech, 429 rate limit, 502 provider, 503 STT not configured, 504 timeout |
| GET `/api/v1/triage?limit=20` | Recent results, newest first, **without input text** (`count`, `total`, `items`) | 200 | 422 (`limit` 1-100) |
| GET `/api/v1/triage/{request_id}` | One stored result | 200 | 404 `triage_not_found` |
| GET `/api/v1/patients?status=&urgency=` | Synthetic queue, most urgent first | 200 | 422 |
| GET `/api/v1/patients/{id}` | e.g. `P-0001` | 200 | 404 `patient_not_found` |
| POST `/api/v1/patients` | Pseudonym only; optional `triage_request_id` copies that case's urgency | 201 | 404, 422 |
| PATCH `/api/v1/patients/{id}` | `status`, `urgency`, `chief_complaint`, `age_group` (>=1 field) | 200 | 404, 422 |
| GET `/api/v1/reports/{request_id}/pdf` | PDF attachment built from the stored result | 200 | 404 `report_not_found` |

`urgency`: `emergency | urgent | routine | undetermined` (undetermined = could not assess, **not** low risk).
`mode`: `rules_only | rules_only_fallback | llm_groq_with_rules`.

## Examples
```
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/v1/triage/text -H "Content-Type: application/json" ^
  -d "{\"symptom_description\":\"Synthetic example: cough and mild fever for 2 days\",\"context\":{\"age_group\":\"adult\"}}"
curl -X POST http://127.0.0.1:8000/api/v1/triage/audio -F "file=@sample.wav;type=audio/wav" -F "age_group=adult"
curl http://127.0.0.1:8000/api/v1/triage?limit=5
curl -o report.pdf http://127.0.0.1:8000/api/v1/reports/<request_id>/pdf
```

## CORS
Allowed origins come from `CORS_ORIGINS` (default: `localhost` and `127.0.0.1` on ports 3000 and 5173). Add your deployed frontend origin there.
The frontend base URL is `VITE_API_BASE_URL` in `frontend/.env`. Multipart uploads must not set `Content-Type` manually.

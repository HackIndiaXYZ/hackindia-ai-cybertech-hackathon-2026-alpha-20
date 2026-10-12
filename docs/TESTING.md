# Testing - what was actually run
Be precise about provenance:

| Check | Result | Run by / where |
|---|---|---|
| Backend baseline `python -m pytest -q` (before this change) | **53 passed** | Reported by the project owner on their machine |
| Live Groq text triage, live audio transcription, PDF | Worked | Reported by the project owner (not re-run in the build sandbox) |
| Service-level tests in `tests/test_core_services.py` (27, incl. 1 new) | **27 passed** | Build sandbox, using a minimal pytest stand-in (real pytest unavailable offline) |
| New API tests (`test_health` +2, `test_text_triage` +2) | Written, **not executed** in the sandbox | Run `python -m pytest -q` - expected total **58** |
| Frontend bundle (esbuild, all imports resolved) | Built OK | Build sandbox |
| Browser end-to-end journey, 33 checks (Playwright/Chromium, 1280px and 375px) | **33/33 passed** | Build sandbox, against a **contract stub** (see below) |
| `npm run build` (Vite) and a run against the **real** FastAPI server | **Not run** in the sandbox (no network) | You: see "Do this before the demo" |
| Live Groq calls from the new frontend | **Not run** | You |

## The contract stub
FastAPI could not be installed in the sandbox, so the browser checks ran against a throwaway Python server that implements the same routes and JSON
shapes using the project's **real** service modules (rules engine, SQLite storage, audio validation, PDF generator). The speech-to-text call was mocked
(fixed transcript / error modes). It proves the UI works with the documented contract and real service logic; it does not prove the real FastAPI wiring.
The stub is not part of the deliverable.

## Browser checks covered
Connection status; empty-state dashboard; seeded queue counts; text validation; emergency banner and badge text; honest rules-only labelling;
request ID; **PDF download is a real PDF**; negation shown as "absent"; cases list/detail; add-to-queue (urgency copied); status change; unknown case ID;
client rejection of `.exe` and oversize audio; backend rejection of fake audio; STT not configured / provider failure messages (no fake transcript);
successful transcript + triage; **microphone recording** (Chromium fake device, real `audio/webm` multipart upload accepted by the real validator);
backend-offline state; no horizontal overflow at 375px on all pages; no unexpected console errors.

## Do this before the demo
```
setup.bat
python -m pytest -q          (expect 58 passed; run inside the venv)
cd frontend && npm run build (expect a dist/ folder, no errors)
start_all.bat                 (then walk through docs/DEMO_SCRIPT.md once)
```
Not covered: real-browser testing beyond Chromium, screen-reader testing, load/security testing, clinical validation.

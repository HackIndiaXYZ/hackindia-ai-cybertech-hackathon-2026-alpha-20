# AI Pipeline
1. **Audio only:** validate size/extension/MIME/magic bytes (WAV also parsed) → in-memory upload to Groq Whisper
   (`/audio/transcriptions`, model `whisper-large-v3-turbo`). Client filenames are never used. Failure → explicit error.
2. **Rules** (`triage_rules.py`): keyword rules with negation scope (5 words, ended by commas/"but"). Ambiguous or conflicting
   negation is treated as *present*. Output: symptoms, absent symptoms, urgency, explanation.
3. **LLM (optional)** (`ai_service.py`, Groq chat completions, JSON mode): summary, symptoms with `evidence_quote`,
   follow-up gaps. Symptoms whose quote is not in the user's text are **discarded**. The report text is delimited and
   treated as data (prompt-injection mitigation). The LLM may only **raise** urgency, never lower it.
4. **Failure handling:** missing key, timeout, 429, auth, malformed JSON → rules-only result labelled `rules_only_fallback`.
5. Result is stored in SQLite; PDF reports are rendered from the stored record.
No dosages, prescriptions or treatment plans are produced.

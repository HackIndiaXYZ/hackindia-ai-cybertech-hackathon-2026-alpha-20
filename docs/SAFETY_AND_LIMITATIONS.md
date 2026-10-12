# Safety and Limitations
**Intended use:** a hackathon demonstration of triage *support* and clinical *documentation* for rural clinics. **Not** a medical device,
not clinically validated, not a diagnosis, no medication/dose/treatment output. A clinician must review every case.
No accuracy, sensitivity or specificity numbers exist and none are claimed.

## Safety design
- **Rules decide urgency.** Deterministic keyword rules with negation handling ("no chest pain" is not chest pain). Unclear or conflicting
  negation is treated as *present*; "mild/slight" never downgrades a warning sign.
- **The AI can only raise urgency, never lower it.** Its symptoms must quote the user's text, otherwise they are discarded; its output is
  validated as untrusted JSON; the report text is delimited as data (prompt-injection mitigation).
- **Emergency advice is deterministic** and shown before/independently of any AI call; the UI shows a prominent banner and a persistent bar.
- Failures (no key, timeout, rate limit, bad output) fall back to a *labelled* rules-only result. A failed transcription is never replaced by fake speech.
- `undetermined` is shown as "could not assess", never as low risk.

## Privacy and security
No secrets in code; `.env` is git-ignored; inputs validated; uploads bounded and checked by signature; parameterised SQL; generic 500 errors.
**No authentication, encryption or retention policy** - do not expose publicly and do not use real patient data. With a key configured, report
text and audio go to Groq. Free text may contain identifiers, so users are told not to enter them.

## Known limitations
- Rules are preliminary, English plus a few Hindi phrases; they need clinician review. List-style negation ("no fever, cough, or chest pain") over-triages by design.
- Whisper transcripts can be wrong (accent, noise, medical terms); the UI says so.
- PDFs: ReportLab does not shape Devanagari; Hindi may render wrongly and unsupported glyphs become `?`.
- The queue and results live in a local SQLite file; the "queue" is synthetic demonstration data.
- Groq's model catalog changes (the earlier Llama defaults were deprecated 2026-08-16); verify `GROQ_MODEL` before presenting.

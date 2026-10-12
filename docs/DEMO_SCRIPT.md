# Demo Script (3-5 minutes, synthetic data only)
Prep: `start_all.bat`; confirm the header shows **Backend connected** and "AI on - Voice on" (add `GROQ_API_KEY` to `.env` first). Have a short fictional
audio clip ready (e.g. someone saying "I have had a cough and a mild fever for two days" - or the chest-pain example for the emergency path).

1. **Dashboard (30 s)** - "Everything here is live from the backend; the queue is synthetic." Point at the status chip and the safety bar.
2. **Text triage (60 s)** - New triage > Text > *Example 2* ("no chest pain, but headache and dizzy"). Show: negated symptom under *Reported as absent*,
   rule-based urgency, summary label (AI vs rules), uncertainty list. Say: "The rules decide urgency; the AI can only raise it."
3. **Emergency path (30 s)** - *Example 3* (chest pain, hard to breathe). Show the red banner appearing immediately with emergency guidance.
4. **Voice (60 s)** - Voice tab > record or upload the clip > show upload progress, then the **machine transcript warning** and the structured result.
5. **Cases and PDF (45 s)** - Open the case, **Download PDF report**, open the PDF. Optionally *Add to queue* (pseudonym) and show it in Clinic queue.
6. **Safety (30 s)** - Safety & about: not a diagnosis, not validated, `UNDETERMINED` is not low risk, no real data.

Fallbacks: if the AI/voice service fails, the UI says exactly why; text triage still works in labelled rules-only mode, and the dashboard,
queue and PDFs need no internet.

"""Orchestrates rules + optional LLM + storage into one triage record.

Urgency policy: the transparent rules decide; the LLM may only raise urgency.
Rules-only output is always labelled as such and never presented as LLM output.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.services import ai_service, triage_rules as rules
from app.services.storage import Database, now_iso

DISCLAIMER = (
    "Hackathon prototype for triage SUPPORT and documentation only. It is not a diagnosis, is not "
    "clinically validated, and does not replace a qualified healthcare professional. If you think "
    "this is an emergency, call your local emergency number immediately."
)


def _rules_summary(symptoms: List[str], negated: List[str]) -> str:
    if symptoms:
        s = "Rule-based extraction (no AI used) found reported: " + ", ".join(symptoms) + "."
    else:
        s = "Rule-based extraction (no AI used) found no symptoms covered by its limited keyword list."
    if negated:
        s += " Reported as absent: " + ", ".join(negated) + "."
    return s


def run_triage(text: str, settings: Any, db: Database, context: Optional[Dict[str, Any]] = None,
               source: str = "text", transcript_info: Optional[Dict[str, Any]] = None,
               ai_transport: Optional[ai_service.Transport] = None) -> Dict[str, Any]:
    ctx = {k: v for k, v in (context or {}).items() if v not in (None, "", "unspecified")}
    r = rules.assess(text, getattr(settings, "emergency_number_hint", "112"))

    uncertainties = list(r.uncertainties)
    uncertainties += [g for g in rules.missing_information(text)
                      if not (ctx.get("age_group") and g.startswith("Age"))
                      and not (ctx.get("duration") and g.startswith("Duration"))]

    urgency, explanation = r.urgency, r.explanation
    symptoms = list(r.reported_symptoms)
    summary, summary_source = _rules_summary(r.reported_symptoms, r.negated_symptoms), "rules"
    ai_used, ai_status, ai_model, mode = False, "not_configured", None, "rules_only"
    ai_symptoms: List[Dict[str, str]] = []

    if getattr(settings, "llm_configured", False):
        try:
            ai = ai_service.analyze_symptoms(text, settings, ctx, ai_transport)
            ai_used, ai_status, ai_model, mode = True, "ok", ai.model, "llm_groq_with_rules"
            summary, summary_source = ai.summary, "ai"
            ai_symptoms = ai.symptoms
            uncertainties += [m for m in ai.missing_information if m not in uncertainties]
            if ai.dropped_ungrounded:
                uncertainties.append(f"{ai.dropped_ungrounded} AI-suggested symptom(s) were discarded because they "
                                     "were not found in the reported text.")
            if ai.suggested_urgency and rules.URGENCY_RANK[ai.suggested_urgency] > rules.URGENCY_RANK[urgency]:
                explanation += (f" The AI assistant suggested a higher level ({ai.suggested_urgency.upper()}); "
                                "the higher level was used to be conservative.")
                urgency = ai.suggested_urgency
        except ai_service.AIServiceError as exc:
            ai_status, mode = f"failed:{exc.code}", "rules_only_fallback"
            explanation += " (AI assistance was unavailable, so only the rules-based assessment was used.)"
    else:
        ai_status = "not_configured"

    advice = r.emergency_advice
    if urgency == rules.EMERGENCY and not advice:
        advice = rules.EMERGENCY_ADVICE.format(num=getattr(settings, "emergency_number_hint", "112"))

    record: Dict[str, Any] = {
        "request_id": uuid.uuid4().hex,
        "created_at": now_iso(),
        "source": source,
        "input_text": text,
        "context": ctx,
        "reported_symptoms": symptoms,
        "ai_extracted_symptoms": ai_symptoms,
        "negated_symptoms": r.negated_symptoms,
        "summary": summary,
        "summary_source": summary_source,
        "uncertainties": uncertainties,
        "urgency": urgency,
        "explanation": explanation,
        "emergency_advice": advice,
        "ai_used": ai_used,
        "mode": mode,
        "ai_status": ai_status,
        "ai_model": ai_model,
        "transcription": transcript_info,
        "disclaimer": DISCLAIMER,
    }
    db.save_triage(record)
    return record

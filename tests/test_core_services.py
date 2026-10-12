"""Pure-Python service tests (no FastAPI needed): rules, AI parsing/errors, STT, storage, PDF."""
import json
import os
from types import SimpleNamespace as NS

import pytest

from app.services import ai_service, transcription_service as stt, triage_rules as rules
from app.services.report_service import generate_pdf
from app.services.storage import Database
from app.services.triage_pipeline import run_triage


def S(key="", **kw):
    base = dict(groq_api_key=key, groq_model="openai/gpt-oss-120b", groq_whisper_model="whisper-large-v3-turbo",
                groq_base_url="https://api.groq.com/openai/v1", default_stt_provider="groq",
                ai_timeout_seconds=5, emergency_number_hint="112", llm_configured=bool(key))
    base.update(kw)
    return NS(**base)


def mkdb(tmp_path):
    db = Database(str(tmp_path / "t.db")); db.init(); return db


def chat(content):
    return lambda *a: (200, json.dumps({"choices": [{"message": {"content": content}}]}))


GOOD = json.dumps({"summary": "Person reports a cough.", "symptoms": [{"name": "cough", "evidence_quote": "a cough"},
                   {"name": "invented", "evidence_quote": "not in text"}],
                   "missing_information": ["How long?"], "suggested_urgency": "routine"})


# ---- rules / safety ----
def test_chest_pain_is_emergency():
    r = rules.assess("I have chest pain")
    assert r.urgency == "emergency" and "112" in r.emergency_advice

def test_negation_not_treated_as_present():
    r = rules.assess("I have no chest pain")
    assert r.urgency != "emergency" and "chest pain or pressure" not in r.reported_symptoms
    assert "chest pain or pressure" in r.negated_symptoms

def test_negation_then_other_symptom():
    r = rules.assess("no chest pain but I have a cough")
    assert r.urgency == "routine" and r.reported_symptoms == ["cough"]

def test_ambiguous_negation_is_conservative():
    r = rules.assess("no fever and chest pain")
    assert r.urgency == "emergency" and r.uncertainties

def test_conflict_treated_as_present():
    r = rules.assess("I had no chest pain earlier, now I have chest pain")
    assert r.urgency == "emergency" and any("Conflicting" in u for u in r.uncertainties)

def test_comma_ends_negation_scope():
    r = rules.assess("denies shortness of breath, has sore throat")
    assert r.reported_symptoms == ["sore throat"]

def test_mild_wording_does_not_downgrade_emergency():
    assert rules.assess("mild chest pain").urgency == "emergency"

def test_urgent_and_routine_levels():
    assert rules.assess("severe stomach pain").urgency == "urgent"
    assert rules.assess("runny nose and sneezing").urgency == "routine"

def test_unknown_and_empty_are_undetermined_not_routine():
    assert rules.assess("I feel strange").urgency == "undetermined"
    assert rules.assess("   ").urgency == "undetermined"
    assert rules.assess("??").urgency == "undetermined"

def test_hindi_chest_pain_and_ambiguous_negation():
    assert rules.assess("मुझे सीने में दर्द है").urgency == "emergency"
    assert rules.assess("मुझे सीने में दर्द नहीं है").urgency == "emergency"

def test_no_treatment_or_dosage_in_output():
    r = rules.assess("fever and cough")
    text = (r.explanation + " ".join(r.uncertainties)).lower()
    assert "mg" not in text and "take " not in text


# ---- AI service ----
def test_ai_missing_key():
    with pytest.raises(ai_service.AIServiceError) as e:
        ai_service.analyze_symptoms("a cough", S(""))
    assert e.value.code == "not_configured"

def test_ai_grounding_drops_invented_symptoms():
    res = ai_service.analyze_symptoms("I have a cough", S("k"), transport=chat(GOOD))
    assert [s["name"] for s in res.symptoms] == ["cough"] and res.dropped_ungrounded == 1

def test_ai_malformed_variants():
    for bad in ["not json", "[]", json.dumps({"summary": ""}), json.dumps({"summary": "x", "symptoms": "no"}), ""]:
        with pytest.raises(ai_service.AIServiceError) as e:
            ai_service.analyze_symptoms("a cough", S("k"), transport=chat(bad))
        assert e.value.code == "malformed_output"

def test_ai_code_fenced_json_accepted():
    res = ai_service.analyze_symptoms("a cough", S("k"), transport=chat("```json\n" + GOOD + "\n```"))
    assert res.summary

def test_ai_http_errors_and_timeout():
    cases = {429: "rate_limited", 401: "auth_failed", 500: "provider_error"}
    for status, code in cases.items():
        with pytest.raises(ai_service.AIServiceError) as e:
            ai_service.analyze_symptoms("a cough", S("k"), transport=lambda *a, s=status: (s, "{}"))
        assert e.value.code == code
    def boom(*a): raise TimeoutError()
    with pytest.raises(ai_service.AIServiceError) as e:
        ai_service.analyze_symptoms("a cough", S("k"), transport=boom)
    assert e.value.code == "timeout"

def test_ai_request_shape_and_no_key_in_body():
    seen = {}
    def t(url, headers, payload, timeout):
        seen.update(url=url, headers=headers, payload=payload)
        return 200, json.dumps({"choices": [{"message": {"content": GOOD}}]})
    ai_service.analyze_symptoms("a cough", S("secret-key"), transport=t)
    assert seen["url"].endswith("/chat/completions") and seen["payload"]["model"] == "openai/gpt-oss-120b"
    assert "secret-key" not in json.dumps(seen["payload"])


# ---- pipeline ----
def test_pipeline_rules_only_without_key(tmp_path):
    rec = run_triage("I have a cough", S(""), mkdb(tmp_path))
    assert rec["mode"] == "rules_only" and rec["ai_used"] is False and rec["summary_source"] == "rules"

def test_pipeline_ai_success_and_escalation(tmp_path):
    out = json.dumps({"summary": "Cough reported.", "symptoms": [], "missing_information": [], "suggested_urgency": "urgent"})
    rec = run_triage("I have a cough", S("k"), mkdb(tmp_path), ai_transport=chat(out))
    assert rec["ai_used"] and rec["urgency"] == "urgent" and rec["mode"] == "llm_groq_with_rules"

def test_pipeline_ai_cannot_downgrade(tmp_path):
    out = json.dumps({"summary": "ok", "symptoms": [], "missing_information": [], "suggested_urgency": "routine"})
    rec = run_triage("I have chest pain", S("k"), mkdb(tmp_path), ai_transport=chat(out))
    assert rec["urgency"] == "emergency"

def test_pipeline_fallback_on_failure_is_labelled(tmp_path):
    rec = run_triage("I have chest pain", S("k"), mkdb(tmp_path), ai_transport=lambda *a: (429, "{}"))
    assert rec["mode"] == "rules_only_fallback" and rec["ai_used"] is False
    assert rec["ai_status"] == "failed:rate_limited" and rec["urgency"] == "emergency"


# ---- audio / STT ----
def wav(frames=800):
    import io, wave
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000); w.writeframes(b"\0\0" * frames)
    return b.getvalue()

def test_audio_validation():
    assert stt.validate_audio("a.wav", "audio/wav", wav(), 15) == "wav"
    for args, code in [(("a.wav", "audio/wav", b"", 15), "empty_file"),
                       (("a.exe", "audio/wav", wav(), 15), "unsupported_extension"),
                       (("a.wav", "text/plain", wav(), 15), "unsupported_mime"),
                       (("a.wav", "audio/wav", b"not audio at all", 15), "unreadable_audio"),
                       (("a.wav", "audio/wav", wav(), 0.0001), "file_too_large"),
                       (("a.mp3", "audio/mpeg", b"RIFFxxxxWAVE", 15), "unreadable_audio")]:
        with pytest.raises(stt.AudioValidationError) as e:
            stt.validate_audio(*args)
        assert e.value.code == code

def test_path_traversal_filename_uses_only_extension():
    assert stt.validate_audio("../../etc/passwd.wav", "audio/wav", wav(), 15) == "wav"

def test_transcribe_success_and_failures():
    ok = lambda *a: (200, json.dumps({"text": " I have a cough "}))
    assert stt.transcribe(b"x", "wav", S("k"), ok) == "I have a cough"
    for status, body, code in [(429, "{}", "rate_limited"), (500, "{}", "provider_error"),
                               (200, "nope", "malformed_response"), (200, json.dumps({"text": "  "}), "empty_transcript")]:
        with pytest.raises(stt.TranscriptionError) as e:
            stt.transcribe(b"x", "wav", S("k"), lambda *a, s=status, b=body: (s, b))
        assert e.value.code == code
    with pytest.raises(stt.TranscriptionError) as e:
        stt.transcribe(b"x", "wav", S(""), ok)
    assert e.value.code == "not_configured"


# ---- storage / PDF ----
def test_patients_storage(tmp_path):
    db = mkdb(tmp_path)
    ps = db.list_patients()
    assert len(ps) == 5 and ps[0]["urgency"] == "emergency" and ps[0]["id"].startswith("P-")
    assert db.get_patient("P-0002")["display_name"].startswith("Demo")
    assert db.get_patient("P-9999") is None and db.get_patient("../etc") is None
    new = db.create_patient("Demo Patient F", "adult", "Cough")
    assert db.update_patient(new["id"], {"status": "seen"})["status"] == "seen"
    assert db.update_patient("P-9999", {"status": "seen"}) is None
    db.init()  # idempotent, no duplicate seeding
    assert len(db.list_patients()) == 6

def test_pdf_from_stored_record(tmp_path):
    db = mkdb(tmp_path)
    rec = run_triage("I have chest pain & a <cough> मुझे बुखार है", S(""), db)
    pdf = generate_pdf(db.get_triage(rec["request_id"]))
    assert pdf.startswith(b"%PDF") and len(pdf) > 1500
    assert db.get_triage("0" * 32) is None


def test_list_triage_summary_is_minimal_and_ordered(tmp_path):
    db = mkdb(tmp_path)
    assert db.list_triage() == [] and db.count_triage() == 0
    a = run_triage("sore throat", S(""), db)["request_id"]
    b = run_triage("chest pain", S(""), db)["request_id"]
    items = db.list_triage(10)
    assert [i["request_id"] for i in items] == [b, a] and "input_text" not in items[0]
    assert len(db.list_triage(1)) == 1 and db.count_triage() == 2

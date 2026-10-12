import json
from tests.conftest import groq_chat_body

URL = "/api/v1/triage/text"
GOOD = json.dumps({"summary": "Cough reported.", "symptoms": [{"name": "cough", "evidence_quote": "cough"}],
                   "missing_information": ["Duration?"], "suggested_urgency": "routine"})

def test_valid_text_without_key_is_rules_only(client):
    r = client.post(URL, json={"symptom_description": "I have a cough and runny nose for 2 days"})
    assert r.status_code == 200
    b = r.json()
    assert b["mode"] == "rules_only" and b["ai_used"] is False and b["urgency"] == "routine"
    assert b["request_id"] and b["disclaimer"] and b["summary_source"] == "rules"

def test_emergency_has_advice(client):
    b = client.post(URL, json={"symptom_description": "chest pain and trouble breathing"}).json()
    assert b["urgency"] == "emergency" and "emergency" in b["emergency_advice"].lower()

def test_negation(client):
    b = client.post(URL, json={"symptom_description": "I have no chest pain"}).json()
    assert b["urgency"] != "emergency" and b["reported_symptoms"] == []

def test_invalid_inputs_return_422_with_error_format(client):
    for payload in [{}, {"symptom_description": ""}, {"symptom_description": "   "}, {"symptom_description": "??"},
                    {"symptom_description": "x" * 2001}, {"symptom_description": 5},
                    {"symptom_description": "cough", "context": {"age_group": "alien"}}]:
        r = client.post(URL, json=payload)
        assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"

def test_malformed_json_body(client):
    r = client.post(URL, content="{bad", headers={"Content-Type": "application/json"})
    assert r.status_code == 422

def test_ai_success(make_client):
    c, app = make_client(groq_api_key="test-key")
    app.state.ai_transport = lambda *a: (200, groq_chat_body(GOOD))
    b = c.post(URL, json={"symptom_description": "I have a cough"}).json()
    assert b["ai_used"] is True and b["mode"] == "llm_groq_with_rules" and b["summary_source"] == "ai"

def test_ai_malformed_timeout_ratelimit_fall_back_safely(make_client):
    c, app = make_client(groq_api_key="test-key")
    def timeout(*a): raise TimeoutError()
    for transport, code in [(lambda *a: (200, groq_chat_body("not json")), "malformed_output"),
                            (timeout, "timeout"), (lambda *a: (429, "{}"), "rate_limited")]:
        app.state.ai_transport = transport
        r = c.post(URL, json={"symptom_description": "chest pain"})
        b = r.json()
        assert r.status_code == 200 and b["mode"] == "rules_only_fallback" and b["ai_used"] is False
        assert b["ai_status"] == f"failed:{code}" and b["urgency"] == "emergency"

def test_get_stored_result(client):
    rid = client.post(URL, json={"symptom_description": "sore throat"}).json()["request_id"]
    assert client.get(f"/api/v1/triage/{rid}").status_code == 200
    assert client.get("/api/v1/triage/" + "0" * 32).status_code == 404

def test_triage_history_empty_then_newest_first(client):
    b = client.get("/api/v1/triage").json()
    assert b == {"count": 0, "total": 0, "items": []}
    a = client.post(URL, json={"symptom_description": "sore throat"}).json()["request_id"]
    c = client.post(URL, json={"symptom_description": "chest pain"}).json()["request_id"]
    b = client.get("/api/v1/triage").json()
    assert b["total"] == 2 and [i["request_id"] for i in b["items"]] == [c, a]
    assert "input_text" not in b["items"][0] and b["items"][0]["urgency"] == "emergency"
    assert len(client.get("/api/v1/triage", params={"limit": 1}).json()["items"]) == 1

def test_triage_history_limit_validation(client):
    for lim in (0, 101, "x"):
        assert client.get("/api/v1/triage", params={"limit": lim}).status_code == 422

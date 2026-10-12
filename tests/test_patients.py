def test_list_and_order(client):
    b = client.get("/api/v1/patients").json()
    assert b["count"] == 5 and b["patients"][0]["urgency"] == "emergency"
    assert "synthetic" in b["synthetic_data_notice"].lower()

def test_filters(client):
    b = client.get("/api/v1/patients", params={"status": "waiting"}).json()
    assert all(p["status"] == "waiting" for p in b["patients"])
    assert client.get("/api/v1/patients", params={"status": "bogus"}).status_code == 422

def test_get_and_unknown(client):
    assert client.get("/api/v1/patients/P-0001").status_code == 200
    r = client.get("/api/v1/patients/P-9999")
    assert r.status_code == 404 and r.json()["error"]["code"] == "patient_not_found"
    assert client.get("/api/v1/patients/abc").status_code == 404

def test_create_and_patch(client):
    r = client.post("/api/v1/patients", json={"display_name": "Demo Patient Z", "chief_complaint": "Cough"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert client.patch(f"/api/v1/patients/{pid}", json={"status": "seen"}).json()["status"] == "seen"
    assert client.patch(f"/api/v1/patients/{pid}", json={}).status_code == 422
    assert client.patch("/api/v1/patients/P-9999", json={"status": "seen"}).status_code == 404

def test_create_from_triage_result_uses_its_urgency(client):
    rid = client.post("/api/v1/triage/text", json={"symptom_description": "chest pain"}).json()["request_id"]
    p = client.post("/api/v1/patients", json={"display_name": "Demo Q", "chief_complaint": "Chest pain",
                                             "triage_request_id": rid}).json()
    assert p["urgency"] == "emergency"
    assert client.post("/api/v1/patients", json={"display_name": "D", "chief_complaint": "Cough",
                                                "triage_request_id": "0" * 32}).status_code == 404

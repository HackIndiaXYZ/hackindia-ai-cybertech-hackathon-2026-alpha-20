def test_pdf_download(client):
    rid = client.post("/api/v1/triage/text", json={"symptom_description": "cough and fever"}).json()["request_id"]
    r = client.get(f"/api/v1/reports/{rid}/pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"] and r.content.startswith(b"%PDF")

def test_unknown_and_malformed_report_ids(client):
    for rid in ["0" * 32, "abc", "..%2F..%2Fetc"]:
        r = client.get(f"/api/v1/reports/{rid}/pdf")
        assert r.status_code == 404 and r.json()["error"]["code"] in ("report_not_found", "http_error")

def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["llm_configured"] is False and body["stt_configured"] is False
    assert "key" not in str(body).lower().replace("llm_configured", "")

def test_startup_without_credentials_and_docs(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200

def test_unknown_route_uses_error_format(client):
    r = client.get("/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "http_error"

def test_cors_allows_configured_origin(client):
    r = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
    r = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers

def test_health_exposes_audio_limits(client):
    b = client.get("/health").json()
    assert b["max_audio_mb"] > 0 and "wav" in b["allowed_audio_formats"] and b["max_text_chars"] == 2000

def test_default_cors_includes_127_origin(client):
    r = client.get("/health", headers={"Origin": "http://127.0.0.1:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

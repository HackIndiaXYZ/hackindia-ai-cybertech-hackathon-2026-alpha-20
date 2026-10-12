import json
from tests.conftest import wav_bytes

URL = "/api/v1/triage/audio"

def up(data=None, name="a.wav", ctype="audio/wav"):
    return {"file": (name, wav_bytes() if data is None else data, ctype)}

def test_audio_success_with_mocked_stt(make_client):
    c, app = make_client(groq_api_key="test-key")
    app.state.stt_transport = lambda *a: (200, json.dumps({"text": "I have chest pain"}))
    app.state.ai_transport = lambda *a: (429, "{}")  # AI down: rules still run on the real transcript
    r = c.post(URL, files=up())
    b = r.json()
    assert r.status_code == 200 and b["transcript"] == "I have chest pain" and b["source"] == "audio"
    assert b["transcription"]["status"] == "ok" and b["urgency"] == "emergency"

def test_audio_without_key_is_clear_error_not_fake_transcript(client):
    r = client.post(URL, files=up())
    assert r.status_code == 503 and r.json()["error"]["code"] == "transcription_not_configured"

def test_audio_transcription_failures(make_client):
    c, app = make_client(groq_api_key="test-key")
    for status, body, http in [(429, "{}", 429), (500, "{}", 502), (200, json.dumps({"text": ""}), 422)]:
        app.state.stt_transport = lambda *a, s=status, b=body: (s, b)
        assert c.post(URL, files=up()).status_code == http
    def boom(*a): raise TimeoutError()
    app.state.stt_transport = boom
    assert c.post(URL, files=up()).status_code == 504

def test_audio_validation_errors(make_client):
    c, _ = make_client(groq_api_key="test-key", max_audio_mb=0.001)
    assert c.post(URL, files=up(b"")).status_code == 400
    assert c.post(URL, files=up(b"x" * 5000)).status_code == 413
    c2, _ = make_client(groq_api_key="test-key")
    assert c2.post(URL, files=up(name="a.exe")).status_code == 415
    assert c2.post(URL, files=up(ctype="text/plain")).status_code == 415
    assert c2.post(URL, files=up(b"not really audio")).status_code == 422
    assert c2.post(URL).status_code == 422

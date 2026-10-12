import os
import tempfile

# Must be set BEFORE app.main is imported (it builds a default app at import time).
os.environ["GROQ_API_KEY"] = ""
os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(), "import_default.db")

import json
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def make_client(tmp_path):
    def _make(**overrides):
        s = Settings(_env_file=None, database_path=str(tmp_path / "t.db"), **overrides)
        app = create_app(s)
        return TestClient(app, raise_server_exceptions=False), app
    return _make


@pytest.fixture
def client(make_client):
    return make_client(groq_api_key="")[0]


def groq_chat_body(content):
    return json.dumps({"choices": [{"message": {"content": content}}]})


def wav_bytes(frames=800):
    import io, wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
        w.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()

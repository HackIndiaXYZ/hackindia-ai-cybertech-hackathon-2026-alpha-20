"""Audio validation and speech-to-text (Groq Whisper, OpenAI-compatible endpoint).

Audio is handled fully in memory (no temp files, client filenames are never used).
A failed transcription is NEVER replaced with fake patient speech.
"""
from __future__ import annotations

import io
import wave
from typing import Any, Callable, Dict, Optional, Tuple

ALLOWED_EXTENSIONS = {"flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"}
ALLOWED_MIME_PREFIXES = ("audio/",)
ALLOWED_MIME_EXTRA = {"video/mp4", "video/webm", "application/ogg", "application/octet-stream"}
MIME_FOR_EXT = {"flac": "audio/flac", "mp3": "audio/mpeg", "mpeg": "audio/mpeg", "mpga": "audio/mpeg",
                "mp4": "audio/mp4", "m4a": "audio/mp4", "ogg": "audio/ogg", "wav": "audio/wav", "webm": "audio/webm"}

# transport(url, headers, data, files, timeout) -> (status, body_text)
STTTransport = Callable[[str, Dict[str, str], Dict[str, str], Dict[str, Tuple[str, bytes, str]], float], Tuple[int, str]]


class AudioValidationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class TranscriptionError(Exception):
    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code


def _extension(filename: Optional[str]) -> str:
    name = (filename or "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def _magic_ok(ext: str, data: bytes) -> bool:
    if ext == "wav":
        return data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    if ext == "flac":
        return data[:4] == b"fLaC"
    if ext == "ogg":
        return data[:4] == b"OggS"
    if ext == "webm":
        return data[:4] == b"\x1a\x45\xdf\xa3"
    if ext in ("mp4", "m4a"):
        return data[4:8] == b"ftyp"
    if ext in ("mp3", "mpeg", "mpga"):
        return data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0)
    return False


def validate_audio(filename: Optional[str], content_type: Optional[str], data: bytes, max_mb: float) -> str:
    """Validate an upload; returns the safe extension. Raises AudioValidationError."""
    if not data:
        raise AudioValidationError("empty_file", "The uploaded audio file is empty.")
    if len(data) > int(max_mb * 1024 * 1024):
        raise AudioValidationError("file_too_large", f"Audio file exceeds the {max_mb:g} MB limit.")
    ext = _extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise AudioValidationError("unsupported_extension",
                                   "Unsupported audio file type. Allowed: " + ", ".join(sorted(ALLOWED_EXTENSIONS)) + ".")
    ct = (content_type or "").split(";")[0].strip().lower()
    if not (ct.startswith(ALLOWED_MIME_PREFIXES) or ct in ALLOWED_MIME_EXTRA):
        raise AudioValidationError("unsupported_mime", f"Unsupported content type '{ct or 'missing'}'.")
    if not _magic_ok(ext, data):
        raise AudioValidationError("unreadable_audio", "File content does not look like the declared audio format.")
    if ext == "wav":
        try:
            with wave.open(io.BytesIO(data)) as w:
                if w.getnframes() <= 0 or w.getframerate() <= 0:
                    raise AudioValidationError("unreadable_audio", "WAV file contains no audio.")
        except (wave.Error, EOFError) as exc:
            raise AudioValidationError("unreadable_audio", "WAV file could not be read.") from exc
    return ext


def _default_transport(url, headers, data, files, timeout):
    import httpx
    from app.services.ai_service import AIServiceError  # noqa: F401  (kept for symmetry)
    try:
        r = httpx.post(url, headers=headers, data=data, files=files, timeout=timeout)
    except httpx.TimeoutException as exc:
        raise TranscriptionError("timeout", "Transcription request timed out.") from exc
    except httpx.HTTPError as exc:
        raise TranscriptionError("provider_unreachable", "Could not reach the transcription provider.") from exc
    return r.status_code, r.text


def transcribe(data: bytes, ext: str, settings: Any, transport: Optional[STTTransport] = None) -> str:
    key = (getattr(settings, "groq_api_key", "") or "").strip()
    if getattr(settings, "default_stt_provider", "groq") != "groq" or not key:
        raise TranscriptionError("not_configured", "Speech-to-text is not configured (missing API key).")
    url = settings.groq_base_url.rstrip("/") + "/audio/transcriptions"
    headers = {"Authorization": f"Bearer {key}"}
    form = {"model": settings.groq_whisper_model, "response_format": "json", "temperature": "0"}
    files = {"file": (f"audio.{ext}", data, MIME_FOR_EXT.get(ext, "application/octet-stream"))}
    send = transport or _default_transport
    try:
        status, body = send(url, headers, form, files, settings.ai_timeout_seconds)
    except TranscriptionError:
        raise
    except TimeoutError as exc:
        raise TranscriptionError("timeout", "Transcription request timed out.") from exc
    except Exception as exc:
        raise TranscriptionError("provider_unreachable", "Transcription call failed.") from exc
    if status == 429:
        raise TranscriptionError("rate_limited", "Transcription rate limit reached.")
    if status in (401, 403):
        raise TranscriptionError("auth_failed", "Transcription provider rejected the credentials.")
    if status >= 400:
        raise TranscriptionError("provider_error", f"Transcription provider returned HTTP {status}.")
    import json
    try:
        text = json.loads(body)["text"]
    except (ValueError, KeyError, TypeError) as exc:
        raise TranscriptionError("malformed_response", "Unexpected transcription response.") from exc
    if not isinstance(text, str) or not text.strip():
        raise TranscriptionError("empty_transcript", "No speech was detected in the audio.")
    return text.strip()

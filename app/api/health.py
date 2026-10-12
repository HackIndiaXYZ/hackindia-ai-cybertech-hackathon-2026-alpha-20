from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.schemas import HealthResponse
from app.services.transcription_service import ALLOWED_EXTENSIONS

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """Liveness check. Reports only whether providers are configured, never any secret."""
    s = request.app.state.settings
    return HealthResponse(status="ok", service="medtriage-ai", version=request.app.version,
                          llm_configured=s.llm_configured, stt_configured=s.stt_configured,
                          timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                          max_audio_mb=s.max_audio_mb, allowed_audio_formats=sorted(ALLOWED_EXTENSIONS))

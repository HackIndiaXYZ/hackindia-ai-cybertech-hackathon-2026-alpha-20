import re

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.deps import APIError
from app.schemas import AgeGroup, ErrorResponse, TextTriageRequest, TriageList, TriageResponse
from app.services import transcription_service as stt
from app.services.triage_pipeline import run_triage

router = APIRouter(prefix="/api/v1/triage", tags=["triage"])

_AUDIO_STATUS = {"empty_file": 400, "file_too_large": 413, "unsupported_extension": 415,
                 "unsupported_mime": 415, "unreadable_audio": 422}
_STT_STATUS = {"not_configured": 503, "timeout": 504, "rate_limited": 429, "auth_failed": 502,
               "provider_error": 502, "provider_unreachable": 502, "malformed_response": 502,
               "empty_transcript": 422}


def _response(record: dict) -> TriageResponse:
    data = dict(record)
    data["transcript"] = record.get("input_text") if record.get("transcription") else None
    return TriageResponse.model_validate(data)


@router.post("/text", response_model=TriageResponse, responses={422: {"model": ErrorResponse}})
def triage_text(payload: TextTriageRequest, request: Request) -> TriageResponse:
    """Text triage. Works without API keys (rules-only mode, clearly labelled)."""
    ctx = payload.context.model_dump(mode="json") if payload.context else None
    record = run_triage(payload.symptom_description, request.app.state.settings, request.app.state.db, ctx,
                        ai_transport=getattr(request.app.state, "ai_transport", None))
    return _response(record)


@router.get("", response_model=TriageList)
def list_triage(request: Request, limit: int = Query(20, ge=1, le=100)) -> TriageList:
    """Recent triage results (newest first), without the original input text."""
    db = request.app.state.db
    items = db.list_triage(limit)
    return TriageList(count=len(items), total=db.count_triage(), items=items)


@router.get("/{request_id}", response_model=TriageResponse, responses={404: {"model": ErrorResponse}})
def get_triage(request_id: str, request: Request) -> TriageResponse:
    record = request.app.state.db.get_triage(request_id) if re.fullmatch(r"[0-9a-f]{32}", request_id) else None
    if record is None:
        raise APIError(404, "triage_not_found", "No triage result exists for this request ID.")
    return _response(record)


@router.post("/audio", response_model=TriageResponse,
             responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}, 415: {"model": ErrorResponse},
                        422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
async def triage_audio(request: Request, file: UploadFile = File(...),
                       age_group: AgeGroup = Form(AgeGroup.unspecified)) -> TriageResponse:
    """Transcribe uploaded audio, then run the SAME triage pipeline on the real transcript."""
    settings = request.app.state.settings
    limit = int(settings.max_audio_mb * 1024 * 1024)
    data = await file.read(limit + 1)  # bounded read: never loads more than limit+1 bytes
    try:
        ext = stt.validate_audio(file.filename, file.content_type, data, settings.max_audio_mb)
    except stt.AudioValidationError as exc:
        raise APIError(_AUDIO_STATUS.get(exc.code, 400), exc.code, exc.message)
    finally:
        await file.close()

    try:
        transcript = await run_in_threadpool(stt.transcribe, data, ext, settings,
                                             getattr(request.app.state, "stt_transport", None))
    except stt.TranscriptionError as exc:
        raise APIError(_STT_STATUS.get(exc.code, 502), f"transcription_{exc.code}", str(exc))

    info = {"status": "ok", "provider": settings.default_stt_provider,
            "model": settings.groq_whisper_model, "characters": len(transcript)}
    ctx = {"age_group": age_group.value}
    record = await run_in_threadpool(
        run_triage, transcript[:2000], settings, request.app.state.db, ctx, "audio", info,
        getattr(request.app.state, "ai_transport", None))
    return _response(record)

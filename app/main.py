"""FastAPI application factory for MedTriage AI (hackathon prototype)."""
import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import health, patients, reports, triage
from app.api.deps import APIError
from app.config import Settings, get_settings
from app.services.storage import Database

log = logging.getLogger("medtriage")
VERSION = "0.1.0"


def _error(status: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="MedTriage AI", version=VERSION,
                  description="Hackathon prototype for triage SUPPORT. Not a medical device; not clinically validated.")
    app.state.settings = settings
    app.state.db = Database(settings.database_path)
    app.state.db.init()
    app.state.ai_transport = None   # tests inject mocks here
    app.state.stt_transport = None

    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
                       allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["Content-Type"],
                       expose_headers=["Content-Disposition"])

    @app.exception_handler(APIError)
    async def _api_error(_: Request, exc: APIError):
        return _error(exc.status_code, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        return _error(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in e.get("loc", [])), "message": str(e.get("msg", ""))}
                   for e in exc.errors()]
        return _error(422, "validation_error", "Request validation failed.", details)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.error("Unhandled error: %s", type(exc).__name__)  # no request bodies / secrets logged
        return _error(500, "internal_error", "An unexpected error occurred.")

    for module in (health, triage, patients, reports):
        app.include_router(module.router)
    return app


app = create_app()

import re

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.api.deps import APIError
from app.schemas import ErrorResponse
from app.services.report_service import generate_pdf

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/{request_id}/pdf", responses={200: {"content": {"application/pdf": {}}}, 404: {"model": ErrorResponse}})
def report_pdf(request_id: str, request: Request) -> Response:
    """Download a PDF built from the STORED triage result for this request ID."""
    record = request.app.state.db.get_triage(request_id) if re.fullmatch(r"[0-9a-f]{32}", request_id) else None
    if record is None:
        raise APIError(404, "report_not_found", "No triage result exists for this request ID.")
    pdf = generate_pdf(record, (getattr(request.app.state.settings, "report_font_path", "") or None))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="medtriage-report-{request_id[:8]}.pdf"',
                             "Cache-Control": "no-store"})

from typing import Optional

from fastapi import APIRouter, Request

from app.api.deps import APIError
from app.schemas import ErrorResponse, Patient, PatientCreate, PatientList, PatientStatus, PatientUpdate, Urgency

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])
_404 = {404: {"model": ErrorResponse}}


@router.get("", response_model=PatientList)
def list_patients(request: Request, status: Optional[PatientStatus] = None,
                  urgency: Optional[Urgency] = None) -> PatientList:
    """Synthetic queue, most urgent first, then earliest arrival."""
    rows = request.app.state.db.list_patients(status.value if status else None, urgency.value if urgency else None)
    return PatientList(count=len(rows), patients=[Patient(**r) for r in rows])


@router.get("/{patient_id}", response_model=Patient, responses=_404)
def get_patient(patient_id: str, request: Request) -> Patient:
    row = request.app.state.db.get_patient(patient_id)
    if row is None:
        raise APIError(404, "patient_not_found", "No patient with this ID exists in the demo queue.")
    return Patient(**row)


@router.post("", response_model=Patient, status_code=201, responses=_404)
def create_patient(payload: PatientCreate, request: Request) -> Patient:
    db = request.app.state.db
    urgency = payload.urgency.value
    if payload.triage_request_id:
        record = db.get_triage(payload.triage_request_id)
        if record is None:
            raise APIError(404, "triage_not_found", "The referenced triage result does not exist.")
        urgency = record["urgency"]
    row = db.create_patient(payload.display_name, payload.age_group.value, payload.chief_complaint,
                            urgency, payload.triage_request_id)
    return Patient(**row)


@router.patch("/{patient_id}", response_model=Patient, responses=_404)
def update_patient(patient_id: str, payload: PatientUpdate, request: Request) -> Patient:
    changes = {k: (v.value if hasattr(v, "value") else v) for k, v in payload.model_dump().items()}
    row = request.app.state.db.update_patient(patient_id, changes)
    if row is None:
        raise APIError(404, "patient_not_found", "No patient with this ID exists in the demo queue.")
    return Patient(**row)

"""Pydantic request/response models (stable JSON contract for the frontend)."""
import re
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Urgency(str, Enum):
    emergency = "emergency"
    urgent = "urgent"
    routine = "routine"
    undetermined = "undetermined"


class AgeGroup(str, Enum):
    infant = "infant"
    child = "child"
    adult = "adult"
    older_adult = "older_adult"
    unspecified = "unspecified"


class PatientStatus(str, Enum):
    waiting = "waiting"
    in_assessment = "in_assessment"
    seen = "seen"


class TriageContext(BaseModel):
    """Optional NON-identifying context. Do not put names or phone numbers here."""
    age_group: AgeGroup = AgeGroup.unspecified
    duration: Optional[str] = Field(default=None, max_length=100, description="e.g. '2 days'")


def _meaningful(v: str) -> str:
    v = v.strip()
    if len(re.sub(r"[\W_]+", "", v)) < 3:
        raise ValueError("must contain meaningful text (at least 3 letters or digits)")
    return v


class TextTriageRequest(BaseModel):
    symptom_description: str = Field(..., min_length=1, max_length=2000,
                                     examples=["Synthetic example: I have had a cough and mild fever for 2 days."])
    context: Optional[TriageContext] = None

    _check = field_validator("symptom_description")(_meaningful)


class TranscriptionInfo(BaseModel):
    status: str
    provider: str
    model: str
    characters: int


class TriageResponse(BaseModel):
    request_id: str
    created_at: str
    source: str
    reported_symptoms: List[str]
    negated_symptoms: List[str]
    summary: str
    summary_source: str = Field(description="'ai' or 'rules'")
    uncertainties: List[str]
    urgency: Urgency
    explanation: str
    emergency_advice: Optional[str] = None
    ai_used: bool
    mode: str = Field(description="rules_only | rules_only_fallback | llm_groq_with_rules")
    ai_status: str
    ai_model: Optional[str] = None
    transcript: Optional[str] = None
    transcription: Optional[TranscriptionInfo] = None
    disclaimer: str


class PatientCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=60, description="Pseudonym only. No real names.")
    age_group: AgeGroup = AgeGroup.unspecified
    chief_complaint: str = Field(..., min_length=3, max_length=300)
    triage_request_id: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{32}$")
    urgency: Urgency = Urgency.undetermined


class PatientUpdate(BaseModel):
    status: Optional[PatientStatus] = None
    urgency: Optional[Urgency] = None
    chief_complaint: Optional[str] = Field(default=None, min_length=3, max_length=300)
    age_group: Optional[AgeGroup] = None

    @model_validator(mode="after")
    def _at_least_one(self):
        if not any(v is not None for v in (self.status, self.urgency, self.chief_complaint, self.age_group)):
            raise ValueError("provide at least one field to update")
        return self


class Patient(BaseModel):
    id: str
    display_name: str
    age_group: AgeGroup
    chief_complaint: str
    urgency: Urgency
    status: PatientStatus
    triage_request_id: Optional[str] = None
    arrived_at: str
    updated_at: str


class PatientList(BaseModel):
    count: int
    storage: str = "sqlite"
    synthetic_data_notice: str = "All records are synthetic demonstration data."
    patients: List[Patient]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    llm_configured: bool
    stt_configured: bool
    timestamp: str
    max_audio_mb: float
    allowed_audio_formats: List[str]
    max_text_chars: int = 2000


class TriageListItem(BaseModel):
    request_id: str
    created_at: str
    source: str
    urgency: Urgency
    reported_symptoms: List[str]
    summary_source: str
    mode: str
    ai_used: bool


class TriageList(BaseModel):
    count: int = Field(description="Number of items returned (bounded by `limit`)")
    total: int = Field(description="Total stored results")
    items: List[TriageListItem]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[List[Dict[str, Any]]] = None


class ErrorResponse(BaseModel):
    error: ErrorBody

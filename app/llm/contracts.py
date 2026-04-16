from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.schemas.models import StateEnum

ALLOWED_EMOTION_LABELS = ("anxiety", "fear", "panic", "shame", "sadness", "despair")
ALLOWED_RISK_FLAGS = (
    "suicidal_intent",
    "passive_death_wish",
    "hopelessness",
    "psychotic_expression",
    "acute_deterioration",
)
ALLOWED_DISTORTION_LABELS = (
    "mind_reading",
    "fortune_telling",
    "catastrophizing",
    "should_statements",
    "self_blame",
    "overgeneralization",
    "intolerance_of_uncertainty",
    "probability_overestimation",
    "uncertainty_focus",
)


class CandidateText(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    evidence_span: str = ""


class CandidateEmotion(BaseModel):
    label: str
    intensity_hint: int = Field(default=0, ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    evidence_span: str = ""


class CandidateDistortion(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    rationale_code: str = ""


class CandidateRiskFlag(BaseModel):
    flag: str
    confidence: float = Field(ge=0, le=1)
    evidence_span: str = ""


class LLMStructuredOutput(BaseModel):
    situation_candidates: list[CandidateText] = Field(default_factory=list)
    automatic_thought_candidates: list[CandidateText] = Field(default_factory=list)
    worry_prediction_candidates: list[CandidateText] = Field(default_factory=list)
    emotion_candidates: list[CandidateEmotion] = Field(default_factory=list)
    behavior_candidates: list[CandidateText] = Field(default_factory=list)
    distortion_candidates: list[CandidateDistortion] = Field(default_factory=list)
    risk_flags: list[CandidateRiskFlag] = Field(default_factory=list)
    needs_clarification: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)


class LLMRenderRequest(BaseModel):
    template_id: str
    source_text: str
    context: dict[str, Any] = Field(default_factory=dict)


class LLMRenderResponse(BaseModel):
    rendered_text: str
    fallback_used: bool = False


class LLMParsePreviewRequest(BaseModel):
    free_text: str
    state: StateEnum


class LLMParsePreviewResponse(BaseModel):
    structured_output: LLMStructuredOutput
    fallback_used: bool = False
    invocation: "LLMInvocationLog"


class LLMRenderPreviewResponse(BaseModel):
    rendered_text: str
    fallback_used: bool = False
    invocation: "LLMInvocationLog"


class LLMHealthResponse(BaseModel):
    enabled: bool
    api_key_configured: bool
    models_configured: bool
    live_call_available: bool
    live_test_enabled: bool
    base_url: str
    structurer_model: str
    renderer_model: str
    risk_assist_model: str


class LLMLiveCheckRequest(BaseModel):
    free_text: str = "회의 전에 발표가 망할까 불안하다."
    state: StateEnum = StateEnum.SITUATION_CAPTURE


class LLMLiveCheckResponse(BaseModel):
    ok: bool
    enabled: bool
    model_name: str
    prompt_version: str
    latency_ms: float
    schema_valid: bool
    error_code: str | None = None
    fallback_used: bool = False


class LLMInvocationLog(BaseModel):
    invocation_id: UUID = Field(default_factory=uuid4)
    session_id: UUID | None = None
    state: StateEnum | None = None
    task_type: str
    model_name: str
    model_version: str
    prompt_version: str
    request_hash: str
    response_hash: str
    raw_response: str
    parsed_output: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    succeeded: bool = False
    error_code: str | None = None


LLMParsePreviewResponse.model_rebuild()
LLMRenderPreviewResponse.model_rebuild()

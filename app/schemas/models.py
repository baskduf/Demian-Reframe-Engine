from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.config.versions import (
    ENGINE_VERSION,
    PROTOCOL_VERSION,
    RISK_RULES_VERSION,
    RULE_SET_VERSION,
    TEMPLATE_BUNDLE_VERSION,
)


class StateEnum(StrEnum):
    RISK_SCREEN = "risk_screen"
    ELIGIBILITY_CHECK = "eligibility_check"
    SITUATION_CAPTURE = "situation_capture"
    WORRY_THOUGHT_CAPTURE = "worry_thought_capture"
    EMOTION_BODY_BEHAVIOR_CAPTURE = "emotion_body_behavior_capture"
    DISTORTION_HYPOTHESIS = "distortion_hypothesis"
    EVIDENCE_FOR = "evidence_for"
    EVIDENCE_AGAINST = "evidence_against"
    ALTERNATIVE_THOUGHT = "alternative_thought"
    RE_RATE_ANXIETY = "re_rate_anxiety"
    BEHAVIOR_EXPERIMENT = "behavior_experiment"
    SUMMARY_PLAN = "summary_plan"
    CRISIS = "crisis"
    OUT_OF_SCOPE = "out_of_scope"
    CLOSE_SESSION = "close_session"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    CLOSED = "closed"


class RiskLevel(StrEnum):
    NONE = "none"
    MODERATE = "moderate"
    HIGH = "high"


class EmotionScore(BaseModel):
    label: str
    intensity: int = Field(ge=0, le=100)


class RuleMatch(BaseModel):
    rule_id: str
    label: str
    confidence: Literal["deterministic"] = "deterministic"


class DistortionCandidate(BaseModel):
    distortion_id: str
    label: str
    is_primary: bool = False
    rule_matches: list[RuleMatch] = Field(default_factory=list)


class BehaviorExperiment(BaseModel):
    action: str
    timebox: str
    hypothesis: str | None = None


class LLMTextCandidate(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    evidence_span: str = ""


class LLMEmotionCandidate(BaseModel):
    label: str
    intensity_hint: int = Field(default=0, ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    evidence_span: str = ""


class LLMDistortionCandidate(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    rationale_code: str = ""


class LLMRiskFlag(BaseModel):
    flag: str
    confidence: float = Field(ge=0, le=1)
    evidence_span: str = ""


class TemplateResponse(BaseModel):
    template_id: str
    message: str
    source: Literal["template"] = "template"


class ProtocolManifest(BaseModel):
    protocol_version: str
    target_condition: str
    state_machine_version: str
    rule_set_version: str
    template_bundle_version: str
    risk_rules_version: str
    effective_date: date
    states: list[str]


class Session(BaseModel):
    session_id: UUID
    user_id: str
    protocol_version: str = PROTOCOL_VERSION
    engine_version: str = ENGINE_VERSION
    current_state: StateEnum
    status: SessionStatus
    opened_at: datetime
    closed_at: datetime | None = None
    closed_reason: str | None = None


class SessionEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    state_before: StateEnum
    event_type: str
    payload: dict[str, Any]
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    actor: Literal["user", "system", "admin"] = "user"


class RiskAssessment(BaseModel):
    assessment_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    risk_level: RiskLevel
    suicidality_flag: bool = False
    psychosis_flag: bool = False
    acute_deterioration_flag: bool = False
    triggered_rule_ids: list[str] = Field(default_factory=list)
    disposition: str
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class ThoughtRecord(BaseModel):
    record_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    situation_text: str | None = None
    trigger_text: str | None = None
    automatic_thought: str | None = None
    worry_prediction: str | None = None
    emotions: list[EmotionScore] = Field(default_factory=list)
    body_symptoms: list[str] = Field(default_factory=list)
    safety_behaviors: list[str] = Field(default_factory=list)
    candidate_distortions: list[DistortionCandidate] = Field(default_factory=list)
    selected_distortion_ids: list[str] = Field(default_factory=list)
    evidence_for: list[str] = Field(default_factory=list)
    evidence_against: list[str] = Field(default_factory=list)
    alternative_thought: str | None = None
    re_rated_anxiety: int | None = Field(default=None, ge=0, le=100)
    behavior_experiment: BehaviorExperiment | None = None
    llm_situation_candidates: list[LLMTextCandidate] = Field(default_factory=list)
    llm_automatic_thought_candidates: list[LLMTextCandidate] = Field(default_factory=list)
    llm_worry_prediction_candidates: list[LLMTextCandidate] = Field(default_factory=list)
    llm_emotion_candidates: list[LLMEmotionCandidate] = Field(default_factory=list)
    llm_behavior_candidates: list[LLMTextCandidate] = Field(default_factory=list)
    llm_distortion_candidates: list[LLMDistortionCandidate] = Field(default_factory=list)
    llm_risk_flags: list[LLMRiskFlag] = Field(default_factory=list)
    llm_needs_clarification: bool = False
    llm_missing_fields: list[str] = Field(default_factory=list)


class TransitionLog(BaseModel):
    transition_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    from_state: StateEnum
    to_state: StateEnum
    decision_time: datetime = Field(default_factory=datetime.utcnow)
    rule_set_version: str = RULE_SET_VERSION
    matched_rule_ids: list[str] = Field(default_factory=list)
    input_hash: str
    output_hash: str
    template_ids: list[str] = Field(default_factory=list)


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


class VersionEnvelope(BaseModel):
    engine_version: str = ENGINE_VERSION
    protocol_version: str = PROTOCOL_VERSION
    rule_set_version: str = RULE_SET_VERSION
    template_bundle_version: str = TEMPLATE_BUNDLE_VERSION
    risk_rules_version: str = RISK_RULES_VERSION


class SessionEnvelope(VersionEnvelope):
    session: Session
    current_state: StateEnum
    allowed_actions: list[str]
    transition_trace_id: UUID | None = None
    state_data: dict[str, Any] = Field(default_factory=dict)
    template_response: TemplateResponse | None = None


class CreateSessionRequest(BaseModel):
    user_id: str
    locale: str = "ko-KR"


class RiskScreenRequest(BaseModel):
    free_text: str = ""
    suicidal_intent: bool = False
    suicidal_plan: bool = False
    means_access: bool = False
    command_hallucination: bool = False
    psychotic_language: bool = False
    acute_deterioration: bool = False


class EventRequest(BaseModel):
    event_type: str
    payload: dict[str, Any]


class AuditResponse(VersionEnvelope):
    session_id: UUID
    transitions: list[TransitionLog]
    risks: list[RiskAssessment]
    events: list[SessionEvent]
    llm_invocations: list[LLMInvocationLog]


class ArtifactsResponse(VersionEnvelope):
    session_id: UUID
    thought_record: ThoughtRecord

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.config.versions import PROTOCOL_MANIFEST
from app.domain.distortions import detect_distortions
from app.domain.risk import evaluate_risk
from app.domain.state_machine import allowed_actions, has_required_fields, next_state
from app.domain.templates import PROMPT_BY_STATE, render_template
from app.llm.contracts import (
    LLMHealthResponse,
    LLMLiveCheckRequest,
    LLMLiveCheckResponse,
    LLMParsePreviewRequest,
    LLMParsePreviewResponse,
    LLMRenderPreviewResponse,
    LLMRenderRequest,
)
from app.persistence.sqlite import SQLiteRepository
from app.schemas.events import PAYLOAD_MODEL_BY_EVENT, EventTypeEnum, expected_event_type_for_state
from app.schemas.models import (
    ArtifactsResponse,
    AuditResponse,
    BehaviorExperiment,
    CreateSessionRequest,
    EmotionScore,
    EventRequest,
    LLMDistortionCandidate,
    LLMEmotionCandidate,
    LLMRiskFlag,
    LLMTextCandidate,
    ProtocolManifest,
    RiskLevel,
    RiskScreenRequest,
    Session,
    SessionEnvelope,
    SessionEvent,
    SessionStatus,
    StateEnum,
    ThoughtRecord,
    TransitionLog,
)
from app.services.llm_gateway import LLMGateway


class SessionService:
    STRUCTURED_STATES = {
        StateEnum.SITUATION_CAPTURE,
        StateEnum.WORRY_THOUGHT_CAPTURE,
        StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE,
    }

    def __init__(self, repository: SQLiteRepository, llm_gateway: LLMGateway | None = None) -> None:
        self.repository = repository
        self.llm_gateway = llm_gateway or LLMGateway()

    @staticmethod
    def _hash_payload(payload: dict) -> str:
        dumped = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(dumped.encode("utf-8")).hexdigest()

    def _load_session(self, session_id: UUID) -> Session:
        session = self.repository.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        return session

    def _load_record(self, session_id: UUID) -> ThoughtRecord:
        record = self.repository.get_thought_record(session_id)
        if record is None:
            record = ThoughtRecord(session_id=session_id)
            self.repository.save_thought_record(record)
        return record

    @staticmethod
    def _invalid_fields_from_error(exc: ValidationError) -> list[str]:
        fields: list[str] = []
        for error in exc.errors():
            if not error.get("loc"):
                continue
            field = str(error["loc"][0])
            if field not in fields:
                fields.append(field)
        return fields

    def _validate_event_payload(self, state: StateEnum, event_type: str, payload: dict) -> tuple[dict, dict]:
        expected_event_type = expected_event_type_for_state(state)
        if expected_event_type is None:
            return payload, {}

        try:
            parsed_event_type = EventTypeEnum(event_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"unsupported event_type {event_type}") from exc

        if parsed_event_type != expected_event_type:
            raise HTTPException(
                status_code=400,
                detail=f"event_type {parsed_event_type.value} is not allowed in state {state.value}",
            )

        payload_model = PAYLOAD_MODEL_BY_EVENT[parsed_event_type]
        try:
            validated = payload_model.model_validate(payload)
        except ValidationError as exc:
            return payload, {"invalid_fields": self._invalid_fields_from_error(exc)}
        return validated.model_dump(exclude_none=True), {}

    def _transition(self, session: Session, to_state: StateEnum, payload: dict, matched_rule_ids: list[str], template_ids: list[str]) -> TransitionLog:
        transition = TransitionLog(
            session_id=session.session_id,
            from_state=session.current_state,
            to_state=to_state,
            matched_rule_ids=matched_rule_ids,
            input_hash=self._hash_payload(payload),
            output_hash=self._hash_payload({"to_state": to_state, "status": session.status}),
            template_ids=template_ids,
        )
        session.current_state = to_state
        if to_state == StateEnum.CLOSE_SESSION and session.status == SessionStatus.ACTIVE:
            session.status = SessionStatus.COMPLETED
            session.closed_at = datetime.now(UTC)
            session.closed_reason = "session_complete"
        self.repository.upsert_session(session)
        self.repository.add_transition(transition)
        return transition

    def _build_envelope(self, session: Session, trace_id=None, state_data=None, template_id=None) -> SessionEnvelope:
        template_key = template_id or PROMPT_BY_STATE.get(session.current_state, "summary.complete")
        template_response = render_template(template_key)
        merged_state_data = dict(state_data or {})
        if self.llm_gateway.enabled:
            rendered, invocation = self.llm_gateway.render_text(
                session_id=session.session_id,
                state=session.current_state,
                template_id=template_response.template_id,
                source_text=template_response.message,
            )
            self.repository.add_llm_invocation(invocation)
            template_response.message = rendered.rendered_text
            if rendered.fallback_used:
                merged_state_data["llm_fallback_used"] = True
                merged_state_data["llm_error_code"] = invocation.error_code
        return SessionEnvelope(
            session=session,
            current_state=session.current_state,
            allowed_actions=allowed_actions(session.current_state),
            transition_trace_id=trace_id,
            state_data=merged_state_data,
            template_response=template_response,
        )

    @staticmethod
    def _merge_missing_fields(static_fields: list[str], llm_fields: list[str]) -> list[str]:
        seen: list[str] = []
        for field in static_fields + llm_fields:
            if field not in seen:
                seen.append(field)
        return seen

    @staticmethod
    def _candidate_above_threshold(confidence: float) -> bool:
        from app.config.llm import LLM_CONFIDENCE_THRESHOLD

        return confidence >= LLM_CONFIDENCE_THRESHOLD

    def _store_llm_output(self, record: ThoughtRecord, structured_output, risk_flags) -> None:
        record.llm_situation_candidates = [LLMTextCandidate.model_validate(item.model_dump()) for item in structured_output.situation_candidates]
        record.llm_automatic_thought_candidates = [
            LLMTextCandidate.model_validate(item.model_dump()) for item in structured_output.automatic_thought_candidates
        ]
        record.llm_worry_prediction_candidates = [
            LLMTextCandidate.model_validate(item.model_dump()) for item in structured_output.worry_prediction_candidates
        ]
        record.llm_emotion_candidates = [LLMEmotionCandidate.model_validate(item.model_dump()) for item in structured_output.emotion_candidates]
        record.llm_behavior_candidates = [LLMTextCandidate.model_validate(item.model_dump()) for item in structured_output.behavior_candidates]
        record.llm_distortion_candidates = [
            LLMDistortionCandidate.model_validate(item.model_dump()) for item in structured_output.distortion_candidates
        ]
        record.llm_risk_flags = [LLMRiskFlag.model_validate(item.model_dump()) for item in risk_flags or structured_output.risk_flags]
        record.llm_needs_clarification = structured_output.needs_clarification
        record.llm_missing_fields = structured_output.missing_fields
        self.repository.save_thought_record(record)

    def _apply_llm_structuring(self, session: Session, record: ThoughtRecord, payload: dict) -> tuple[dict, dict]:
        free_text = str(payload.get("free_text", "")).strip()
        if not free_text or session.current_state not in self.STRUCTURED_STATES:
            return payload, {}

        structured_output, parse_log = self.llm_gateway.parse_structured(
            session_id=session.session_id,
            state=session.current_state,
            free_text=free_text,
        )
        self.repository.add_llm_invocation(parse_log)
        risk_flags, risk_log = self.llm_gateway.assist_risk(
            session_id=session.session_id,
            state=session.current_state,
            free_text=free_text,
        )
        self.repository.add_llm_invocation(risk_log)

        self._store_llm_output(record, structured_output, risk_flags)

        enriched_payload = dict(payload)
        if session.current_state == StateEnum.SITUATION_CAPTURE and "situation_text" not in enriched_payload:
            if structured_output.situation_candidates and self._candidate_above_threshold(structured_output.situation_candidates[0].confidence):
                enriched_payload["situation_text"] = structured_output.situation_candidates[0].text

        if session.current_state == StateEnum.WORRY_THOUGHT_CAPTURE and "automatic_thought" not in enriched_payload:
            if structured_output.automatic_thought_candidates and self._candidate_above_threshold(
                structured_output.automatic_thought_candidates[0].confidence
            ):
                enriched_payload["automatic_thought"] = structured_output.automatic_thought_candidates[0].text
        if session.current_state == StateEnum.WORRY_THOUGHT_CAPTURE and "worry_prediction" not in enriched_payload:
            if structured_output.worry_prediction_candidates and self._candidate_above_threshold(
                structured_output.worry_prediction_candidates[0].confidence
            ):
                enriched_payload["worry_prediction"] = structured_output.worry_prediction_candidates[0].text

        if session.current_state == StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE:
            if "emotions" not in enriched_payload and structured_output.emotion_candidates:
                enriched_payload["emotions"] = [
                    {"label": item.label, "intensity": item.intensity_hint or 50}
                    for item in structured_output.emotion_candidates
                    if self._candidate_above_threshold(item.confidence)
                ]
            if "safety_behaviors" not in enriched_payload and structured_output.behavior_candidates:
                enriched_payload["safety_behaviors"] = [
                    item.text for item in structured_output.behavior_candidates if self._candidate_above_threshold(item.confidence)
                ]

        state_data = {
            "llm_structured_output": structured_output.model_dump(),
            "llm_risk_flags": [flag.model_dump() for flag in risk_flags],
        }
        if not parse_log.succeeded:
            state_data["llm_fallback_used"] = True
            state_data["llm_error_code"] = parse_log.error_code
        elif not risk_log.succeeded:
            state_data["llm_fallback_used"] = True
            state_data["llm_error_code"] = risk_log.error_code
        return enriched_payload, state_data

    def create_session(self, request: CreateSessionRequest) -> SessionEnvelope:
        session = Session(
            session_id=uuid4(),
            user_id=request.user_id,
            current_state=StateEnum.RISK_SCREEN,
            status=SessionStatus.ACTIVE,
            opened_at=datetime.now(UTC),
        )
        self.repository.upsert_session(session)
        self.repository.save_thought_record(ThoughtRecord(session_id=session.session_id))
        return self._build_envelope(session, state_data={"locale": request.locale})

    def submit_risk_screen(self, session_id: UUID, request: RiskScreenRequest) -> SessionEnvelope:
        session = self._load_session(session_id)
        risk = evaluate_risk(session_id, request)
        self.repository.add_risk(risk)
        self.repository.add_event(SessionEvent(session_id=session_id, state_before=session.current_state, event_type="risk_screen", payload=request.model_dump()))

        if risk.risk_level == RiskLevel.HIGH:
            session.status = SessionStatus.ESCALATED
            session.closed_at = datetime.now(UTC)
            session.closed_reason = "safety_escalation"
            trace = self._transition(session, StateEnum.CRISIS, request.model_dump(), risk.triggered_rule_ids, ["risk.high"])
            return self._build_envelope(session, trace.transition_id, {"risk_level": risk.risk_level, "triggered_rule_ids": risk.triggered_rule_ids}, "risk.high")

        template_id = "risk.moderate" if risk.risk_level == RiskLevel.MODERATE else "prompt.situation"
        trace = self._transition(session, StateEnum.ELIGIBILITY_CHECK, request.model_dump(), risk.triggered_rule_ids, [template_id])
        return self._build_envelope(session, trace.transition_id, {"risk_level": risk.risk_level, "triggered_rule_ids": risk.triggered_rule_ids}, template_id)

    def submit_event(self, session_id: UUID, request: EventRequest) -> SessionEnvelope:
        session = self._load_session(session_id)
        if session.current_state in {StateEnum.CRISIS, StateEnum.OUT_OF_SCOPE, StateEnum.CLOSE_SESSION}:
            return self._build_envelope(session)

        free_text = str(request.payload.get("free_text", ""))
        if free_text:
            risk = evaluate_risk(session_id, RiskScreenRequest(free_text=free_text))
            if risk.risk_level == RiskLevel.HIGH:
                self.repository.add_risk(risk)
                self.repository.add_event(SessionEvent(session_id=session_id, state_before=session.current_state, event_type=request.event_type, payload=request.payload))
                session.status = SessionStatus.ESCALATED
                session.closed_at = datetime.now(UTC)
                session.closed_reason = "safety_escalation"
                trace = self._transition(session, StateEnum.CRISIS, request.payload, risk.triggered_rule_ids, ["risk.high"])
                return self._build_envelope(session, trace.transition_id, {"risk_level": risk.risk_level, "triggered_rule_ids": risk.triggered_rule_ids}, "risk.high")

        record = self._load_record(session_id)
        self.repository.add_event(SessionEvent(session_id=session_id, state_before=session.current_state, event_type=request.event_type, payload=request.payload))
        state = session.current_state
        payload, llm_state_data = self._apply_llm_structuring(session, record, request.payload)
        payload, validation_state_data = self._validate_event_payload(state, request.event_type, payload)
        llm_state_data = {**llm_state_data, **validation_state_data}

        if state == StateEnum.ELIGIBILITY_CHECK:
            if "invalid_fields" in validation_state_data:
                return self._build_envelope(session, state_data=llm_state_data, template_id="prompt.situation")
            if not payload.get("is_adult", False) or payload.get("target_condition") != "gad":
                session.status = SessionStatus.CLOSED
                session.closed_reason = "out_of_scope"
                session.closed_at = datetime.now(UTC)
                trace = self._transition(session, StateEnum.OUT_OF_SCOPE, payload, ["eligibility_out_of_scope"], ["eligibility.out_of_scope"])
                return self._build_envelope(session, trace.transition_id, {"eligible": False}, "eligibility.out_of_scope")
            trace = self._transition(session, next_state(state), payload, ["eligibility_pass"], ["prompt.situation"])
            return self._build_envelope(session, trace.transition_id)

        if state == StateEnum.SITUATION_CAPTURE:
            if "invalid_fields" in validation_state_data:
                return self._build_envelope(session, state_data=llm_state_data, template_id="prompt.situation")
            if not has_required_fields(state, payload):
                return self._build_envelope(
                    session,
                    state_data={
                        **llm_state_data,
                        "missing_fields": self._merge_missing_fields(["situation_text", "trigger_text"], record.llm_missing_fields),
                    },
                    template_id="prompt.situation",
                )
            record.situation_text = payload["situation_text"]
            record.trigger_text = payload["trigger_text"]
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["situation_complete"], ["prompt.worry"])
            return self._build_envelope(session, trace.transition_id)

        if state == StateEnum.WORRY_THOUGHT_CAPTURE:
            if "invalid_fields" in validation_state_data:
                return self._build_envelope(session, state_data=llm_state_data, template_id="prompt.worry")
            if not has_required_fields(state, payload):
                return self._build_envelope(
                    session,
                    state_data={
                        **llm_state_data,
                        "missing_fields": self._merge_missing_fields(["automatic_thought", "worry_prediction"], record.llm_missing_fields),
                    },
                    template_id="prompt.worry",
                )
            record.automatic_thought = payload["automatic_thought"]
            record.worry_prediction = payload["worry_prediction"]
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["worry_complete"], ["prompt.emotion"])
            return self._build_envelope(session, trace.transition_id)

        if state == StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE:
            if "invalid_fields" in validation_state_data:
                return self._build_envelope(session, state_data=llm_state_data, template_id="prompt.emotion")
            if not has_required_fields(state, payload):
                return self._build_envelope(
                    session,
                    state_data={
                        **llm_state_data,
                        "missing_fields": self._merge_missing_fields(
                            ["emotions", "body_symptoms_or_safety_behaviors"], record.llm_missing_fields
                        ),
                    },
                    template_id="prompt.emotion",
                )
            record.emotions = [EmotionScore.model_validate(item) for item in payload["emotions"]]
            record.body_symptoms = payload.get("body_symptoms", [])
            record.safety_behaviors = payload.get("safety_behaviors", [])
            record.candidate_distortions = detect_distortions(record.automatic_thought or "", record.worry_prediction or "")
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["emotion_complete"], ["prompt.distortion"])
            return self._build_envelope(
                session,
                trace.transition_id,
                {
                    **llm_state_data,
                    "candidate_distortions": [candidate.model_dump() for candidate in record.candidate_distortions],
                    "llm_distortion_candidates": [candidate.model_dump() for candidate in record.llm_distortion_candidates],
                },
            )

        if state == StateEnum.DISTORTION_HYPOTHESIS:
            if "invalid_fields" in validation_state_data:
                return self._build_envelope(session, state_data=llm_state_data, template_id="prompt.distortion")
            selected = payload.get("selected_distortion_ids") or [candidate.distortion_id for candidate in record.candidate_distortions[:1]]
            record.selected_distortion_ids = selected
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["distortion_selected"], ["prompt.evidence_for"])
            return self._build_envelope(session, trace.transition_id, {"selected_distortion_ids": selected})

        if state == StateEnum.EVIDENCE_FOR:
            if "invalid_fields" in validation_state_data:
                return self._build_envelope(session, state_data=llm_state_data, template_id="prompt.evidence_for")
            if not has_required_fields(state, payload):
                return self._build_envelope(session, state_data={"missing_fields": ["evidence_for"]}, template_id="prompt.evidence_for")
            record.evidence_for = payload["evidence_for"]
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["evidence_for_complete"], ["prompt.evidence_against"])
            return self._build_envelope(session, trace.transition_id)

        if state == StateEnum.EVIDENCE_AGAINST:
            if "invalid_fields" in validation_state_data:
                return self._build_envelope(session, state_data=llm_state_data, template_id="prompt.evidence_against")
            if not has_required_fields(state, payload):
                return self._build_envelope(session, state_data={"missing_fields": ["evidence_against"]}, template_id="prompt.evidence_against")
            record.evidence_against = payload["evidence_against"]
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["evidence_against_complete"], ["prompt.alternative"])
            return self._build_envelope(session, trace.transition_id)

        if state == StateEnum.ALTERNATIVE_THOUGHT:
            if "invalid_fields" in validation_state_data:
                return self._build_envelope(session, state_data=llm_state_data, template_id="prompt.alternative")
            if not has_required_fields(state, payload):
                return self._build_envelope(session, state_data={"missing_fields": ["balanced_view", "coping_statement"]}, template_id="prompt.alternative")
            record.alternative_thought = f"A more balanced view is: {payload['balanced_view']}. A workable next response is: {payload['coping_statement']}."
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["alternative_complete"], ["prompt.re_rate"])
            return self._build_envelope(session, trace.transition_id, {"alternative_thought": record.alternative_thought})

        if state == StateEnum.RE_RATE_ANXIETY:
            if "invalid_fields" in validation_state_data:
                return self._build_envelope(session, state_data=llm_state_data, template_id="prompt.re_rate")
            if not has_required_fields(state, payload):
                return self._build_envelope(session, state_data={"missing_fields": ["re_rated_anxiety", "experiment_required"]}, template_id="prompt.re_rate")
            record.re_rated_anxiety = payload["re_rated_anxiety"]
            self.repository.save_thought_record(record)
            if payload["experiment_required"]:
                trace = self._transition(session, next_state(state), payload, ["experiment_required"], ["prompt.experiment"])
                return self._build_envelope(session, trace.transition_id)
            trace = self._transition(session, StateEnum.SUMMARY_PLAN, payload, ["experiment_skipped"], ["summary.complete"])
            return self._build_envelope(session, trace.transition_id)

        if state == StateEnum.BEHAVIOR_EXPERIMENT:
            if "invalid_fields" in validation_state_data:
                return self._build_envelope(session, state_data=llm_state_data, template_id="prompt.experiment")
            if not has_required_fields(state, payload):
                return self._build_envelope(session, state_data={"missing_fields": ["action", "timebox"]}, template_id="prompt.experiment")
            record.behavior_experiment = BehaviorExperiment(action=payload["action"], timebox=payload["timebox"], hypothesis=payload.get("hypothesis"))
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["experiment_complete"], ["summary.complete"])
            return self._build_envelope(session, trace.transition_id)

        if state == StateEnum.SUMMARY_PLAN:
            if "invalid_fields" in validation_state_data:
                return self._build_envelope(session, state_data=llm_state_data, template_id="summary.complete")
            if not has_required_fields(state, payload):
                return self._build_envelope(session, state_data={"missing_fields": ["summary_ack"]}, template_id="summary.complete")
            trace = self._transition(session, next_state(state), payload, ["summary_ack"], ["summary.complete"])
            return self._build_envelope(session, trace.transition_id)

        raise HTTPException(status_code=400, detail=f"unsupported state transition from {state}")

    def get_session(self, session_id: UUID) -> SessionEnvelope:
        session = self._load_session(session_id)
        record = self._load_record(session_id)
        state_data = {}
        if session.current_state == StateEnum.DISTORTION_HYPOTHESIS:
            state_data["candidate_distortions"] = [candidate.model_dump() for candidate in record.candidate_distortions]
            state_data["llm_distortion_candidates"] = [candidate.model_dump() for candidate in record.llm_distortion_candidates]
        return self._build_envelope(session, state_data=state_data)

    def get_artifacts(self, session_id: UUID) -> ArtifactsResponse:
        return ArtifactsResponse(session_id=session_id, thought_record=self._load_record(session_id))

    def get_audit(self, session_id: UUID) -> AuditResponse:
        return AuditResponse(
            session_id=session_id,
            transitions=self.repository.list_transitions(session_id),
            risks=self.repository.list_risks(session_id),
            events=self.repository.list_events(session_id),
            llm_invocations=self.repository.list_llm_invocations(session_id),
        )

    def reassess_risk(self, session_id: UUID, request: RiskScreenRequest) -> SessionEnvelope:
        return self.submit_risk_screen(session_id, request)

    def get_protocol(self, version: str) -> ProtocolManifest:
        if version != PROTOCOL_MANIFEST["protocol_version"]:
            raise HTTPException(status_code=404, detail="protocol version not found")
        return ProtocolManifest.model_validate(PROTOCOL_MANIFEST)

    def parse_preview(self, request: LLMParsePreviewRequest) -> LLMParsePreviewResponse:
        return self.llm_gateway.parse_preview(request)

    def render_preview(self, request: LLMRenderRequest) -> LLMRenderPreviewResponse:
        return self.llm_gateway.render_preview(request)

    def get_llm_health(self) -> LLMHealthResponse:
        return self.llm_gateway.health()

    def live_check(self, request: LLMLiveCheckRequest) -> LLMLiveCheckResponse:
        return self.llm_gateway.live_check(request)

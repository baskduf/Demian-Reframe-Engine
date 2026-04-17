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
    ChoiceOption,
    ClarificationBlock,
    CreateSessionRequest,
    EmotionScore,
    EventRequest,
    GuidanceBlock,
    InteractionStatus,
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
    EMOTION_OPTIONS = [
        ChoiceOption(option_id="anxiety", label="anxiety", description="Worry, tension, nervousness"),
        ChoiceOption(option_id="fear", label="fear", description="Threat-focused fear"),
        ChoiceOption(option_id="sadness", label="sadness", description="Low mood or disappointment"),
        ChoiceOption(option_id="shame", label="shame", description="Embarrassment or self-consciousness"),
    ]
    SAFETY_BEHAVIOR_EXAMPLES = [
        ChoiceOption(option_id="avoid", label="피했다", description="Avoided the task or situation"),
        ChoiceOption(option_id="check", label="계속 확인했다", description="Repeatedly checked for reassurance"),
        ChoiceOption(option_id="delay", label="미뤘다", description="Delayed starting or finishing the task"),
    ]
    EXPERIMENT_EXAMPLES = [
        ChoiceOption(option_id="small_step", label="작은 행동실험", description="Try one small step for 10-30 minutes"),
        ChoiceOption(option_id="reality_test", label="현실검증", description="Test one prediction with a concrete action"),
    ]
    STRUCTURED_STATES = {
        StateEnum.SITUATION_CAPTURE,
        StateEnum.WORRY_THOUGHT_CAPTURE,
        StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE,
    }
    GUIDANCE_BY_STATE = {
        StateEnum.RISK_SCREEN: GuidanceBlock(
            title="위험 스크린",
            description="고위험 신호가 있으면 CBT 흐름이 중단되고 crisis 상태로 전환됩니다.",
            examples=["해당 없으면 모든 위험 체크를 n으로 두세요."],
        ),
        StateEnum.ELIGIBILITY_CHECK: GuidanceBlock(
            title="적합성 확인",
            description="성인 여부와 현재 세션 목표가 GAD 관련인지 확인합니다.",
            examples=["성인인가요? y / 목표 상태: gad"],
        ),
        StateEnum.SITUATION_CAPTURE: GuidanceBlock(
            title="상황 입력",
            description="걱정이 커졌던 구체적 상황과 촉발 계기를 적습니다.",
            examples=["상황: 팀 프로젝트 발표가 있다", "촉발: 실수할까 봐 걱정됐다"],
        ),
        StateEnum.WORRY_THOUGHT_CAPTURE: GuidanceBlock(
            title="자동사고와 최악의 예측",
            description="그 순간 머리를 스친 생각과 최악의 예측을 적습니다.",
            examples=["자동사고: 나는 준비가 부족해", "최악의 예측: 발표를 망칠 거야"],
        ),
        StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE: GuidanceBlock(
            title="감정, 몸 반응, 안전행동",
            description="감정은 느낌, 몸 반응은 신체 변화, 안전행동은 불안을 줄이려고 피하거나 확인하는 행동입니다.",
            examples=["감정: anxiety", "몸 반응: 심장이 빨리 뛴다", "안전행동: 계속 확인한다"],
        ),
        StateEnum.DISTORTION_HYPOTHESIS: GuidanceBlock(
            title="인지왜곡 선택",
            description="현재 생각과 가장 가까운 왜곡 후보를 선택합니다.",
            examples=["uncertainty_focus", "catastrophizing"],
        ),
        StateEnum.EVIDENCE_FOR: GuidanceBlock(
            title="걱정을 지지하는 근거",
            description="걱정이 맞을 수도 있다고 느끼게 하는 사실이나 경험을 적습니다.",
            examples=["예전에 비슷한 발표에서 버벅인 적이 있다"],
        ),
        StateEnum.EVIDENCE_AGAINST: GuidanceBlock(
            title="걱정과 반대되는 근거",
            description="걱정이 100% 사실은 아닐 수 있다는 반대 사실이나 예외를 적습니다.",
            examples=["준비를 꽤 했다", "예전에도 결국 해냈다"],
        ),
        StateEnum.ALTERNATIVE_THOUGHT: GuidanceBlock(
            title="균형 잡힌 관점과 대응 문장",
            description="더 균형 잡힌 해석과 바로 써먹을 대응 문장을 적습니다.",
            examples=["균형 잡힌 관점: 긴장할 수 있지만 반드시 망하는 건 아니다", "대응 문장: 핵심만 천천히 말하자"],
        ),
        StateEnum.RE_RATE_ANXIETY: GuidanceBlock(
            title="불안 재평가",
            description="지금 남아 있는 불안을 점수로 적고 행동실험 필요 여부를 고릅니다.",
            examples=["불안 점수: 40", "행동실험 필요: n"],
        ),
        StateEnum.BEHAVIOR_EXPERIMENT: GuidanceBlock(
            title="행동실험",
            description="작게 실행할 행동과 시간 범위를 적습니다.",
            examples=["액션: 발표 핵심 3개만 20분 연습하기", "시간: 오늘 저녁 8시"],
        ),
        StateEnum.SUMMARY_PLAN: GuidanceBlock(
            title="요약 종료",
            description="지금까지 기록한 내용을 확인하고 세션을 종료합니다.",
            examples=["summary_ack: true"],
        ),
        StateEnum.CRISIS: GuidanceBlock(title="위험 중단", description="고위험 신호가 감지되어 CBT 흐름을 중단했습니다."),
        StateEnum.OUT_OF_SCOPE: GuidanceBlock(title="범위 종료", description="현재 세션 범위 밖이어서 일반 흐름을 종료했습니다."),
        StateEnum.CLOSE_SESSION: GuidanceBlock(title="세션 종료", description="구조화된 CBT 기록이 완료되었습니다."),
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

    @staticmethod
    def _weak_text(value: str) -> bool:
        lowered = value.strip().lower()
        weak_tokens = {
            "",
            "모르겠다",
            "잘 모르겠다",
            "글쎄",
            "잘모르겠다",
            "없다",
            "없음",
            "모름",
            "idk",
            "none",
        }
        return lowered in weak_tokens or len(lowered) < 4

    @staticmethod
    def _llm_clarification_assist(record: ThoughtRecord, state: StateEnum) -> list[str]:
        if not record.llm_needs_clarification:
            return []
        examples: list[str] = []
        if state == StateEnum.WORRY_THOUGHT_CAPTURE and record.llm_automatic_thought_candidates:
            examples.append(f"예: {record.llm_automatic_thought_candidates[0].text}")
        if state == StateEnum.SITUATION_CAPTURE and record.llm_situation_candidates:
            examples.append(f"예: {record.llm_situation_candidates[0].text}")
        if state == StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE and record.llm_behavior_candidates:
            examples.append(f"행동 예시: {record.llm_behavior_candidates[0].text}")
        return examples

    def _build_choices(self, state: StateEnum, record: ThoughtRecord) -> dict[str, list[ChoiceOption]]:
        choices: dict[str, list[ChoiceOption]] = {}
        if state == StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE:
            choices["emotion_labels"] = self.EMOTION_OPTIONS
            choices["safety_behavior_examples"] = self.SAFETY_BEHAVIOR_EXAMPLES
        if state == StateEnum.DISTORTION_HYPOTHESIS:
            choices["distortion_candidates"] = [
                ChoiceOption(option_id=item.distortion_id, label=item.label, description="Primary" if item.is_primary else "")
                for item in record.candidate_distortions
            ]
            if record.llm_distortion_candidates:
                choices["llm_distortion_candidates"] = [
                    ChoiceOption(option_id=item.label, label=item.label, description=f"confidence={item.confidence}")
                    for item in record.llm_distortion_candidates
                ]
        if state == StateEnum.BEHAVIOR_EXPERIMENT:
            choices["experiment_examples"] = self.EXPERIMENT_EXAMPLES
        return choices

    def _build_collected_slots(self, state: StateEnum, record: ThoughtRecord) -> dict:
        collected = dict(record.interaction_context.get(state.value, {}))
        if state == StateEnum.SITUATION_CAPTURE:
            if record.situation_text:
                collected.setdefault("situation_text", record.situation_text)
            if record.trigger_text:
                collected.setdefault("trigger_text", record.trigger_text)
        elif state == StateEnum.WORRY_THOUGHT_CAPTURE:
            if record.automatic_thought:
                collected.setdefault("automatic_thought", record.automatic_thought)
            if record.worry_prediction:
                collected.setdefault("worry_prediction", record.worry_prediction)
        elif state == StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE:
            if record.emotions:
                collected.setdefault("emotions", [item.model_dump() for item in record.emotions])
            if record.body_symptoms:
                collected.setdefault("body_symptoms", record.body_symptoms)
            if record.safety_behaviors:
                collected.setdefault("safety_behaviors", record.safety_behaviors)
        elif state == StateEnum.DISTORTION_HYPOTHESIS and record.selected_distortion_ids:
            collected.setdefault("selected_distortion_ids", record.selected_distortion_ids)
        elif state == StateEnum.EVIDENCE_FOR and record.evidence_for:
            collected.setdefault("evidence_for", record.evidence_for)
        elif state == StateEnum.EVIDENCE_AGAINST and record.evidence_against:
            collected.setdefault("evidence_against", record.evidence_against)
        elif state == StateEnum.ALTERNATIVE_THOUGHT and record.alternative_thought:
            collected.setdefault("alternative_thought", record.alternative_thought)
        elif state == StateEnum.RE_RATE_ANXIETY and record.re_rated_anxiety is not None:
            collected.setdefault("re_rated_anxiety", record.re_rated_anxiety)
        elif state == StateEnum.BEHAVIOR_EXPERIMENT and record.behavior_experiment:
            collected.setdefault("behavior_experiment", record.behavior_experiment.model_dump())
        return collected

    def _build_summary(self, record: ThoughtRecord) -> str:
        sections = [
            f"상황: {record.situation_text or '미입력'}",
            f"걱정: {record.automatic_thought or '미입력'} / 최악의 예측: {record.worry_prediction or '미입력'}",
            f"왜곡: {', '.join(record.selected_distortion_ids) if record.selected_distortion_ids else '미선택'}",
            f"반대 근거: {', '.join(record.evidence_against) if record.evidence_against else '미입력'}",
            f"균형 관점: {record.alternative_thought or '미입력'}",
        ]
        if record.behavior_experiment:
            sections.append(f"다음 행동: {record.behavior_experiment.action} ({record.behavior_experiment.timebox})")
        elif record.re_rated_anxiety is not None:
            sections.append(f"다음 행동: 재평가 불안 {record.re_rated_anxiety}")
        return "\n".join(sections)

    def _save_partial_payload(self, record: ThoughtRecord, state: StateEnum, payload: dict) -> None:
        record.interaction_context[state.value] = payload
        self.repository.save_thought_record(record)

    def _clear_partial_payload(self, record: ThoughtRecord, state: StateEnum) -> None:
        if state.value in record.interaction_context:
            record.interaction_context.pop(state.value, None)
            self.repository.save_thought_record(record)

    def _evaluate_response_quality(self, state: StateEnum, payload: dict, record: ThoughtRecord) -> tuple[ClarificationBlock | None, dict]:
        choices = self._build_choices(state, record)
        llm_examples = self._llm_clarification_assist(record, state)
        if state == StateEnum.SITUATION_CAPTURE:
            if self._weak_text(str(payload.get("situation_text", ""))):
                return ClarificationBlock(
                    reason_code="situation_too_short",
                    message="상황 설명이 너무 짧습니다. 걱정이 커졌던 장면을 조금 더 구체적으로 적어주세요.",
                    examples=["예: 팀 프로젝트 발표를 앞두고 있었다", *llm_examples],
                    missing_fields=["situation_text"],
                ), choices
            if self._weak_text(str(payload.get("trigger_text", ""))):
                return ClarificationBlock(
                    reason_code="trigger_too_short",
                    message="걱정을 촉발한 계기를 조금 더 구체적으로 적어주세요.",
                    examples=["예: 실수할까 봐 걱정됐다", *llm_examples],
                    missing_fields=["trigger_text"],
                ), choices
        if state == StateEnum.WORRY_THOUGHT_CAPTURE:
            if self._weak_text(str(payload.get("automatic_thought", ""))):
                return ClarificationBlock(
                    reason_code="automatic_thought_too_short",
                    message="자동적 사고가 너무 짧습니다. 머리를 스친 문장 형태로 적어주세요.",
                    examples=["예: 나는 준비가 부족해서 망칠 거야", *llm_examples],
                    missing_fields=["automatic_thought"],
                ), choices
            if self._weak_text(str(payload.get("worry_prediction", ""))):
                return ClarificationBlock(
                    reason_code="prediction_too_short",
                    message="최악의 예측이 너무 짧습니다. 앞으로 어떤 일이 벌어질 것 같은지 적어주세요.",
                    examples=["예: 발표를 망쳐서 평가가 나빠질 거야"],
                    missing_fields=["worry_prediction"],
                ), choices
        if state == StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE:
            safety_behaviors = payload.get("safety_behaviors") or []
            if not safety_behaviors:
                return ClarificationBlock(
                    reason_code="missing_safety_behavior",
                    message="안전행동은 불안을 줄이려고 피하거나 계속 확인한 행동입니다. 행동 형태로 적어주세요.",
                    examples=["예: 계속 확인했다", "예: 시작을 미뤘다", "예: 발표를 피했다"],
                    missing_fields=["safety_behaviors"],
                ), choices
            for item in safety_behaviors:
                if self._weak_text(str(item)) or "강박" in str(item) or "불안" in str(item):
                    return ClarificationBlock(
                        reason_code="invalid_safety_behavior",
                        message="안전행동은 상태 설명이 아니라 실제 행동이어야 합니다.",
                        examples=["예: 계속 확인했다", "예: 피했다", "예: 미뤘다"],
                        missing_fields=["safety_behaviors"],
                    ), choices
        if state in {StateEnum.EVIDENCE_FOR, StateEnum.EVIDENCE_AGAINST}:
            key = "evidence_for" if state == StateEnum.EVIDENCE_FOR else "evidence_against"
            values = payload.get(key) or []
            if not values:
                return ClarificationBlock(
                    reason_code=f"missing_{key}",
                    message="조금 더 구체적인 근거를 적어주세요.",
                    examples=["예: 예전에 비슷한 발표에서 버벅인 적이 있다" if key == "evidence_for" else "예: 준비를 꽤 했다"],
                    missing_fields=[key],
                ), choices
            for item in values:
                if self._weak_text(str(item)):
                    return ClarificationBlock(
                        reason_code=f"weak_{key}",
                        message="근거가 너무 짧거나 모호합니다. 사실이나 경험을 한 문장으로 적어주세요.",
                        examples=["예: 예전에 비슷한 발표에서 버벅인 적이 있다" if key == "evidence_for" else "예: 예전에도 결국 해냈다"],
                        missing_fields=[key],
                    ), choices
        if state == StateEnum.ALTERNATIVE_THOUGHT:
            balanced_view = str(payload.get("balanced_view", ""))
            coping_statement = str(payload.get("coping_statement", ""))
            if self._weak_text(balanced_view):
                return ClarificationBlock(
                    reason_code="weak_balanced_view",
                    message="균형 잡힌 관점이 너무 짧습니다. 반드시 망하는 것은 아니라는 식으로 더 구체적으로 적어주세요.",
                    examples=["예: 긴장할 수 있지만 반드시 망하는 것은 아니다"],
                    missing_fields=["balanced_view"],
                ), choices
            if self._weak_text(coping_statement) or balanced_view == coping_statement:
                return ClarificationBlock(
                    reason_code="weak_coping_statement",
                    message="대응 문장은 바로 행동으로 옮길 수 있어야 하고, 균형 관점과 같지 않아야 합니다.",
                    examples=["예: 오늘은 핵심 3가지만 정리하자"],
                    missing_fields=["coping_statement"],
                ), choices
        if state == StateEnum.BEHAVIOR_EXPERIMENT:
            action = str(payload.get("action", ""))
            if self._weak_text(action):
                return ClarificationBlock(
                    reason_code="weak_experiment_action",
                    message="행동실험 액션이 너무 짧습니다. 실제 행동을 더 구체적으로 적어주세요.",
                    examples=["예: 오늘 20분 동안 발표 첫 문단만 연습하기"],
                    missing_fields=["action"],
                ), choices
        return None, choices

    def _clarify_current_state(
        self,
        session: Session,
        record: ThoughtRecord,
        state: StateEnum,
        payload: dict,
        clarification: ClarificationBlock,
        template_id: str,
        state_data: dict | None = None,
    ) -> SessionEnvelope:
        self._save_partial_payload(record, state, payload)
        trace = self._transition(
            session,
            state,
            payload,
            [f"clarify:{clarification.reason_code}"],
            [template_id],
        )
        self.repository.add_event(
            SessionEvent(
                session_id=session.session_id,
                state_before=state,
                event_type="clarification",
                payload={
                    "state": state.value,
                    "reason_code": clarification.reason_code,
                    "missing_fields": clarification.missing_fields,
                },
                actor="system",
            )
        )
        return self._build_envelope(
            session,
            trace.transition_id,
            state_data=state_data or {},
            template_id=template_id,
            interaction_status=InteractionStatus.CLARIFY,
            clarification=clarification,
            choices=self._build_choices(state, record),
            collected_slots=self._build_collected_slots(state, record),
        )

    def _build_envelope(
        self,
        session: Session,
        trace_id=None,
        state_data=None,
        template_id=None,
        interaction_status: InteractionStatus = InteractionStatus.CLARIFY,
        clarification: ClarificationBlock | None = None,
        choices: dict[str, list[ChoiceOption]] | None = None,
        collected_slots: dict | None = None,
    ) -> SessionEnvelope:
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
            interaction_status=interaction_status,
            allowed_actions=allowed_actions(session.current_state),
            transition_trace_id=trace_id,
            state_data=merged_state_data,
            template_response=template_response,
            guidance=self.GUIDANCE_BY_STATE.get(session.current_state),
            choices=choices or {},
            clarification=clarification,
            collected_slots=collected_slots or {},
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
        record = ThoughtRecord(session_id=session.session_id)
        self.repository.save_thought_record(record)
        return self._build_envelope(
            session,
            state_data={"locale": request.locale},
            interaction_status=InteractionStatus.CLARIFY,
            choices=self._build_choices(session.current_state, record),
            collected_slots=self._build_collected_slots(session.current_state, record),
        )

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
            return self._build_envelope(
                session,
                trace.transition_id,
                {"risk_level": risk.risk_level, "triggered_rule_ids": risk.triggered_rule_ids},
                "risk.high",
                interaction_status=InteractionStatus.INTERRUPT,
            )

        template_id = "risk.moderate" if risk.risk_level == RiskLevel.MODERATE else "prompt.eligibility"
        trace = self._transition(session, StateEnum.ELIGIBILITY_CHECK, request.model_dump(), risk.triggered_rule_ids, [template_id])
        record = self._load_record(session_id)
        return self._build_envelope(
            session,
            trace.transition_id,
            {"risk_level": risk.risk_level, "triggered_rule_ids": risk.triggered_rule_ids},
            template_id,
            interaction_status=InteractionStatus.ADVANCE,
            choices=self._build_choices(session.current_state, record),
            collected_slots=self._build_collected_slots(session.current_state, record),
        )

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
                return self._build_envelope(
                    session,
                    trace.transition_id,
                    {"risk_level": risk.risk_level, "triggered_rule_ids": risk.triggered_rule_ids},
                    "risk.high",
                    interaction_status=InteractionStatus.INTERRUPT,
                )

        record = self._load_record(session_id)
        self.repository.add_event(SessionEvent(session_id=session_id, state_before=session.current_state, event_type=request.event_type, payload=request.payload))
        state = session.current_state
        payload = {**record.interaction_context.get(state.value, {}), **request.payload}
        payload, llm_state_data = self._apply_llm_structuring(session, record, payload)
        payload, validation_state_data = self._validate_event_payload(state, request.event_type, payload)
        llm_state_data = {**llm_state_data, **validation_state_data}

        if state == StateEnum.ELIGIBILITY_CHECK:
            if "invalid_fields" in validation_state_data:
                clarification = ClarificationBlock(
                    reason_code="invalid_eligibility_fields",
                    message="성인 여부와 목표 상태를 다시 확인해주세요.",
                    missing_fields=validation_state_data["invalid_fields"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.eligibility", llm_state_data)
            if not payload.get("is_adult", False) or payload.get("target_condition") != "gad":
                session.status = SessionStatus.CLOSED
                session.closed_reason = "out_of_scope"
                session.closed_at = datetime.now(UTC)
                trace = self._transition(session, StateEnum.OUT_OF_SCOPE, payload, ["eligibility_out_of_scope"], ["eligibility.out_of_scope"])
                self._clear_partial_payload(record, state)
                return self._build_envelope(
                    session,
                    trace.transition_id,
                    {"eligible": False},
                    "eligibility.out_of_scope",
                    interaction_status=InteractionStatus.INTERRUPT,
                )
            trace = self._transition(session, next_state(state), payload, ["eligibility_pass"], ["prompt.situation"])
            self._clear_partial_payload(record, state)
            return self._build_envelope(
                session,
                trace.transition_id,
                interaction_status=InteractionStatus.ADVANCE,
                choices=self._build_choices(session.current_state, record),
                collected_slots=self._build_collected_slots(session.current_state, record),
            )

        if state == StateEnum.SITUATION_CAPTURE:
            if "invalid_fields" in validation_state_data:
                clarification = ClarificationBlock(
                    reason_code="invalid_situation_fields",
                    message="상황과 촉발 계기를 다시 적어주세요.",
                    missing_fields=validation_state_data["invalid_fields"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.situation", llm_state_data)
            if not has_required_fields(state, payload):
                clarification = ClarificationBlock(
                    reason_code="missing_situation_fields",
                    message="상황과 촉발 계기를 모두 적어주세요.",
                    examples=["상황: 프로젝트 발표를 준비하고 있었다", "촉발: 실수할까 봐 걱정됐다"],
                    missing_fields=self._merge_missing_fields(["situation_text", "trigger_text"], record.llm_missing_fields),
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.situation", llm_state_data)
            clarification, choices = self._evaluate_response_quality(state, payload, record)
            if clarification is not None:
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.situation", {**llm_state_data, "choices_preview": choices})
            record.situation_text = payload["situation_text"]
            record.trigger_text = payload["trigger_text"]
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["situation_complete"], ["prompt.worry"])
            self._clear_partial_payload(record, state)
            return self._build_envelope(
                session,
                trace.transition_id,
                interaction_status=InteractionStatus.ADVANCE,
                choices=self._build_choices(session.current_state, record),
                collected_slots=self._build_collected_slots(session.current_state, record),
            )

        if state == StateEnum.WORRY_THOUGHT_CAPTURE:
            if "invalid_fields" in validation_state_data:
                clarification = ClarificationBlock(
                    reason_code="invalid_worry_fields",
                    message="자동사고와 최악의 예측을 다시 적어주세요.",
                    missing_fields=validation_state_data["invalid_fields"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.worry", llm_state_data)
            if not has_required_fields(state, payload):
                clarification = ClarificationBlock(
                    reason_code="missing_worry_fields",
                    message="자동사고와 최악의 예측을 모두 적어주세요.",
                    examples=["자동사고: 나는 준비가 부족해", "최악의 예측: 발표를 망칠 거야"],
                    missing_fields=self._merge_missing_fields(["automatic_thought", "worry_prediction"], record.llm_missing_fields),
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.worry", llm_state_data)
            clarification, _ = self._evaluate_response_quality(state, payload, record)
            if clarification is not None:
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.worry", llm_state_data)
            record.automatic_thought = payload["automatic_thought"]
            record.worry_prediction = payload["worry_prediction"]
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["worry_complete"], ["prompt.emotion"])
            self._clear_partial_payload(record, state)
            return self._build_envelope(
                session,
                trace.transition_id,
                interaction_status=InteractionStatus.ADVANCE,
                choices=self._build_choices(session.current_state, record),
                collected_slots=self._build_collected_slots(session.current_state, record),
            )

        if state == StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE:
            if "invalid_fields" in validation_state_data:
                clarification = ClarificationBlock(
                    reason_code="invalid_emotion_fields",
                    message="감정, 몸 반응, 안전행동 형식을 다시 확인해주세요.",
                    missing_fields=validation_state_data["invalid_fields"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.emotion", llm_state_data)
            if not has_required_fields(state, payload):
                clarification = ClarificationBlock(
                    reason_code="missing_emotion_fields",
                    message="감정과 몸 반응 또는 안전행동을 모두 적어주세요.",
                    examples=["감정: anxiety 80", "몸 반응: 심장이 빨리 뛴다", "안전행동: 계속 확인한다"],
                    missing_fields=self._merge_missing_fields(
                        ["emotions", "body_symptoms_or_safety_behaviors"], record.llm_missing_fields
                    ),
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.emotion", llm_state_data)
            clarification, _ = self._evaluate_response_quality(state, payload, record)
            if clarification is not None:
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.emotion", llm_state_data)
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
                interaction_status=InteractionStatus.ADVANCE,
                choices=self._build_choices(session.current_state, record),
                collected_slots=self._build_collected_slots(session.current_state, record),
            )

        if state == StateEnum.DISTORTION_HYPOTHESIS:
            if "invalid_fields" in validation_state_data:
                clarification = ClarificationBlock(
                    reason_code="invalid_distortion_selection",
                    message="왜곡 후보 ID를 다시 선택해주세요.",
                    missing_fields=validation_state_data["invalid_fields"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.distortion", llm_state_data)
            selected = payload.get("selected_distortion_ids") or [candidate.distortion_id for candidate in record.candidate_distortions[:1]]
            known_ids = {candidate.distortion_id for candidate in record.candidate_distortions}
            if payload.get("selected_distortion_ids") and not set(selected).issubset(known_ids):
                clarification = ClarificationBlock(
                    reason_code="unknown_distortion_choice",
                    message="현재 후보에 있는 왜곡 ID를 선택해주세요.",
                    examples=list(known_ids),
                    missing_fields=["selected_distortion_ids"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.distortion", llm_state_data)
            record.selected_distortion_ids = selected
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["distortion_selected"], ["prompt.evidence_for"])
            self._clear_partial_payload(record, state)
            return self._build_envelope(
                session,
                trace.transition_id,
                {"selected_distortion_ids": selected},
                interaction_status=InteractionStatus.ADVANCE,
                choices=self._build_choices(session.current_state, record),
                collected_slots=self._build_collected_slots(session.current_state, record),
            )

        if state == StateEnum.EVIDENCE_FOR:
            if "invalid_fields" in validation_state_data:
                clarification = ClarificationBlock(
                    reason_code="invalid_evidence_for",
                    message="걱정을 지지하는 근거를 다시 적어주세요.",
                    missing_fields=validation_state_data["invalid_fields"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.evidence_for", llm_state_data)
            if not has_required_fields(state, payload):
                clarification = ClarificationBlock(
                    reason_code="missing_evidence_for",
                    message="걱정을 지지하는 근거를 한 가지 이상 적어주세요.",
                    examples=["예: 예전에 비슷한 발표에서 버벅인 적이 있다"],
                    missing_fields=["evidence_for"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.evidence_for")
            clarification, _ = self._evaluate_response_quality(state, payload, record)
            if clarification is not None:
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.evidence_for", llm_state_data)
            record.evidence_for = payload["evidence_for"]
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["evidence_for_complete"], ["prompt.evidence_against"])
            self._clear_partial_payload(record, state)
            return self._build_envelope(
                session,
                trace.transition_id,
                interaction_status=InteractionStatus.ADVANCE,
                choices=self._build_choices(session.current_state, record),
                collected_slots=self._build_collected_slots(session.current_state, record),
            )

        if state == StateEnum.EVIDENCE_AGAINST:
            if "invalid_fields" in validation_state_data:
                clarification = ClarificationBlock(
                    reason_code="invalid_evidence_against",
                    message="걱정과 반대되는 근거를 다시 적어주세요.",
                    missing_fields=validation_state_data["invalid_fields"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.evidence_against", llm_state_data)
            if not has_required_fields(state, payload):
                clarification = ClarificationBlock(
                    reason_code="missing_evidence_against",
                    message="걱정과 반대되는 사실이나 예외를 한 가지 이상 적어주세요.",
                    examples=["예: 준비를 꽤 했다", "예: 예전에도 결국 해냈다"],
                    missing_fields=["evidence_against"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.evidence_against")
            clarification, _ = self._evaluate_response_quality(state, payload, record)
            if clarification is not None:
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.evidence_against", llm_state_data)
            record.evidence_against = payload["evidence_against"]
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["evidence_against_complete"], ["prompt.alternative"])
            self._clear_partial_payload(record, state)
            return self._build_envelope(
                session,
                trace.transition_id,
                interaction_status=InteractionStatus.ADVANCE,
                choices=self._build_choices(session.current_state, record),
                collected_slots=self._build_collected_slots(session.current_state, record),
            )

        if state == StateEnum.ALTERNATIVE_THOUGHT:
            if "invalid_fields" in validation_state_data:
                clarification = ClarificationBlock(
                    reason_code="invalid_alternative_fields",
                    message="균형 관점과 대응 문장을 다시 적어주세요.",
                    missing_fields=validation_state_data["invalid_fields"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.alternative", llm_state_data)
            if not has_required_fields(state, payload):
                clarification = ClarificationBlock(
                    reason_code="missing_alternative_fields",
                    message="균형 잡힌 관점과 대응 문장을 모두 적어주세요.",
                    examples=["균형 관점: 긴장할 수 있지만 반드시 망하는 것은 아니다", "대응 문장: 오늘은 핵심 3가지만 정리하자"],
                    missing_fields=["balanced_view", "coping_statement"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.alternative")
            clarification, _ = self._evaluate_response_quality(state, payload, record)
            if clarification is not None:
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.alternative", llm_state_data)
            record.alternative_thought = (
                f"균형 잡힌 관점: {payload['balanced_view']} / "
                f"실행할 대응 문장: {payload['coping_statement']}"
            )
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["alternative_complete"], ["prompt.re_rate"])
            self._clear_partial_payload(record, state)
            return self._build_envelope(
                session,
                trace.transition_id,
                {"alternative_thought": record.alternative_thought},
                interaction_status=InteractionStatus.ADVANCE,
                choices=self._build_choices(session.current_state, record),
                collected_slots=self._build_collected_slots(session.current_state, record),
            )

        if state == StateEnum.RE_RATE_ANXIETY:
            if "invalid_fields" in validation_state_data:
                clarification = ClarificationBlock(
                    reason_code="invalid_rerate_fields",
                    message="불안 점수와 행동실험 필요 여부를 다시 입력해주세요.",
                    missing_fields=validation_state_data["invalid_fields"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.re_rate", llm_state_data)
            if not has_required_fields(state, payload):
                clarification = ClarificationBlock(
                    reason_code="missing_rerate_fields",
                    message="불안 점수와 행동실험 필요 여부를 모두 입력해주세요.",
                    missing_fields=["re_rated_anxiety", "experiment_required"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.re_rate")
            record.re_rated_anxiety = payload["re_rated_anxiety"]
            self.repository.save_thought_record(record)
            if payload["experiment_required"]:
                trace = self._transition(session, next_state(state), payload, ["experiment_required"], ["prompt.experiment"])
                self._clear_partial_payload(record, state)
                return self._build_envelope(
                    session,
                    trace.transition_id,
                    interaction_status=InteractionStatus.ADVANCE,
                    choices=self._build_choices(session.current_state, record),
                    collected_slots=self._build_collected_slots(session.current_state, record),
                )
            trace = self._transition(session, StateEnum.SUMMARY_PLAN, payload, ["experiment_skipped"], ["summary.complete"])
            self._clear_partial_payload(record, state)
            return self._build_envelope(
                session,
                trace.transition_id,
                interaction_status=InteractionStatus.ADVANCE,
                choices=self._build_choices(session.current_state, record),
                collected_slots=self._build_collected_slots(session.current_state, record),
            )

        if state == StateEnum.BEHAVIOR_EXPERIMENT:
            if "invalid_fields" in validation_state_data:
                clarification = ClarificationBlock(
                    reason_code="invalid_experiment_fields",
                    message="행동실험 정보를 다시 적어주세요.",
                    missing_fields=validation_state_data["invalid_fields"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.experiment", llm_state_data)
            if not has_required_fields(state, payload):
                clarification = ClarificationBlock(
                    reason_code="missing_experiment_fields",
                    message="행동실험 액션과 시간 범위를 모두 적어주세요.",
                    missing_fields=["action", "timebox"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.experiment")
            clarification, _ = self._evaluate_response_quality(state, payload, record)
            if clarification is not None:
                return self._clarify_current_state(session, record, state, payload, clarification, "prompt.experiment", llm_state_data)
            record.behavior_experiment = BehaviorExperiment(action=payload["action"], timebox=payload["timebox"], hypothesis=payload.get("hypothesis"))
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["experiment_complete"], ["summary.complete"])
            self._clear_partial_payload(record, state)
            return self._build_envelope(
                session,
                trace.transition_id,
                interaction_status=InteractionStatus.ADVANCE,
                choices=self._build_choices(session.current_state, record),
                collected_slots=self._build_collected_slots(session.current_state, record),
            )

        if state == StateEnum.SUMMARY_PLAN:
            if "invalid_fields" in validation_state_data:
                clarification = ClarificationBlock(
                    reason_code="invalid_summary_ack",
                    message="요약 확인 여부를 다시 입력해주세요.",
                    missing_fields=validation_state_data["invalid_fields"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "summary.complete", llm_state_data)
            if not has_required_fields(state, payload):
                clarification = ClarificationBlock(
                    reason_code="missing_summary_ack",
                    message="요약을 확인하고 종료할지 선택해주세요.",
                    missing_fields=["summary_ack"],
                )
                return self._clarify_current_state(session, record, state, payload, clarification, "summary.complete")
            record.final_summary = self._build_summary(record)
            self.repository.save_thought_record(record)
            trace = self._transition(session, next_state(state), payload, ["summary_ack"], ["summary.complete"])
            self._clear_partial_payload(record, state)
            return self._build_envelope(
                session,
                trace.transition_id,
                {"final_summary": record.final_summary},
                interaction_status=InteractionStatus.ADVANCE,
            )

        raise HTTPException(status_code=400, detail=f"unsupported state transition from {state}")

    def get_session(self, session_id: UUID) -> SessionEnvelope:
        session = self._load_session(session_id)
        record = self._load_record(session_id)
        state_data = {}
        if session.current_state == StateEnum.DISTORTION_HYPOTHESIS:
            state_data["candidate_distortions"] = [candidate.model_dump() for candidate in record.candidate_distortions]
            state_data["llm_distortion_candidates"] = [candidate.model_dump() for candidate in record.llm_distortion_candidates]
        if record.final_summary:
            state_data["final_summary"] = record.final_summary
        return self._build_envelope(
            session,
            state_data=state_data,
            interaction_status=InteractionStatus.CLARIFY,
            choices=self._build_choices(session.current_state, record),
            collected_slots=self._build_collected_slots(session.current_state, record),
        )

    def get_artifacts(self, session_id: UUID) -> ArtifactsResponse:
        record = self._load_record(session_id)
        if record.final_summary is None and record.alternative_thought:
            record.final_summary = self._build_summary(record)
            self.repository.save_thought_record(record)
        return ArtifactsResponse(session_id=session_id, thought_record=record)

    def get_audit(self, session_id: UUID) -> AuditResponse:
        return AuditResponse(
            session_id=session_id,
            transitions=self.repository.list_transitions(session_id),
            risks=self.repository.list_risks(session_id),
            events=self.repository.list_events(session_id),
            llm_invocations=self.repository.list_llm_invocations(session_id),
        )

    def reassess_risk(self, session_id: UUID, request: RiskScreenRequest) -> SessionEnvelope:
        session = self._load_session(session_id)
        risk = evaluate_risk(session_id, request)
        self.repository.add_risk(risk)
        self.repository.add_event(
            SessionEvent(
                session_id=session_id,
                state_before=session.current_state,
                event_type="risk_reassessment",
                payload=request.model_dump(),
            )
        )

        if risk.risk_level == RiskLevel.HIGH:
            session.status = SessionStatus.ESCALATED
            session.closed_at = datetime.now(UTC)
            session.closed_reason = "safety_escalation"
            trace = self._transition(session, StateEnum.CRISIS, request.model_dump(), risk.triggered_rule_ids, ["risk.high"])
            return self._build_envelope(
                session,
                trace.transition_id,
                {"risk_level": risk.risk_level, "triggered_rule_ids": risk.triggered_rule_ids},
                "risk.high",
                interaction_status=InteractionStatus.INTERRUPT,
            )

        template_id = PROMPT_BY_STATE.get(session.current_state)
        trace = self._transition(session, session.current_state, request.model_dump(), risk.triggered_rule_ids, [template_id] if template_id else [])
        return self._build_envelope(
            session,
            trace.transition_id,
            {"risk_level": risk.risk_level, "triggered_rule_ids": risk.triggered_rule_ids},
            template_id,
            interaction_status=InteractionStatus.CLARIFY,
            choices=self._build_choices(session.current_state, self._load_record(session_id)),
            collected_slots=self._build_collected_slots(session.current_state, self._load_record(session_id)),
        )

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

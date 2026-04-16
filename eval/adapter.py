from __future__ import annotations

import time

from app.config.llm import OPENAI_ENABLE_LIVE_EVAL, live_call_available
from app.services.llm_gateway import LLMGateway
from eval.models import EvalCase, EvalPrediction


def live_eval_enabled() -> bool:
    return OPENAI_ENABLE_LIVE_EVAL and live_call_available()


def predict_case_with_gateway(case: EvalCase, gateway: LLMGateway) -> EvalPrediction:
    started = time.perf_counter()
    structured_output, invocation = gateway.parse_structured(session_id=None, state=case.state, free_text=case.free_text)
    risk_flags = []
    risk_prompt_version = ""
    if invocation.succeeded:
        risk_flags, risk_invocation = gateway.assist_risk(session_id=None, state=case.state, free_text=case.free_text)
        risk_prompt_version = risk_invocation.prompt_version
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    return EvalPrediction(
        case_id=case.case_id,
        situation=[item.text for item in structured_output.situation_candidates],
        automatic_thought=[item.text for item in structured_output.automatic_thought_candidates],
        emotion_labels=[item.label for item in structured_output.emotion_candidates],
        behavior=[item.text for item in structured_output.behavior_candidates],
        distortion_candidates=[item.label for item in structured_output.distortion_candidates],
        risk_flags=[item.flag for item in risk_flags or structured_output.risk_flags],
        needs_clarification=structured_output.needs_clarification,
        missing_fields=structured_output.missing_fields,
        schema_valid=invocation.succeeded,
        fallback_used=not invocation.succeeded,
        banned_content=invocation.error_code == "banned_content",
        latency_ms=latency_ms,
        source="live",
        model_name=invocation.model_name,
        prompt_version=invocation.prompt_version,
        risk_prompt_version=risk_prompt_version,
    )

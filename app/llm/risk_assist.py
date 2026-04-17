from __future__ import annotations

from typing import Any

from app.config.llm import OPENAI_MODEL_RISK_ASSIST
from app.llm.client import OpenAIClientError, OpenAIResponsesClient
from app.llm.contracts import ALLOWED_RISK_FLAGS, CandidateRiskFlag, LLMInvocationLog
from app.llm.prompts import RISK_ASSIST_PROMPT_VERSION, RISK_ASSIST_SYSTEM_PROMPT


RISK_FLAG_ALIASES = {
    "suicidal_intent": "suicidal_intent",
    "suicide_intent": "suicidal_intent",
    "self_harm_intent": "suicidal_intent",
    "passive_death_wish": "passive_death_wish",
    "death_wish": "passive_death_wish",
    "wish_to_disappear": "passive_death_wish",
    "hopelessness": "hopelessness",
    "despair": "hopelessness",
    "psychotic_expression": "psychotic_expression",
    "paranoia": "psychotic_expression",
    "hallucination": "psychotic_expression",
    "acute_deterioration": "acute_deterioration",
    "panic_dyscontrol": "acute_deterioration",
}

RISK_FALLBACK_MARKERS: dict[str, tuple[str, ...]] = {
    "suicidal_intent": ("죽고 싶", "자살", "끝내고 싶", "방법이 떠오", "나를 해치"),
    "passive_death_wish": ("사라지고 싶", "없어지고 싶", "그냥 없어졌으면", "깨어나지 않았으면"),
    "hopelessness": ("희망이 없", "아무 의미 없", "다 끝났", "소용없"),
    "psychotic_expression": ("감시하", "목소리", "누가 나를", "해코지", "쫓아"),
    "acute_deterioration": ("통제가 안", "무너질 것 같", "패닉", "멈출 수 없", "완전히 무너"),
}


def _normalize_risk_flag(flag: str) -> str:
    normalized = flag.strip().lower()
    if normalized in ALLOWED_RISK_FLAGS:
        return normalized
    return RISK_FLAG_ALIASES.get(normalized, normalized)


def _normalize_risk_payload(parsed: dict[str, Any]) -> dict[str, Any]:
    normalized_flags = []
    for item in parsed.get("risk_flags", []):
        candidate = dict(item)
        candidate["flag"] = _normalize_risk_flag(str(candidate.get("flag", "")))
        normalized_flags.append(candidate)
    return {"risk_flags": normalized_flags}


def _fallback_risk_flags(free_text: str) -> list[CandidateRiskFlag]:
    lowered = free_text.lower()
    flags: list[CandidateRiskFlag] = []
    for flag, markers in RISK_FALLBACK_MARKERS.items():
        for marker in markers:
            if marker in lowered:
                flags.append(
                    CandidateRiskFlag(
                        flag=flag,
                        confidence=0.65,
                        evidence_span=marker,
                    )
                )
                break
    return flags


class LLMRiskAssist:
    def __init__(self, client: OpenAIResponsesClient) -> None:
        self.client = client

    def assess(self, *, session_id, state, free_text: str) -> tuple[list[CandidateRiskFlag], LLMInvocationLog]:
        user_prompt = (
            f"State: {state.value}\n"
            f"User text: {free_text}\n\n"
            "Return only candidate risk flags related to self-harm, suicide, psychotic-like expression, or acute deterioration."
        )
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "risk_flags": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "flag": {"type": "string", "enum": list(ALLOWED_RISK_FLAGS)},
                            "confidence": {"type": "number"},
                            "evidence_span": {"type": "string"},
                        },
                        "required": ["flag", "confidence", "evidence_span"],
                    },
                }
            },
            "required": ["risk_flags"],
        }
        try:
            raw_response, parsed = self.client.request_json(
                model=OPENAI_MODEL_RISK_ASSIST,
                system_prompt=RISK_ASSIST_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                schema_name="cbt_risk_assist",
                schema=schema,
            )
            parsed = _normalize_risk_payload(parsed)
            flags = [CandidateRiskFlag.model_validate(item) for item in parsed["risk_flags"]]
            if not flags:
                flags = _fallback_risk_flags(free_text)
            log = LLMInvocationLog(
                session_id=session_id,
                state=state,
                task_type="risk_assist",
                model_name=OPENAI_MODEL_RISK_ASSIST,
                model_version=OPENAI_MODEL_RISK_ASSIST,
                prompt_version=RISK_ASSIST_PROMPT_VERSION,
                request_hash=self.client._hash_text(user_prompt),
                response_hash=self.client._hash_text(raw_response),
                raw_response=raw_response,
                parsed_output={"risk_flags": [flag.model_dump() for flag in flags]},
                succeeded=True,
            )
            return flags, log
        except OpenAIClientError as exc:
            fallback_flags = _fallback_risk_flags(free_text)
            log = LLMInvocationLog(
                session_id=session_id,
                state=state,
                task_type="risk_assist",
                model_name=OPENAI_MODEL_RISK_ASSIST,
                model_version=OPENAI_MODEL_RISK_ASSIST,
                prompt_version=RISK_ASSIST_PROMPT_VERSION,
                request_hash=self.client._hash_text(user_prompt),
                response_hash=self.client._hash_text(str(exc)),
                raw_response=str(exc),
                parsed_output={"risk_flags": [flag.model_dump() for flag in fallback_flags]},
                succeeded=not fallback_flags,
                error_code=None if fallback_flags else exc.code,
            )
            return fallback_flags, log

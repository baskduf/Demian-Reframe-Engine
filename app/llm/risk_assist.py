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
                parsed_output={"risk_flags": []},
                succeeded=False,
                error_code=exc.code,
            )
            return [], log

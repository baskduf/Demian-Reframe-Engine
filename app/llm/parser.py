from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.config.llm import OPENAI_MODEL_STRUCTURER
from app.llm.client import OpenAIClientError, OpenAIResponsesClient
from app.llm.contracts import ALLOWED_EMOTION_LABELS, LLMInvocationLog, LLMStructuredOutput
from app.llm.prompts import PARSER_PROMPT_VERSION, PARSER_SYSTEM_PROMPT
from app.schemas.models import StateEnum


STRUCTURED_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "situation_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "confidence": {"type": "number"},
                    "evidence_span": {"type": "string"},
                },
                "required": ["text", "confidence", "evidence_span"],
            },
        },
        "automatic_thought_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "confidence": {"type": "number"},
                    "evidence_span": {"type": "string"},
                },
                "required": ["text", "confidence", "evidence_span"],
            },
        },
        "emotion_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "label": {"type": "string", "enum": list(ALLOWED_EMOTION_LABELS)},
                    "intensity_hint": {"type": "integer"},
                    "confidence": {"type": "number"},
                    "evidence_span": {"type": "string"},
                },
                "required": ["label", "intensity_hint", "confidence", "evidence_span"],
            },
        },
        "behavior_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "text": {"type": "string"},
                    "confidence": {"type": "number"},
                    "evidence_span": {"type": "string"},
                },
                "required": ["text", "confidence", "evidence_span"],
            },
        },
        "distortion_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "label": {"type": "string"},
                    "confidence": {"type": "number"},
                    "rationale_code": {"type": "string"},
                },
                "required": ["label", "confidence", "rationale_code"],
            },
        },
        "risk_flags": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "flag": {"type": "string"},
                    "confidence": {"type": "number"},
                    "evidence_span": {"type": "string"},
                },
                "required": ["flag", "confidence", "evidence_span"],
            },
        },
        "needs_clarification": {"type": "boolean"},
        "missing_fields": {"type": "array", "items": {"type": "string"}},
        "confidence": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "overall": {"type": "number"},
                "situation": {"type": "number"},
                "automatic_thought": {"type": "number"},
                "emotion": {"type": "number"},
                "behavior": {"type": "number"},
                "distortion": {"type": "number"},
                "risk": {"type": "number"},
            },
            "required": [
                "overall",
                "situation",
                "automatic_thought",
                "emotion",
                "behavior",
                "distortion",
                "risk",
            ],
        },
    },
    "required": [
        "situation_candidates",
        "automatic_thought_candidates",
        "emotion_candidates",
        "behavior_candidates",
        "distortion_candidates",
        "risk_flags",
        "needs_clarification",
        "missing_fields",
        "confidence",
    ],
}

BANNED_TERMS = ("diagnosis", "diagnosed", "delusion", "psychosis", "major depressive disorder", "schizophrenia")


def _contains_banned_terms(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_contains_banned_terms(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_banned_terms(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return any(term in lowered for term in BANNED_TERMS)
    return False


EMOTION_LABEL_ALIASES = {
    "불안": "anxiety",
    "긴장": "anxiety",
    "초조": "anxiety",
    "anxious": "anxiety",
    "anxiety": "anxiety",
    "fear": "fear",
    "afraid": "fear",
    "scared": "fear",
    "무서움": "fear",
    "겁": "fear",
    "두려움": "fear",
    "panic": "panic",
    "panic attack": "panic",
    "패닉": "panic",
    "공황": "panic",
    "shame": "shame",
    "ashamed": "shame",
    "embarrassed": "shame",
    "부끄러움": "shame",
    "창피": "shame",
    "수치": "shame",
    "sadness": "sadness",
    "sad": "sadness",
    "depressed": "sadness",
    "슬픔": "sadness",
    "우울": "sadness",
    "despair": "despair",
    "hopeless": "despair",
    "절망": "despair",
    "희망없음": "despair",
}


def _normalize_emotion_label(label: str) -> str:
    normalized = label.strip().lower()
    if normalized in ALLOWED_EMOTION_LABELS:
        return normalized
    for alias, canonical in EMOTION_LABEL_ALIASES.items():
        if alias in normalized:
            return canonical
    return normalized


def _normalize_structured_output(parsed: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(parsed)
    normalized_emotions = []
    for item in parsed.get("emotion_candidates", []):
        candidate = dict(item)
        candidate["label"] = _normalize_emotion_label(str(candidate.get("label", "")))
        normalized_emotions.append(candidate)
    normalized["emotion_candidates"] = normalized_emotions
    return normalized


class LLMParser:
    def __init__(self, client: OpenAIResponsesClient) -> None:
        self.client = client

    def parse(self, *, session_id, state: StateEnum, free_text: str) -> tuple[LLMStructuredOutput, LLMInvocationLog]:
        user_prompt = (
            f"Current CBT state: {state.value}\n"
            f"User text:\n{free_text}\n\n"
            "Return structured CBT candidates as JSON."
        )
        try:
            raw_response, parsed = self.client.request_json(
                model=OPENAI_MODEL_STRUCTURER,
                system_prompt=PARSER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                schema_name="cbt_structured_output",
                schema=STRUCTURED_OUTPUT_SCHEMA,
            )
            parsed = _normalize_structured_output(parsed)
            if _contains_banned_terms(parsed):
                raise OpenAIClientError("banned_content", "Structured output contained banned clinical language")
            output = LLMStructuredOutput.model_validate(parsed)
            log = LLMInvocationLog(
                session_id=session_id,
                state=state,
                task_type="parse_structured",
                model_name=OPENAI_MODEL_STRUCTURER,
                model_version=OPENAI_MODEL_STRUCTURER,
                prompt_version=PARSER_PROMPT_VERSION,
                request_hash=self.client._hash_text(user_prompt),
                response_hash=self.client._hash_text(raw_response),
                raw_response=raw_response,
                parsed_output=output.model_dump(),
                succeeded=True,
            )
            return output, log
        except (OpenAIClientError, ValidationError, json.JSONDecodeError) as exc:
            fallback = LLMStructuredOutput(needs_clarification=True, missing_fields=["manual_structuring_required"])
            log = LLMInvocationLog(
                session_id=session_id,
                state=state,
                task_type="parse_structured",
                model_name=OPENAI_MODEL_STRUCTURER,
                model_version=OPENAI_MODEL_STRUCTURER,
                prompt_version=PARSER_PROMPT_VERSION,
                request_hash=self.client._hash_text(user_prompt),
                response_hash=self.client._hash_text(str(exc)),
                raw_response=str(exc),
                parsed_output=fallback.model_dump(),
                succeeded=False,
                error_code="schema_validation_failed" if isinstance(exc, ValidationError) else getattr(exc, "code", "parse_failed"),
            )
            return fallback, log

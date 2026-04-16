from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.config.llm import OPENAI_MODEL_STRUCTURER
from app.llm.client import OpenAIClientError, OpenAIResponsesClient
from app.llm.contracts import LLMInvocationLog, LLMStructuredOutput
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
                    "label": {"type": "string"},
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
            "additionalProperties": {"type": "number"},
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
                error_code=getattr(exc, "code", "parse_failed"),
            )
            return fallback, log

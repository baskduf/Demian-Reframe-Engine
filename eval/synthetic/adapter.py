from __future__ import annotations

import json
import random
from uuid import uuid4

from pydantic import ValidationError

from app.config.llm import OPENAI_MODEL_SYNTHETIC_GENERATOR
from app.llm.client import OpenAIClientError, OpenAIResponsesClient
from app.llm.contracts import ALLOWED_DISTORTION_LABELS, ALLOWED_EMOTION_LABELS, ALLOWED_RISK_FLAGS
from eval.synthetic.models import SyntheticCaseDraft, SyntheticCaseRequest, SyntheticRawRecord
from eval.synthetic.prompts import SYNTHETIC_GENERATOR_PROMPT_VERSION, SYNTHETIC_GENERATOR_SYSTEM_PROMPT

SYNTHETIC_CASE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "case_id": {"type": "string"},
        "state": {"type": "string", "enum": ["situation_capture", "worry_thought_capture", "emotion_body_behavior_capture"]},
        "language": {"type": "string", "enum": ["ko"]},
        "free_text": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "source_type": {"type": "string", "enum": ["synthetic"]},
        "generation_run_id": {"type": "string"},
        "generator_model": {"type": "string"},
        "generator_prompt_version": {"type": "string"},
        "review_status": {"type": "string", "enum": ["pending"]},
        "review_notes": {"type": "string"},
        "gold": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "situation": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"acceptable": {"type": "array", "items": {"type": "string"}}},
                    "required": ["acceptable"],
                },
                "automatic_thought": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"acceptable": {"type": "array", "items": {"type": "string"}}},
                    "required": ["acceptable"],
                },
                "emotion": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"acceptable_labels": {"type": "array", "items": {"type": "string", "enum": list(ALLOWED_EMOTION_LABELS)}}},
                    "required": ["acceptable_labels"],
                },
                "behavior": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"acceptable": {"type": "array", "items": {"type": "string"}}},
                    "required": ["acceptable"],
                },
                "distortion_candidates": {"type": "array", "items": {"type": "string", "enum": list(ALLOWED_DISTORTION_LABELS)}},
                "risk_expected_flags": {"type": "array", "items": {"type": "string", "enum": list(ALLOWED_RISK_FLAGS)}},
                "risk_expected_level": {"type": "string", "enum": ["none", "moderate", "high"]},
                "needs_clarification": {"type": "boolean"},
                "missing_fields": {"type": "array", "items": {"type": "string"}},
                "notes": {"type": "string"},
            },
            "required": [
                "situation",
                "automatic_thought",
                "emotion",
                "behavior",
                "distortion_candidates",
                "risk_expected_flags",
                "risk_expected_level",
                "needs_clarification",
                "missing_fields",
                "notes",
            ],
        },
    },
    "required": [
        "case_id",
        "state",
        "language",
        "free_text",
        "tags",
        "gold",
        "source_type",
        "generation_run_id",
        "generator_model",
        "generator_prompt_version",
        "review_status",
        "review_notes",
    ],
}


class SyntheticGenerator:
    def __init__(self, client: OpenAIResponsesClient | None = None, model_name: str = OPENAI_MODEL_SYNTHETIC_GENERATOR) -> None:
        self.client = client or OpenAIResponsesClient()
        self.model_name = model_name

    @property
    def enabled(self) -> bool:
        return self.client.enabled

    def generate_case(self, *, generation_run_id: str, request: SyntheticCaseRequest) -> SyntheticRawRecord:
        request_payload = request.model_dump(mode="json")
        if not self.enabled:
            return SyntheticRawRecord(
                record_id=str(uuid4()),
                generation_run_id=generation_run_id,
                request=request,
                generator_model=self.model_name,
                generator_prompt_version=SYNTHETIC_GENERATOR_PROMPT_VERSION,
                request_payload=request_payload,
                raw_response="",
                succeeded=False,
                error_code="llm_disabled",
            )

        user_prompt = json.dumps(
            {
                "request_id": request.request_id,
                "primary_tag": request.primary_tag,
                "target_state": request.state.value,
                "language": request.language,
                "risk_severity": request.risk_severity,
            },
            ensure_ascii=False,
        )

        try:
            raw_response, parsed = self.client.request_json(
                model=self.model_name,
                system_prompt=SYNTHETIC_GENERATOR_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                schema_name="synthetic_case_draft",
                schema=SYNTHETIC_CASE_SCHEMA,
            )
            parsed_case = SyntheticCaseDraft.model_validate(parsed)
            parsed_case.generation_run_id = generation_run_id
            parsed_case.generator_model = self.model_name
            parsed_case.generator_prompt_version = SYNTHETIC_GENERATOR_PROMPT_VERSION
            parsed_case.source_type = "synthetic"
            parsed_case.review_status = "pending"
            if request.primary_tag not in parsed_case.tags:
                parsed_case.tags = [request.primary_tag, *parsed_case.tags]
            return SyntheticRawRecord(
                record_id=str(uuid4()),
                generation_run_id=generation_run_id,
                request=request,
                generator_model=self.model_name,
                generator_prompt_version=SYNTHETIC_GENERATOR_PROMPT_VERSION,
                request_payload=request_payload,
                raw_response=raw_response,
                succeeded=True,
                parsed_case=parsed_case,
            )
        except (OpenAIClientError, ValidationError) as exc:
            error_code = exc.code if isinstance(exc, OpenAIClientError) else "schema_validation_failed"
            return SyntheticRawRecord(
                record_id=str(uuid4()),
                generation_run_id=generation_run_id,
                request=request,
                generator_model=self.model_name,
                generator_prompt_version=SYNTHETIC_GENERATOR_PROMPT_VERSION,
                request_payload=request_payload,
                raw_response="",
                succeeded=False,
                error_code=error_code,
            )


def weighted_choices(counts: dict[str, int], *, total: int, rng: random.Random) -> list[str]:
    keys = list(counts)
    weights = [counts[key] for key in keys]
    total_weight = sum(weights)
    normalized = [(weight / total_weight) * total for weight in weights]
    assigned = [int(value) for value in normalized]
    remainder = total - sum(assigned)
    order = sorted(range(len(keys)), key=lambda index: normalized[index] - assigned[index], reverse=True)
    for index in order[:remainder]:
        assigned[index] += 1
    choices: list[str] = []
    for key, qty in zip(keys, assigned):
        choices.extend([key] * qty)
    rng.shuffle(choices)
    return choices

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from app.config.llm import OPENAI_MODEL_STRUCTURER
from app.llm.client import OpenAIClientError, OpenAIResponsesClient
from app.llm.contracts import ALLOWED_DISTORTION_LABELS, ALLOWED_EMOTION_LABELS, LLMInvocationLog, LLMStructuredOutput
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
        "worry_prediction_candidates": {
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
                    "label": {"type": "string", "enum": list(ALLOWED_DISTORTION_LABELS)},
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
        "worry_prediction_candidates",
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
FUTURE_MARKERS = ("will", "going to", "might", "could", "probably", "definitely", "결국", "분명", "망치면", "잘못될", "어쩌나", "같아")
SELF_OR_OTHER_JUDGMENT_MARKERS = ("i am", "i'm", "they will think", "people will think", "나는", "내가", "다들", "사람들이", "무능", "문제")
AMBIGUITY_MARKERS = (
    "모르겠",
    "잘 모르",
    "잘 안",
    "막연",
    "정확히",
    "설명은 잘 안",
    "뭐라고 말",
    "안 잡혀",
    "not sure",
)
DIRECT_EMOTION_MARKERS = (
    "불안",
    "긴장",
    "초조",
    "무섭",
    "겁",
    "두렵",
    "공황",
    "패닉",
    "창피",
    "부끄",
    "수치",
    "우울",
    "슬프",
    "절망",
)
BODY_MARKERS = (
    "가슴",
    "심장",
    "숨",
    "손이 떨",
    "몸이 굳",
    "배가 아프",
    "두근",
    "조여",
    "초조해서",
    "잠을 거의 못",
)
STATE_REQUIRED_MISSING_FIELDS: dict[StateEnum, tuple[str, ...]] = {
    StateEnum.SITUATION_CAPTURE: ("situation", "trigger_text"),
    StateEnum.WORRY_THOUGHT_CAPTURE: ("automatic_thought", "worry_prediction"),
    StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE: ("emotions", "body_symptoms_or_safety_behaviors"),
}
SENTENCE_SPLIT_RE = re.compile(r"[.!?。！？\n]+")
THOUGHT_MARKERS = (
    "생각",
    "같아",
    "거야",
    "무능",
    "인정",
    "비웃",
    "실패",
    "큰일",
    "소용없",
    "망할",
    "문제야",
)
BEHAVIOR_MARKERS = (
    "피하",
    "숨고 싶",
    "확인",
    "다시 확인",
    "준비만",
    "집에 가",
    "밖에 나가",
    "걷",
    "조절",
    "미루",
    "도망",
    "회피",
    "물어보",
    "검색",
    "안 하고 싶",
)


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
    "무서": "fear",
    "겁": "fear",
    "두려": "fear",
    "panic": "panic",
    "panic attack": "panic",
    "패닉": "panic",
    "공황": "panic",
    "shame": "shame",
    "ashamed": "shame",
    "embarrassed": "shame",
    "부끄": "shame",
    "창피": "shame",
    "수치": "shame",
    "sadness": "sadness",
    "sad": "sadness",
    "depressed": "sadness",
    "우울": "sadness",
    "슬프": "sadness",
    "despair": "despair",
    "hopeless": "despair",
    "절망": "despair",
}


def _normalize_emotion_label(label: str) -> str:
    normalized = label.strip().lower()
    if normalized in ALLOWED_EMOTION_LABELS:
        return normalized
    for alias, canonical in EMOTION_LABEL_ALIASES.items():
        if alias in normalized:
            return canonical
    return normalized


def _contains_any_marker(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def _dedupe_fields(fields: list[str]) -> list[str]:
    deduped: list[str] = []
    for field in fields:
        if field not in deduped:
            deduped.append(field)
    return deduped


def _split_sentences(text: str) -> list[str]:
    return [segment.strip() for segment in SENTENCE_SPLIT_RE.split(text) if segment.strip()]


def _append_text_candidate(candidates: list[dict[str, Any]], text: str, confidence: float = 0.55) -> None:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return
    if any(item.get("text") == normalized for item in candidates):
        return
    candidates.append({"text": normalized, "confidence": confidence, "evidence_span": normalized})


def _fallback_thought_candidate(free_text: str) -> str | None:
    for sentence in _split_sentences(free_text):
        lowered = sentence.lower()
        if any(marker in lowered for marker in AMBIGUITY_MARKERS):
            continue
        if "무슨 생각" in lowered or "어떤 생각" in lowered:
            continue
        if any(marker in lowered for marker in THOUGHT_MARKERS):
            return sentence
    return None


def _fallback_prediction_candidate(free_text: str) -> str | None:
    for sentence in _split_sentences(free_text):
        lowered = sentence.lower()
        if any(marker in lowered for marker in FUTURE_MARKERS):
            return sentence
    return None


def _fallback_behavior_candidate(free_text: str) -> str | None:
    for sentence in _split_sentences(free_text):
        lowered = sentence.lower()
        if any(marker in lowered for marker in BEHAVIOR_MARKERS):
            return sentence
    return None


def _enrich_candidates_from_free_text(parsed: dict[str, Any], *, free_text: str) -> dict[str, Any]:
    normalized = dict(parsed)
    situation_candidates = list(normalized.get("situation_candidates", []))
    thought_candidates = list(normalized.get("automatic_thought_candidates", []))
    prediction_candidates = list(normalized.get("worry_prediction_candidates", []))
    behavior_candidates = list(normalized.get("behavior_candidates", []))

    if not situation_candidates:
        first_sentence = next(iter(_split_sentences(free_text)), "")
        _append_text_candidate(situation_candidates, first_sentence, confidence=0.45)

    if not thought_candidates:
        thought_text = _fallback_thought_candidate(free_text)
        if thought_text:
            _append_text_candidate(thought_candidates, thought_text)

    if not prediction_candidates:
        prediction_text = _fallback_prediction_candidate(free_text)
        if prediction_text:
            _append_text_candidate(prediction_candidates, prediction_text)

    if not behavior_candidates:
        behavior_text = _fallback_behavior_candidate(free_text)
        if behavior_text:
            _append_text_candidate(behavior_candidates, behavior_text)

    normalized["situation_candidates"] = situation_candidates
    normalized["automatic_thought_candidates"] = thought_candidates
    normalized["worry_prediction_candidates"] = prediction_candidates
    normalized["behavior_candidates"] = behavior_candidates
    return normalized


def _normalize_structured_output(parsed: dict[str, Any], *, state: StateEnum | None = None, free_text: str = "") -> dict[str, Any]:
    normalized = dict(parsed)
    automatic_candidates = _normalize_text_candidates(
        parsed.get("automatic_thought_candidates", []),
        kind="automatic_thought",
    )
    worry_candidates = _normalize_text_candidates(
        parsed.get("worry_prediction_candidates", []),
        kind="worry_prediction",
    )
    automatic_candidates, worry_candidates = _rebalance_thought_and_prediction_candidates(automatic_candidates, worry_candidates)
    normalized["automatic_thought_candidates"] = automatic_candidates
    normalized["worry_prediction_candidates"] = worry_candidates
    normalized_emotions = []
    for item in parsed.get("emotion_candidates", []):
        candidate = dict(item)
        candidate["label"] = _normalize_emotion_label(str(candidate.get("label", "")))
        normalized_emotions.append(candidate)
    normalized["emotion_candidates"] = normalized_emotions
    normalized["distortion_candidates"] = _normalize_distortion_candidates(parsed.get("distortion_candidates", []))
    normalized = _enrich_candidates_from_free_text(normalized, free_text=free_text)
    if state is not None:
        normalized = _apply_state_clarification_rules(normalized, state=state, free_text=free_text)
    return normalized


def _normalize_text_candidates(candidates: list[dict[str, Any]], *, kind: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in candidates:
        candidate = dict(item)
        text = " ".join(str(candidate.get("text", "")).strip().split())
        lowered = text.lower()
        if not text:
            continue
        if kind == "automatic_thought" and any(marker in lowered for marker in FUTURE_MARKERS) and not any(
            marker in lowered for marker in SELF_OR_OTHER_JUDGMENT_MARKERS
        ):
            continue
        if kind == "worry_prediction" and any(marker in lowered for marker in SELF_OR_OTHER_JUDGMENT_MARKERS) and not any(
            marker in lowered for marker in FUTURE_MARKERS
        ):
            continue
        candidate["text"] = text
        normalized.append(candidate)
    return normalized


def _rebalance_thought_and_prediction_candidates(
    automatic_candidates: list[dict[str, Any]],
    worry_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    def contains_marker(text: str, markers: tuple[str, ...]) -> bool:
        lowered = text.lower()
        return any(marker in lowered for marker in markers)

    rebalanced_automatic = list(automatic_candidates)
    rebalanced_worry = list(worry_candidates)

    for candidate in automatic_candidates:
        text = candidate["text"]
        if contains_marker(text, FUTURE_MARKERS) and not any(item["text"] == text for item in rebalanced_worry):
            rebalanced_worry.append(dict(candidate))

    for candidate in worry_candidates:
        text = candidate["text"]
        if contains_marker(text, SELF_OR_OTHER_JUDGMENT_MARKERS) and not any(item["text"] == text for item in rebalanced_automatic):
            rebalanced_automatic.append(dict(candidate))

    return rebalanced_automatic, rebalanced_worry


def _apply_state_clarification_rules(parsed: dict[str, Any], *, state: StateEnum, free_text: str) -> dict[str, Any]:
    normalized = dict(parsed)
    normalized["needs_clarification"] = False
    lowered = free_text.strip().lower()
    has_ambiguity = _contains_any_marker(lowered, AMBIGUITY_MARKERS)
    has_direct_emotion_words = _contains_any_marker(lowered, DIRECT_EMOTION_MARKERS)
    has_body_markers = _contains_any_marker(lowered, BODY_MARKERS)

    missing_fields: list[str] = []
    situation_candidates = normalized.get("situation_candidates", [])
    thought_candidates = normalized.get("automatic_thought_candidates", [])
    worry_candidates = normalized.get("worry_prediction_candidates", [])
    emotion_candidates = normalized.get("emotion_candidates", [])
    behavior_candidates = normalized.get("behavior_candidates", [])

    if state == StateEnum.SITUATION_CAPTURE:
        if not situation_candidates:
            missing_fields.extend(["situation", "trigger_text"])
        else:
            missing_fields.append("trigger_text")
            if has_ambiguity:
                missing_fields.append("situation")

    elif state == StateEnum.WORRY_THOUGHT_CAPTURE:
        if not thought_candidates and not worry_candidates:
            missing_fields.extend(["automatic_thought", "worry_prediction"])
        elif has_ambiguity:
            if not thought_candidates:
                missing_fields.append("automatic_thought")
            if not worry_candidates:
                missing_fields.append("worry_prediction")

    elif state == StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE:
        if not emotion_candidates:
            missing_fields.append("emotions")
        if has_ambiguity:
            if not emotion_candidates:
                missing_fields.append("emotions")
            missing_fields.append("body_symptoms_or_safety_behaviors")
        elif has_body_markers and not has_direct_emotion_words and not emotion_candidates:
            missing_fields.extend(["emotions", "body_symptoms_or_safety_behaviors"])

    normalized["missing_fields"] = _dedupe_fields(missing_fields)
    required_fields = STATE_REQUIRED_MISSING_FIELDS.get(state, tuple())
    if state == StateEnum.SITUATION_CAPTURE and situation_candidates and "trigger_text" in normalized["missing_fields"] and not has_ambiguity:
        return normalized
    if any(field in normalized["missing_fields"] for field in required_fields):
        normalized["needs_clarification"] = True
    return normalized


DISTORTION_LABEL_ALIASES = {
    "mind reading": "mind_reading",
    "mind_reading": "mind_reading",
    "fortune telling": "fortune_telling",
    "fortune_telling": "fortune_telling",
    "catastrophizing": "catastrophizing",
    "should statements": "should_statements",
    "should_statements": "should_statements",
    "self blame": "self_blame",
    "self_blame": "self_blame",
    "overgeneralization": "overgeneralization",
    "intolerance of uncertainty": "intolerance_of_uncertainty",
    "intolerance_of_uncertainty": "intolerance_of_uncertainty",
    "probability overestimation": "probability_overestimation",
    "probability_overestimation": "probability_overestimation",
    "uncertainty focus": "uncertainty_focus",
    "uncertainty_focus": "uncertainty_focus",
}


def _normalize_distortion_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in candidates:
        candidate = dict(item)
        label = str(candidate.get("label", "")).strip().lower()
        canonical = DISTORTION_LABEL_ALIASES.get(label, label.replace(" ", "_"))
        if canonical not in ALLOWED_DISTORTION_LABELS:
            continue
        candidate["label"] = canonical
        normalized.append(candidate)
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
            parsed = _normalize_structured_output(parsed, state=state, free_text=free_text)
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

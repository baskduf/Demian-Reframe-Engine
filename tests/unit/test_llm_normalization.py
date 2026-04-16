from __future__ import annotations

from app.llm.parser import _normalize_structured_output
from app.llm.risk_assist import _normalize_risk_payload
from app.schemas.models import StateEnum


def test_parser_normalizes_emotion_aliases() -> None:
    normalized = _normalize_structured_output(
        {
            "situation_candidates": [],
            "automatic_thought_candidates": [],
            "worry_prediction_candidates": [],
            "emotion_candidates": [
                {"label": "ashamed", "intensity_hint": 70, "confidence": 0.9, "evidence_span": "ashamed"}
            ],
            "behavior_candidates": [],
            "distortion_candidates": [],
            "risk_flags": [],
            "needs_clarification": False,
            "missing_fields": [],
            "confidence": {
                "overall": 0.9,
                "situation": 0.0,
                "automatic_thought": 0.0,
                "emotion": 0.9,
                "behavior": 0.0,
                "distortion": 0.0,
                "risk": 0.0,
            },
        }
    )
    assert normalized["emotion_candidates"][0]["label"] == "shame"


def test_parser_separates_thought_and_prediction_candidates() -> None:
    normalized = _normalize_structured_output(
        {
            "situation_candidates": [],
            "automatic_thought_candidates": [
                {"text": "분명 잘못될 거고 결국 최악이 될 거야", "confidence": 0.9, "evidence_span": "full"}
            ],
            "worry_prediction_candidates": [
                {"text": "나는 항상 문제를 만드는 사람이야", "confidence": 0.9, "evidence_span": "full"},
                {"text": "분명 잘못될 거고 결국 최악이 될 거야", "confidence": 0.9, "evidence_span": "full"},
            ],
            "emotion_candidates": [],
            "behavior_candidates": [],
            "distortion_candidates": [{"label": "mind reading", "confidence": 0.8, "rationale_code": "x"}],
            "risk_flags": [],
            "needs_clarification": False,
            "missing_fields": [],
            "confidence": {
                "overall": 0.9,
                "situation": 0.0,
                "automatic_thought": 0.9,
                "emotion": 0.0,
                "behavior": 0.0,
                "distortion": 0.8,
                "risk": 0.0,
            },
        }
    )
    assert normalized["automatic_thought_candidates"] == []
    assert normalized["worry_prediction_candidates"][0]["text"] == "분명 잘못될 거고 결국 최악이 될 거야"
    assert normalized["distortion_candidates"][0]["label"] == "mind_reading"


def test_risk_assist_normalizes_flag_aliases() -> None:
    normalized = _normalize_risk_payload(
        {"risk_flags": [{"flag": "death_wish", "confidence": 0.8, "evidence_span": "death wish"}]}
    )
    assert normalized["risk_flags"][0]["flag"] == "passive_death_wish"


def test_parser_upgrades_clarification_for_ambiguous_worry_text() -> None:
    normalized = _normalize_structured_output(
        {
            "situation_candidates": [],
            "automatic_thought_candidates": [],
            "worry_prediction_candidates": [],
            "emotion_candidates": [{"label": "anxiety", "intensity_hint": 50, "confidence": 0.8, "evidence_span": "불안"}],
            "behavior_candidates": [],
            "distortion_candidates": [],
            "risk_flags": [],
            "needs_clarification": False,
            "missing_fields": [],
            "confidence": {
                "overall": 0.8,
                "situation": 0.0,
                "automatic_thought": 0.0,
                "emotion": 0.8,
                "behavior": 0.0,
                "distortion": 0.0,
                "risk": 0.0,
            },
        },
        state=StateEnum.WORRY_THOUGHT_CAPTURE,
        free_text="정확히 무슨 생각 때문에 불안한지 모르겠어. 그냥 답답해.",
    )
    assert normalized["needs_clarification"] is True
    assert normalized["missing_fields"] == ["automatic_thought", "worry_prediction"]


def test_parser_marks_missing_trigger_for_situation_capture() -> None:
    normalized = _normalize_structured_output(
        {
            "situation_candidates": [{"text": "내일 팀 회의에서 발표해야 하는 상황", "confidence": 0.9, "evidence_span": "발표"}],
            "automatic_thought_candidates": [],
            "worry_prediction_candidates": [],
            "emotion_candidates": [{"label": "anxiety", "intensity_hint": 60, "confidence": 0.9, "evidence_span": "긴장"}],
            "behavior_candidates": [],
            "distortion_candidates": [],
            "risk_flags": [],
            "needs_clarification": False,
            "missing_fields": [],
            "confidence": {
                "overall": 0.9,
                "situation": 0.9,
                "automatic_thought": 0.0,
                "emotion": 0.9,
                "behavior": 0.0,
                "distortion": 0.0,
                "risk": 0.0,
            },
        },
        state=StateEnum.SITUATION_CAPTURE,
        free_text="내일 팀 회의에서 발표해야 해서 하루 종일 긴장돼.",
    )
    assert normalized["needs_clarification"] is False
    assert "trigger_text" in normalized["missing_fields"]


def test_parser_marks_missing_emotion_for_ambiguous_body_text() -> None:
    normalized = _normalize_structured_output(
        {
            "situation_candidates": [],
            "automatic_thought_candidates": [],
            "worry_prediction_candidates": [],
            "emotion_candidates": [],
            "behavior_candidates": [{"text": "반복 확인한다", "confidence": 0.8, "evidence_span": "확인"}],
            "distortion_candidates": [],
            "risk_flags": [],
            "needs_clarification": False,
            "missing_fields": [],
            "confidence": {
                "overall": 0.7,
                "situation": 0.0,
                "automatic_thought": 0.0,
                "emotion": 0.0,
                "behavior": 0.8,
                "distortion": 0.0,
                "risk": 0.0,
            },
        },
        state=StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE,
        free_text="불안해서 자꾸 일정을 다시 확인하는데 어떤 감정인지 설명은 잘 안 돼.",
    )
    assert normalized["needs_clarification"] is True
    assert "body_symptoms_or_safety_behaviors" in normalized["missing_fields"]

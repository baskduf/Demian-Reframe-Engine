from __future__ import annotations

from app.llm.parser import _normalize_structured_output
from app.llm.risk_assist import _normalize_risk_payload


def test_parser_normalizes_emotion_aliases() -> None:
    normalized = _normalize_structured_output(
        {
            "situation_candidates": [],
            "automatic_thought_candidates": [],
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


def test_risk_assist_normalizes_flag_aliases() -> None:
    normalized = _normalize_risk_payload(
        {"risk_flags": [{"flag": "death_wish", "confidence": 0.8, "evidence_span": "death wish"}]}
    )
    assert normalized["risk_flags"][0]["flag"] == "passive_death_wish"

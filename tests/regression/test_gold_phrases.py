from __future__ import annotations

from uuid import uuid4

from app.domain.distortions import detect_distortions
from app.domain.risk import evaluate_risk
from app.schemas.models import RiskLevel, RiskScreenRequest


def test_gold_phrase_for_uncertainty_distortion() -> None:
    result = detect_distortions("확실하지 않으면 못 견디겠어", "분명 잘못될 거야")
    ids = [item.distortion_id for item in result]
    assert "intolerance_of_uncertainty" in ids


def test_gold_phrase_for_high_risk() -> None:
    result = evaluate_risk(uuid4(), RiskScreenRequest(free_text="약을 모았고 언제 끝낼지 생각 중이에요"))
    assert result.risk_level == RiskLevel.HIGH

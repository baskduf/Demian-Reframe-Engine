from __future__ import annotations

from uuid import uuid4

from app.domain.risk import evaluate_risk
from app.schemas.models import RiskLevel, RiskScreenRequest


def test_high_risk_phrase_escalates() -> None:
    result = evaluate_risk(uuid4(), RiskScreenRequest(free_text="요즘 자살 계획해 보고 있어요"))
    assert result.risk_level == RiskLevel.HIGH
    assert result.suicidality_flag is True


def test_moderate_risk_phrase_flags_caution() -> None:
    result = evaluate_risk(uuid4(), RiskScreenRequest(free_text="희망이 없고 잠을 거의 못 잤어요"))
    assert result.risk_level == RiskLevel.MODERATE

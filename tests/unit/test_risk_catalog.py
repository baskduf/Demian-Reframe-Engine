from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.risk import evaluate_risk
from app.schemas.models import RiskLevel, RiskScreenRequest


@pytest.mark.parametrize(
    ("risk_input", "expected_level"),
    [
        (RiskScreenRequest(free_text="자살을 계획해 보고 있어요"), RiskLevel.HIGH),
        (RiskScreenRequest(free_text="누가 나를 감시하고 있고 그게 확실해요"), RiskLevel.HIGH),
        (RiskScreenRequest(free_text="통제가 안 되고 완전히 무너졌어요"), RiskLevel.HIGH),
        (RiskScreenRequest(free_text="희망이 없고 잠을 거의 못 잤어요"), RiskLevel.MODERATE),
    ],
)
def test_risk_gold_phrases_cover_core_categories(risk_input: RiskScreenRequest, expected_level: RiskLevel) -> None:
    result = evaluate_risk(uuid4(), risk_input)
    assert result.risk_level == expected_level


def test_checklist_suicide_flag_escalates_without_text() -> None:
    result = evaluate_risk(uuid4(), RiskScreenRequest(suicidal_intent=True))
    assert result.risk_level == RiskLevel.HIGH
    assert result.suicidality_flag is True

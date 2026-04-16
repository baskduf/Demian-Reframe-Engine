from __future__ import annotations

import pytest

from app.domain.distortions import detect_distortions


@pytest.mark.parametrize(
    ("automatic_thought", "worry_prediction", "expected_id"),
    [
        ("이 발표가 망하면 끝장이야", "최악이 될 거야", "catastrophizing"),
        ("분명 실패할 거야", "잘못될 거야", "fortune_telling"),
        ("확실하지 않으면 못 견디겠어", "모르면 너무 위험해", "intolerance_of_uncertainty"),
        ("나쁜 일이 생길 가능성이 크다", "분명 위험하다", "probability_overestimation"),
        ("나는 반드시 완벽해야 한다", "이러면 안 된다", "should_statements"),
        ("다들 내가 이상하다고 생각해", "저 사람은 날 무능하다고 볼 거야", "mind_reading"),
        ("항상 이런 식이야", "결국 늘 망해", "overgeneralization"),
        ("전부 내 탓이야", "내가 문제라서 이렇게 됐어", "self_blame"),
    ],
)
def test_each_distortion_has_a_gold_phrase(automatic_thought: str, worry_prediction: str, expected_id: str) -> None:
    result = detect_distortions(automatic_thought, worry_prediction)
    ids = [item.distortion_id for item in result]
    assert expected_id in ids


def test_distortion_falls_back_to_uncertainty_focus_when_no_rule_matches() -> None:
    result = detect_distortions("회의가 있다", "어떻게 될지 모르겠다")
    assert result[0].distortion_id == "uncertainty_focus"
    assert result[0].is_primary is True


def test_distortion_is_thought_aware_and_prioritizes_thought_matches_first() -> None:
    result = detect_distortions("나는 항상 문제를 만드는 사람이야", "분명 잘못될 거고 결국 최악이 될 거야")
    ids = [item.distortion_id for item in result]
    assert ids[0] in {"overgeneralization", "self_blame"}
    assert "fortune_telling" in ids or "catastrophizing" in ids

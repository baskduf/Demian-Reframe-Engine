from __future__ import annotations

from app.domain.distortions import detect_distortions


def test_distortion_detection_returns_expected_categories() -> None:
    result = detect_distortions(
        "이 발표 하나 망하면 나는 항상 실패하는 사람이야",
        "분명 잘못될 거고 모두가 내가 이상하다고 생각할 거야",
    )
    ids = [item.distortion_id for item in result]
    assert "catastrophizing" in ids
    assert "fortune_telling" in ids

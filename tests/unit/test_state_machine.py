from __future__ import annotations

from app.domain.state_machine import has_required_fields
from app.schemas.models import StateEnum


def test_missing_fields_block_transition() -> None:
    assert has_required_fields(StateEnum.SITUATION_CAPTURE, {"situation_text": "회의"}) is False


def test_emotion_state_requires_behavior_or_body_signal() -> None:
    payload = {"emotions": [{"label": "anxiety", "intensity": 80}]}
    assert has_required_fields(StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE, payload) is False

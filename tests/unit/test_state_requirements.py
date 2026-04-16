from __future__ import annotations

import pytest

from app.domain.state_machine import has_required_fields
from app.schemas.models import StateEnum


@pytest.mark.parametrize(
    ("state", "payload"),
    [
        (StateEnum.SITUATION_CAPTURE, {"situation_text": "회의 전"}),
        (StateEnum.WORRY_THOUGHT_CAPTURE, {"automatic_thought": "망할 거야"}),
        (StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE, {"emotions": [{"label": "anxiety", "intensity": 70}]}),
        (StateEnum.EVIDENCE_FOR, {"evidence_for": []}),
        (StateEnum.EVIDENCE_AGAINST, {"evidence_against": []}),
        (StateEnum.ALTERNATIVE_THOUGHT, {"balanced_view": "실수해도 괜찮다"}),
        (StateEnum.RE_RATE_ANXIETY, {"re_rated_anxiety": 50}),
        (StateEnum.BEHAVIOR_EXPERIMENT, {"action": "연습만 해본다"}),
        (StateEnum.SUMMARY_PLAN, {}),
    ],
)
def test_required_fields_fail_when_payload_is_incomplete(state: StateEnum, payload: dict) -> None:
    assert has_required_fields(state, payload) is False

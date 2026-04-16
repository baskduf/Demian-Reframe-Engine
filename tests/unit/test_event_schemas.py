from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.events import (
    EVENT_TYPE_BY_STATE,
    EmotionBehaviorPayload,
    EventTypeEnum,
    ReRatePayload,
    expected_event_type_for_state,
)
from app.schemas.models import StateEnum


def test_state_event_mapping_is_defined_for_all_interactive_states() -> None:
    assert expected_event_type_for_state(StateEnum.ELIGIBILITY_CHECK) == EventTypeEnum.ELIGIBILITY
    assert expected_event_type_for_state(StateEnum.SITUATION_CAPTURE) == EventTypeEnum.SITUATION
    assert expected_event_type_for_state(StateEnum.SUMMARY_PLAN) == EventTypeEnum.SUMMARY
    assert StateEnum.CRISIS not in EVENT_TYPE_BY_STATE


def test_rerate_payload_rejects_wrong_type() -> None:
    with pytest.raises(ValidationError):
        ReRatePayload.model_validate({"re_rated_anxiety": "high", "experiment_required": False})


def test_emotion_payload_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        EmotionBehaviorPayload.model_validate({"emotions": [], "unexpected": True})

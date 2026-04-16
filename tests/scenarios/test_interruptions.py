from __future__ import annotations

import pytest

from tests.helpers import advance_to_state, create_session


@pytest.mark.parametrize(
    ("target_state", "free_text"),
    [
        ("situation_capture", "자살 계획해 보고 있어요"),
        ("worry_thought_capture", "오늘 자살 계획해 보고 있어요"),
        ("emotion_body_behavior_capture", "자살 생각이 강해졌어요"),
        ("distortion_hypothesis", "오늘은 자살 계획해 보고 있어요"),
        ("evidence_for", "자살 준비를 생각하고 있어요"),
        ("evidence_against", "자살을 계획 중이에요"),
        ("alternative_thought", "자살하고 싶어요"),
        ("re_rate_anxiety", "자살 계획이 있어요"),
    ],
)
def test_high_risk_interrupts_from_major_states(client, target_state: str, free_text: str) -> None:
    session_id = create_session(client)
    advance_to_state(client, session_id, target_state)
    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "interrupt", "payload": {"free_text": free_text}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "crisis"
    assert body["session"]["closed_reason"] == "safety_escalation"


def test_psychotic_expression_interrupts_session(client) -> None:
    session_id = create_session(client)
    advance_to_state(client, session_id, "situation_capture")
    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "interrupt", "payload": {"free_text": "누가 날 감시하고 있고 그게 확실해요"}},
    )
    assert response.status_code == 200
    assert response.json()["current_state"] == "crisis"


def test_acute_deterioration_interrupts_session(client) -> None:
    session_id = create_session(client)
    advance_to_state(client, session_id, "situation_capture")
    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "interrupt", "payload": {"free_text": "통제가 안 되고 완전히 무너졌어요"}},
    )
    assert response.status_code == 200
    assert response.json()["current_state"] == "crisis"

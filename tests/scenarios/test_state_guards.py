from __future__ import annotations

import pytest

from tests.helpers import advance_to_state, create_session


@pytest.mark.parametrize(
    ("target_state", "payload"),
    [
        ("situation_capture", {"event_type": "situation", "payload": {"situation_text": "회의 전"}}),
        ("worry_thought_capture", {"event_type": "worry", "payload": {"automatic_thought": "망할 거야"}}),
        ("emotion_body_behavior_capture", {"event_type": "emotion", "payload": {"emotions": [{"label": "anxiety", "intensity": 80}]}}),
        ("evidence_for", {"event_type": "evidence_for", "payload": {"evidence_for": []}}),
        ("evidence_against", {"event_type": "evidence_against", "payload": {"evidence_against": []}}),
        ("alternative_thought", {"event_type": "alternative", "payload": {"balanced_view": "괜찮을 수 있다"}}),
        ("re_rate_anxiety", {"event_type": "rerate", "payload": {"re_rated_anxiety": 50}}),
        ("behavior_experiment", {"event_type": "experiment", "payload": {"action": "연습"}}),
        ("summary_plan", {"event_type": "summary", "payload": {}}),
    ],
)
def test_incomplete_payload_keeps_session_in_same_state(client, target_state: str, payload: dict) -> None:
    session_id = create_session(client)
    advance_to_state(client, session_id, target_state)
    response = client.post(f"/v1/sessions/{session_id}/events", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == target_state
    assert "missing_fields" in body["state_data"]


def test_rerate_false_skips_experiment_and_moves_to_summary(client) -> None:
    session_id = create_session(client)
    advance_to_state(client, session_id, "re_rate_anxiety")
    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "rerate", "payload": {"re_rated_anxiety": 40, "experiment_required": False}},
    )
    assert response.status_code == 200
    assert response.json()["current_state"] == "summary_plan"


def test_rerate_true_moves_to_experiment(client) -> None:
    session_id = create_session(client)
    advance_to_state(client, session_id, "re_rate_anxiety")
    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "rerate", "payload": {"re_rated_anxiety": 40, "experiment_required": True}},
    )
    assert response.status_code == 200
    assert response.json()["current_state"] == "behavior_experiment"


@pytest.mark.parametrize("target_state", ["crisis", "out_of_scope", "close_session"])
def test_terminal_states_ignore_additional_events(client, target_state: str) -> None:
    session_id = create_session(client)
    if target_state == "crisis":
        client.post(f"/v1/sessions/{session_id}/risk-screen", json={"suicidal_intent": True})
    elif target_state == "out_of_scope":
        client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
        client.post(
            f"/v1/sessions/{session_id}/events",
            json={"event_type": "eligibility", "payload": {"is_adult": False, "target_condition": "gad"}},
        )
    else:
        advance_to_state(client, session_id, "close_session")

    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "noop", "payload": {"free_text": "extra input"}},
    )
    assert response.status_code == 200
    assert response.json()["current_state"] == target_state

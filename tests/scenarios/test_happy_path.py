from __future__ import annotations


def test_happy_path_session(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]

    steps = [
        (f"/v1/sessions/{session_id}/risk-screen", {}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}}),
        (
            f"/v1/sessions/{session_id}/events",
            {"event_type": "situation", "payload": {"situation_text": "before a meeting with my manager", "trigger_text": "fear of making a mistake"}},
        ),
        (
            f"/v1/sessions/{session_id}/events",
            {"event_type": "worry", "payload": {"automatic_thought": "If I get something wrong, everything is over", "worry_prediction": "I will definitely mess this up"}},
        ),
        (
            f"/v1/sessions/{session_id}/events",
            {
                "event_type": "emotion",
                "payload": {
                    "emotions": [{"label": "anxiety", "intensity": 85}],
                    "body_symptoms": ["heart racing"],
                    "safety_behaviors": ["delaying the presentation"],
                },
            },
        ),
        (f"/v1/sessions/{session_id}/events", {"event_type": "distortion", "payload": {"selected_distortion_ids": ["uncertainty_focus"]}}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "evidence_for", "payload": {"evidence_for": ["I stumbled over my words once before"]}}),
        (
            f"/v1/sessions/{session_id}/events",
            {"event_type": "evidence_against", "payload": {"evidence_against": ["I prepared the main points well"]}},
        ),
        (
            f"/v1/sessions/{session_id}/events",
            {
                "event_type": "alternative",
                "payload": {
                    "balanced_view": "One mistake would not mean the whole conversation failed",
                    "coping_statement": "I will start with the three key points slowly",
                },
            },
        ),
        (f"/v1/sessions/{session_id}/events", {"event_type": "rerate", "payload": {"re_rated_anxiety": 55, "experiment_required": False}}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "summary", "payload": {"summary_ack": True}}),
    ]

    state = None
    for path, payload in steps:
        response = client.post(path, json=payload)
        assert response.status_code == 200
        state = response.json()["current_state"]

    assert state == "close_session"

    audit = client.get(f"/v1/audit/sessions/{session_id}")
    assert audit.status_code == 200
    assert len(audit.json()["transitions"]) >= 1

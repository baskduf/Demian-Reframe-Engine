from __future__ import annotations


def create_session(client, user_id: str = "user-1") -> str:
    response = client.post("/v1/sessions", json={"user_id": user_id})
    assert response.status_code == 200
    return response.json()["session"]["session_id"]


def advance_to_state(client, session_id: str, target_state: str) -> dict:
    if target_state == "risk_screen":
        return client.get(f"/v1/sessions/{session_id}").json()

    response = client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    assert response.status_code == 200
    if target_state == "eligibility_check":
        return response.json()

    steps = [
        ("situation_capture", {"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}}),
        ("worry_thought_capture", {"event_type": "situation", "payload": {"situation_text": "before a meeting", "trigger_text": "fear of messing up"}}),
        ("emotion_body_behavior_capture", {"event_type": "worry", "payload": {"automatic_thought": "I will probably fail", "worry_prediction": "Everything will go badly"}}),
        (
            "distortion_hypothesis",
            {
                "event_type": "emotion",
                "payload": {
                    "emotions": [{"label": "anxiety", "intensity": 80}],
                    "body_symptoms": ["heart racing"],
                    "safety_behaviors": ["avoiding the conversation"],
                },
            },
        ),
        ("evidence_for", {"event_type": "distortion", "payload": {"selected_distortion_ids": ["uncertainty_focus"]}}),
        ("evidence_against", {"event_type": "evidence_for", "payload": {"evidence_for": ["I stumbled once before"]}}),
        ("alternative_thought", {"event_type": "evidence_against", "payload": {"evidence_against": ["I have prepared well enough"]}}),
        (
            "re_rate_anxiety",
            {
                "event_type": "alternative",
                "payload": {
                    "balanced_view": "A mistake is possible, but it would not define the whole outcome",
                    "coping_statement": "I will say the first three points slowly",
                },
            },
        ),
        ("behavior_experiment", {"event_type": "rerate", "payload": {"re_rated_anxiety": 60, "experiment_required": True}}),
        (
            "summary_plan",
            {
                "event_type": "experiment",
                "payload": {"action": "practice a short talk", "timebox": "10m", "hypothesis": "my anxiety will drop a little"},
            },
        ),
        ("close_session", {"event_type": "summary", "payload": {"summary_ack": True}}),
    ]

    for state_name, payload in steps:
        response = client.post(f"/v1/sessions/{session_id}/events", json=payload)
        assert response.status_code == 200
        if state_name == target_state:
            return response.json()

    raise AssertionError(f"Could not advance to {target_state}")

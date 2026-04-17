from __future__ import annotations


def _prepare_until_emotion_stage(client, session_id: str) -> None:
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}},
    )
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "situation", "payload": {"situation_text": "job interview tomorrow", "trigger_text": "fear of failure"}},
    )
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "worry", "payload": {"automatic_thought": "I will fail badly", "worry_prediction": "No one will hire me"}},
    )


def _complete_low_risk_session(client, session_id: str) -> None:
    steps = [
        (f"/v1/sessions/{session_id}/risk-screen", {}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}}),
        (
            f"/v1/sessions/{session_id}/events",
            {"event_type": "situation", "payload": {"situation_text": "presentation tomorrow", "trigger_text": "fear of mistakes"}},
        ),
        (
            f"/v1/sessions/{session_id}/events",
            {"event_type": "worry", "payload": {"automatic_thought": "I will fail badly", "worry_prediction": "Everyone will judge me"}},
        ),
        (
            f"/v1/sessions/{session_id}/events",
            {
                "event_type": "emotion",
                "payload": {
                    "emotions": [{"label": "anxiety", "intensity": 85}],
                    "body_symptoms": ["heart racing"],
                    "safety_behaviors": ["checking notes"],
                },
            },
        ),
        (f"/v1/sessions/{session_id}/events", {"event_type": "distortion", "payload": {"selected_distortion_ids": ["uncertainty_focus"]}}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "evidence_for", "payload": {"evidence_for": ["I stumbled once before"]}}),
        (
            f"/v1/sessions/{session_id}/events",
            {"event_type": "evidence_against", "payload": {"evidence_against": ["I prepared well this time"]}},
        ),
        (
            f"/v1/sessions/{session_id}/events",
            {
                "event_type": "alternative",
                "payload": {
                    "balanced_view": "I may feel nervous, but that does not mean I will fail",
                    "coping_statement": "I will focus on the key points",
                },
            },
        ),
        (f"/v1/sessions/{session_id}/events", {"event_type": "rerate", "payload": {"re_rated_anxiety": 45, "experiment_required": False}}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "summary", "payload": {"summary_ack": True}}),
    ]

    for path, payload in steps:
        response = client.post(path, json=payload)
        assert response.status_code == 200


def test_session_creation_exposes_versions(client) -> None:
    response = client.post("/v1/sessions", json={"user_id": "user-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "risk_screen"
    assert body["interaction_status"] == "clarify"
    assert body["protocol_version"] == "gad-cbt-v1"
    assert "transition_trace_id" in body
    assert body["guidance"]["title"]


def test_initial_risk_screen_returns_eligibility_prompt(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]

    response = client.post(f"/v1/sessions/{session_id}/risk-screen", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "eligibility_check"
    assert body["template_response"]["template_id"] == "prompt.eligibility"
    assert body["interaction_status"] == "advance"


def test_reassess_risk_keeps_current_state_when_not_high_risk(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}},
    )
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "situation", "payload": {"situation_text": "presentation prep", "trigger_text": "worry about mistakes"}},
    )

    response = client.post(f"/v1/sessions/{session_id}/reassess-risk", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "worry_thought_capture"
    assert body["state_data"]["risk_level"] == "none"
    assert body["interaction_status"] == "clarify"


def test_reassess_risk_interrupts_flow_when_high_risk(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}},
    )

    response = client.post(
        f"/v1/sessions/{session_id}/reassess-risk",
        json={"suicidal_intent": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "crisis"
    assert body["state_data"]["risk_level"] == "high"
    assert body["interaction_status"] == "interrupt"


def test_missing_rerate_fields_keeps_state_and_reports_invalid_fields(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    _prepare_until_emotion_stage(client, session_id)
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={
            "event_type": "emotion",
            "payload": {
                "emotions": [{"label": "anxiety", "intensity": 80}],
                "body_symptoms": ["hands shaking"],
                "safety_behaviors": ["avoiding calls"],
            },
        },
    )
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "distortion", "payload": {"selected_distortion_ids": ["uncertainty_focus"]}})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "evidence_for", "payload": {"evidence_for": ["I froze once before"]}})
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "evidence_against", "payload": {"evidence_against": ["I also recovered and finished"]}},
    )
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={
            "event_type": "alternative",
            "payload": {
                "balanced_view": "One difficult moment does not guarantee failure",
                "coping_statement": "I can pause and continue",
            },
        },
    )
    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "rerate", "payload": {"experiment_required": False}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "re_rate_anxiety"
    assert body["interaction_status"] == "clarify"
    assert "re_rated_anxiety" in body["clarification"]["missing_fields"]


def test_wrong_event_type_for_state_returns_400(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}},
    )
    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "summary", "payload": {"summary_ack": True}},
    )
    assert response.status_code == 400


def test_alternative_thought_artifact_uses_korean_summary_format(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    _prepare_until_emotion_stage(client, session_id)
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={
            "event_type": "emotion",
            "payload": {
                "emotions": [{"label": "anxiety", "intensity": 80}],
                "body_symptoms": ["shaking"],
                "safety_behaviors": ["avoiding calls"],
            },
        },
    )
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "distortion", "payload": {"selected_distortion_ids": ["uncertainty_focus"]}})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "evidence_for", "payload": {"evidence_for": ["I was rejected once"]}})
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "evidence_against", "payload": {"evidence_against": ["I am still applying"]}},
    )

    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={
            "event_type": "alternative",
            "payload": {
                "balanced_view": "One rejection does not define everything",
                "coping_statement": "I will keep preparing and applying",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["state_data"]["alternative_thought"].startswith("\uade0\ud615 \uc7a1\ud78c \uad00\uc810:")


def test_ambiguous_evidence_against_returns_clarify_and_keeps_state(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    _prepare_until_emotion_stage(client, session_id)
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={
            "event_type": "emotion",
            "payload": {
                "emotions": [{"label": "anxiety", "intensity": 80}],
                "body_symptoms": ["shaking"],
                "safety_behaviors": ["avoiding calls"],
            },
        },
    )
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "distortion", "payload": {"selected_distortion_ids": ["uncertainty_focus"]}})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "evidence_for", "payload": {"evidence_for": ["I was rejected once"]}})

    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "evidence_against", "payload": {"evidence_against": ["idk"]}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "evidence_against"
    assert body["interaction_status"] == "clarify"
    assert body["clarification"]["reason_code"] == "weak_evidence_against"


def test_emotion_stage_includes_choices(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}},
    )
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "situation", "payload": {"situation_text": "job interview", "trigger_text": "fear of failure"}},
    )

    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "worry", "payload": {"automatic_thought": "I will fail badly", "worry_prediction": "No one will hire me"}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "emotion_body_behavior_capture"
    assert "emotion_labels" in body["choices"]
    assert body["guidance"]["examples"]


def test_final_summary_is_saved_in_artifacts(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    _complete_low_risk_session(client, session_id)

    artifacts = client.get(f"/v1/sessions/{session_id}/artifacts")
    assert artifacts.status_code == 200
    thought_record = artifacts.json()["thought_record"]
    assert thought_record["final_summary"]


def test_weak_situation_input_returns_clarify_and_collected_slots(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}},
    )

    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "situation", "payload": {"situation_text": "work", "trigger_text": ""}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "situation_capture"
    assert body["interaction_status"] == "clarify"
    assert body["clarification"]["reason_code"] == "missing_situation_fields"
    assert body["collected_slots"]["situation_text"] == "work"


def test_behavior_experiment_branch_returns_choices(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    _prepare_until_emotion_stage(client, session_id)
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={
            "event_type": "emotion",
            "payload": {
                "emotions": [{"label": "anxiety", "intensity": 80}],
                "body_symptoms": ["shaking"],
                "safety_behaviors": ["avoiding calls"],
            },
        },
    )
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "distortion", "payload": {"selected_distortion_ids": ["uncertainty_focus"]}})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "evidence_for", "payload": {"evidence_for": ["I stumbled once before"]}})
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "evidence_against", "payload": {"evidence_against": ["I recovered and still finished"]}},
    )
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={
            "event_type": "alternative",
            "payload": {
                "balanced_view": "Feeling nervous does not guarantee failure",
                "coping_statement": "I can focus on one point at a time",
            },
        },
    )

    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "rerate", "payload": {"re_rated_anxiety": 55, "experiment_required": True}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "behavior_experiment"
    assert body["interaction_status"] == "advance"
    assert "experiment_examples" in body["choices"]

from __future__ import annotations


def test_session_creation_exposes_versions(client) -> None:
    response = client.post("/v1/sessions", json={"user_id": "user-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "risk_screen"
    assert body["protocol_version"] == "gad-cbt-v1"
    assert "transition_trace_id" in body


def test_high_risk_mid_session_interrupts_flow(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}})
    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "situation", "payload": {"free_text": "오늘은 자살 계획해 보고 있어요"}},
    )
    assert response.status_code == 200
    assert response.json()["current_state"] == "crisis"


def test_initial_risk_screen_returns_eligibility_prompt(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]

    response = client.post(f"/v1/sessions/{session_id}/risk-screen", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "eligibility_check"
    assert body["template_response"]["template_id"] == "prompt.eligibility"


def test_reassess_risk_keeps_current_state_when_not_high_risk(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}})
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "situation", "payload": {"situation_text": "presentation prep", "trigger_text": "worry about mistakes"}},
    )

    response = client.post(f"/v1/sessions/{session_id}/reassess-risk", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "worry_thought_capture"
    assert body["state_data"]["risk_level"] == "none"


def test_reassess_risk_interrupts_flow_when_high_risk(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}})

    response = client.post(
        f"/v1/sessions/{session_id}/reassess-risk",
        json={"suicidal_intent": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "crisis"
    assert body["state_data"]["risk_level"] == "high"


def test_wrong_type_input_keeps_state_and_reports_invalid_fields(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "situation", "payload": {"situation_text": "회의 전", "trigger_text": "실수"}})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "worry", "payload": {"automatic_thought": "망할 거야", "worry_prediction": "분명 잘못될 거야"}})
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "emotion", "payload": {"emotions": [{"label": "anxiety", "intensity": 80}], "body_symptoms": ["두근거림"]}},
    )
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "distortion", "payload": {"selected_distortion_ids": ["fortune_telling"]}})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "evidence_for", "payload": {"evidence_for": ["지난번 실수"]}})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "evidence_against", "payload": {"evidence_against": ["준비했다"]}})
    client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "alternative", "payload": {"balanced_view": "실수해도 끝은 아니다", "coping_statement": "핵심부터 말하자"}},
    )
    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "rerate", "payload": {"re_rated_anxiety": "high", "experiment_required": False}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "re_rate_anxiety"
    assert "re_rated_anxiety" in body["state_data"]["invalid_fields"]


def test_wrong_event_type_for_state_returns_400(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    client.post(f"/v1/sessions/{session_id}/events", json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}})
    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "summary", "payload": {"summary_ack": True}},
    )
    assert response.status_code == 400

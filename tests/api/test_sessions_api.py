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

from __future__ import annotations

from tests.helpers import advance_to_state, create_session


def test_get_session_returns_contract_fields(client) -> None:
    session_id = create_session(client)
    response = client.get(f"/v1/sessions/{session_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "risk_screen"
    assert "allowed_actions" in body
    assert "engine_version" in body
    assert "protocol_version" in body
    assert "rule_set_version" in body
    assert "template_bundle_version" in body
    assert "risk_rules_version" in body
    assert "transition_trace_id" in body


def test_get_artifacts_returns_thought_record_and_versions(client) -> None:
    session_id = create_session(client)
    response = client.get(f"/v1/sessions/{session_id}/artifacts")
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session_id
    assert "thought_record" in body
    assert body["protocol_version"] == "gad-cbt-v1"


def test_get_protocol_returns_manifest(client) -> None:
    response = client.get("/v1/protocols/gad-cbt-v1")
    assert response.status_code == 200
    body = response.json()
    assert body["protocol_version"] == "gad-cbt-v1"
    assert "states" in body
    assert "risk_screen" in body["states"]


def test_get_audit_returns_collections(client) -> None:
    session_id = create_session(client)
    advance_to_state(client, session_id, "situation_capture")
    response = client.get(f"/v1/audit/sessions/{session_id}")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["transitions"], list)
    assert isinstance(body["risks"], list)
    assert isinstance(body["events"], list)


def test_unknown_session_returns_404(client) -> None:
    response = client.get("/v1/sessions/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_unknown_protocol_returns_404(client) -> None:
    response = client.get("/v1/protocols/does-not-exist")
    assert response.status_code == 404


def test_moderate_risk_session_start_keeps_flow_active(client) -> None:
    session_id = create_session(client)
    response = client.post(
        f"/v1/sessions/{session_id}/risk-screen",
        json={"free_text": "희망이 없고 잠을 거의 못 잤어요"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "eligibility_check"
    assert body["state_data"]["risk_level"] == "moderate"
    assert body["template_response"]["template_id"] == "risk.moderate"
    assert body["session"]["status"] == "active"


def test_high_risk_session_start_closes_into_crisis(client) -> None:
    session_id = create_session(client)
    response = client.post(
        f"/v1/sessions/{session_id}/risk-screen",
        json={"suicidal_intent": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "crisis"
    assert body["session"]["closed_reason"] == "safety_escalation"


def test_out_of_scope_sets_closed_reason(client) -> None:
    session_id = create_session(client)
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    response = client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "eligibility", "payload": {"is_adult": False, "target_condition": "gad"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "out_of_scope"
    assert body["session"]["closed_reason"] == "out_of_scope"

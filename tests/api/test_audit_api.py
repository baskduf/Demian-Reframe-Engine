from __future__ import annotations

from tests.helpers import advance_to_state, create_session


def test_audit_stores_transition_hashes_and_rule_metadata(client) -> None:
    session_id = create_session(client)
    advance_to_state(client, session_id, "worry_thought_capture")
    audit = client.get(f"/v1/audit/sessions/{session_id}")
    assert audit.status_code == 200
    body = audit.json()
    assert len(body["transitions"]) >= 2
    assert all(entry["template_ids"] for entry in body["transitions"])
    assert all(entry["input_hash"] for entry in body["transitions"])
    assert all(entry["output_hash"] for entry in body["transitions"])
    assert any(entry["matched_rule_ids"] for entry in body["transitions"])


def test_reassess_risk_adds_audit_traces(client) -> None:
    session_id = create_session(client)
    client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    before = client.get(f"/v1/audit/sessions/{session_id}").json()
    response = client.post(
        f"/v1/sessions/{session_id}/reassess-risk",
        json={"free_text": "희망이 없고 잠을 거의 못 잤어요"},
    )
    assert response.status_code == 200
    after = client.get(f"/v1/audit/sessions/{session_id}").json()
    assert len(after["risks"]) == len(before["risks"]) + 1
    assert len(after["events"]) == len(before["events"]) + 1
    assert len(after["transitions"]) == len(before["transitions"]) + 1


def test_audit_reproduces_expected_transition_order(client) -> None:
    session_id = create_session(client)
    advance_to_state(client, session_id, "alternative_thought")
    audit = client.get(f"/v1/audit/sessions/{session_id}")
    transitions = audit.json()["transitions"]
    to_states = [entry["to_state"] for entry in transitions]
    assert to_states[:7] == [
        "eligibility_check",
        "situation_capture",
        "worry_thought_capture",
        "emotion_body_behavior_capture",
        "distortion_hypothesis",
        "evidence_for",
        "evidence_against",
    ]

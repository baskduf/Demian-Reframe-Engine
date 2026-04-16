from __future__ import annotations


def test_happy_path_session(client) -> None:
    create = client.post("/v1/sessions", json={"user_id": "user-1"}).json()
    session_id = create["session"]["session_id"]

    steps = [
        (f"/v1/sessions/{session_id}/risk-screen", {}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "situation", "payload": {"situation_text": "상사와 면담 전", "trigger_text": "실수할까 봐 걱정"}}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "worry", "payload": {"automatic_thought": "틀리면 끝이야", "worry_prediction": "분명 망할 거야"}}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "emotion", "payload": {"emotions": [{"label": "anxiety", "intensity": 85}], "body_symptoms": ["심장 두근거림"], "safety_behaviors": ["발표를 미루고 싶음"]}}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "distortion", "payload": {"selected_distortion_ids": ["catastrophizing"]}}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "evidence_for", "payload": {"evidence_for": ["지난번에 말을 더듬었다"]}}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "evidence_against", "payload": {"evidence_against": ["준비한 내용은 충분하다"]}}),
        (f"/v1/sessions/{session_id}/events", {"event_type": "alternative", "payload": {"balanced_view": "실수 하나가 전체 실패를 뜻하지 않는다", "coping_statement": "준비한 핵심 세 문장부터 차분히 말하자"}}),
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

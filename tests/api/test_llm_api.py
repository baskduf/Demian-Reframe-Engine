from __future__ import annotations

from tests.helpers import advance_to_state, create_session


def test_parse_preview_returns_structured_json(mock_client) -> None:
    response = mock_client.post(
        "/v1/llm/parse-preview",
        json={"free_text": "상사와 면담 전 발표가 망할까 불안하다", "state": "situation_capture"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "structured_output" in body
    assert body["structured_output"]["situation_candidates"]
    assert body["invocation"]["task_type"] == "parse_structured"


def test_render_preview_returns_rendered_text(mock_client) -> None:
    response = mock_client.post(
        "/v1/llm/render-preview",
        json={"template_id": "prompt.situation", "source_text": "최근 걱정이 커졌던 상황을 적어주세요.", "context": {}},
    )
    assert response.status_code == 200
    assert response.json()["rendered_text"].startswith("[rendered]")


def test_event_free_text_uses_llm_candidates_and_persists_artifact(mock_client) -> None:
    session_id = create_session(mock_client)
    mock_client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    mock_client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}},
    )
    response = mock_client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "situation", "payload": {"free_text": "상사와 면담 전 발표가 망할까 불안하다", "trigger_text": "발표 일정"}},
    )
    assert response.status_code == 200
    assert response.json()["current_state"] == "worry_thought_capture"

    artifacts = mock_client.get(f"/v1/sessions/{session_id}/artifacts").json()
    assert artifacts["thought_record"]["situation_text"] == "상사와 면담 전"
    assert artifacts["thought_record"]["llm_situation_candidates"]


def test_needs_clarification_keeps_state_and_returns_missing_fields(mock_client) -> None:
    session_id = create_session(mock_client)
    advance_to_state(mock_client, session_id, "worry_thought_capture")
    response = mock_client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "worry", "payload": {"free_text": "clarify this please", "worry_prediction": "큰일 날 거야"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "worry_thought_capture"
    assert "automatic_thought" in body["clarification"]["missing_fields"]


def test_llm_risk_flag_does_not_override_deterministic_safety_logic(mock_client) -> None:
    session_id = create_session(mock_client)
    advance_to_state(mock_client, session_id, "situation_capture")
    response = mock_client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "situation", "payload": {"free_text": "flag_only but not an actual crisis phrase", "trigger_text": "trigger"}},
    )
    assert response.status_code == 200
    assert response.json()["current_state"] != "crisis"


def test_audit_includes_llm_invocations(mock_client) -> None:
    session_id = create_session(mock_client)
    advance_to_state(mock_client, session_id, "situation_capture")
    mock_client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "situation", "payload": {"free_text": "상사와 면담 전 발표가 망할까 불안하다", "trigger_text": "발표 일정"}},
    )
    audit = mock_client.get(f"/v1/audit/sessions/{session_id}")
    assert audit.status_code == 200
    body = audit.json()
    assert "llm_invocations" in body
    assert len(body["llm_invocations"]) >= 1


def test_llm_health_reports_enabled_state(mock_client) -> None:
    response = mock_client.get("/v1/health/llm")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["live_call_available"] is True


def test_llm_health_reports_disabled_state(disabled_llm_client) -> None:
    response = disabled_llm_client.get("/v1/health/llm")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["live_call_available"] is False


def test_live_check_returns_disabled_contract(disabled_llm_client) -> None:
    response = disabled_llm_client.post("/v1/llm/live-check", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "llm_disabled"


def test_live_check_returns_success_contract(mock_client) -> None:
    response = mock_client.post("/v1/llm/live-check", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["schema_valid"] is True


def test_parse_preview_is_stable_when_llm_is_disabled(disabled_llm_client) -> None:
    response = disabled_llm_client.post(
        "/v1/llm/parse-preview",
        json={"free_text": "자유 텍스트", "state": "situation_capture"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fallback_used"] is True
    assert body["invocation"]["error_code"] == "llm_disabled"


def test_render_preview_is_stable_when_llm_is_disabled(disabled_llm_client) -> None:
    response = disabled_llm_client.post(
        "/v1/llm/render-preview",
        json={"template_id": "prompt.situation", "source_text": "원문 템플릿", "context": {}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fallback_used"] is True
    assert body["rendered_text"] == "원문 템플릿"


def test_timeout_fallback_sets_state_data(failing_llm_client) -> None:
    session_id = create_session(failing_llm_client)
    failing_llm_client.post(f"/v1/sessions/{session_id}/risk-screen", json={})
    failing_llm_client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "eligibility", "payload": {"is_adult": True, "target_condition": "gad"}},
    )
    response = failing_llm_client.post(
        f"/v1/sessions/{session_id}/events",
        json={"event_type": "situation", "payload": {"free_text": "timeout please", "trigger_text": "발표 일정"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_state"] == "situation_capture"
    assert body["state_data"]["llm_fallback_used"] is True
    assert body["state_data"]["llm_error_code"] == "timeout"

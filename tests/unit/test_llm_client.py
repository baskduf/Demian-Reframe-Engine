from __future__ import annotations

import httpx
import pytest

from app.llm.client import (
    ERROR_HTTP,
    ERROR_INVALID_JSON,
    ERROR_MISSING_OUTPUT,
    ERROR_TIMEOUT,
    OpenAIClientError,
    OpenAIResponsesClient,
)


class DummyResponse:
    def __init__(self, *, text: str, payload, raise_http: bool = False) -> None:
        self.text = text
        self._payload = payload
        self._raise_http = raise_http

    def raise_for_status(self) -> None:
        if self._raise_http:
            raise httpx.HTTPStatusError("boom", request=httpx.Request("POST", "https://example.test"), response=httpx.Response(500))

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_request_json_maps_timeout(monkeypatch) -> None:
    def fake_post(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "post", fake_post)
    client = OpenAIResponsesClient(api_key="test-key")
    with pytest.raises(OpenAIClientError) as exc:
        client.request_json(model="test", system_prompt="s", user_prompt="u", schema_name="x", schema={})
    assert exc.value.code == ERROR_TIMEOUT


def test_request_json_maps_http_errors(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: DummyResponse(text="{}", payload={}, raise_http=True))
    client = OpenAIResponsesClient(api_key="test-key")
    with pytest.raises(OpenAIClientError) as exc:
        client.request_json(model="test", system_prompt="s", user_prompt="u", schema_name="x", schema={})
    assert exc.value.code == ERROR_HTTP


def test_request_json_maps_invalid_http_json(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: DummyResponse(text="not-json", payload=ValueError("bad json")))
    client = OpenAIResponsesClient(api_key="test-key")
    with pytest.raises(OpenAIClientError) as exc:
        client.request_json(model="test", system_prompt="s", user_prompt="u", schema_name="x", schema={})
    assert exc.value.code == ERROR_INVALID_JSON


def test_request_json_maps_missing_output_text(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: DummyResponse(text="{}", payload={"output": []}))
    client = OpenAIResponsesClient(api_key="test-key")
    with pytest.raises(OpenAIClientError) as exc:
        client.request_json(model="test", system_prompt="s", user_prompt="u", schema_name="x", schema={})
    assert exc.value.code == ERROR_MISSING_OUTPUT

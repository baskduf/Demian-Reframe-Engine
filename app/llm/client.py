from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx

from app.config.llm import OPENAI_BASE_URL, OPENAI_TIMEOUT_SECONDS, get_openai_api_key


class OpenAIClientError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class OpenAIResponsesClient:
    def __init__(self, api_key: str | None = None, base_url: str = OPENAI_BASE_URL, timeout_seconds: float = OPENAI_TIMEOUT_SECONDS) -> None:
        self.api_key = api_key or get_openai_api_key()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _hash_text(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def request_json(self, *, model: str, system_prompt: str, user_prompt: str, schema_name: str, schema: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if not self.enabled:
            raise OpenAIClientError("llm_disabled", "OPENAI_API_KEY is not configured")

        payload = {
            "model": model,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        }

        try:
            response = httpx.post(
                f"{self.base_url}/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise OpenAIClientError("timeout", str(exc)) from exc
        except httpx.HTTPError as exc:
            raise OpenAIClientError("http_error", str(exc)) from exc

        raw_body = response.text
        body = response.json()
        text_output = self._extract_output_text(body)
        try:
            parsed = json.loads(text_output)
        except json.JSONDecodeError as exc:
            raise OpenAIClientError("invalid_json", str(exc)) from exc
        return raw_body, parsed

    @staticmethod
    def _extract_output_text(body: dict[str, Any]) -> str:
        for item in body.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    return content["text"]
        if isinstance(body.get("output_text"), str) and body["output_text"]:
            return body["output_text"]
        raise OpenAIClientError("missing_output_text", "No output_text found in Responses API payload")

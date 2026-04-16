from __future__ import annotations

import os

import pytest

from app.llm.client import OpenAIResponsesClient
from app.services.llm_gateway import LLMGateway
from app.llm.contracts import LLMLiveCheckRequest
from app.schemas.models import StateEnum


pytestmark = pytest.mark.live


def _live_tests_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and os.getenv("OPENAI_ENABLE_LIVE_TESTS", "").lower() in {"1", "true", "yes", "on"}


@pytest.mark.skipif(not _live_tests_enabled(), reason="Live OpenAI tests require OPENAI_API_KEY and OPENAI_ENABLE_LIVE_TESTS=true")
def test_live_structured_output_matches_schema() -> None:
    gateway = LLMGateway(OpenAIResponsesClient())
    output, invocation = gateway.parse_structured(
        session_id=None,
        state=StateEnum.SITUATION_CAPTURE,
        free_text="회의 전에 발표가 망할까 불안하고 피하고 싶다.",
    )
    assert invocation.succeeded is True
    assert isinstance(output.model_dump(), dict)


@pytest.mark.skipif(not _live_tests_enabled(), reason="Live OpenAI tests require OPENAI_API_KEY and OPENAI_ENABLE_LIVE_TESTS=true")
def test_live_check_returns_valid_response() -> None:
    gateway = LLMGateway(OpenAIResponsesClient())
    response = gateway.live_check(LLMLiveCheckRequest())
    assert response.ok is True
    assert response.schema_valid is True

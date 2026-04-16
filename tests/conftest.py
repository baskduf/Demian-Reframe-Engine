from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.llm.contracts import (
    CandidateDistortion,
    CandidateEmotion,
    CandidateRiskFlag,
    CandidateText,
    LLMHealthResponse,
    LLMInvocationLog,
    LLMLiveCheckResponse,
    LLMRenderResponse,
    LLMStructuredOutput,
)
from app.main import create_app
from app.schemas.models import StateEnum


class FakeLLMGateway:
    @property
    def enabled(self) -> bool:
        return True

    def parse_structured(self, *, session_id, state, free_text: str):
        if "clarify" in free_text:
            output = LLMStructuredOutput(needs_clarification=True, missing_fields=["automatic_thought"])
        else:
            output = LLMStructuredOutput(
                situation_candidates=[CandidateText(text="상사와 면담 전", confidence=0.91, evidence_span="상사와 면담 전")],
                automatic_thought_candidates=[CandidateText(text="분명 실패할 거야", confidence=0.88, evidence_span="실패할 거야")],
                emotion_candidates=[CandidateEmotion(label="anxiety", intensity_hint=82, confidence=0.9, evidence_span="불안해")],
                behavior_candidates=[CandidateText(text="피하고 싶다", confidence=0.79, evidence_span="피하고 싶다")],
                distortion_candidates=[CandidateDistortion(label="fortune_telling", confidence=0.76, rationale_code="future_certainty")],
                risk_flags=[],
                needs_clarification=False,
                missing_fields=[],
                confidence={"overall": 0.82, "situation": 0.91, "automatic_thought": 0.88, "emotion": 0.9, "behavior": 0.79},
            )
        log = LLMInvocationLog(
            invocation_id=uuid4(),
            session_id=session_id,
            state=state,
            task_type="parse_structured",
            model_name="fake-structurer",
            model_version="fake-structurer",
            prompt_version="parser-test",
            request_hash="req-hash",
            response_hash="res-hash",
            raw_response="{}",
            parsed_output=output.model_dump(),
            succeeded=True,
        )
        return output, log

    def assist_risk(self, *, session_id, state, free_text: str):
        flags = []
        if "flag_only" in free_text:
            flags = [CandidateRiskFlag(flag="llm_only_flag", confidence=0.9, evidence_span="flag_only")]
        log = LLMInvocationLog(
            invocation_id=uuid4(),
            session_id=session_id,
            state=state,
            task_type="risk_assist",
            model_name="fake-risk",
            model_version="fake-risk",
            prompt_version="risk-test",
            request_hash="req-risk",
            response_hash="res-risk",
            raw_response="{}",
            parsed_output={"risk_flags": [flag.model_dump() for flag in flags]},
            succeeded=True,
        )
        return flags, log

    def render_text(self, *, session_id, state, template_id: str, source_text: str):
        fallback = "render_fail" in source_text
        rendered = LLMRenderResponse(rendered_text=source_text if fallback else f"[rendered] {source_text}", fallback_used=fallback)
        log = LLMInvocationLog(
            invocation_id=uuid4(),
            session_id=session_id,
            state=state,
            task_type="render_text",
            model_name="fake-renderer",
            model_version="fake-renderer",
            prompt_version="renderer-test",
            request_hash="req-render",
            response_hash="res-render",
            raw_response="{}",
            parsed_output=rendered.model_dump(),
            succeeded=not fallback,
            error_code="render_failed" if fallback else None,
        )
        return rendered, log

    def parse_preview(self, request):
        output, invocation = self.parse_structured(session_id=None, state=request.state, free_text=request.free_text)
        from app.llm.contracts import LLMParsePreviewResponse

        return LLMParsePreviewResponse(structured_output=output, fallback_used=False, invocation=invocation)

    def render_preview(self, request):
        rendered, invocation = self.render_text(session_id=None, state=None, template_id=request.template_id, source_text=request.source_text)
        from app.llm.contracts import LLMRenderPreviewResponse

        return LLMRenderPreviewResponse(rendered_text=rendered.rendered_text, fallback_used=rendered.fallback_used, invocation=invocation)

    def health(self):
        return LLMHealthResponse(
            enabled=True,
            api_key_configured=True,
            models_configured=True,
            live_call_available=True,
            live_test_enabled=False,
            base_url="https://example.test",
            structurer_model="fake-structurer",
            renderer_model="fake-renderer",
            risk_assist_model="fake-risk",
        )

    def live_check(self, request):
        return LLMLiveCheckResponse(
            ok=True,
            enabled=True,
            model_name="fake-structurer",
            prompt_version="parser-test",
            latency_ms=5.0,
            schema_valid=True,
            error_code=None,
            fallback_used=False,
        )


class DisabledLLMGateway:
    @property
    def enabled(self) -> bool:
        return False

    def parse_structured(self, *, session_id, state, free_text: str):
        output = LLMStructuredOutput(needs_clarification=True, missing_fields=["manual_structuring_required"])
        log = LLMInvocationLog(
            invocation_id=uuid4(),
            session_id=session_id,
            state=state,
            task_type="parse_structured",
            model_name="disabled",
            model_version="disabled",
            prompt_version="parser-disabled",
            request_hash="req-disabled",
            response_hash="res-disabled",
            raw_response="disabled",
            parsed_output=output.model_dump(),
            succeeded=False,
            error_code="llm_disabled",
        )
        return output, log

    def assist_risk(self, *, session_id, state, free_text: str):
        log = LLMInvocationLog(
            invocation_id=uuid4(),
            session_id=session_id,
            state=state,
            task_type="risk_assist",
            model_name="disabled",
            model_version="disabled",
            prompt_version="risk-disabled",
            request_hash="req-disabled",
            response_hash="res-disabled",
            raw_response="disabled",
            parsed_output={"risk_flags": []},
            succeeded=False,
            error_code="llm_disabled",
        )
        return [], log

    def render_text(self, *, session_id, state, template_id: str, source_text: str):
        rendered = LLMRenderResponse(rendered_text=source_text, fallback_used=True)
        log = LLMInvocationLog(
            invocation_id=uuid4(),
            session_id=session_id,
            state=state,
            task_type="render_text",
            model_name="disabled",
            model_version="disabled",
            prompt_version="renderer-disabled",
            request_hash="req-disabled",
            response_hash="res-disabled",
            raw_response="disabled",
            parsed_output=rendered.model_dump(),
            succeeded=False,
            error_code="llm_disabled",
        )
        return rendered, log

    def parse_preview(self, request):
        output, invocation = self.parse_structured(session_id=None, state=request.state, free_text=request.free_text)
        from app.llm.contracts import LLMParsePreviewResponse

        return LLMParsePreviewResponse(structured_output=output, fallback_used=True, invocation=invocation)

    def render_preview(self, request):
        rendered, invocation = self.render_text(session_id=None, state=None, template_id=request.template_id, source_text=request.source_text)
        from app.llm.contracts import LLMRenderPreviewResponse

        return LLMRenderPreviewResponse(rendered_text=rendered.rendered_text, fallback_used=True, invocation=invocation)

    def health(self):
        return LLMHealthResponse(
            enabled=False,
            api_key_configured=False,
            models_configured=True,
            live_call_available=False,
            live_test_enabled=False,
            base_url="https://api.openai.com/v1",
            structurer_model="disabled",
            renderer_model="disabled",
            risk_assist_model="disabled",
        )

    def live_check(self, request):
        return LLMLiveCheckResponse(
            ok=False,
            enabled=False,
            model_name="disabled",
            prompt_version="parser-disabled",
            latency_ms=0.0,
            schema_valid=False,
            error_code="llm_disabled",
            fallback_used=True,
        )


class FailingLLMGateway(FakeLLMGateway):
    def parse_structured(self, *, session_id, state, free_text: str):
        output = LLMStructuredOutput(needs_clarification=True, missing_fields=["manual_structuring_required"])
        log = LLMInvocationLog(
            invocation_id=uuid4(),
            session_id=session_id,
            state=state,
            task_type="parse_structured",
            model_name="failing",
            model_version="failing",
            prompt_version="parser-failing",
            request_hash="req-timeout",
            response_hash="res-timeout",
            raw_response="timeout",
            parsed_output=output.model_dump(),
            succeeded=False,
            error_code="timeout",
        )
        return output, log


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(str(tmp_path / "test.sqlite3"))
    return TestClient(app)


@pytest.fixture()
def mock_client(tmp_path: Path) -> TestClient:
    app = create_app(str(tmp_path / "test-llm.sqlite3"), llm_gateway=FakeLLMGateway())
    return TestClient(app)


@pytest.fixture()
def disabled_llm_client(tmp_path: Path) -> TestClient:
    app = create_app(str(tmp_path / "test-disabled.sqlite3"), llm_gateway=DisabledLLMGateway())
    return TestClient(app)


@pytest.fixture()
def failing_llm_client(tmp_path: Path) -> TestClient:
    app = create_app(str(tmp_path / "test-failing.sqlite3"), llm_gateway=FailingLLMGateway())
    return TestClient(app)

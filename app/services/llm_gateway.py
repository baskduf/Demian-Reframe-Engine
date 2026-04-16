from __future__ import annotations

import time

from app.config.llm import (
    OPENAI_BASE_URL,
    OPENAI_ENABLE_LIVE_TESTS,
    OPENAI_MODEL_RENDERER,
    OPENAI_MODEL_RISK_ASSIST,
    OPENAI_MODEL_STRUCTURER,
    live_call_available,
    llm_models_configured,
)
from app.llm.client import OpenAIClientError, OpenAIResponsesClient
from app.llm.contracts import (
    CandidateRiskFlag,
    LLMHealthResponse,
    LLMInvocationLog,
    LLMLiveCheckRequest,
    LLMLiveCheckResponse,
    LLMParsePreviewRequest,
    LLMParsePreviewResponse,
    LLMRenderRequest,
    LLMRenderResponse,
    LLMRenderPreviewResponse,
    LLMStructuredOutput,
)
from app.llm.parser import LLMParser
from app.llm.renderer import LLMRenderer
from app.llm.risk_assist import LLMRiskAssist


class LLMGateway:
    def __init__(self, client: OpenAIResponsesClient | None = None) -> None:
        self.client = client or OpenAIResponsesClient()
        self.parser = LLMParser(self.client)
        self.renderer = LLMRenderer(self.client)
        self.risk_assist = LLMRiskAssist(self.client)

    @property
    def enabled(self) -> bool:
        return self.client.enabled

    def parse_structured(self, *, session_id, state, free_text: str) -> tuple[LLMStructuredOutput, LLMInvocationLog]:
        return self.parser.parse(session_id=session_id, state=state, free_text=free_text)

    def render_text(self, *, session_id, state, template_id: str, source_text: str) -> tuple[LLMRenderResponse, LLMInvocationLog]:
        return self.renderer.render(session_id=session_id, state=state, template_id=template_id, source_text=source_text)

    def assist_risk(self, *, session_id, state, free_text: str) -> tuple[list[CandidateRiskFlag], LLMInvocationLog]:
        return self.risk_assist.assess(session_id=session_id, state=state, free_text=free_text)

    def parse_preview(self, request: LLMParsePreviewRequest) -> LLMParsePreviewResponse:
        output, invocation = self.parse_structured(session_id=None, state=request.state, free_text=request.free_text)
        return LLMParsePreviewResponse(structured_output=output, fallback_used=not invocation.succeeded, invocation=invocation)

    def render_preview(self, request: LLMRenderRequest) -> LLMRenderPreviewResponse:
        rendered, invocation = self.render_text(session_id=None, state=None, template_id=request.template_id, source_text=request.source_text)
        return LLMRenderPreviewResponse(rendered_text=rendered.rendered_text, fallback_used=rendered.fallback_used, invocation=invocation)

    def health(self) -> LLMHealthResponse:
        return LLMHealthResponse(
            enabled=self.enabled,
            api_key_configured=self.client.enabled,
            models_configured=llm_models_configured(),
            live_call_available=live_call_available(),
            live_test_enabled=OPENAI_ENABLE_LIVE_TESTS,
            base_url=OPENAI_BASE_URL,
            structurer_model=OPENAI_MODEL_STRUCTURER,
            renderer_model=OPENAI_MODEL_RENDERER,
            risk_assist_model=OPENAI_MODEL_RISK_ASSIST,
        )

    def live_check(self, request: LLMLiveCheckRequest) -> LLMLiveCheckResponse:
        started = time.perf_counter()
        try:
            output, invocation = self.parse_structured(session_id=None, state=request.state, free_text=request.free_text)
            latency_ms = (time.perf_counter() - started) * 1000
            return LLMLiveCheckResponse(
                ok=invocation.succeeded,
                enabled=self.enabled,
                model_name=invocation.model_name,
                prompt_version=invocation.prompt_version,
                latency_ms=round(latency_ms, 2),
                schema_valid=bool(output.model_dump() and invocation.succeeded),
                error_code=invocation.error_code,
                fallback_used=not invocation.succeeded,
            )
        except OpenAIClientError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return LLMLiveCheckResponse(
                ok=False,
                enabled=self.enabled,
                model_name=OPENAI_MODEL_STRUCTURER,
                prompt_version="parser-live-check",
                latency_ms=round(latency_ms, 2),
                schema_valid=False,
                error_code=exc.code,
                fallback_used=True,
            )

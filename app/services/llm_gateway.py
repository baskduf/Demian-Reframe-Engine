from __future__ import annotations

from app.llm.client import OpenAIResponsesClient
from app.llm.contracts import (
    CandidateRiskFlag,
    LLMInvocationLog,
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

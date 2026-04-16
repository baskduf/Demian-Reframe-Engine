from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.llm.contracts import LLMParsePreviewRequest, LLMParsePreviewResponse, LLMRenderPreviewResponse
from app.schemas.models import ArtifactsResponse, AuditResponse, CreateSessionRequest, EventRequest, ProtocolManifest, RiskScreenRequest, SessionEnvelope
from app.llm.contracts import LLMRenderRequest
from app.services.session_service import SessionService


def build_router(service: SessionService) -> APIRouter:
    router = APIRouter(prefix="/v1")

    @router.post("/sessions", response_model=SessionEnvelope)
    def create_session(request: CreateSessionRequest) -> SessionEnvelope:
        return service.create_session(request)

    @router.get("/sessions/{session_id}", response_model=SessionEnvelope)
    def get_session(session_id: UUID) -> SessionEnvelope:
        return service.get_session(session_id)

    @router.post("/sessions/{session_id}/events", response_model=SessionEnvelope)
    def submit_event(session_id: UUID, request: EventRequest) -> SessionEnvelope:
        return service.submit_event(session_id, request)

    @router.post("/sessions/{session_id}/risk-screen", response_model=SessionEnvelope)
    def submit_risk_screen(session_id: UUID, request: RiskScreenRequest) -> SessionEnvelope:
        return service.submit_risk_screen(session_id, request)

    @router.post("/sessions/{session_id}/reassess-risk", response_model=SessionEnvelope)
    def reassess_risk(session_id: UUID, request: RiskScreenRequest) -> SessionEnvelope:
        return service.reassess_risk(session_id, request)

    @router.get("/sessions/{session_id}/artifacts", response_model=ArtifactsResponse)
    def get_artifacts(session_id: UUID) -> ArtifactsResponse:
        return service.get_artifacts(session_id)

    @router.get("/protocols/{version}", response_model=ProtocolManifest)
    def get_protocol(version: str) -> ProtocolManifest:
        return service.get_protocol(version)

    @router.get("/audit/sessions/{session_id}", response_model=AuditResponse)
    def get_audit(session_id: UUID) -> AuditResponse:
        return service.get_audit(session_id)

    @router.post("/llm/parse-preview", response_model=LLMParsePreviewResponse)
    def parse_preview(request: LLMParsePreviewRequest) -> LLMParsePreviewResponse:
        return service.parse_preview(request)

    @router.post("/llm/render-preview", response_model=LLMRenderPreviewResponse)
    def render_preview(request: LLMRenderRequest) -> LLMRenderPreviewResponse:
        return service.render_preview(request)

    return router

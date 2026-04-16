from __future__ import annotations

from app.config.llm import OPENAI_MODEL_RENDERER
from app.llm.client import OpenAIClientError, OpenAIResponsesClient
from app.llm.contracts import LLMInvocationLog, LLMRenderResponse
from app.llm.prompts import RENDERER_PROMPT_VERSION, RENDERER_SYSTEM_PROMPT


class LLMRenderer:
    def __init__(self, client: OpenAIResponsesClient) -> None:
        self.client = client

    def render(self, *, session_id, state, template_id: str, source_text: str) -> tuple[LLMRenderResponse, LLMInvocationLog]:
        user_prompt = (
            f"Template ID: {template_id}\n"
            f"Source text: {source_text}\n\n"
            "Rewrite this as a short, neutral Korean sentence without changing the meaning. "
            "Return JSON with a single field rendered_text."
        )
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"rendered_text": {"type": "string"}},
            "required": ["rendered_text"],
        }
        try:
            raw_response, parsed = self.client.request_json(
                model=OPENAI_MODEL_RENDERER,
                system_prompt=RENDERER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                schema_name="cbt_render_output",
                schema=schema,
            )
            response = LLMRenderResponse(rendered_text=str(parsed["rendered_text"]), fallback_used=False)
            log = LLMInvocationLog(
                session_id=session_id,
                state=state,
                task_type="render_text",
                model_name=OPENAI_MODEL_RENDERER,
                model_version=OPENAI_MODEL_RENDERER,
                prompt_version=RENDERER_PROMPT_VERSION,
                request_hash=self.client._hash_text(user_prompt),
                response_hash=self.client._hash_text(raw_response),
                raw_response=raw_response,
                parsed_output=response.model_dump(),
                succeeded=True,
            )
            return response, log
        except OpenAIClientError as exc:
            fallback = LLMRenderResponse(rendered_text=source_text, fallback_used=True)
            log = LLMInvocationLog(
                session_id=session_id,
                state=state,
                task_type="render_text",
                model_name=OPENAI_MODEL_RENDERER,
                model_version=OPENAI_MODEL_RENDERER,
                prompt_version=RENDERER_PROMPT_VERSION,
                request_hash=self.client._hash_text(user_prompt),
                response_hash=self.client._hash_text(str(exc)),
                raw_response=str(exc),
                parsed_output=fallback.model_dump(),
                succeeded=False,
                error_code=exc.code,
            )
            return fallback, log

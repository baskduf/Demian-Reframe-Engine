from __future__ import annotations

import os


OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL_STRUCTURER = os.getenv("OPENAI_MODEL_STRUCTURER", "gpt-4.1-mini")
OPENAI_MODEL_RENDERER = os.getenv("OPENAI_MODEL_RENDERER", "gpt-4.1-mini")
OPENAI_MODEL_RISK_ASSIST = os.getenv("OPENAI_MODEL_RISK_ASSIST", "gpt-4.1-mini")
OPENAI_MODEL_SYNTHETIC_GENERATOR = os.getenv("OPENAI_MODEL_SYNTHETIC_GENERATOR", OPENAI_MODEL_STRUCTURER)
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "20"))
LLM_CONFIDENCE_THRESHOLD = float(os.getenv("LLM_CONFIDENCE_THRESHOLD", "0.6"))
OPENAI_ENABLE_LIVE_TESTS = os.getenv("OPENAI_ENABLE_LIVE_TESTS", "0").lower() in {"1", "true", "yes", "on"}
OPENAI_ENABLE_LIVE_EVAL = os.getenv("OPENAI_ENABLE_LIVE_EVAL", os.getenv("OPENAI_ENABLE_LIVE_TESTS", "0")).lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def get_openai_api_key() -> str | None:
    return os.getenv(OPENAI_API_KEY_ENV)


def llm_models_configured() -> bool:
    return all([OPENAI_MODEL_STRUCTURER, OPENAI_MODEL_RENDERER, OPENAI_MODEL_RISK_ASSIST, OPENAI_MODEL_SYNTHETIC_GENERATOR])


def live_call_available() -> bool:
    return bool(get_openai_api_key()) and llm_models_configured()

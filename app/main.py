from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import build_router
from app.persistence.sqlite import SQLiteRepository
from app.services.llm_gateway import LLMGateway
from app.services.session_service import SessionService


def create_app(db_path: str = "data/cbt_engine.sqlite3", llm_gateway: LLMGateway | None = None) -> FastAPI:
    repository = SQLiteRepository(db_path)
    service = SessionService(repository, llm_gateway=llm_gateway)
    app = FastAPI(title="GAD CBT Engine", version="0.1.0")
    app.include_router(build_router(service))
    return app


app = create_app()

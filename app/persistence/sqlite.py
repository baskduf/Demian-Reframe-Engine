from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from app.schemas.models import LLMInvocationLog, RiskAssessment, Session, SessionEvent, ThoughtRecord, TransitionLog


class SQLiteRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS risk_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS thought_records (
                    session_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transition_logs (
                    transition_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS llm_invocations (
                    invocation_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    payload TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _dump(model: Any) -> str:
        return model.model_dump_json() if hasattr(model, "model_dump_json") else json.dumps(model)

    def upsert_session(self, session: Session) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions(session_id, user_id, payload) VALUES (?, ?, ?)",
                (str(session.session_id), session.user_id, self._dump(session)),
            )

    def get_session(self, session_id: UUID) -> Session | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM sessions WHERE session_id = ?", (str(session_id),)).fetchone()
        return None if row is None else Session.model_validate_json(row["payload"])

    def add_event(self, event: SessionEvent) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events(event_id, session_id, payload) VALUES (?, ?, ?)",
                (str(event.event_id), str(event.session_id), self._dump(event)),
            )

    def list_events(self, session_id: UUID) -> list[SessionEvent]:
        adapter = TypeAdapter(list[SessionEvent])
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM events WHERE session_id = ? ORDER BY rowid", (str(session_id),)).fetchall()
        return adapter.validate_python([json.loads(row["payload"]) for row in rows])

    def add_risk(self, risk: RiskAssessment) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO risk_assessments(assessment_id, session_id, payload) VALUES (?, ?, ?)",
                (str(risk.assessment_id), str(risk.session_id), self._dump(risk)),
            )

    def list_risks(self, session_id: UUID) -> list[RiskAssessment]:
        adapter = TypeAdapter(list[RiskAssessment])
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM risk_assessments WHERE session_id = ? ORDER BY rowid",
                (str(session_id),),
            ).fetchall()
        return adapter.validate_python([json.loads(row["payload"]) for row in rows])

    def save_thought_record(self, record: ThoughtRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO thought_records(session_id, payload) VALUES (?, ?)",
                (str(record.session_id), self._dump(record)),
            )

    def get_thought_record(self, session_id: UUID) -> ThoughtRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM thought_records WHERE session_id = ?", (str(session_id),)).fetchone()
        return None if row is None else ThoughtRecord.model_validate_json(row["payload"])

    def add_transition(self, transition: TransitionLog) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO transition_logs(transition_id, session_id, payload) VALUES (?, ?, ?)",
                (str(transition.transition_id), str(transition.session_id), self._dump(transition)),
            )

    def list_transitions(self, session_id: UUID) -> list[TransitionLog]:
        adapter = TypeAdapter(list[TransitionLog])
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM transition_logs WHERE session_id = ? ORDER BY rowid",
                (str(session_id),),
            ).fetchall()
        return adapter.validate_python([json.loads(row["payload"]) for row in rows])

    def add_llm_invocation(self, invocation: LLMInvocationLog) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO llm_invocations(invocation_id, session_id, payload) VALUES (?, ?, ?)",
                (str(invocation.invocation_id), str(invocation.session_id) if invocation.session_id else None, self._dump(invocation)),
            )

    def list_llm_invocations(self, session_id: UUID) -> list[LLMInvocationLog]:
        adapter = TypeAdapter(list[LLMInvocationLog])
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM llm_invocations WHERE session_id = ? ORDER BY rowid",
                (str(session_id),),
            ).fetchall()
        return adapter.validate_python([json.loads(row["payload"]) for row in rows])

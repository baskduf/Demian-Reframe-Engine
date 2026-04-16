from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from eval.models import EvalCase, EvalPrediction


def load_eval_cases(path: str | Path) -> list[EvalCase]:
    file_path = Path(path)
    lines = [line for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    adapter = TypeAdapter(list[EvalCase])
    return adapter.validate_python([json.loads(line) for line in lines])


def load_eval_predictions(path: str | Path) -> list[EvalPrediction]:
    file_path = Path(path)
    lines = [line for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    adapter = TypeAdapter(list[EvalPrediction])
    return adapter.validate_python([json.loads(line) for line in lines])


def write_json(path: str | Path, payload: dict) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: str | Path, content: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

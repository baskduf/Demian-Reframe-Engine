from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from eval.models import DatasetManifest, EvalCase, EvalPrediction, EvalSummary


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


def load_dataset_manifest(path: str | Path) -> DatasetManifest:
    file_path = Path(path)
    return DatasetManifest.model_validate(json.loads(file_path.read_text(encoding="utf-8")))


def infer_manifest_path(dataset_path: str | Path) -> Path:
    file_path = Path(dataset_path)
    return file_path.with_suffix(".manifest.json")


def load_eval_summary(path: str | Path) -> EvalSummary:
    file_path = Path(path)
    if file_path.is_dir():
        file_path = file_path / "summary.json"
    return EvalSummary.model_validate(json.loads(file_path.read_text(encoding="utf-8")))


def write_json(path: str | Path, payload: dict) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: str | Path, content: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

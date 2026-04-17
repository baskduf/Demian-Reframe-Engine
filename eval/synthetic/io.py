from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from eval.loader import write_json
from eval.synthetic.models import (
    SyntheticApprovedCase,
    SyntheticGenerationConfig,
    SyntheticRawRecord,
    SyntheticReviewRecord,
    SyntheticRunManifest,
)


def ensure_parent(path: str | Path) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return file_path


def load_generation_config(path: str | Path) -> SyntheticGenerationConfig:
    file_path = Path(path)
    return SyntheticGenerationConfig.model_validate(json.loads(file_path.read_text(encoding="utf-8-sig")))


def load_raw_records(path: str | Path) -> list[SyntheticRawRecord]:
    file_path = Path(path)
    lines = [line for line in file_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    return TypeAdapter(list[SyntheticRawRecord]).validate_python([json.loads(line) for line in lines])


def load_review_records(path: str | Path) -> list[SyntheticReviewRecord]:
    file_path = Path(path)
    lines = [line for line in file_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    return TypeAdapter(list[SyntheticReviewRecord]).validate_python([json.loads(line) for line in lines])


def load_approved_cases(path: str | Path) -> list[SyntheticApprovedCase]:
    file_path = Path(path)
    lines = [line for line in file_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    return TypeAdapter(list[SyntheticApprovedCase]).validate_python([json.loads(line) for line in lines])


def write_jsonl(path: str | Path, records: list[dict]) -> None:
    file_path = ensure_parent(path)
    file_path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + ("\n" if records else ""), encoding="utf-8")


def write_manifest(path: str | Path, manifest: SyntheticRunManifest) -> None:
    write_json(path, manifest.model_dump(mode="json"))


def load_manifest(path: str | Path) -> SyntheticRunManifest:
    file_path = Path(path)
    return SyntheticRunManifest.model_validate(json.loads(file_path.read_text(encoding="utf-8-sig")))

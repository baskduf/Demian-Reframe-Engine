from __future__ import annotations

import argparse
import json
from pathlib import Path

from eval.baselines.models import BaselineRecord, BaselineRegistry

BASELINE_REGISTRY_PATH = Path("eval/baselines/baselines.json")


def load_baseline_registry(path: str | Path = BASELINE_REGISTRY_PATH) -> BaselineRegistry:
    file_path = Path(path)
    return BaselineRegistry.model_validate(json.loads(file_path.read_text(encoding="utf-8-sig")))


def get_baseline_record(baseline_id: str, path: str | Path = BASELINE_REGISTRY_PATH) -> BaselineRecord:
    registry = load_baseline_registry(path)
    for record in registry.records:
        if record.baseline_id == baseline_id:
            return record
    raise KeyError(f"Unknown baseline id: {baseline_id}")


def resolve_baseline_path(baseline_or_path: str) -> str:
    candidate_path = Path(baseline_or_path)
    if candidate_path.exists():
        return str(candidate_path)
    return get_baseline_record(baseline_or_path).run_path


def _list_baselines() -> int:
    registry = load_baseline_registry()
    for record in registry.records:
        print(f"{record.baseline_id}\t{record.status}\t{record.run_path}")
    return 0


def _show_baseline(baseline_id: str) -> int:
    record = get_baseline_record(baseline_id)
    print(json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect locked evaluation baselines.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("--id", required=True)
    args = parser.parse_args()
    if args.command == "list":
        return _list_baselines()
    return _show_baseline(args.id)


if __name__ == "__main__":
    raise SystemExit(main())


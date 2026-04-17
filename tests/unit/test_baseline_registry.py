from __future__ import annotations

from pathlib import Path

from eval.baselines.registry import get_baseline_record, load_baseline_registry, resolve_baseline_path


def test_baseline_registry_contains_expected_statuses() -> None:
    registry = load_baseline_registry()
    records = {record.baseline_id: record for record in registry.records}
    assert records["expanded-live-eval"].status == "official"
    assert records["live-thought-distortion-v3"].status == "reference"
    assert records["clarification-live-v2"].status == "experimental"
    assert records["synthetic-live-eval-002"].status == "experimental_provisional"
    assert records["synthetic-live-eval-005-reviewed-v2"].status == "experimental_reviewed"


def test_resolve_baseline_path_returns_locked_run_path() -> None:
    record = get_baseline_record("expanded-live-eval")
    assert resolve_baseline_path("expanded-live-eval") == record.run_path
    assert Path(resolve_baseline_path(record.run_path)) == Path(record.run_path)

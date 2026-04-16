from __future__ import annotations

from pathlib import Path

from eval.models import EvalRunConfig
from eval.run_eval import run_evaluation


DATASET_PATH = Path("eval/datasets/sample_gad_gold.jsonl")
PREDICTIONS_PATH = Path("eval/datasets/sample_predictions.jsonl")


def test_static_eval_runner_generates_reports(tmp_path) -> None:
    output_dir = tmp_path / "reports"
    summary = run_evaluation(
        EvalRunConfig(
            dataset_path=DATASET_PATH,
            predictions_path=PREDICTIONS_PATH,
            output_dir=output_dir,
            mode="static",
            allow_live_eval=False,
        )
    )

    assert summary["skipped"] is False
    assert output_dir.joinpath("summary.json").exists()
    assert output_dir.joinpath("case_results.json").exists()
    assert output_dir.joinpath("report.md").exists()


def test_live_eval_runner_safely_skips_without_configuration(tmp_path) -> None:
    output_dir = tmp_path / "reports"
    summary = run_evaluation(
        EvalRunConfig(
            dataset_path=DATASET_PATH,
            output_dir=output_dir,
            mode="live",
            allow_live_eval=False,
        )
    )

    assert summary["skipped"] is True
    assert summary["reason"] == "live_eval_disabled"
    assert output_dir.joinpath("summary.json").exists()
    assert output_dir.joinpath("report.md").exists()

from __future__ import annotations

from pathlib import Path

from eval.baselines.registry import resolve_baseline_path
from eval.compare_runs import compare_runs
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
    assert "run_metadata" in summary
    assert summary["run_metadata"]["dataset_version"] == "2026-04-16-expanded-v1"
    assert summary["run_metadata"]["case_mix"]["clarification"] >= 10
    assert summary["metrics"]["risk_expected_case_recall"] >= 0.0
    assert summary["metrics"]["automatic_thought_case_hit_rate"] >= 0.0
    assert summary["metrics"]["clarification_case_accuracy"] >= 0.0
    assert output_dir.joinpath("summary.json").exists()
    assert output_dir.joinpath("case_results.json").exists()
    assert output_dir.joinpath("report.md").exists()
    report_text = output_dir.joinpath("report.md").read_text(encoding="utf-8")
    assert "Risk-Case Summary" in report_text
    assert "Clarification Summary" in report_text
    assert "Common predicted missing-field patterns" in report_text
    assert "Emotion Miss Summary" in report_text
    assert "Automatic Thought Miss Summary" in report_text
    assert "Distortion Miss Summary" in report_text


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
    assert summary["run_metadata"]["live_eval_enabled"] is False
    assert output_dir.joinpath("summary.json").exists()
    assert output_dir.joinpath("report.md").exists()


def test_compare_runs_generates_worsened_case_report(tmp_path) -> None:
    baseline_dir = tmp_path / "baseline"
    candidate_dir = tmp_path / "candidate"

    run_evaluation(
        EvalRunConfig(
            dataset_path=DATASET_PATH,
            predictions_path=PREDICTIONS_PATH,
            output_dir=baseline_dir,
            mode="static",
            allow_live_eval=False,
            report_label="baseline",
        )
    )

    degraded_predictions = tmp_path / "degraded_predictions.jsonl"
    degraded_predictions.write_text(
        PREDICTIONS_PATH.read_text(encoding="utf-8").replace('"risk_flags":["suicidal_intent"]', '"risk_flags":[]', 1),
        encoding="utf-8",
    )
    run_evaluation(
        EvalRunConfig(
            dataset_path=DATASET_PATH,
            predictions_path=degraded_predictions,
            output_dir=candidate_dir,
            mode="static",
            allow_live_eval=False,
            report_label="candidate",
        )
    )

    comparison = compare_runs(baseline_dir, candidate_dir)
    assert comparison.metric_deltas["risk_false_negative_count"].delta == 1
    assert any(case.case_id == "case-017" for case in comparison.worsened_cases)
    assert "risk_expected_case_recall" in comparison.metric_deltas
    assert "automatic_thought_hit_rate" in comparison.metric_deltas
    assert "distortion_top3_hit_rate" in comparison.metric_deltas
    assert "automatic_thought_case_hit_rate" in comparison.metric_deltas
    assert "clarification_case_accuracy" in comparison.metric_deltas


def test_compare_runs_accepts_locked_baseline_id(tmp_path) -> None:
    candidate_dir = tmp_path / "candidate"
    run_evaluation(
        EvalRunConfig(
            dataset_path=DATASET_PATH,
            predictions_path=PREDICTIONS_PATH,
            output_dir=candidate_dir,
            mode="static",
            allow_live_eval=False,
            report_label="candidate",
        )
    )
    comparison = compare_runs("expanded-live-eval", candidate_dir)
    assert comparison.baseline_label == "expanded-live-eval"
    assert resolve_baseline_path("expanded-live-eval").endswith("eval/reports/live/expanded-live-eval")

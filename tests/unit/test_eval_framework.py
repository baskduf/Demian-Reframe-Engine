from __future__ import annotations

from pathlib import Path

from eval.loader import infer_manifest_path, load_dataset_manifest, load_eval_cases, load_eval_predictions
from eval.scorer import aggregate_metrics, score_case


DATASET_PATH = Path("eval/datasets/sample_gad_gold.jsonl")
PREDICTIONS_PATH = Path("eval/datasets/sample_predictions.jsonl")


def test_eval_loader_reads_sample_dataset() -> None:
    cases = load_eval_cases(DATASET_PATH)
    assert len(cases) >= 20
    assert cases[0].case_id == "case-001"


def test_eval_loader_reads_sample_predictions() -> None:
    predictions = load_eval_predictions(PREDICTIONS_PATH)
    assert len(predictions) >= 20
    assert predictions[0].case_id == "case-001"


def test_eval_loader_reads_dataset_manifest() -> None:
    manifest = load_dataset_manifest(infer_manifest_path(DATASET_PATH))
    assert manifest.dataset_name == "sample_gad_gold"
    assert manifest.case_count >= 20


def test_eval_scoring_detects_complete_match() -> None:
    case = load_eval_cases(DATASET_PATH)[0]
    prediction = load_eval_predictions(PREDICTIONS_PATH)[0]
    result = score_case(case, prediction)
    assert result.situation_hit is True
    assert result.emotion_label_hit is True
    assert result.behavior_hit is True
    assert result.needs_clarification_hit is True


def test_eval_metrics_are_deterministic() -> None:
    cases = load_eval_cases(DATASET_PATH)
    predictions = {prediction.case_id: prediction for prediction in load_eval_predictions(PREDICTIONS_PATH)}
    results_first = [score_case(case, predictions[case.case_id]) for case in cases]
    results_second = [score_case(case, predictions[case.case_id]) for case in cases]

    first_metrics = aggregate_metrics(results_first)
    second_metrics = aggregate_metrics(results_second)

    assert first_metrics.model_dump() == second_metrics.model_dump()
    assert first_metrics.total_cases == len(cases)
    assert first_metrics.risk_false_negative_count == 0

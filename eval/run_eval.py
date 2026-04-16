from __future__ import annotations

import argparse
from pathlib import Path

from app.services.llm_gateway import LLMGateway
from eval.adapter import live_eval_enabled, predict_case_with_gateway
from eval.loader import load_eval_cases, load_eval_predictions, write_json, write_markdown
from eval.models import EvalPrediction, EvalRunConfig
from eval.scorer import aggregate_metrics, score_case


def _markdown_report(summary: dict, case_results: list[dict]) -> str:
    lines = [
        "# Model Evaluation Report",
        "",
        f"- Total cases: {summary['metrics']['total_cases']}",
        f"- Situation hit rate: {summary['metrics']['situation_hit_rate']:.2f}",
        f"- Automatic thought hit rate: {summary['metrics']['automatic_thought_hit_rate']:.2f}",
        f"- Emotion label hit rate: {summary['metrics']['emotion_label_hit_rate']:.2f}",
        f"- Behavior hit rate: {summary['metrics']['behavior_hit_rate']:.2f}",
        f"- Clarification accuracy: {summary['metrics']['needs_clarification_accuracy']:.2f}",
        f"- Distortion top-3 hit rate: {summary['metrics']['distortion_top3_hit_rate']:.2f}",
        f"- Risk false negatives: {summary['metrics']['risk_false_negative_count']}",
        f"- Schema valid rate: {summary['metrics']['schema_valid_rate']:.2f}",
        f"- Fallback rate: {summary['metrics']['fallback_rate']:.2f}",
        "",
        "## Case Errors",
        "",
    ]
    for case in case_results:
        if case["errors"]:
            lines.append(f"- `{case['case_id']}`: {', '.join(case['errors'])}")
    if len(lines) == 12:
        lines.append("- No case-level errors.")
    return "\n".join(lines) + "\n"


def run_evaluation(config: EvalRunConfig) -> dict:
    cases = load_eval_cases(config.dataset_path)
    if config.mode == "live":
        if not config.allow_live_eval or not live_eval_enabled():
            summary = {
                "mode": "live",
                "skipped": True,
                "reason": "live_eval_disabled",
                "metrics": {"total_cases": 0},
                "case_results": [],
            }
            config.output_dir.mkdir(parents=True, exist_ok=True)
            write_json(config.output_dir / "summary.json", summary)
            write_markdown(config.output_dir / "report.md", "# Model Evaluation Report\n\n- Live evaluation skipped.\n")
            return summary
        gateway = LLMGateway()
        predictions = [predict_case_with_gateway(case, gateway) for case in cases]
    else:
        if config.predictions_path is None:
            raise ValueError("predictions_path is required for static mode")
        predictions = load_eval_predictions(config.predictions_path)

    prediction_by_case = {item.case_id: item for item in predictions}
    case_results = []
    for case in cases:
        prediction = prediction_by_case.get(case.case_id, EvalPrediction(case_id=case.case_id))
        case_results.append(score_case(case, prediction))

    metrics = aggregate_metrics(case_results)
    summary = {
        "mode": config.mode,
        "skipped": False,
        "metrics": metrics.model_dump(),
        "case_results": [item.model_dump() for item in case_results],
    }
    config.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(config.output_dir / "summary.json", summary)
    write_json(config.output_dir / "case_results.json", {"case_results": [item.model_dump() for item in case_results]})
    write_markdown(config.output_dir / "report.md", _markdown_report(summary, [item.model_dump() for item in case_results]))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LLM evaluation against a CBT gold set.")
    parser.add_argument("--dataset", default="eval/datasets/sample_gad_gold.jsonl")
    parser.add_argument("--predictions", default="eval/datasets/sample_predictions.jsonl")
    parser.add_argument("--output-dir", default="eval/reports")
    parser.add_argument("--mode", choices=["static", "live"], default="static")
    args = parser.parse_args()

    config = EvalRunConfig(
        dataset_path=Path(args.dataset),
        predictions_path=Path(args.predictions) if args.mode == "static" else None,
        output_dir=Path(args.output_dir),
        mode=args.mode,
        allow_live_eval=True,
    )
    run_evaluation(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

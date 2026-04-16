from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from app.services.llm_gateway import LLMGateway
from eval.adapter import live_eval_enabled, predict_case_with_gateway
from eval.loader import infer_manifest_path, load_dataset_manifest, load_eval_cases, load_eval_predictions, write_json, write_markdown
from eval.models import DatasetManifest, EvalPrediction, EvalRunConfig, EvalRunMetadata, EvalSummary
from eval.scorer import aggregate_metrics, score_case


def _resolve_output_dir(base_output_dir: Path, mode: str, run_name: str) -> Path:
    if base_output_dir == Path("eval/reports"):
        return base_output_dir / mode / run_name
    return base_output_dir


def _load_manifest(config: EvalRunConfig, case_count: int) -> DatasetManifest:
    manifest_path = infer_manifest_path(config.dataset_path)
    if manifest_path.exists():
        return load_dataset_manifest(manifest_path)
    return DatasetManifest(
        dataset_name=config.dataset_name or config.dataset_path.stem,
        dataset_version=config.dataset_version or "unversioned",
        case_count=case_count,
        language="ko",
        notes="Inferred manifest",
    )


def _build_run_metadata(
    *,
    config: EvalRunConfig,
    manifest: DatasetManifest,
    predictions: list[EvalPrediction],
    run_timestamp: datetime,
    live_enabled: bool,
) -> EvalRunMetadata:
    first_prediction = next((item for item in predictions if item.model_name or item.prompt_version or item.risk_prompt_version), None)
    run_name = config.run_name or f"{config.mode}-{run_timestamp.strftime('%Y%m%d-%H%M%S')}"
    return EvalRunMetadata(
        run_name=run_name,
        report_label=config.report_label or run_name,
        run_timestamp=run_timestamp,
        mode=config.mode,
        dataset_name=config.dataset_name or manifest.dataset_name,
        dataset_version=config.dataset_version or manifest.dataset_version,
        dataset_path=str(config.dataset_path),
        case_count=manifest.case_count,
        live_eval_enabled=live_enabled,
        include_live_risk_assist=config.include_live_risk_assist,
        include_latency=True,
        model_name=first_prediction.model_name if first_prediction else "",
        prompt_version=first_prediction.prompt_version if first_prediction else "",
        risk_prompt_version=first_prediction.risk_prompt_version if first_prediction else "",
    )


def _markdown_report(summary: EvalSummary) -> str:
    metrics = summary.metrics
    meta = summary.run_metadata
    emotion_misses = [case.case_id for case in summary.case_results if not case.emotion_label_hit]
    risk_false_negative_cases = [case.case_id for case in summary.case_results if case.risk_false_negative]
    lines = [
        "# Model Evaluation Report",
        "",
        f"- Run: {meta.report_label}",
        f"- Mode: {meta.mode}",
        f"- Timestamp: {meta.run_timestamp.isoformat()}",
        f"- Dataset: {meta.dataset_name} ({meta.dataset_version})",
        f"- Model: {meta.model_name or 'n/a'}",
        f"- Parser prompt: {meta.prompt_version or 'n/a'}",
        f"- Risk prompt: {meta.risk_prompt_version or 'n/a'}",
        f"- Total cases: {metrics.total_cases}",
        f"- Situation hit rate: {metrics.situation_hit_rate:.2f}",
        f"- Automatic thought hit rate: {metrics.automatic_thought_hit_rate:.2f}",
        f"- Emotion label hit rate: {metrics.emotion_label_hit_rate:.2f}",
        f"- Behavior hit rate: {metrics.behavior_hit_rate:.2f}",
        f"- Clarification accuracy: {metrics.needs_clarification_accuracy:.2f}",
        f"- Distortion top-3 hit rate: {metrics.distortion_top3_hit_rate:.2f}",
        f"- Risk false negatives: {metrics.risk_false_negative_count}",
        f"- Risk expected case recall: {metrics.risk_expected_case_recall:.2f}",
        f"- Schema invalid count: {sum(1 for item in summary.case_results if not item.schema_valid)}",
        f"- Fallback count: {sum(1 for item in summary.case_results if item.fallback_used)}",
        f"- Banned content count: {sum(1 for item in summary.case_results if item.banned_content)}",
        "",
        "## Risk-Case Summary",
        "",
        f"- Expected risk cases: {metrics.risk_expected_case_count}",
        f"- Expected risk case recall: {metrics.risk_expected_case_recall:.2f}",
        f"- False negative cases: {', '.join(risk_false_negative_cases) if risk_false_negative_cases else 'None'}",
        "",
        "## Emotion Miss Summary",
        "",
        f"- Emotion misses: {len(emotion_misses)}",
        f"- Missed cases: {', '.join(emotion_misses) if emotion_misses else 'None'}",
        "",
        "## Case Errors",
        "",
    ]
    error_cases = 0
    for case in summary.case_results:
        if case.errors:
            error_cases += 1
            lines.append(f"- `{case.case_id}`: {', '.join(case.errors)}")
    if error_cases == 0:
        lines.append("- No case-level errors.")
    return "\n".join(lines) + "\n"


def run_evaluation(config: EvalRunConfig) -> dict:
    cases = load_eval_cases(config.dataset_path)
    manifest = _load_manifest(config, len(cases))
    run_timestamp = datetime.utcnow()
    run_name = config.run_name or f"{config.mode}-{run_timestamp.strftime('%Y%m%d-%H%M%S')}"
    output_dir = _resolve_output_dir(config.output_dir, config.mode, run_name)

    if config.mode == "live":
        if not config.allow_live_eval or not live_eval_enabled():
            summary = EvalSummary(
                mode="live",
                skipped=True,
                reason="live_eval_disabled",
                run_metadata=EvalRunMetadata(
                    run_name=run_name,
                    report_label=config.report_label or run_name,
                    run_timestamp=run_timestamp,
                    mode="live",
                    dataset_name=config.dataset_name or manifest.dataset_name,
                    dataset_version=config.dataset_version or manifest.dataset_version,
                    dataset_path=str(config.dataset_path),
                    case_count=manifest.case_count,
                    live_eval_enabled=False,
                    include_live_risk_assist=config.include_live_risk_assist,
                    include_latency=True,
                ),
                metrics=aggregate_metrics([]),
                case_results=[],
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            write_json(output_dir / "summary.json", summary.model_dump(mode="json"))
            write_markdown(output_dir / "report.md", "# Model Evaluation Report\n\n- Live evaluation skipped.\n")
            return summary.model_dump(mode="json")
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

    summary = EvalSummary(
        mode=config.mode,
        skipped=False,
        run_metadata=_build_run_metadata(
            config=config,
            manifest=manifest,
            predictions=predictions,
            run_timestamp=run_timestamp,
            live_enabled=(config.mode == "live" and config.allow_live_eval and live_eval_enabled()),
        ),
        metrics=aggregate_metrics(case_results),
        case_results=case_results,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "summary.json", summary.model_dump(mode="json"))
    write_json(output_dir / "case_results.json", {"case_results": [item.model_dump(mode="json") for item in case_results]})
    write_markdown(output_dir / "report.md", _markdown_report(summary))
    return summary.model_dump(mode="json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LLM evaluation against a CBT gold set.")
    parser.add_argument("--dataset", default="eval/datasets/sample_gad_gold.jsonl")
    parser.add_argument("--predictions", default="eval/datasets/sample_predictions.jsonl")
    parser.add_argument("--output-dir", default="eval/reports")
    parser.add_argument("--mode", choices=["static", "live"], default="static")
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--dataset-name", default=None)
    parser.add_argument("--dataset-version", default=None)
    parser.add_argument("--report-label", default=None)
    args = parser.parse_args()

    config = EvalRunConfig(
        dataset_path=Path(args.dataset),
        predictions_path=Path(args.predictions) if args.mode == "static" else None,
        output_dir=Path(args.output_dir),
        mode=args.mode,
        allow_live_eval=True,
        run_name=args.run_name,
        dataset_name=args.dataset_name,
        dataset_version=args.dataset_version,
        report_label=args.report_label,
    )
    run_evaluation(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

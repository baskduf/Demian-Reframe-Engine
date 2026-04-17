from __future__ import annotations

import argparse
from pathlib import Path

from eval.baselines.registry import resolve_baseline_path
from eval.loader import load_eval_summary, write_json, write_markdown
from eval.models import EvalComparison, EvalComparisonCaseDelta, EvalComparisonMetricDelta


METRIC_FIELDS = [
    "situation_hit_rate",
    "automatic_thought_hit_rate",
    "automatic_thought_case_hit_rate",
    "emotion_label_hit_rate",
    "behavior_hit_rate",
    "needs_clarification_accuracy",
    "clarification_case_accuracy",
    "missing_fields_overlap",
    "distortion_top1_hit_rate",
    "distortion_top3_hit_rate",
    "distortion_case_top3_hit_rate",
    "risk_flag_recall",
    "risk_expected_case_recall",
    "risk_false_negative_count",
    "schema_valid_rate",
    "fallback_rate",
    "banned_content_rate",
    "avg_latency_ms",
]


def compare_runs(baseline_path: str | Path, candidate_path: str | Path) -> EvalComparison:
    baseline = load_eval_summary(resolve_baseline_path(str(baseline_path)))
    candidate = load_eval_summary(resolve_baseline_path(str(candidate_path)))

    metric_deltas: dict[str, EvalComparisonMetricDelta] = {}
    for field in METRIC_FIELDS:
        baseline_value = getattr(baseline.metrics, field)
        candidate_value = getattr(candidate.metrics, field)
        metric_deltas[field] = EvalComparisonMetricDelta(
            baseline=baseline_value,
            candidate=candidate_value,
            delta=candidate_value - baseline_value,
        )

    baseline_cases = {item.case_id: set(item.errors) for item in baseline.case_results}
    candidate_cases = {item.case_id: set(item.errors) for item in candidate.case_results}
    worsened_cases: list[EvalComparisonCaseDelta] = []
    improved_cases: list[EvalComparisonCaseDelta] = []
    for case_id in sorted(set(baseline_cases) | set(candidate_cases)):
        baseline_errors = baseline_cases.get(case_id, set())
        candidate_errors = candidate_cases.get(case_id, set())
        new_errors = sorted(candidate_errors - baseline_errors)
        resolved_errors = sorted(baseline_errors - candidate_errors)
        if new_errors:
            worsened_cases.append(EvalComparisonCaseDelta(case_id=case_id, newly_failed_checks=new_errors))
        if resolved_errors:
            improved_cases.append(EvalComparisonCaseDelta(case_id=case_id, resolved_checks=resolved_errors))

    return EvalComparison(
        baseline_label=baseline.run_metadata.report_label,
        candidate_label=candidate.run_metadata.report_label,
        metric_deltas=metric_deltas,
        worsened_cases=worsened_cases,
        improved_cases=improved_cases,
    )


def _markdown_report(comparison: EvalComparison) -> str:
    lines = [
        "# Evaluation Comparison Report",
        "",
        f"- Baseline: {comparison.baseline_label}",
        f"- Candidate: {comparison.candidate_label}",
        "",
        "## Metric Deltas",
        "",
    ]
    for metric, delta in comparison.metric_deltas.items():
        lines.append(f"- `{metric}`: {delta.baseline} -> {delta.candidate} ({delta.delta:+})")
    lines.extend(["", "## Worsened Cases", ""])
    if comparison.worsened_cases:
        for case in comparison.worsened_cases:
            lines.append(f"- `{case.case_id}`: {', '.join(case.newly_failed_checks)}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Improved Cases", ""])
    if comparison.improved_cases:
        for case in comparison.improved_cases:
            lines.append(f"- `{case.case_id}`: {', '.join(case.resolved_checks)}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Thought And Distortion Focus",
            "",
            f"- `automatic_thought_hit_rate`: {comparison.metric_deltas['automatic_thought_hit_rate'].baseline} -> {comparison.metric_deltas['automatic_thought_hit_rate'].candidate} ({comparison.metric_deltas['automatic_thought_hit_rate'].delta:+})",
            f"- `automatic_thought_case_hit_rate`: {comparison.metric_deltas['automatic_thought_case_hit_rate'].baseline} -> {comparison.metric_deltas['automatic_thought_case_hit_rate'].candidate} ({comparison.metric_deltas['automatic_thought_case_hit_rate'].delta:+})",
            f"- `distortion_top3_hit_rate`: {comparison.metric_deltas['distortion_top3_hit_rate'].baseline} -> {comparison.metric_deltas['distortion_top3_hit_rate'].candidate} ({comparison.metric_deltas['distortion_top3_hit_rate'].delta:+})",
            f"- `distortion_case_top3_hit_rate`: {comparison.metric_deltas['distortion_case_top3_hit_rate'].baseline} -> {comparison.metric_deltas['distortion_case_top3_hit_rate'].candidate} ({comparison.metric_deltas['distortion_case_top3_hit_rate'].delta:+})",
            "",
            "## Clarification Focus",
            "",
            f"- `clarification_case_accuracy`: {comparison.metric_deltas['clarification_case_accuracy'].baseline} -> {comparison.metric_deltas['clarification_case_accuracy'].candidate} ({comparison.metric_deltas['clarification_case_accuracy'].delta:+})",
            f"- `missing_fields_overlap`: {comparison.metric_deltas['missing_fields_overlap'].baseline} -> {comparison.metric_deltas['missing_fields_overlap'].candidate} ({comparison.metric_deltas['missing_fields_overlap'].delta:+})",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two evaluation runs.")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output-dir", default="eval/reports/comparison")
    args = parser.parse_args()

    comparison = compare_runs(args.baseline, args.candidate)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "comparison.json", comparison.model_dump(mode="json"))
    write_markdown(output_dir / "comparison.md", _markdown_report(comparison))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from pathlib import Path

from eval.loader import load_eval_cases
from eval.synthetic.workflow import prepare_review_records, promote_reviewed_cases


def test_prepare_review_skips_failed_raw_records(tmp_path: Path) -> None:
    raw_path = tmp_path / "synthetic" / "raw" / "run.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_items = [
        {
            "record_id": "ok-1",
            "generation_run_id": "run-1",
            "request": {"request_id": "run-1-001", "primary_tag": "automatic_thought", "state": "worry_thought_capture", "language": "ko", "risk_severity": None},
            "generator_model": "fake",
            "generator_prompt_version": "v1",
            "request_payload": {},
            "raw_response": "{}",
            "succeeded": True,
            "parsed_case": {
                "case_id": "synthetic-1",
                "state": "worry_thought_capture",
                "language": "ko",
                "free_text": "불안해서 큰일 날 것 같아.",
                "tags": ["automatic_thought"],
                "gold": {
                    "situation": {"acceptable": []},
                    "automatic_thought": {"acceptable": ["큰일 날 것 같아"]},
                    "emotion": {"acceptable_labels": ["anxiety"]},
                    "behavior": {"acceptable": []},
                    "distortion_candidates": [],
                    "risk_expected_flags": [],
                    "risk_expected_level": "none",
                    "needs_clarification": False,
                    "missing_fields": [],
                    "notes": ""
                }
            }
        },
        {
            "record_id": "bad-1",
            "generation_run_id": "run-1",
            "request": {"request_id": "run-1-002", "primary_tag": "clarification", "state": "worry_thought_capture", "language": "ko", "risk_severity": None},
            "generator_model": "fake",
            "generator_prompt_version": "v1",
            "request_payload": {},
            "raw_response": "",
            "succeeded": False,
            "error_code": "invalid_json"
        }
    ]
    raw_path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in raw_items) + "\n", encoding="utf-8")

    result = prepare_review_records(raw_path=raw_path, output_root=tmp_path / "synthetic", run_name="run")
    review_path = Path(result["review_path"])
    lines = [line for line in review_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1


def test_promote_exports_only_approved_cases(tmp_path: Path) -> None:
    review_path = tmp_path / "synthetic" / "review" / "run.jsonl"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_items = [
        {
            "record_id": "rv-1",
            "generation_run_id": "run-1",
            "source_type": "synthetic",
            "generator_model": "fake",
            "generator_prompt_version": "v1",
            "review_status": "approved",
            "review_notes": "good",
            "adjudication_notes": "",
            "case": {
                "case_id": "synthetic-1",
                "state": "emotion_body_behavior_capture",
                "language": "ko",
                "free_text": "심장이 빨리 뛰고 숨고 싶다.",
                "tags": ["emotion_behavior"],
                "gold": {
                    "situation": {"acceptable": []},
                    "automatic_thought": {"acceptable": []},
                    "emotion": {"acceptable_labels": ["anxiety"]},
                    "behavior": {"acceptable": ["숨고 싶다"]},
                    "distortion_candidates": [],
                    "risk_expected_flags": [],
                    "risk_expected_level": "none",
                    "needs_clarification": False,
                    "missing_fields": [],
                    "notes": ""
                }
            }
        },
        {
            "record_id": "rv-2",
            "generation_run_id": "run-1",
            "source_type": "synthetic",
            "generator_model": "fake",
            "generator_prompt_version": "v1",
            "review_status": "rejected",
            "review_notes": "bad",
            "adjudication_notes": "",
            "case": {
                "case_id": "synthetic-2",
                "state": "emotion_body_behavior_capture",
                "language": "ko",
                "free_text": "버려져야 마땅해.",
                "tags": ["distortion"],
                "gold": {
                    "situation": {"acceptable": []},
                    "automatic_thought": {"acceptable": []},
                    "emotion": {"acceptable_labels": ["shame"]},
                    "behavior": {"acceptable": []},
                    "distortion_candidates": ["self_blame"],
                    "risk_expected_flags": [],
                    "risk_expected_level": "none",
                    "needs_clarification": False,
                    "missing_fields": [],
                    "notes": ""
                }
            }
        }
    ]
    review_path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in review_items) + "\n", encoding="utf-8")

    export_path = tmp_path / "datasets" / "approved.jsonl"
    result = promote_reviewed_cases(review_path=review_path, output_root=tmp_path / "synthetic", run_name="run", export_dataset_path=export_path)
    assert result["approved_count"] == 1
    exported = load_eval_cases(export_path)
    assert len(exported) == 1
    assert exported[0].tags == ["emotion_behavior"]

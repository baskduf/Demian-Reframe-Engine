from __future__ import annotations

import json
from pathlib import Path

from app.schemas.models import StateEnum
from eval.loader import load_eval_cases
from eval.models import EvalGold
from eval.synthetic.models import SyntheticCaseDraft, SyntheticRawRecord
from eval.synthetic.io import load_generation_config, load_manifest, load_raw_records, load_review_records
from eval.synthetic.workflow import build_generation_requests, generate_synthetic_raw, prepare_review_records, promote_reviewed_cases, validate_synthetic_case


class FakeSyntheticGenerator:
    def __init__(self) -> None:
        self.model_name = "fake-synthetic-model"

    def generate_case(self, *, generation_run_id: str, request):
        if request.primary_tag == "clarification":
            return SyntheticRawRecord(
                record_id=f"{request.request_id}-raw",
                generation_run_id=generation_run_id,
                request=request,
                generator_model=self.model_name,
                generator_prompt_version="synthetic-generator-test",
                request_payload=request.model_dump(mode="json"),
                raw_response="",
                succeeded=False,
                error_code="schema_validation_failed",
            )

        draft = SyntheticCaseDraft(
            case_id=f"synthetic-{request.request_id}",
            state=request.state,
            language="ko",
            free_text=f"{request.primary_tag} 케이스 예시",
            tags=[request.primary_tag],
            gold=EvalGold(
                automatic_thought={"acceptable": ["나는 잘 못할 거야"]} if request.primary_tag in {"automatic_thought", "distortion"} else {},
                emotion={"acceptable_labels": ["anxiety"]},
                behavior={"acceptable": ["회피하고 싶다"]},
                needs_clarification=request.primary_tag == "risk",
                missing_fields=["automatic_thought"] if request.primary_tag == "risk" else [],
            ),
            generation_run_id=generation_run_id,
            generator_model=self.model_name,
            generator_prompt_version="synthetic-generator-test",
            review_status="pending",
        )
        return SyntheticRawRecord(
            record_id=f"{request.request_id}-raw",
            generation_run_id=generation_run_id,
            request=request,
            generator_model=self.model_name,
            generator_prompt_version="synthetic-generator-test",
            request_payload=request.model_dump(mode="json"),
            raw_response=json.dumps(draft.model_dump(mode="json"), ensure_ascii=False),
            succeeded=True,
            parsed_case=draft,
        )


def _write_config(path: Path) -> Path:
    payload = {
        "dataset_name": "synthetic_test",
        "dataset_version": "2026-04-17-test",
        "language": "ko",
        "random_seed": 7,
        "total_cases": 4,
        "split": "dev",
        "case_mix": {
            "automatic_thought": 1,
            "distortion": 1,
            "clarification": 1,
            "risk": 1,
        },
        "risk_severity_mix": {"subtle": 1, "moderate": 1, "explicit": 1},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_synthetic_config_loader_reads_default_shape(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "config.json")
    config = load_generation_config(config_path)
    assert config.dataset_name == "synthetic_test"
    assert config.total_cases == 4
    assert config.case_mix["risk"] == 1


def test_build_generation_requests_uses_weighted_mix(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "config.json")
    requests, config_payload = build_generation_requests(config_path, total_cases=8)
    assert len(requests) == 8
    assert config_payload["dataset_name"] == "synthetic_test"
    assert any(item.primary_tag == "risk" and item.risk_severity is not None for item in requests)
    assert all(item.state in {StateEnum.WORRY_THOUGHT_CAPTURE, StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE} for item in requests)


def test_synthetic_pipeline_round_trip_exports_eval_compatible_dataset(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "config.json")
    output_root = tmp_path / "synthetic"
    generator = FakeSyntheticGenerator()

    generate_result = generate_synthetic_raw(
        config_path=config_path,
        output_root=output_root,
        run_name="demo-run",
        total_cases=4,
        generator=generator,
    )
    raw_records = load_raw_records(generate_result["raw_path"])
    assert len(raw_records) == 4
    assert any(not record.succeeded for record in raw_records)

    prepare_result = prepare_review_records(raw_path=generate_result["raw_path"], output_root=output_root, run_name="demo-run")
    review_records = load_review_records(prepare_result["review_path"])
    assert len(review_records) == 3

    updated_records = []
    for index, record in enumerate(review_records):
        record.review_status = "approved" if index == 0 else "needs_edit"
        record.review_notes = "checked"
        updated_records.append(record.model_dump(mode="json"))
    Path(prepare_result["review_path"]).write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in updated_records) + "\n", encoding="utf-8")

    export_path = tmp_path / "exported" / "synthetic_eval.jsonl"
    promote_result = promote_reviewed_cases(
        review_path=prepare_result["review_path"],
        output_root=output_root,
        run_name="demo-run",
        export_dataset_path=export_path,
    )
    assert promote_result["approved_count"] == 1
    eval_cases = load_eval_cases(export_path)
    assert len(eval_cases) == 1
    assert eval_cases[0].source_type == "synthetic"
    assert eval_cases[0].generator_model == "fake-synthetic-model"

    manifest = load_manifest(output_root / "manifests" / "demo-run.json")
    assert manifest.total_raw_records == 4
    assert manifest.total_review_records == 3
    assert manifest.total_approved_cases == 1
    assert prepare_result["invalid_issues"]


def test_synthetic_validation_rejects_duplicate_and_invalid_tags() -> None:
    case = SyntheticCaseDraft(
        case_id="dup-case",
        state=StateEnum.WORRY_THOUGHT_CAPTURE,
        language="ko",
        free_text="불안해서 큰일 날 것 같아.",
        tags=["automatic_thought", "bad_tag"],
        gold=EvalGold(
            automatic_thought={"acceptable": ["큰일 날 것 같아"]},
            emotion={"acceptable_labels": ["anxiety"]},
            behavior={"acceptable": []},
        ),
    )
    first = validate_synthetic_case(case, seen_case_ids=set())
    second = validate_synthetic_case(case, seen_case_ids={"dup-case"})
    assert first.status == "valid"
    assert "normalized_tags" in first.errors
    assert first.normalized_tags == ["automatic_thought"]
    assert second.status == "invalid"
    assert "duplicate_case_id" in second.errors


def test_synthetic_validation_rejects_garbled_text() -> None:
    case = SyntheticCaseDraft(
        case_id="garbled-case",
        state=StateEnum.WORRY_THOUGHT_CAPTURE,
        language="ko",
        free_text="??? ??? ???",
        tags=["automatic_thought"],
        gold=EvalGold(
            automatic_thought={"acceptable": ["잘못될 거야"]},
            emotion={"acceptable_labels": ["anxiety"]},
            behavior={"acceptable": []},
        ),
    )
    result = validate_synthetic_case(case, seen_case_ids=set())
    assert result.status == "invalid"
    assert "garbled_text" in result.errors

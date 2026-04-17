from __future__ import annotations

import json
import random
import re
from pathlib import Path
from uuid import uuid4

from app.schemas.models import StateEnum
from eval.loader import write_json
from eval.synthetic.adapter import SyntheticGenerator, weighted_choices
from eval.synthetic.io import load_generation_config, load_manifest, load_raw_records, load_review_records, write_jsonl, write_manifest
from eval.synthetic.models import (
    SyntheticApprovedCase,
    SyntheticCaseRequest,
    SyntheticPaths,
    SyntheticRawRecord,
    SyntheticReviewRecord,
    SyntheticRunManifest,
    SyntheticValidationIssue,
    SyntheticValidationResult,
)

ALLOWED_SYNTHETIC_TAGS = {
    "automatic_thought",
    "distortion",
    "clarification",
    "emotion_behavior",
    "risk",
}
GARBLED_TEXT_PATTERN = re.compile(r"[?�]{3,}")


STATE_BY_TAG = {
    "automatic_thought": StateEnum.WORRY_THOUGHT_CAPTURE,
    "distortion": StateEnum.WORRY_THOUGHT_CAPTURE,
    "clarification": StateEnum.WORRY_THOUGHT_CAPTURE,
    "emotion_behavior": StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE,
    "risk": StateEnum.WORRY_THOUGHT_CAPTURE,
}


def build_paths(root: str | Path, run_name: str) -> SyntheticPaths:
    root_path = Path(root)
    return SyntheticPaths(
        root=root_path,
        raw_path=root_path / "raw" / f"{run_name}.jsonl",
        review_path=root_path / "review" / f"{run_name}.jsonl",
        approved_path=root_path / "approved" / f"{run_name}.jsonl",
        manifest_path=root_path / "manifests" / f"{run_name}.json",
    )


def build_generation_requests(config_path: str | Path, *, total_cases: int | None = None) -> tuple[list[SyntheticCaseRequest], dict]:
    config = load_generation_config(config_path)
    requested_total = total_cases or config.total_cases
    rng = random.Random(config.random_seed)
    primary_tags = weighted_choices(config.case_mix, total=requested_total, rng=rng)
    risk_levels = weighted_choices(config.risk_severity_mix, total=max(1, sum(1 for tag in primary_tags if tag == "risk")), rng=rng)
    risk_index = 0
    requests: list[SyntheticCaseRequest] = []
    generation_run_id = str(uuid4())
    for index, tag in enumerate(primary_tags, start=1):
        requests.append(
            SyntheticCaseRequest(
                request_id=f"{generation_run_id}-{index:03d}",
                primary_tag=tag,
                state=STATE_BY_TAG[tag],
                language=config.language,
                risk_severity=risk_levels[risk_index] if tag == "risk" else None,
            )
        )
        if tag == "risk":
            risk_index += 1
    return requests, config.model_dump(mode="json")


def generate_synthetic_raw(
    *,
    config_path: str | Path,
    output_root: str | Path,
    run_name: str,
    total_cases: int | None = None,
    generator: SyntheticGenerator | None = None,
) -> dict:
    requests, config_payload = build_generation_requests(config_path, total_cases=total_cases)
    generation_run_id = requests[0].request_id.rsplit("-", 1)[0] if requests else str(uuid4())
    paths = build_paths(output_root, run_name)
    generator = generator or SyntheticGenerator()
    raw_records: list[SyntheticRawRecord] = [generator.generate_case(generation_run_id=generation_run_id, request=request) for request in requests]
    write_jsonl(paths.raw_path, [record.model_dump(mode="json") for record in raw_records])
    manifest = SyntheticRunManifest(
        generation_run_id=generation_run_id,
        dataset_name=config_payload["dataset_name"],
        dataset_version=config_payload["dataset_version"],
        split=config_payload["split"],
        config_path=str(config_path),
        raw_output_path=str(paths.raw_path),
        generator_model=generator.model_name,
        generator_prompt_version=raw_records[0].generator_prompt_version if raw_records else "",
        total_requested_cases=len(requests),
        total_raw_records=len(raw_records),
        config=config_payload,
    )
    write_manifest(paths.manifest_path, manifest)
    return {"raw_path": str(paths.raw_path), "manifest_path": str(paths.manifest_path), "generation_run_id": generation_run_id}


def prepare_review_records(*, raw_path: str | Path, output_root: str | Path, run_name: str) -> dict:
    raw_records = load_raw_records(raw_path)
    paths = build_paths(output_root, run_name)
    review_records: list[SyntheticReviewRecord] = []
    invalid_issues: list[SyntheticValidationIssue] = []
    seen_case_ids: set[str] = set()
    for raw_record in raw_records:
        if not raw_record.succeeded or raw_record.parsed_case is None:
            invalid_issues.append(SyntheticValidationIssue(record_id=raw_record.record_id, errors=[raw_record.error_code or "generation_failed"]))
            continue
        validation = validate_synthetic_case(raw_record.parsed_case, seen_case_ids=seen_case_ids)
        if validation.status == "invalid":
            invalid_issues.append(
                SyntheticValidationIssue(
                    record_id=raw_record.record_id,
                    case_id=raw_record.parsed_case.case_id,
                    errors=validation.errors,
                )
            )
            continue
        raw_record.parsed_case.tags = validation.normalized_tags
        seen_case_ids.add(raw_record.parsed_case.case_id)
        review_records.append(
            SyntheticReviewRecord(
                record_id=raw_record.record_id,
                generation_run_id=raw_record.generation_run_id,
                generator_model=raw_record.generator_model,
                generator_prompt_version=raw_record.generator_prompt_version,
                review_status="pending",
                review_notes="",
                adjudication_notes="",
                case=raw_record.parsed_case,
            )
        )
    write_jsonl(paths.review_path, [record.model_dump(mode="json") for record in review_records])
    if paths.manifest_path.exists():
        manifest = load_manifest(paths.manifest_path)
        manifest.review_output_path = str(paths.review_path)
        manifest.total_review_records = len(review_records)
        manifest.invalid_count = len(invalid_issues)
        write_manifest(paths.manifest_path, manifest)
    return {"review_path": str(paths.review_path), "review_count": len(review_records), "invalid_issues": [issue.model_dump(mode="json") for issue in invalid_issues]}


def promote_reviewed_cases(
    *,
    review_path: str | Path,
    output_root: str | Path,
    run_name: str,
    export_dataset_path: str | Path | None = None,
) -> dict:
    review_records = load_review_records(review_path)
    paths = build_paths(output_root, run_name)
    approved_cases: list[SyntheticApprovedCase] = []
    seen_case_ids: set[str] = set()
    invalid_issues: list[SyntheticValidationIssue] = []
    approved_count = 0
    needs_edit_count = 0
    rejected_count = 0
    for record in review_records:
        if record.review_status == "approved":
            approved_count += 1
            validation = validate_synthetic_case(record.case, seen_case_ids=seen_case_ids)
            if validation.status == "invalid":
                invalid_issues.append(SyntheticValidationIssue(record_id=record.record_id, case_id=record.case.case_id, errors=validation.errors))
                continue
            record.case.tags = validation.normalized_tags
            seen_case_ids.add(record.case.case_id)
            approved_cases.append(
                SyntheticApprovedCase.model_validate(
                    {
                        **record.case.model_dump(mode="json"),
                        "source_type": "synthetic",
                        "generation_run_id": record.generation_run_id,
                        "generator_model": record.generator_model,
                        "generator_prompt_version": record.generator_prompt_version,
                        "review_status": record.review_status,
                        "review_notes": record.review_notes,
                    }
                )
            )
        elif record.review_status == "needs_edit":
            needs_edit_count += 1
        elif record.review_status == "rejected":
            rejected_count += 1
    write_jsonl(paths.approved_path, [case.model_dump(mode="json") for case in approved_cases])
    if paths.manifest_path.exists():
        manifest = load_manifest(paths.manifest_path)
        manifest.approved_output_path = str(paths.approved_path)
        manifest.total_approved_cases = len(approved_cases)
        manifest.approved_count = approved_count
        manifest.needs_edit_count = needs_edit_count
        manifest.rejected_count = rejected_count
        manifest.invalid_count = len(invalid_issues)
        manifest.tag_mix_normalized = _case_mix(approved_cases)
        write_manifest(paths.manifest_path, manifest)
    if export_dataset_path:
        write_jsonl(export_dataset_path, [case.model_dump(mode="json") for case in approved_cases])
        export_manifest = {
            "dataset_name": Path(export_dataset_path).stem,
            "dataset_version": "synthetic-approved-v1",
            "case_count": len(approved_cases),
            "language": "ko",
            "notes": "Approved synthetic evaluation cases",
            "case_mix": _case_mix(approved_cases),
            "approved_case_count": approved_count,
            "needs_edit_count": needs_edit_count,
            "rejected_count": rejected_count,
            "invalid_count": len(invalid_issues),
            "provisional_approval_used": False,
        }
        write_json(Path(export_dataset_path).with_suffix(".manifest.json"), export_manifest)
    return {
        "approved_path": str(paths.approved_path),
        "approved_count": len(approved_cases),
        "invalid_issues": [issue.model_dump(mode="json") for issue in invalid_issues],
    }


def _case_mix(cases: list[SyntheticApprovedCase]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        for tag in case.tags:
            counts[tag] = counts.get(tag, 0) + 1
    return counts


def validate_synthetic_case(case: SyntheticApprovedCase | SyntheticReviewRecord | object, *, seen_case_ids: set[str]) -> SyntheticValidationResult:
    case_obj = case.case if hasattr(case, "case") else case
    errors: list[str] = []
    case_id = getattr(case_obj, "case_id", "")
    tags = list(getattr(case_obj, "tags", []))
    free_text = getattr(case_obj, "free_text", "")
    gold = getattr(case_obj, "gold", None)

    normalized_tags = [tag for tag in tags if tag in ALLOWED_SYNTHETIC_TAGS]
    if not normalized_tags:
        errors.append("invalid_tags")
    if len(normalized_tags) != len(tags):
        errors.append("normalized_tags")
    if not case_id:
        errors.append("missing_case_id")
    elif case_id in seen_case_ids:
        errors.append("duplicate_case_id")
    if not str(free_text).strip():
        errors.append("empty_free_text")
    if GARBLED_TEXT_PATTERN.search(str(free_text)):
        errors.append("garbled_text")
    if gold is None:
        errors.append("missing_gold")
    else:
        if getattr(gold, "risk_expected_level", "none") == "none" and getattr(gold, "risk_expected_flags", []):
            errors.append("risk_level_flag_mismatch")
        if getattr(gold, "risk_expected_level", "none") != "none" and not getattr(gold, "risk_expected_flags", []):
            errors.append("risk_level_flag_mismatch")
        if GARBLED_TEXT_PATTERN.search(str(getattr(gold, "notes", ""))):
            errors.append("garbled_gold_notes")

    status = "invalid" if any(error not in {"normalized_tags"} for error in errors) else "valid"
    return SyntheticValidationResult(status=status, normalized_tags=normalized_tags, errors=errors)

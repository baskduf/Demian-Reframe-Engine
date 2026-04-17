from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.models import StateEnum
from eval.models import EvalCase, EvalGold

SyntheticReviewStatus = Literal["pending", "approved", "needs_edit", "rejected"]
SyntheticRiskSeverity = Literal["subtle", "moderate", "explicit"]
SyntheticValidationStatus = Literal["valid", "invalid"]


class SyntheticGenerationConfig(BaseModel):
    dataset_name: str
    dataset_version: str
    language: str = "ko"
    random_seed: int = 17
    total_cases: int = 20
    split: Literal["dev", "regression", "holdout"] = "dev"
    case_mix: dict[str, int] = Field(default_factory=dict)
    risk_severity_mix: dict[SyntheticRiskSeverity, int] = Field(
        default_factory=lambda: {"subtle": 1, "moderate": 1, "explicit": 1}
    )
    notes: str = ""

    @model_validator(mode="after")
    def validate_mix(self) -> "SyntheticGenerationConfig":
        if self.total_cases <= 0:
            raise ValueError("total_cases must be positive")
        if not self.case_mix:
            raise ValueError("case_mix must not be empty")
        if any(value <= 0 for value in self.case_mix.values()):
            raise ValueError("case_mix values must be positive")
        if not self.risk_severity_mix or any(value <= 0 for value in self.risk_severity_mix.values()):
            raise ValueError("risk_severity_mix values must be positive")
        return self


class SyntheticCaseRequest(BaseModel):
    request_id: str
    primary_tag: str
    state: StateEnum
    language: str = "ko"
    risk_severity: SyntheticRiskSeverity | None = None


class SyntheticCaseDraft(BaseModel):
    case_id: str
    state: StateEnum
    language: str = "ko"
    free_text: str
    tags: list[str] = Field(default_factory=list)
    gold: EvalGold
    source_type: str = "synthetic"
    generation_run_id: str = ""
    generator_model: str = ""
    generator_prompt_version: str = ""
    review_status: SyntheticReviewStatus = "pending"
    review_notes: str = ""


class SyntheticRawRecord(BaseModel):
    record_id: str
    generation_run_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    request: SyntheticCaseRequest
    generator_model: str
    generator_prompt_version: str
    request_payload: dict = Field(default_factory=dict)
    raw_response: str = ""
    succeeded: bool = False
    error_code: str | None = None
    parsed_case: SyntheticCaseDraft | None = None


class SyntheticReviewRecord(BaseModel):
    record_id: str
    generation_run_id: str
    source_type: str = "synthetic"
    generator_model: str
    generator_prompt_version: str
    review_status: SyntheticReviewStatus = "pending"
    review_notes: str = ""
    adjudication_notes: str = ""
    case: SyntheticCaseDraft


class SyntheticApprovedCase(EvalCase):
    source_type: str = "synthetic"
    generation_run_id: str
    generator_model: str
    generator_prompt_version: str
    review_status: str = "approved"
    review_notes: str = ""


class SyntheticRunManifest(BaseModel):
    generation_run_id: str
    dataset_name: str
    dataset_version: str
    split: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    config_path: str = ""
    raw_output_path: str = ""
    review_output_path: str = ""
    approved_output_path: str = ""
    generator_model: str = ""
    generator_prompt_version: str = ""
    total_requested_cases: int = 0
    total_raw_records: int = 0
    total_review_records: int = 0
    total_approved_cases: int = 0
    approved_count: int = 0
    needs_edit_count: int = 0
    rejected_count: int = 0
    invalid_count: int = 0
    provisional_approval_used: bool = False
    tag_mix_normalized: dict[str, int] = Field(default_factory=dict)
    config: dict = Field(default_factory=dict)


class SyntheticPaths(BaseModel):
    root: Path
    raw_path: Path
    review_path: Path
    approved_path: Path
    manifest_path: Path


class SyntheticValidationIssue(BaseModel):
    record_id: str
    case_id: str = ""
    errors: list[str] = Field(default_factory=list)


class SyntheticValidationResult(BaseModel):
    status: SyntheticValidationStatus = "valid"
    normalized_tags: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

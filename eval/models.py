from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from app.schemas.models import StateEnum


class AcceptableTextSet(BaseModel):
    acceptable: list[str] = Field(default_factory=list)


class AcceptableEmotionSet(BaseModel):
    acceptable_labels: list[str] = Field(default_factory=list)


class EvalGold(BaseModel):
    situation: AcceptableTextSet = Field(default_factory=AcceptableTextSet)
    automatic_thought: AcceptableTextSet = Field(default_factory=AcceptableTextSet)
    emotion: AcceptableEmotionSet = Field(default_factory=AcceptableEmotionSet)
    behavior: AcceptableTextSet = Field(default_factory=AcceptableTextSet)
    distortion_candidates: list[str] = Field(default_factory=list)
    risk_expected_flags: list[str] = Field(default_factory=list)
    risk_expected_level: str = "none"
    needs_clarification: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    notes: str = ""


class EvalCase(BaseModel):
    case_id: str
    state: StateEnum
    language: str = "ko"
    free_text: str
    gold: EvalGold


class EvalPrediction(BaseModel):
    case_id: str
    situation: list[str] = Field(default_factory=list)
    automatic_thought: list[str] = Field(default_factory=list)
    emotion_labels: list[str] = Field(default_factory=list)
    behavior: list[str] = Field(default_factory=list)
    distortion_candidates: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    schema_valid: bool = True
    fallback_used: bool = False
    banned_content: bool = False
    latency_ms: float = 0.0
    source: str = "static"


class EvalMetrics(BaseModel):
    total_cases: int = 0
    situation_hit_rate: float = 0.0
    automatic_thought_hit_rate: float = 0.0
    emotion_label_hit_rate: float = 0.0
    behavior_hit_rate: float = 0.0
    needs_clarification_accuracy: float = 0.0
    missing_fields_overlap: float = 0.0
    distortion_top1_hit_rate: float = 0.0
    distortion_top3_hit_rate: float = 0.0
    risk_flag_recall: float = 0.0
    risk_false_negative_count: int = 0
    schema_valid_rate: float = 0.0
    fallback_rate: float = 0.0
    banned_content_rate: float = 0.0
    avg_latency_ms: float = 0.0


class EvalCaseResult(BaseModel):
    case_id: str
    situation_hit: bool
    automatic_thought_hit: bool
    emotion_label_hit: bool
    behavior_hit: bool
    needs_clarification_hit: bool
    missing_fields_overlap: float
    distortion_top1_hit: bool
    distortion_top3_hit: bool
    risk_flag_hit: bool
    risk_false_negative: bool
    schema_valid: bool
    fallback_used: bool
    banned_content: bool
    latency_ms: float
    errors: list[str] = Field(default_factory=list)


class EvalRunConfig(BaseModel):
    dataset_path: Path
    predictions_path: Path | None = None
    output_dir: Path = Path("eval/reports")
    mode: str = "static"
    include_live_risk_assist: bool = True
    allow_live_eval: bool = False

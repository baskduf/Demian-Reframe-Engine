from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BaselineStatus = Literal[
    "official",
    "reference",
    "experimental",
    "experimental_provisional",
    "experimental_reviewed",
    "deprecated",
]


class BaselineRecord(BaseModel):
    baseline_id: str
    status: BaselineStatus
    run_path: str
    dataset_path: str
    dataset_version: str
    model_name: str
    prompt_version: str
    risk_prompt_version: str
    run_timestamp: str
    notes: str = ""


class BaselineRegistry(BaseModel):
    records: list[BaselineRecord] = Field(default_factory=list)

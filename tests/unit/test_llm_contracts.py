from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.llm.contracts import CandidateText, LLMStructuredOutput


def test_llm_structured_output_accepts_expected_shape() -> None:
    output = LLMStructuredOutput(
        situation_candidates=[CandidateText(text="회의 전", confidence=0.8, evidence_span="회의 전")],
        needs_clarification=False,
        confidence={"overall": 0.8},
    )
    assert output.situation_candidates[0].text == "회의 전"


def test_llm_candidate_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        CandidateText(text="회의 전", confidence=1.5, evidence_span="")

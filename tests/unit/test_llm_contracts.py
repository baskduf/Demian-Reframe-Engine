from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.llm.contracts import CandidateDistortion, CandidateText, LLMStructuredOutput


def test_llm_structured_output_accepts_expected_shape() -> None:
    output = LLMStructuredOutput(
        situation_candidates=[CandidateText(text="회의 전", confidence=0.8, evidence_span="회의 전")],
        automatic_thought_candidates=[CandidateText(text="나는 망할 거야", confidence=0.7, evidence_span="망할 거야")],
        worry_prediction_candidates=[CandidateText(text="분명 잘못될 거야", confidence=0.75, evidence_span="잘못될 거야")],
        distortion_candidates=[CandidateDistortion(label="fortune_telling", confidence=0.6, rationale_code="future")],
        needs_clarification=False,
        confidence={"overall": 0.8},
    )
    assert output.situation_candidates[0].text == "회의 전"
    assert output.worry_prediction_candidates[0].text == "분명 잘못될 거야"


def test_llm_candidate_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        CandidateText(text="회의 전", confidence=1.5, evidence_span="")

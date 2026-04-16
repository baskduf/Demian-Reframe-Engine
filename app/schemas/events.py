from __future__ import annotations

from enum import StrEnum
from typing import Type

from pydantic import BaseModel, ConfigDict

from app.schemas.models import EmotionScore, StateEnum


class EventTypeEnum(StrEnum):
    ELIGIBILITY = "eligibility"
    SITUATION = "situation"
    WORRY = "worry"
    EMOTION = "emotion"
    DISTORTION = "distortion"
    EVIDENCE_FOR = "evidence_for"
    EVIDENCE_AGAINST = "evidence_against"
    ALTERNATIVE = "alternative"
    RERATE = "rerate"
    EXPERIMENT = "experiment"
    SUMMARY = "summary"


class BaseEventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EligibilityPayload(BaseEventPayload):
    is_adult: bool | None = None
    target_condition: str | None = None


class SituationPayload(BaseEventPayload):
    situation_text: str | None = None
    trigger_text: str | None = None
    free_text: str | None = None


class WorryPayload(BaseEventPayload):
    automatic_thought: str | None = None
    worry_prediction: str | None = None
    free_text: str | None = None


class EmotionBehaviorPayload(BaseEventPayload):
    emotions: list[EmotionScore] | None = None
    body_symptoms: list[str] | None = None
    safety_behaviors: list[str] | None = None
    free_text: str | None = None


class DistortionSelectionPayload(BaseEventPayload):
    selected_distortion_ids: list[str] | None = None


class EvidenceForPayload(BaseEventPayload):
    evidence_for: list[str] | None = None


class EvidenceAgainstPayload(BaseEventPayload):
    evidence_against: list[str] | None = None


class AlternativeThoughtPayload(BaseEventPayload):
    balanced_view: str | None = None
    coping_statement: str | None = None


class ReRatePayload(BaseEventPayload):
    re_rated_anxiety: int | None = None
    experiment_required: bool | None = None


class BehaviorExperimentPayload(BaseEventPayload):
    action: str | None = None
    timebox: str | None = None
    hypothesis: str | None = None


class SummaryPayload(BaseEventPayload):
    summary_ack: bool | None = None


PAYLOAD_MODEL_BY_EVENT: dict[EventTypeEnum, Type[BaseEventPayload]] = {
    EventTypeEnum.ELIGIBILITY: EligibilityPayload,
    EventTypeEnum.SITUATION: SituationPayload,
    EventTypeEnum.WORRY: WorryPayload,
    EventTypeEnum.EMOTION: EmotionBehaviorPayload,
    EventTypeEnum.DISTORTION: DistortionSelectionPayload,
    EventTypeEnum.EVIDENCE_FOR: EvidenceForPayload,
    EventTypeEnum.EVIDENCE_AGAINST: EvidenceAgainstPayload,
    EventTypeEnum.ALTERNATIVE: AlternativeThoughtPayload,
    EventTypeEnum.RERATE: ReRatePayload,
    EventTypeEnum.EXPERIMENT: BehaviorExperimentPayload,
    EventTypeEnum.SUMMARY: SummaryPayload,
}


EVENT_TYPE_BY_STATE: dict[StateEnum, EventTypeEnum] = {
    StateEnum.ELIGIBILITY_CHECK: EventTypeEnum.ELIGIBILITY,
    StateEnum.SITUATION_CAPTURE: EventTypeEnum.SITUATION,
    StateEnum.WORRY_THOUGHT_CAPTURE: EventTypeEnum.WORRY,
    StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE: EventTypeEnum.EMOTION,
    StateEnum.DISTORTION_HYPOTHESIS: EventTypeEnum.DISTORTION,
    StateEnum.EVIDENCE_FOR: EventTypeEnum.EVIDENCE_FOR,
    StateEnum.EVIDENCE_AGAINST: EventTypeEnum.EVIDENCE_AGAINST,
    StateEnum.ALTERNATIVE_THOUGHT: EventTypeEnum.ALTERNATIVE,
    StateEnum.RE_RATE_ANXIETY: EventTypeEnum.RERATE,
    StateEnum.BEHAVIOR_EXPERIMENT: EventTypeEnum.EXPERIMENT,
    StateEnum.SUMMARY_PLAN: EventTypeEnum.SUMMARY,
}


def expected_event_type_for_state(state: StateEnum) -> EventTypeEnum | None:
    return EVENT_TYPE_BY_STATE.get(state)

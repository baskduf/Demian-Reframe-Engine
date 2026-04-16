from __future__ import annotations

from app.schemas.models import StateEnum


FLOW = [
    StateEnum.RISK_SCREEN,
    StateEnum.ELIGIBILITY_CHECK,
    StateEnum.SITUATION_CAPTURE,
    StateEnum.WORRY_THOUGHT_CAPTURE,
    StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE,
    StateEnum.DISTORTION_HYPOTHESIS,
    StateEnum.EVIDENCE_FOR,
    StateEnum.EVIDENCE_AGAINST,
    StateEnum.ALTERNATIVE_THOUGHT,
    StateEnum.RE_RATE_ANXIETY,
    StateEnum.BEHAVIOR_EXPERIMENT,
    StateEnum.SUMMARY_PLAN,
    StateEnum.CLOSE_SESSION,
]


REQUIRED_FIELDS: dict[StateEnum, tuple[str, ...]] = {
    StateEnum.ELIGIBILITY_CHECK: ("is_adult", "target_condition"),
    StateEnum.SITUATION_CAPTURE: ("situation_text", "trigger_text"),
    StateEnum.WORRY_THOUGHT_CAPTURE: ("automatic_thought", "worry_prediction"),
    StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE: ("emotions",),
    StateEnum.EVIDENCE_FOR: ("evidence_for",),
    StateEnum.EVIDENCE_AGAINST: ("evidence_against",),
    StateEnum.ALTERNATIVE_THOUGHT: ("balanced_view", "coping_statement"),
    StateEnum.RE_RATE_ANXIETY: ("re_rated_anxiety", "experiment_required"),
    StateEnum.BEHAVIOR_EXPERIMENT: ("action", "timebox"),
    StateEnum.SUMMARY_PLAN: ("summary_ack",),
}


def next_state(current: StateEnum) -> StateEnum:
    idx = FLOW.index(current)
    return FLOW[min(idx + 1, len(FLOW) - 1)]


def allowed_actions(state: StateEnum) -> list[str]:
    return {
        StateEnum.RISK_SCREEN: ["submit_risk_screen"],
        StateEnum.ELIGIBILITY_CHECK: ["submit_event"],
        StateEnum.SITUATION_CAPTURE: ["submit_event"],
        StateEnum.WORRY_THOUGHT_CAPTURE: ["submit_event"],
        StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE: ["submit_event"],
        StateEnum.DISTORTION_HYPOTHESIS: ["submit_event"],
        StateEnum.EVIDENCE_FOR: ["submit_event"],
        StateEnum.EVIDENCE_AGAINST: ["submit_event"],
        StateEnum.ALTERNATIVE_THOUGHT: ["submit_event"],
        StateEnum.RE_RATE_ANXIETY: ["submit_event"],
        StateEnum.BEHAVIOR_EXPERIMENT: ["submit_event"],
        StateEnum.SUMMARY_PLAN: ["submit_event"],
        StateEnum.CRISIS: [],
        StateEnum.OUT_OF_SCOPE: [],
        StateEnum.CLOSE_SESSION: [],
    }[state]


def has_required_fields(state: StateEnum, payload: dict) -> bool:
    for field in REQUIRED_FIELDS.get(state, tuple()):
        if field not in payload or payload[field] in ("", None, [], {}):
            return False
    if state == StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE:
        return bool(payload.get("emotions")) and bool(payload.get("body_symptoms") or payload.get("safety_behaviors"))
    return True

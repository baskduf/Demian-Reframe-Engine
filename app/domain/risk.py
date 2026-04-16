from __future__ import annotations

from app.schemas.models import RiskAssessment, RiskLevel, RiskScreenRequest


HIGH_RISK_PATTERNS = {
    "suicidal_intent_text": ["죽고 싶", "자살", "목숨을 끊", "해치고 싶", "끝내고 싶"],
    "suicidal_plan_text": ["유서", "수단을 준비", "약을 모았", "언제 죽을지", "계획해"],
    "psychotic_expression_text": ["명령하는 목소리", "누가 날 감시", "누가 나를 감시하고 있고 그게 확실", "현실이 아닌데도 확실", "머릿속에서 시킨다"],
    "acute_deterioration_text": ["통제가 안 된다", "완전히 무너졌", "너무 불안해서 아무것도 못", "밤새 한숨도 못 잤"],
}

MODERATE_RISK_PATTERNS = {
    "passive_death_wish": ["사라지고 싶", "없어지고 싶", "그만하고 싶"],
    "hopelessness": ["희망이 없", "버틸 수 없", "끝이 없을 것 같"],
    "functional_decline": ["일을 못 하겠", "아무것도 못 하겠", "잠을 거의 못 잤"],
}


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def evaluate_risk(session_id, request: RiskScreenRequest) -> RiskAssessment:
    text = request.free_text.strip().lower()
    triggered: list[str] = []
    suicidality_flag = False
    psychosis_flag = False
    acute_flag = False
    risk_level = RiskLevel.NONE
    disposition = "continue_structured_flow"

    if request.suicidal_intent or request.suicidal_plan or request.means_access:
        triggered.append("suicidal_checklist")
        suicidality_flag = True
    if request.command_hallucination or request.psychotic_language:
        triggered.append("psychosis_checklist")
        psychosis_flag = True
    if request.acute_deterioration:
        triggered.append("acute_deterioration_checklist")
        acute_flag = True

    for rule_id, phrases in HIGH_RISK_PATTERNS.items():
        if _contains_any(text, phrases):
            triggered.append(rule_id)

    if any("suicidal" in item for item in triggered):
        suicidality_flag = True
    if any("psych" in item for item in triggered):
        psychosis_flag = True
    if any("acute" in item for item in triggered):
        acute_flag = True

    if suicidality_flag or psychosis_flag or acute_flag:
        risk_level = RiskLevel.HIGH
        disposition = "interrupt_and_escalate"
    else:
        for rule_id, phrases in MODERATE_RISK_PATTERNS.items():
            if _contains_any(text, phrases):
                triggered.append(rule_id)
        if triggered:
            risk_level = RiskLevel.MODERATE
            disposition = "continue_with_caution"

    return RiskAssessment(
        session_id=session_id,
        risk_level=risk_level,
        suicidality_flag=suicidality_flag,
        psychosis_flag=psychosis_flag,
        acute_deterioration_flag=acute_flag,
        triggered_rule_ids=triggered,
        disposition=disposition,
    )

from __future__ import annotations

from app.schemas.models import StateEnum, TemplateResponse


TEMPLATES: dict[str, str] = {
    "risk.high": "높은 위험 신호가 감지되었습니다. 일반 CBT 세션을 중단하고 즉시 지역 응급 자원 또는 신뢰할 수 있는 지원자에게 도움을 요청하세요.",
    "risk.moderate": "주의가 필요한 표현이 감지되었습니다. 현재 안전 상태를 확인하면서 구조화된 흐름을 이어갑니다. 성인 여부와 목표 상태가 GAD인지 확인해주세요.",
    "eligibility.out_of_scope": "이 세션은 성인 GAD 구조화 기록용으로만 설계되어 있습니다. 범위를 벗어나므로 일반 흐름을 종료합니다.",
    "prompt.eligibility": "성인 여부와 목표 상태가 GAD인지 확인해주세요.",
    "prompt.situation": "최근 걱정이 커졌던 상황과 촉발 요인을 간단히 적어주세요.",
    "prompt.worry": "그 순간 스친 자동적 사고와 최악의 예측을 각각 적어주세요.",
    "prompt.emotion": "그때 느낀 감정 강도와 몸의 반응 또는 안전행동을 적어주세요.",
    "prompt.distortion": "규칙 기반 후보 왜곡을 확인하고 가장 가까운 것을 선택하세요.",
    "prompt.evidence_for": "그 걱정을 지지하는 근거를 한 가지 이상 적어주세요.",
    "prompt.evidence_against": "그 걱정과 다른 방향의 사실이나 예외를 한 가지 이상 적어주세요.",
    "prompt.alternative": "균형 잡힌 관점과 실행 가능한 대응 문장을 적어주세요.",
    "prompt.re_rate": "걱정을 다시 0~100으로 평가하고 행동실험이 필요한지 선택하세요.",
    "prompt.experiment": "짧은 행동실험 또는 걱정 검증 계획과 시간 범위를 적어주세요.",
    "summary.complete": "구조화된 걱정 기록이 완료되었습니다. 요약을 검토하고 마무리합니다.",
}


PROMPT_BY_STATE = {
    StateEnum.RISK_SCREEN: "prompt.situation",
    StateEnum.ELIGIBILITY_CHECK: "prompt.eligibility",
    StateEnum.SITUATION_CAPTURE: "prompt.situation",
    StateEnum.WORRY_THOUGHT_CAPTURE: "prompt.worry",
    StateEnum.EMOTION_BODY_BEHAVIOR_CAPTURE: "prompt.emotion",
    StateEnum.DISTORTION_HYPOTHESIS: "prompt.distortion",
    StateEnum.EVIDENCE_FOR: "prompt.evidence_for",
    StateEnum.EVIDENCE_AGAINST: "prompt.evidence_against",
    StateEnum.ALTERNATIVE_THOUGHT: "prompt.alternative",
    StateEnum.RE_RATE_ANXIETY: "prompt.re_rate",
    StateEnum.BEHAVIOR_EXPERIMENT: "prompt.experiment",
    StateEnum.SUMMARY_PLAN: "summary.complete",
    StateEnum.CRISIS: "risk.high",
    StateEnum.OUT_OF_SCOPE: "eligibility.out_of_scope",
    StateEnum.CLOSE_SESSION: "summary.complete",
}


def render_template(template_id: str) -> TemplateResponse:
    return TemplateResponse(template_id=template_id, message=TEMPLATES[template_id])

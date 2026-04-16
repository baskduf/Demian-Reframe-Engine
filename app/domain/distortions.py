from __future__ import annotations

from app.schemas.models import DistortionCandidate, RuleMatch


DISTORTION_RULES: list[tuple[str, str, list[tuple[str, tuple[str, ...]]]]] = [
    ("catastrophizing", "Catastrophizing", [("contains_disaster_terms", ("망했다", "망하면", "끔찍", "재앙", "최악", "끝장"))]),
    ("fortune_telling", "Fortune telling", [("future_certainty", ("분명", "틀림없이", "반드시", "분명히 실패", "잘못될 거"))]),
    ("intolerance_of_uncertainty", "Intolerance of uncertainty", [("uncertainty_intolerance", ("모르면 못 견디", "확실하지 않으면", "불확실해서 못 버티"))]),
    ("probability_overestimation", "Probability overestimation", [("threat_probability", ("아마도 큰일", "분명 위험", "나쁜 일이 생길 가능성이 크다"))]),
    ("should_statements", "Should statements", [("rigid_should_language", ("해야 한다", "반드시 해야", "이러면 안 된다", "꼭 그래야"))]),
    ("mind_reading", "Mind reading", [("assumed_other_judgment", ("저 사람은 날", "다들 내가", "분명 날 이상하게"))]),
    ("overgeneralization", "Overgeneralization", [("global_generalization", ("항상", "매번", "결국 늘", "다 망한다"))]),
    ("self_blame", "Self blame", [("global_self_fault", ("전부 내 탓", "내가 문제", "내 잘못 때문에"))]),
]


def detect_distortions(automatic_thought: str, worry_prediction: str) -> list[DistortionCandidate]:
    combined = f"{automatic_thought} {worry_prediction}".lower()
    matches: list[DistortionCandidate] = []

    for distortion_id, label, rules in DISTORTION_RULES:
        rule_matches: list[RuleMatch] = []
        for rule_id, phrases in rules:
            if any(phrase in combined for phrase in phrases):
                rule_matches.append(RuleMatch(rule_id=rule_id, label=rule_id.replace("_", " ")))
        if rule_matches:
            matches.append(
                DistortionCandidate(
                    distortion_id=distortion_id,
                    label=label,
                    rule_matches=rule_matches,
                )
            )

    if not matches:
        return [
            DistortionCandidate(
                distortion_id="uncertainty_focus",
                label="Uncertainty-focused worry",
                is_primary=True,
                rule_matches=[RuleMatch(rule_id="default_uncertainty_rule", label="default uncertainty rule")],
            )
        ]

    matches[0].is_primary = True
    return matches[:3]

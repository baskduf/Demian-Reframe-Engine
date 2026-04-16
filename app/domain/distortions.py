from __future__ import annotations

from app.schemas.models import DistortionCandidate, RuleMatch


THOUGHT_RULES: list[tuple[str, str, list[tuple[str, tuple[str, ...]]]]] = [
    ("mind_reading", "Mind reading", [("assumed_other_judgment", ("다들", "사람들이", "내가 이상하다고", "무능하다고 생각"))]),
    ("should_statements", "Should statements", [("rigid_should_language", ("반드시", "해야 한다", "이러면 안 돼", "그래야 한다"))]),
    ("self_blame", "Self blame", [("global_self_fault", ("전부 내 탓", "내가 문제", "내 잘못", "내 탓"))]),
    ("overgeneralization", "Overgeneralization", [("global_generalization", ("항상", "매번", "결국 다", "늘"))]),
    ("catastrophizing", "Catastrophizing", [("contains_disaster_terms", ("망하면", "최악", "큰일", "파국"))]),
    (
        "intolerance_of_uncertainty",
        "Intolerance of uncertainty",
        [("uncertainty_intolerance", ("확실하지 않으면", "모르면 못 견디", "불확실하면 못 버티"))],
    ),
]

PREDICTION_RULES: list[tuple[str, str, list[tuple[str, tuple[str, ...]]]]] = [
    ("fortune_telling", "Fortune telling", [("future_certainty", ("분명", "틀림없이", "결국", "잘못될 거", "망칠 거"))]),
    ("catastrophizing", "Catastrophizing", [("contains_disaster_terms", ("최악", "망했다", "망하면", "실패하면", "큰일", "끔찍", "파국"))]),
    (
        "intolerance_of_uncertainty",
        "Intolerance of uncertainty",
        [("uncertainty_intolerance", ("확실하지 않으면", "모르면 못 견디", "불확실하면 못 버티"))],
    ),
    (
        "probability_overestimation",
        "Probability overestimation",
        [("threat_probability", ("높을 것 같", "위험할 것 같", "가능성이 높", "분명 위험"))],
    ),
]


def _collect_rule_matches(source: str, rules: list[tuple[str, str, list[tuple[str, tuple[str, ...]]]]]) -> list[DistortionCandidate]:
    lowered = source.lower()
    matches: list[DistortionCandidate] = []
    for distortion_id, label, rule_defs in rules:
        rule_matches: list[RuleMatch] = []
        for rule_id, phrases in rule_defs:
            if any(phrase in lowered for phrase in phrases):
                rule_matches.append(RuleMatch(rule_id=rule_id, label=rule_id.replace("_", " ")))
        if rule_matches:
            matches.append(
                DistortionCandidate(
                    distortion_id=distortion_id,
                    label=label,
                    rule_matches=rule_matches,
                )
            )
    return matches


def detect_distortions(automatic_thought: str, worry_prediction: str) -> list[DistortionCandidate]:
    thought_matches = _collect_rule_matches(automatic_thought, THOUGHT_RULES)
    prediction_matches = _collect_rule_matches(worry_prediction, PREDICTION_RULES)

    merged: list[DistortionCandidate] = []
    seen: set[str] = set()
    for candidate in thought_matches + prediction_matches:
        if candidate.distortion_id in seen:
            continue
        seen.add(candidate.distortion_id)
        merged.append(candidate)

    if not merged:
        return [
            DistortionCandidate(
                distortion_id="uncertainty_focus",
                label="Uncertainty-focused worry",
                is_primary=True,
                rule_matches=[RuleMatch(rule_id="default_uncertainty_rule", label="default uncertainty rule")],
            )
        ]

    merged[0].is_primary = True
    return merged[:3]

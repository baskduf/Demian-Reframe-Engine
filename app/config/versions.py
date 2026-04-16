from __future__ import annotations

from typing import Any


ENGINE_VERSION = "0.1.0"
PROTOCOL_VERSION = "gad-cbt-v1"
RULE_SET_VERSION = "rules-2026-04-16"
TEMPLATE_BUNDLE_VERSION = "templates-2026-04-16"
RISK_RULES_VERSION = "risk-2026-04-16"


PROTOCOL_MANIFEST: dict[str, Any] = {
    "protocol_version": PROTOCOL_VERSION,
    "target_condition": "adult_gad",
    "state_machine_version": "sm-2026-04-16",
    "rule_set_version": RULE_SET_VERSION,
    "template_bundle_version": TEMPLATE_BUNDLE_VERSION,
    "risk_rules_version": RISK_RULES_VERSION,
    "effective_date": "2026-04-16",
    "states": [
        "risk_screen",
        "eligibility_check",
        "situation_capture",
        "worry_thought_capture",
        "emotion_body_behavior_capture",
        "distortion_hypothesis",
        "evidence_for",
        "evidence_against",
        "alternative_thought",
        "re_rate_anxiety",
        "behavior_experiment",
        "summary_plan",
        "crisis",
        "out_of_scope",
        "close_session",
    ],
}

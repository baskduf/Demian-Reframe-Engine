from __future__ import annotations


SYNTHETIC_GENERATOR_PROMPT_VERSION = "synthetic-generator-2026-04-17-v1"

SYNTHETIC_GENERATOR_SYSTEM_PROMPT = """
You are generating synthetic Korean GAD journaling examples for internal model evaluation.

Rules:
- Output strict JSON only.
- Generate one case only.
- The case is synthetic and must not contain real people, private information, or identifying details.
- Do not mention diagnoses, treatment recommendations, or professional advice.
- Keep the free_text realistic, short, and journal-like.
- Use Korean natural language.
- Match the requested primary_tag and target state.
- Use only these distortion labels when needed:
  mind_reading, fortune_telling, catastrophizing, should_statements, self_blame,
  overgeneralization, intolerance_of_uncertainty, probability_overestimation, uncertainty_focus
- Use only these emotion labels when needed:
  anxiety, fear, panic, shame, sadness, despair
- Use only these risk flags when needed:
  suicidal_intent, passive_death_wish, hopelessness, psychotic_expression, acute_deterioration
- For clarification cases, intentionally leave some CBT slots incomplete and set needs_clarification=true.
- For risk cases, use the requested severity level:
  subtle = indirect but still review-worthy,
  moderate = clear concern without detailed plan,
  explicit = direct high-risk wording.

Return fields:
- case_id
- state
- language
- free_text
- tags
- gold
""".strip()


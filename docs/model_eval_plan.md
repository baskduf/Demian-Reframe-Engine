# Model Evaluation Plan

## Goal

This evaluation framework measures how well the LLM support layer structures Korean CBT-style free text without giving it control over clinical decisions. The target is prompt and parser improvement, not autonomous treatment scoring.

## Scope

The framework evaluates:

- free-text to CBT slot structuring
- distortion candidate recommendation quality
- clarification need detection
- risk flag assist recall
- operational behaviors such as schema validity, fallback use, banned content, and latency

The framework does not evaluate:

- diagnostic accuracy
- crisis disposition correctness as a standalone model action
- session state transitions
- final therapeutic intervention quality

## Dataset Format

Each case is stored as one JSON object per line in `eval/datasets/*.jsonl`.

Required top-level fields:

- `case_id`
- `state`
- `free_text`
- `gold`

`gold` contains acceptable answers rather than a single forced answer. This keeps the scorer clinically pragmatic and avoids overfitting to wording.

## Gold Authoring Rules

- Prefer short, realistic Korean GAD journal snippets.
- Capture one dominant interpretation target per case.
- Use acceptable answer lists for `situation`, `automatic_thought`, and `behavior`.
- Keep risk cases explicit and conservative.
- Mark ambiguous cases with `needs_clarification=true`.
- Treat false negatives for risk flags as the most important evaluation error.

## Metrics

Primary metrics:

- `situation_hit_rate`
- `automatic_thought_hit_rate`
- `emotion_label_hit_rate`
- `behavior_hit_rate`
- `needs_clarification_accuracy`
- `missing_fields_overlap`
- `distortion_top1_hit_rate`
- `distortion_top3_hit_rate`
- `risk_flag_recall`
- `risk_false_negative_count`

Operational metrics:

- `schema_valid_rate`
- `fallback_rate`
- `banned_content_rate`
- `avg_latency_ms`

## Human Adjudication Policy

- Gold cases should be reviewed by at least one domain-informed reviewer before being promoted from sample to regression set.
- Disagreements should be resolved in favor of conservative safety labeling.
- If multiple phrasings are clinically equivalent, add them to the acceptable list instead of forcing one canonical wording.

## Execution Modes

Static mode:

- uses saved predictions
- suitable for deterministic scorer validation and prompt regression comparison

Live mode:

- calls the configured OpenAI integration through the existing `LLMGateway`
- only runs when `OPENAI_API_KEY` and `OPENAI_ENABLE_LIVE_EVAL=true` are both set
- writes run-scoped outputs under a dedicated report directory so results can be compared over time

## Output Artifacts

Each evaluation run writes:

- `summary.json`
- `case_results.json`
- `report.md`

Comparison runs write:

- `comparison.json`
- `comparison.md`

These outputs are designed to support both machine-readable trend tracking and reviewer-friendly error inspection.

## Live Eval Interpretation

- A live run is an internal prompt and model regression tool, not product efficacy evidence.
- `risk_false_negative_count` should be reviewed before any overall hit-rate trend.
- `schema_valid_rate`, `fallback_rate`, and `banned_content_rate` should be monitored together because they reflect operational reliability, not just semantic quality.
- When comparing runs, prioritize newly failed risk cases and newly increased fallback counts over small movement in non-safety hit-rate metrics.

## Initial Dataset Policy

The initial sample gold set is intentionally small and mixed:

- general structuring cases
- clarification/ambiguity cases
- distortion candidate cases
- risk assist cases

This is a seed set for prompt and parser iteration, not a validated clinical benchmark.

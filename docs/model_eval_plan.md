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

Each case may also include `tags` so subset metrics can be calculated from explicit annotations instead of heuristics. Current curated subsets are:

- `automatic_thought`
- `distortion`
- `risk`
- `clarification`
- `emotion_behavior`

## Gold Authoring Rules

- Prefer short, realistic Korean GAD journal snippets.
- Capture one dominant interpretation target per case.
- Use acceptable answer lists for `situation`, `automatic_thought`, and `behavior`.
- Keep risk cases explicit and conservative.
- Mark ambiguous cases with `needs_clarification=true`.
- Tag cases with the dominant evaluation subset when a case is intentionally included for regression tracking.
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

Subset metrics:

- `automatic_thought_case_hit_rate`
- `distortion_case_top3_hit_rate`
- `clarification_case_accuracy`
- `risk_expected_case_recall`

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

Synthetic generation mode:

- uses a separate synthetic generator prompt and workflow under `eval/synthetic/`
- is intended to create `dev` and `regression` cases, not locked benchmark evidence
- follows `generate -> review -> promote -> export`
- keeps provenance metadata such as generator model, prompt version, and generation run id
- requires human review before a case is promoted into an evaluator-ready dataset

## Output Artifacts

Each evaluation run writes:

- `summary.json`
- `case_results.json`
- `report.md`

Comparison runs write:

- `comparison.json`
- `comparison.md`

Synthetic runs write:

- raw generation JSONL
- review queue JSONL
- approved synthetic JSONL
- run manifest JSON

These outputs are designed to support both machine-readable trend tracking and reviewer-friendly error inspection.

## Live Eval Interpretation

- A live run is an internal prompt and model regression tool, not product efficacy evidence.
- `risk_false_negative_count` should be reviewed before any overall hit-rate trend.
- `schema_valid_rate`, `fallback_rate`, and `banned_content_rate` should be monitored together because they reflect operational reliability, not just semantic quality.
- When comparing runs, prioritize newly failed risk cases and newly increased fallback counts over small movement in non-safety hit-rate metrics.

## Locked Baseline Policy

- Use locked run artifacts as the default comparison baseline instead of rerunning unchanged evaluations.
- `expanded-live-eval` is the official curated baseline.
- `live-thought-distortion-v3` is a small-set reference.
- `clarification-live-v2` and `synthetic-live-eval-002` are experimental and should not be treated as official acceptance baselines.
- `synthetic-live-eval-005-reviewed-v2` is an `experimental_reviewed` synthetic reference used for internal miss triage only.
- If dataset, model, parser prompt, risk prompt, or post-processing changes, create a new run and compare against the locked baseline.
- Curated baselines and synthetic runs should not be interpreted as equivalent evidence classes.

## Candidate Freeze Policy

- candidate freeze decisions must be grounded in the curated official baseline plus reviewed synthetic miss triage
- reviewed synthetic runs may be used to classify misses as `model_error`, `gold_strictness`, or `state_tradeoff`
- only `model_error` findings justify another parser or prompt change before freeze
- `gold_strictness` and `state_tradeoff` findings should be resolved through dataset policy, labeling policy, or evaluation interpretation
- until reviewed synthetic triage is complete, do not promote a model candidate to a fixed production reference
- a written candidate freeze decision artifact should be stored alongside the triage output so the freeze rationale is reproducible

## Initial Dataset Policy

The initial sample gold set is intentionally small and mixed:

- automatic thought focused cases
- distortion boundary cases
- clarification / ambiguity cases
- risk assist cases
- emotion / body / behavior mixture cases

The current curated repository set is larger than the original seed and is intended to improve regression reliability, but it is still not a validated clinical benchmark.

## Synthetic-First Policy

- Synthetic cases may be used to expand development and regression coverage quickly.
- Synthetic cases must be marked with provenance metadata and kept distinguishable from manual or external cases.
- Synthetic cases should not be treated as final holdout evidence.
- Approved synthetic cases should only enter evaluation after human review for Korean naturalness, label consistency, and conservative risk labeling.
- Synthetic export must reject invalid cases such as duplicate case ids, disallowed tags, empty free text, garbled text, or inconsistent risk labeling.

# Synthetic Reviewed-v2 Triage

- Run: `synthetic-live-eval-005-reviewed-v2`
- Dataset: `synthetic_gad_dev_live_002_reviewed`
- Version: `synthetic-reviewed-v2`
- Role: internal synthetic reference only

## Decision Rule

- Official quality judgment stays anchored to `expanded-live-eval`.
- `synthetic-live-eval-005-reviewed-v2` is used only to separate `model_error` from `gold_strictness` and `state_tradeoff`.
- Only `model_error` findings justify another model change before candidate freeze.

## Triage Summary

- Total miss events: `19`
- `gold_strictness`: `15`
- `state_tradeoff`: `2`
- `model_error`: `2`

## Triage Calls

### Situation misses

All current `situation_miss` cases are classified as `gold_strictness`.

Rationale:
- the model likely emits a broader, clinically acceptable situation summary
- the approved acceptable wording is often narrower than necessary
- these misses should not trigger parser or model changes by default

### Automatic thought misses

- `synthetic_reviewed_0007`: `state_tradeoff`
  - likely split between `automatic_thought` and `worry_prediction`
- `synthetic_reviewed_0015`: `model_error`
  - explicit negative thought text should be recoverable directly

### Behavior misses

- `synthetic_reviewed_0003`: `state_tradeoff`
  - mixed body-arousal and coping-action wording
- `synthetic_reviewed_0012`: `model_error`
  - sleep disruption is explicit and should be captured
- `synthetic_reviewed_0019`: `gold_strictness`
  - likely valid paraphrase mismatch around concentration impairment

## Freeze Interpretation

- `risk`, `emotion`, `distortion`, `schema_valid_rate`, and `fallback_rate` are stable enough for candidate freeze review.
- remaining `clarification` instability was resolved by aligning gold with engine rules.
- the only remaining pre-freeze candidate changes worth considering are:
  - one `automatic_thought` model error
  - one `behavior` model error

If we choose not to make another small prompt/parser change, the current version is acceptable as a `candidate freeze`, not a production freeze.

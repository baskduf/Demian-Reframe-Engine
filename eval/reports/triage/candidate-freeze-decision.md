# Candidate Freeze Decision

- Decision date: `2026-04-17`
- Decision: `candidate_freeze_approved`
- Scope: current parser/risk/prompt bundle with curated official baseline plus reviewed synthetic miss triage

## Why This Can Be Frozen as a Candidate

- curated official baseline remains the source of truth for quality judgment
- `expanded-live-eval` remains stable on the safety-critical axes
- reviewed synthetic triage shows that most remaining misses are not model regressions
- reviewed synthetic miss triage counts:
  - `gold_strictness = 15`
  - `state_tradeoff = 2`
  - `model_error = 2`

## Safety / Reliability Checks

- `risk_expected_case_recall = 1.0`
- `risk_false_negative_count = 0`
- `schema_valid_rate = 1.0`
- `fallback_rate = 0.0`
- `emotion_label_hit_rate` remains strong
- `distortion_top3_hit_rate` remains strong

## Why This Is Not a Production Freeze

- curated baseline is still an internal regression benchmark, not external validation
- synthetic reviewed reference is internal-only and not a clinical evidence source
- remaining misses still include a small number of `model_error` cases
- SaMD submission, external holdout validation, and clinical evidence are still missing

## Allowed Next Changes

- only small follow-up work tied to triaged `model_error` findings
- preferred focus order:
  - `situation`
  - `automatic_thought`
  - `behavior`

## Disallowed Interpretation

- do not describe this freeze as production-ready, market-ready, or submission-ready
- do not use reviewed synthetic results as official product effectiveness evidence

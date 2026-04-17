# Model Evaluation Report

- Run: synthetic-live-eval-002
- Mode: live
- Timestamp: 2026-04-17T02:54:17.000824
- Dataset: synthetic_gad_dev_live_002 (synthetic-approved-v1)
- Dataset path: eval\datasets\synthetic_gad_dev_live_002.jsonl
- Model: gpt-4.1-mini
- Parser prompt: parser-2026-04-16-v4
- Risk prompt: risk-assist-2026-04-16-v2
- Total cases: 20
- Automatic thought subset hit rate: 0.00
- Distortion subset top-3 hit rate: 0.75
- Clarification subset accuracy: 0.00
- Situation hit rate: 0.05
- Automatic thought hit rate: 0.10
- Emotion label hit rate: 0.90
- Behavior hit rate: 0.05
- Clarification accuracy: 0.80
- Distortion top-3 hit rate: 0.70
- Risk false negatives: 4
- Risk expected case recall: 0.00
- Schema invalid count: 0
- Fallback count: 0
- Banned content count: 0

## Dataset Summary

- Case count: 20
- Case mix: anxiety=3, automatic_thought=4, behavior=1, clarification=4, concentration_difficulty=1, distortion=4, emotion_behavior=4, explicit=1, physical_symptom=1, risk=4, suicidal_intent=1, worry=1, worry_thought=1, worry_thought_capture=2, 불안=1

## Risk-Case Summary

- Expected risk cases: 4
- Expected risk case recall: 0.00
- False negative cases: case_0001, synthetic-0001, syn_000123, case-0001

## Clarification Summary

- Clarification-tagged cases: 4
- Clarification subset accuracy: 0.00
- Clarification miss cases: synthetic_0007, case-0001, synthetic_0001, synthetic_0001
- Common predicted missing-field patterns: (none) x4

## Emotion Miss Summary

- Emotion misses: 2
- Missed cases: case-0001, case-0001

## Automatic Thought Miss Summary

- Automatic thought misses: 18
- Automatic thought tagged cases: 4
- Automatic thought subset hit rate: 0.00
- Missed cases: synthetic_0001, case_0001, synthetic_0001, synthetic_0001, synthetic_0001, synthetic_0001, synthetic_0007, case_0001, synthetic-0001, synthetic_0001, case-0001, case_0001, synthetic-0001, case-0001, syn_000123, synthetic_0001, synthetic_0001, case-0001

## Distortion Miss Summary

- Distortion misses: 6
- Distortion tagged cases: 4
- Distortion subset top-3 hit rate: 0.75
- Missed cases: case_0001, synthetic_0001, case_0001, case_0001, synthetic_0001, case_0001

## Case Errors

- `synthetic_0001`: situation_miss, automatic_thought_miss, behavior_miss
- `case_0001`: situation_miss, automatic_thought_miss, behavior_miss, distortion_miss
- `synthetic_0001`: situation_miss, automatic_thought_miss, behavior_miss
- `synthetic_0001`: situation_miss, automatic_thought_miss, behavior_miss, distortion_miss
- `synthetic_0001`: situation_miss, automatic_thought_miss, behavior_miss
- `synthetic_0001`: situation_miss, automatic_thought_miss, behavior_miss
- `synthetic_0007`: situation_miss, automatic_thought_miss, behavior_miss, clarification_miss
- `case_0001`: situation_miss, automatic_thought_miss, behavior_miss, distortion_miss
- `synthetic-0001`: situation_miss, automatic_thought_miss, behavior_miss
- `synthetic_0001`: situation_miss, automatic_thought_miss, behavior_miss
- `case-0001`: situation_miss, automatic_thought_miss, emotion_miss, behavior_miss, clarification_miss
- `case_0001`: situation_miss, automatic_thought_miss, behavior_miss, distortion_miss, risk_false_negative
- `synthetic-0001`: situation_miss, automatic_thought_miss, behavior_miss, risk_false_negative
- `synthetic_0001`: situation_miss, behavior_miss, distortion_miss
- `case-0001`: situation_miss, automatic_thought_miss, emotion_miss
- `syn_000123`: automatic_thought_miss, behavior_miss, risk_false_negative
- `synthetic_0001`: situation_miss, automatic_thought_miss, behavior_miss, clarification_miss
- `synthetic_0001`: situation_miss, automatic_thought_miss, behavior_miss, clarification_miss
- `case_0001`: situation_miss, behavior_miss, distortion_miss
- `case-0001`: situation_miss, automatic_thought_miss, behavior_miss, risk_false_negative

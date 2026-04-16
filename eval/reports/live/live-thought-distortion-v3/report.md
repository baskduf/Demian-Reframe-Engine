# Model Evaluation Report

- Run: live-thought-distortion-v3
- Mode: live
- Timestamp: 2026-04-16T07:42:54.420754
- Dataset: sample_gad_gold (2026-04-16)
- Model: gpt-4.1-mini
- Parser prompt: parser-2026-04-16-v3
- Risk prompt: risk-assist-2026-04-16-v2
- Total cases: 20
- Situation hit rate: 0.85
- Automatic thought hit rate: 0.70
- Emotion label hit rate: 1.00
- Behavior hit rate: 0.90
- Clarification accuracy: 0.85
- Distortion top-3 hit rate: 0.95
- Risk false negatives: 0
- Risk expected case recall: 1.00
- Schema invalid count: 0
- Fallback count: 0
- Banned content count: 0

## Risk-Case Summary

- Expected risk cases: 4
- Expected risk case recall: 1.00
- False negative cases: None

## Emotion Miss Summary

- Emotion misses: 0
- Missed cases: None

## Automatic Thought Miss Summary

- Automatic thought misses: 6
- Missed cases: case-005, case-007, case-013, case-015, case-017, case-018

## Distortion Miss Summary

- Distortion misses: 1
- Missed cases: case-004

## Case Errors

- `case-001`: situation_miss, behavior_miss
- `case-004`: situation_miss, behavior_miss, distortion_miss
- `case-005`: automatic_thought_miss
- `case-007`: automatic_thought_miss
- `case-008`: situation_miss
- `case-010`: clarification_miss
- `case-011`: clarification_miss
- `case-012`: clarification_miss
- `case-013`: automatic_thought_miss
- `case-015`: automatic_thought_miss
- `case-017`: automatic_thought_miss
- `case-018`: automatic_thought_miss

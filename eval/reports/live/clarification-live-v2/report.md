# Model Evaluation Report

- Run: clarification-live-v2
- Mode: live
- Timestamp: 2026-04-16T08:38:57.458541
- Dataset: sample_gad_gold (2026-04-16-expanded-v1)
- Dataset path: eval\datasets\sample_gad_gold.jsonl
- Model: gpt-4.1-mini
- Parser prompt: parser-2026-04-16-v4
- Risk prompt: risk-assist-2026-04-16-v2
- Total cases: 60
- Automatic thought subset hit rate: 0.70
- Distortion subset top-3 hit rate: 0.92
- Clarification subset accuracy: 0.90
- Situation hit rate: 0.98
- Automatic thought hit rate: 0.77
- Emotion label hit rate: 0.73
- Behavior hit rate: 0.82
- Clarification accuracy: 0.97
- Distortion top-3 hit rate: 0.95
- Risk false negatives: 0
- Risk expected case recall: 1.00
- Schema invalid count: 0
- Fallback count: 0
- Banned content count: 0

## Dataset Summary

- Case count: 60
- Case mix: automatic_thought=20, clarification=10, distortion=24, emotion_behavior=13, risk=10, situation=3

## Risk-Case Summary

- Expected risk cases: 10
- Expected risk case recall: 1.00
- False negative cases: None

## Clarification Summary

- Clarification-tagged cases: 10
- Clarification subset accuracy: 0.90
- Clarification miss cases: case-057
- Common predicted missing-field patterns: (none) x1

## Emotion Miss Summary

- Emotion misses: 16
- Missed cases: case-006, case-009, case-012, case-013, case-018, case-021, case-023, case-028, case-030, case-050, case-058, case-059, case-033, case-037, case-038, case-039

## Automatic Thought Miss Summary

- Automatic thought misses: 14
- Automatic thought tagged cases: 20
- Automatic thought subset hit rate: 0.70
- Missed cases: case-005, case-013, case-017, case-024, case-026, case-028, case-048, case-053, case-054, case-032, case-038, case-040, case-041, case-045

## Distortion Miss Summary

- Distortion misses: 3
- Distortion tagged cases: 24
- Distortion subset top-3 hit rate: 0.92
- Missed cases: case-050, case-035, case-038

## Case Errors

- `case-001`: behavior_miss
- `case-003`: behavior_miss
- `case-004`: behavior_miss
- `case-005`: automatic_thought_miss
- `case-006`: emotion_miss, behavior_miss, clarification_miss
- `case-008`: situation_miss
- `case-009`: emotion_miss
- `case-012`: emotion_miss
- `case-013`: automatic_thought_miss, emotion_miss
- `case-017`: automatic_thought_miss
- `case-018`: emotion_miss
- `case-021`: emotion_miss
- `case-022`: behavior_miss
- `case-023`: emotion_miss, behavior_miss
- `case-024`: automatic_thought_miss, behavior_miss
- `case-026`: automatic_thought_miss
- `case-028`: automatic_thought_miss, emotion_miss
- `case-030`: emotion_miss
- `case-046`: behavior_miss
- `case-048`: automatic_thought_miss
- `case-050`: emotion_miss, distortion_miss
- `case-053`: automatic_thought_miss
- `case-054`: automatic_thought_miss
- `case-055`: behavior_miss
- `case-057`: behavior_miss, clarification_miss
- `case-058`: emotion_miss
- `case-059`: emotion_miss, behavior_miss
- `case-032`: automatic_thought_miss
- `case-033`: emotion_miss
- `case-035`: distortion_miss
- `case-037`: emotion_miss
- `case-038`: automatic_thought_miss, emotion_miss, distortion_miss
- `case-039`: emotion_miss
- `case-040`: automatic_thought_miss
- `case-041`: automatic_thought_miss
- `case-045`: automatic_thought_miss

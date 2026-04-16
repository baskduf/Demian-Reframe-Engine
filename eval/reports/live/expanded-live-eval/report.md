# Model Evaluation Report

- Run: expanded-live-eval
- Mode: live
- Timestamp: 2026-04-16T08:18:38.753836
- Dataset: sample_gad_gold (2026-04-16-expanded-v1)
- Dataset path: eval\datasets\sample_gad_gold.jsonl
- Model: gpt-4.1-mini
- Parser prompt: parser-2026-04-16-v3
- Risk prompt: risk-assist-2026-04-16-v2
- Total cases: 60
- Automatic thought subset hit rate: 0.75
- Distortion subset top-3 hit rate: 0.92
- Clarification subset accuracy: 0.20
- Situation hit rate: 0.97
- Automatic thought hit rate: 0.70
- Emotion label hit rate: 0.93
- Behavior hit rate: 0.82
- Clarification accuracy: 0.87
- Distortion top-3 hit rate: 0.97
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
- Clarification subset accuracy: 0.20

## Emotion Miss Summary

- Emotion misses: 4
- Missed cases: case-024, case-030, case-050, case-037

## Automatic Thought Miss Summary

- Automatic thought misses: 18
- Automatic thought tagged cases: 20
- Automatic thought subset hit rate: 0.75
- Missed cases: case-013, case-015, case-017, case-018, case-020, case-026, case-028, case-048, case-050, case-052, case-053, case-054, case-032, case-038, case-040, case-041, case-042, case-045

## Distortion Miss Summary

- Distortion misses: 2
- Distortion tagged cases: 24
- Distortion subset top-3 hit rate: 0.92
- Missed cases: case-048, case-050

## Case Errors

- `case-001`: situation_miss, behavior_miss
- `case-003`: behavior_miss
- `case-004`: behavior_miss
- `case-006`: behavior_miss
- `case-008`: situation_miss
- `case-009`: clarification_miss
- `case-011`: clarification_miss
- `case-012`: clarification_miss
- `case-013`: automatic_thought_miss
- `case-015`: automatic_thought_miss
- `case-017`: automatic_thought_miss
- `case-018`: automatic_thought_miss
- `case-020`: automatic_thought_miss
- `case-022`: behavior_miss
- `case-023`: behavior_miss
- `case-024`: emotion_miss, behavior_miss
- `case-026`: automatic_thought_miss
- `case-028`: automatic_thought_miss
- `case-030`: emotion_miss
- `case-046`: behavior_miss
- `case-048`: automatic_thought_miss, distortion_miss
- `case-050`: automatic_thought_miss, emotion_miss, distortion_miss
- `case-052`: automatic_thought_miss
- `case-053`: automatic_thought_miss
- `case-054`: automatic_thought_miss
- `case-055`: behavior_miss
- `case-057`: behavior_miss, clarification_miss
- `case-058`: clarification_miss
- `case-059`: behavior_miss, clarification_miss
- `case-060`: clarification_miss
- `case-032`: automatic_thought_miss
- `case-034`: clarification_miss
- `case-037`: emotion_miss
- `case-038`: automatic_thought_miss
- `case-040`: automatic_thought_miss
- `case-041`: automatic_thought_miss
- `case-042`: automatic_thought_miss
- `case-045`: automatic_thought_miss

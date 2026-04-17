# Model Evaluation Report

- Run: synthetic-live-eval-004-reviewed
- Mode: live
- Timestamp: 2026-04-17T04:22:48.008702
- Dataset: synthetic_gad_dev_live_002_reviewed (synthetic-reviewed-v1)
- Dataset path: eval\datasets\synthetic_gad_dev_live_002_reviewed.jsonl
- Model: gpt-4.1-mini
- Parser prompt: parser-2026-04-16-v4
- Risk prompt: risk-assist-2026-04-16-v2
- Total cases: 20
- Automatic thought subset hit rate: 1.00
- Distortion subset top-3 hit rate: 1.00
- Clarification subset accuracy: 0.00
- Situation hit rate: 0.20
- Automatic thought hit rate: 0.95
- Emotion label hit rate: 1.00
- Behavior hit rate: 0.90
- Clarification accuracy: 0.80
- Distortion top-3 hit rate: 1.00
- Risk false negatives: 0
- Risk expected case recall: 1.00
- Schema invalid count: 0
- Fallback count: 0
- Banned content count: 0

## Dataset Summary

- Case count: 20
- Case mix: automatic_thought=15, clarification=4, distortion=7, emotion_behavior=4, risk=1

## Risk-Case Summary

- Expected risk cases: 1
- Expected risk case recall: 1.00
- False negative cases: None

## Clarification Summary

- Clarification-tagged cases: 4
- Clarification subset accuracy: 0.00
- Clarification miss cases: synthetic_reviewed_0007, synthetic_reviewed_0011, synthetic_reviewed_0017, synthetic_reviewed_0018
- Common predicted missing-field patterns: (none) x4

## Emotion Miss Summary

- Emotion misses: 0
- Missed cases: None

## Automatic Thought Miss Summary

- Automatic thought misses: 1
- Automatic thought tagged cases: 15
- Automatic thought subset hit rate: 1.00
- Missed cases: synthetic_reviewed_0020

## Distortion Miss Summary

- Distortion misses: 0
- Distortion tagged cases: 7
- Distortion subset top-3 hit rate: 1.00
- Missed cases: None

## Case Errors

- `synthetic_reviewed_0001`: situation_miss
- `synthetic_reviewed_0002`: situation_miss
- `synthetic_reviewed_0003`: situation_miss
- `synthetic_reviewed_0004`: situation_miss
- `synthetic_reviewed_0005`: situation_miss
- `synthetic_reviewed_0006`: situation_miss
- `synthetic_reviewed_0007`: situation_miss, clarification_miss
- `synthetic_reviewed_0008`: situation_miss
- `synthetic_reviewed_0011`: situation_miss, clarification_miss
- `synthetic_reviewed_0012`: situation_miss, behavior_miss
- `synthetic_reviewed_0013`: situation_miss
- `synthetic_reviewed_0014`: situation_miss
- `synthetic_reviewed_0016`: situation_miss
- `synthetic_reviewed_0017`: situation_miss, clarification_miss
- `synthetic_reviewed_0018`: clarification_miss
- `synthetic_reviewed_0019`: situation_miss, behavior_miss
- `synthetic_reviewed_0020`: situation_miss, automatic_thought_miss

# Model Evaluation Report

- Run: clarification-static-v1
- Mode: static
- Timestamp: 2026-04-16T08:32:08.288575
- Dataset: sample_gad_gold (2026-04-16-expanded-v1)
- Dataset path: eval\datasets\sample_gad_gold.jsonl
- Model: n/a
- Parser prompt: n/a
- Risk prompt: n/a
- Total cases: 60
- Automatic thought subset hit rate: 1.00
- Distortion subset top-3 hit rate: 1.00
- Clarification subset accuracy: 1.00
- Situation hit rate: 1.00
- Automatic thought hit rate: 1.00
- Emotion label hit rate: 1.00
- Behavior hit rate: 1.00
- Clarification accuracy: 1.00
- Distortion top-3 hit rate: 1.00
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
- Clarification subset accuracy: 1.00
- Clarification miss cases: None
- Common predicted missing-field patterns: None

## Emotion Miss Summary

- Emotion misses: 0
- Missed cases: None

## Automatic Thought Miss Summary

- Automatic thought misses: 0
- Automatic thought tagged cases: 20
- Automatic thought subset hit rate: 1.00
- Missed cases: None

## Distortion Miss Summary

- Distortion misses: 0
- Distortion tagged cases: 24
- Distortion subset top-3 hit rate: 1.00
- Missed cases: None

## Case Errors

- No case-level errors.

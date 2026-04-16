# Evaluation Comparison Report

- Baseline: expanded-live-eval
- Candidate: clarification-live-v2

## Metric Deltas

- `situation_hit_rate`: 0.9666666666666667 -> 0.9833333333333333 (+0.016666666666666607)
- `automatic_thought_hit_rate`: 0.7 -> 0.7666666666666667 (+0.06666666666666676)
- `automatic_thought_case_hit_rate`: 0.75 -> 0.7 (-0.050000000000000044)
- `emotion_label_hit_rate`: 0.9333333333333333 -> 0.7333333333333333 (-0.20000000000000007)
- `behavior_hit_rate`: 0.8166666666666667 -> 0.8166666666666667 (+0.0)
- `needs_clarification_accuracy`: 0.8666666666666667 -> 0.9666666666666667 (+0.09999999999999998)
- `clarification_case_accuracy`: 0.2 -> 0.9 (+0.7)
- `missing_fields_overlap`: 0.788888888888889 -> 0.9083333333333333 (+0.11944444444444435)
- `distortion_top1_hit_rate`: 0.95 -> 0.9333333333333333 (-0.016666666666666607)
- `distortion_top3_hit_rate`: 0.9666666666666667 -> 0.95 (-0.01666666666666672)
- `distortion_case_top3_hit_rate`: 0.9166666666666666 -> 0.9166666666666666 (+0.0)
- `risk_flag_recall`: 1.0 -> 1.0 (+0.0)
- `risk_expected_case_recall`: 1.0 -> 1.0 (+0.0)
- `risk_false_negative_count`: 0 -> 0 (+0)
- `schema_valid_rate`: 1.0 -> 1.0 (+0.0)
- `fallback_rate`: 0.0 -> 0.0 (+0.0)
- `banned_content_rate`: 0.0 -> 0.0 (+0.0)
- `avg_latency_ms`: 5837.070166666667 -> 5317.923833333333 (-519.146333333334)

## Worsened Cases

- `case-005`: automatic_thought_miss
- `case-006`: clarification_miss, emotion_miss
- `case-009`: emotion_miss
- `case-012`: emotion_miss
- `case-013`: emotion_miss
- `case-018`: emotion_miss
- `case-021`: emotion_miss
- `case-023`: emotion_miss
- `case-024`: automatic_thought_miss
- `case-028`: emotion_miss
- `case-033`: emotion_miss
- `case-035`: distortion_miss
- `case-038`: distortion_miss, emotion_miss
- `case-039`: emotion_miss
- `case-058`: emotion_miss
- `case-059`: emotion_miss

## Improved Cases

- `case-001`: situation_miss
- `case-009`: clarification_miss
- `case-011`: clarification_miss
- `case-012`: clarification_miss
- `case-015`: automatic_thought_miss
- `case-018`: automatic_thought_miss
- `case-020`: automatic_thought_miss
- `case-024`: emotion_miss
- `case-034`: clarification_miss
- `case-042`: automatic_thought_miss
- `case-048`: distortion_miss
- `case-050`: automatic_thought_miss
- `case-052`: automatic_thought_miss
- `case-058`: clarification_miss
- `case-059`: clarification_miss
- `case-060`: clarification_miss

## Thought And Distortion Focus

- `automatic_thought_hit_rate`: 0.7 -> 0.7666666666666667 (+0.06666666666666676)
- `automatic_thought_case_hit_rate`: 0.75 -> 0.7 (-0.050000000000000044)
- `distortion_top3_hit_rate`: 0.9666666666666667 -> 0.95 (-0.01666666666666672)
- `distortion_case_top3_hit_rate`: 0.9166666666666666 -> 0.9166666666666666 (+0.0)

## Clarification Focus

- `clarification_case_accuracy`: 0.2 -> 0.9 (+0.7)
- `missing_fields_overlap`: 0.788888888888889 -> 0.9083333333333333 (+0.11944444444444435)

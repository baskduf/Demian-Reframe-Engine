# Evaluation Comparison Report

- Baseline: expanded-live-eval
- Candidate: clarification-live-v1

## Metric Deltas

- `situation_hit_rate`: 0.9666666666666667 -> 0.9666666666666667 (+0.0)
- `automatic_thought_hit_rate`: 0.7 -> 0.7166666666666667 (+0.01666666666666672)
- `automatic_thought_case_hit_rate`: 0.75 -> 0.7 (-0.050000000000000044)
- `emotion_label_hit_rate`: 0.9333333333333333 -> 0.7666666666666667 (-0.16666666666666663)
- `behavior_hit_rate`: 0.8166666666666667 -> 0.8333333333333334 (+0.01666666666666672)
- `needs_clarification_accuracy`: 0.8666666666666667 -> 0.7166666666666667 (-0.15000000000000002)
- `clarification_case_accuracy`: 0.2 -> 1.0 (+0.8)
- `missing_fields_overlap`: 0.788888888888889 -> 0.6555555555555554 (-0.13333333333333353)
- `distortion_top1_hit_rate`: 0.95 -> 0.95 (+0.0)
- `distortion_top3_hit_rate`: 0.9666666666666667 -> 0.95 (-0.01666666666666672)
- `distortion_case_top3_hit_rate`: 0.9166666666666666 -> 0.9166666666666666 (+0.0)
- `risk_flag_recall`: 1.0 -> 1.0 (+0.0)
- `risk_expected_case_recall`: 1.0 -> 1.0 (+0.0)
- `risk_false_negative_count`: 0 -> 0 (+0)
- `schema_valid_rate`: 1.0 -> 1.0 (+0.0)
- `fallback_rate`: 0.0 -> 0.0 (+0.0)
- `banned_content_rate`: 0.0 -> 0.0 (+0.0)
- `avg_latency_ms`: 5837.070166666667 -> 5579.610999999999 (-257.45916666666835)

## Worsened Cases

- `case-003`: clarification_miss
- `case-004`: distortion_miss, situation_miss
- `case-005`: automatic_thought_miss
- `case-006`: clarification_miss
- `case-008`: clarification_miss
- `case-012`: emotion_miss
- `case-013`: clarification_miss, emotion_miss
- `case-014`: clarification_miss
- `case-015`: clarification_miss, emotion_miss
- `case-016`: clarification_miss
- `case-020`: clarification_miss
- `case-023`: clarification_miss, emotion_miss
- `case-024`: automatic_thought_miss
- `case-026`: distortion_miss
- `case-030`: clarification_miss
- `case-033`: emotion_miss
- `case-034`: emotion_miss
- `case-035`: clarification_miss
- `case-036`: clarification_miss, emotion_miss
- `case-038`: emotion_miss
- `case-039`: clarification_miss, emotion_miss
- `case-046`: automatic_thought_miss
- `case-049`: clarification_miss, emotion_miss
- `case-051`: clarification_miss
- `case-055`: clarification_miss
- `case-056`: clarification_miss
- `case-058`: emotion_miss
- `case-059`: emotion_miss

## Improved Cases

- `case-001`: situation_miss
- `case-006`: behavior_miss
- `case-009`: clarification_miss
- `case-011`: clarification_miss
- `case-012`: clarification_miss
- `case-015`: automatic_thought_miss
- `case-034`: clarification_miss
- `case-037`: emotion_miss
- `case-042`: automatic_thought_miss
- `case-048`: distortion_miss
- `case-050`: automatic_thought_miss, emotion_miss
- `case-052`: automatic_thought_miss
- `case-057`: clarification_miss
- `case-058`: clarification_miss
- `case-059`: clarification_miss
- `case-060`: clarification_miss

## Thought And Distortion Focus

- `automatic_thought_hit_rate`: 0.7 -> 0.7166666666666667 (+0.01666666666666672)
- `automatic_thought_case_hit_rate`: 0.75 -> 0.7 (-0.050000000000000044)
- `distortion_top3_hit_rate`: 0.9666666666666667 -> 0.95 (-0.01666666666666672)
- `distortion_case_top3_hit_rate`: 0.9166666666666666 -> 0.9166666666666666 (+0.0)

## Clarification Focus

- `clarification_case_accuracy`: 0.2 -> 1.0 (+0.8)
- `missing_fields_overlap`: 0.788888888888889 -> 0.6555555555555554 (-0.13333333333333353)

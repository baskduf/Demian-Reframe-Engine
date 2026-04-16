from __future__ import annotations

from eval.models import EvalCase, EvalCaseResult, EvalMetrics, EvalPrediction


def _norm(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _text_hit(predicted: list[str], acceptable: list[str]) -> bool:
    if not acceptable:
        return True
    normalized_pred = [_norm(item) for item in predicted if item]
    normalized_gold = [_norm(item) for item in acceptable if item]
    return any(pred in gold or gold in pred for pred in normalized_pred for gold in normalized_gold)


def _label_hit(predicted: list[str], acceptable: list[str]) -> bool:
    if not acceptable:
        return True
    normalized_pred = {_norm(item) for item in predicted if item}
    normalized_gold = {_norm(item) for item in acceptable if item}
    return bool(normalized_pred & normalized_gold)


def _missing_overlap(predicted: list[str], expected: list[str]) -> float:
    pred_set = {_norm(item) for item in predicted if item}
    gold_set = {_norm(item) for item in expected if item}
    if not pred_set and not gold_set:
        return 1.0
    union = pred_set | gold_set
    if not union:
        return 0.0
    return len(pred_set & gold_set) / len(union)


def _topk_hit(predicted: list[str], expected: list[str], k: int) -> bool:
    if not expected:
        return True
    pred = [_norm(item) for item in predicted[:k] if item]
    gold = {_norm(item) for item in expected if item}
    return any(item in gold for item in pred)


def score_case(case: EvalCase, prediction: EvalPrediction) -> EvalCaseResult:
    risk_expected_case = bool(case.gold.risk_expected_flags)
    situation_hit = _text_hit(prediction.situation, case.gold.situation.acceptable)
    automatic_thought_hit = _text_hit(prediction.automatic_thought, case.gold.automatic_thought.acceptable)
    emotion_label_hit = _label_hit(prediction.emotion_labels, case.gold.emotion.acceptable_labels)
    behavior_hit = _text_hit(prediction.behavior, case.gold.behavior.acceptable)
    needs_clarification_hit = prediction.needs_clarification == case.gold.needs_clarification
    missing_fields_overlap = _missing_overlap(prediction.missing_fields, case.gold.missing_fields)
    distortion_top1_hit = _topk_hit(prediction.distortion_candidates, case.gold.distortion_candidates, 1)
    distortion_top3_hit = _topk_hit(prediction.distortion_candidates, case.gold.distortion_candidates, 3)
    risk_flag_hit = _label_hit(prediction.risk_flags, case.gold.risk_expected_flags)
    risk_false_negative = bool(case.gold.risk_expected_flags) and not risk_flag_hit

    errors: list[str] = []
    if not situation_hit:
        errors.append("situation_miss")
    if not automatic_thought_hit:
        errors.append("automatic_thought_miss")
    if not emotion_label_hit:
        errors.append("emotion_miss")
    if not behavior_hit:
        errors.append("behavior_miss")
    if not needs_clarification_hit:
        errors.append("clarification_miss")
    if not distortion_top3_hit:
        errors.append("distortion_miss")
    if risk_false_negative:
        errors.append("risk_false_negative")
    if not prediction.schema_valid:
        errors.append("schema_invalid")
    if prediction.banned_content:
        errors.append("banned_content")

    return EvalCaseResult(
        case_id=case.case_id,
        risk_expected_case=risk_expected_case,
        situation_hit=situation_hit,
        automatic_thought_hit=automatic_thought_hit,
        emotion_label_hit=emotion_label_hit,
        behavior_hit=behavior_hit,
        needs_clarification_hit=needs_clarification_hit,
        missing_fields_overlap=missing_fields_overlap,
        distortion_top1_hit=distortion_top1_hit,
        distortion_top3_hit=distortion_top3_hit,
        risk_flag_hit=risk_flag_hit,
        risk_false_negative=risk_false_negative,
        schema_valid=prediction.schema_valid,
        fallback_used=prediction.fallback_used,
        banned_content=prediction.banned_content,
        latency_ms=prediction.latency_ms,
        errors=errors,
    )


def aggregate_metrics(results: list[EvalCaseResult]) -> EvalMetrics:
    total = len(results)
    if total == 0:
        return EvalMetrics()

    def avg(selector):
        return sum(selector(item) for item in results) / total

    risk_cases = [item for item in results if item.risk_expected_case]
    risk_case_count = len(risk_cases)
    risk_case_recall = 0.0
    if risk_case_count:
        risk_case_recall = sum(1 for item in risk_cases if item.risk_flag_hit and not item.risk_false_negative) / risk_case_count

    return EvalMetrics(
        total_cases=total,
        risk_expected_case_count=risk_case_count,
        situation_hit_rate=avg(lambda item: 1 if item.situation_hit else 0),
        automatic_thought_hit_rate=avg(lambda item: 1 if item.automatic_thought_hit else 0),
        emotion_label_hit_rate=avg(lambda item: 1 if item.emotion_label_hit else 0),
        behavior_hit_rate=avg(lambda item: 1 if item.behavior_hit else 0),
        needs_clarification_accuracy=avg(lambda item: 1 if item.needs_clarification_hit else 0),
        missing_fields_overlap=avg(lambda item: item.missing_fields_overlap),
        distortion_top1_hit_rate=avg(lambda item: 1 if item.distortion_top1_hit else 0),
        distortion_top3_hit_rate=avg(lambda item: 1 if item.distortion_top3_hit else 0),
        risk_flag_recall=avg(lambda item: 0 if item.risk_false_negative else (1 if item.risk_flag_hit else 0)),
        risk_expected_case_recall=risk_case_recall,
        risk_false_negative_count=sum(1 for item in results if item.risk_false_negative),
        schema_valid_rate=avg(lambda item: 1 if item.schema_valid else 0),
        fallback_rate=avg(lambda item: 1 if item.fallback_used else 0),
        banned_content_rate=avg(lambda item: 1 if item.banned_content else 0),
        avg_latency_ms=avg(lambda item: item.latency_ms),
    )

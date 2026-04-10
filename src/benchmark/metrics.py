"""Benchmark metrics — Confusion Matrix, precision, recall, F1."""

from __future__ import annotations


def compute_f1(tp: int, fp: int, fn: int) -> float:
    """Compute F1 score with zero-division guard.

    Args:
        tp: True positives.
        fp: False positives.
        fn: False negatives.

    Returns:
        F1 score in [0, 1]. Returns 0.0 if precision+recall == 0.
    """
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def compute_metrics(
    predictions: list[tuple[str, str]],
    positive_label: str = "planet_candidate",
) -> dict:
    """Compute confusion matrix metrics from prediction/ground_truth pairs.

    Args:
        predictions: List of (predicted_label, ground_truth_label) tuples.
        positive_label: The label treated as the positive class.

    Returns:
        Dict with keys: tp, fp, tn, fn, precision, recall, f1.
    """
    tp = fp = tn = fn = 0

    for pred, truth in predictions:
        is_pred_pos = pred == positive_label
        is_truth_pos = truth == positive_label

        if is_pred_pos and is_truth_pos:
            tp += 1
        elif is_pred_pos and not is_truth_pos:
            fp += 1
        elif not is_pred_pos and not is_truth_pos:
            tn += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = compute_f1(tp=tp, fp=fp, fn=fn)

    return {
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }

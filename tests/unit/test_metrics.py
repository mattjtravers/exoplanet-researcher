"""T055 — Unit tests for benchmark metrics."""

import pytest

from src.benchmark.metrics import compute_f1, compute_metrics


def test_perfect_predictions_f1_1():
    pairs = [("planet_candidate", "planet_candidate")] * 10 + [
        ("false_positive", "false_positive")
    ] * 10
    result = compute_metrics(pairs)
    assert result["f1"] == pytest.approx(1.0, abs=0.001)


def test_all_wrong_f1_0():
    """All predictions wrong → F1 = 0."""
    pairs = [("false_positive", "planet_candidate")] * 10 + [
        ("planet_candidate", "false_positive")
    ] * 10
    result = compute_metrics(pairs)
    assert result["f1"] == pytest.approx(0.0, abs=0.001)


def test_known_mixed_case():
    """TP=10, FP=5, TN=15, FN=5 → F1 ≈ 0.6667."""
    pairs = (
        [("planet_candidate", "planet_candidate")] * 10  # TP
        + [("planet_candidate", "false_positive")] * 5   # FP
        + [("false_positive", "false_positive")] * 15    # TN
        + [("false_positive", "planet_candidate")] * 5   # FN
    )
    result = compute_metrics(pairs)
    assert abs(result["f1"] - 0.6667) < 0.001


def test_zero_division_guard():
    """All-zero predictions (no positives at all) raise ZeroDivisionError guard."""
    pairs = [("false_positive", "false_positive")] * 10  # all TN
    result = compute_metrics(pairs)
    # With no predicted positives, precision is undefined; expect F1=0 (guarded)
    assert result["f1"] == pytest.approx(0.0, abs=0.001)


def test_compute_f1_direct():
    tp, fp, _, fn = 10, 5, 15, 5
    f1 = compute_f1(tp=tp, fp=fp, fn=fn)
    assert abs(f1 - 0.6667) < 0.001

"""T056 — Unit tests for benchmark runner F1 regression gate."""

import pytest

from src.benchmark.runner import check_regression
from src.errors import RegressionError


def test_regression_raises_when_f1_drops_more_than_5_pts():
    """current F1=0.75, prior F1=0.85 → RegressionError raised."""
    with pytest.raises(RegressionError) as exc_info:
        check_regression(current_f1=0.75, prior_f1=0.85)
    assert exc_info.value.current_f1 == pytest.approx(0.75)
    assert exc_info.value.prior_f1 == pytest.approx(0.85)


def test_no_regression_when_within_threshold():
    """current F1=0.82, prior F1=0.85 → no error (drop is 3 pts < 5 pts)."""
    check_regression(current_f1=0.82, prior_f1=0.85)  # should not raise


def test_no_regression_when_improved():
    """current F1=0.90, prior F1=0.85 → no error."""
    check_regression(current_f1=0.90, prior_f1=0.85)  # should not raise


def test_no_regression_when_exactly_at_threshold():
    """current F1=0.80, prior F1=0.85 → exactly 5 pts drop → no error."""
    check_regression(current_f1=0.80, prior_f1=0.85)  # 5 pts drop is NOT > 5 pts


def test_regression_raises_when_just_over_threshold():
    """current F1=0.7999, prior F1=0.85 → just over 5 pts → raises."""
    with pytest.raises(RegressionError):
        check_regression(current_f1=0.7999, prior_f1=0.85)

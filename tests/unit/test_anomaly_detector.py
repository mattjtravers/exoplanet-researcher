"""T049 — Unit tests for anomaly_detector tool."""

import numpy as np

from src.tools.anomaly_detector import detect_anomaly


def _flat_lc(n: int = 1000):
    """Symmetric flat (non-anomalous) light curve."""
    rng = np.random.default_rng(42)
    time = np.linspace(0, 30, n).tolist()
    flux = (np.ones(n) + rng.normal(0, 0.0005, n)).tolist()
    flux_err = [0.0005] * n
    return time, flux, flux_err


def _transit_lc(period: float = 5.0, ingress_depth: float = 0.01, egress_depth: float = 0.01):
    """Synthetic transit light curve with controllable asymmetry."""
    rng = np.random.default_rng(0)
    n = 2000
    time = np.linspace(0, 30, n)
    flux = np.ones(n) + rng.normal(0, 0.0002, n)
    duration = 0.2  # days

    for center in np.arange(period, 30, period):
        half_dur = duration / 2.0
        # Ingress: first half of transit
        ingress_mask = (time >= center - half_dur) & (time < center)
        egress_mask = (time >= center) & (time < center + half_dur)
        flux[ingress_mask] -= ingress_depth
        flux[egress_mask] -= egress_depth

    flux_err = np.full(n, 0.0002)
    return time.tolist(), flux.tolist(), flux_err.tolist()


def test_symmetric_lc_returns_none():
    """Symmetric synthetic light curve → None returned (no anomaly)."""
    time, flux, flux_err = _flat_lc()
    result = detect_anomaly(
        time=time,
        flux=flux,
        flux_err=flux_err,
        quarter=1,
        sigma_threshold=2.0,
        transit_period=5.0,
        transit_duration=0.1,
    )
    assert result is None


def test_asymmetric_transit_returns_record():
    """Asymmetric transit (ingress >> egress) → AnomalyRecord with asymmetric_transit type."""
    # Make ingress very deep, egress shallow — exaggerated for test detectability
    time, flux, flux_err = _transit_lc(ingress_depth=0.05, egress_depth=0.001)
    result = detect_anomaly(
        time=time,
        flux=flux,
        flux_err=flux_err,
        quarter=3,
        sigma_threshold=1.0,  # low threshold to ensure detection
        transit_period=5.0,
        transit_duration=0.2,
    )
    # Either an asymmetric transit or aperiodicity record
    assert result is not None
    assert result.data_quarter == 3
    assert result.anomaly_type in ("asymmetric_transit", "aperiodicity")


def test_anomaly_record_has_correct_quarter():
    """Detected anomaly records the correct data_quarter."""
    time, flux, flux_err = _transit_lc(ingress_depth=0.05, egress_depth=0.001)
    result = detect_anomaly(
        time=time,
        flux=flux,
        flux_err=flux_err,
        quarter=7,
        sigma_threshold=1.0,
        transit_period=5.0,
        transit_duration=0.2,
    )
    if result is not None:
        assert result.data_quarter == 7


def test_no_period_returns_none():
    """Without transit period, anomaly detector returns None."""
    time, flux, flux_err = _flat_lc()
    result = detect_anomaly(
        time=time,
        flux=flux,
        flux_err=flux_err,
        quarter=1,
        sigma_threshold=2.0,
        transit_period=None,
        transit_duration=None,
    )
    assert result is None


def test_anomaly_record_has_nonempty_hypotheses():
    """Any returned AnomalyRecord must have non-empty hypotheses_searched."""
    time, flux, flux_err = _transit_lc(ingress_depth=0.05, egress_depth=0.001)
    result = detect_anomaly(
        time=time,
        flux=flux,
        flux_err=flux_err,
        quarter=1,
        sigma_threshold=1.0,
        transit_period=5.0,
        transit_duration=0.2,
    )
    if result is not None:
        assert len(result.hypotheses_searched) > 0

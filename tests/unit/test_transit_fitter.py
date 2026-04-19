"""T024 — Unit tests for transit_fitter tool."""


from src.tools.transit_fitter import fit_transit

# KIC-11442793 known approximate ephemeris (Kepler-90):
# Multiple planets; we use rough values for testing tolerance
_KNOWN_PERIOD_DAYS = 14.64  # approximate for one of the planets
_KNOWN_DEPTH = 0.003


def _make_synthetic_lc(period_days: float = 14.64, depth: float = 0.003):
    """Generate a synthetic light curve with a known transit signal."""
    import numpy as np

    rng = np.random.default_rng(0)
    n = 2000
    time = np.linspace(0, 100, n)
    flux = np.ones(n) + rng.normal(0, 0.0002, n)
    flux_err = np.full(n, 0.0002)

    # Inject transits
    for k in range(int(100 / period_days) + 1):
        center = k * period_days + 1.0
        mask = np.abs(time - center) < 0.1
        flux[mask] -= depth

    return time.tolist(), flux.tolist(), flux_err.tolist()


def test_transit_fitter_returns_period():
    time, flux, flux_err = _make_synthetic_lc()
    result = fit_transit(time=time, flux=flux, flux_err=flux_err, target_id="KIC-test")
    assert result.period_days > 0


def test_transit_fitter_period_within_5_percent():
    known_period = _KNOWN_PERIOD_DAYS
    time, flux, flux_err = _make_synthetic_lc(period_days=known_period)
    result = fit_transit(time=time, flux=flux, flux_err=flux_err, target_id="KIC-test")
    fitted = result.period_days
    relative_error = abs(fitted - known_period) / known_period
    assert relative_error < 0.05, (
        f"Period {fitted:.4f} not within 5% of known {known_period:.4f} "
        f"(error={relative_error:.1%})"
    )


def test_transit_fitter_depth_within_10_percent():
    known_depth = _KNOWN_DEPTH
    time, flux, flux_err = _make_synthetic_lc(depth=known_depth)
    result = fit_transit(time=time, flux=flux, flux_err=flux_err, target_id="KIC-test")
    fitted_depth = result.depth
    assert fitted_depth is not None
    relative_error = abs(fitted_depth - known_depth) / known_depth
    assert relative_error < 0.10, (
        f"Depth {fitted_depth:.5f} not within 10% of known {known_depth:.5f} "
        f"(error={relative_error:.1%})"
    )


def test_transit_fitter_returns_rp_rs():
    time, flux, flux_err = _make_synthetic_lc()
    result = fit_transit(time=time, flux=flux, flux_err=flux_err, target_id="KIC-test")
    assert result.rp_rs > 0


def test_transit_fitter_returns_tool_call_id():
    time, flux, flux_err = _make_synthetic_lc()
    result = fit_transit(time=time, flux=flux, flux_err=flux_err, target_id="KIC-test")
    assert len(result.tool_call_id) > 0


def test_transit_fitter_returns_duration():
    time, flux, flux_err = _make_synthetic_lc()
    result = fit_transit(time=time, flux=flux, flux_err=flux_err, target_id="KIC-test")
    assert result.duration_hours > 0

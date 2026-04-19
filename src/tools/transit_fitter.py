"""Transit fitter tool — BLS periodogram + transit parameter extraction."""

from __future__ import annotations

import math
import uuid

import numpy as np

from src.schemas.tools import TransitFitResult


def fit_transit(
    time: list[float],
    flux: list[float],
    flux_err: list[float],
    target_id: str,
    period_min: float = 0.5,
    period_max: float = 50.0,
) -> TransitFitResult:
    """Fit a transit model using BLS periodogram and extract key parameters.

    Args:
        time: Array of timestamps (BJD or phase-folded days).
        flux: Normalised flux values.
        flux_err: Flux uncertainties.
        target_id: Candidate identifier (used in lineage entries).
        period_min: Minimum trial period in days.
        period_max: Maximum trial period in days.

    Returns:
        TransitFitResult with period_days, depth, duration_hours, rp_rs, target_id, tool_call_id.
    """
    time_arr = np.asarray(time, dtype=float)
    flux_arr = np.asarray(flux, dtype=float)
    flux_err_arr = np.asarray(flux_err, dtype=float)

    # Use astropy's BLS implementation
    from astropy.timeseries import BoxLeastSquares

    # Build BLS model
    model = BoxLeastSquares(time_arr, flux_arr, dy=flux_err_arr)

    # Period grid
    n_periods = 5000
    periods = np.linspace(period_min, period_max, n_periods)

    # Duration grid: 0.5h to max 10h, must be < period_min
    max_duration_days = min(10.0 / 24.0, period_min * 0.9)
    durations = np.linspace(0.5 / 24.0, max_duration_days, 20)

    result = model.power(periods, durations, objective="snr")

    # Best period
    best_idx = np.argmax(result.power)
    best_period = float(result.period[best_idx])
    best_duration = float(result.duration[best_idx])
    best_t0 = float(result.transit_time[best_idx])

    # Compute depth: mean in-transit minus out-of-transit
    phase = (time_arr - best_t0) % best_period
    half_dur = best_duration / 2.0
    in_transit = (phase < half_dur) | (phase > best_period - half_dur)

    if in_transit.sum() == 0 or (~in_transit).sum() == 0:
        depth = 0.0
    else:
        depth = float(np.median(flux_arr[~in_transit]) - np.median(flux_arr[in_transit]))
        depth = max(depth, 0.0)

    # Rp/Rs from depth (depth ≈ (Rp/Rs)^2)
    rp_rs = math.sqrt(depth) if depth > 0 else 0.0

    return TransitFitResult(
        target_id=target_id,
        period_days=best_period,
        depth=depth,
        duration_hours=best_duration * 24.0,
        rp_rs=rp_rs,
        tool_call_id=str(uuid.uuid4()),
    )

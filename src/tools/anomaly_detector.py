"""Anomaly detector — BLS residuals for aperiodicity and ingress/egress asymmetry detection."""

from __future__ import annotations

import numpy as np

from src.schemas.report import AnomalyRecord


def detect_anomaly(
    time: list[float],
    flux: list[float],
    flux_err: list[float],
    quarter: int,
    sigma_threshold: float = 2.0,
    transit_period: float | None = None,
    transit_duration: float | None = None,
) -> AnomalyRecord | None:
    """Detect light curve anomalies: aperiodicity or asymmetric transits.

    Args:
        time: Timestamps (days).
        flux: Normalised flux values.
        flux_err: Flux uncertainties.
        quarter: Data quarter (for AnomalyRecord).
        sigma_threshold: Detection threshold in sigma units.
        transit_period: Best-fit transit period in days (from transit_fitter).
        transit_duration: Transit duration in days (from transit_fitter).

    Returns:
        AnomalyRecord if an anomaly is detected, None otherwise.
    """
    time_arr = np.asarray(time, dtype=float)
    flux_arr = np.asarray(flux, dtype=float)
    flux_err_arr = np.asarray(flux_err, dtype=float)

    if transit_period is None or transit_duration is None or transit_period <= 0:
        return None

    # --- Aperiodicity detection via BLS residuals ---
    # Phase-fold the light curve
    phase = (time_arr % transit_period) / transit_period  # 0..1

    # Identify in-transit and out-of-transit points
    transit_phase_width = transit_duration / transit_period
    in_transit = phase < transit_phase_width / 2.0

    if in_transit.sum() < 3:
        return None

    out_flux = flux_arr[~in_transit]
    out_baseline = np.median(out_flux)
    out_std = np.std(out_flux)

    # Check for scatter above the fitted model — indicative of aperiodicity
    # Compute expected in-transit flux
    in_transit_flux = flux_arr[in_transit]
    in_transit_time = time_arr[in_transit]

    if len(in_transit_flux) < 3:
        return None

    expected_depth = out_baseline - np.median(in_transit_flux)

    # Check asymmetry: compare ingress half vs egress half
    mid_idx = len(in_transit_time) // 2
    ingress_flux = in_transit_flux[:mid_idx]
    egress_flux = in_transit_flux[mid_idx:]

    if len(ingress_flux) < 2 or len(egress_flux) < 2:
        return None

    ingress_mean = float(np.mean(ingress_flux))
    egress_mean = float(np.mean(egress_flux))
    asymmetry = abs(ingress_mean - egress_mean)

    # Sigma of asymmetry relative to out-of-transit noise
    if out_std > 0:
        asymmetry_sigma = asymmetry / out_std
    else:
        asymmetry_sigma = 0.0

    if asymmetry_sigma >= sigma_threshold:
        return AnomalyRecord(
            anomaly_type="asymmetric_transit",
            data_quarter=quarter,
            description=(
                f"Ingress/egress asymmetry detected: asymmetry={asymmetry:.5f}, "
                f"sigma={asymmetry_sigma:.2f}σ (threshold={sigma_threshold}σ)."
            ),
            sigma_deviation=float(asymmetry_sigma),
            hypotheses_searched=["dust_disk", "comet_transit", "contamination"],
            literature_references=[],
        )

    # --- Aperiodicity check: residuals from periodic box model ---
    # Phase-fold and fit median box
    # Residuals after subtracting the box model
    box_model = np.where(in_transit, out_baseline - expected_depth, out_baseline)
    residuals = flux_arr - box_model
    residual_std = np.std(residuals)

    # Check if residuals show excess variance compared to flux_err
    expected_std = np.median(flux_err_arr)
    if expected_std > 0:
        excess_sigma = (residual_std - expected_std) / expected_std
    else:
        excess_sigma = 0.0

    if excess_sigma >= sigma_threshold:
        return AnomalyRecord(
            anomaly_type="aperiodicity",
            data_quarter=quarter,
            description=(
                f"Aperiodic signal detected: residual excess={excess_sigma:.2f}σ "
                f"above noise floor (threshold={sigma_threshold}σ)."
            ),
            sigma_deviation=float(excess_sigma),
            hypotheses_searched=["stellar_variability", "eclipsing_binary", "instrumental"],
            literature_references=[],
        )

    return None

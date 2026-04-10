"""MCP tool: get_light_curve — retrieve and detrend a light curve via lightkurve."""

from __future__ import annotations

import uuid
from typing import Literal

from src.errors import ArchiveConnectionError, ArchiveNotFoundError


def get_light_curve(
    target_id: str,
    quarter: int,
    mission: Literal["Kepler", "TESS"] = "Kepler",
) -> dict:
    """Retrieve and detrend the light curve for a given target and quarter.

    Args:
        target_id: KIC/TIC/TOI identifier (e.g. "KIC-11442793").
        quarter: Data quarter number (≥ 0).
        mission: Observing mission — "Kepler" or "TESS".

    Returns:
        Dict with keys: target_id, quarter, time, flux, flux_err, cadence, tool_call_id.

    Raises:
        ArchiveNotFoundError: If no data exists for this target/quarter.
        ArchiveConnectionError: If the archive is unreachable.
    """
    try:
        import lightkurve as lk
    except ImportError as exc:
        raise ArchiveConnectionError("lightkurve not installed") from exc

    try:
        # Build search expression
        search_term = target_id.replace("-", " ")
        if mission == "Kepler":
            results = lk.search_lightcurve(
                search_term,
                quarter=quarter,
                mission="Kepler",
                author="Kepler",
                exptime="long",
            )
        else:
            results = lk.search_lightcurve(
                search_term,
                sector=quarter,
                mission="TESS",
                exptime="long",
            )

        if len(results) == 0:
            raise ArchiveNotFoundError(f"No data for {target_id} Q{quarter}")

        lc = results[0].download()
        if lc is None:
            raise ArchiveNotFoundError(f"No data for {target_id} Q{quarter}")

        # Flatten (detrend) the light curve
        lc_flat = lc.normalize().flatten(window_length=401)
        time = lc_flat.time.value.tolist()
        flux = lc_flat.flux.value.tolist()
        flux_err = (
            lc_flat.flux_err.value.tolist()
            if lc_flat.flux_err is not None
            else [0.001] * len(time)
        )

        cadence = "short" if len(time) > 5000 else "long"

        return {
            "target_id": target_id,
            "quarter": quarter,
            "time": time,
            "flux": flux,
            "flux_err": flux_err,
            "cadence": cadence,
            "tool_call_id": str(uuid.uuid4()),
        }

    except (ArchiveNotFoundError, ArchiveConnectionError):
        raise
    except Exception as exc:
        error_msg = str(exc).lower()
        if any(kw in error_msg for kw in ["connection", "timeout", "network", "http"]):
            raise ArchiveConnectionError(str(exc)) from exc
        raise ArchiveNotFoundError(f"No data for {target_id} Q{quarter}") from exc

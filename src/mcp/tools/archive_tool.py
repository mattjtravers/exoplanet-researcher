"""MCP tool: get_stellar_properties — retrieve host star properties from NASA archive."""

from __future__ import annotations

import uuid

import requests

from src.errors import ArchiveConnectionError, ArchiveNotFoundError

_NASA_EXOPLANET_API = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"


def get_stellar_properties(target_id: str) -> dict:
    """Retrieve host star physical properties from the NASA Exoplanet Archive.

    Args:
        target_id: KIC/TIC/TOI identifier (e.g. "KIC-11442793").

    Returns:
        Dict with stellar properties and tool_call_id.

    Raises:
        ArchiveNotFoundError: If the target is not found.
        ArchiveConnectionError: If the archive is unreachable.
    """
    # Normalise the ID for the query
    kic_id = target_id.replace("KIC-", "").replace("KIC ", "").strip()

    query = (
        f"SELECT kepid,radius,mass,teff,logg,feh "
        f"FROM q1_q17_dr25_stellar "
        f"WHERE kepid={kic_id}"
    )

    try:
        response = requests.get(
            _NASA_EXOPLANET_API,
            params={"query": query, "format": "json"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.ConnectionError as exc:
        raise ArchiveConnectionError(str(exc)) from exc
    except requests.exceptions.Timeout as exc:
        raise ArchiveConnectionError(f"Request timed out: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise ArchiveConnectionError(str(exc)) from exc

    if not data:
        raise ArchiveNotFoundError(f"No stellar properties for {target_id}")

    row = data[0] if isinstance(data, list) and data else {}

    return {
        "target_id": target_id,
        "stellar_radius_rsun": row.get("radius"),
        "stellar_mass_msun": row.get("mass"),
        "stellar_teff_k": row.get("teff"),
        "log_g": row.get("logg"),
        "metallicity_dex": row.get("feh"),
        "source_catalog": "Kepler Stellar Properties Catalog DR25",
        "tool_call_id": str(uuid.uuid4()),
    }

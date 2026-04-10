"""Golden Dataset loader — downloads and validates the NASA KOI Cumulative Table."""

from __future__ import annotations

import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests

from src.schemas.benchmark import GoldenDataset, GoldenObject

_KOI_TAP_URL = (
    "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"
    "?query=select+kepid,koi_disposition+from+cumulative"
    "+where+koi_disposition+in+('CONFIRMED','FALSE+POSITIVE')"
    "&format=json"
)
_CACHE_PATH = Path("benchmarks") / "golden_dataset_cache.json"


def download_koi_table(min_confirmed: int = 20, min_false_positives: int = 20) -> GoldenDataset:
    """Download and validate the NASA KOI Cumulative Table.

    Args:
        min_confirmed: Minimum number of CONFIRMED objects required.
        min_false_positives: Minimum number of FALSE POSITIVE objects required.

    Returns:
        Validated GoldenDataset.

    Raises:
        RuntimeError: If the table cannot be downloaded or has insufficient objects.
    """
    try:
        response = requests.get(_KOI_TAP_URL, timeout=60)
        response.raise_for_status()
        rows = response.json()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Failed to download KOI table: {exc}") from exc

    confirmed = [r for r in rows if r.get("koi_disposition") == "CONFIRMED"]
    false_positives = [r for r in rows if r.get("koi_disposition") == "FALSE POSITIVE"]

    if len(confirmed) < min_confirmed:
        raise RuntimeError(
            f"Only {len(confirmed)} CONFIRMED objects; need at least {min_confirmed}"
        )
    if len(false_positives) < min_false_positives:
        raise RuntimeError(
            f"Only {len(false_positives)} FALSE POSITIVE objects; need at least {min_false_positives}"
        )

    # Build GoldenObject list (balanced: equal numbers)
    objects: list[GoldenObject] = []
    for row in confirmed[:min_confirmed]:
        kepid = str(row.get("kepid", ""))
        objects.append(GoldenObject(target_id=f"KIC-{kepid}", ground_truth="planet_candidate"))
    for row in false_positives[:min_false_positives]:
        kepid = str(row.get("kepid", ""))
        objects.append(GoldenObject(target_id=f"KIC-{kepid}", ground_truth="false_positive"))

    # Version: date + row count hash
    row_hash = hashlib.md5(str(len(rows)).encode()).hexdigest()[:8]
    version = f"{datetime.now(UTC).date()}-{row_hash}"

    dataset = GoldenDataset(
        dataset_version=version,
        source_table=f"NASA KOI Cumulative Table {datetime.now(UTC).date()}",
        objects=objects,
    )

    # Cache to disk
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    import json
    _CACHE_PATH.write_text(json.dumps(dataset.model_dump(mode="json"), default=str))

    return dataset


def load_cached_dataset() -> GoldenDataset | None:
    """Load the cached Golden Dataset from disk, or None if not available."""
    if not _CACHE_PATH.exists():
        return None
    import json
    data = json.loads(_CACHE_PATH.read_text())
    try:
        return GoldenDataset(**data)
    except Exception:
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialise the Golden Dataset.")
    parser.add_argument("--init", action="store_true", help="Download and cache the KOI table.")
    args = parser.parse_args()

    if args.init:
        print("Downloading KOI Cumulative Table from NASA Exoplanet Archive...")
        try:
            ds = download_koi_table()
            print(f"Golden Dataset ready: {len(ds.objects)} objects (version={ds.dataset_version})")
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

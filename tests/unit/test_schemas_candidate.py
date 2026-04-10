"""T005 — Unit tests for CandidateTarget schema."""

import pytest
from pydantic import ValidationError

from src.schemas.candidate import CandidateTarget


def _valid_candidate(**overrides) -> dict:
    base = {
        "target_id": "KIC-11442793",
        "catalog": "KIC",
        "available_quarters": [1, 2, 3],
    }
    base.update(overrides)
    return base


def test_valid_candidate():
    c = CandidateTarget(**_valid_candidate())
    assert c.target_id == "KIC-11442793"
    assert c.catalog == "KIC"


def test_invalid_catalog_literal_raises():
    with pytest.raises(ValidationError):
        CandidateTarget(**_valid_candidate(catalog="HIPPARCOS"))


def test_empty_target_id_raises():
    with pytest.raises(ValidationError):
        CandidateTarget(**_valid_candidate(target_id=""))


def test_whitespace_target_id_raises():
    with pytest.raises(ValidationError):
        CandidateTarget(**_valid_candidate(target_id="   "))


def test_negative_stellar_radius_raises():
    with pytest.raises(ValidationError):
        CandidateTarget(**_valid_candidate(stellar_radius_rsun=-1.0))


def test_zero_stellar_radius_raises():
    with pytest.raises(ValidationError):
        CandidateTarget(**_valid_candidate(stellar_radius_rsun=0.0))


def test_positive_stellar_radius_accepted():
    c = CandidateTarget(**_valid_candidate(stellar_radius_rsun=1.2))
    assert c.stellar_radius_rsun == 1.2


def test_negative_stellar_mass_raises():
    with pytest.raises(ValidationError):
        CandidateTarget(**_valid_candidate(stellar_mass_msun=-0.5))


def test_teff_below_range_raises():
    with pytest.raises(ValidationError):
        CandidateTarget(**_valid_candidate(stellar_teff_k=1000.0))


def test_teff_above_range_raises():
    with pytest.raises(ValidationError):
        CandidateTarget(**_valid_candidate(stellar_teff_k=70000.0))


def test_teff_in_range_accepted():
    c = CandidateTarget(**_valid_candidate(stellar_teff_k=5778.0))
    assert c.stellar_teff_k == 5778.0


def test_empty_available_quarters_raises():
    with pytest.raises(ValidationError):
        CandidateTarget(**_valid_candidate(available_quarters=[]))


def test_none_stellar_fields_accepted():
    c = CandidateTarget(**_valid_candidate())
    assert c.stellar_radius_rsun is None
    assert c.stellar_mass_msun is None
    assert c.stellar_teff_k is None


def test_tic_catalog_accepted():
    c = CandidateTarget(**_valid_candidate(target_id="TIC-12345", catalog="TIC"))
    assert c.catalog == "TIC"


def test_toi_catalog_accepted():
    c = CandidateTarget(**_valid_candidate(target_id="TOI-700", catalog="TOI"))
    assert c.catalog == "TOI"

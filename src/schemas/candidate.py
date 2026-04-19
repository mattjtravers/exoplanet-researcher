"""CandidateTarget schema — the exoplanet candidate submitted for vetting."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, field_validator

_TARGET_PATTERN = re.compile(r"^(KIC|TIC|TOI)-?\d+(\.\d+)?$")


class CandidateTarget(BaseModel):
    """The exoplanet candidate submitted for vetting."""

    target_id: str
    catalog: Literal["KIC", "TIC", "TOI"]
    stellar_radius_rsun: float | None = None
    stellar_mass_msun: float | None = None
    stellar_teff_k: float | None = None
    available_quarters: list[int]
    prior_disposition: str | None = None

    @field_validator("target_id")
    @classmethod
    def target_id_must_be_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("target_id must not be empty")
        return v

    @field_validator("stellar_radius_rsun")
    @classmethod
    def stellar_radius_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("stellar_radius_rsun must be > 0")
        return v

    @field_validator("stellar_mass_msun")
    @classmethod
    def stellar_mass_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("stellar_mass_msun must be > 0")
        return v

    @field_validator("stellar_teff_k")
    @classmethod
    def stellar_teff_range(cls, v: float | None) -> float | None:
        if v is not None and not (2000 <= v <= 60000):
            raise ValueError("stellar_teff_k must be between 2000 and 60000")
        return v

    @field_validator("available_quarters")
    @classmethod
    def available_quarters_nonempty(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("available_quarters must not be empty")
        return v

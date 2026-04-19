"""Typed return models for all XPI tool functions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LightCurveResult(BaseModel):
    """Return type for get_light_curve()."""

    target_id: str
    quarter: int
    time: list[float]
    flux: list[float]
    flux_err: list[float]
    cadence: Literal["short", "long"]
    tool_call_id: str


class StellarPropertiesResult(BaseModel):
    """Return type for get_stellar_properties()."""

    target_id: str
    stellar_radius_rsun: float | None
    stellar_mass_msun: float | None
    stellar_teff_k: float | None
    log_g: float | None
    metallicity_dex: float | None
    source_catalog: str
    tool_call_id: str


class TransitFitResult(BaseModel):
    """Return type for fit_transit()."""

    target_id: str
    period_days: float
    depth: float
    duration_hours: float
    rp_rs: float
    tool_call_id: str


class LiteraturePaper(BaseModel):
    """Single literature search result."""

    source_id: str
    abstract: str
    source_type: Literal["arxiv", "ads"]


class LiteratureSearchResult(BaseModel):
    """Aggregated result from iterative_search()."""

    papers: list[LiteraturePaper]
    queries_issued: list[str] = []

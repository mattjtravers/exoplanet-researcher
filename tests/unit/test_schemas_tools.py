"""T005 — Unit tests for tool result Pydantic models in src/schemas/tools.py."""

import pytest
from pydantic import ValidationError

from src.schemas.tools import (
    LightCurveResult,
    LiteraturePaper,
    LiteratureSearchResult,
    StellarPropertiesResult,
    TransitFitResult,
)

# ---------------------------------------------------------------------------
# LightCurveResult
# ---------------------------------------------------------------------------


def test_light_curve_result_construction():
    r = LightCurveResult(
        target_id="KIC-11442793",
        quarter=5,
        time=[1.0, 2.0, 3.0],
        flux=[1.0, 0.999, 1.001],
        flux_err=[0.001, 0.001, 0.001],
        cadence="long",
        tool_call_id="abc-123",
    )
    assert r.target_id == "KIC-11442793"
    assert r.quarter == 5
    assert r.cadence == "long"
    assert r.tool_call_id == "abc-123"


def test_light_curve_result_short_cadence():
    r = LightCurveResult(
        target_id="KIC-1",
        quarter=1,
        time=[float(i) for i in range(6000)],
        flux=[1.0] * 6000,
        flux_err=[0.001] * 6000,
        cadence="short",
        tool_call_id="x",
    )
    assert r.cadence == "short"


def test_light_curve_result_invalid_cadence():
    with pytest.raises(ValidationError):
        LightCurveResult(
            target_id="KIC-1",
            quarter=1,
            time=[1.0],
            flux=[1.0],
            flux_err=[0.001],
            cadence="medium",  # invalid
            tool_call_id="x",
        )


# ---------------------------------------------------------------------------
# StellarPropertiesResult
# ---------------------------------------------------------------------------


def test_stellar_properties_result_construction():
    r = StellarPropertiesResult(
        target_id="KIC-11442793",
        stellar_radius_rsun=1.2,
        stellar_mass_msun=1.1,
        stellar_teff_k=5800.0,
        log_g=4.4,
        metallicity_dex=0.1,
        source_catalog="Kepler Stellar Properties Catalog DR25",
        tool_call_id="abc-456",
    )
    assert r.stellar_radius_rsun == 1.2
    assert r.source_catalog == "Kepler Stellar Properties Catalog DR25"


def test_stellar_properties_result_nullable_fields():
    r = StellarPropertiesResult(
        target_id="KIC-99",
        stellar_radius_rsun=None,
        stellar_mass_msun=None,
        stellar_teff_k=None,
        log_g=None,
        metallicity_dex=None,
        source_catalog="unknown",
        tool_call_id="x",
    )
    assert r.stellar_radius_rsun is None
    assert r.log_g is None


# ---------------------------------------------------------------------------
# TransitFitResult
# ---------------------------------------------------------------------------


def test_transit_fit_result_construction():
    r = TransitFitResult(
        target_id="KIC-11442793",
        period_days=14.64,
        depth=0.003,
        duration_hours=3.5,
        rp_rs=0.0548,
        tool_call_id="abc-789",
    )
    assert r.period_days == 14.64
    assert r.depth == 0.003
    assert r.rp_rs == pytest.approx(0.0548, rel=1e-5)


def test_transit_fit_result_attribute_access():
    r = TransitFitResult(
        target_id="T",
        period_days=1.0,
        depth=0.001,
        duration_hours=2.0,
        rp_rs=0.03,
        tool_call_id="id",
    )
    assert hasattr(r, "period_days")
    assert hasattr(r, "depth")
    assert hasattr(r, "duration_hours")
    assert hasattr(r, "rp_rs")
    assert hasattr(r, "tool_call_id")


def test_transit_fit_result_invalid_type():
    with pytest.raises(ValidationError):
        TransitFitResult(
            target_id="T",
            period_days="not-a-float",  # invalid
            depth=0.001,
            duration_hours=2.0,
            rp_rs=0.03,
            tool_call_id="id",
        )


# ---------------------------------------------------------------------------
# LiteraturePaper
# ---------------------------------------------------------------------------


def test_literature_paper_arxiv():
    p = LiteraturePaper(source_id="2301.12345", abstract="An exoplanet study.", source_type="arxiv")
    assert p.source_type == "arxiv"
    assert p.source_id == "2301.12345"


def test_literature_paper_ads():
    p = LiteraturePaper(source_id="2023ApJ...001A", abstract="ADS abstract.", source_type="ads")
    assert p.source_type == "ads"


def test_literature_paper_invalid_source_type():
    with pytest.raises(ValidationError):
        LiteraturePaper(source_id="x", abstract="y", source_type="pubmed")  # invalid


# ---------------------------------------------------------------------------
# LiteratureSearchResult
# ---------------------------------------------------------------------------


def test_literature_search_result_construction():
    papers = [
        LiteraturePaper(source_id="2301.00001", abstract="Abstract A", source_type="arxiv"),
        LiteraturePaper(source_id="2023ApJ.001", abstract="Abstract B", source_type="ads"),
    ]
    r = LiteratureSearchResult(papers=papers, queries_issued=["query1", "query2"])
    assert len(r.papers) == 2
    assert r.queries_issued == ["query1", "query2"]


def test_literature_search_result_empty():
    r = LiteratureSearchResult(papers=[])
    assert r.papers == []
    assert r.queries_issued == []


def test_literature_search_result_paper_attribute_access():
    r = LiteratureSearchResult(
        papers=[LiteraturePaper(source_id="id1", abstract="abc", source_type="arxiv")],
        queries_issued=["q"],
    )
    assert r.papers[0].source_id == "id1"
    assert r.papers[0].abstract == "abc"
    assert r.papers[0].source_type == "arxiv"

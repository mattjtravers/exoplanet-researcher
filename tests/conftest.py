"""Shared fixtures for XPI test suite."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

from src.schemas.candidate import CandidateTarget
from src.schemas.confidence import ConfidenceAssessment
from src.schemas.config import AgentConfig


@pytest.fixture
def sample_candidate() -> CandidateTarget:
    """A valid CandidateTarget for KIC-11442793 (confirmed planet host)."""
    return CandidateTarget(
        target_id="KIC-11442793",
        catalog="KIC",
        stellar_radius_rsun=1.2,
        stellar_mass_msun=1.1,
        stellar_teff_k=5850.0,
        available_quarters=list(range(1, 18)),
        prior_disposition="CONFIRMED",
    )


@pytest.fixture
def sample_observer_config() -> AgentConfig:
    return AgentConfig(token_budget=8000, anomaly_sigma_threshold=2.0)


@pytest.fixture
def sample_scholar_config() -> AgentConfig:
    return AgentConfig(token_budget=16000, max_iterations=3)


@pytest.fixture
def sample_synthesizer_config() -> AgentConfig:
    return AgentConfig(token_budget=12000, conflict_threshold=30.0, max_correction_iterations=2)


@pytest.fixture
def sample_observer_confidence() -> ConfidenceAssessment:
    return ConfidenceAssessment(
        agent="observer",
        score=85.0,
        disposition="planet_candidate",
        primary_evidence=["Q1", "Q2"],
        reasoning_summary="Strong periodic transit detected with depth consistent with Jupiter-sized planet.",
    )


@pytest.fixture
def sample_scholar_confidence() -> ConfidenceAssessment:
    return ConfidenceAssessment(
        agent="scholar",
        score=78.0,
        disposition="planet_candidate",
        primary_evidence=["arxiv:1234.5678"],
        reasoning_summary="Multiple papers confirm planetary nature with radial velocity follow-up.",
    )


@pytest.fixture
def synthetic_flat_lc():
    """A synthetic flat (non-transit) light curve for anomaly detection tests."""
    rng = np.random.default_rng(42)
    time = np.linspace(0, 30, 1000)
    flux = np.ones(1000) + rng.normal(0, 0.001, 1000)
    flux_err = np.full(1000, 0.001)
    return time, flux, flux_err


@pytest.fixture
def synthetic_transit_lc():
    """A synthetic symmetric transit light curve."""
    rng = np.random.default_rng(42)
    time = np.linspace(0, 30, 1000)
    flux = np.ones(1000) + rng.normal(0, 0.0005, 1000)
    # Inject symmetric transits every ~5 days, depth 0.01
    for center in [5.0, 10.0, 15.0, 20.0, 25.0]:
        mask = np.abs(time - center) < 0.15
        flux[mask] -= 0.01
    flux_err = np.full(1000, 0.0005)
    return time, flux, flux_err


@pytest.fixture
def utcnow() -> datetime:
    return datetime.now(UTC)

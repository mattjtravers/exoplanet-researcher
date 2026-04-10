"""T007 — Unit tests for ConfidenceAssessment schema."""

import pytest
from pydantic import ValidationError

from src.schemas.confidence import ConfidenceAssessment


def _valid_confidence(**overrides) -> dict:
    base = {
        "agent": "observer",
        "score": 75.0,
        "disposition": "planet_candidate",
        "primary_evidence": ["Q1", "Q2"],
        "reasoning_summary": "Strong periodic transit signal detected.",
    }
    base.update(overrides)
    return base


def test_valid_confidence():
    c = ConfidenceAssessment(**_valid_confidence())
    assert c.score == 75.0


def test_score_above_100_raises():
    with pytest.raises(ValidationError):
        ConfidenceAssessment(**_valid_confidence(score=100.1))


def test_score_below_0_raises():
    with pytest.raises(ValidationError):
        ConfidenceAssessment(**_valid_confidence(score=-0.1))


def test_score_exactly_0_accepted():
    c = ConfidenceAssessment(**_valid_confidence(score=0.0))
    assert c.score == 0.0


def test_score_exactly_100_accepted():
    c = ConfidenceAssessment(**_valid_confidence(score=100.0))
    assert c.score == 100.0


def test_empty_primary_evidence_raises():
    with pytest.raises(ValidationError):
        ConfidenceAssessment(**_valid_confidence(primary_evidence=[]))


def test_empty_reasoning_summary_raises():
    with pytest.raises(ValidationError):
        ConfidenceAssessment(**_valid_confidence(reasoning_summary=""))


def test_invalid_agent_raises():
    with pytest.raises(ValidationError):
        ConfidenceAssessment(**_valid_confidence(agent="validator"))


def test_invalid_disposition_raises():
    with pytest.raises(ValidationError):
        ConfidenceAssessment(**_valid_confidence(disposition="unknown"))


def test_scholar_agent_accepted():
    c = ConfidenceAssessment(**_valid_confidence(agent="scholar"))
    assert c.agent == "scholar"

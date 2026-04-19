"""T044 — Unit tests for Synthesizer conflict detection."""

import pytest
from pydantic import ValidationError

from src.agents.observer import ObserverOutput
from src.agents.scholar import ScholarOutput
from src.agents.synthesizer import SynthesizerAgent
from src.schemas.confidence import ConfidenceAssessment
from src.schemas.config import AgentConfig
from src.schemas.report import ConsensusConflictFlag


def _make_observer_output(score: float = 85.0, disposition: str = "planet_candidate"):
    return ObserverOutput(
        confidence=ConfidenceAssessment(
            agent="observer",
            score=score,
            disposition=disposition,
            primary_evidence=["Q1"],
            reasoning_summary="Transit detected.",
        ),
        lineage_partial=[],
        anomaly_records=[],
    )


def _make_scholar_output(score: float = 15.0, disposition: str = "false_positive"):
    return ScholarOutput(
        confidence=ConfidenceAssessment(
            agent="scholar",
            score=score,
            disposition=disposition,
            primary_evidence=["arxiv:0001"],
            reasoning_summary="Literature suggests EB.",
        ),
        distilled_records=[],
        queries_issued=["query1"],
        lineage_partial=[],
    )


def _make_config(conflict_threshold: float = 30.0, max_correction_iterations: int = 2) -> AgentConfig:
    return AgentConfig(
        token_budget=12000,
        conflict_threshold=conflict_threshold,
        max_correction_iterations=max_correction_iterations,
    )


def test_large_divergence_emits_conflict_flag():
    """Observer 85% + Scholar 15% → ConsensusConflictFlag emitted."""
    agent = SynthesizerAgent(config=_make_config(conflict_threshold=30.0))
    obs = _make_observer_output(score=85.0)
    sch = _make_scholar_output(score=15.0)
    result = agent.run(observer_output=obs, scholar_output=sch)
    assert result.conflict_flag is not None
    assert result.conflict_flag.divergence == pytest.approx(70.0, abs=0.1)
    assert result.consensus_confidence is None


def test_small_divergence_no_conflict_flag():
    """Observer 80% + Scholar 75% → no conflict flag."""
    agent = SynthesizerAgent(config=_make_config(conflict_threshold=30.0))
    obs = _make_observer_output(score=80.0, disposition="planet_candidate")
    sch = _make_scholar_output(score=75.0, disposition="planet_candidate")
    result = agent.run(observer_output=obs, scholar_output=sch)
    assert result.conflict_flag is None
    assert result.consensus_confidence is not None
    assert result.consensus_confidence == pytest.approx(77.5, abs=0.1)


def test_conflict_flag_has_correct_divergence():
    """Emitted flag includes correct divergence value."""
    agent = SynthesizerAgent(config=_make_config(conflict_threshold=30.0))
    obs = _make_observer_output(score=85.0)
    sch = _make_scholar_output(score=15.0)
    result = agent.run(observer_output=obs, scholar_output=sch)
    flag = result.conflict_flag
    assert flag is not None
    assert flag.divergence == pytest.approx(abs(85.0 - 15.0), abs=0.1)
    assert flag.threshold_used == pytest.approx(30.0)


def test_conflict_flag_missing_conflict_summary_raises():
    """ConsensusConflictFlag with empty conflict_summary raises ValidationError."""
    obs_conf = ConfidenceAssessment(
        agent="observer", score=85.0, disposition="planet_candidate",
        primary_evidence=["Q1"], reasoning_summary="Transit."
    )
    sch_conf = ConfidenceAssessment(
        agent="scholar", score=15.0, disposition="false_positive",
        primary_evidence=["arxiv:001"], reasoning_summary="EB."
    )
    with pytest.raises(ValidationError):
        ConsensusConflictFlag(
            observer_assessment=obs_conf,
            scholar_assessment=sch_conf,
            divergence=70.0,
            threshold_used=30.0,
            conflict_summary="",  # empty — must raise
            resolved=False,
        )


def test_reasoning_trace_is_nonempty():
    """SynthesizerOutput always has a non-empty reasoning trace."""
    agent = SynthesizerAgent(config=_make_config())
    obs = _make_observer_output(score=80.0, disposition="planet_candidate")
    sch = _make_scholar_output(score=75.0, disposition="planet_candidate")
    result = agent.run(observer_output=obs, scholar_output=sch)
    assert len(result.reasoning_trace) > 0


def test_exactly_one_of_confidence_or_conflict():
    """Exactly one of consensus_confidence or conflict_flag must be non-None."""
    agent = SynthesizerAgent(config=_make_config())
    obs = _make_observer_output(score=85.0)
    sch = _make_scholar_output(score=15.0)
    result = agent.run(observer_output=obs, scholar_output=sch)
    has_confidence = result.consensus_confidence is not None
    has_conflict = result.conflict_flag is not None
    assert has_confidence != has_conflict

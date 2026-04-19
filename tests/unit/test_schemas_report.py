"""T008 — Unit tests for ConsensusConflictFlag, AnomalyRecord, VettingReport."""

import pytest
from pydantic import ValidationError

from src.schemas.confidence import ConfidenceAssessment
from src.schemas.report import (
    AnomalyRecord,
    ConsensusConflictFlag,
    ReasoningStep,
    ValidatorResult,
    VettingReport,
)


def _observer_confidence():
    return ConfidenceAssessment(
        agent="observer",
        score=85.0,
        disposition="planet_candidate",
        primary_evidence=["Q1"],
        reasoning_summary="Strong transit.",
    )


def _scholar_confidence():
    return ConfidenceAssessment(
        agent="scholar",
        score=20.0,
        disposition="false_positive",
        primary_evidence=["arxiv:0001"],
        reasoning_summary="Literature suggests EB.",
    )


def _valid_conflict_flag(**overrides) -> dict:
    base = {
        "observer_assessment": _observer_confidence(),
        "scholar_assessment": _scholar_confidence(),
        "divergence": 65.0,
        "threshold_used": 30.0,
        "conflict_summary": "Observer and Scholar diverge by 65 points.",
        "resolved": False,
    }
    base.update(overrides)
    return base


def _valid_report_base() -> dict:
    return {
        "target_id": "KIC-11442793",
        "disposition": "planet_candidate",
        "reasoning_trace": [
            ReasoningStep(step_number=1, agent="observer", conclusion="Transit detected.")
        ],
        "validator_result": ValidatorResult(passed=True),
        "lineage_map_path": "outputs/KIC-11442793/lineage_map.json",
        "light_curve_chart_path": "outputs/KIC-11442793/light_curve.png",
        "interpretive_description": "The light curve shows periodic dimming.",
    }


# --- ConsensusConflictFlag tests ---

def test_valid_conflict_flag():
    f = ConsensusConflictFlag(**_valid_conflict_flag())
    assert f.divergence == 65.0
    assert not f.resolved


def test_conflict_flag_missing_conflict_summary_raises():
    with pytest.raises(ValidationError):
        ConsensusConflictFlag(**_valid_conflict_flag(conflict_summary=""))


def test_conflict_flag_negative_divergence_raises():
    with pytest.raises(ValidationError):
        ConsensusConflictFlag(**_valid_conflict_flag(divergence=-1.0))


def test_conflict_flag_zero_threshold_raises():
    with pytest.raises(ValidationError):
        ConsensusConflictFlag(**_valid_conflict_flag(threshold_used=0.0))


# --- AnomalyRecord tests ---

def test_valid_anomaly_record():
    a = AnomalyRecord(
        anomaly_type="asymmetric_transit",
        data_quarter=3,
        description="Ingress longer than egress by 3σ.",
        sigma_deviation=3.1,
        hypotheses_searched=["dust_disk", "eclipsing_binary"],
    )
    assert a.anomaly_type == "asymmetric_transit"


def test_anomaly_record_empty_hypotheses_raises():
    with pytest.raises(ValidationError):
        AnomalyRecord(
            anomaly_type="aperiodicity",
            data_quarter=1,
            description="Irregular timing.",
            sigma_deviation=2.5,
            hypotheses_searched=[],
        )


def test_anomaly_record_negative_quarter_raises():
    with pytest.raises(ValidationError):
        AnomalyRecord(
            anomaly_type="aperiodicity",
            data_quarter=-1,
            description="Irregular timing.",
            sigma_deviation=2.5,
            hypotheses_searched=["stellar_variability"],
        )


# --- VettingReport mutual exclusion tests ---

def test_vetting_report_both_null_raises():
    """Both consensus_confidence and conflict_flag null must raise."""
    base = _valid_report_base()
    # Neither set — should raise
    with pytest.raises(ValidationError):
        VettingReport(**base)


def test_vetting_report_both_nonnull_raises():
    """Both consensus_confidence and conflict_flag set must raise."""
    base = _valid_report_base()
    base["consensus_confidence"] = 80.0
    base["conflict_flag"] = ConsensusConflictFlag(**_valid_conflict_flag())
    with pytest.raises(ValidationError):
        VettingReport(**base)


def test_vetting_report_only_confidence():
    base = _valid_report_base()
    base["consensus_confidence"] = 80.0
    r = VettingReport(**base)
    assert r.consensus_confidence == 80.0
    assert r.conflict_flag is None


def test_vetting_report_only_conflict_flag():
    base = _valid_report_base()
    base["conflict_flag"] = ConsensusConflictFlag(**_valid_conflict_flag())
    r = VettingReport(**base)
    assert r.conflict_flag is not None
    assert r.consensus_confidence is None


def test_vetting_report_empty_reasoning_trace_raises():
    base = _valid_report_base()
    base["consensus_confidence"] = 80.0
    base["reasoning_trace"] = []
    with pytest.raises(ValidationError):
        VettingReport(**base)

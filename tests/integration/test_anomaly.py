"""T050 — Integration test: anomaly detection for known asymmetric transit."""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="Requires network access and full pipeline")
def test_asymmetric_transit_koi_produces_anomaly_record():
    """Known asymmetric-transit KOI → report contains AnomalyRecord."""
    from src.dag.pipeline import run_pipeline

    # KIC-12557548 is known for asymmetric transit (disintegrating planet / dust disk)
    state = run_pipeline(target_id="KIC-12557548", catalog="KIC")
    assert state.get("error") is None

    report = state.get("vetting_report")
    assert report is not None

    # Should detect at least one anomaly
    assert len(report.anomaly_records) > 0, "Expected at least one AnomalyRecord for KIC-12557548"

    anomaly = report.anomaly_records[0]
    assert anomaly.anomaly_type in ("asymmetric_transit", "aperiodicity")
    assert len(anomaly.hypotheses_searched) > 0

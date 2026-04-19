"""T025 — Integration test skeleton for the basic pipeline (US1).

This test is intentionally marked with pytest.mark.integration so it is skipped
in fast/unit-only CI runs. It requires network access to the NASA archive.
"""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="Pipeline not yet wired — confirm red before T036")
def test_known_confirmed_planet_produces_vetting_report():
    """Known confirmed planet KIC-11442793 should produce a valid VettingReport."""
    from src.dag.pipeline import run_pipeline

    state = run_pipeline(target_id="KIC-11442793", catalog="KIC")

    assert state.get("error") is None, f"Pipeline error: {state.get('error')}"
    report = state.get("vetting_report")
    assert report is not None, "No VettingReport in state"
    assert report.disposition == "planet_candidate"
    assert len(report.reasoning_trace) > 0
    assert report.light_curve_chart_path
    import os
    assert os.path.exists(report.light_curve_chart_path) or report.light_curve_chart_path.startswith(
        "outputs/"
    )

"""T045 — Integration test: conflict detection for known eclipsing binary."""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="Requires network access and full pipeline")
def test_eclipsing_binary_produces_conflict_flag():
    """Known eclipsing binary KOI → report contains ConsensusConflictFlag."""
    from src.dag.pipeline import run_pipeline

    # KIC-3861595 is a known eclipsing binary (KOI false positive)
    state = run_pipeline(target_id="KIC-3861595", catalog="KIC")
    assert state.get("error") is None

    report = state.get("vetting_report")
    assert report is not None

    # Either a conflict flag OR a false_positive disposition expected
    has_conflict = report.conflict_flag is not None
    is_fp = report.disposition == "false_positive"
    assert has_conflict or is_fp, "Expected conflict flag or false_positive disposition for known EB"

    if has_conflict:
        flag = report.conflict_flag
        assert flag.conflict_summary
        assert flag.observer_assessment is not None
        assert flag.scholar_assessment is not None

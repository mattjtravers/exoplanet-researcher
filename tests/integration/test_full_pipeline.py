"""T065 — End-to-end integration test: known anomaly AND known conflict."""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="Requires network access and full pipeline — confirm all user stories first")
def test_full_pipeline_produces_all_artefacts():
    """One Golden Dataset object → report, lineage map, and PNG all written.

    Verifies:
    - VettingReport schema validates
    - Lineage Map passes JSON Schema validation
    - PNG file exists
    - All output files written to outputs/
    """
    import json
    from pathlib import Path

    import jsonschema

    from src.dag.pipeline import run_pipeline

    state = run_pipeline(target_id="KIC-11442793", catalog="KIC")
    assert state.get("error") is None

    report = state.get("vetting_report")
    assert report is not None

    # Lineage Map validation
    lineage_path = Path(report.lineage_map_path)
    assert lineage_path.exists()
    schema_path = Path("specs/001-xpi-agentic-vetting/contracts/lineage-map-schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    with open(lineage_path) as f:
        lineage_data = json.load(f)
    jsonschema.validate(lineage_data, schema)

    # PNG exists
    chart_path = Path(report.light_curve_chart_path)
    assert chart_path.exists()

    # Report.md exists
    report_md = Path(f"outputs/{report.target_id}/report.md")
    assert report_md.exists()

    # Mandatory sections present
    from src.tools.report_generator import validate_report
    assert validate_report(report_md)

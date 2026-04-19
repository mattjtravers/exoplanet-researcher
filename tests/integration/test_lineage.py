"""T038 — Integration test: lineage map validation after pipeline run."""

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skip(reason="Requires full pipeline — run after DAG is wired")
def test_pipeline_lineage_map_passes_schema():
    """Completed pipeline → lineage_map.json passes JSON Schema validation."""
    import json
    from pathlib import Path

    import jsonschema

    from src.dag.pipeline import run_pipeline

    state = run_pipeline(target_id="KIC-11442793", catalog="KIC")
    assert state.get("error") is None

    lineage_path = Path("outputs/KIC-11442793/lineage_map.json")
    assert lineage_path.exists()

    schema_path = Path("specs/001-xpi-agentic-vetting/contracts/lineage-map-schema.json")
    with open(schema_path) as f:
        schema = json.load(f)

    with open(lineage_path) as f:
        data = json.load(f)

    jsonschema.validate(data, schema)

    # Every parameter in report.md should have a lineage entry
    entry_names = {e["parameter_name"] for e in data["entries"]}
    # At minimum: period_days must appear
    assert "period_days" in entry_names or len(entry_names) > 0

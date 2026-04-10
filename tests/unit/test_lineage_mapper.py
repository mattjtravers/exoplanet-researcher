"""T037 — Unit tests for lineage_mapper tool."""

import json
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from src.schemas.lineage import ConfidenceLineageEntry, LineageEntry, LineageMap
from src.tools.lineage_mapper import _validate_against_schema

SCHEMA_PATH = Path("specs/001-xpi-agentic-vetting/contracts/lineage-map-schema.json")


def _make_entry(parameter_name: str = "period_days", **kwargs) -> LineageEntry:
    base = dict(
        parameter_name=parameter_name,
        parameter_value=5.76,
        tool_call_id="tc-001",
        source_id="Q1",
        source_type="nasa_quarter",
        agent="observer",
    )
    base.update(kwargs)
    return LineageEntry(**base)


def _make_conf_entry(agent: str = "observer") -> ConfidenceLineageEntry:
    return ConfidenceLineageEntry(
        agent=agent,
        score=80.0,
        disposition="planet_candidate",
        primary_evidence=["Q1"],
    )


def test_lineage_map_missing_source_id_fails_schema():
    """LineageMap with a blank source_id should fail schema validation."""
    with pytest.raises(ValidationError):
        LineageEntry(
            parameter_name="period_days",
            parameter_value=5.76,
            tool_call_id="tc-001",
            source_id="",  # empty — should raise
            source_type="nasa_quarter",
            agent="observer",
        )


def test_lineage_map_valid_passes_json_schema():
    """A properly built LineageMap passes JSON Schema validation."""
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    m = LineageMap(
        target_id="KIC-11442793",
        entries=[_make_entry()],
        confidence_entries=[_make_conf_entry("observer"), _make_conf_entry("scholar")],
    )
    data = json.loads(json.dumps(m.to_json_ld(), default=str))
    jsonschema.validate(data, schema)  # should not raise


def test_merged_map_from_two_partials_has_correct_count():
    """Merged map from two partials has the expected total entry count."""
    partial_a = [_make_entry(f"param_a_{i}") for i in range(3)]
    partial_b = [_make_entry(f"param_b_{i}") for i in range(4)]
    all_entries = partial_a + partial_b
    conf = [_make_conf_entry("observer")]

    m = LineageMap(
        target_id="KIC-test",
        entries=all_entries,
        confidence_entries=conf,
    )
    assert len(m.entries) == 7


def test_lineage_map_validate_against_schema_passes():
    """_validate_against_schema does not raise for a valid map."""
    m = LineageMap(
        target_id="KIC-test",
        entries=[_make_entry()],
        confidence_entries=[_make_conf_entry("observer"), _make_conf_entry("scholar")],
    )
    _validate_against_schema(m)  # should not raise


def test_to_json_ld_uses_at_context():
    m = LineageMap(
        target_id="KIC-test",
        entries=[_make_entry()],
        confidence_entries=[_make_conf_entry()],
    )
    data = m.to_json_ld()
    assert "@context" in data
    assert data["@context"] == "https://xpi.science/lineage/v1"

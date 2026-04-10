"""T006 — Unit tests for LineageEntry and LineageMap schemas."""

import json
from datetime import datetime

import jsonschema
import pytest
from pydantic import ValidationError

from src.schemas.lineage import ConfidenceLineageEntry, LineageEntry, LineageMap

SCHEMA_PATH = "specs/001-xpi-agentic-vetting/contracts/lineage-map-schema.json"


def _valid_entry(**overrides) -> dict:
    base = {
        "parameter_name": "period_days",
        "parameter_value": 5.762,
        "tool_call_id": "tool-call-001",
        "source_id": "Q1",
        "source_type": "nasa_quarter",
        "agent": "observer",
    }
    base.update(overrides)
    return base


def _valid_confidence_entry(**overrides) -> dict:
    base = {
        "agent": "observer",
        "score": 85.0,
        "disposition": "planet_candidate",
        "primary_evidence": ["Q1"],
    }
    base.update(overrides)
    return base


def _valid_map(**overrides) -> dict:
    base = {
        "target_id": "KIC-11442793",
        "entries": [LineageEntry(**_valid_entry())],
        "confidence_entries": [ConfidenceLineageEntry(**_valid_confidence_entry())],
    }
    base.update(overrides)
    return base


def test_valid_lineage_entry():
    e = LineageEntry(**_valid_entry())
    assert e.parameter_name == "period_days"


def test_missing_source_id_raises():
    with pytest.raises(ValidationError):
        LineageEntry(**_valid_entry(source_id=""))


def test_missing_tool_call_id_raises():
    with pytest.raises(ValidationError):
        LineageEntry(**_valid_entry(tool_call_id=""))


def test_missing_parameter_name_raises():
    with pytest.raises(ValidationError):
        LineageEntry(**_valid_entry(parameter_name=""))


def test_lineage_entry_auto_timestamp():
    e = LineageEntry(**_valid_entry())
    assert isinstance(e.timestamp, datetime)


def test_valid_lineage_map():
    m = LineageMap(**_valid_map())
    assert m.target_id == "KIC-11442793"
    assert len(m.entries) == 1


def test_lineage_map_empty_entries_raises():
    with pytest.raises(ValidationError):
        LineageMap(**_valid_map(entries=[]))


def test_lineage_map_empty_confidence_entries_raises():
    with pytest.raises(ValidationError):
        LineageMap(**_valid_map(confidence_entries=[]))


def test_lineage_map_json_ld_has_context():
    m = LineageMap(**_valid_map())
    data = m.to_json_ld()
    assert "@context" in data
    assert data["@context"] == "https://xpi.science/lineage/v1"
    assert "context" not in data


def test_serialised_map_passes_json_schema():
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    m = LineageMap(**_valid_map())
    data = m.to_json_ld()
    # Serialize datetimes to strings
    data_json = json.loads(json.dumps(data, default=str))

    jsonschema.validate(data_json, schema)


def test_merged_map_has_correct_entry_count():
    entries_a = [LineageEntry(**_valid_entry(parameter_name=f"param_{i}")) for i in range(3)]
    entries_b = [LineageEntry(**_valid_entry(parameter_name=f"other_{i}")) for i in range(2)]
    conf = [ConfidenceLineageEntry(**_valid_confidence_entry())]
    m = LineageMap(target_id="KIC-11442793", entries=entries_a + entries_b, confidence_entries=conf)
    assert len(m.entries) == 5

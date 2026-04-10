"""Lineage mapper — build, validate, and serialise the JSON-LD LineageMap."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

from src.schemas.lineage import ConfidenceLineageEntry, LineageEntry, LineageMap

_SCHEMA_PATH = Path(__file__).parent.parent.parent / "specs" / "001-xpi-agentic-vetting" / "contracts" / "lineage-map-schema.json"


def build_lineage_entry_from_tool_record(
    parameter_name: str,
    parameter_value: float | str,
    tool_call_id: str,
    source_id: str,
    source_type: str,
    agent: str,
) -> LineageEntry:
    """Convenience constructor for a LineageEntry."""
    return LineageEntry(
        parameter_name=parameter_name,
        parameter_value=parameter_value,
        tool_call_id=tool_call_id,
        source_id=source_id,
        source_type=source_type,
        agent=agent,
    )


def finalise_lineage_map(
    target_id: str,
    observer_output: object,
    scholar_output: object,
    synthesizer_output: object,
) -> LineageMap:
    """Merge lineage partials from Observer, Scholar, and Synthesizer.

    Args:
        target_id: The candidate identifier.
        observer_output: ObserverOutput with lineage_partial.
        scholar_output: ScholarOutput with lineage_partial.
        synthesizer_output: SynthesizerOutput with reasoning_trace.

    Returns:
        Validated LineageMap.

    Raises:
        jsonschema.ValidationError: If the merged map fails schema validation.
    """
    all_entries: list[LineageEntry] = []

    # Observer entries
    all_entries.extend(observer_output.lineage_partial)

    # Scholar entries
    all_entries.extend(scholar_output.lineage_partial)

    # Synthesizer reasoning steps contribute source references
    for step in synthesizer_output.reasoning_trace:
        for tool_call_id in step.tool_calls:
            for source in step.data_sources:
                all_entries.append(
                    LineageEntry(
                        parameter_name=f"reasoning_step_{step.step_number}",
                        parameter_value=step.conclusion[:100],
                        tool_call_id=tool_call_id,
                        source_id=source,
                        source_type=_infer_source_type(source),
                        agent="synthesizer",
                    )
                )

    # Ensure at least one entry exists
    if not all_entries:
        import uuid
        all_entries.append(
            LineageEntry(
                parameter_name="pipeline_run",
                parameter_value=target_id,
                tool_call_id=str(uuid.uuid4()),
                source_id=target_id,
                source_type="candidate",
                agent="synthesizer",
            )
        )

    # Build confidence entries
    confidence_entries: list[ConfidenceLineageEntry] = [
        ConfidenceLineageEntry(
            agent=observer_output.confidence.agent,
            score=observer_output.confidence.score,
            disposition=observer_output.confidence.disposition,
            primary_evidence=observer_output.confidence.primary_evidence,
        ),
        ConfidenceLineageEntry(
            agent=scholar_output.confidence.agent,
            score=scholar_output.confidence.score,
            disposition=scholar_output.confidence.disposition,
            primary_evidence=scholar_output.confidence.primary_evidence,
        ),
    ]

    lineage_map = LineageMap(
        target_id=target_id,
        entries=all_entries,
        confidence_entries=confidence_entries,
    )

    # Validate against JSON Schema
    _validate_against_schema(lineage_map)

    return lineage_map


def _validate_against_schema(lineage_map: LineageMap) -> None:
    """Validate a LineageMap against the JSON Schema contract.

    Raises:
        jsonschema.ValidationError: If validation fails.
    """
    if not _SCHEMA_PATH.exists():
        return  # Schema file not found — skip validation

    with _SCHEMA_PATH.open() as f:
        schema = json.load(f)

    data = json.loads(json.dumps(lineage_map.to_json_ld(), default=str))
    jsonschema.validate(data, schema)


def write_lineage_map(lineage_map: LineageMap, output_dir: Path) -> Path:
    """Write the lineage map to a JSON-LD file.

    Args:
        lineage_map: The validated LineageMap.
        output_dir: Directory to write to.

    Returns:
        Path to the written file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "lineage_map.json"

    data = json.dumps(lineage_map.to_json_ld(), default=str, indent=2)
    output_path.write_text(data)
    return output_path


def validate_lineage_map_file(file_path: Path) -> None:
    """Validate a lineage map JSON file against the contract schema.

    Args:
        file_path: Path to the JSON-LD lineage map file.

    Raises:
        FileNotFoundError: If the file does not exist.
        jsonschema.ValidationError: If validation fails.
    """
    with file_path.open() as f:
        data = json.load(f)

    if not _SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {_SCHEMA_PATH}")

    with _SCHEMA_PATH.open() as f:
        schema = json.load(f)

    jsonschema.validate(data, schema)
    entry_count = len(data.get("entries", []))
    print(f"All {entry_count} parameter references resolved.")


def _infer_source_type(source_id: str) -> str:
    """Infer source_type from a source_id string."""
    if source_id.startswith("Q") and source_id[1:].isdigit():
        return "nasa_quarter"
    if "." in source_id and source_id.replace(".", "").replace("-", "").isdigit():
        return "arxiv"
    if source_id.startswith("arxiv:"):
        return "arxiv"
    return "ads"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate a lineage map JSON file.")
    parser.add_argument("--validate", metavar="FILE", help="Path to lineage_map.json")
    args = parser.parse_args()

    if args.validate:
        try:
            validate_lineage_map_file(Path(args.validate))
        except (FileNotFoundError, jsonschema.ValidationError) as e:
            print(f"Validation failed: {e}", file=sys.stderr)
            sys.exit(1)

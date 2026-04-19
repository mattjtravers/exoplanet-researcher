# MCP Tool Interface Contracts

**Feature**: 001-xpi-agentic-vetting | **Date**: 2026-04-09

All NASA data access MUST route through these MCP tools (FR-004, FR-005). No agent
may call `lightkurve`, `astropy`, or any archive HTTP endpoint directly.

---

## Tool: `get_light_curve`

**File**: `src/mcp/tools/lightkurve_tool.py`
**Description**: Retrieves and detrends the light curve for a given target and quarter.

### Input Schema

```json
{
  "target_id": "string (KIC/TIC/TOI identifier, required)",
  "quarter": "integer (≥ 0, required)",
  "mission": "string (enum: 'Kepler', 'TESS', required)"
}
```

### Output Schema

```json
{
  "target_id": "string",
  "quarter": "integer",
  "time": "array of float (BJD timestamps)",
  "flux": "array of float (normalised flux)",
  "flux_err": "array of float (flux uncertainties)",
  "cadence": "string (enum: 'short', 'long')",
  "tool_call_id": "string (UUID, for Lineage Map reference)"
}
```

### Error Cases

| Condition | Error Type | Message |
|-----------|------------|---------|
| Target ID not found in archive | `ArchiveNotFoundError` | `"No data for {target_id} Q{quarter}"` |
| Quarter out of range for mission | `ArchiveNotFoundError` | `"Quarter {quarter} not available for {mission}"` |
| Archive unreachable | `ArchiveConnectionError` | `"NASA archive unreachable: {detail}"` |

---

## Tool: `get_stellar_properties`

**File**: `src/mcp/tools/archive_tool.py`
**Description**: Retrieves host star physical properties from the NASA archive.

### Input Schema

```json
{
  "target_id": "string (KIC/TIC/TOI identifier, required)"
}
```

### Output Schema

```json
{
  "target_id": "string",
  "stellar_radius_rsun": "float | null",
  "stellar_mass_msun": "float | null",
  "stellar_teff_k": "float | null",
  "log_g": "float | null",
  "metallicity_dex": "float | null",
  "source_catalog": "string (e.g., 'Kepler Stellar Properties Catalog DR25')",
  "tool_call_id": "string (UUID, for Lineage Map reference)"
}
```

### Error Cases

| Condition | Error Type | Message |
|-----------|------------|---------|
| Target ID not found | `ArchiveNotFoundError` | `"No stellar properties for {target_id}"` |
| All properties null | Returns result with nulls | Caller responsible for low-confidence scoring |
| Archive unreachable | `ArchiveConnectionError` | `"NASA archive unreachable: {detail}"` |

---

## MCP Server Registration

**File**: `src/mcp/server.py`

Tools are registered at server startup. The tool manifest must match this list exactly;
any tool called by an agent that is not in this manifest MUST raise `ToolNotFoundError`.

```python
REGISTERED_TOOLS = [
    "get_light_curve",
    "get_stellar_properties",
]
```

**Invariant**: Adding a new NASA data source requires a new registered MCP tool and a
corresponding entry in this contract document. Direct archive calls outside MCP are a
constitutional violation (Principle IV gate).

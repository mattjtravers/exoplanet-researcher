# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This is a **spec-first, greenfield project**. The `spec/` directory contains the full system design; the `src/` directory does not yet exist and must be created. All implementation work should faithfully follow the specs before deviating from them.

## Environment & Commands

Dependencies are managed with `uv`. The `.venv` is pre-created in Codespaces via the `postCreateCommand`.

```bash
uv sync                     # Install/sync dependencies
uv run python src/main.py --target "KIC-10666592"  # Run the pipeline

# Linting & formatting (Ruff, line-length 100)
uv run ruff check .         # Lint
uv run ruff format .        # Format
uv run ruff check --fix .   # Auto-fix lint issues

# Tests
uv run pytest               # Run all tests
uv run pytest -m unit       # Unit tests only
uv run pytest -m integration  # Integration tests (may hit network)
uv run pytest tests/path/to/test_file.py::test_name  # Single test
```

## Architecture

The pipeline is a deterministic `pydantic_graph` state machine. A `CandidateInput` (bare ID + catalog) flows into six sequential `BaseNode` subclasses, each appending its strictly typed output to a shared `GraphState`. **No raw dicts or untyped tuples are passed between nodes.**

### Node Execution Order

```
InitializationNode → ObserverNode → ScholarNode → DistillationNode → SynthesizerNode → ValidatorNode
       │                  ↑                                                  ↑                │
       │                  │ (violation_source="data" retry)                  │                │
       │                  └──────────────────────────────────────────────────┼────────────────┤
       │                                                                     │                │
       │                                       (violation_source="synthesis" retry)           │
       │                                                                     └────────────────┘
       ▼
   InitializationOutput → ObserverOutputs[] → ScholarOutputs[] → ... (all retry-loop outputs are append-only lists)
```

- **InitializationNode** — resolves bare target ID via `fetch_stellar_properties_mcp` and constructs the full `CandidateTarget`. Single-shot, not in any retry loop.
- **ObserverNode** — fetches light curves and fits transit models via MCP. Re-entered when `ValidatorViolation.violation_source == "data"`.
- **ScholarNode** — searches ArXiv/ADS via the Literature MCP using anomalies from the latest `ObserverOutput`.
- **DistillationNode** — no tools; compresses raw paper abstracts into `DistilledLiteratureRecord[]`.
- **SynthesizerNode** — no tools; assembles `VettingReport`, `LineageMap`, optional `ConsensusConflictFlag`. Always populates `VettingReport.node_assessments` regardless of conflict status. Re-entered when `ValidatorViolation.violation_source == "synthesis"`.
- **ValidatorNode** — enforces astrophysical boundaries via `astrophysics_constants_mcp` and classifies each violation by `violation_source`. Routes back to Observer (data violations) or Synthesizer (synthesis violations), with separate bounded retry counters.

### Key Types (from `spec/data-model.md`)

| Type | Purpose |
|------|---------|
| `CandidateInput` | Bare CLI input — target ID + catalog origin only |
| `CandidateTarget` | Fully populated target (stellar params resolved by InitializationNode) |
| `GraphState` | Mutable shared state; retry-loop outputs are append-only lists |
| `GraphDeps` | Static deps: `AgentConfig` dict, `astro_mcp_session`, `literature_mcp_session`, timeout |
| `VettingReport` | Terminal success artifact; always includes `node_assessments` |
| `ValidatorError` | Terminal failure artifact |
| `ValidatorViolation` | Carries `violation_source: Literal["data","synthesis"]` driving retry routing |
| `LineageMap` | JSON-LD provenance graph linking every parameter to its source |

### MCP Integration

External capabilities are split across **two MCP servers**, each with its own client session in `GraphDeps`:
- `astro_mcp_session` — `fetch_stellar_properties_mcp`, `fetch_mcp_lightcurve`, `fit_transit_model`, `astrophysics_constants_mcp`
- `literature_mcp_session` — `search_arxiv_mcp`, `query_ads_mcp`

Tool input/output contracts are defined in `spec/architecture.md` §4.

### Observability

- **Pydantic Logfire** instruments all node transitions, LLM inferences, and MCP calls as OpenTelemetry spans.
- **`FileStatePersistence`** snapshots `NodeSnapshot` objects to disk between every node transition, enabling pause/resume without cloud infra.

### Agent Configuration

Each node is configured via a YAML-loaded `AgentConfig` (model identifier, system prompt template, token budget, `max_retries`, temperature). Configs are passed through `GraphDeps.configs` keyed by node name.

## Spec Files

| File | Contents |
|------|---------|
| `spec/spec.md` | Product requirements and user scenarios |
| `spec/architecture.md` | Node contracts, MCP integrations, and exact state read/write paths |
| `spec/data-model.md` | All Pydantic schemas (canonical source of truth for types) |

When implementing, `spec/data-model.md` is authoritative for field names and types.

## Code Conventions

- All inter-node payloads must be Pydantic `BaseModel` subclasses — never plain `dict`.
- Evaluations live in `src/evals/` and run via `pydantic_evals` (offline, no live API calls required).
- Tests live in `tests/` with markers: `unit`, `integration`, `benchmark`.
- Python 3.11+ type syntax (`X | None`, `list[X]`) — no `Optional` or `List` imports.

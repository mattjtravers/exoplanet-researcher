# Quickstart: XPI — Independent Agentic Exoplanet Vetting

**Date**: 2026-04-09 | **Plan**: [plan.md](plan.md)

This guide covers environment setup, running the pipeline on a single candidate, and
executing the Benchmark Runner. It assumes GitHub Codespaces with the project devcontainer.

---

## Prerequisites

- GitHub Codespaces (devcontainer auto-provisions Python 3.11+)
- `uv` installed (included in devcontainer)
- ADS API token (set as a Codespaces secret named `ADS_API_TOKEN`)

---

## 1. Environment Setup

```bash
# Install all dependencies from the lock file
uv sync

# Verify linting passes
uv run ruff check src/

# Verify tests are discoverable
uv run pytest --collect-only
```

---

## 2. Configuration

Copy the default agent config and set your API token:

```bash
cp config/agents.yaml.example config/agents.yaml
```

The config controls per-agent token budgets, iteration limits, and thresholds.
Edit `config/agents.yaml` to change the runtime LLM model (set via `model_id` key).
No model identifier is hardcoded in source code.

Set your ADS token (if not using Codespaces secrets):
```bash
export ADS_API_TOKEN="your-token-here"
```

---

## 3. Run the MCP Server

The MCP server must be running before the pipeline is invoked:

```bash
uv run python -m src.mcp.server &
```

The server registers `get_light_curve` and `get_stellar_properties` tools and listens
on localhost. The pipeline connects to it automatically.

---

## 4. Vet a Single Candidate

```bash
uv run python -m src.dag.pipeline --target-id KIC-11442793 --catalog KIC
```

Outputs written to `outputs/KIC-11442793/`:
- `report.md` — Markdown Vetting Report
- `lineage_map.json` — JSON-LD Lineage Map
- `light_curve.png` — Annotated light curve chart

To verify the Lineage Map passes schema validation:
```bash
uv run python -m src.tools.lineage_mapper --validate outputs/KIC-11442793/lineage_map.json
```

---

## 5. Run the Test Suite

```bash
# All tests (unit + integration)
uv run pytest

# Unit tests only (fast)
uv run pytest tests/unit/

# Integration test (single known candidate end-to-end)
uv run pytest tests/integration/
```

All mathematical tests (transit fitter, anomaly detector) MUST be written before
implementation and confirmed to fail first (Principle III).

---

## 6. Run the Benchmark Runner

```bash
# Download and validate Golden Dataset (first run only)
uv run python -m src.benchmark.dataset --init

# Run full benchmark against Golden Dataset
uv run python -m src.benchmark.runner
```

Output written to `benchmarks/history/<run-id>.json`. The runner prints the Confusion
Matrix and F1 score to stdout. If F1 regresses > 5 points from the prior run, the
process exits with a non-zero code.

---

## 7. Validate a Report Programmatically

```bash
uv run python -m src.tools.report_generator --validate outputs/KIC-11442793/report.md
```

Checks that all mandatory sections per FR-023 are present and that the Lineage Map
reference resolves to an existing file.

---

## Known Limitations (v1)

- Single candidate per invocation; batch processing is not supported.
- Offline operation is not supported; ArXiv, ADS, and NASA archive must be reachable.
- Real-time continuous benchmarking is not included; trigger the Benchmark Runner manually
  or via CI.

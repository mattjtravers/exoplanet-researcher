# Implementation Plan: XPI — Independent Agentic Exoplanet Vetting

**Branch**: `001-xpi-agentic-vetting` | **Date**: 2026-04-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-xpi-agentic-vetting/spec.md`

## Summary

XPI is a five-agent PydanticAI pipeline that independently vets exoplanet candidates by
reconciling NASA photometric data with peer-reviewed literature. The Observer analyses
light curves quantitatively; the Scholar retrieves and synthesises literature agentically;
the Distillation Agent compresses papers to target-relevant content using a PydanticAI Agent
with a YAML agent spec; the Synthesizer resolves conflicts and issues the Vetting Report;
the Validator enforces physical law constraints. All tool functions return typed Pydantic
models. Every parameter is traced in a JSON-LD Lineage Map. A standalone Benchmark Runner
evaluates accuracy against a 40-object Golden Dataset, complemented by pydantic_evals
evaluation datasets for per-agent quality measurement.

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: PydanticAI, pydantic-evals, lightkurve, astropy, numpy,
matplotlib, pyyaml, anthropic, uv, ruff, pytest, mcp (Python MCP SDK)
**Storage**: File-based — JSON-LD Lineage Maps and Markdown Vetting Reports written to
`outputs/`; benchmark results versioned in `benchmarks/history/`
**Testing**: pytest (unit + integration); mathematical tests against known ephemerides
**Target Platform**: GitHub Codespaces — Linux, Python 3.11+ devcontainer
**Project Type**: Agentic pipeline with CLI entry point (one candidate per invocation)
**Performance Goals**: Produce a complete Vetting Report per candidate invocation without
manual intervention; Benchmark Runner completes 40-object run without errors
**Constraints**: Single candidate per invocation (v1); no direct NASA HTTP calls (MCP
only); token budget enforced per agent via config; no hardcoded model identifiers
**Scale/Scope**: One candidate per run; Golden Dataset ≥ 40 objects; v1 scope only

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Pre-Design Status | Phase Delivering Compliance |
|-----------|------------------|-----------------------------|
| I. Reasoning Transparency & Scientific Lineage | ✅ | Phase 2 (Lineage Map generator) + all agents emit citations |
| II. Type-Safe Scientific Rigor | ✅ | Phase 1 (PydanticAI schemas + FR-033 inter-agent contracts) |
| III. Test-First Development | ✅ | Every task carries a Test Plan; red before green enforced |
| IV. DAG-Driven Single-Responsibility Agents | ✅ | Phase 4 (PydanticAI Agent Specs + sequential DAG; 5 agents, single bounded roles) |
| V. Simplicity & YAGNI | ✅ | Single-candidate scope; no batch, no speculative features |
| VI. Agentic RAG with Anomaly Detection | ✅ | Phase 2 (Observer anomaly) + Phase 3 (Scholar iterative RAG) |
| VII. Uncertainty Quantification & Conflict Detection | ✅ | Phase 4 (Conflict Flag + reasoning loop) |
| VIII. Benchmark-Driven Accuracy Validation | ✅ | Phase 5 (Benchmark Runner + Golden Dataset + F1 gate) |
| IX. Context Efficiency & Token Budget | ✅ | Phase 3 (Distillation Agent + configurable budget) |
| X. Evaluation-Driven Quality Assurance | ✅ | src/evals/ (pydantic_evals Dataset + Evaluator per LLM-backed agent) |

**Post-Design Re-check**: See bottom of this document after Phase 1 artifacts are complete.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-xpi-agentic-vetting/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── agent-interfaces.md
│   ├── lineage-map-schema.json
│   └── mcp-tools.md
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── schemas/                    # PydanticAI entity schemas (Phase 1)
│   ├── candidate.py            # CandidateTarget
│   ├── report.py               # VettingReport, AnomalyRecord, ConsensusConflictFlag
│   ├── lineage.py              # LineageMap, LineageEntry
│   ├── confidence.py           # ConfidenceAssessment
│   ├── literature.py           # DistilledLiteratureRecord
│   └── benchmark.py            # BenchmarkResult, GoldenDataset
├── mcp/                        # MCP server — NASA data gateway (Phase 1)
│   ├── server.py               # Tool registration and server entry point
│   └── tools/
│       ├── lightkurve_tool.py  # Light curve retrieval tool
│       └── archive_tool.py     # Stellar properties lookup tool
├── agents/                     # One file per agent (Phases 2–4)
│   ├── observer.py             # Quantitative analysis + anomaly detection
│   ├── scholar.py              # Agentic RAG + iterative search
│   ├── distillation.py         # Paper compression agent
│   ├── synthesizer.py          # Conflict resolution + report assembly
│   └── validator.py            # Physical law enforcement
├── tools/                      # Atomic tool functions used by agents
│   ├── transit_fitter.py       # BLS + transit parameter extraction
│   ├── anomaly_detector.py     # Aperiodicity + asymmetry detection
│   ├── lineage_mapper.py       # Lineage Map construction + validation
│   ├── rag_tools.py            # ArXiv + ADS search + distillation helpers
│   └── report_generator.py     # Markdown report + visualisation renderer
├── dag/
│   └── pipeline.py             # LangGraph DAG definition and state schema
└── benchmark/
    ├── runner.py                # Benchmark Runner (standalone)
    ├── dataset.py               # Golden Dataset loader and validator
    └── metrics.py               # Confusion Matrix + F1 computation

tests/
├── unit/                       # Per-tool and per-schema tests
├── integration/                # End-to-end pipeline tests (single candidate)
└── benchmark/                  # Regression tests against stored F1 baseline

outputs/                        # Generated Vetting Reports + Lineage Maps
benchmarks/
└── history/                    # Versioned benchmark results (JSON)
```

**Structure Decision**: Single-project layout. All agents are Python modules within
`src/agents/`; atomic tool functions are in `src/tools/` so they can be tested
independently of agent orchestration. The MCP server lives in `src/mcp/` and is the
exclusive gateway to NASA data per FR-004/FR-005. The LangGraph DAG is defined in
`src/dag/pipeline.py` and imports agents — not the reverse — keeping the DAG topology
explicit and auditable.

---

## Phase 0: Research

*See [research.md](research.md) for full decision log.*

Key decisions resolved in Phase 0:

| Topic | Decision |
|-------|----------|
| Lineage Map format | JSON-LD (machine-readable, schema-validatable; satisfies FR-006/FR-007) |
| LangGraph state type | Typed `TypedDict` state with PydanticAI-validated messages at node boundaries |
| MCP server pattern | Python `mcp` SDK; tools registered at startup; one server process per pipeline run |
| ArXiv/ADS access | `arxiv` Python client for ArXiv; ADS REST API via `pyvo` or `requests` with ADS token |
| Anomaly detection method | BLS periodogram residuals + ingress/egress asymmetry ratio; flagged if > 2σ from symmetric model |
| Token budget enforcement | Per-agent limits in `config/agents.yaml`; checked in agent base class before LLM call |
| Distillation strategy | Structured extraction prompt targeting Star ID; output is `DistilledLiteratureRecord` schema |
| Golden Dataset source | NASA Cumulative KOI Table (confirmed + false positives); downloaded at benchmark init |

---

## Phase 1: Design

*See [data-model.md](data-model.md) and [contracts/](contracts/) for full artefacts.*

### Post-Design Constitution Re-check

| Principle | Post-Design Status | Notes |
|-----------|-------------------|-------|
| I. Reasoning Transparency | ✅ | `LineageMap` schema has mandatory `source_id` + `tool_call_id` fields on every entry |
| II. Type-Safe Scientific Rigor | ✅ | All inter-agent messages are `PydanticAI` models; `agent-interfaces.md` defines contracts |
| III. Test-First | ✅ | Contract schemas enable writing failing tests before agent implementation |
| IV. DAG Topology | ✅ | `pipeline.py` state graph is acyclic; correction loops bounded by `max_iterations` field |
| V. YAGNI | ✅ | No batch processing, no async multi-candidate, no speculative nodes in DAG |
| VI. Agentic RAG + Anomaly | ✅ | `ScholarInput` carries `anomaly_directives` from Observer; queries generated at runtime |
| VII. Uncertainty + Conflict | ✅ | `ConfidenceAssessment` schema enforced; `ConsensusConflictFlag` has typed fields |
| VIII. Benchmark | ✅ | `BenchmarkResult` schema versioned; runner is standalone module |
| IX. Token Budget | ✅ | `config/agents.yaml` schema defined; budget field on `AgentConfig` |

---

## Phase 2: Implementation Phases

### Phase 1 — Core Infrastructure & Type-Safety

**Goal**: Establish the type-safe foundation that all agents depend on. Nothing else
starts until schemas and the MCP server are complete and tested.

**Constitution gates**: Principles II, IV, V

| Task | Description | Dependencies | Test Plan |
|------|-------------|--------------|-----------|
| T001 | Initialise `uv` workspace; pin all dependencies in lock file; configure `ruff` and `pytest` | None | `uv run ruff check src/` passes; `uv run pytest` discovers tests |
| T002 | Define `CandidateTarget` PydanticAI schema in `src/schemas/candidate.py` | T001 | Write test asserting malformed ID raises `ValidationError`; confirm red → implement → green |
| T003 | Define `LineageEntry` + `LineageMap` schemas in `src/schemas/lineage.py`; include JSON-LD `@context` | T001 | Test: serialised map passes JSON Schema validation; missing `source_id` raises error |
| T004 | Define `ConfidenceAssessment` schema in `src/schemas/confidence.py`; score range 0–100 enforced | T001 | Test: score > 100 raises `ValidationError`; score < 0 raises `ValidationError` |
| T005 | Define `ConsensusConflictFlag` schema in `src/schemas/report.py` | T004 | Test: flag with equal scores raises no error; flag missing `evidence` raises error |
| T006 | Define `AnomalyRecord`, `VettingReport` schemas in `src/schemas/report.py` | T003, T004, T005 | Test: `VettingReport` without `lineage_map_ref` raises error; full valid report passes |
| T007 | Define `DistilledLiteratureRecord` schema in `src/schemas/literature.py` | T001 | Test: record without ArXiv/ADS `source_id` raises error; verbatim `citation_string` preserved |
| T008 | Define `BenchmarkResult` + `GoldenDataset` schemas in `src/schemas/benchmark.py` | T001 | Test: `BenchmarkResult` with negative TP raises error; F1 computed correctly from TP/FP/TN/FN |
| T009 | Define `AgentConfig` schema in `src/schemas/config.py`; `token_budget` field required | T001 | Test: config missing `token_budget` raises error; budget = 0 raises error |
| T010 | Implement MCP server entry point in `src/mcp/server.py`; register tool stubs | T001 | Test: server starts without error; registered tool names match contract in `contracts/mcp-tools.md` |
| T011 | Implement `lightkurve_tool.py`: retrieves light curve for a given KIC/TIC/TOI via MCP | T010 | Test: known KIC returns non-empty `LightCurve` object; unknown ID raises typed `ArchiveError` |
| T012 | Implement `archive_tool.py`: retrieves stellar properties (radius, mass, Teff) via MCP | T010 | Test: known star returns schema-validated properties; missing field raises typed error |

**Checkpoint**: All schemas tested and passing. MCP server starts and returns data. No
agent code written yet.

---

### Phase 2 — Quantitative Tools (The Observer)

**Goal**: Implement all atomic tools used by the Observer agent. Agent wiring in Phase 4.

**Constitution gates**: Principles I, II, VI

| Task | Description | Dependencies | Test Plan |
|------|-------------|--------------|-----------|
| T013 | Implement `transit_fitter.py`: BLS periodogram + transit parameter extraction (period, depth, duration, Rp/Rs) | T011 | Test against known KIC with published ephemeris; assert parameters within 5% of published values |
| T014 | Implement `anomaly_detector.py`: ingress/egress asymmetry ratio + aperiodicity detection; returns `AnomalyRecord` or `None` | T011 | Test: symmetric synthetic transit → no record; asymmetric synthetic transit → record with correct quarter |
| T015 | Implement `lineage_mapper.py`: builds and validates `LineageMap` entries; serialises to JSON-LD | T003, T013 | Test: map built from transit fit contains `tool_call_id`, `source_id`, `parameter_name`; schema validation passes |
| T016 | Implement Observer tool integration test: light curve → transit parameters + lineage entries + optional anomaly record | T013, T014, T015 | End-to-end test using a real KIC from the Golden Dataset; output matches expected parameter ranges |

**Checkpoint**: Observer tools independently verified. Lineage Map generation tested.

---

### Phase 3 — Qualitative Tools (The Scholar + Distillation Agent)

**Goal**: Build literature retrieval and distillation tools. No agent wiring yet.

**Constitution gates**: Principles VI, IX, I

| Task | Description | Dependencies | Test Plan |
|------|-------------|--------------|-----------|
| T017 | Implement ArXiv search tool in `src/tools/rag_tools.py`: accepts query string, returns list of `(arxiv_id, abstract)` | T001 | Test: query for known exoplanet returns ≥1 result containing target ID; empty query raises error |
| T018 | Implement ADS search tool in `src/tools/rag_tools.py`: accepts query, returns ADS bibcodes + abstracts | T001 | Test: known star ID returns ≥1 ADS record; ADS token missing raises typed `ConfigError` |
| T019 | Implement iterative query builder: generates search terms from `CandidateTarget` + `AnomalyRecord`; produces ≥2 query variants | T002, T014 | Test: candidate with anomaly record produces query containing anomaly hypothesis terms |
| T020 | Implement `distillation.py` agent: takes full paper text + Star ID → `DistilledLiteratureRecord`; enforces token budget | T007, T009 | Test: 10k-token paper reduced to record containing target-relevant params only; verbatim citation preserved; budget exceeded → typed error |
| T021 | Integration test: KIC with known literature → Scholar tools → `DistilledLiteratureRecord` list with correct source IDs | T017, T018, T019, T020 | Golden Dataset object with known paper → record contains expected physical parameters |

**Checkpoint**: Scholar tools and Distillation Agent independently verified.

---

### Phase 4 — Orchestration & Reasoning (DAG + Synthesizer + Validator)

**Goal**: Wire all agents into the LangGraph DAG; implement conflict detection and
physical validation.

**Constitution gates**: Principles IV, VII, II, I

| Task | Description | Dependencies | Test Plan |
|------|-------------|--------------|-----------|
| T022 | Define LangGraph `PipelineState` typed dict in `src/dag/pipeline.py`; all fields are PydanticAI models or None | T002–T009 | Test: state transitions between valid schemas pass; invalid schema at node boundary raises typed error |
| T023 | Implement Observer agent node in `src/agents/observer.py`: calls T013/T014/T015 tools; emits `ConfidenceAssessment` + `LineageMap` partial | T016, T022 | Test: known planet input → confidence > 50%; known false positive → anomaly record emitted |
| T024 | Implement Scholar agent node in `src/agents/scholar.py`: iterative query loop (max iterations from config); emits `ConfidenceAssessment` + `DistilledLiteratureRecord` list | T021, T022 | Test: Scholar with zero results → iterates with broadened query; exits after max_iterations with low-confidence assessment |
| T025 | Implement Distillation Agent node in `src/agents/distillation.py`: wraps T020; enforces budget from `AgentConfig` | T020, T022 | Test: agent respects budget; outputs schema-valid `DistilledLiteratureRecord`; budget overrun → typed error propagates to DAG |
| T026 | Implement Synthesizer agent in `src/agents/synthesizer.py`: compares Observer + Scholar `ConfidenceAssessment`; emits `ConsensusConflictFlag` if divergence > threshold | T023, T024, T022 | Test: Observer 85% planet + Scholar 15% planet → flag emitted; Observer 80% + Scholar 75% → no flag; flag includes both scores and evidence |
| T027 | Implement self-correction loop in Synthesizer: on conflict, re-query Scholar with additional directive; bounded by config max_iterations | T026 | Test: conflict on first pass → loop runs ≤ max_iterations; loop terminates even if unresolved |
| T028 | Implement Validator agent in `src/agents/validator.py`: checks Rp/Rs bounds, mass-radius constraints; emits typed `ValidatorResult` | T022 | Test: physically impossible parameters (e.g., Rp > Rs) → validator failure documented; valid parameters → pass |
| T029 | Wire full DAG in `src/dag/pipeline.py`: Observer → Scholar (parallel) → Distillation → Synthesizer → Validator → Report; correction loop on conflict | T022–T028 | Integration test: end-to-end with known confirmed planet → disposition "Planet Candidate"; known false positive → "False Positive" or Conflict Flag |

**Checkpoint**: Full pipeline runs on a single candidate. Conflict detection and
validation tested end-to-end.

---

### Phase 5 — Evaluation & Reporting

**Goal**: Build the Benchmark Runner, Golden Dataset loader, and report generator.

**Constitution gates**: Principles VIII, I, IX

| Task | Description | Dependencies | Test Plan |
|------|-------------|--------------|-----------|
| T030 | Implement `dataset.py`: downloads + validates NASA KOI table; builds `GoldenDataset` with ≥20 planets + ≥20 false positives | T008 | Test: dataset loads without error; all entries have ground-truth label; schema validation passes |
| T031 | Implement `metrics.py`: computes Confusion Matrix (TP/FP/TN/FN), precision, recall, F1 from list of `(prediction, ground_truth)` pairs | T008 | Test: perfect predictions → F1 = 1.0; all wrong → F1 = 0.0; known test case matches hand-calculated values |
| T032 | Implement `runner.py`: iterates Golden Dataset; calls pipeline per object; aggregates `BenchmarkResult`; persists to `benchmarks/history/` | T029, T030, T031 | Test: single-object subset run → produces `BenchmarkResult` with correct structure; file written to history |
| T033 | Implement F1 regression gate in `runner.py`: loads prior result from history; raises `RegressionError` if F1 drops > 5 pts | T032 | Test: current F1 0.75, prior 0.85 → `RegressionError` raised; current 0.82, prior 0.85 → no error |
| T034 | Implement `report_generator.py`: renders `VettingReport` to Markdown; generates annotated light curve PNG via matplotlib; writes interpretive description | T006, T015, T029 | Test: report contains all mandatory sections per FR-023; PNG file written; interpretive description is non-empty string |
| T035 | Implement Lineage Map finaliser: merges partial maps from Observer, Scholar, Synthesizer into single JSON-LD file; runs schema validation | T015, T029 | Test: merged map has entry for every parameter in report; schema validation passes; no dangling `source_id` references |
| T036 | Full pipeline + report integration test: known Golden Dataset object → complete Markdown report + JSON-LD Lineage Map + PNG; all files written to `outputs/` | T029, T034, T035 | Assert report passes FR-023 checklist programmatically; Lineage Map passes schema validation |

**Checkpoint**: Benchmark Runner produces a Confusion Matrix and F1 on the full Golden
Dataset. Report generator outputs all required artefacts. System is ready for
production use.

---

## Complexity Tracking

> No constitutional violations requiring justification at this time.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Five agents (constitution names four) | Distillation Agent is a distinct bounded responsibility per Principle IV; embedding it in Scholar would violate single-responsibility | Scholar + embedded distillation creates untestable mixed concerns |

---

## Dependencies & Execution Order

```
T001 (env setup)
  └── T002–T009 (schemas) ← all in parallel after T001
        └── T010 (MCP server)
              ├── T011 (lightkurve tool)
              └── T012 (archive tool)
                    └── T013 (transit fitter)
                          ├── T014 (anomaly detector)
                          └── T015 (lineage mapper)
                                └── T016 (Observer integration test)
                                      ├── T017–T019 (RAG tools) ← parallel
                                      └── T020 (distillation tool)
                                            └── T021 (Scholar integration test)
                                                  └── T022 (DAG state)
                                                        └── T023–T025 (agent nodes) ← parallel
                                                              └── T026–T028 (Synthesizer + Validator)
                                                                    └── T029 (full DAG wiring)
                                                                          ├── T030–T031 (dataset + metrics) ← parallel
                                                                          └── T034–T035 (report + lineage) ← parallel
                                                                                └── T032–T033 (runner + regression gate)
                                                                                      └── T036 (final integration test)
```

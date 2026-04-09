---
description: "Task list for XPI — Independent Agentic Exoplanet Vetting"
---

# Tasks: XPI — Independent Agentic Exoplanet Vetting

**Input**: Design documents from `/specs/001-xpi-agentic-vetting/`
**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Test tasks are included per the Test-First mandate (Constitution Principle III,
NON-NEGOTIABLE). Tests MUST be written and confirmed to FAIL before implementation begins.

**Organization**: Tasks grouped by user story to enable independent implementation and
delivery of each story as a working increment.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths included in all implementation tasks

## Path Conventions

- Source: `src/` at repository root
- Tests: `tests/unit/`, `tests/integration/`, `tests/benchmark/`
- Outputs: `outputs/` (generated reports, not committed)
- Benchmark history: `benchmarks/history/` (committed, versioned)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — dev tooling, directory structure, and base config.

- [ ] T001 Initialize `uv` workspace; create `pyproject.toml` with all pinned dependencies from research.md; create `config/agents.yaml.example`
- [ ] T002 [P] Configure `ruff` lint rules in `pyproject.toml` (line-length, import sort, docstring enforcement)
- [ ] T003 [P] Configure `pytest` in `pyproject.toml`; create `tests/conftest.py` with shared fixtures
- [ ] T004 Create full `src/` directory structure per plan.md: `schemas/`, `mcp/tools/`, `agents/`, `tools/`, `dag/`, `benchmark/`; create `outputs/` and `benchmarks/history/` directories with `.gitkeep`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: All PydanticAI schemas, typed errors, MCP server, and base agent class.
No user story can begin until this phase is complete.

**⚠️ CRITICAL**: Tests for schemas are written FIRST and confirmed red before implementation.

### Schema Tests (write first — confirm red)

- [ ] T005 [P] Write unit tests for `CandidateTarget` in `tests/unit/test_schemas_candidate.py`: invalid catalog literal raises `ValidationError`; empty `target_id` raises `ValidationError`; negative stellar radius raises `ValidationError`
- [ ] T006 [P] Write unit tests for `LineageEntry` + `LineageMap` in `tests/unit/test_schemas_lineage.py`: missing `source_id` raises `ValidationError`; serialised map passes JSON Schema validation against `contracts/lineage-map-schema.json`
- [ ] T007 [P] Write unit tests for `ConfidenceAssessment` in `tests/unit/test_schemas_confidence.py`: score > 100 raises `ValidationError`; score < 0 raises `ValidationError`; empty `primary_evidence` raises `ValidationError`
- [ ] T008 [P] Write unit tests for `ConsensusConflictFlag`, `AnomalyRecord`, `VettingReport` in `tests/unit/test_schemas_report.py`: both `consensus_confidence` and `conflict_flag` null raises `ValidationError`; both non-null raises `ValidationError`
- [ ] T009 [P] Write unit tests for `BenchmarkResult` in `tests/unit/test_schemas_benchmark.py`: negative TP raises `ValidationError`; F1 computed correctly from known TP/FP/TN/FN values
- [ ] T010 [P] Write unit tests for `AgentConfig` in `tests/unit/test_schemas_config.py`: missing `token_budget` raises `ValidationError`; `token_budget` = 0 raises `ValidationError`

### Schema Implementation

- [ ] T011 [P] Implement `CandidateTarget` schema in `src/schemas/candidate.py` (makes T005 green)
- [ ] T012 [P] Implement `LineageEntry` + `LineageMap` schemas in `src/schemas/lineage.py`; include JSON-LD `@context` field (makes T006 green)
- [ ] T013 [P] Implement `ConfidenceAssessment` schema in `src/schemas/confidence.py` (makes T007 green)
- [ ] T014 [P] Implement `ConsensusConflictFlag`, `AnomalyRecord`, `ReasoningStep`, `ValidatorViolation`, `ValidatorResult`, `VettingReport` schemas in `src/schemas/report.py` (makes T008 green)
- [ ] T015 [P] Implement `DistilledLiteratureRecord` schema in `src/schemas/literature.py`
- [ ] T016 [P] Implement `BenchmarkResult`, `GoldenObject`, `GoldenDataset` schemas in `src/schemas/benchmark.py` (makes T009 green)
- [ ] T017 [P] Implement `AgentConfig` schema + YAML loader in `src/schemas/config.py`; create `config/agents.yaml` from example (makes T010 green)

### Typed Errors + Agent Base

- [ ] T018 [P] Implement typed error classes in `src/errors.py`: `TokenBudgetExceededError`, `ArchiveNotFoundError`, `ArchiveConnectionError`, `ToolNotFoundError`, `RegressionError`, `ValidationContractError`
- [ ] T019 Implement `AgentBase` class in `src/agents/base.py`: `check_token_budget()` raises `TokenBudgetExceededError` if exceeded; `validate_input()` / `validate_output()` raise `ValidationContractError` on schema failure (depends T017, T018)

### MCP Server

- [ ] T020 Implement MCP server entry point in `src/mcp/server.py`: register `get_light_curve` and `get_stellar_properties` tools from manifest; raise `ToolNotFoundError` for unregistered calls (depends T018)
- [ ] T021 [P] Implement `get_light_curve` MCP tool in `src/mcp/tools/lightkurve_tool.py`: retrieve + detrend light curve for KIC/TIC/TOI + quarter; return typed output schema; raise `ArchiveNotFoundError` or `ArchiveConnectionError` on failure (depends T020)
- [ ] T022 [P] Implement `get_stellar_properties` MCP tool in `src/mcp/tools/archive_tool.py`: retrieve stellar radius, mass, Teff from NASA archive; return typed output schema (depends T020)

### Pipeline State

- [ ] T023 Implement `PipelineState` TypedDict in `src/dag/pipeline.py`: all fields are PydanticAI model instances or `None`; import all agent I/O schemas (depends T011–T017)

**Checkpoint**: All schema tests green. MCP server starts. `AgentBase` enforces token budget. No agent logic written yet.

---

## Phase 3: User Story 1 — Researcher Receives a Transparent Vetting Report (Priority: P1) 🎯 MVP

**Goal**: End-to-end pipeline produces a Vetting Report (disposition + confidence score +
annotated light curve + Reasoning Trace) for a single candidate invocation.

**Independent Test**: Submit known confirmed planet KIC-11442793. Pipeline produces
`outputs/KIC-11442793/report.md` with "Planet Candidate" disposition, a confidence score,
a matplotlib PNG, and a non-empty Reasoning Trace.

### Tests for User Story 1 (write first — confirm red) ⚠️

- [ ] T024 [P] [US1] Write unit test for `transit_fitter` in `tests/unit/test_transit_fitter.py`: known KIC ephemeris → period within 5% of published value; transit depth within 10% of published value
- [ ] T025 [P] [US1] Write integration test skeleton in `tests/integration/test_pipeline_basic.py`: known confirmed planet → `VettingReport` with `disposition="planet_candidate"`, non-empty `reasoning_trace`, non-empty `light_curve_chart_path`; confirm test fails (no pipeline yet)

### Implementation for User Story 1

- [ ] T026 [P] [US1] Implement `transit_fitter.py` in `src/tools/transit_fitter.py`: BLS periodogram + period, depth, duration, Rp/Rs extraction using `lightkurve` + `astropy`; returns typed parameter dict with tool_call_id (makes T024 green) (depends T021)
- [ ] T027 [US1] Implement Observer agent in `src/agents/observer.py`: calls `get_light_curve` via MCP, runs `transit_fitter`, emits `ObserverOutput` (ConfidenceAssessment + empty anomaly_records list + lineage_partial stub); inherits `AgentBase` (depends T019, T023, T026)
- [ ] T028 [P] [US1] Implement ArXiv search tool in `src/tools/rag_tools.py`: accepts query string, returns list of `(arxiv_id, abstract)` tuples; raises typed error on empty query (depends T018)
- [ ] T029 [P] [US1] Implement ADS search tool in `src/tools/rag_tools.py`: accepts query string, returns ADS bibcodes + abstracts via REST API using `ADS_API_TOKEN` env var; raises `ConfigError` if token missing (depends T018)
- [ ] T030 [US1] Implement iterative query builder in `src/tools/rag_tools.py`: generates ≥2 query variants from `CandidateTarget` fields; broadens query on empty results (depends T011, T028, T029)
- [ ] T031 [US1] Implement Distillation Agent in `src/agents/distillation.py`: takes raw paper list + Star ID → `DistilledLiteratureRecord` list; enforces token budget via `AgentBase.check_token_budget()`; preserves `citation_string` verbatim (depends T015, T019, T030)
- [ ] T032 [US1] Implement Scholar agent in `src/agents/scholar.py`: calls iterative query builder (max_iterations from config), feeds results to Distillation Agent, emits `ScholarOutput` (ConfidenceAssessment + records + queries_issued); inherits `AgentBase` (depends T019, T023, T031)
- [ ] T033 [US1] Implement basic Synthesizer in `src/agents/synthesizer.py`: receives Observer + Scholar outputs, emits consensus disposition + confidence score (conflict detection added in US3); emits `ReasoningStep` list; inherits `AgentBase` (depends T019, T023, T027, T032)
- [ ] T034 [US1] Implement Validator agent in `src/agents/validator.py`: checks Rp/Rs bounds + mass-radius constraint from `CandidateTarget` stellar properties; emits `ValidatorResult`; if failed → `annotated_disposition="validator_failed"` (depends T019, T023, T033)
- [ ] T035 [US1] Implement `report_generator.py` in `src/tools/report_generator.py`: renders `VettingReport` to Markdown with all FR-023 mandatory sections; generates annotated light curve PNG via matplotlib with system-authored interpretive description; writes to `outputs/{target_id}/` (depends T014, T034)
- [ ] T036 [US1] Wire basic DAG in `src/dag/pipeline.py`: Observer → Scholar (parallel) → Distillation → Synthesizer → Validator → Report; add CLI entry `python -m src.dag.pipeline --target-id --catalog` (depends T027, T032, T034, T035)

**Checkpoint**: `uv run python -m src.dag.pipeline --target-id KIC-11442793 --catalog KIC` produces report.md + PNG. T025 integration test is now green.

---

## Phase 4: User Story 2 — Researcher Traces Any Parameter to Its Origin (Priority: P1)

**Goal**: Every Vetting Report is accompanied by a JSON-LD Lineage Map linking every
physical parameter to its source data and tool call. Map passes schema validation with
zero dangling references.

**Independent Test**: Run pipeline on KIC-11442793. Open `outputs/KIC-11442793/lineage_map.json`.
Run `python -m src.tools.lineage_mapper --validate outputs/KIC-11442793/lineage_map.json` —
exits 0, prints "All N parameter references resolved."

### Tests for User Story 2 (write first — confirm red) ⚠️

- [ ] T037 [P] [US2] Write unit tests in `tests/unit/test_lineage_mapper.py`: LineageMap with missing `source_id` in any entry fails JSON Schema validation; merged map from two partials has correct total entry count
- [ ] T038 [US2] Write integration test in `tests/integration/test_lineage.py`: completed pipeline → `lineage_map.json` passes JSON Schema validation; every parameter name in `report.md` has a corresponding entry in the map

### Implementation for User Story 2

- [ ] T039 [US2] Implement `lineage_mapper.py` in `src/tools/lineage_mapper.py`: build `LineageEntry` list from tool call records; serialise `LineageMap` to JSON-LD; validate against `contracts/lineage-map-schema.json` using `jsonschema`; raise `ValidationError` on any dangling reference (depends T012)
- [ ] T040 [US2] Update Observer agent in `src/agents/observer.py` to emit full `lineage_partial`: one `LineageEntry` per computed parameter (period, depth, duration, Rp/Rs, stellar radius used) with `tool_call_id` and `source_id` (depends T039, T027)
- [ ] T041 [US2] Update Scholar agent in `src/agents/scholar.py` to emit `lineage_partial`: one `LineageEntry` per extracted paper parameter, citing `arxiv_id` or ADS bibcode as `source_id` (depends T039, T032)
- [ ] T042 [US2] Implement Lineage Map finaliser in `src/tools/lineage_mapper.py`: merge `lineage_partial` lists from Observer + Scholar + Synthesizer `ReasoningStep` sources; run full schema validation; include `confidence_entries` from both `ConfidenceAssessment` objects (depends T039, T040, T041)
- [ ] T043 [US2] Update DAG in `src/dag/pipeline.py` to call Lineage Map finaliser after Validator; write `lineage_map.json` to `outputs/{target_id}/`; set `VettingReport.lineage_map_path` (depends T042, T036)

**Checkpoint**: US1 + US2 both independently testable. Lineage Map written and validated on every run. T038 integration test is green.

---

## Phase 5: User Story 3 — System Flags a Conflict Between Quantitative and Literary Evidence (Priority: P2)

**Goal**: When Observer and Scholar confidence scores diverge by more than the configured
threshold, the Synthesizer emits a `ConsensusConflictFlag` with both scores and evidence,
triggers a self-correction loop, and surfaces any unresolved conflict in the report.

**Independent Test**: Submit KIC known to be an eclipsing binary (false positive). Report
contains a `ConsensusConflictFlag` with `observer_assessment.score` ≥ 60% and
`scholar_assessment.score` ≤ 30%, plus at least one literature citation.

### Tests for User Story 3 (write first — confirm red) ⚠️

- [ ] T044 [P] [US3] Write unit tests in `tests/unit/test_synthesizer_conflict.py`: Observer 85% + Scholar 15% → `ConsensusConflictFlag` emitted with correct divergence value; Observer 80% + Scholar 75% → no flag; flag missing `conflict_summary` raises `ValidationError`
- [ ] T045 [US3] Write integration test in `tests/integration/test_conflict.py`: known eclipsing binary KOI → report contains `ConsensusConflictFlag`; flag includes both agent scores and at least one literature reference

### Implementation for User Story 3

- [ ] T046 [US3] Update Synthesizer in `src/agents/synthesizer.py` to compare Observer + Scholar scores; emit `ConsensusConflictFlag` with divergence + both assessments + `conflict_summary` when delta exceeds `agent_config.conflict_threshold` (depends T033)
- [ ] T047 [US3] Implement self-correction loop in `src/agents/synthesizer.py`: on `ConsensusConflictFlag`, re-invoke Scholar with updated directive; iterate up to `agent_config.max_correction_iterations`; set `conflict_flag.resolved=True/False` on exit (depends T046, T032)
- [ ] T048 [US3] Update `report_generator.py` to include `ConsensusConflictFlag` section in Markdown report when present; unresolved flag displayed prominently alongside disposition (depends T035, T047)

**Checkpoint**: US1 + US2 + US3 each independently testable. T045 integration test is green.

---

## Phase 6: User Story 4 — System Detects and Investigates Light Curve Anomalies (Priority: P2)

**Goal**: Observer detects aperiodicities and asymmetric transits; Scholar is directed to
search for non-planetary explanations; AnomalyRecord appears in the Vetting Report.

**Independent Test**: Submit a KIC with a known asymmetric transit (dust disk candidate).
Report contains an `AnomalyRecord` with `anomaly_type="asymmetric_transit"`, the correct
quarter, and at least one literature reference related to a non-planetary hypothesis.

### Tests for User Story 4 (write first — confirm red) ⚠️

- [ ] T049 [P] [US4] Write unit tests in `tests/unit/test_anomaly_detector.py`: symmetric synthetic light curve → `None` returned; asymmetric synthetic transit (ingress ≠ egress by 3σ) → `AnomalyRecord` with `anomaly_type="asymmetric_transit"` and correct `data_quarter`; aperiodic signal → `AnomalyRecord` with `anomaly_type="aperiodicity"`
- [ ] T050 [US4] Write integration test in `tests/integration/test_anomaly.py`: known asymmetric-transit KOI → report contains `AnomalyRecord` with non-empty `hypotheses_searched` and non-empty `literature_references`

### Implementation for User Story 4

- [ ] T051 [P] [US4] Implement `anomaly_detector.py` in `src/tools/anomaly_detector.py`: BLS periodogram residuals for aperiodicity detection; ingress/egress asymmetry ratio; threshold from `AgentConfig.anomaly_sigma_threshold`; returns `AnomalyRecord` or `None` (makes T049 green) (depends T021, T014)
- [ ] T052 [US4] Update Observer agent in `src/agents/observer.py` to call `anomaly_detector`; attach `AnomalyRecord` list to `ObserverOutput.anomaly_records`; emit lineage entry for anomaly detection tool call (depends T051, T040)
- [ ] T053 [US4] Update Scholar agent in `src/agents/scholar.py` to accept `anomaly_directives` from `ScholarInput`; inject hypothesis terms (e.g., "stellar variability", "dust disk", "eclipsing binary") into at least one generated query when directives are non-empty (depends T050, T041)
- [ ] T054 [US4] Update DAG in `src/dag/pipeline.py` to pass `ObserverOutput.anomaly_records` as `anomaly_directives` to `ScholarInput` (depends T052, T053, T043)

**Checkpoint**: US1–US4 each independently testable. T050 integration test is green. Anomaly reports are produced for edge-case candidates.

---

## Phase 7: User Story 5 — Benchmark Operator Measures System Accuracy (Priority: P3)

**Goal**: Standalone Benchmark Runner evaluates the full pipeline against ≥40 known objects,
produces a Confusion Matrix + F1, and raises `RegressionError` if F1 drops > 5 points.

**Independent Test**: Run `uv run python -m src.benchmark.runner`. Exits 0 (no regression).
Prints Confusion Matrix + F1. Writes `BenchmarkResult` JSON to `benchmarks/history/`.

### Tests for User Story 5 (write first — confirm red) ⚠️

- [ ] T055 [P] [US5] Write unit tests in `tests/unit/test_metrics.py`: perfect predictions → F1 = 1.0; all wrong → F1 = 0.0; mixed known case → hand-calculated F1 matches; all-zero predictions raise `ZeroDivisionError` guard
- [ ] T056 [P] [US5] Write unit test in `tests/unit/test_runner.py`: `RegressionError` raised when current F1 = 0.75 and prior = 0.85; no error when current = 0.82 and prior = 0.85
- [ ] T057 [US5] Write integration test in `tests/integration/test_benchmark.py`: 2-object subset run → `BenchmarkResult` schema validates; JSON written to `benchmarks/history/`; per-object results have correct target IDs

### Implementation for User Story 5

- [ ] T058 [P] [US5] Implement `metrics.py` in `src/benchmark/metrics.py`: compute Confusion Matrix (TP/FP/TN/FN) + precision + recall + F1 from list of `(prediction, ground_truth)` pairs; handle zero-division guard (makes T055 green) (depends T016)
- [ ] T059 [P] [US5] Implement `dataset.py` in `src/benchmark/dataset.py`: download NASA KOI Cumulative Table via TAP service; filter to ≥20 `CONFIRMED` + ≥20 `FALSE POSITIVE`; build + validate `GoldenDataset` schema; store `dataset_version` = download date + row count hash (depends T016)
- [ ] T060 [US5] Implement `runner.py` in `src/benchmark/runner.py`: iterate `GoldenDataset.objects`; call full pipeline per object (re-using `pipeline.py`); catch per-object errors and log to `ObjectFailure` list without stopping the run; aggregate `BenchmarkResult`; persist to `benchmarks/history/{run_id}.json` (depends T058, T059, T054)
- [ ] T061 [US5] Implement F1 regression gate in `src/benchmark/runner.py`: load most recent result from `benchmarks/history/`; raise `RegressionError` with delta if F1 regresses > 5 pts (makes T056 green) (depends T060, T018)

**Checkpoint**: All 5 user stories independently functional. T057 integration test is green. Benchmark produces Confusion Matrix.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Cross-story hardening, FR-033 inter-agent contract enforcement, CLI flags, final validation.

- [ ] T062 [P] Implement `validate_input` / `validate_output` contract decorators on all agent node boundaries in `src/agents/base.py`: raise `ValidationContractError` with field name on schema mismatch; add unit tests in `tests/unit/test_agent_base.py`
- [ ] T063 [P] Implement `--validate` flag for `report_generator` CLI in `src/tools/report_generator.py`: programmatically checks all FR-023 mandatory sections present + lineage map path resolves; exits non-zero if any fail
- [ ] T064 [P] Create `config/agents.yaml.example` with documented defaults for all `AgentConfig` fields; add CI step in quickstart.md to verify example is valid against `AgentConfig` schema
- [ ] T065 Write full end-to-end integration test in `tests/integration/test_full_pipeline.py`: one Golden Dataset object with known anomaly AND known conflict → report contains both `AnomalyRecord` and `ConsensusConflictFlag`; Lineage Map passes validation; all output files written to `outputs/`
- [ ] T066 [P] Run `uv run ruff check src/ tests/` and fix all lint issues; run `uv run pytest` and confirm all tests green

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — first story, delivers MVP pipeline
- **US2 (Phase 4)**: Depends on Phase 3 (Observer + Scholar agents must exist to add lineage emissions)
- **US3 (Phase 5)**: Depends on Phase 3 (Synthesizer must exist to add conflict logic)
- **US4 (Phase 6)**: Depends on Phase 3 (Observer must exist to add anomaly detection)
- **US5 (Phase 7)**: Depends on Phase 3 (full pipeline must exist to benchmark)
- **Polish (Phase 8)**: Depends on all user stories complete

### Within US1 (Critical Path)

```
T026 (transit fitter) → T027 (Observer) → T033 (Synthesizer) → T034 (Validator) → T035 (report gen) → T036 (DAG)
T028–T030 (RAG tools) → T031 (Distillation) → T032 (Scholar) ──────────────────────────────────────────────↑
```

### Parallel Opportunities per Story

**Foundational (Phase 2)**:
```
T005–T010 (schema tests)    — all parallel
T011–T017 (schema impl)     — all parallel
T018–T019 (errors + base)   — T019 depends T018
T020–T022 (MCP)             — T021 + T022 parallel after T020
```

**US1 (Phase 3)**:
```
T026 (transit fitter) ──┐
T028 (ArXiv tool)    ──┤  both feed into T027 + T031 independently
T029 (ADS tool)      ──┘
T024 + T025 (tests)     — parallel
```

**US5 (Phase 7)**:
```
T055–T056 (unit tests) — parallel
T058 (metrics) ────────┐
T059 (dataset) ─────── both parallel, both feed T060
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (schemas + MCP) — CRITICAL gate
3. Complete Phase 3: US1 — basic Vetting Report produced
4. **STOP and VALIDATE**: `uv run python -m src.dag.pipeline --target-id KIC-11442793 --catalog KIC`
5. Confirm report.md + PNG written; review reasoning trace

### Incremental Delivery

1. Setup + Foundational → foundation locked
2. US1 → basic Vetting Report → demo/validate (MVP)
3. US2 → Lineage Map → provenance validated
4. US3 + US4 (can be parallelised) → conflict + anomaly → scientific rigour demonstrated
5. US5 → Benchmark Runner → accuracy quantified
6. Polish → production-ready

### Parallel Team Strategy

After Phase 2 completes:
- **Stream A**: US1 → US2 (core pipeline + lineage)
- **Stream B**: US3 (conflict detection, requires Synthesizer from US1)
- **Stream C**: US4 (anomaly detection, requires Observer from US1)
- **Stream D**: US5 (benchmark, requires full pipeline from US1)

---

## Notes

- `[P]` = different files, no incomplete dependencies — safe to run in parallel
- `[Story]` label maps every task to a user story for traceability
- Tests MUST be written and CONFIRMED RED before implementation (Constitution Principle III)
- Commit after each task or logical group; reference task ID in commit message (e.g., `T026: implement transit fitter`)
- Stop at each story checkpoint to validate independently before proceeding
- No task should modify the same file as another parallel task in the same phase

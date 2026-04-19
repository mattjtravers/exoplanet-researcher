# Tasks: PydanticAI Migration

**Input**: Design documents from `/specs/002-pydantic-ai-migration/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Test tasks are included — FR-008, FR-009, FR-010 in spec.md explicitly require new and updated test modules.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup (New Directory Structure)

**Purpose**: Create the three new directories this feature introduces. The `src/` and `tests/` roots already exist.

- [x] T001 [P] Create `config/agent_specs/` directory (mkdir -p config/agent_specs)
- [x] T002 [P] Create `src/evals/` directory (mkdir -p src/evals)
- [x] T003 [P] Create `tests/evals/` directory with `tests/evals/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: The single shared schema module that every tool, caller, and test in Phases 3–5 depends on. No user story work can begin until this phase is complete.

**⚠️ CRITICAL**: Phases 3, 4, and 5 all import from `src/schemas/tools.py`.

- [x] T004 Create `src/schemas/tools.py` — define five Pydantic models: `LightCurveResult`, `StellarPropertiesResult`, `TransitFitResult`, `LiteraturePaper`, `LiteratureSearchResult` (see data-model.md for all fields, types, and constraints)

**Checkpoint**: `python -c "from src.schemas.tools import LightCurveResult, TransitFitResult; print('OK')"` must succeed.

---

## Phase 3: User Story 1 — Typed Tool Return Values (Priority: P1) 🎯 MVP

**Goal**: All four tool modules return typed Pydantic model instances; all callers updated to attribute access; test suite updated and passing.

**Independent Test**: Run `cd src && pytest tests/unit/test_transit_fitter.py tests/unit/test_schemas_tools.py -v` — all tests pass with attribute-style assertions.

### Tests for User Story 1

> **Write test_schemas_tools.py before (or alongside) T005–T008 to confirm models validate correctly**

- [x] T005 [P] [US1] Create `tests/unit/test_schemas_tools.py` — unit tests validating construction, field access, and validation errors for all five models in `src/schemas/tools.py` (depends on T004)
- [x] T006 [P] [US1] Update `tests/unit/test_transit_fitter.py` — replace all dict-style assertions (`result["key"]`, `result.get("key")`) with attribute access (`result.key`) across all 6 tests (depends on T004; write updates, confirm they FAIL before T010 is done)

### Implementation for User Story 1

- [x] T007 [P] [US1] Update `src/tools/transit_fitter.py` — change `fit_transit()` return type from `dict` to `TransitFitResult`; replace the `return {...}` dict literal with `return TransitFitResult(target_id=target_id, period_days=best_period, depth=depth, duration_hours=best_duration * 24.0, rp_rs=rp_rs, tool_call_id=str(uuid.uuid4()))` (depends on T004)
- [x] T008 [P] [US1] Update `src/mcp/tools/lightkurve_tool.py` — change `get_light_curve()` return type from `dict` to `LightCurveResult`; replace the `return {...}` dict literal with `return LightCurveResult(**{...})` (depends on T004)
- [x] T009 [P] [US1] Update `src/mcp/tools/archive_tool.py` — change `get_stellar_properties()` return type from `dict` to `StellarPropertiesResult`; replace the `return {...}` dict literal with `return StellarPropertiesResult(**{...})` (depends on T004)
- [x] T010 [P] [US1] Update `src/tools/rag_tools.py` — change `search_arxiv()` and `search_ads()` return types from `list[tuple[str, str]]` to `list[LiteraturePaper]`; wrap each tuple result as `LiteraturePaper(source_id=..., abstract=..., source_type="arxiv"/"ads")` (depends on T004)
- [x] T011 [US1] Update `src/tools/rag_tools.py` — change `iterative_search()` return type from `tuple[list, list]` to `LiteratureSearchResult`; replace `return all_results, queries_issued` with `return LiteratureSearchResult(papers=all_results, queries_issued=queries_issued)` where `all_results` is now `list[LiteraturePaper]` (depends on T010)
- [x] T012 [US1] Update `src/agents/observer.py` — replace all dict-style access on `lc_data` and `transit_params` with attribute access: `lc_data["quarter"]` → `lc_data.quarter`, `lc_data["time"]` → `lc_data.time`, `transit_params["tool_call_id"]` → `transit_params.tool_call_id`, `transit_params.get("period_days")` → `transit_params.period_days`, etc. (depends on T007, T008)
- [x] T013 [US1] Update `src/agents/scholar.py` — replace `raw_results, queries_issued = iterative_search(...)` with `search_result = iterative_search(...)`; then `raw_papers = [(p.source_id, p.abstract) for p in search_result.papers]`; `queries_issued = search_result.queries_issued`; pass `raw_papers` to `distillation.run()` (depends on T011)
- [x] T014 [US1] Update `src/mcp/server.py` — change `call_tool()` return type annotation from `-> dict` to `-> Any` (already imported); update docstring to reflect typed model returns (depends on T008, T009)

**Checkpoint**: `cd src && pytest tests/unit/test_transit_fitter.py tests/unit/test_schemas_tools.py -v` — all pass. `ruff check .` — clean.

---

## Phase 4: User Story 2 — PydanticAI Agent for Distillation (Priority: P2)

**Goal**: `DistillationAgent._llm_distil()` uses a PydanticAI `Agent` loaded from YAML spec, with typed `DistillationExtraction` output replacing manual JSON parsing.

**Independent Test**: `python -c "from src.agents.distillation import DistillationAgent; print('import OK')"` succeeds without `ANTHROPIC_API_KEY`. With a mocked agent, the distillation path produces a `DistilledLiteratureRecord` with correctly populated fields.

### Configuration for User Story 2

- [x] T015 [P] [US2] Create `config/agent_specs/distillation.yaml` — set `model: anthropic:claude-haiku-4-5-20251001`, write `system_prompt` instructing the LLM to extract parameters and return `extracted_parameters`, `disposition_notes`, `citation_string`; set `retries: 2` (depends on T001)
- [x] T016 [P] [US2] Create `config/agent_specs/scholar.yaml` — documentation-only spec with `model: anthropic:claude-sonnet-4-6`, brief system prompt describing Scholar's role, `retries: 1` (depends on T001)

### Implementation for User Story 2

- [x] T017 [US2] Add `DistillationExtraction` Pydantic model to `src/agents/distillation.py` — fields: `extracted_parameters: dict[str, float | str] = {}`, `disposition_notes: str | None = None`, `citation_string: str` (depends on T004)
- [x] T018 [US2] Add `_build_distillation_agent()` and `_get_distillation_agent()` lazy singleton functions to `src/agents/distillation.py` — load YAML from `Path(__file__).parent.parent.parent / "config/agent_specs/distillation.yaml"` using `yaml.safe_load()`; construct `Agent(model=spec["model"], output_type=DistillationExtraction, system_prompt=spec["system_prompt"], retries=spec.get("retries", 2))` (depends on T015, T017)
- [x] T019 [US2] Replace `_llm_distil()` body in `src/agents/distillation.py` — remove the raw `anthropic.Anthropic()` call and `json.loads()` parsing; add `from pydantic_ai import UsageLimits`; call `agent.run_sync(prompt, usage_limits=UsageLimits(total_tokens_limit=remaining))`; use `result.output` (typed `DistillationExtraction`) to populate `DistilledLiteratureRecord` fields (depends on T018)
- [x] T020 [US2] Update token tracking in `src/agents/distillation.py` `run()` method — replace `self.consume_tokens(estimated_tokens)` with `self.consume_tokens(record.distillation_token_count)` to use the actual token count from `result.usage().total_tokens` rather than the character-based pre-estimate; update `_llm_distil()` to set `distillation_token_count=result.usage().total_tokens` (depends on T019)

**Checkpoint**: `python -c "from src.agents.distillation import DistillationAgent; print('OK')"` — succeeds without API key. `cd src && pytest tests/unit/ -v` — all unit tests pass.

---

## Phase 5: User Story 3 — pydantic_evals Evaluation Module (Priority: P3)

**Goal**: `src/evals/` module exists with named `Evaluator` classes and `Dataset` builders for distillation and pipeline quality evaluation, runnable without live LLM calls.

**Independent Test**: `python -c "from src.evals.distillation_eval import build_distillation_dataset; d = build_distillation_dataset(); print(d)"` — completes in < 1 second, prints Dataset summary.

### Implementation for User Story 3

- [x] T021 [P] [US3] Create `src/evals/__init__.py` — empty init file exporting nothing (depends on T002)
- [x] T022 [P] [US3] Create `src/evals/distillation_eval.py` — define `DistillationInput(BaseModel)` with `source_id`, `abstract`, `target_star_id` fields; define `HasExtractedPeriod(Evaluator[DistillationInput, DistilledLiteratureRecord, None])` evaluator with `name = "has_period"` and `evaluate()` returning `EvaluationResult(score=1.0)` if `"period_days" in ctx.output.extracted_parameters` else `0.0`; implement `build_distillation_dataset() -> Dataset` returning a `Dataset` with at least one sample `Case` and `evaluators=(HasExtractedPeriod(),)` (depends on T002, T017)
- [x] T023 [P] [US3] Create `src/evals/pipeline_eval.py` — import `Dataset`, `Case`, `EqualsExpected` from `pydantic_evals`; implement `build_pipeline_dataset(golden: GoldenDataset) -> Dataset` building cases from `golden.objects` with `inputs={"target_id": obj.target_id, "catalog": "KIC"}` and `expected_output=obj.ground_truth`, using `evaluators=(EqualsExpected(),)` (depends on T002)

### Tests for User Story 3

- [x] T024 [US3] Create `tests/evals/test_distillation_eval.py` — test that `build_distillation_dataset()` returns a `Dataset` instance; test that `HasExtractedPeriod` scores `1.0` when `extracted_parameters` contains `period_days`; test that it scores `0.0` when `period_days` is absent — all without LLM calls (depends on T003, T022)

**Checkpoint**: `cd src && pytest tests/evals/ -v` — all pass. `python -c "from src.evals.distillation_eval import build_distillation_dataset; print(build_distillation_dataset())"` — succeeds.

---

## Phase 6: User Story 4 — LangChain Removal (Priority: P4)

**Goal**: `pyproject.toml` no longer declares `langgraph`, `langchain`, or `langchain-anthropic`; `pydantic-evals` is explicitly listed; full test suite remains green.

**Independent Test**: `grep -r "langchain\|langgraph" src/` returns zero results. `cd src && pytest tests/unit/ -v` — all pass.

- [x] T025 [US4] Update `pyproject.toml` — remove the three lines `"langgraph>=0.2.0"`, `"langchain>=0.3.0"`, `"langchain-anthropic>=0.3.0"` from `dependencies`; add `"pydantic-evals>=0.0.14"` after the `"pydantic-ai>=0.0.14"` line

**Checkpoint**: `grep -r "langchain\|langgraph" pyproject.toml` returns empty. `cd src && pytest tests/unit/ -v && ruff check .` — both pass.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Constitution amendment, feature spec updates, and final verification across all user stories.

- [x] T026 [P] Amend `.specify/memory/constitution.md` — MINOR bump to v1.3.0: (1) expand Principle II to add "all tool return values MUST use typed Pydantic models (no bare `dict` or `tuple` returns from tools)"; (2) rewrite Principle IV to replace "The system MUST be a LangGraph DAG" with "The system MUST use a DAG-style sequential orchestration. LLM-backed agents MUST be defined using PydanticAI `Agent` with YAML Agent Specs (`config/agent_specs/*.yaml`)"; (3) add new Principle X: "Agent output quality MUST be measurable. At least one `pydantic_evals.Dataset` MUST exist for each LLM-backed agent, with named `Evaluator` classes"; (4) update tech stack table Orchestration row to "PydanticAI Agent Specs + sequential DAG"; add Evaluation row "pydantic_evals — named Dataset + Evaluator per LLM-backed agent"; update version header and Last Amended date
- [x] T027 [P] Update `specs/001-xpi-agentic-vetting/spec.md` — remove all LangGraph/LangChain references; add FRs for typed tool returns (all tools must return Pydantic models), YAML agent specs, and pydantic_evals evaluations
- [x] T028 Update `specs/001-xpi-agentic-vetting/plan.md` — update tech stack section: replace "LangChain Deep Agents / LangGraph" with "PydanticAI Agent Specs (`config/agent_specs/*.yaml`) + sequential DAG"; add pydantic-evals to Primary Dependencies; remove langgraph/langchain entries
- [x] T029 Run full verification suite: `cd src && pytest tests/unit/ tests/evals/ -v` (all must pass); `ruff check .` (must be clean); `python -c "from src.schemas.tools import LightCurveResult; print('OK')"` and `python -c "from src.evals.distillation_eval import build_distillation_dataset; print(build_distillation_dataset())"` (both must succeed)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — T001, T002, T003 can all run in parallel immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 completion — BLOCKS Phase 3 (tool functions and tests all import from `src/schemas/tools.py`)
- **Phase 3 (US1)**: Depends on Phase 2 — T005–T006 (tests) can start with T007–T011 (tool functions) in parallel
- **Phase 4 (US2)**: T015–T016 (YAML files) can start after Phase 1; T017–T020 depend on T004 (Phase 2 foundational)
- **Phase 5 (US3)**: T021–T023 depend on T002 (Phase 1); T022 also depends on T017 (Phase 4)
- **Phase 6 (US4)**: No code dependencies — safe to do any time after Phase 3 checkpoint passes
- **Phase 7 (Polish)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends on T004 (foundational schema module) only
- **US2 (P2)**: T015–T016 depend on T001 (Setup); T017–T020 depend on T004 (Phase 2); T018 depends on T015
- **US3 (P3)**: T021, T023 depend on T002–T003 (Setup); T022 depends on T017 (US2 partial)
- **US4 (P4)**: No inter-story dependencies — can be done at any time

### Within Each User Story

- Tool function changes (T007–T011) and test updates (T005–T006) can be written in parallel
- Caller updates (T012–T014) depend on the tool function changes completing
- YAML configs (T015–T016) are independent of code changes
- `DistillationExtraction` model (T017) must exist before agent construction (T018)
- Agent construction (T018) must be complete before `_llm_distil()` replacement (T019)
- Token tracking update (T020) is the last step in the distillation chain

### Parallel Opportunities

```text
T001 ──┐
T002 ──┤── (all Phase 1 in parallel)
T003 ──┘
         │
         └── T004 ──┐
                    ├── T005 [P], T006 [P]       (US1 tests)
                    ├── T007 [P], T008 [P],       (US1 tool functions)
                    │   T009 [P], T010 [P]
                    │        │
                    │        └── T011 ── T013     (US1 callers)
                    │   T007 ─────── T012         (observer caller)
                    │   T008,T009 ── T014         (server annotation)
                    ├── T017 ── T018 ── T019 ── T020   (US2 chain)
                    └── T022 (needs T017)

T015 [P], T016 [P]   (US2 config — parallel with everything after T001)
T021 [P], T023 [P]   (US3 init files — parallel with everything after T002–T003)
T024 (needs T022)
T025 (US4 — any time after Phase 3 checkpoint)
T026 [P], T027 [P]   (Polish — parallel with each other)
T028, T029           (sequential after T026–T027)
```

---

## Parallel Example: User Story 1

```bash
# Launch tool function updates together (all different files):
Task T007: Update src/tools/transit_fitter.py
Task T008: Update src/mcp/tools/lightkurve_tool.py
Task T009: Update src/mcp/tools/archive_tool.py
Task T010: Update src/tools/rag_tools.py (search_arxiv, search_ads)

# Simultaneously launch test updates:
Task T005: Create tests/unit/test_schemas_tools.py
Task T006: Update tests/unit/test_transit_fitter.py
```

## Parallel Example: User Story 2

```bash
# Config files are pure data — launch immediately after T001:
Task T015: Create config/agent_specs/distillation.yaml
Task T016: Create config/agent_specs/scholar.yaml

# Then the code chain is sequential:
T017 → T018 → T019 → T020
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003) — ~5 min
2. Complete Phase 2: Foundational (T004) — ~15 min
3. Complete Phase 3: User Story 1 (T005–T014) — ~45 min
4. **STOP and VALIDATE**: `pytest tests/unit/test_transit_fitter.py tests/unit/test_schemas_tools.py -v` — all green
5. This delivers: typed tool returns, all callers updated, tests passing — a complete, reviewable increment

### Incremental Delivery

1. Setup + Foundational → schema module ready
2. US1 → typed tool returns + callers + tests → **MVP deliverable**
3. US2 → PydanticAI distillation agent → LLM path no longer uses raw SDK
4. US3 → evaluation module → quality measurement capability added
5. US4 → LangChain removed → clean dependency tree
6. Polish → constitution + spec updates → all artifacts consistent

### Verification Checkpoints

```bash
# After US1 (T014 complete):
cd src && pytest tests/unit/test_transit_fitter.py tests/unit/test_schemas_tools.py -v && ruff check .

# After US2 (T020 complete):
python -c "from src.agents.distillation import DistillationAgent; print('OK')"
cd src && pytest tests/unit/ -v && ruff check .

# After US3 (T024 complete):
python -c "from src.evals.distillation_eval import build_distillation_dataset; print(build_distillation_dataset())"
cd src && pytest tests/unit/ tests/evals/ -v

# After US4 (T025 complete):
grep -r "langchain\|langgraph" pyproject.toml  # must return empty
cd src && pytest tests/unit/ tests/evals/ -v && ruff check .

# Final (T029):
cd src && pytest tests/unit/ tests/evals/ -v && ruff check .
```

---

## Notes

- `[P]` tasks operate on different files with no shared-file conflicts — safe to parallelize
- `[US]` label maps each task to its user story for traceability and independent review
- T006 (test_transit_fitter.py updates) should be written and confirmed FAILING before T007 is done — this satisfies Constitution Principle III (test-first)
- T004 is the single critical-path blocker — prioritize it above all other work
- US4 (T025) has zero code risk — `langgraph`, `langchain`, `langchain-anthropic` are confirmed unimported in `src/`
- The constitution amendment (T026) is a PR-blocking requirement per governance rules before merge

# Feature Specification: PydanticAI Migration

**Feature Branch**: `002-pydantic-ai-migration`  
**Created**: 2026-04-19  
**Status**: Draft  
**Input**: Incorporate Pydantic AI features into the current architecture — typed tool returns, YAML agent specs, pydantic_evals evaluations, LangChain removal.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Typed Tool Return Values (Priority: P1)

As a developer consuming tool output, I receive a structured, validated Pydantic model instead of a raw `dict` or `tuple`, so I can access fields by attribute, get immediate type errors on bad data, and write unambiguous tests.

**Why this priority**: Tools are the lowest-level data contract. Every agent and test depends on tool outputs being correct. Typed returns eliminate an entire class of runtime `KeyError` and `None`-access bugs.

**Independent Test**: Can be fully tested by running the unit test suite against the four changed tool modules and verifying attribute-style access passes where dict-style access previously passed.

**Acceptance Scenarios**:

1. **Given** `get_light_curve()` is called with a valid target, **When** the result is returned, **Then** the return value is a `LightCurveResult` instance with fields accessible as attributes (`result.target_id`, `result.flux`), not as dict keys.
2. **Given** `fit_transit()` is called, **When** the result is returned, **Then** constructing a `TransitFitResult` with invalid field types raises a validation error, not a silent bad value.
3. **Given** `iterative_search()` is called, **When** the result is returned, **Then** `result.papers` is a typed list of literature models and `result.queries_issued` is a list of strings.

---

### User Story 2 - PydanticAI Agent for Distillation (Priority: P2)

As a researcher running the pipeline, the distillation step uses a PydanticAI `Agent` with a typed output so that LLM responses are automatically parsed and validated, eliminating manual JSON parsing and silent extraction failures.

**Why this priority**: The distillation agent is the only component making raw LLM calls with manual JSON parsing — the highest-risk point for silent data corruption.

**Independent Test**: Can be tested by unit-mocking the agent run call and asserting the resulting distillation record is populated from the typed extraction model.

**Acceptance Scenarios**:

1. **Given** the distillation agent is initialised from `config/agent_specs/distillation.yaml`, **When** the YAML is loaded, **Then** the agent model identifier, system prompt, and retry count match the YAML values.
2. **Given** a valid paper abstract is provided, **When** distillation runs, **Then** `extracted_parameters` and `citation_string` are populated from the typed output model, not from manual JSON parsing.
3. **Given** the LLM returns malformed output, **When** validation fails, **Then** the agent retries up to the configured number of times before raising a structured error.

---

### User Story 3 - pydantic_evals Evaluation Module (Priority: P3)

As a researcher or CI reviewer, I can run a formal evaluation dataset against the distillation agent and the full pipeline to get a quantitative quality score — without writing ad-hoc quality checks or needing a live benchmark run.

**Why this priority**: Evaluation is additive and does not block existing functionality. It provides measurable quality assurance before future model upgrades.

**Independent Test**: Can be fully tested by constructing the evaluation datasets and verifying they are correctly wired without making real LLM calls.

**Acceptance Scenarios**:

1. **Given** the distillation evaluation dataset is built, **When** it is inspected, **Then** it contains at least one test case with a named `HasExtractedPeriod` evaluator attached.
2. **Given** the evaluation suite is run with mocked output containing `period_days`, **When** the evaluator runs, **Then** it returns a score of `1.0`.
3. **Given** the evaluation suite is run with mocked output missing `period_days`, **When** the evaluator runs, **Then** it returns a score of `0.0`.

---

### User Story 4 - LangChain Removal (Priority: P4)

As a maintainer, the codebase no longer declares or imports `langgraph`, `langchain`, or `langchain-anthropic`, so the dependency tree is smaller, there are no unused packages to audit, and the stated tech stack matches reality.

**Why this priority**: LangChain packages are not imported anywhere in `src/` — this is pure dead-weight removal with no functional risk.

**Independent Test**: Can be verified by grepping `src/` for any `langchain` or `langgraph` import and confirming zero matches, then confirming the test suite remains green.

**Acceptance Scenarios**:

1. **Given** the updated dependency configuration is installed, **When** the package list is inspected, **Then** `langgraph`, `langchain`, and `langchain-anthropic` are absent.
2. **Given** the full test suite is run after removal, **When** all tests complete, **Then** no import errors or missing-dependency failures occur.

---

### Edge Cases

- What happens when the distillation agent spec YAML file is missing at runtime? The system should raise a clear file-not-found error rather than a generic attribute error.
- How does the system handle an LLM response that passes initial parsing but fails typed validation? The agent retries up to the configured maximum before raising a structured error.
- What happens when `iterative_search()` returns zero results? The search result model must represent an empty list — callers must not assume a non-empty result.
- How are existing dict-style test assertions handled after tool return types change? All affected assertions must be updated to attribute access in the same change set to keep the suite green.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All tool functions (`get_light_curve`, `get_stellar_properties`, `fit_transit`, `search_arxiv`, `search_ads`, `iterative_search`) MUST return typed Pydantic model instances, not raw `dict` or `tuple` values.
- **FR-002**: Five Pydantic models MUST be defined in a single shared module: `LightCurveResult`, `StellarPropertiesResult`, `TransitFitResult`, `LiteraturePaper`, `LiteratureSearchResult`.
- **FR-003**: The distillation agent MUST be implemented as a PydanticAI `Agent` with a typed output type, configured via a YAML spec file at `config/agent_specs/distillation.yaml`.
- **FR-004**: YAML agent spec files MUST exist for all LLM-backed agents, declaring at minimum: model identifier, system prompt, and retry count.
- **FR-005**: A `src/evals/` module MUST exist containing at least `distillation_eval.py` (per-paper quality) and `pipeline_eval.py` (full pipeline against golden dataset), each using named evaluator classes.
- **FR-006**: All callers of changed tool functions MUST be updated to use attribute access on the new model types.
- **FR-007**: The project dependency configuration MUST NOT declare `langgraph`, `langchain`, or `langchain-anthropic`. The `pydantic-evals` package MUST be listed explicitly.
- **FR-008**: The full unit test suite (110 tests) MUST remain green after all changes. Dict-style assertions in transit fitter tests MUST be updated to attribute access.
- **FR-009**: A new test module MUST validate all five tool result Pydantic models for construction and field validation.
- **FR-010**: A new evaluation test module MUST verify dataset construction without making real LLM calls.

### Key Entities

- **LightCurveResult**: Structured return from the light curve tool — target ID, quarter, time/flux arrays, cadence type, and tool call ID.
- **StellarPropertiesResult**: Structured return from the archive tool — stellar radius, mass, temperature, log g, metallicity, source catalog, and tool call ID.
- **TransitFitResult**: Structured return from the transit fitter — target ID, period, depth, duration, and radius ratio.
- **LiteraturePaper**: Single literature result — source ID, abstract text, and source type.
- **LiteratureSearchResult**: Aggregated search result — list of literature papers and list of queries issued.
- **DistillationExtraction**: LLM-structured output — extracted numeric/string parameters, disposition notes, and citation string.
- **Agent Spec (YAML)**: Declarative configuration for an LLM-backed agent — model identifier, system prompt, and retry policy.
- **Evaluation Dataset**: A structured dataset paired with named evaluator classes that produce numeric quality scores for agent outputs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 110 existing unit tests pass after migration, with only assertion syntax updated from dict-style to attribute access where required.
- **SC-002**: Zero `langchain`, `langgraph`, or `langchain-anthropic` imports exist anywhere in the source directory after migration.
- **SC-003**: Every changed tool function returns a typed model instance — verified by static analysis passing with zero errors.
- **SC-004**: The distillation evaluation dataset instantiates and its evaluators produce a numeric score without any live LLM call, completing in under 1 second.
- **SC-005**: The distillation agent YAML spec loads successfully and produces a correctly configured agent instance, verified by a smoke-test import.
- **SC-006**: Exactly one new dependency is added (`pydantic-evals`) and exactly three are removed (`langgraph`, `langchain`, `langchain-anthropic`).

## Assumptions

- LangChain packages are confirmed unused in `src/` — no hidden runtime imports exist via dynamic loading or plugin systems.
- The existing `pydantic-ai` version already satisfies the PydanticAI `Agent` API used in this feature.
- `pydantic-evals` is versioned compatibly with the installed `pydantic-ai` version and can be added without dependency resolver conflicts.
- The `AgentBase`, `SynthesizerAgent`, `ValidatorAgent`, and DAG pipeline are stable and require no changes beyond caller updates for new return types.
- Token budget tracking in the distillation agent will use actual token counts from the PydanticAI result rather than pre-call estimates.
- The benchmark runner is not changed; the new `src/evals/` module is additive and runs independently.
- The YAML agent spec for the scholar agent is documentation-only (no live LLM calls in scholar); no scholar code changes are required beyond caller updates.

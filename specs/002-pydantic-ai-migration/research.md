# Research: PydanticAI Migration

**Branch**: `002-pydantic-ai-migration` | **Date**: 2026-04-19

## Phase 0 Findings

### Finding 1 — LangChain/LangGraph are truly dead dependencies

**Decision**: Remove `langgraph`, `langchain`, `langchain-anthropic` outright.

**Evidence**: Full `grep` of `src/` finds zero imports of any `langchain` or `langgraph` symbol. The packages are declared in `pyproject.toml` but have never been used. The DAG pipeline in `src/dag/pipeline.py` and all agents in `src/agents/` use plain Python — no LangGraph nodes, edges, or StateGraph objects anywhere.

**Rationale**: Zero-risk removal. No callers to update. Reduces install footprint and eliminates three packages from the dependency audit surface.

**Alternatives considered**: Keeping stubs for "future use" — rejected per Principle V (YAGNI). The system already has a working sequential DAG in `src/dag/pipeline.py` without LangGraph.

---

### Finding 2 — PydanticAI is already installed; only `Agent` class needs wiring

**Decision**: Use `pydantic_ai.Agent` with `output_type=DistillationExtraction` for the distillation LLM call.

**Evidence**: `pydantic-ai>=0.0.14` is in `pyproject.toml` and importable. The `DistillationAgent._llm_distil()` method currently makes a raw `anthropic.Anthropic()` call and does manual `json.loads()` on the response — the highest-risk fragile path in the codebase. PydanticAI's `Agent` provides built-in retry, output validation, and `UsageLimits` for token budgeting.

**Rationale**: Direct replacement of the only raw-SDK LLM call. Typed `output_type` eliminates manual JSON parsing and silent `{}` fallback on `JSONDecodeError`.

**Alternatives considered**: Keep raw anthropic SDK + add manual Pydantic validation — rejected because it duplicates what PydanticAI `Agent` already provides and leaves the retry logic as a manual concern.

---

### Finding 3 — Tool functions return raw `dict`/`tuple`; callers use dict access throughout

**Decision**: Add `src/schemas/tools.py` with five new Pydantic models; update all four tool modules; update all callers.

**Evidence**:
- `fit_transit()` returns `dict` with 6 keys. Observer accesses via `transit_params["tool_call_id"]`, `transit_params.get("period_days")`, etc.
- `get_light_curve()` returns `dict` with 7 keys. Observer accesses via `lc_data["quarter"]`, `lc_data["time"]`, etc.
- `get_stellar_properties()` returns `dict` with 7 keys. Used by archive tool consumers.
- `search_arxiv()` / `search_ads()` return `list[tuple[str, str]]`. Scholar passes these directly as `raw_papers` to `DistillationAgent.run()`.
- `iterative_search()` returns `tuple[list, list]` unpacked as `raw_results, queries_issued`.

**Caller impact matrix**:

| File | Current access | Post-migration access |
|------|---------------|----------------------|
| `src/agents/observer.py:87` | `lc_data["quarter"]` | `lc_data.quarter` |
| `src/agents/observer.py:90-95` | `lc_data["time"]`, `["flux"]`, `["flux_err"]` | `lc_data.time`, `.flux`, `.flux_err` |
| `src/agents/observer.py:97` | `transit_params["tool_call_id"]` | `transit_params.tool_call_id` |
| `src/agents/observer.py:101-109` | `transit_params.get(param_name)` | `getattr(transit_params, param_name)` |
| `src/agents/observer.py:133-136` | `lc_data["time"]`, `lc_data["flux"]`, etc. | attribute access |
| `src/agents/observer.py:142-144` | `transit_params.get("depth")`, etc. | `transit_params.depth`, etc. |
| `src/agents/scholar.py:61` | `raw_results, queries_issued = iterative_search(...)` | `search_result = iterative_search(...)`; `raw_results = [(p.source_id, p.abstract) for p in search_result.papers]`; `queries_issued = search_result.queries_issued` |
| `src/mcp/server.py:23` | `-> dict` return type | `-> Any` |
| `tests/unit/test_transit_fitter.py` | `result["period_days"]`, `result.get("depth")`, etc. | `result.period_days`, `result.depth`, etc. |

**Alternatives considered**: Leave tool functions returning `dict` and just add runtime validation — rejected because it defeats type safety at the exact boundary where it matters most (Principle II).

---

### Finding 4 — `pydantic-evals` API compatible with installed `pydantic-ai`

**Decision**: Add `pydantic-evals>=0.0.14` matching the `pydantic-ai` lower bound already in use.

**Evidence**: `pydantic-evals` is the companion evaluation library shipped alongside `pydantic-ai`. The `Dataset`, `Case`, `Evaluator`, `EvaluatorContext`, and `EvaluationResult` classes are the public API. The `EqualsExpected` built-in evaluator handles pipeline-level evaluation. No API version conflicts expected since both packages share the same version series.

**Rationale**: The evaluation module (`src/evals/`) is additive — it imports `pydantic_evals` independently and does not touch the benchmark runner or any existing module.

**Alternatives considered**: Use pytest parametrize + manual score accumulation — rejected because it lacks the structured `Dataset`/`Evaluator` abstraction required by Principle X (new constitution principle).

---

### Finding 5 — YAML Agent Spec loading pattern

**Decision**: Load YAML at first use (lazy singleton) via `_build_distillation_agent()`.

**Evidence**: The distillation agent is imported at module level in `scholar.py` via `from src.agents.distillation import DistillationAgent`. Agent construction (which loads the YAML) should not happen at import time to avoid requiring `config/agent_specs/distillation.yaml` during test collection.

**Rationale**: Lazy singleton pattern (`_distillation_agent: Agent | None = None`) keeps unit tests fast and avoids file-system side effects at import.

**File path convention**: `config/agent_specs/<agent_name>.yaml` relative to repo root. Loaded via `Path(__file__).parent.parent.parent / "config/agent_specs/distillation.yaml"`.

---

### Finding 6 — MCP server `call_tool()` return type annotation

**Decision**: Update `call_tool() -> dict` to `call_tool() -> Any`.

**Evidence**: After `get_light_curve` and `get_stellar_properties` return typed Pydantic models instead of `dict`, the `-> dict` annotation is incorrect. Changing to `-> Any` is accurate and requires no logic change.

**Rationale**: Minimal-change annotation fix. The MCP server does not validate the return type; callers hold typed references from the tool functions directly.

---

### Finding 7 — Constitution amendment required (Principle IV)

**Decision**: Amend constitution (MINOR bump v1.3.0) as part of this feature.

**Evidence**: Constitution Principle IV currently states "The system MUST be a LangGraph DAG." LangGraph was never implemented. The actual orchestration is a plain sequential DAG in `src/dag/pipeline.py`. The plan proposes replacing this principle with a PydanticAI-centric statement. Per governance rules, a MINOR amendment (new principle or material expansion) requires a PR to `.specify/memory/constitution.md`.

**Rationale**: The constitution must reflect the actual stack. Leaving a "MUST use LangGraph" principle while removing LangGraph would make the constitution unenforceable and misleading.

**Amendment scope**:
- Principle II: Add "all tool return values MUST use typed Pydantic models (no bare `dict` or `tuple` returns)"
- Principle IV: Replace LangGraph requirement with "PydanticAI `Agent` with YAML Agent Specs"
- New Principle X: Evaluation-Driven Quality Assurance via `pydantic_evals`
- Tech stack table: Update Orchestration row; add Evaluation row

---

## Resolved NEEDS CLARIFICATION Items

None were raised in the spec — all design decisions were determinable from existing code.

## Unresolved Items

None.

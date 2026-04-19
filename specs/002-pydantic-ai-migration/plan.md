# Implementation Plan: PydanticAI Migration

**Branch**: `002-pydantic-ai-migration` | **Date**: 2026-04-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-pydantic-ai-migration/spec.md`

## Summary

Migrate the XPI codebase from dead LangChain/LangGraph dependencies to a fully PydanticAI-native stack: (1) add typed Pydantic models for all tool return values, (2) replace the raw Anthropic SDK call in `DistillationAgent` with a PydanticAI `Agent` loaded from a YAML spec, (3) add a `src/evals/` module using `pydantic_evals` for measurable agent quality, and (4) remove `langgraph`, `langchain`, `langchain-anthropic` from `pyproject.toml`. Amend the constitution to match the new stack (MINOR bump v1.3.0).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic-ai ≥ 0.0.14, pydantic-evals ≥ 0.0.14 (new), pyyaml ≥ 6.0.0, anthropic ≥ 0.40.0, lightkurve ≥ 2.4.0, astropy ≥ 6.0.0, numpy ≥ 1.26.0, arxiv ≥ 2.1.0, requests ≥ 2.31.0
**Removing**: langgraph, langchain, langchain-anthropic (declared, never imported in `src/`)
**Storage**: N/A (no persistent store; data flows through pipeline in memory)
**Testing**: pytest ≥ 8.0.0, pytest-asyncio
**Target Platform**: GitHub Codespaces / devcontainer (Python 3.11+ image)
**Project Type**: Library / CLI pipeline
**Performance Goals**: Evaluation dataset runs in < 1 second without LLM calls
**Constraints**: Token budget enforcement unchanged; retry count ≤ configured max
**Scale/Scope**: 110 existing unit tests must stay green; 3 new test modules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reasoning Transparency | PASS | Lineage system unchanged; `DistilledLiteratureRecord` fields preserved verbatim through the new typed extraction |
| II. Type-Safe Scientific Rigor | **VIOLATION → BEING FIXED** | Currently tools return raw `dict`/`tuple`. This feature corrects the violation by adding typed Pydantic models for all tool returns. Constitution amendment (Principle II expansion) included in scope. |
| III. Test-First Development | PASS | All new models have test modules; `test_transit_fitter.py` updated in same PR |
| IV. DAG-Driven Single-Responsibility | **VIOLATION → CONSTITUTION AMENDMENT** | Principle IV says "MUST be a LangGraph DAG." LangGraph was never implemented; the actual DAG is in `src/dag/pipeline.py` using plain Python. This feature removes the dead LangGraph requirement and amends Principle IV. See Complexity Tracking. |
| V. Simplicity & YAGNI | PASS | Only removing dead deps + wiring existing PydanticAI; no new abstractions |
| VI. Agentic RAG | PASS | `iterative_search()` and Scholar unchanged except return type wrapping |
| VII. Uncertainty Quantification | PASS | Confidence scoring logic unchanged |
| VIII. Benchmark-Driven Accuracy | PASS | Benchmark runner untouched; `src/evals/` is additive |
| IX. Context Efficiency | PASS | Token budget tracking updated to use `result.usage().total_tokens` (more accurate than estimate) |

**Post-Phase 1 re-check**: Constitution gates II and IV require the MINOR amendment (see constitution amendment task) to be included in this PR. All other gates pass.

## Project Structure

### Documentation (this feature)

```text
specs/002-pydantic-ai-migration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/
│   └── tool-schemas.md  # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code Changes

```text
src/
├── schemas/
│   └── tools.py                     # NEW — LightCurveResult, StellarPropertiesResult,
│                                    #        TransitFitResult, LiteraturePaper,
│                                    #        LiteratureSearchResult
├── agents/
│   └── distillation.py              # MODIFY — add DistillationExtraction, PydanticAI Agent,
│                                    #          replace _llm_distil(), update token tracking
├── mcp/
│   ├── server.py                    # MODIFY — call_tool() → Any return type
│   └── tools/
│       ├── lightkurve_tool.py       # MODIFY — return LightCurveResult
│       └── archive_tool.py          # MODIFY — return StellarPropertiesResult
├── tools/
│   ├── transit_fitter.py            # MODIFY — return TransitFitResult
│   └── rag_tools.py                 # MODIFY — return LiteraturePaper/LiteratureSearchResult
└── evals/                           # NEW directory
    ├── __init__.py
    ├── distillation_eval.py         # NEW — per-paper DistillationAgent evaluation
    └── pipeline_eval.py             # NEW — full pipeline against GoldenDataset

config/
└── agent_specs/                     # NEW directory
    ├── distillation.yaml            # NEW — model, system_prompt, retries
    └── scholar.yaml                 # NEW — documentation-only spec

tests/
├── unit/
│   ├── test_transit_fitter.py       # MODIFY — dict-style → attribute access
│   └── test_schemas_tools.py        # NEW — validates all 5 tool result models
└── evals/
    ├── __init__.py                  # NEW
    └── test_distillation_eval.py    # NEW — dataset construction, no LLM calls

pyproject.toml                       # MODIFY — remove 3 deps, add pydantic-evals
.specify/memory/constitution.md      # MODIFY — MINOR v1.3.0 amendment
specs/001-xpi-agentic-vetting/
├── spec.md                          # MODIFY — remove LangChain refs, add PydanticAI patterns
└── plan.md                          # MODIFY — update tech stack section
```

**Structure Decision**: Single-project layout (existing `src/`). New directories `src/evals/` and `config/agent_specs/` follow established naming conventions. `tests/evals/` mirrors `tests/unit/` structure.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle IV states "MUST be LangGraph DAG" but LangGraph is being removed | LangGraph was declared in `pyproject.toml` but never imported. The actual DAG has always been plain Python in `src/dag/pipeline.py`. The principle no longer describes reality. | Keeping LangGraph as a dep to satisfy the constitution would add a dead ~100MB dependency with no code benefit and no enforcement path. |

## Implementation Phases

### Phase A — New schemas and config (no callers yet)

1. `src/schemas/tools.py` — define all 5 new tool result models
2. `config/agent_specs/distillation.yaml` — model, system_prompt, retries
3. `config/agent_specs/scholar.yaml` — documentation-only
4. `src/evals/__init__.py` — empty init
5. `src/evals/distillation_eval.py` — DistillationInput, HasExtractedPeriod, build_distillation_dataset()
6. `src/evals/pipeline_eval.py` — build_pipeline_dataset()

### Phase B — Update tool functions (return new types)

7. `src/mcp/tools/lightkurve_tool.py` — return `LightCurveResult(**data)` where `data` is the existing dict
8. `src/mcp/tools/archive_tool.py` — return `StellarPropertiesResult(**data)`
9. `src/tools/transit_fitter.py` — return `TransitFitResult(...)` instead of dict
10. `src/tools/rag_tools.py` — `search_arxiv`/`search_ads` → `list[LiteraturePaper]`; `iterative_search` → `LiteratureSearchResult`

### Phase C — Update callers (attribute access)

11. `src/agents/observer.py` — `lc_data["key"]` → `lc_data.key`; `transit_params.get("key")` → `transit_params.key`
12. `src/agents/scholar.py` — `raw_results, queries_issued = iterative_search(...)` → `search_result = iterative_search(...)`
13. `src/mcp/server.py` — `call_tool() -> dict` → `-> Any`

### Phase D — PydanticAI Agent for Distillation

14. `src/agents/distillation.py` — add `DistillationExtraction`, `_build_distillation_agent()`, `_get_distillation_agent()`, replace `_llm_distil()`, update token tracking to use `result.usage().total_tokens`

### Phase E — Tests

15. `tests/unit/test_transit_fitter.py` — dict-style → attribute access (6 tests)
16. `tests/unit/test_schemas_tools.py` — NEW: construction + field validation for all 5 models
17. `tests/evals/__init__.py` — NEW empty init
18. `tests/evals/test_distillation_eval.py` — NEW: dataset construction, evaluator wiring, no LLM calls

### Phase F — Dependencies and constitution

19. `pyproject.toml` — remove 3 LangChain deps; add `pydantic-evals>=0.0.14`
20. `.specify/memory/constitution.md` — MINOR bump v1.3.0: expand Principle II, rewrite Principle IV, add Principle X, update tech stack table

### Phase G — Feature spec updates

21. `specs/001-xpi-agentic-vetting/spec.md` — remove LangChain references; add PydanticAI typed tool returns, YAML specs, pydantic_evals FRs
22. `specs/001-xpi-agentic-vetting/plan.md` — update tech stack section

## Verification Commands

```bash
cd src
pytest tests/unit/ -v                       # all 110+ unit tests must pass
ruff check .                                # must be clean
python -c "from src.schemas.tools import LightCurveResult, TransitFitResult; print('OK')"
python -c "from src.evals.distillation_eval import build_distillation_dataset; print(build_distillation_dataset())"
python -c "from src.agents.distillation import DistillationAgent; print('import OK')"
```

For full LLM path (requires `ANTHROPIC_API_KEY`):
```bash
ANTHROPIC_API_KEY=... python -m src.dag.pipeline --target KIC-11442793 --catalog KIC
```

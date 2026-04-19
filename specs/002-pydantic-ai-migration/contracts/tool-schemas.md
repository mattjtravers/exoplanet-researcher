# Tool Schema Contracts: PydanticAI Migration

**Branch**: `002-pydantic-ai-migration` | **Date**: 2026-04-19

These contracts document the typed return schemas for all XPI tool functions after migration. They replace the informal `dict`/`tuple` shapes previously documented only in docstrings.

## MCP Tool Contracts

### get_light_curve

**Module**: `src/mcp/tools/lightkurve_tool`  
**Return type**: `LightCurveResult` (from `src.schemas.tools`)

```python
class LightCurveResult(BaseModel):
    target_id: str
    quarter: int
    time: list[float]
    flux: list[float]
    flux_err: list[float]
    cadence: Literal["short", "long"]
    tool_call_id: str  # UUID
```

**Invariant**: `len(time) == len(flux) == len(flux_err)`

---

### get_stellar_properties

**Module**: `src/mcp/tools/archive_tool`  
**Return type**: `StellarPropertiesResult` (from `src.schemas.tools`)

```python
class StellarPropertiesResult(BaseModel):
    target_id: str
    stellar_radius_rsun: float | None
    stellar_mass_msun: float | None
    stellar_teff_k: float | None
    log_g: float | None
    metallicity_dex: float | None
    source_catalog: str
    tool_call_id: str  # UUID
```

**Note**: All physical properties are `None` when absent from the archive record — callers must handle nullable fields.

---

## Computational Tool Contracts

### fit_transit

**Module**: `src/tools/transit_fitter`  
**Return type**: `TransitFitResult` (from `src.schemas.tools`)

```python
class TransitFitResult(BaseModel):
    target_id: str
    period_days: float
    depth: float
    duration_hours: float
    rp_rs: float
    tool_call_id: str  # UUID
```

---

## RAG Tool Contracts

### search_arxiv / search_ads

**Module**: `src/tools/rag_tools`  
**Return type**: `list[LiteraturePaper]`

```python
class LiteraturePaper(BaseModel):
    source_id: str
    abstract: str
    source_type: Literal["arxiv", "ads"]
```

**Breaking change from prior interface**: Previously returned `list[tuple[str, str]]`. Callers must update to attribute access.

---

### iterative_search

**Module**: `src/tools/rag_tools`  
**Return type**: `LiteratureSearchResult`

```python
class LiteratureSearchResult(BaseModel):
    papers: list[LiteraturePaper]
    queries_issued: list[str]
```

**Breaking change from prior interface**: Previously returned `tuple[list[tuple[str, str]], list[str]]`. Callers must update from tuple unpacking to attribute access.

---

## MCP Dispatcher Contract

### call_tool (src/mcp/server)

```python
def call_tool(tool_name: str, **kwargs: Any) -> Any: ...
```

**Change**: Return type annotation updated from `-> dict` to `-> Any` to reflect that registered tools now return typed Pydantic models.

---

## Agent YAML Spec Contract

All LLM-backed agents MUST have a spec file at `config/agent_specs/<agent_name>.yaml` with this schema:

```yaml
model: <provider>:<model-id>        # required — e.g. "anthropic:claude-haiku-4-5-20251001"
system_prompt: |                    # required — multiline string
  <prompt text>
retries: <int>                      # required — number of retry attempts on validation failure
```

**Current specs**:
- `config/agent_specs/distillation.yaml` — active (loaded at runtime)
- `config/agent_specs/scholar.yaml` — documentation only (Scholar has no live LLM calls)

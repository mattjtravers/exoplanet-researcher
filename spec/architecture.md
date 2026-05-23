# Architecture & Node Contracts

## 1. Execution Topology (The `pydantic_graph` State Machine)
The pipeline is orchestrated as a strict state machine using `pydantic_graph`. Each agent operates within a dedicated `BaseNode`, and the control flow is determined by strict return types.

1. **Graph Instantiation:** The graph is instantiated by passing a bare `CandidateInput` (target ID + catalog origin) into the initial `GraphState`. Stellar parameters are not required at this stage.
2. **InitializationNode:** Resolves the bare target ID against the appropriate catalog via the Astro MCP Server, constructs and validates the full `CandidateTarget`, and writes `InitializationOutput`.
3. **ObserverNode:** Analyzes quantitative data, calculates transit parameters, and detects structural anomalies. Reads stellar properties from `InitializationOutput`.
4. **ScholarNode:** Utilizes the Observer's recorded anomalies to guide its literature search via the Literature MCP Server.
5. **DistillationNode:** Processes the raw papers retrieved by the Scholar.
6. **SynthesizerNode:** Compiles the Lineage Map, checks for context errors, reviews previous `ValidatorOutput` violations (if any), and drafts the Vetting Report.
7. **ValidatorNode:** Evaluates final parameters against physical boundaries via the Astro MCP Server. Routing depends on the `violation_source` of each `ValidatorViolation` in the result:
    * **All `passed`** → returns `End[VettingReport]`.
    * **Any `violation_source == "data"`** → the underlying transit fit or stellar parameters are physically impossible; route back to `ObserverNode` if `observer_retry_count < configs["observer"].max_retries`, else `End[ValidatorError]`. Resets `synthesizer_retry_count` to 0.
    * **All `violation_source == "synthesis"`** → the Synthesizer's reasoning/weighting introduced the violation; route back to `SynthesizerNode` if `synthesizer_retry_count < configs["validator"].max_retries`, else `End[ValidatorError]`.

## 2. Graph State & Observability
Execution relies on `GraphState` (a strict Pydantic `BaseModel`) and `GraphRunContext`.
* **State Mutation:** Nodes read global execution data via `ctx.state` and append their strictly typed outputs. If a node emits a malformed payload, Pydantic throws an immediate validation error, which Pydantic AI catches and self-corrects before the graph transitions to the next node.
* **Local Persistence:** Execution utilizes `pydantic_graph.persistence.FileStatePersistence`. State is automatically dumped to disk between transitions, allowing reviewers to inspect the exact payload injected into any given step or pause/resume the pipeline locally.

## 3. Graph Node Definitions & MCP Integrations

### 3.1 Initialization Node
* **Responsibility:** Resolve a bare target ID against the appropriate stellar catalog and construct a fully populated `CandidateTarget`. Decouples CLI input from the strict `CandidateTarget` contract.
* **Tools (via Astro MCP):** `fetch_stellar_properties_mcp`
* **MCP Session Used:** `astro_mcp_session`
* **Graph Input:** `ctx: GraphRunContext[GraphState, GraphDeps]`. Path traversal: reads `ctx.state.candidate_input.target_id` and `ctx.state.candidate_input.catalog_origin`.
* **State Update:** Sets `ctx.state.initialization_output` to a new `InitializationOutput`.
* **Edge / Return Type:** Returns `ObserverNode`.

### 3.2 Observer Node
* **Responsibility:** Quantitative anomaly detection, light curve fitting, and mathematical confidence scoring.
* **Tools (via Astro MCP):** `fetch_mcp_lightcurve`, `fit_transit_model`
* **MCP Session Used:** `astro_mcp_session`
* **Graph Input:** `ctx: GraphRunContext[GraphState, GraphDeps]`. Path traversal: reads `ctx.state.initialization_output.candidate` and `ctx.state.initialization_output.stellar_properties`. If re-entering after a `"data"`-classified retry, also reads the most recent `ctx.state.validator_outputs[-1]` to inform its corrected approach.
* **State Update:** Appends a new `ObserverOutput` to `ctx.state.observer_outputs`. If re-executing under a retry, increments `ctx.state.observer_retry_count` and resets `ctx.state.synthesizer_retry_count = 0`.
* **Edge / Return Type:** Returns `ScholarNode`.

### 3.3 Scholar Node
* **Responsibility:** Agentic search orchestration based on candidate data and observed anomalies.
* **Tools (via Literature MCP):** `search_arxiv_mcp`, `query_ads_mcp`
* **MCP Session Used:** `literature_mcp_session`
* **Graph Input:** `ctx: GraphRunContext[GraphState, GraphDeps]`. Path traversal: reads anomalies from `ctx.state.observer_outputs[-1].anomaly_records`.
* **State Update:** Appends a new `ScholarOutput` to `ctx.state.scholar_outputs`.
* **Edge / Return Type:** Returns `DistillationNode`.

### 3.4 Distillation Node
* **Responsibility:** Compress retrieved text into structured parameters, eliminating hallucinations and standardizing citation strings.
* **Tools:** None (Strict summarization of context).
* **MCP Session Used:** None.
* **Graph Input:** `ctx: GraphRunContext[GraphState, GraphDeps]`. Path traversal: reads text from `ctx.state.scholar_outputs[-1].literature_search_result`.
* **State Update:** Appends a new `DistillationOutput` to `ctx.state.distillation_outputs`.
* **Edge / Return Type:** Returns `SynthesizerNode`.

### 3.5 Synthesizer Node
* **Responsibility:** Convergence checking, conflict detection, Lineage Map assembly, and final Vetting Report drafting.
* **Tools:** None (Reasoning and formatting only).
* **MCP Session Used:** None.
* **Graph Input:** `ctx: GraphRunContext[GraphState, GraphDeps]`. Path traversal: reads cumulative state from `ctx.state.observer_outputs[-1]`, `ctx.state.scholar_outputs[-1]`, `ctx.state.distillation_outputs[-1]`. When entering a `"synthesis"`-classified retry loop, also reads `ctx.state.validator_outputs[-1]` to address the prior violations. The full `ctx.state.synthesizer_outputs` list is available for reference but only the latest is acted upon.
* **State Update:** Appends a new `SynthesizerOutput` to `ctx.state.synthesizer_outputs`. Always populates `node_assessments` on the drafted `VettingReport` with the per-node `ConfidenceAssessment` objects from `observer_outputs[-1]` and `scholar_outputs[-1]`, regardless of whether a `ConsensusConflictFlag` is set.
* **Edge / Return Type:** Returns `ValidatorNode`.

### 3.6 Validator Node
* **Responsibility:** Strict Pydantic enforcement of astrophysical boundaries (e.g., mass-radius limits, stellar density limits) and classification of each violation by source for retry routing.
* **Tools (via Astro MCP):** `astrophysics_constants_mcp` (for exact boundary limits).
* **MCP Session Used:** `astro_mcp_session`
* **Graph Input:** `ctx: GraphRunContext[GraphState, GraphDeps]`. Path traversal: reads parameters from `ctx.state.synthesizer_outputs[-1].vetting_report`.
* **State Update:** Appends a new `ValidatorOutput` to `ctx.state.validator_outputs`. Each `ValidatorViolation` in the result must carry a `violation_source` classification.
* **Edge / Return Type:**
    * On `ValidatorResult.passed == True`: returns `End[VettingReport]`.
    * If any violation has `violation_source == "data"`:
        * If `ctx.state.observer_retry_count < ctx.deps.configs["observer"].max_retries`, returns `ObserverNode` (the Observer will increment its counter and reset `synthesizer_retry_count`).
        * Otherwise returns `End[ValidatorError]`.
    * If all violations have `violation_source == "synthesis"`:
        * If `ctx.state.synthesizer_retry_count < ctx.deps.configs["validator"].max_retries`, increments `ctx.state.synthesizer_retry_count` and returns `SynthesizerNode`.
        * Otherwise returns `End[ValidatorError]`.

## 4. MCP Tool Contracts
Each tool below is hosted on one of the two decoupled MCP servers. Inputs and outputs are strict Pydantic `BaseModel` instances (or primitive arguments where indicated) and serve as the wire contract between the graph and the MCP server.

### 4.1 Astro MCP Server (`astro_mcp_session`)
* `fetch_stellar_properties_mcp(target_id: str, catalog: Literal["KIC", "TIC", "TOI"]) -> StellarPropertiesResult`
* `fetch_mcp_lightcurve(target_id: str, quarters: list[int] | None = None) -> LightCurveResult`
* `fit_transit_model(light_curve: LightCurveResult) -> TransitFitResult`
* `astrophysics_constants_mcp(boundary_type: Literal["mass_radius", "stellar_density", "transit_geometry"]) -> dict[str, float]`

### 4.2 Literature MCP Server (`literature_mcp_session`)
* `search_arxiv_mcp(query: str, max_results: int = 10) -> list[LiteraturePaper]`
* `query_ads_mcp(query: str, max_results: int = 10) -> list[LiteraturePaper]`

## 5. Agent Configuration
LLM-backed nodes load their `AgentConfig` from YAML files at startup.

* **File location:** `configs/<node_name>.yaml` (e.g., `configs/observer.yaml`, `configs/synthesizer.yaml`).
* **YAML structure:** keys mirror the `AgentConfig` BaseModel fields (`model_identifier`, `system_prompt_template`, `token_budget`, `max_retries`, `temperature`). Loaded into `GraphDeps.configs` keyed by node name lowercased (`"initialization"`, `"observer"`, `"scholar"`, `"distillation"`, `"synthesizer"`, `"validator"`).
* **Per-node prompt intent:**
    * `initialization`: deterministic catalog lookup; minimal LLM involvement.
    * `observer`: quantitative reasoning over light curve metrics and transit-fit outputs.
    * `scholar`: agentic literature search planning, query refinement based on anomalies.
    * `distillation`: strict extraction with no inference beyond the source text.
    * `synthesizer`: cross-source reasoning, conflict detection, vetting-report composition.
    * `validator`: deterministic boundary checking with violation source classification.
* **Recommended model selection:** deterministic / low-temperature models for `observer`, `distillation`, `validator`; reasoning-capable models for `scholar` and `synthesizer`.
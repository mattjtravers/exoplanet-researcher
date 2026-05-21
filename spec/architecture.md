# Architecture & Node Contracts

## 1. Execution Topology (The `pydantic_graph` State Machine)
The pipeline is orchestrated as a strict state machine using `pydantic_graph`. Each agent operates within a dedicated `BaseNode`, and the control flow is determined by strict return types.

1. **Initialization:** The graph is instantiated by passing a validated `CandidateTarget` into the initial `GraphState`.
2. **ObserverNode:** Analyzes quantitative data, calculates transit parameters, and detects structural anomalies.
3. **ScholarNode:** Utilizes the Observer's recorded anomalies to guide its literature search via an MCP Server.
4. **DistillationNode:** Processes the raw papers retrieved by the Scholar.
5. **SynthesizerNode:** Compiles the Lineage Map, checks for context errors, reviews previous `ValidatorOutput` violations (if any), and drafts the Vetting Report.
6. **ValidatorNode:** Evaluates final parameters against physical boundaries. If validation fails and the iteration limit is not exceeded, it increments the loop counter and returns `SynthesizerNode` to initiate a self-correction loop. If the limit is reached, it returns `End[ValidatorError]`. On success, it returns `End[VettingReport]`.

## 2. Graph State & Observability
Execution relies on `GraphState` (a strict Pydantic `BaseModel`) and `GraphRunContext`.
* **State Mutation:** Nodes read global execution data via `ctx.state` and append their strictly typed outputs. If a node emits a malformed payload, Pydantic throws an immediate validation error, which Pydantic AI catches and self-corrects before the graph transitions to the next node.
* **Local Persistence:** Execution utilizes `pydantic_graph.persistence.FileStatePersistence`. State is automatically dumped to disk between transitions, allowing reviewers to inspect the exact payload injected into any given step or pause/resume the pipeline locally.

## 3. Graph Node Definitions & MCP Integrations

### 3.1 Observer Node
* **Responsibility:** Quantitative anomaly detection, light curve fitting, and mathematical confidence scoring.
* **Tools (via local MCP):** `fetch_mcp_lightcurve`, `fit_transit_model`
* **Graph Input:** `ctx: GraphRunContext[GraphState, GraphDeps]`
* **State Update:** Appends `ObserverOutput` to `ctx.state.observer_output`.
* **Edge / Return Type:** Returns `ScholarNode`.

### 3.2 Scholar Node
* **Responsibility:** Agentic search orchestration based on candidate data and observed anomalies.
* **Tools (via local MCP):** `search_arxiv_mcp`, `query_ads_mcp`
* **Graph Input:** `ctx: GraphRunContext[GraphState, GraphDeps]`. Path traversal: reads anomalies from `ctx.state.observer_output.anomaly_records`.
* **State Update:** Appends `ScholarOutput` to `ctx.state.scholar_output`.
* **Edge / Return Type:** Returns `DistillationNode`.

### 3.3 Distillation Node
* **Responsibility:** Compress retrieved text into structured parameters, eliminating hallucinations and standardizing citation strings.
* **Tools:** None (Strict summarization of context).
* **Graph Input:** `ctx: GraphRunContext[GraphState, GraphDeps]`. Path traversal: reads text from `ctx.state.scholar_output.literature_search_result`.
* **State Update:** Appends `DistillationOutput` to `ctx.state.distillation_output`.
* **Edge / Return Type:** Returns `SynthesizerNode`.

### 3.4 Synthesizer Node
* **Responsibility:** Convergence checking, conflict resolution, Lineage Map assembly, and final Vetting Report drafting.
* **Tools:** None (Reasoning and formatting only).
* **Graph Input:** `ctx: GraphRunContext[GraphState, GraphDeps]`. Path traversal: reads cumulative state from `ctx.state.observer_output`, `ctx.state.scholar_output`, `ctx.state.distillation_output`, and analyzes past errors in `ctx.state.validator_output` if a correction loop was triggered.
* **State Update:** Appends `SynthesizerOutput` to `ctx.state.synthesizer_output`.
* **Edge / Return Type:** Returns `ValidatorNode`.

### 3.5 Validator Node
* **Responsibility:** Strict Pydantic enforcement of astrophysical boundaries (e.g., mass-radius limits, stellar density limits).
* **Tools:** `astrophysics_constants_mcp` (for exact boundary limits).
* **Graph Input:** `ctx: GraphRunContext[GraphState, GraphDeps]`. Path traversal: reads parameters from `ctx.state.synthesizer_output.vetting_report`.
* **State Update:** Appends `ValidatorOutput` to `ctx.state.validator_output` and updates `ctx.state.loop_counters["self_correction"]`.
* **Edge / Return Type:** Returns `End[VettingReport]` upon success. If violations occur and `ctx.state.loop_counters["self_correction"] < ctx.deps.configs["validator"].max_retries`, returns `SynthesizerNode`; otherwise returns `End[ValidatorError]`.
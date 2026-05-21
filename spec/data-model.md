# Data Model

All schemas are strictly enforced Pydantic `BaseModel` subclasses to ensure runtime structural validation, automatic type coercion, and seamless integration with Pydantic Logfire and MCP tool servers.

## 1. Domain Entities
* **CandidateTarget:** Root graph input containing target ID (KIC/TIC/TOI), catalog origin, and primary stellar parameters (radius, mass, effective temperature, log_g).
* **LineageEntry:** Individual provenance point linking a `parameter_name` and `parameter_value` to an active state lifecycle. Contains an optional `mcp_tool_call_id` (null for text-based extractions), an optional `citation_snippet`, a `source_id`, the executing `node_name`, and the Logfire `trace_id`.
* **LineageMap:** A JSON-LD compliant graph representing the collection of all `LineageEntry` points across the state machine execution.
* **ConfidenceAssessment:** A node's independent evaluation payload. Includes an integer score (0-100), a target disposition, and an array of primary evidence references.
* **ConsensusConflictFlag:** Generated when data boundaries diverge. Contains the divergence magnitude, target fields, and a boolean resolution status flag.
* **AnomalyRecord:** Outlines irregular light curve structures. Tracks `anomaly_type`, sigma deviation, affected target data quarters, and non-planetary search keys.
* **ValidatorViolation:** Identifies a failed physical constraint, capturing the field name, computed value, boundary exceeded, and structural mathematical rule violated.
* **ValidatorResult:** Contains a boolean `passed` flag and a list of `ValidatorViolation` structures.
* **ReasoningStep:** A trace object recording an individual node action, underlying deduction, and OpenTelemetry timestamp from the consolidation process.
* **VettingReport:** Final assembled artifact. Contains target ID, final disposition, an aggregated consensus score, a non-null reasoning history trace, the root Logfire `trace_id`, and a mutually exclusive choice of either `consensus_confidence` or an unresolved `conflict_flag`.
* **ValidatorError:** Terminal execution fault object returned when the graph fails validation bounds and exhausts its retry allocation budget. Contains a list of final `ValidatorViolation` details, the root `trace_id`, and a failure summary string.

## 2. MCP Tool & Extraction Contracts
*Note: These models serve as the strict serialization contract between the Pydantic AI graph and external MCP tool servers.*

* **LightCurveResult:** Validated light curve data holding a `target_id`, `quarter`, arrays for `time`, `flux`, and `flux_err`, a `cadence` indicator, and a tracking MCP `tool_call_id`.
* **StellarPropertiesResult:** Archive physical values containing `target_id`, nullable radius/mass/temperature fields, `source_catalog`, and an MCP `tool_call_id`.
* **TransitFitResult:** Mathematical output containing calculated `period_days`, `depth`, `duration_hours`, and calculated planet-to-star radius ratio.
* **LiteraturePaper:** Representation of research metadata holding a `source_id` (ArXiv ID/ADS bibcode), the source text `abstract`, and a `source_type` category flag.
* **LiteratureSearchResult:** Aggregated output containing an array of `LiteraturePaper` models and a chronological list of all `queries_issued` via the literature MCP server.
* **DistilledLiteratureRecord:** Target output extracted directly by the LLM containing a key-value parameter dictionary, a textual summary of disposition notes, and a literal citation string snippet.

## 3. Graph Node & State Payloads
* **ObserverOutput:** Contains a `ConfidenceAssessment` (where node name is locked to "ObserverNode"), a collection of `LineageEntry` logs, an array of `AnomalyRecord` models, `TransitFitResult`, and `StellarPropertiesResult`.
* **ScholarOutput:** Contains a `ConfidenceAssessment` (where node name is locked to "ScholarNode"), a `LiteratureSearchResult` object, and a collection of `LineageEntry` logs.
* **DistillationOutput:** Structured conversion wrapper capturing an array of `DistilledLiteratureRecord` components and an execution integer tracking total tokens consumed.
* **SynthesizerOutput:** Core integration summary containing the assembled `VettingReport`, the constructed `LineageMap`, a nullable `ConsensusConflictFlag`, and a complete trace history array of `ReasoningStep` events.
* **ValidatorOutput:** Final filter receipt providing a `ValidatorResult` record alongside an annotated final state classification string literal.

## 4. Pipeline Execution State (`pydantic_graph`)

### 4.1 AgentConfig (BaseModel)
* `model_identifier`: `str` # e.g., "gemini-2.5-pro" or "claude-3-7-sonnet"
* `system_prompt_template`: `str`
* `token_budget`: `int`
* `max_retries`: `int`
* `temperature`: `float`

### 4.2 GraphState (BaseModel)
The central, mutable synchronous state tracked across the entire `pydantic_graph` lifecycle.
* `candidate`: `CandidateTarget`
* `observer_output`: `ObserverOutput | None` = None
* `scholar_output`: `ScholarOutput | None` = None
* `distillation_output`: `DistillationOutput | None` = None
* `synthesizer_output`: `SynthesizerOutput | None` = None
* `validator_output`: `ValidatorOutput | None` = None
* `loop_counters`: `dict[str, int]` = Field(default_factory=dict) # Tracks bounded self-correction iterations
* `graph_error`: `str | None` = None

### 4.3 GraphDeps (BaseModel)
Static runtime dependencies injected into the `GraphRunContext`.
* `configs`: `dict[str, AgentConfig]` # Node-specific execution profiles
* `mcp_client_session`: `Any` # Active connection session to the decoupled MCP Tool Server
* `global_timeout_seconds`: `int`

## 5. Evaluation Entities
* **DistillationInput:** Test corpus entry isolating parsing functions, providing a static target `source_id`, reference paper `abstract`, and reference target ID string.
* **EvaluationResult:** Assessment metric payload returning a numeric score metric (0.0 to 1.0) alongside a structural validation justification string.
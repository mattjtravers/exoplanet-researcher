# Data Model

All schemas are strictly enforced Pydantic `BaseModel` subclasses to ensure runtime structural validation, automatic type coercion, and seamless integration with Pydantic Logfire and MCP tool servers.

## 1. Domain Entities
* **CandidateInput:** Bare-bones graph input accepted by the CLI. Contains only `target_id: str` and `catalog_origin: Literal["KIC", "TIC", "TOI"]`. Used to bootstrap the graph before stellar parameters have been fetched.
* **CandidateTarget:** Fully populated target containing `target_id`, `catalog_origin`, and primary stellar parameters (radius, mass, effective temperature, log_g). Constructed by `InitializationNode` from a `CandidateInput`.
* **LineageEntry:** Individual provenance point linking a `parameter_name` and `parameter_value` to an active state lifecycle. Contains an optional `tool_call_id` (null for text-based extractions), an optional `citation_snippet`, a `source_id`, the executing `node_name`, and the Logfire `trace_id`.
* **LineageMap:** A JSON-LD compliant graph representing the collection of all `LineageEntry` points across the state machine execution.
* **ConfidenceAssessment:** A node's independent evaluation payload. Includes an integer score (0-100), a target disposition, and an array of primary evidence references.
* **ConsensusConflictFlag:** Generated when data boundaries diverge. Contains the divergence magnitude, target fields, and a `conflict_type: Literal["data_literature_divergence", "parameter_boundary", "cross_node_inconsistency"]` describing the nature of the conflict for forensic review.
* **AnomalyRecord:** Outlines irregular light curve structures. Tracks `anomaly_type`, sigma deviation, affected target data quarters, and non-planetary search keys.
* **ValidatorViolation:** Identifies a failed physical constraint, capturing the field name, computed value, boundary exceeded, structural mathematical rule violated, and `violation_source: Literal["data", "synthesis"]`. A `"data"` source indicates the violated value originated from ObserverNode MCP tools (transit fit, stellar properties); a `"synthesis"` source indicates the violation was introduced by SynthesizerNode reasoning/weighting. This field drives ValidatorNode's retry routing.
* **ValidatorResult:** Contains a boolean `passed` flag and a list of `ValidatorViolation` structures.
* **ReasoningStep:** A trace object recording an individual node action and underlying deduction. Contains `execution_timestamp: datetime` captured by the node at the moment it writes its output to state (Python `datetime.utcnow()`). OpenTelemetry spans are a separate observability layer managed by Logfire and are not embedded in this model.
* **VettingReport:** Final assembled artifact. Contains:
    * `target_id`
    * `final_disposition`
    * `node_assessments: dict[str, ConfidenceAssessment]` — mandatory, always-present map of per-node confidence scores keyed by node name (e.g., `"ObserverNode"`, `"ScholarNode"`). Preserves raw per-node evaluations regardless of whether a conflict was detected.
    * `reasoning_trace: list[ReasoningStep]` (non-null)
    * `trace_id` (root Logfire trace ID)
    * Mutually exclusive aggregate outcome: either `consensus_confidence: ConfidenceAssessment` or `conflict_flag: ConsensusConflictFlag` (exactly one is non-null).
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
* **InitializationOutput:** Contains the fully constructed `CandidateTarget`, the source `StellarPropertiesResult`, and a collection of `LineageEntry` logs documenting the catalog lookup. Produced by `InitializationNode` from a bare `CandidateInput`.
* **ObserverOutput:** Contains a `ConfidenceAssessment` (where node name is locked to "ObserverNode"), a collection of `LineageEntry` logs, an array of `AnomalyRecord` models, and a `TransitFitResult`. Stellar properties are read from `InitializationOutput`, not duplicated here.
* **ScholarOutput:** Contains a `ConfidenceAssessment` (where node name is locked to "ScholarNode"), a `LiteratureSearchResult` object, and a collection of `LineageEntry` logs.
* **DistillationOutput:** Structured conversion wrapper capturing an array of `DistilledLiteratureRecord` components and an execution integer tracking total tokens consumed (sourced from `pydantic_ai` result usage metadata).
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
The central, mutable synchronous state tracked across the entire `pydantic_graph` lifecycle. Outputs of nodes that may execute more than once (due to either of the self-correction loops) are stored as append-only lists to preserve full lineage on disk via `FileStatePersistence`. Downstream nodes always read the latest element (`[-1]`).
* `candidate_input`: `CandidateInput` — bare ID supplied at graph instantiation
* `initialization_output`: `InitializationOutput | None` = None — single-shot; not in any retry loop
* `observer_outputs`: `list[ObserverOutput]` = Field(default_factory=list)
* `scholar_outputs`: `list[ScholarOutput]` = Field(default_factory=list)
* `distillation_outputs`: `list[DistillationOutput]` = Field(default_factory=list)
* `synthesizer_outputs`: `list[SynthesizerOutput]` = Field(default_factory=list)
* `validator_outputs`: `list[ValidatorOutput]` = Field(default_factory=list)
* `observer_retry_count`: `int` = 0 — incremented when ValidatorNode routes back to ObserverNode due to `"data"` violations
* `synthesizer_retry_count`: `int` = 0 — incremented when ValidatorNode routes back to SynthesizerNode due to `"synthesis"` violations; reset to 0 whenever ObserverNode re-executes
* `graph_error`: `str | None` = None

### 4.3 GraphDeps (BaseModel)
Static runtime dependencies injected into the `GraphRunContext`.
* `configs`: `dict[str, AgentConfig]` # Node-specific execution profiles
* `astro_mcp_session`: `Any` # Active connection to the Astro MCP Tool Server (light curves, transit fitting, stellar properties, astrophysics constants)
* `literature_mcp_session`: `Any` # Active connection to the Literature MCP Server (ArXiv, ADS)
* `global_timeout_seconds`: `int`

## 5. Evaluation Entities
* **DistillationInput:** Test corpus entry isolating parsing functions, providing a static target `source_id`, reference paper `abstract`, and reference target ID string.
* **EvaluationResult:** Assessment metric payload returning a numeric score metric (0.0 to 1.0) alongside a structural validation justification string.
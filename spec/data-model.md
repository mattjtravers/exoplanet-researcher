# Data Model

All schemas are strictly enforced Pydantic `BaseModel` subclasses unless noted otherwise.

## 1. Domain Entities
* **CandidateTarget:** Root pipeline input containing target ID (KIC/TIC/TOI), catalog origin, and primary stellar parameters (radius, mass, effective temperature, log_g).
* **LineageEntry:** Individual provenance point linking a `parameter_name` and `parameter_value` to a specific `tool_call_id`, `source_id`, and issuing `agent`.
* **LineageMap:** A JSON-LD compliant graph representing the collection of all `LineageEntry` points across the pipeline.
* **ConfidenceAssessment:** An agent's independent evaluation payload. Includes an integer score (0-100), a target disposition, and a tracking array of primary evidence references.
* **ConsensusConflictFlag:** Generated when data boundaries diverge. Contains the divergence magnitude, target fields, and a boolean resolution status flag.
* **AnomalyRecord:** Outlines irregular light curve structures. Tracks `anomaly_type`, sigma deviation, affected target data quarters, and non-planetary search keys.
* **ValidatorViolation:** Identifies a failed physical constraint, capturing the field name, computed value, boundary exceeded, and structural mathematical rule violated.
* **ValidatorResult:** Contains a boolean `passed` flag and a list of `ValidatorViolation` structures.
* **ReasoningStep:** A trace object recording an individual action, underlying deduction, and time signature from the consolidation process.
* **VettingReport:** Final assembled artifact. Contains target ID, final disposition, an aggregated consensus score, a non-null reasoning history trace, and a mutually exclusive choice of either `consensus_confidence` or an unresolved `conflict_flag`.

## 2. Tool & Extraction Contracts
* **LightCurveResult:** Validated light curve data holding a `target_id`, `quarter`, arrays for `time`, `flux`, and `flux_err`, a `cadence` indicator, and a tracking `tool_call_id`.
* **StellarPropertiesResult:** Archive physical values containing `target_id`, nullable radius/mass/temperature fields, `source_catalog`, and a `tool_call_id`.
* **TransitFitResult:** Mathematical output containing calculated `period_days`, `depth`, `duration_hours`, and calculated planet-to-star radius ratio (`rp_rs`).
* **LiteraturePaper:** Representation of research metadata holding a `source_id` (ArXiv ID/ADS bibcode), the source text `abstract`, and a `source_type` category flag.
* **LiteratureSearchResult:** Aggregated output containing an array of `LiteraturePaper` models and a chronological list of all `queries_issued`.
* **DistilledLiteratureRecord:** Target output extracted directly by the LLM containing a key-value parameter dictionary, a textual summary of disposition notes, and a literal citation string snippet.

## 3. Orchestration & Agent Interface Payloads
* **AgentConfig:** Base operation configuration tracking token limits, target model identifiers, execution timeouts, and retry limits.
* **ObserverOutput:** Delivered by the quantitative node. Contains a `ConfidenceAssessment` (where agent name is locked to "observer"), a collection of `LineageEntry` logs, an array of `AnomalyRecord` models, `TransitFitResult`, and `StellarPropertiesResult`.
* **ScholarOutput:** Delivered by the literature retrieval node. Contains a `ConfidenceAssessment` (where agent name is locked to "scholar"), a `LiteratureSearchResult` object, and a collection of `LineageEntry` logs.
* **DistillationOutput:** Structured conversion wrapper capturing an array of `DistilledLiteratureRecord` components and an execution integer tracking total tokens consumed.
* **SynthesizerOutput:** Core integration summary containing the assembled `VettingReport`, the constructed `LineageMap`, a nullable `ConsensusConflictFlag`, and a complete trace history array of `ReasoningStep` events.
* **ValidatorOutput:** Final filter receipt providing a `ValidatorResult` record alongside an annotated final state classification string literal.

## 4. Pipeline Execution State
* **PipelineState (TypedDict):** Global, in-memory asynchronous context state tracking pipeline execution. Agents possess global read clearance but are strictly isolated to writing to their dedicated schema destination field.
  * `candidate`: `CandidateTarget`
  * `config`: `dict[str, AgentConfig]`
  * `observer_output`: `ObserverOutput | None`
  * `scholar_output`: `ScholarOutput | None`
  * `distillation_output`: `DistillationOutput | None`
  * `synthesizer_output`: `SynthesizerOutput | None`
  * `validator_output`: `ValidatorOutput | None`
  * `error`: `str | None`

## 5. Evaluation Entities
* **GoldenDatasetEntry:** Static reference object containing a target ID, verified ground-truth disposition (Planet, False Positive, Inconclusive), and verified physical parameters.
* **DistillationInput:** Test corpus entry isolating parsing functions, providing a static target `source_id`, reference paper `abstract`, and reference target ID string.
* **EvaluationResult:** Assessment metric payload returning a numeric score metric (0.0 to 1.0) alongside a structural validation justification string.
* **BenchmarkResult:** Global framework report compiling calculated precision, recall, and F1 calculations accompanied by absolute coordinate counts for the confusion matrix.
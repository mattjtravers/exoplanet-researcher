# Architecture & Agent Contracts

## 1. Execution Topology (The DAG)
The pipeline executes as a Directed Acyclic Graph orchestrated via Pydantic AI dependencies.
1. **Observer** runs first to analyze quantitative data, calculate transit parameters, and detect structural anomalies.
2. **Scholar** runs second, utilizing the Observer's anomalies to guide its literature search.
3. **Distillation** runs third, strictly processing the raw papers retrieved by the Scholar.
4. **Synthesizer** runs fourth, comparing the Observer's math against Distillation's text to compile the Lineage Map and draft the Vetting Report.
5. **Validator** runs strictly last as a final physical boundary check against the synthesized data.



## 2. Pipeline State
The execution graph relies on `PipelineState` (a TypedDict) as the single source of truth during asynchronous processing. Agents possess global read clearance for the state but are strictly restricted to writing to their designated output field.

## 3. Agent Node Definitions

*Note: All agents in this pipeline are built on Pydantic AI, enforcing strict input/output validation, token tracking, and structured tool calling.*

### 3.1 Observer Agent
* **Responsibility:** Quantitative anomaly detection, light curve fitting, and mathematical confidence scoring.
* **Input:** `CandidateTarget`, `AgentConfig`
* **Output:** `ObserverOutput` (Contains: `ConfidenceAssessment`, `list[LineageEntry]`, `list[AnomalyRecord]`, `TransitFitResult`, `StellarPropertiesResult`)

### 3.2 Scholar Agent
* **Responsibility:** Agentic search orchestration based on candidate data and observed anomalies. Generates independent queries to ArXiv/ADS.
* **Input:** `CandidateTarget`, `list[AnomalyRecord]` (from Observer), `AgentConfig`
* **Output:** `ScholarOutput` (Contains: `ConfidenceAssessment`, `LiteratureSearchResult`, `list[LineageEntry]`)

### 3.3 Distillation Agent
* **Responsibility:** Compress retrieved text into structured parameters, eliminating hallucinations and standardizing citation strings.
* **Input:** `LiteratureSearchResult` (from Scholar), Target Star ID, `AgentConfig`
* **Output:** `DistillationOutput` (Contains: `list[DistilledLiteratureRecord]`, token consumption tracker)

### 3.4 Synthesizer Agent
* **Responsibility:** Convergence checking, conflict resolution, Lineage Map assembly, and final Vetting Report drafting.
* **Input:** `ObserverOutput`, `ScholarOutput`, `DistillationOutput`, `AgentConfig`, Iteration count
* **Output:** `SynthesizerOutput` (Contains: `VettingReport`, `LineageMap`, `ConsensusConflictFlag`, `list[ReasoningStep]`)
* **Constraint:** May initiate a bounded self-correction loop (max iterations defined in config) if data fundamentally contradicts without explanation.

### 3.5 Validator Agent
* **Responsibility:** Strict enforcement of astrophysical boundaries (e.g., mass-radius limits, stellar density limits).
* **Input:** `SynthesizerOutput`, `ObserverOutput`, `CandidateTarget`
* **Output:** `ValidatorOutput` (Contains: `ValidatorResult` detailing passed/failed flags and explicit `ValidatorViolation` lists)
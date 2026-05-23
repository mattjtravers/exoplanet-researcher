# Product Specification: Exoplanet Researcher — Independent Agentic Exoplanet Vetting

## Overview
XPI is a portfolio demonstration of a multi-agent pipeline designed to vet exoplanet candidates. It analyzes photometric data and scientific literature, flags conflicting evidence, and produces a reproducible Vetting Report. Built entirely within the Pydantic AI ecosystem, the framework uses a deterministic `pydantic_graph` state machine to orchestrate agents, standardizes external tools via the Model Context Protocol (MCP), and tracks full-stack execution observability using Pydantic Logfire. The design focuses on clean code structure, strict typing, and local reproducibility for technical reviewers.

## User Scenarios

1. **Local Demonstration:** A reviewer clones the repository, configures API keys locally, and submits a bare candidate ID (KIC/TIC/TOI). The `InitializationNode` resolves the ID against the appropriate catalog via MCP, the pipeline executes locally, and a final Vetting Report and Lineage Map are written to disk.
2. **Transparent Vetting Report:** The pipeline produces a Vetting Report with a disposition (Planet Candidate / False Positive / Inconclusive), per-node confidence scores (always preserved in `node_assessments`), an aggregated consensus score or conflict flag, an annotated light curve, and a reasoning trace citing data and literature.
3. **Conflict Detection:** If quantitative data (e.g., a clean transit) and literature (e.g., known eclipsing binary) diverge beyond a threshold, the system flags a Consensus Conflict — typed by `conflict_type` for forensic review — instead of averaging the scores. Individual node scores remain visible in `node_assessments`.
4. **State Machine Resumption:** A reviewer forces an execution interruption mid-run to test durability. Using Pydantic's native `FileStatePersistence`, the graph resumes seamlessly from the local JSON snapshot. Because retry-loop node outputs are stored as append-only lists, every failed draft remains inspectable.
5. **System Evaluation:** Reviewers can execute the `pydantic_evals` suite to verify extraction quality and prompt boundaries without requiring a full live pipeline execution or excessive LLM API costs.

## System Requirements

### 1. State-Machine Orchestration (`pydantic-graph`)
- The multi-agent workflow is explicitly defined using `GraphBuilder` and `BaseNode` subclasses.
- The pipeline execution is modeled as a strict state machine, preventing loose, autonomous agent-to-agent chatter. Nodes (Initialization, Observer, Scholar, Distillation, Synthesizer, Validator) dictate control flow by returning defined edge types (the next `BaseNode` or an `End` state).
- A central `GraphRunContext` and `GraphState` object passes cumulative vetting data between nodes. Outputs of nodes that may execute more than once (due to a self-correction loop) are stored as append-only lists so the full lineage of every retry attempt is preserved.
- Two distinct self-correction loops are supported, routed by `ValidatorViolation.violation_source`: `"data"` violations route back to the `ObserverNode` (the underlying photometric values are at fault); `"synthesis"` violations route back to the `SynthesizerNode` (the reasoning is at fault). Each loop has an independent bounded retry counter.

### 2. The Model Context Protocol (MCP) Standard & Data Contracts
- All external actions (`get_light_curve`, `fit_transit`, `search_arxiv`) are decoupled from the agent definitions and hosted via a local MCP Tool Server.
- Agents access these tools over MCP connections rather than direct function references, showcasing modern, decoupled tool integration.
- Inter-agent payloads and `GraphState` mutations are strictly validated via Pydantic models. Raw dictionaries and untyped tuples are prohibited.

### 3. Agentic Execution & Configurations
- LLM-backed nodes execute under decoupled YAML configurations defining the target model identifier, prompt configurations, and tool availability per node.
- Pydantic AI's retry frameworks natively handle transient API failures or validation errors inside a node before returning its state.

### 4. Traceability & Local Persistence
- **State Persistence:** The pipeline implements `FileStatePersistence` out-of-the-box. As the graph executes, `NodeSnapshot` objects are serialized to a local `.json` file, demonstrating durable execution patterns without requiring cloud infrastructure.
- **Unified Tracing:** Pydantic Logfire natively captures all node transitions, agent prompt payloads, MCP tool executions, and LLM inferences as OpenTelemetry spans.

### 5. Validation & Evaluations
- **Astrophysical Constraint Enforcement:** A dedicated Validator Node enforces hard physical boundaries utilizing strict Pydantic `BaseModel` assertions. Edges that fail validation emit structured error parameters back into the graph.
- **Offline Evaluation (`src/evals/`):** Quality assessments run via `pydantic_evals`, grading extraction accuracy and prompt effectiveness locally.
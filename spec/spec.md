# Product Specification: XPI — Independent Agentic Exoplanet Vetting

## Overview
XPI is an automated, multi-agent pipeline designed to vet exoplanet candidates. It analyzes photometric data and scientific literature, flags conflicting evidence, and produces a transparent, fully reproducible Vetting Report. The framework uses Pydantic AI as a lightweight agent manager, utilizing its deep integration with Pydantic for structural validation, type safety, and runtime execution control. The system enforces strict physical laws and uses probabilistic confidence scoring.

## User Scenarios

1. **Transparent Vetting Report:** A researcher submits a candidate ID (KIC/TIC/TOI). The system produces a Vetting Report with a disposition (Planet Candidate / False Positive / Inconclusive), confidence score, annotated light curve, and a reasoning trace citing data and literature.
2. **Provenance Tracing:** A researcher uses the JSON-LD Lineage Map to trace any calculated physical parameter to its source data quarter or literature citation without rerunning the pipeline.
3. **Conflict Detection:** If quantitative data (e.g., a clean transit) and literature (e.g., known eclipsing binary) diverge beyond a threshold, the system flags a Consensus Conflict, detailing the divergence instead of averaging the scores.
4. **Anomaly Investigation:** If an asymmetric or irregular transit is detected, the system generates an Anomaly Record and directs literature searches specifically toward non-planetary hypotheses.
5. **System Evaluation:** A pipeline maintainer runs the Benchmark Runner against a Golden Dataset of ≥40 known objects, receiving a Confusion Matrix and F1 score to detect regressions. Developers run isolated `pydantic_evals` on the distillation agent to verify extraction quality without live LLM calls.

## System Requirements

### 1. Multi-Agent Pipeline & Orchestration
- The system orchestrates five specialized agents using Pydantic AI: Observer, Scholar, Distillation, Synthesizer, and Validator.
- Pydantic AI handles agent state, system prompts, dependency injection, and tool calling across the entire pipeline.
- The execution flow is acyclic, except for strictly bounded self-correction loops managed by the Synthesizer.

### 2. Strict Typing & Data Contracts
- All inter-agent communication and state transitions rely on validated Pydantic models. Raw dictionaries and untyped tuples are prohibited.
- All tools (`get_light_curve`, `fit_transit`, `search_arxiv`, etc.) must be registered as Pydantic AI tools and return typed Pydantic models (`LightCurveResult`, `TransitFitResult`, etc.).

### 3. Agentic Execution & Configurations
- LLM-backed agents rely on YAML specifications (e.g., `config/agent_specs/distillation.yaml`) defining the target model identifier, system prompt overrides, and operational bounds.
- Pydantic AI's built-in retry mechanisms and validation error handling must be used to recover from transient API failures or malformed model responses.
- Agents must operate within a defined token budget. Overruns must raise typed errors, prohibiting silent truncation.

### 4. Lineage & Traceability
- Every Vetting Report must link to a JSON-LD Lineage Map passing automated schema validation with zero unresolved parameter references.

### 5. Validation & Evaluations
- **Astrophysical Constraint Enforcement:** A standalone Validator Agent enforces hard physical boundaries on final parameters (e.g., mass-radius limits, stellar density constraints). Any edge-case or failure state requires a `validator_failed` annotation.
- **The Golden Dataset:** The system relies on a curated, static benchmark corpus consisting of ≥40 verified objects to detect pipeline performance regressions. This dataset explicitly includes a balanced distribution of true exoplanets alongside verified astrophysical false positives (such as Eclipsing Binaries and Background Blends). The presence of false positives is mathematically mandatory to calculate a complete Confusion Matrix, allowing the evaluation suite to measure Precision, Recall, and F1-Scores without signal bias.
- **Offline vs. Inline Validation Architecture:** - *Inline Validation:* Handled strictly via runtime Pydantic structural validation. If an agent emits a malformed data payload during a run, Pydantic AI's built-in retry framework intercepts and corrects the schema violation immediately.
  - *Offline Evaluation (`src/evals/`):* Quality assessments of agent extraction accuracy, prompt effectiveness, and semantic reasoning are executed exclusively offline using `pydantic_evals`. Running these checks asynchronously separates functional execution from meta-analysis, isolates production performance from test-induced latency, and prevents the compounding LLM token costs associated with live grading or "judge" LLM calls.
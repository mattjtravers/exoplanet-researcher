# Agent Interface Contracts

**Feature**: 001-xpi-agentic-vetting | **Date**: 2026-04-09

Each contract defines the typed input and output schema for one agent node in the
LangGraph DAG. All types reference schemas defined in `data-model.md`. Violations of
these contracts MUST raise a typed error at the node boundary (FR-033).

---

## Observer Agent

**File**: `src/agents/observer.py`
**Responsibility**: Quantitative light curve analysis and anomaly detection.

### Input

```python
class ObserverInput(BaseModel):
    candidate: CandidateTarget
    agent_config: AgentConfig
```

### Output

```python
class ObserverOutput(BaseModel):
    confidence: ConfidenceAssessment          # agent="observer"
    lineage_partial: list[LineageEntry]       # entries for all computed parameters
    anomaly_records: list[AnomalyRecord]      # empty list if no anomalies detected
```

**Contract rules**:
- `confidence.agent` MUST equal `"observer"`
- `lineage_partial` MUST contain an entry for every parameter in `confidence.primary_evidence`
- `anomaly_records` MUST be an empty list (not `None`) when no anomalies are detected

---

## Scholar Agent

**File**: `src/agents/scholar.py`
**Responsibility**: Agentic iterative literature retrieval and confidence scoring.

### Input

```python
class ScholarInput(BaseModel):
    candidate: CandidateTarget
    anomaly_directives: list[str]             # hypothesis categories from AnomalyRecords
    agent_config: AgentConfig
```

### Output

```python
class ScholarOutput(BaseModel):
    confidence: ConfidenceAssessment          # agent="scholar"
    distilled_records: list[DistilledLiteratureRecord]
    queries_issued: list[str]                 # all search queries generated (for audit)
    lineage_partial: list[LineageEntry]       # entries for all cited paper parameters
```

**Contract rules**:
- `confidence.agent` MUST equal `"scholar"`
- If `anomaly_directives` is non-empty, at least one query in `queries_issued` MUST
  contain a term from `anomaly_directives`
- `distilled_records` MAY be empty (no literature found); confidence score MUST be
  low (≤ 40%) and disposition MUST be `"inconclusive"` in this case

---

## Distillation Agent

**File**: `src/agents/distillation.py`
**Responsibility**: Compress retrieved papers to target-relevant content.

### Input

```python
class DistillationInput(BaseModel):
    raw_papers: list[tuple[str, str]]         # (source_id, full_text) pairs
    target_star_id: str
    agent_config: AgentConfig
```

### Output

```python
class DistillationOutput(BaseModel):
    records: list[DistilledLiteratureRecord]
    total_tokens_consumed: int
```

**Contract rules**:
- `records` length MUST equal `raw_papers` length (one record per paper, even if empty)
- `total_tokens_consumed` MUST be ≤ `agent_config.token_budget`; if budget would be
  exceeded during processing, MUST raise `TokenBudgetExceededError` before the LLM call
- `citation_string` in each record MUST be verbatim from the source paper

---

## Synthesizer Agent

**File**: `src/agents/synthesizer.py`
**Responsibility**: Conflict detection, resolution loop, and final disposition.

### Input

```python
class SynthesizerInput(BaseModel):
    observer_output: ObserverOutput
    scholar_output: ScholarOutput
    agent_config: AgentConfig
    iteration: int = 0                        # current correction loop count
```

### Output

```python
class SynthesizerOutput(BaseModel):
    disposition: Literal["planet_candidate", "false_positive", "inconclusive"]
    consensus_confidence: float | None        # present if no unresolved conflict
    conflict_flag: ConsensusConflictFlag | None  # present if unresolved
    reasoning_trace: list[ReasoningStep]
```

**Contract rules**:
- Exactly one of `consensus_confidence` or `conflict_flag` MUST be non-None
- `conflict_flag.resolved` MUST be `False` only when `iteration` ≥
  `agent_config.max_iterations`
- `reasoning_trace` MUST be non-empty

---

## Validator Agent

**File**: `src/agents/validator.py`
**Responsibility**: Physical law constraint enforcement.

### Input

```python
class ValidatorInput(BaseModel):
    synthesizer_output: SynthesizerOutput
    observer_output: ObserverOutput
    candidate: CandidateTarget
```

### Output

```python
class ValidatorOutput(BaseModel):
    result: ValidatorResult
    annotated_disposition: Literal["planet_candidate", "false_positive",
                                   "inconclusive", "validator_failed"]
```

**Contract rules**:
- If `result.passed` is `False`, `annotated_disposition` MUST be `"validator_failed"`
- `result.violations` MUST be non-empty when `result.passed` is `False`
- The Validator MUST NOT alter confidence scores — it only annotates the disposition

---

## Pipeline State

**File**: `src/dag/pipeline.py`

```python
class PipelineState(TypedDict):
    candidate: CandidateTarget
    config: dict[str, AgentConfig]            # keyed by agent name
    observer_output: ObserverOutput | None
    scholar_output: ScholarOutput | None
    distillation_output: DistillationOutput | None
    synthesizer_output: SynthesizerOutput | None
    validator_output: ValidatorOutput | None
    lineage_map: LineageMap | None
    vetting_report: VettingReport | None
    error: str | None                          # set if any node raises
```

**Contract rule**: No agent node MAY write to a field that is not its designated output
field. Reading from other fields for context is permitted.

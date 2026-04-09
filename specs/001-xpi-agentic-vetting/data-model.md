# Data Model: XPI — Independent Agentic Exoplanet Vetting

**Phase**: 1 | **Date**: 2026-04-09 | **Plan**: [plan.md](plan.md)

All entities are implemented as PydanticAI `BaseModel` subclasses in `src/schemas/`.
Field constraints are schema validators (not runtime checks), per Principle II.

---

## CandidateTarget

**File**: `src/schemas/candidate.py`
**Purpose**: The exoplanet candidate submitted for vetting.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `target_id` | `str` | non-empty, matches KIC/TIC/TOI pattern | Primary identifier |
| `catalog` | `Literal["KIC","TIC","TOI"]` | required | Source catalogue |
| `stellar_radius_rsun` | `float \| None` | > 0 if present | Host star radius in solar radii |
| `stellar_mass_msun` | `float \| None` | > 0 if present | Host star mass in solar masses |
| `stellar_teff_k` | `float \| None` | 2000–60000 if present | Effective temperature (K) |
| `available_quarters` | `list[int]` | non-empty | Kepler/TESS data quarters available |
| `prior_disposition` | `str \| None` | — | Previously published disposition, if any |

**Relationships**: Root input to the pipeline. Referenced by `LineageEntry.source_id`
when the candidate's own properties are used as inputs to a calculation.

---

## LineageEntry

**File**: `src/schemas/lineage.py`
**Purpose**: A single provenance record linking one physical parameter to its origin.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `parameter_name` | `str` | non-empty | e.g., `"rp_rs"`, `"period_days"` |
| `parameter_value` | `float \| str` | required | The computed or extracted value |
| `tool_call_id` | `str` | non-empty | ID of the tool call that produced this value |
| `source_id` | `str` | non-empty | NASA quarter ID or ArXiv/ADS identifier |
| `source_type` | `Literal["nasa_quarter","arxiv","ads","candidate"]` | required | Disambiguates `source_id` format |
| `agent` | `str` | non-empty | Name of the agent that created this entry |
| `timestamp` | `datetime` | auto-set | UTC time of creation |

---

## LineageMap

**File**: `src/schemas/lineage.py`
**Purpose**: The complete JSON-LD provenance document for one Vetting Report.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `context` | `str` | fixed value `"https://xpi.science/lineage/v1"` | JSON-LD `@context` |
| `target_id` | `str` | non-empty | Links map to its `CandidateTarget` |
| `entries` | `list[LineageEntry]` | non-empty | All parameter provenance records |
| `confidence_entries` | `list[ConfidenceLineageEntry]` | non-empty | Confidence score provenance |
| `created_at` | `datetime` | auto-set | UTC creation time |
| `schema_version` | `str` | semver format | Lineage Map schema version |

**Validation rule**: After construction, a validator asserts that every
`parameter_name` referenced in the `VettingReport` has a corresponding `LineageEntry`.
Dangling references raise `ValidationError`.

**Serialisation**: `model.model_dump_json()` with `@context` field produces valid
JSON-LD. A companion JSON Schema file at `contracts/lineage-map-schema.json` is used
for independent validation.

---

## ConfidenceAssessment

**File**: `src/schemas/confidence.py`
**Purpose**: An agent's independent scoring of the candidate's disposition.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `agent` | `Literal["observer","scholar"]` | required | Issuing agent |
| `score` | `float` | 0.0 ≤ score ≤ 100.0 | Confidence percentage |
| `disposition` | `Literal["planet_candidate","false_positive","inconclusive"]` | required | Agent's assessed disposition |
| `primary_evidence` | `list[str]` | non-empty | Source IDs (quarters or paper IDs) driving the assessment |
| `reasoning_summary` | `str` | non-empty | Plain-language explanation |

---

## ConsensusConflictFlag

**File**: `src/schemas/report.py`
**Purpose**: Raised when Observer and Scholar diverge beyond the configured threshold.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `observer_assessment` | `ConfidenceAssessment` | required | Observer's score |
| `scholar_assessment` | `ConfidenceAssessment` | required | Scholar's score |
| `divergence` | `float` | ≥ 0.0 | Absolute score difference |
| `threshold_used` | `float` | > 0.0 | Configured threshold at time of detection |
| `conflict_summary` | `str` | non-empty | Plain-language description of the disagreement |
| `resolved` | `bool` | required | Whether the correction loop resolved the conflict |
| `resolution_reasoning` | `str \| None` | required if `resolved=True` | How conflict was resolved |

---

## AnomalyRecord

**File**: `src/schemas/report.py`
**Purpose**: Documents an irregular signal detected in the light curve.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `anomaly_type` | `Literal["aperiodicity","asymmetric_transit","flux_spike","other"]` | required | Signal classification |
| `data_quarter` | `int` | ≥ 0 | Quarter in which the anomaly was detected |
| `description` | `str` | non-empty | Plain-language description |
| `sigma_deviation` | `float` | ≥ 0.0 | Statistical significance of the anomaly |
| `hypotheses_searched` | `list[str]` | non-empty | Non-planetary explanations searched |
| `literature_references` | `list[str]` | — | ArXiv/ADS IDs found for these hypotheses |

---

## VettingReport

**File**: `src/schemas/report.py`
**Purpose**: The primary output document of the pipeline.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `target_id` | `str` | non-empty | Candidate identifier |
| `disposition` | `Literal["planet_candidate","false_positive","inconclusive"]` | required | Final disposition |
| `consensus_confidence` | `float \| None` | 0–100 if present | Combined confidence (present if no unresolved conflict) |
| `conflict_flag` | `ConsensusConflictFlag \| None` | — | Present if divergence exceeded threshold and was not resolved |
| `anomaly_records` | `list[AnomalyRecord]` | default `[]` | Empty list if no anomalies |
| `reasoning_trace` | `list[ReasoningStep]` | non-empty | Sequential log of conclusions |
| `validator_result` | `ValidatorResult` | required | Physical law check outcome |
| `lineage_map_path` | `str` | non-empty | Relative path to the JSON-LD Lineage Map file |
| `light_curve_chart_path` | `str` | non-empty | Relative path to the annotated PNG |
| `interpretive_description` | `str` | non-empty | System-authored chart description |
| `created_at` | `datetime` | auto-set | UTC report generation time |

**Validation rule**: `consensus_confidence` and `conflict_flag` are mutually exclusive;
at least one must be present.

---

## ReasoningStep

**File**: `src/schemas/report.py`
**Purpose**: One entry in the Reasoning Trace.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `step_number` | `int` | ≥ 1, sequential | Order in the trace |
| `agent` | `str` | non-empty | Agent that produced this step |
| `conclusion` | `str` | non-empty | Plain-language statement |
| `data_sources` | `list[str]` | — | NASA quarter IDs or paper IDs used |
| `tool_calls` | `list[str]` | — | Tool call IDs invoked |

---

## ValidatorResult

**File**: `src/schemas/report.py`
**Purpose**: Outcome of physical law validation.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `passed` | `bool` | required | Whether all constraints were satisfied |
| `violations` | `list[ValidatorViolation]` | default `[]` | Each failed constraint |

## ValidatorViolation

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `constraint` | `str` | non-empty | Name of the violated constraint (e.g., `"mass_radius_bound"`) |
| `observed_value` | `float` | required | The parameter value that failed |
| `allowed_range` | `tuple[float, float]` | required | (min, max) allowed |
| `description` | `str` | non-empty | Plain-language violation description |

---

## DistilledLiteratureRecord

**File**: `src/schemas/literature.py`
**Purpose**: Output of the Distillation Agent — target-relevant extraction from one paper.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `source_id` | `str` | non-empty, ArXiv or ADS format | Paper identifier |
| `source_type` | `Literal["arxiv","ads"]` | required | Disambiguates ID format |
| `target_star_id` | `str` | non-empty | Star ID this record was extracted for |
| `extracted_parameters` | `dict[str, float \| str]` | — | Verbatim parameter values keyed by name |
| `disposition_notes` | `str \| None` | — | Verbatim quoted disposition text from the paper |
| `citation_string` | `str` | non-empty | Full verbatim citation (author, year, journal, DOI) |
| `distillation_token_count` | `int` | > 0 | Tokens consumed by the Distillation Agent for this record |

---

## BenchmarkResult

**File**: `src/schemas/benchmark.py`
**Purpose**: Output of one Benchmark Runner execution.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `run_id` | `str` | UUID format | Unique run identifier |
| `run_timestamp` | `datetime` | auto-set | UTC start time |
| `dataset_version` | `str` | non-empty | Golden Dataset version tag |
| `true_positives` | `int` | ≥ 0 | Correctly identified planets |
| `false_positives` | `int` | ≥ 0 | False positives called planet |
| `true_negatives` | `int` | ≥ 0 | Correctly identified false positives |
| `false_negatives` | `int` | ≥ 0 | Planets called false positive |
| `precision` | `float` | 0–1, computed | TP / (TP + FP) |
| `recall` | `float` | 0–1, computed | TP / (TP + FN) |
| `f1` | `float` | 0–1, computed | 2 × precision × recall / (precision + recall) |
| `per_object_results` | `list[ObjectResult]` | non-empty | Per-candidate breakdown |
| `failures` | `list[ObjectFailure]` | default `[]` | Objects where the pipeline raised an error |

---

## GoldenDataset

**File**: `src/schemas/benchmark.py`
**Purpose**: The evaluation corpus.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `dataset_version` | `str` | non-empty | Download date + row count hash |
| `source_table` | `str` | non-empty | e.g., `"NASA KOI Cumulative Table v2026-04-09"` |
| `objects` | `list[GoldenObject]` | ≥ 40 | Labelled candidates |

## GoldenObject

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `target_id` | `str` | KIC format | Candidate identifier |
| `ground_truth` | `Literal["planet_candidate","false_positive"]` | required | NASA confirmed label |

---

## AgentConfig

**File**: `src/schemas/config.py`
**Purpose**: Per-agent runtime configuration loaded from `config/agents.yaml`.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `token_budget` | `int` | > 0 | Maximum tokens per LLM call |
| `max_iterations` | `int \| None` | > 0 if present | Loop iteration cap (Scholar, Synthesizer) |
| `conflict_threshold` | `float \| None` | 0–100 if present | Conflict detection threshold (Synthesizer only) |
| `anomaly_sigma_threshold` | `float \| None` | > 0 if present | Anomaly detection sensitivity (Observer only) |

---

## State Transitions

```
CandidateTarget
  │
  ▼
PipelineState (DAG entry)
  │
  ├─► Observer node → ConfidenceAssessment (observer) + LineageMap partial + optional AnomalyRecord
  │
  ├─► Scholar node → ConfidenceAssessment (scholar) + list[DistilledLiteratureRecord]
  │       │
  │       └─► Distillation Agent (pre-Scholar) → list[DistilledLiteratureRecord]
  │
  ├─► Synthesizer node → ConsensusConflictFlag (if divergence) or consensus_confidence
  │       │
  │       └─► Self-correction loop (bounded) if ConflictFlag emitted
  │
  ├─► Validator node → ValidatorResult
  │
  └─► Report Assembly → VettingReport + merged LineageMap (JSON-LD) + PNG
```

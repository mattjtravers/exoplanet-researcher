# Feature Specification: XPI — Independent Agentic Exoplanet Vetting

**Feature Branch**: `001-xpi-agentic-vetting`
**Created**: 2026-04-09
**Status**: Draft

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Researcher Receives a Transparent Vetting Report (Priority: P1)

A planetary scientist submits a candidate target identifier (e.g., a KIC, TIC, or TOI
number) and receives a complete **Vetting Report** containing: a final disposition
(Planet Candidate / False Positive / Inconclusive), a confidence score, an interpretive
annotated light curve visualisation, and a full reasoning trail showing how each
conclusion was reached.

**Why this priority**: This is the core value proposition. Every other feature exists
to make this report trustworthy and reproducible. Without it the system has no output.

**Independent Test**: Submit a known confirmed planet ID. The system produces a Vetting
Report with a "Planet Candidate" disposition, a confidence score, at least one annotated
light curve chart with an interpretive description, and a reasoning trace citing at
least one data quarter and one literature source.

**Acceptance Scenarios**:

1. **Given** a valid candidate target ID, **When** the researcher submits it,
   **Then** the system produces a Vetting Report containing disposition, confidence
   score, annotated light curve visualisation with interpretive description, and
   Reasoning Trace.

2. **Given** a candidate with an existing literature history, **When** the report is
   generated, **Then** every cited physical parameter is linked to the specific
   literature source and data measurement that produced it.

3. **Given** a candidate for which no literature exists, **When** the report is
   generated, **Then** the system documents the absence of literature explicitly, relies
   solely on quantitative analysis, and notes the increased uncertainty in the
   confidence score.

---

### User Story 2 — Researcher Traces Any Parameter to Its Origin (Priority: P1)

A researcher reviewing a report questions how a specific physical parameter (e.g., the
planet-to-star radius ratio) was derived. They open the accompanying **Lineage Map**
and trace the parameter directly to the source measurement and the paper that validated
the host-star property used in the calculation — without contacting the authors or
re-running the pipeline.

**Why this priority**: Without traceability, the report cannot be peer-reviewed or
reproduced. This is a constitutional requirement and a prerequisite for scientific
credibility.

**Independent Test**: Open the Lineage Map for a completed Vetting Report. For any
selected parameter, the map provides: the data quarter or instrument reading used, the
operation that computed it, and the ArXiv or ADS identifier of the reference paper.
Parse the Lineage Map with a schema validator — zero unresolved references.

**Acceptance Scenarios**:

1. **Given** a completed Vetting Report, **When** the researcher opens its Lineage Map,
   **Then** every physical parameter entry links to a data source identifier and a
   recorded operation — no dangling references exist.

2. **Given** a Lineage Map, **When** parsed by an automated validator,
   **Then** it passes schema validation and all source identifiers are resolvable
   (valid NASA quarter IDs or valid ArXiv/ADS IDs).

3. **Given** a Lineage Map that includes confidence scores, **When** examined,
   **Then** each score is linked to the agent that produced it and the evidence it used.

---

### User Story 3 — System Flags a Conflict Between Quantitative and Literary Evidence (Priority: P2)

The quantitative analysis concludes a candidate is likely a planet (high confidence),
but the literature review surfaces a paper identifying the host star as an eclipsing
binary. The system detects the divergence, raises a **Consensus Conflict Flag**, and
presents both assessments with their evidence before attempting resolution — rather than
silently averaging the scores.

**Why this priority**: Averaging conflicting signals without disclosure is the primary
failure mode this system is designed to prevent. Conflict detection is the key
differentiator from black-box models.

**Independent Test**: Submit a known false positive (eclipsing binary mislabelled as a
planet candidate). Verify the report contains a Consensus Conflict Flag with the
quantitative confidence score, the qualitative confidence score, and at least one
citation explaining the binary classification.

**Acceptance Scenarios**:

1. **Given** a candidate where quantitative and qualitative confidence scores diverge
   by more than the configured threshold, **When** the Synthesizer runs,
   **Then** the report contains a Consensus Conflict Flag with both scores and the
   primary evidence from each assessor.

2. **Given** a Consensus Conflict Flag, **When** a researcher reads the report,
   **Then** the flag includes a plain-language summary of the specific disagreement
   (e.g., "Transit geometry is consistent with a planet, but literature identifies the
   host as a known binary system").

3. **Given** a candidate where both assessments agree, **When** the Synthesizer runs,
   **Then** no Conflict Flag is emitted and a single consensus confidence score is
   reported.

---

### User Story 4 — System Detects and Investigates Light Curve Anomalies (Priority: P2)

During analysis, the system detects an asymmetric transit profile inconsistent with
a simple planetary occultation. It flags the anomaly, directs its literature search
specifically toward non-planetary explanations for that target, and includes an
**Anomaly Record** in the final report — rather than discarding the edge case.

**Why this priority**: Routine transit detection is well-solved. XPI's novel value lies
in identifying edge cases that distinguish a real discovery from known false positive
classes.

**Independent Test**: Submit a candidate with a known asymmetric transit (e.g., a
confirmed dusty debris disk target). Verify the report contains an Anomaly Record
describing the irregular signal and citing at least one literature reference related to
a non-planetary hypothesis.

**Acceptance Scenarios**:

1. **Given** a light curve containing aperiodicities or asymmetric transit features,
   **When** the Observer analyses it, **Then** an Anomaly Record is created and the
   Scholar is directed to search for non-planetary explanations.

2. **Given** an Anomaly Record, **When** included in the Vetting Report, **Then** it
   contains: the anomalous feature described in plain language, the data quarter it was
   found in, and the non-planetary hypothesis categories that were searched.

3. **Given** a clean, symmetric transit signal, **When** analysed,
   **Then** no Anomaly Record is created and analysis proceeds through the standard path.

---

### User Story 5 — Benchmark Operator Measures System Accuracy (Priority: P3)

A benchmark operator runs the **Benchmark Runner** against the Golden Dataset of 40
known objects. The runner executes the full pipeline on each object and produces a
Confusion Matrix with F1 score. The operator uses these metrics to detect regressions
after a model swap or configuration change.

**Why this priority**: Without quantitative accuracy measurement there is no way to
validate improvements or detect regressions — the system cannot be trusted in
production without it.

**Independent Test**: Execute the Benchmark Runner against the full Golden Dataset
(≥20 confirmed planets, ≥20 confirmed false positives). The runner completes without
manual intervention, outputs a Confusion Matrix and F1 score, and persists results to
the benchmark history.

**Acceptance Scenarios**:

1. **Given** the Golden Dataset is available, **When** the Benchmark Runner executes,
   **Then** it processes every object and produces a Confusion Matrix (TP, FP, TN, FN)
   with precision, recall, and F1.

2. **Given** a completed benchmark run, **When** compared to the prior stored result,
   **Then** the system flags any F1 regression exceeding 5 percentage points as a
   blocking failure.

3. **Given** a pipeline failure on one specific object during a run, **When** the run
   completes, **Then** the failure is logged with object ID and reason, and the
   remaining objects are still evaluated.

---

### Edge Cases

- What happens when the archive returns no light curve data for a submitted ID?
- What happens when the literature search returns zero results for a candidate?
- What happens when all retrieved papers are inaccessible (paywalled or unavailable)?
- How are partial Lineage Maps handled if an operation fails mid-pipeline?
- What disposition is reported when both quantitative and qualitative analyses are
  inconclusive (low confidence on both sides)?
- What happens when the Distillation step finds no parameters relevant to the target
  Star ID in a retrieved paper?
- What happens when the physical law Validator rejects a parameter produced by the
  Observer?

---

## Requirements *(mandatory)*

### Functional Requirements

**Multi-Agent Pipeline**

- **FR-001**: The system MUST orchestrate analysis through five specialised agents:
  Observer (quantitative analysis), Scholar (literature synthesis), Distillation Agent
  (paper preprocessing), Synthesizer (conflict resolution and reporting), and Validator
  (physical law enforcement).
- **FR-002**: Each agent MUST have a single bounded responsibility and MUST NOT perform
  work belonging to another agent.
- **FR-003**: The pipeline MUST be acyclic — execution flow MUST NOT cycle between
  agents except within explicitly bounded self-correction loops, each of which MUST
  have a configurable maximum iteration count.

**Data Access**

- **FR-004**: All raw photometric data retrieval MUST route through a standardised,
  model-agnostic data-access interface that exposes operations as discoverable tools.
- **FR-005**: No agent MAY make direct, unmediated archive calls outside of this
  interface.

**Scientific Lineage & Traceability**

- **FR-006**: Every Vetting Report MUST be accompanied by a machine-readable Lineage
  Map linking each physical parameter to: (a) the operation that produced it, and
  (b) the data source (NASA quarter ID or ArXiv/ADS identifier) used as input.
- **FR-007**: The Lineage Map MUST pass automated schema validation independently of the
  report narrative, with zero unresolved parameter references.
- **FR-008**: Confidence scores MUST be recorded in the Lineage Map, linked to the
  agent and evidence that generated each score.

**Probabilistic Confidence & Conflict Detection**

- **FR-009**: The Observer MUST output an independent numerical confidence score
  (0–100%) based solely on quantitative data.
- **FR-010**: The Scholar MUST output an independent numerical confidence score
  (0–100%) based solely on retrieved literature.
- **FR-011**: The Synthesizer MUST compare both scores; when divergence exceeds the
  configured conflict threshold it MUST emit a Consensus Conflict Flag containing both
  scores, both dispositions, and the primary evidence from each agent.
- **FR-012**: A Conflict Flag MUST trigger a dedicated reasoning loop in which the
  Synthesizer attempts reconciliation before issuing a final disposition.
- **FR-013**: Any unresolved Conflict Flag MUST appear in the final Vetting Report
  alongside the disposition — silent averaging of conflicting scores is prohibited.

**Anomaly Detection**

- **FR-014**: The Observer MUST analyse each light curve for aperiodicities, asymmetric
  transit profiles, and signals inconsistent with simple planetary occultation.
- **FR-015**: When an anomaly is detected the Observer MUST create an Anomaly Record
  and direct the Scholar to search for non-planetary explanations (stellar variability,
  dust disks, eclipsing binaries).
- **FR-016**: Every Anomaly Record MUST appear in the Vetting Report with: anomaly
  description, affected data quarter, and non-planetary hypotheses explored.

**Agentic Literature Retrieval**

- **FR-017**: The Scholar MUST generate its own search queries from the candidate's
  properties and prior findings — pre-defined static queries are prohibited as the
  primary retrieval strategy.
- **FR-018**: The Scholar MUST iterate its search — expanding or refining queries —
  when initial results are insufficient to produce a confidence score.
- **FR-019**: Every paper cited in the report MUST be identified by its ArXiv or ADS
  identifier in the Lineage Map.

**Distillation Pipeline**

- **FR-020**: Before retrieved papers reach the Synthesizer, the Distillation Agent
  MUST extract only the physical parameters and disposition notes relevant to the target
  Star ID — full-text documents MUST NOT be forwarded directly.
- **FR-021**: Physical parameter values and verbatim citation strings MUST be preserved
  exactly during distillation; paraphrasing these fields is prohibited.
- **FR-022**: Each agent MUST operate within a configurable processing budget; exceeding
  the budget MUST produce a typed error — silent truncation is prohibited.

**Vetting Report**

- **FR-023**: Every Vetting Report MUST contain: target ID, final disposition, consensus
  confidence score (or unresolved Conflict Flag), interpretive annotated light curve
  visualisation, Reasoning Trace, Anomaly Records (if any), Validator findings, and
  a reference to its Lineage Map.
- **FR-024**: The light curve visualisation MUST include a system-authored interpretive
  description — not only a raw chart.
- **FR-025**: The Reasoning Trace MUST be a sequential log linking each conclusion to
  the agent, data source, and literature reference that produced it.

**Physical Law Validation**

- **FR-026**: The Validator MUST check that reported physical parameters satisfy known
  astrophysical constraints (e.g., mass-radius relationships, transit depth bounds)
  before the report is finalised.
- **FR-027**: A Validator failure MUST prevent the report from being issued without
  qualification; the failure and its reason MUST be documented in the report.

**Benchmark Runner**

- **FR-028**: A Benchmark Runner MUST exist as a standalone executable component,
  independent of the main vetting pipeline.
- **FR-029**: The Benchmark Runner MUST evaluate the full pipeline against a Golden
  Dataset of at least 40 objects (≥20 confirmed planets, ≥20 confirmed false positives
  from published NASA disposition tables).
- **FR-030**: The Benchmark Runner MUST output a Confusion Matrix (TP, FP, TN, FN)
  with precision, recall, and F1 score.
- **FR-031**: Benchmark results MUST be persisted and versioned so accuracy trends are
  traceable over time.
- **FR-032**: An F1 regression of more than 5 percentage points from the most recent
  stored result MUST be surfaced as a blocking failure.

**Inter-Agent Data Contracts**

- **FR-033**: All data passed between agents MUST conform to a defined schema contract
  for that interface. A schema validation failure MUST surface as an explicit typed
  error — silent passing of malformed or unvalidated data between agents is prohibited.

### Key Entities

- **CandidateTarget**: The object under investigation. Key attributes: unique identifier
  (KIC/TIC/TOI), stellar properties, available data quarters, prior disposition history.
- **VettingReport**: Primary output. Attributes: disposition, consensus confidence,
  Conflict Flag (if any), annotated light curve + interpretive description, Reasoning
  Trace, Anomaly Records, Validator findings, Lineage Map reference.
- **LineageMap**: Machine-readable provenance document. Attributes: parameter entries
  (name, value, producing operation, data source reference, paper citation), confidence
  score entries.
- **ConfidenceAssessment**: An agent's independent scoring output. Attributes: issuing
  agent, score (0–100%), disposition, primary evidence references.
- **ConsensusConflictFlag**: Raised on divergence. Attributes: quantitative score,
  qualitative score, divergence magnitude, evidence summaries from each agent.
- **AnomalyRecord**: Documented irregular signal. Attributes: anomaly type, affected
  data quarter, plain-language description, hypotheses explored, literature references.
- **DistilledLiteratureRecord**: Output of the Distillation Agent. Attributes: source
  identifier, target Star ID, extracted parameters (verbatim), disposition notes,
  citation string. Schema-validated before passing to the Synthesizer.
- **BenchmarkResult**: Benchmark run output. Attributes: run timestamp, dataset version,
  TP/FP/TN/FN counts, precision, recall, F1, per-object outcomes.
- **GoldenDataset**: Evaluation corpus. Attributes: ≥40 labelled objects, ground-truth
  dispositions, dataset version, NASA source table reference.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A researcher can submit a candidate ID and receive a complete Vetting
  Report — including disposition, confidence score, annotated visualisation with
  interpretive description, and Reasoning Trace — in a single uninterrupted workflow.
- **SC-002**: Every physical parameter in a Vetting Report can be traced to its origin
  data source and reference paper within 3 navigation steps using the Lineage Map.
- **SC-003**: The Lineage Map for any Vetting Report passes automated schema validation
  with zero unresolved parameter references.
- **SC-004**: The system surfaces a Consensus Conflict Flag on ≥ 90% of test cases
  where the ground-truth explanation involves a discrepancy between photometric
  appearance and known stellar classification.
- **SC-005**: Anomaly Detection identifies irregular transit signals in ≥ 85% of Golden
  Dataset objects with known non-planetary explanations.
- **SC-006**: The Benchmark Runner achieves an F1 score of ≥ 0.80 on the Golden
  Dataset at initial release.
- **SC-007**: The Benchmark Runner completes a full 40-object evaluation and produces a
  Confusion Matrix without manual intervention.
- **SC-008**: Processing budget overruns surface as typed errors in 100% of cases —
  zero silent truncations observed in a 40-object benchmark run.

---

## Assumptions

- Candidate target IDs are valid identifiers resolvable against NASA's public archive;
  validation of malformed IDs is out of scope for v1.
- The Golden Dataset uses NASA's published Cumulative KOI Table and confirmed planet
  catalogue as the ground-truth source; no proprietary data is required.
- Literature retrieval assumes ArXiv and ADS are accessible from the deployment
  environment; offline-only operation is out of scope for v1.
- The conflict threshold (default: 30 percentage points divergence) is operator
  configurable; no fixed value is mandated by this spec.
- Interpretive descriptions of light curve visualisations are generated automatically
  by the system; human editorial review is not part of the automated pipeline.
- The Benchmark Runner is triggered manually or via a CI event; real-time continuous
  benchmarking is out of scope for v1.
- Multi-candidate batch submission is out of scope for v1; the pipeline processes one
  candidate per invocation.

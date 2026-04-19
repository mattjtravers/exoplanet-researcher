# Research: XPI — Independent Agentic Exoplanet Vetting

**Phase**: 0 | **Date**: 2026-04-09 | **Plan**: [plan.md](plan.md)

---

## 1. Lineage Map Format

**Decision**: JSON-LD

**Rationale**: JSON-LD is machine-readable, schema-validatable with standard JSON
Schema tooling, and supports semantic linking via `@context`. It satisfies FR-006
(machine-readable), FR-007 (schema validation), and Principle I without requiring a
custom parser. Markdown lineage maps are human-readable but cannot be programmatically
validated for dangling references.

**Alternatives considered**:
- Markdown table: readable but not machine-validatable; rejected.
- Plain JSON: viable but lacks semantic context; JSON-LD is a strict superset with no
  additional implementation cost.

---

## 2. LangGraph State & Inter-Agent Contracts

**Decision**: `TypedDict` pipeline state with PydanticAI model fields; validation at
every node boundary via a decorator pattern.

**Rationale**: LangGraph's `StateGraph` accepts a `TypedDict` as state. Each agent
node receives the typed state and MUST return a state update. By enforcing that every
field in the state dict is either a PydanticAI `BaseModel` instance or `None`, schema
violations are caught at assignment time (FR-033). A shared `validate_input` /
`validate_output` decorator on each node provides the typed-error boundary without
repeating validation logic in every agent.

**Alternatives considered**:
- Untyped dict state: fast to prototype but allows silent data corruption; rejected per
  Principle II.
- Dataclasses: valid but PydanticAI validators provide richer constraint enforcement
  (e.g., score range, mandatory fields) with less boilerplate.

---

## 3. MCP Server Implementation Pattern

**Decision**: Python `mcp` SDK; single server process per pipeline invocation; tools
registered at startup from a manifest.

**Rationale**: The `mcp` Python SDK provides a standard tool-registration API that
makes each NASA data operation discoverable without hardcoded function calls in agent
code (FR-004, FR-005). Running one MCP server per pipeline invocation (not a shared
daemon) keeps scope simple and avoids shared-state bugs — consistent with Principle V
(YAGNI).

**Alternatives considered**:
- Direct `lightkurve` calls inside agents: violates FR-005; rejected.
- Shared long-running MCP daemon: adds process management complexity with no v1 benefit;
  deferred.

---

## 4. ArXiv and ADS Access

**Decision**: `arxiv` Python client for ArXiv; ADS REST API via `requests` with an
ADS API token supplied via environment variable.

**Rationale**: The `arxiv` client handles pagination and rate-limiting. ADS REST API
(`api.adsabs.harvard.edu`) supports field-level queries (author, abstract, identifier)
and returns BibCode identifiers suitable for the Lineage Map. Both are accessible from
GitHub Codespaces without special network configuration.

**Alternatives considered**:
- `pyvo` for ADS: provides TAP/ADQL query interface but adds complexity for simple
  keyword searches; kept as an option for future versions.
- Web scraping: brittle and against both services' terms of use; rejected.

**Configuration required**: `ADS_API_TOKEN` environment variable must be set in the
devcontainer or Codespaces secrets.

---

## 5. Anomaly Detection Method

**Decision**: BLS periodogram residuals for aperiodicity; ingress/egress asymmetry
ratio for morphology; flagged if > 2σ deviation from a symmetric box model.

**Rationale**: Box Least Squares (BLS) is the standard transit-search algorithm used
by NASA's TESS pipeline. Fitting a symmetric box model and measuring residuals provides
a principled, reproducible basis for the 2σ anomaly threshold. Ingress/egress ratio
(time to first contact / time to last contact) captures asymmetric transits (e.g.,
dust tails, contamination). Both methods use `lightkurve` and `astropy` directly,
consistent with the canonical stack.

**Alternatives considered**:
- Neural network anomaly detection: high accuracy but adds a model dependency, violates
  YAGNI for v1; deferred.
- Wavelet decomposition: powerful for non-periodic signals but adds complexity;
  deferred to v2.

**Threshold**: Default 2σ; configurable in `config/agents.yaml` under
`observer.anomaly_sigma_threshold`.

---

## 6. Token Budget Enforcement

**Decision**: Per-agent limits defined in `config/agents.yaml`; an `AgentConfig`
PydanticAI schema enforces the field; a shared base utility checks the budget before
each LLM call and raises `TokenBudgetExceededError` (a typed error) if exceeded.

**Rationale**: Centralising the budget check in a shared utility (not repeated in each
agent) satisfies Principle V (no duplication). Raising a typed error rather than
silently truncating satisfies Principle IX and FR-022.

**Config structure**:
```yaml
agents:
  observer:
    token_budget: 8000
    anomaly_sigma_threshold: 2.0
  scholar:
    token_budget: 16000
    max_iterations: 3
  distillation:
    token_budget: 4000
  synthesizer:
    token_budget: 12000
    conflict_threshold: 30
    max_correction_iterations: 2
  validator:
    token_budget: 4000
```

---

## 7. Distillation Strategy

**Decision**: Structured extraction prompt targeting the specific Star ID; output is
schema-validated as `DistilledLiteratureRecord` before leaving the Distillation Agent.

**Rationale**: Rather than summarising a paper freely (which risks losing verbatim
parameter values), the prompt instructs the LLM to extract only named fields
(stellar radius, mass, disposition, period, depth) for the exact Star ID. Any field
not found is left as `None` rather than inferred. This preserves FR-021 (verbatim
preservation) while meeting the token budget.

**Alternatives considered**:
- Free-form summarisation: faster but risks paraphrasing citation strings; rejected per
  FR-021.
- Embedding-based retrieval from paper chunks: more accurate but adds a vector store
  dependency violating YAGNI for v1; deferred.

---

## 8. Golden Dataset Source

**Decision**: NASA Exoplanet Archive Cumulative KOI Table (`cumulative.csv`) downloaded
at benchmark initialisation via the NASA Exoplanet Archive TAP service.

**Rationale**: The KOI Table is publicly accessible, machine-readable, and contains
`koi_disposition` labels (`CONFIRMED`, `FALSE POSITIVE`, `CANDIDATE`). Filtering to
`CONFIRMED` (≥20) and `FALSE POSITIVE` (≥20) provides the ground-truth labels required
by FR-029. No proprietary data access is needed.

**Alternatives considered**:
- Manual curated list: simpler but not reproducible or updatable; rejected.
- TESS TOI catalogue: valid alternative but KOI (Kepler) has denser literature
  coverage, making Scholar testing more meaningful.

**Dataset version pinning**: The KOI Table version (download date + row count) is
stored in the `GoldenDataset` schema's `dataset_version` field to ensure reproducibility.

<!-- v1.3.0 | Ratified: 2026-04-09 | Last Amended: 2026-04-19 -->

# Exoplanet Investigator (XPI) Constitution

## Core Principles

### I. Reasoning Transparency & Scientific Lineage (NON-NEGOTIABLE)

Every `VettingReport` MUST include a **Reasoning Trace** linking each claim to a data
source (NASA archive quarter, ArXiv/ADS ID, or computed metric) AND a **Lineage Map**
(JSON-LD or Markdown) tracing every physical parameter to the tool call that produced
it and the paper that validated the host-star property used. Lineage Maps MUST be
machine-readable and stored alongside the report. Black-box outputs are prohibited.

### II. Type-Safe Scientific Rigor

All inter-agent data AND all tool return values MUST use typed Pydantic models (no bare
`dict` or `tuple` returns from tools). Physical constraints (mass-radius relationships,
transit depth bounds) MUST be schema validators — not runtime checks. Validation failures
MUST surface as typed errors; silent data corruption is prohibited. All LLM-backed agents
MUST be defined as PydanticAI `Agent` instances with a typed `output_type`.

### III. Test-First Development (NON-NEGOTIABLE)

For all mathematical and data-pipeline logic: write tests → get approval → confirm red
→ implement green → refactor. Skipping any step MUST be justified in the feature plan's
Complexity Tracking table.

### IV. DAG-Driven Single-Responsibility Agents

The system MUST use a DAG-style sequential orchestration. LLM-backed agents MUST be
defined using PydanticAI `Agent` with YAML Agent Specs (`config/agent_specs/*.yaml`)
declaring at minimum: model identifier, system prompt, and retry count. Each agent
(Observer, Scholar, Synthesizer, Validator) MUST have one bounded responsibility and
MUST NOT perform another agent's work. Recursive self-correction loops MUST have a
defined maximum iteration count.

### V. Simplicity & YAGNI

Use the simplest design that satisfies the current requirement. Abstractions MUST NOT
be introduced unless immediately required by two or more concrete use cases. Speculative
features are prohibited.

### VI. Agentic RAG with Anomaly Detection

Paper retrieval MUST be agentic: the Scholar agent generates and iterates search terms
from candidate context — static queries are prohibited as the sole strategy. Retrieved
papers MUST be cited in the Reasoning Trace. The Observer MUST actively search for
anomalies (aperiodicities, asymmetric transits); the Scholar MUST correspondingly search
for non-planetary explanations (stellar variability, dust disks) when anomalies appear.

### VII. Uncertainty Quantification & Consensus Conflict Detection

Observer and Scholar MUST each produce an independent confidence score. The Synthesizer
MUST compare them; where divergence exceeds a configurable threshold (default: 30 pts)
it MUST emit a **Consensus Conflict Flag** containing both scores and the evidence
driving each. Confidence scores MUST propagate into the Lineage Map. Averaging without
flagging conflict is prohibited.

### VIII. Benchmark-Driven Accuracy Validation

A **Benchmark Runner** MUST execute the full pipeline against a Golden Dataset (≥20
confirmed planets, ≥20 confirmed false positives) and output a Confusion Matrix with
precision, recall, and F1. It MUST run as a standalone CI job. An F1 regression of
more than 5 percentage points from the prior run MUST block merge. Results MUST be
versioned alongside the codebase.

### IX. Context Efficiency & Token Budget Management

A **Distillation Agent** MUST preprocess retrieved papers before the Synthesizer,
extracting only parameters and disposition notes relevant to the target Star ID. Each
agent MUST operate within a configurable token budget (not hardcoded); exceeding it
MUST raise a typed error. Parameters and citations feeding the Reasoning Trace MUST be
preserved verbatim through distillation.

### X. Evaluation-Driven Quality Assurance

Agent output quality MUST be measurable. At least one `pydantic_evals.Dataset` MUST
exist for each LLM-backed agent, with named `Evaluator` classes covering key output
dimensions (e.g., parameter extraction completeness, disposition accuracy). Evaluation
datasets MUST be runnable independently of the benchmark runner without live LLM calls.
Ad-hoc LLM quality checks without a formal evaluator are prohibited.

## Technology Stack & Standards

Canonical stack — deviations require Complexity Tracking justification in the feature plan.

| Concern | Canonical Choice |
|---------|-----------------|
| Language | Python 3.11+ |
| Package manager | `uv` (venv isolation; no system-wide installs) |
| Orchestration | PydanticAI Agent Specs (`config/agent_specs/*.yaml`) + sequential DAG |
| Validation | PydanticAI — typed `output_type` on all LLM agents; Pydantic `BaseModel` on all tool returns |
| Evaluation | `pydantic_evals` — named `Dataset` + `Evaluator` per LLM-backed agent |
| LLM (runtime) | Model-agnostic; backend set via env var / config — no hardcoded model |
| Data tools | `lightkurve`, `astropy`, `numpy`, `matplotlib` |
| NASA data access | MCP server only — no direct HTTP calls in agent code |
| Quality control | `ruff` (lint/format), `pytest` (all tests) |
| Environment | GitHub Codespaces / devcontainer (Python 3.11+ image) |

Dependencies MUST be pinned in the `uv` lock file. Unpinned ("latest") in production is prohibited.

## Development Workflow

- **Branches**: sequential numeric prefix, e.g., `001-observer-agent`.
- **Commits**: atomic; MUST reference the task ID (e.g., `T012: implement transit fitter`).
- **Merge gate**: `ruff` lint + full `pytest` suite MUST pass; Benchmark Runner F1 MUST not regress > 5 pts.
- **Docs**: each agent module MUST have a docstring stating its single responsibility and its input/output schema types.

## Governance

This constitution supersedes all informal conventions. Where conflict exists with any
other artefact, this document takes precedence.

- **Amendments**: PR to `.specify/memory/constitution.md` stating bump type (MAJOR /
  MINOR / PATCH) + rationale, template sync, and one reviewer approval.
- **Versioning**: MAJOR = principle removal/redefinition; MINOR = new principle or
  material expansion; PATCH = wording/clarification.
- **Compliance gate**: Constitution Check in `plan-template.md` MUST be evaluated at
  plan start and re-checked after Phase 1. Unrecorded violations block plan approval.

**Version**: 1.3.0 | **Ratified**: 2026-04-09 | **Last Amended**: 2026-04-19

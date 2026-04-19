# Data Model: PydanticAI Migration

**Branch**: `002-pydantic-ai-migration` | **Date**: 2026-04-19

## New Entities (src/schemas/tools.py)

### LightCurveResult

Replaces the `dict` returned by `get_light_curve()`.

| Field | Type | Constraints | Notes |
|-------|------|------------|-------|
| `target_id` | `str` | non-empty | KIC/TIC/TOI identifier |
| `quarter` | `int` | ≥ 0 | Kepler quarter or TESS sector |
| `time` | `list[float]` | non-empty | BJD timestamps |
| `flux` | `list[float]` | same length as `time` | Normalised, detrended flux |
| `flux_err` | `list[float]` | same length as `time` | Flux uncertainties |
| `cadence` | `Literal["short", "long"]` | — | Derived from len(time) > 5000 |
| `tool_call_id` | `str` | UUID | Lineage identifier |

**Validation rules**: `len(flux) == len(time)`, `len(flux_err) == len(time)`.

---

### StellarPropertiesResult

Replaces the `dict` returned by `get_stellar_properties()`.

| Field | Type | Constraints | Notes |
|-------|------|------------|-------|
| `target_id` | `str` | non-empty | KIC/TIC/TOI identifier |
| `stellar_radius_rsun` | `float \| None` | > 0 if present | Stellar radius in solar radii |
| `stellar_mass_msun` | `float \| None` | > 0 if present | Stellar mass in solar masses |
| `stellar_teff_k` | `float \| None` | > 0 if present | Effective temperature (K) |
| `log_g` | `float \| None` | — | Surface gravity (cgs) |
| `metallicity_dex` | `float \| None` | — | [Fe/H] in dex |
| `source_catalog` | `str` | non-empty | Catalog name (e.g. "Kepler Stellar Properties Catalog DR25") |
| `tool_call_id` | `str` | UUID | Lineage identifier |

---

### TransitFitResult

Replaces the `dict` returned by `fit_transit()`.

| Field | Type | Constraints | Notes |
|-------|------|------------|-------|
| `target_id` | `str` | non-empty | Candidate identifier |
| `period_days` | `float` | > 0 | Best-fit orbital period |
| `depth` | `float` | ≥ 0 | Transit depth (fractional flux decrease) |
| `duration_hours` | `float` | > 0 | Transit duration in hours |
| `rp_rs` | `float` | ≥ 0 | Planet-to-star radius ratio (√depth) |
| `tool_call_id` | `str` | UUID | Lineage identifier |

**Physical constraint**: `rp_rs ≈ sqrt(depth)` — enforced by computation, not schema validator (value is computed, not user-supplied).

---

### LiteraturePaper

Replaces `tuple[str, str]` in `list[tuple[str, str]]` from search tools.

| Field | Type | Constraints | Notes |
|-------|------|------------|-------|
| `source_id` | `str` | non-empty | ArXiv ID or ADS bibcode |
| `abstract` | `str` | — | Paper abstract text |
| `source_type` | `Literal["arxiv", "ads"]` | — | Origin database |

**Note**: `source_type` is set by the producing function (`search_arxiv` → `"arxiv"`, `search_ads` → `"ads"`).

---

### LiteratureSearchResult

Replaces `tuple[list[tuple[str, str]], list[str]]` from `iterative_search()`.

| Field | Type | Constraints | Notes |
|-------|------|------------|-------|
| `papers` | `list[LiteraturePaper]` | may be empty | All retrieved papers from all queries |
| `queries_issued` | `list[str]` | default `[]` | Queries issued in order |

---

## New Intermediate Model (src/agents/distillation.py)

### DistillationExtraction

LLM output type for the PydanticAI distillation agent.

| Field | Type | Constraints | Notes |
|-------|------|------------|-------|
| `extracted_parameters` | `dict[str, float \| str]` | default `{}` | Parameter name → value map |
| `disposition_notes` | `str \| None` | — | Planetary vs FP disposition from LLM |
| `citation_string` | `str` | non-empty | Verbatim citation from abstract |

**Relationship**: `DistillationExtraction` is the `output_type` of the PydanticAI `Agent`. After extraction, fields are merged with caller-owned metadata (`source_id`, `source_type`, `target_star_id`, token count) to produce the existing `DistilledLiteratureRecord` schema (unchanged).

---

## New Evaluation Models (src/evals/)

### DistillationInput (evaluation case input)

| Field | Type | Notes |
|-------|------|-------|
| `source_id` | `str` | Paper identifier |
| `abstract` | `str` | Paper abstract |
| `target_star_id` | `str` | Target being vetted |

### EvaluationResult (from pydantic_evals)

Produced by named `Evaluator` classes. Fields: `score: float` (0.0–1.0), optional `reason: str`.

---

## Unchanged Entities

The following schemas are **not modified** by this feature:

- `DistilledLiteratureRecord` (`src/schemas/literature.py`) — existing, unchanged
- `ConfidenceAssessment` (`src/schemas/confidence.py`) — existing, unchanged
- `LineageEntry` (`src/schemas/lineage.py`) — existing, unchanged
- `VettingReport` (`src/schemas/report.py`) — existing, unchanged
- `CandidateTarget` (`src/schemas/candidate.py`) — existing, unchanged
- `AgentConfig` (`src/schemas/config.py`) — existing, unchanged
- All benchmark schemas — existing, unchanged

---

## Entity Relationships

```text
get_light_curve() ──► LightCurveResult
                           │
                           └──► ObserverAgent.run() ──► fit_transit()
                                                              │
                                                              └──► TransitFitResult ──► LineageEntry

get_stellar_properties() ──► StellarPropertiesResult

search_arxiv()  ──► list[LiteraturePaper] ──┐
search_ads()    ──► list[LiteraturePaper] ──┤
                                            └──► LiteratureSearchResult
                                                        │
                                                        └──► ScholarAgent ──► DistillationAgent
                                                                                      │
                                                                 (PydanticAI Agent)   │
                                                                 DistillationExtraction
                                                                        │
                                                                        └──► DistilledLiteratureRecord
```

---

## State Transitions

### Distillation Agent (updated)

```text
YAML spec loaded ──► Agent constructed ──► run_sync(prompt) ──► DistillationExtraction
                                                                        │
                                              (retry on validation fail) │ (up to N retries)
                                                                        └──► DistilledLiteratureRecord
                                                                               (merged with metadata)
```

### Tool Return Type Migration

```text
[Before] fit_transit() ──► dict ──► transit_params["key"]   (observer.py)
[After]  fit_transit() ──► TransitFitResult ──► transit_params.key
```

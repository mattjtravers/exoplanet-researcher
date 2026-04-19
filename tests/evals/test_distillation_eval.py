"""T024 — Tests for distillation evaluation dataset construction (no LLM calls)."""

from __future__ import annotations

from pydantic_evals import Dataset

from src.evals.distillation_eval import (
    DistillationInput,
    HasCitationString,
    HasExtractedPeriod,
    build_distillation_dataset,
)
from src.schemas.literature import DistilledLiteratureRecord


def _make_record(
    source_id: str = "test-id",
    extracted_parameters: dict | None = None,
    citation_string: str = "[test-id] Test citation...",
) -> DistilledLiteratureRecord:
    return DistilledLiteratureRecord(
        source_id=source_id,
        source_type="arxiv",
        target_star_id="KIC-11442793",
        extracted_parameters=extracted_parameters or {},
        disposition_notes=None,
        citation_string=citation_string,
        distillation_token_count=10,
    )


def test_build_distillation_dataset_returns_dataset():
    ds = build_distillation_dataset()
    assert isinstance(ds, Dataset)


def test_build_distillation_dataset_has_cases():
    ds = build_distillation_dataset()
    assert len(ds.cases) >= 1


def test_build_distillation_dataset_has_evaluators():
    ds = build_distillation_dataset()
    assert len(ds.evaluators) >= 1


def test_has_extracted_period_scores_one_when_period_present():
    from unittest.mock import MagicMock

    evaluator = HasExtractedPeriod()
    ctx = MagicMock()
    ctx.output = _make_record(extracted_parameters={"period_days": 14.64})
    score = evaluator.evaluate(ctx)
    assert score == 1.0


def test_has_extracted_period_scores_zero_when_period_absent():
    from unittest.mock import MagicMock

    evaluator = HasExtractedPeriod()
    ctx = MagicMock()
    ctx.output = _make_record(extracted_parameters={"stellar_radius_rsun": 1.2})
    score = evaluator.evaluate(ctx)
    assert score == 0.0


def test_has_extracted_period_scores_zero_for_empty_params():
    from unittest.mock import MagicMock

    evaluator = HasExtractedPeriod()
    ctx = MagicMock()
    ctx.output = _make_record(extracted_parameters={})
    score = evaluator.evaluate(ctx)
    assert score == 0.0


def test_has_citation_string_scores_one_when_non_empty():
    from unittest.mock import MagicMock

    evaluator = HasCitationString()
    ctx = MagicMock()
    ctx.output = _make_record(citation_string="[2301.12345] Transit period 14.64 days...")
    score = evaluator.evaluate(ctx)
    assert score == 1.0


def test_has_citation_string_scores_zero_for_empty():
    from unittest.mock import MagicMock

    evaluator = HasCitationString()
    ctx = MagicMock()
    # Use a plain mock for output to avoid DistilledLiteratureRecord's non-empty validator
    ctx.output = MagicMock()
    ctx.output.citation_string = "   "
    score = evaluator.evaluate(ctx)
    assert score == 0.0


def test_distillation_input_model():
    inp = DistillationInput(
        source_id="2301.99999",
        abstract="An exoplanet transit study.",
        target_star_id="KIC-11442793",
    )
    assert inp.source_id == "2301.99999"
    assert inp.target_star_id == "KIC-11442793"

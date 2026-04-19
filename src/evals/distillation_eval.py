"""Evaluation module for DistillationAgent output quality."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from src.schemas.literature import DistilledLiteratureRecord


class DistillationInput(BaseModel):
    """Input for a single distillation evaluation case."""

    source_id: str
    abstract: str
    target_star_id: str


@dataclass
class HasExtractedPeriod(Evaluator[DistillationInput, DistilledLiteratureRecord, None]):
    """Score 1.0 if the distillation extracted a period_days parameter, else 0.0."""

    def evaluate(
        self, ctx: EvaluatorContext[DistillationInput, DistilledLiteratureRecord, None]
    ) -> float:
        return 1.0 if "period_days" in ctx.output.extracted_parameters else 0.0


@dataclass
class HasCitationString(Evaluator[DistillationInput, DistilledLiteratureRecord, None]):
    """Score 1.0 if the distillation produced a non-empty citation string."""

    def evaluate(
        self, ctx: EvaluatorContext[DistillationInput, DistilledLiteratureRecord, None]
    ) -> float:
        return 1.0 if ctx.output.citation_string.strip() else 0.0


def build_distillation_dataset() -> Dataset[DistillationInput, DistilledLiteratureRecord, None]:
    """Build a sample evaluation dataset for DistillationAgent."""
    cases = [
        Case(
            name="period_extraction",
            inputs=DistillationInput(
                source_id="2301.12345",
                abstract=(
                    "We report the confirmed planet KIC-11442793b with an orbital "
                    "period of 14.64 days and a transit depth of 0.003."
                ),
                target_star_id="KIC-11442793",
            ),
        ),
        Case(
            name="false_positive",
            inputs=DistillationInput(
                source_id="2022AJ.001B",
                abstract=(
                    "Analysis reveals KIC-11442793 is an eclipsing binary system, "
                    "making the transit signal a false positive."
                ),
                target_star_id="KIC-11442793",
            ),
        ),
    ]
    return Dataset(
        name="distillation_quality",
        cases=cases,
        evaluators=[HasExtractedPeriod(), HasCitationString()],
    )

"""Evaluation module for full pipeline output quality."""

from __future__ import annotations

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import EqualsExpected

from src.schemas.benchmark import GoldenDataset


def build_pipeline_dataset(golden: GoldenDataset) -> Dataset:
    """Build an evaluation dataset from a GoldenDataset for full pipeline assessment.

    Args:
        golden: A GoldenDataset with ground-truth dispositions.

    Returns:
        Dataset where each case pairs a target_id input with expected ground-truth output.
    """
    cases = [
        Case(
            name=obj.target_id,
            inputs={"target_id": obj.target_id, "catalog": "KIC"},
            expected_output=obj.ground_truth,
        )
        for obj in golden.objects
    ]
    return Dataset(cases=cases, evaluators=[EqualsExpected()])

"""Benchmark schemas: BenchmarkResult, GoldenDataset, GoldenObject, ObjectResult, ObjectFailure."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class GoldenObject(BaseModel):
    """A single labelled candidate in the Golden Dataset."""

    target_id: str
    ground_truth: Literal["planet_candidate", "false_positive"]

    @field_validator("target_id")
    @classmethod
    def target_id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("target_id must not be empty")
        return v


class GoldenDataset(BaseModel):
    """The evaluation corpus."""

    dataset_version: str
    source_table: str
    objects: list[GoldenObject]

    @field_validator("objects")
    @classmethod
    def objects_min_40(cls, v: list[GoldenObject]) -> list[GoldenObject]:
        if len(v) < 40:
            raise ValueError("GoldenDataset must contain at least 40 objects")
        return v

    @field_validator("dataset_version")
    @classmethod
    def dataset_version_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("dataset_version must not be empty")
        return v


class ObjectResult(BaseModel):
    """Per-candidate benchmark result."""

    target_id: str
    ground_truth: Literal["planet_candidate", "false_positive"]
    prediction: Literal["planet_candidate", "false_positive", "inconclusive"]
    confidence: float | None = None


class ObjectFailure(BaseModel):
    """An object where the pipeline raised an error during benchmarking."""

    target_id: str
    error_type: str
    error_message: str


class BenchmarkResult(BaseModel):
    """Output of one Benchmark Runner execution."""

    run_id: str = None  # type: ignore[assignment]
    run_timestamp: datetime = None  # type: ignore[assignment]
    dataset_version: str
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float
    per_object_results: list[ObjectResult]
    failures: list[ObjectFailure] = []

    def model_post_init(self, __context: object) -> None:
        if self.run_id is None:
            object.__setattr__(self, "run_id", str(uuid.uuid4()))
        if self.run_timestamp is None:
            object.__setattr__(self, "run_timestamp", datetime.now(UTC))

    @field_validator("true_positives")
    @classmethod
    def tp_nonneg(cls, v: int) -> int:
        if v < 0:
            raise ValueError("true_positives must be >= 0")
        return v

    @field_validator("false_positives")
    @classmethod
    def fp_nonneg(cls, v: int) -> int:
        if v < 0:
            raise ValueError("false_positives must be >= 0")
        return v

    @field_validator("true_negatives")
    @classmethod
    def tn_nonneg(cls, v: int) -> int:
        if v < 0:
            raise ValueError("true_negatives must be >= 0")
        return v

    @field_validator("false_negatives")
    @classmethod
    def fn_nonneg(cls, v: int) -> int:
        if v < 0:
            raise ValueError("false_negatives must be >= 0")
        return v

    @field_validator("per_object_results")
    @classmethod
    def per_object_results_nonempty(cls, v: list[ObjectResult]) -> list[ObjectResult]:
        if not v:
            raise ValueError("per_object_results must not be empty")
        return v

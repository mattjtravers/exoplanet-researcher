"""Report schemas: VettingReport, AnomalyRecord, ConsensusConflictFlag, ReasoningStep, ValidatorResult."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from src.schemas.confidence import ConfidenceAssessment


class ConsensusConflictFlag(BaseModel):
    """Raised when Observer and Scholar diverge beyond the configured threshold."""

    observer_assessment: ConfidenceAssessment
    scholar_assessment: ConfidenceAssessment
    divergence: float
    threshold_used: float
    conflict_summary: str
    resolved: bool
    resolution_reasoning: str | None = None

    @field_validator("divergence")
    @classmethod
    def divergence_nonneg(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("divergence must be >= 0.0")
        return v

    @field_validator("threshold_used")
    @classmethod
    def threshold_positive(cls, v: float) -> float:
        if v <= 0.0:
            raise ValueError("threshold_used must be > 0.0")
        return v

    @field_validator("conflict_summary")
    @classmethod
    def conflict_summary_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("conflict_summary must not be empty")
        return v


class AnomalyRecord(BaseModel):
    """Documents an irregular signal detected in the light curve."""

    anomaly_type: Literal["aperiodicity", "asymmetric_transit", "flux_spike", "other"]
    data_quarter: int
    description: str
    sigma_deviation: float
    hypotheses_searched: list[str]
    literature_references: list[str] = []

    @field_validator("data_quarter")
    @classmethod
    def data_quarter_nonneg(cls, v: int) -> int:
        if v < 0:
            raise ValueError("data_quarter must be >= 0")
        return v

    @field_validator("sigma_deviation")
    @classmethod
    def sigma_nonneg(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("sigma_deviation must be >= 0.0")
        return v

    @field_validator("description")
    @classmethod
    def description_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description must not be empty")
        return v

    @field_validator("hypotheses_searched")
    @classmethod
    def hypotheses_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("hypotheses_searched must not be empty")
        return v


class ReasoningStep(BaseModel):
    """One entry in the Reasoning Trace."""

    step_number: int
    agent: str
    conclusion: str
    data_sources: list[str] = []
    tool_calls: list[str] = []

    @field_validator("step_number")
    @classmethod
    def step_number_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("step_number must be >= 1")
        return v

    @field_validator("agent")
    @classmethod
    def agent_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("agent must not be empty")
        return v

    @field_validator("conclusion")
    @classmethod
    def conclusion_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("conclusion must not be empty")
        return v


class ValidatorViolation(BaseModel):
    """A single failed physical constraint."""

    constraint: str
    observed_value: float
    allowed_range: tuple[float, float]
    description: str

    @field_validator("constraint")
    @classmethod
    def constraint_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("constraint must not be empty")
        return v

    @field_validator("description")
    @classmethod
    def description_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("description must not be empty")
        return v


class ValidatorResult(BaseModel):
    """Outcome of physical law validation."""

    passed: bool
    violations: list[ValidatorViolation] = []


class VettingReport(BaseModel):
    """The primary output document of the pipeline."""

    target_id: str
    disposition: Literal["planet_candidate", "false_positive", "inconclusive"]
    consensus_confidence: float | None = None
    conflict_flag: ConsensusConflictFlag | None = None
    anomaly_records: list[AnomalyRecord] = []
    reasoning_trace: list[ReasoningStep]
    validator_result: ValidatorResult
    lineage_map_path: str
    light_curve_chart_path: str
    interpretive_description: str
    created_at: datetime = None  # type: ignore[assignment]

    def model_post_init(self, __context: object) -> None:
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now(UTC))

    @model_validator(mode="after")
    def exactly_one_confidence_or_conflict(self) -> VettingReport:
        has_confidence = self.consensus_confidence is not None
        has_conflict = self.conflict_flag is not None
        if has_confidence == has_conflict:
            raise ValueError(
                "Exactly one of consensus_confidence or conflict_flag must be non-None"
            )
        return self

    @field_validator("target_id")
    @classmethod
    def target_id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("target_id must not be empty")
        return v

    @field_validator("reasoning_trace")
    @classmethod
    def reasoning_trace_nonempty(cls, v: list[ReasoningStep]) -> list[ReasoningStep]:
        if not v:
            raise ValueError("reasoning_trace must not be empty")
        return v

    @field_validator("lineage_map_path")
    @classmethod
    def lineage_map_path_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("lineage_map_path must not be empty")
        return v

    @field_validator("light_curve_chart_path")
    @classmethod
    def light_curve_chart_path_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("light_curve_chart_path must not be empty")
        return v

    @field_validator("interpretive_description")
    @classmethod
    def interpretive_description_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("interpretive_description must not be empty")
        return v

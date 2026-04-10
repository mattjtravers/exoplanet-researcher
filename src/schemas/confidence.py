"""ConfidenceAssessment schema — an agent's independent scoring of the candidate."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class ConfidenceAssessment(BaseModel):
    """An agent's independent scoring of the candidate's disposition."""

    agent: Literal["observer", "scholar"]
    score: float
    disposition: Literal["planet_candidate", "false_positive", "inconclusive"]
    primary_evidence: list[str]
    reasoning_summary: str

    @field_validator("score")
    @classmethod
    def score_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 100.0):
            raise ValueError("score must be between 0.0 and 100.0")
        return v

    @field_validator("primary_evidence")
    @classmethod
    def primary_evidence_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("primary_evidence must not be empty")
        return v

    @field_validator("reasoning_summary")
    @classmethod
    def reasoning_summary_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("reasoning_summary must not be empty")
        return v

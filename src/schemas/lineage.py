"""LineageEntry and LineageMap schemas for JSON-LD provenance tracking."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class LineageEntry(BaseModel):
    """A single provenance record linking one physical parameter to its origin."""

    parameter_name: str
    parameter_value: float | str
    tool_call_id: str
    source_id: str
    source_type: Literal["nasa_quarter", "arxiv", "ads", "candidate"]
    agent: str
    timestamp: datetime = None  # type: ignore[assignment]

    def model_post_init(self, __context: object) -> None:
        if self.timestamp is None:
            object.__setattr__(self, "timestamp", datetime.now(UTC))

    @field_validator("parameter_name")
    @classmethod
    def parameter_name_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("parameter_name must not be empty")
        return v

    @field_validator("tool_call_id")
    @classmethod
    def tool_call_id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("tool_call_id must not be empty")
        return v

    @field_validator("source_id")
    @classmethod
    def source_id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source_id must not be empty")
        return v

    @field_validator("agent")
    @classmethod
    def agent_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("agent must not be empty")
        return v


class ConfidenceLineageEntry(BaseModel):
    """Confidence score provenance for the lineage map."""

    agent: Literal["observer", "scholar"]
    score: float
    disposition: Literal["planet_candidate", "false_positive", "inconclusive"]
    primary_evidence: list[str]
    timestamp: datetime = None  # type: ignore[assignment]

    def model_post_init(self, __context: object) -> None:
        if self.timestamp is None:
            object.__setattr__(self, "timestamp", datetime.now(UTC))

    @field_validator("primary_evidence")
    @classmethod
    def primary_evidence_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("primary_evidence must not be empty")
        return v


class LineageMap(BaseModel):
    """The complete JSON-LD provenance document for one Vetting Report."""

    context: str = "https://xpi.science/lineage/v1"
    target_id: str
    entries: list[LineageEntry]
    confidence_entries: list[ConfidenceLineageEntry]
    created_at: datetime = None  # type: ignore[assignment]
    schema_version: str = "1.0.0"

    def model_post_init(self, __context: object) -> None:
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now(UTC))

    @field_validator("target_id")
    @classmethod
    def target_id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("target_id must not be empty")
        return v

    @field_validator("entries")
    @classmethod
    def entries_nonempty(cls, v: list[LineageEntry]) -> list[LineageEntry]:
        if not v:
            raise ValueError("entries must not be empty")
        return v

    @field_validator("confidence_entries")
    @classmethod
    def confidence_entries_nonempty(
        cls, v: list[ConfidenceLineageEntry]
    ) -> list[ConfidenceLineageEntry]:
        if not v:
            raise ValueError("confidence_entries must not be empty")
        return v

    def to_json_ld(self) -> dict:
        """Serialize to a JSON-LD compatible dict with @context key."""
        data = self.model_dump(mode="json")
        data["@context"] = data.pop("context")
        return data

"""DistilledLiteratureRecord schema — target-relevant extraction from one paper."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class DistilledLiteratureRecord(BaseModel):
    """Output of the Distillation Agent — target-relevant extraction from one paper."""

    source_id: str
    source_type: Literal["arxiv", "ads"]
    target_star_id: str
    extracted_parameters: dict[str, float | str] = {}
    disposition_notes: str | None = None
    citation_string: str
    distillation_token_count: int

    @field_validator("source_id")
    @classmethod
    def source_id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source_id must not be empty")
        return v

    @field_validator("target_star_id")
    @classmethod
    def target_star_id_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("target_star_id must not be empty")
        return v

    @field_validator("citation_string")
    @classmethod
    def citation_string_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("citation_string must not be empty")
        return v

    @field_validator("distillation_token_count")
    @classmethod
    def token_count_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("distillation_token_count must be > 0")
        return v

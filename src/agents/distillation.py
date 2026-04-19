"""Distillation Agent — compress retrieved papers to target-relevant content."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_ai import Agent

from src.agents.base import AgentBase
from src.schemas.config import AgentConfig
from src.schemas.literature import DistilledLiteratureRecord


class DistillationInput(BaseModel):
    """Input contract for the Distillation Agent."""

    raw_papers: list[tuple[str, str]]  # (source_id, full_text) pairs
    target_star_id: str
    agent_config: AgentConfig


class DistillationOutput(BaseModel):
    """Output contract for the Distillation Agent."""

    records: list[DistilledLiteratureRecord]
    total_tokens_consumed: int


class DistillationExtraction(BaseModel):
    """Typed LLM output for a single paper distillation."""

    extracted_parameters: dict[str, float | str] = {}
    disposition_notes: str | None = None
    citation_string: str


# ---------------------------------------------------------------------------
# PydanticAI Agent — lazy singleton
# ---------------------------------------------------------------------------

_distillation_agent: Agent | None = None


def _build_distillation_agent() -> Agent:
    spec_path = Path(__file__).parent.parent.parent / "config" / "agent_specs" / "distillation.yaml"
    spec = yaml.safe_load(spec_path.read_text())
    return Agent(
        model=spec["model"],
        output_type=DistillationExtraction,
        system_prompt=spec["system_prompt"],
        retries=spec.get("retries", 2),
    )


def _get_distillation_agent() -> Agent:
    global _distillation_agent
    if _distillation_agent is None:
        _distillation_agent = _build_distillation_agent()
    return _distillation_agent


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------


class DistillationAgent(AgentBase):
    """Compresses retrieved papers into target-relevant DistilledLiteratureRecord objects."""

    def __init__(self, config: AgentConfig) -> None:
        super().__init__("distillation", config)

    def run(
        self,
        raw_papers: list[tuple[str, str]],
        target_star_id: str,
    ) -> DistillationOutput:
        """Distil each paper into a DistilledLiteratureRecord.

        Args:
            raw_papers: List of (source_id, abstract_or_text) tuples.
            target_star_id: The star being vetted (for targeted extraction).

        Returns:
            DistillationOutput with one record per paper.
        """
        records: list[DistilledLiteratureRecord] = []
        total_tokens = 0

        for source_id, text in raw_papers:
            # Estimate tokens (rough: ~4 chars per token) for budget check
            estimated_tokens = max(1, len(text) // 4)
            self.check_token_budget(estimated_tokens)

            record = self._distil_paper(
                source_id=source_id,
                text=text,
                target_star_id=target_star_id,
                token_estimate=estimated_tokens,
            )
            records.append(record)
            self.consume_tokens(record.distillation_token_count)
            total_tokens += record.distillation_token_count

        return DistillationOutput(records=records, total_tokens_consumed=total_tokens)

    def _distil_paper(
        self,
        source_id: str,
        text: str,
        target_star_id: str,
        token_estimate: int,
    ) -> DistilledLiteratureRecord:
        """Extract target-relevant parameters from a paper.

        Uses PydanticAI Agent if ANTHROPIC_API_KEY is set; otherwise falls back
        to keyword-based extraction for testing.
        """
        source_type = "arxiv" if _looks_like_arxiv(source_id) else "ads"

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key and len(text) > 100:
            try:
                return self._llm_distil(
                    source_id=source_id,
                    source_type=source_type,
                    text=text,
                    target_star_id=target_star_id,
                )
            except Exception:
                pass  # Fall through to keyword extraction

        return _keyword_distil(
            source_id=source_id,
            source_type=source_type,
            text=text,
            target_star_id=target_star_id,
            token_estimate=token_estimate,
        )

    def _llm_distil(
        self,
        source_id: str,
        source_type: str,
        text: str,
        target_star_id: str,
    ) -> DistilledLiteratureRecord:
        """PydanticAI-based parameter extraction with typed output and retry."""
        from pydantic_ai import UsageLimits

        agent = _get_distillation_agent()
        remaining = self.config.token_budget - self._tokens_used
        prompt = f"Target star: {target_star_id}\nSource: {source_id}\n\nAbstract:\n{text[:2000]}"

        result = agent.run_sync(
            prompt,
            usage_limits=UsageLimits(total_tokens_limit=max(remaining, 500)),
        )
        extraction: DistillationExtraction = result.output
        actual_tokens = result.usage().total_tokens

        return DistilledLiteratureRecord(
            source_id=source_id,
            source_type=source_type,
            target_star_id=target_star_id,
            extracted_parameters=extraction.extracted_parameters,
            disposition_notes=extraction.disposition_notes,
            citation_string=extraction.citation_string or f"[{source_id}]",
            distillation_token_count=actual_tokens,
        )


def _looks_like_arxiv(source_id: str) -> bool:
    """Check if a source_id looks like an ArXiv ID."""
    return "." in source_id and source_id.replace(".", "").replace("-", "").isdigit()


def _keyword_distil(
    source_id: str,
    source_type: str,
    text: str,
    target_star_id: str,
    token_estimate: int,
) -> DistilledLiteratureRecord:
    """Simple keyword-based parameter extraction (fallback / testing)."""
    import re

    extracted: dict[str, float | str] = {}
    disposition_notes = None

    period_match = re.search(r"period[:\s]+(\d+\.?\d*)\s*days?", text, re.IGNORECASE)
    if period_match:
        extracted["period_days"] = float(period_match.group(1))

    text_lower = text.lower()
    if "confirmed" in text_lower and "planet" in text_lower:
        disposition_notes = "Paper confirms planetary nature."
    elif "false positive" in text_lower or "eclipsing binary" in text_lower:
        disposition_notes = "Paper suggests false positive (eclipsing binary)."

    citation_string = f"[{source_id}] {text[:80].strip()}..."

    return DistilledLiteratureRecord(
        source_id=source_id,
        source_type=source_type,
        target_star_id=target_star_id,
        extracted_parameters=extracted,
        disposition_notes=disposition_notes,
        citation_string=citation_string,
        distillation_token_count=max(1, token_estimate),
    )

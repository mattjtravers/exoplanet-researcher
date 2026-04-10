"""Distillation Agent — compress retrieved papers to target-relevant content."""

from __future__ import annotations

import os

from pydantic import BaseModel

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
            # Estimate tokens (rough: ~4 chars per token)
            estimated_tokens = max(1, len(text) // 4)
            self.check_token_budget(estimated_tokens)

            record = self._distil_paper(
                source_id=source_id,
                text=text,
                target_star_id=target_star_id,
                token_estimate=estimated_tokens,
            )
            records.append(record)
            self.consume_tokens(estimated_tokens)
            total_tokens += estimated_tokens

        return DistillationOutput(records=records, total_tokens_consumed=total_tokens)

    def _distil_paper(
        self,
        source_id: str,
        text: str,
        target_star_id: str,
        token_estimate: int,
    ) -> DistilledLiteratureRecord:
        """Extract target-relevant parameters from a paper.

        This uses an LLM call if ANTHROPIC_API_KEY is set; otherwise falls back
        to a keyword-based extraction for testing.
        """
        source_type = "arxiv" if _looks_like_arxiv(source_id) else "ads"

        # Try LLM-based extraction if API key present
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key and len(text) > 100:
            try:
                return self._llm_distil(
                    source_id=source_id,
                    source_type=source_type,
                    text=text,
                    target_star_id=target_star_id,
                    token_estimate=token_estimate,
                )
            except Exception:
                pass  # Fall through to keyword extraction

        # Keyword-based fallback for testing / offline use
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
        token_estimate: int,
    ) -> DistilledLiteratureRecord:
        """LLM-based parameter extraction."""
        import anthropic

        client = anthropic.Anthropic()
        prompt = (
            f"Extract parameters for star {target_star_id} from this paper abstract. "
            f"Return a JSON object with keys: extracted_parameters (dict), "
            f"disposition_notes (string or null), citation_string (full verbatim citation).\n\n"
            f"Abstract:\n{text[:2000]}"
        )
        response = client.messages.create(
            model=os.environ.get("XPI_MODEL_ID", "claude-haiku-4-5-20251001"),
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        content = response.content[0].text
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = {}

        return DistilledLiteratureRecord(
            source_id=source_id,
            source_type=source_type,
            target_star_id=target_star_id,
            extracted_parameters=data.get("extracted_parameters", {}),
            disposition_notes=data.get("disposition_notes"),
            citation_string=data.get("citation_string") or f"[{source_id}]",
            distillation_token_count=token_estimate,
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

    # Look for period mentions
    period_match = re.search(r"period[:\s]+(\d+\.?\d*)\s*days?", text, re.IGNORECASE)
    if period_match:
        extracted["period_days"] = float(period_match.group(1))

    # Look for disposition keywords
    text_lower = text.lower()
    if "confirmed" in text_lower and "planet" in text_lower:
        disposition_notes = "Paper confirms planetary nature."
    elif "false positive" in text_lower or "eclipsing binary" in text_lower:
        disposition_notes = "Paper suggests false positive (eclipsing binary)."

    # Build a minimal citation string
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

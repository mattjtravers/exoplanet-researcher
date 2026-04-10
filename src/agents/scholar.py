"""Scholar agent — agentic iterative literature retrieval and confidence scoring."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from src.agents.base import AgentBase
from src.schemas.candidate import CandidateTarget
from src.schemas.confidence import ConfidenceAssessment
from src.schemas.config import AgentConfig
from src.schemas.lineage import LineageEntry
from src.schemas.literature import DistilledLiteratureRecord


class ScholarInput(BaseModel):
    """Input contract for the Scholar agent."""

    candidate: CandidateTarget
    anomaly_directives: list[str]
    agent_config: AgentConfig


class ScholarOutput(BaseModel):
    """Output contract for the Scholar agent."""

    confidence: ConfidenceAssessment
    distilled_records: list[DistilledLiteratureRecord]
    queries_issued: list[str]
    lineage_partial: list[LineageEntry]


class ScholarAgent(AgentBase):
    """Agentic iterative literature retrieval and confidence scoring."""

    def __init__(self, config: AgentConfig) -> None:
        super().__init__("scholar", config)

    def run(
        self,
        candidate: CandidateTarget,
        anomaly_directives: list[str] | None = None,
    ) -> ScholarOutput:
        """Execute the Scholar pipeline for a given candidate.

        Args:
            candidate: The candidate being vetted.
            anomaly_directives: Anomaly type hints from the Observer.

        Returns:
            ScholarOutput with confidence, distilled records, and lineage entries.
        """
        from src.agents.distillation import DistillationAgent
        from src.tools.rag_tools import iterative_search

        anomaly_hints = anomaly_directives or []
        max_iters = self.config.max_iterations or 3

        # Run iterative search
        raw_results, queries_issued = iterative_search(
            candidate=candidate,
            anomaly_hints=anomaly_hints,
            max_iterations=max_iters,
        )

        # If anomaly directives were given, ensure at least one query contains them
        if anomaly_hints:
            has_directive_query = any(
                any(hint.replace("_", " ") in q for hint in anomaly_hints)
                for q in queries_issued
            )
            if not has_directive_query and raw_results == []:
                # Add a directive-specific query
                directive_query = f"{candidate.target_id} {' '.join(anomaly_hints).replace('_', ' ')}"
                queries_issued.append(directive_query)
                from src.tools.rag_tools import search_arxiv
                try:
                    extra = search_arxiv(directive_query, max_results=3)
                    raw_results.extend(extra)
                except Exception:
                    pass

        # Distil the raw results
        distil_config = AgentConfig(token_budget=self.config.token_budget // 2)
        distillation = DistillationAgent(config=distil_config)

        if raw_results:
            distil_out = distillation.run(
                raw_papers=raw_results[:10],  # limit to 10 papers
                target_star_id=candidate.target_id,
            )
            distilled_records = distil_out.records
        else:
            distilled_records = []

        # Build lineage entries for cited parameters
        lineage_entries: list[LineageEntry] = []
        for record in distilled_records:
            for param_name, param_value in record.extracted_parameters.items():
                lineage_entries.append(
                    LineageEntry(
                        parameter_name=param_name,
                        parameter_value=param_value if isinstance(param_value, (int, float)) else str(param_value),
                        tool_call_id=str(uuid.uuid4()),
                        source_id=record.source_id,
                        source_type=record.source_type,
                        agent="scholar",
                    )
                )

        # Score confidence from literature
        confidence = _score_from_literature(
            candidate=candidate,
            distilled_records=distilled_records,
            queries_issued=queries_issued,
        )

        return ScholarOutput(
            confidence=confidence,
            distilled_records=distilled_records,
            queries_issued=queries_issued,
            lineage_partial=lineage_entries,
        )


def _score_from_literature(
    candidate: CandidateTarget,
    distilled_records: list[DistilledLiteratureRecord],
    queries_issued: list[str],
) -> ConfidenceAssessment:
    """Derive a confidence score from distilled literature records."""
    if not distilled_records:
        return ConfidenceAssessment(
            agent="scholar",
            score=20.0,
            disposition="inconclusive",
            primary_evidence=[candidate.target_id],
            reasoning_summary=(
                f"No literature found after {len(queries_issued)} search iterations. "
                "Confidence is low; disposition inconclusive."
            ),
        )

    planet_signals = 0
    fp_signals = 0
    evidence_ids: list[str] = []

    for rec in distilled_records:
        evidence_ids.append(rec.source_id)
        notes = (rec.disposition_notes or "").lower()
        if "confirm" in notes or "planet" in notes:
            planet_signals += 1
        elif "false positive" in notes or "eclipsing binary" in notes:
            fp_signals += 1

    total_signals = planet_signals + fp_signals
    if total_signals == 0:
        score = 45.0
        disposition = "inconclusive"
        reasoning = (
            f"Found {len(distilled_records)} papers but no clear disposition signals. "
            "Confidence is borderline."
        )
    elif planet_signals > fp_signals:
        score = 55.0 + min(35.0, planet_signals * 10.0)
        disposition = "planet_candidate"
        reasoning = (
            f"{planet_signals}/{total_signals} papers support planetary nature. "
            f"Confidence score: {score:.0f}%."
        )
    else:
        score = 55.0 + min(35.0, fp_signals * 10.0)
        disposition = "false_positive"
        reasoning = (
            f"{fp_signals}/{total_signals} papers suggest false positive. "
            f"Confidence score: {score:.0f}%."
        )

    return ConfidenceAssessment(
        agent="scholar",
        score=min(score, 95.0),
        disposition=disposition,
        primary_evidence=evidence_ids[:5] or [candidate.target_id],
        reasoning_summary=reasoning,
    )

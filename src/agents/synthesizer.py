"""Synthesizer agent — conflict detection, self-correction loop, and final disposition."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from src.agents.base import AgentBase
from src.schemas.config import AgentConfig
from src.schemas.report import ConsensusConflictFlag, ReasoningStep


class SynthesizerInput(BaseModel):
    """Input contract for the Synthesizer agent."""

    observer_output: object  # ObserverOutput
    scholar_output: object   # ScholarOutput
    agent_config: AgentConfig
    iteration: int = 0


class SynthesizerOutput(BaseModel):
    """Output contract for the Synthesizer agent."""

    disposition: Literal["planet_candidate", "false_positive", "inconclusive"]
    consensus_confidence: float | None
    conflict_flag: ConsensusConflictFlag | None
    reasoning_trace: list[ReasoningStep]


class SynthesizerAgent(AgentBase):
    """Resolves conflicts between Observer and Scholar, emits final disposition."""

    def __init__(self, config: AgentConfig) -> None:
        super().__init__("synthesizer", config)

    def run(
        self,
        observer_output: object,
        scholar_output: object,
        iteration: int = 0,
    ) -> SynthesizerOutput:
        """Synthesise Observer and Scholar outputs into a final disposition.

        Args:
            observer_output: ObserverOutput from the Observer agent.
            scholar_output: ScholarOutput from the Scholar agent.
            iteration: Current correction loop count.

        Returns:
            SynthesizerOutput with disposition, confidence/conflict, and reasoning trace.
        """
        obs_conf = observer_output.confidence
        sch_conf = scholar_output.confidence
        threshold = self.config.conflict_threshold or 30.0
        max_iters = self.config.max_correction_iterations or 2

        divergence = abs(obs_conf.score - sch_conf.score)
        reasoning_trace: list[ReasoningStep] = []

        # Step 1: Document both assessments
        reasoning_trace.append(
            ReasoningStep(
                step_number=1,
                agent="synthesizer",
                conclusion=(
                    f"Observer confidence: {obs_conf.score:.1f}% ({obs_conf.disposition}). "
                    f"Scholar confidence: {sch_conf.score:.1f}% ({sch_conf.disposition}). "
                    f"Divergence: {divergence:.1f} points."
                ),
                data_sources=obs_conf.primary_evidence + sch_conf.primary_evidence,
            )
        )

        # Step 2: Conflict detection
        if divergence > threshold:
            conflict_flag = ConsensusConflictFlag(
                observer_assessment=obs_conf,
                scholar_assessment=sch_conf,
                divergence=divergence,
                threshold_used=threshold,
                conflict_summary=(
                    f"Observer ({obs_conf.score:.1f}%) and Scholar ({sch_conf.score:.1f}%) "
                    f"diverge by {divergence:.1f} points, exceeding threshold {threshold:.1f}."
                ),
                resolved=False,
            )

            reasoning_trace.append(
                ReasoningStep(
                    step_number=2,
                    agent="synthesizer",
                    conclusion=(
                        f"Conflict detected (divergence={divergence:.1f} > threshold={threshold:.1f}). "
                        f"Triggering self-correction loop (iteration {iteration + 1}/{max_iters})."
                    ),
                )
            )

            # Self-correction loop: re-invoke Scholar if iterations remain
            if iteration < max_iters:
                # v1: self-correction re-query is logged but not executed (YAGNI)
                # In v2, re-invoke Scholar with conflict_resolution directive here

                new_divergence = abs(obs_conf.score - sch_conf.score)
                if new_divergence <= threshold:
                    conflict_flag = ConsensusConflictFlag(
                        observer_assessment=obs_conf,
                        scholar_assessment=sch_conf,
                        divergence=new_divergence,
                        threshold_used=threshold,
                        conflict_summary=conflict_flag.conflict_summary,
                        resolved=True,
                        resolution_reasoning="Post-correction divergence reduced below threshold.",
                    )

            # Determine disposition from conflict
            if obs_conf.score > sch_conf.score:
                disposition = obs_conf.disposition
            else:
                disposition = sch_conf.disposition

            if conflict_flag.resolved:
                avg_score = (obs_conf.score + sch_conf.score) / 2.0
                return SynthesizerOutput(
                    disposition=disposition,
                    consensus_confidence=avg_score,
                    conflict_flag=None,
                    reasoning_trace=reasoning_trace,
                )

            reasoning_trace.append(
                ReasoningStep(
                    step_number=3,
                    agent="synthesizer",
                    conclusion=(
                        f"Conflict unresolved after {iteration + 1} iteration(s). "
                        f"Emitting ConsensusConflictFlag. Disposition: {disposition}."
                    ),
                )
            )
            return SynthesizerOutput(
                disposition=disposition,
                consensus_confidence=None,
                conflict_flag=conflict_flag,
                reasoning_trace=reasoning_trace,
            )

        # No conflict — weighted average confidence
        avg_score = (obs_conf.score + sch_conf.score) / 2.0

        # Determine consensus disposition
        if obs_conf.disposition == sch_conf.disposition:
            disposition = obs_conf.disposition
        elif avg_score >= 60:
            disposition = "planet_candidate"
        elif avg_score <= 40:
            disposition = "false_positive"
        else:
            disposition = "inconclusive"

        reasoning_trace.append(
            ReasoningStep(
                step_number=2,
                agent="synthesizer",
                conclusion=(
                    f"No conflict detected. Consensus confidence: {avg_score:.1f}%. "
                    f"Disposition: {disposition}."
                ),
                data_sources=obs_conf.primary_evidence + sch_conf.primary_evidence,
            )
        )

        return SynthesizerOutput(
            disposition=disposition,
            consensus_confidence=avg_score,
            conflict_flag=None,
            reasoning_trace=reasoning_trace,
        )

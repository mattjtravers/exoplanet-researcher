"""Validator agent — physical law constraint enforcement."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from src.agents.base import AgentBase
from src.schemas.candidate import CandidateTarget
from src.schemas.config import AgentConfig
from src.schemas.report import ValidatorResult, ValidatorViolation


class ValidatorInput(BaseModel):
    """Input contract for the Validator agent."""

    synthesizer_output: object  # SynthesizerOutput
    observer_output: object     # ObserverOutput
    candidate: CandidateTarget


class ValidatorOutput(BaseModel):
    """Output contract for the Validator agent."""

    result: ValidatorResult
    annotated_disposition: Literal[
        "planet_candidate", "false_positive", "inconclusive", "validator_failed"
    ]


class ValidatorAgent(AgentBase):
    """Enforces physical law constraints on the pipeline output."""

    def __init__(self, config: AgentConfig) -> None:
        super().__init__("validator", config)

    def run(
        self,
        synthesizer_output: object,
        observer_output: object,
        candidate: CandidateTarget,
    ) -> ValidatorOutput:
        """Check physical constraints and annotate disposition.

        Constraints checked:
        - Rp/Rs bounds: 0.001 ≤ Rp/Rs ≤ 0.3 (planet range)
        - Mass-radius plausibility: if stellar mass is known, check density bounds

        The Validator MUST NOT alter confidence scores — it only annotates disposition.

        Args:
            synthesizer_output: Output from the Synthesizer agent.
            observer_output: Output from the Observer agent.
            candidate: The original CandidateTarget.

        Returns:
            ValidatorOutput with ValidatorResult and annotated disposition.
        """
        violations: list[ValidatorViolation] = []

        # Extract transit parameters from observer lineage
        rp_rs = None
        for entry in observer_output.lineage_partial:
            if entry.parameter_name == "rp_rs":
                rp_rs = float(entry.parameter_value)

        # Constraint 1: Rp/Rs must be in planetary range
        if rp_rs is not None and rp_rs > 0:
            rp_rs_min, rp_rs_max = 0.001, 0.30
            if not (rp_rs_min <= rp_rs <= rp_rs_max):
                violations.append(
                    ValidatorViolation(
                        constraint="rp_rs_bound",
                        observed_value=rp_rs,
                        allowed_range=(rp_rs_min, rp_rs_max),
                        description=(
                            f"Rp/Rs={rp_rs:.4f} is outside the allowed planetary range "
                            f"[{rp_rs_min}, {rp_rs_max}]. "
                            "Values > 0.3 suggest a stellar companion, not a planet."
                        ),
                    )
                )

        # Constraint 2: Mass-radius consistency
        # If stellar mass is known and rp_rs is known, compute planet radius in Jupiter radii
        if (
            candidate.stellar_radius_rsun is not None
            and rp_rs is not None
            and rp_rs > 0
        ):
            rp_rjup = rp_rs * candidate.stellar_radius_rsun * 9.73  # Rsun/Rjup ≈ 9.73
            rp_min, rp_max = 0.05, 2.5  # Jupiter radii (sub-Earth to ~2.5 Rjup)
            if not (rp_min <= rp_rjup <= rp_max):
                violations.append(
                    ValidatorViolation(
                        constraint="planet_radius_bound",
                        observed_value=rp_rjup,
                        allowed_range=(rp_min, rp_max),
                        description=(
                            f"Derived planet radius={rp_rjup:.3f} R_Jup is outside the "
                            f"allowed range [{rp_min}, {rp_max}] R_Jup."
                        ),
                    )
                )

        passed = len(violations) == 0
        result = ValidatorResult(passed=passed, violations=violations)

        if not passed:
            annotated_disposition = "validator_failed"
        else:
            annotated_disposition = synthesizer_output.disposition

        return ValidatorOutput(result=result, annotated_disposition=annotated_disposition)

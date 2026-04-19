"""LangGraph DAG definition, PipelineState, and CLI entry point."""

from __future__ import annotations

import argparse
import sys
from typing import TypedDict

from src.schemas.candidate import CandidateTarget
from src.schemas.config import AgentConfig, load_agent_configs

# --- Agent I/O schemas (imported here for use in state and node functions) ---
# These are forward-referenced to avoid circular imports during schema-only phases.
# Each will be populated as agents are implemented.

class PipelineState(TypedDict, total=False):
    """LangGraph pipeline state — all fields are PydanticAI model instances or None."""

    candidate: CandidateTarget
    config: dict  # keyed by agent name -> AgentConfig
    observer_output: object | None  # ObserverOutput | None
    scholar_output: object | None   # ScholarOutput | None
    distillation_output: object | None  # DistillationOutput | None
    synthesizer_output: object | None   # SynthesizerOutput | None
    validator_output: object | None     # ValidatorOutput | None
    lineage_map: object | None          # LineageMap | None
    vetting_report: object | None       # VettingReport | None
    error: str | None


def _build_initial_state(candidate: CandidateTarget, configs: dict[str, AgentConfig]) -> PipelineState:
    return PipelineState(
        candidate=candidate,
        config=configs,
        observer_output=None,
        scholar_output=None,
        distillation_output=None,
        synthesizer_output=None,
        validator_output=None,
        lineage_map=None,
        vetting_report=None,
        error=None,
    )


def run_pipeline(target_id: str, catalog: str) -> PipelineState:
    """Run the full XPI vetting pipeline for a single candidate.

    Args:
        target_id: The candidate identifier (e.g. "KIC-11442793").
        catalog: The source catalogue ("KIC", "TIC", or "TOI").

    Returns:
        Final PipelineState after all nodes have executed.
    """
    from src.agents.observer import ObserverAgent
    from src.agents.scholar import ScholarAgent
    from src.agents.synthesizer import SynthesizerAgent
    from src.agents.validator import ValidatorAgent
    from src.tools.lineage_mapper import finalise_lineage_map
    from src.tools.report_generator import generate_report

    configs = load_agent_configs()

    # Build initial candidate (stellar properties fetched by Observer via MCP)
    candidate = CandidateTarget(
        target_id=target_id,
        catalog=catalog,  # type: ignore[arg-type]
        available_quarters=list(range(1, 18)),  # default; Observer will refine
    )

    state = _build_initial_state(candidate, configs)

    # --- Node: Observer ---
    observer = ObserverAgent(config=configs.get("observer", configs.get("observer")))
    state["observer_output"] = observer.run(candidate=candidate)

    # --- Node: Scholar (parallel with Observer, but requires candidate) ---
    anomaly_directives: list[str] = []
    obs_out = state["observer_output"]
    if obs_out and obs_out.anomaly_records:
        anomaly_directives = [ar.anomaly_type for ar in obs_out.anomaly_records]

    scholar = ScholarAgent(config=configs.get("scholar", configs.get("scholar")))
    state["scholar_output"] = scholar.run(
        candidate=candidate,
        anomaly_directives=anomaly_directives,
    )

    # --- Node: Distillation (embedded in Scholar output) ---
    # Already processed inside ScholarAgent; distillation_output mirrors scholar records
    state["distillation_output"] = state["scholar_output"]

    # --- Node: Synthesizer ---
    synthesizer = SynthesizerAgent(config=configs.get("synthesizer", configs.get("synthesizer")))
    state["synthesizer_output"] = synthesizer.run(
        observer_output=state["observer_output"],
        scholar_output=state["scholar_output"],
    )

    # --- Node: Validator ---
    validator = ValidatorAgent(config=configs.get("validator", configs.get("validator")))
    state["validator_output"] = validator.run(
        synthesizer_output=state["synthesizer_output"],
        observer_output=state["observer_output"],
        candidate=candidate,
    )

    # --- Node: Lineage Map Finaliser ---
    state["lineage_map"] = finalise_lineage_map(
        target_id=target_id,
        observer_output=state["observer_output"],
        scholar_output=state["scholar_output"],
        synthesizer_output=state["synthesizer_output"],
    )

    # --- Node: Report Generator ---
    report = generate_report(
        target_id=target_id,
        synthesizer_output=state["synthesizer_output"],
        validator_output=state["validator_output"],
        observer_output=state["observer_output"],
        lineage_map=state["lineage_map"],
    )
    state["vetting_report"] = report

    return state


def main() -> None:
    parser = argparse.ArgumentParser(
        description="XPI — Independent Agentic Exoplanet Vetting Pipeline"
    )
    parser.add_argument("--target-id", required=True, help="Candidate identifier (e.g. KIC-11442793)")
    parser.add_argument(
        "--catalog", required=True, choices=["KIC", "TIC", "TOI"], help="Source catalogue"
    )
    args = parser.parse_args()

    print(f"[XPI] Vetting {args.target_id} (catalog={args.catalog}) ...")
    state = run_pipeline(target_id=args.target_id, catalog=args.catalog)

    if state.get("error"):
        print(f"[XPI] ERROR: {state['error']}", file=sys.stderr)
        sys.exit(1)

    report = state.get("vetting_report")
    if report:
        print(f"[XPI] Disposition: {report.disposition}")
        print(f"[XPI] Report written to: outputs/{args.target_id}/report.md")
    else:
        print("[XPI] Pipeline completed but no report was generated.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Observer agent — quantitative light curve analysis and anomaly detection."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from src.agents.base import AgentBase
from src.errors import ArchiveConnectionError, ArchiveNotFoundError
from src.schemas.candidate import CandidateTarget
from src.schemas.confidence import ConfidenceAssessment
from src.schemas.config import AgentConfig
from src.schemas.lineage import LineageEntry
from src.schemas.report import AnomalyRecord


class ObserverOutput(BaseModel):
    """Output contract for the Observer agent."""

    confidence: ConfidenceAssessment
    lineage_partial: list[LineageEntry]
    anomaly_records: list[AnomalyRecord]


class ObserverAgent(AgentBase):
    """Quantitative light curve analysis agent."""

    def __init__(self, config: AgentConfig) -> None:
        super().__init__("observer", config)

    def run(self, candidate: CandidateTarget) -> ObserverOutput:
        """Execute the Observer pipeline for a given candidate.

        Steps:
        1. Retrieve light curve via MCP get_light_curve
        2. Fit transit parameters (period, depth, duration, Rp/Rs)
        3. Detect anomalies
        4. Build lineage entries
        5. Emit ConfidenceAssessment

        Args:
            candidate: The exoplanet candidate to vet.

        Returns:
            ObserverOutput with confidence, lineage partial, and anomaly records.
        """
        from src.mcp.server import call_tool
        from src.tools.anomaly_detector import detect_anomaly
        from src.tools.transit_fitter import fit_transit

        lineage_entries: list[LineageEntry] = []
        anomaly_records: list[AnomalyRecord] = []
        primary_evidence: list[str] = []
        transit_params: dict = {}

        # Try available quarters
        quarters_to_try = candidate.available_quarters[:3]  # try first 3

        for quarter in quarters_to_try:
            try:
                lc_data = call_tool(
                    "get_light_curve",
                    target_id=candidate.target_id,
                    quarter=quarter,
                    mission="Kepler" if candidate.catalog == "KIC" else "TESS",
                )
                break
            except (ArchiveNotFoundError, ArchiveConnectionError):
                lc_data = None

        if lc_data is None:
            # No light curve data available — return low-confidence inconclusive
            return ObserverOutput(
                confidence=ConfidenceAssessment(
                    agent="observer",
                    score=10.0,
                    disposition="inconclusive",
                    primary_evidence=[candidate.target_id],
                    reasoning_summary="No light curve data available from archive.",
                ),
                lineage_partial=[],
                anomaly_records=[],
            )

        # Fit transit
        quarter_id = f"Q{lc_data['quarter']}"
        primary_evidence.append(quarter_id)

        transit_params = fit_transit(
            time=lc_data["time"],
            flux=lc_data["flux"],
            flux_err=lc_data["flux_err"],
            target_id=candidate.target_id,
        )

        tool_call_id = transit_params["tool_call_id"]

        # Build lineage entries for computed parameters
        for param_name in ("period_days", "depth", "duration_hours", "rp_rs"):
            val = transit_params.get(param_name)
            if val is not None:
                lineage_entries.append(
                    LineageEntry(
                        parameter_name=param_name,
                        parameter_value=val,
                        tool_call_id=tool_call_id,
                        source_id=quarter_id,
                        source_type="nasa_quarter",
                        agent="observer",
                    )
                )

        # Add stellar radius if available
        if candidate.stellar_radius_rsun is not None:
            lineage_entries.append(
                LineageEntry(
                    parameter_name="stellar_radius_rsun",
                    parameter_value=candidate.stellar_radius_rsun,
                    tool_call_id=str(uuid.uuid4()),
                    source_id=candidate.target_id,
                    source_type="candidate",
                    agent="observer",
                )
            )

        # Detect anomalies
        sigma_thresh = self.config.anomaly_sigma_threshold or 2.0
        anomaly = detect_anomaly(
            time=lc_data["time"],
            flux=lc_data["flux"],
            flux_err=lc_data["flux_err"],
            quarter=lc_data["quarter"],
            sigma_threshold=sigma_thresh,
            transit_period=transit_params.get("period_days"),
            transit_duration=transit_params.get("duration_hours", 4.0) / 24.0,
        )
        if anomaly is not None:
            anomaly_records.append(anomaly)

        # Score confidence from transit parameters
        depth = transit_params.get("depth", 0.0)
        rp_rs = transit_params.get("rp_rs", 0.0)
        period = transit_params.get("period_days", 0.0)

        # Heuristic scoring: deeper, regular transits with reasonable Rp/Rs → higher confidence
        score = _compute_observer_score(depth=depth, rp_rs=rp_rs, period=period)
        disposition = "planet_candidate" if score >= 50 else "inconclusive"

        reasoning = (
            f"Transit fit: period={period:.3f}d, depth={depth:.5f}, "
            f"Rp/Rs={rp_rs:.4f}. "
            f"{'Anomalies detected.' if anomaly_records else 'No anomalies detected.'}"
        )

        confidence = ConfidenceAssessment(
            agent="observer",
            score=score,
            disposition=disposition,
            primary_evidence=primary_evidence,
            reasoning_summary=reasoning,
        )

        return ObserverOutput(
            confidence=confidence,
            lineage_partial=lineage_entries,
            anomaly_records=anomaly_records,
        )


def _compute_observer_score(depth: float, rp_rs: float, period: float) -> float:
    """Heuristic confidence score from transit parameters."""
    score = 30.0  # base

    # Depth: reasonable planet depths are 0.0001 to 0.05
    if 0.0001 < depth < 0.05:
        score += 25.0
    elif depth > 0:
        score += 10.0

    # Rp/Rs: realistic range 0.01 to 0.25
    if 0.01 < rp_rs < 0.25:
        score += 20.0
    elif rp_rs > 0:
        score += 5.0

    # Period: detected period is meaningful
    if 0.5 < period < 100.0:
        score += 10.0

    return min(score, 95.0)

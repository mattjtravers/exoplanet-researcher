"""AgentConfig schema and YAML loader."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator


class AgentConfig(BaseModel):
    """Per-agent runtime configuration loaded from config/agents.yaml."""

    token_budget: int
    max_iterations: int | None = None
    conflict_threshold: float | None = None
    anomaly_sigma_threshold: float | None = None
    max_correction_iterations: int | None = None

    @field_validator("token_budget")
    @classmethod
    def token_budget_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("token_budget must be > 0")
        return v

    @field_validator("max_iterations")
    @classmethod
    def max_iterations_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("max_iterations must be > 0")
        return v

    @field_validator("conflict_threshold")
    @classmethod
    def conflict_threshold_range(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 100.0):
            raise ValueError("conflict_threshold must be between 0 and 100")
        return v

    @field_validator("anomaly_sigma_threshold")
    @classmethod
    def anomaly_sigma_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0.0:
            raise ValueError("anomaly_sigma_threshold must be > 0")
        return v

    @field_validator("max_correction_iterations")
    @classmethod
    def max_correction_iterations_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("max_correction_iterations must be > 0")
        return v


def load_agent_configs(config_path: str | Path | None = None) -> dict[str, AgentConfig]:
    """Load AgentConfig instances for all agents from the YAML config file.

    Args:
        config_path: Path to agents.yaml. Defaults to config/agents.yaml at repo root.

    Returns:
        Dict mapping agent name -> AgentConfig.
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "agents.yaml"
    config_path = Path(config_path)
    with config_path.open() as f:
        raw = yaml.safe_load(f)
    agents_raw = raw.get("agents", {})
    return {name: AgentConfig(**fields) for name, fields in agents_raw.items()}

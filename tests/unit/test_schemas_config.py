"""T010 — Unit tests for AgentConfig schema."""

import pytest
from pydantic import ValidationError

from src.schemas.config import AgentConfig, load_agent_configs


def _valid_config(**overrides) -> dict:
    base = {"token_budget": 8000}
    base.update(overrides)
    return base


def test_valid_agent_config():
    c = AgentConfig(**_valid_config())
    assert c.token_budget == 8000


def test_missing_token_budget_raises():
    with pytest.raises(ValidationError):
        AgentConfig()


def test_zero_token_budget_raises():
    with pytest.raises(ValidationError):
        AgentConfig(token_budget=0)


def test_negative_token_budget_raises():
    with pytest.raises(ValidationError):
        AgentConfig(token_budget=-100)


def test_max_iterations_positive():
    c = AgentConfig(**_valid_config(max_iterations=3))
    assert c.max_iterations == 3


def test_zero_max_iterations_raises():
    with pytest.raises(ValidationError):
        AgentConfig(**_valid_config(max_iterations=0))


def test_conflict_threshold_accepted():
    c = AgentConfig(**_valid_config(conflict_threshold=30.0))
    assert c.conflict_threshold == 30.0


def test_conflict_threshold_out_of_range_raises():
    with pytest.raises(ValidationError):
        AgentConfig(**_valid_config(conflict_threshold=101.0))


def test_anomaly_sigma_zero_raises():
    with pytest.raises(ValidationError):
        AgentConfig(**_valid_config(anomaly_sigma_threshold=0.0))


def test_anomaly_sigma_positive_accepted():
    c = AgentConfig(**_valid_config(anomaly_sigma_threshold=2.0))
    assert c.anomaly_sigma_threshold == 2.0


def test_load_agent_configs_from_yaml():
    configs = load_agent_configs()
    assert "observer" in configs
    assert "scholar" in configs
    assert configs["observer"].token_budget > 0
    assert configs["scholar"].max_iterations is not None

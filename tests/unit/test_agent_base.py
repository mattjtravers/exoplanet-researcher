"""T062 — Unit tests for AgentBase contract enforcement."""

import pytest
from pydantic import BaseModel

from src.agents.base import AgentBase
from src.errors import TokenBudgetExceededError, ValidationContractError
from src.schemas.config import AgentConfig


class SampleSchema(BaseModel):
    name: str
    value: float


def _make_agent(budget: int = 1000) -> AgentBase:
    return AgentBase("test_agent", AgentConfig(token_budget=budget))


def test_check_token_budget_raises_when_exceeded():
    agent = _make_agent(budget=500)
    with pytest.raises(TokenBudgetExceededError) as exc_info:
        agent.check_token_budget(501)
    assert exc_info.value.agent == "test_agent"
    assert exc_info.value.budget == 500


def test_check_token_budget_passes_when_within():
    agent = _make_agent(budget=1000)
    agent.check_token_budget(999)  # should not raise


def test_check_token_budget_raises_after_consumption():
    agent = _make_agent(budget=1000)
    agent.consume_tokens(900)
    with pytest.raises(TokenBudgetExceededError):
        agent.check_token_budget(200)


def test_reset_token_count_allows_new_budget():
    agent = _make_agent(budget=500)
    agent.consume_tokens(400)
    agent.reset_token_count()
    agent.check_token_budget(400)  # should not raise after reset


def test_validate_input_passes_valid_schema():
    agent = _make_agent()
    data = {"name": "test", "value": 42.0}
    result = agent.validate_input(data, SampleSchema)
    assert isinstance(result, SampleSchema)
    assert result.name == "test"


def test_validate_input_raises_on_invalid_data():
    agent = _make_agent()
    with pytest.raises(ValidationContractError) as exc_info:
        agent.validate_input({"name": "test"}, SampleSchema)  # missing 'value'
    assert exc_info.value.direction == "input"
    assert exc_info.value.agent == "test_agent"


def test_validate_output_passes_valid_schema():
    agent = _make_agent()
    data = {"name": "output", "value": 99.9}
    result = agent.validate_output(data, SampleSchema)
    assert result.value == 99.9


def test_validate_output_raises_on_invalid_data():
    agent = _make_agent()
    with pytest.raises(ValidationContractError) as exc_info:
        agent.validate_output({"name": "test", "value": "not_a_float"}, SampleSchema)
    assert exc_info.value.direction == "output"


def test_validate_input_accepts_model_instance():
    agent = _make_agent()
    instance = SampleSchema(name="x", value=1.0)
    result = agent.validate_input(instance, SampleSchema)
    assert result.name == "x"

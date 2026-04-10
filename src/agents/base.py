"""AgentBase class providing token budget enforcement and contract validation."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from src.errors import TokenBudgetExceededError, ValidationContractError
from src.schemas.config import AgentConfig


class AgentBase:
    """Base class for all XPI agents.

    Provides:
    - Token budget enforcement via check_token_budget()
    - Input/output schema validation via validate_input() / validate_output()
    """

    def __init__(self, agent_name: str, config: AgentConfig) -> None:
        self.agent_name = agent_name
        self.config = config
        self._tokens_used: int = 0

    def check_token_budget(self, tokens_requested: int) -> None:
        """Raise TokenBudgetExceededError if the request would exceed the budget.

        Args:
            tokens_requested: The number of tokens about to be consumed.

        Raises:
            TokenBudgetExceededError: If tokens_requested > remaining budget.
        """
        remaining = self.config.token_budget - self._tokens_used
        if tokens_requested > remaining:
            raise TokenBudgetExceededError(
                agent=self.agent_name,
                budget=self.config.token_budget,
                requested=tokens_requested,
            )

    def consume_tokens(self, tokens: int) -> None:
        """Record tokens consumed (called after a successful LLM call)."""
        self._tokens_used += tokens

    def reset_token_count(self) -> None:
        """Reset the token counter (e.g., between pipeline runs)."""
        self._tokens_used = 0

    def validate_input(self, data: object, schema: type[BaseModel]) -> BaseModel:
        """Validate input data against a Pydantic schema.

        Args:
            data: The raw input (dict or BaseModel instance).
            schema: The expected Pydantic model class.

        Returns:
            A validated instance of schema.

        Raises:
            ValidationContractError: If validation fails.
        """
        try:
            if isinstance(data, schema):
                return data
            if isinstance(data, BaseModel):
                return schema.model_validate(data.model_dump())
            return schema.model_validate(data)
        except ValidationError as exc:
            field = exc.errors()[0].get("loc", ("unknown",))[0] if exc.errors() else "unknown"
            raise ValidationContractError(
                agent=self.agent_name,
                direction="input",
                field=str(field),
                detail=str(exc),
            ) from exc

    def validate_output(self, data: object, schema: type[BaseModel]) -> BaseModel:
        """Validate output data against a Pydantic schema.

        Args:
            data: The output to validate (dict or BaseModel instance).
            schema: The expected Pydantic model class.

        Returns:
            A validated instance of schema.

        Raises:
            ValidationContractError: If validation fails.
        """
        try:
            if isinstance(data, schema):
                return data
            if isinstance(data, BaseModel):
                return schema.model_validate(data.model_dump())
            return schema.model_validate(data)
        except ValidationError as exc:
            field = exc.errors()[0].get("loc", ("unknown",))[0] if exc.errors() else "unknown"
            raise ValidationContractError(
                agent=self.agent_name,
                direction="output",
                field=str(field),
                detail=str(exc),
            ) from exc

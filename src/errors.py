"""Typed error classes for the XPI pipeline."""

from __future__ import annotations


class XPIError(Exception):
    """Base class for all XPI pipeline errors."""


class TokenBudgetExceededError(XPIError):
    """Raised when an agent's token budget would be exceeded before an LLM call."""

    def __init__(self, agent: str, budget: int, requested: int) -> None:
        self.agent = agent
        self.budget = budget
        self.requested = requested
        super().__init__(
            f"Agent '{agent}' token budget exceeded: budget={budget}, requested={requested}"
        )


class ArchiveNotFoundError(XPIError):
    """Raised when requested data is not found in the NASA archive."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ArchiveConnectionError(XPIError):
    """Raised when the NASA archive is unreachable."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"NASA archive unreachable: {detail}")


class ToolNotFoundError(XPIError):
    """Raised when an unregistered MCP tool is called."""

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"MCP tool not registered: '{tool_name}'")


class RegressionError(XPIError):
    """Raised when the F1 score regresses beyond the allowed threshold."""

    def __init__(self, current_f1: float, prior_f1: float, delta: float) -> None:
        self.current_f1 = current_f1
        self.prior_f1 = prior_f1
        self.delta = delta
        super().__init__(
            f"F1 regression detected: current={current_f1:.4f}, "
            f"prior={prior_f1:.4f}, delta={delta:.4f}"
        )


class ValidationContractError(XPIError):
    """Raised when an agent's input or output fails schema validation at a node boundary."""

    def __init__(self, agent: str, direction: str, field: str, detail: str) -> None:
        self.agent = agent
        self.direction = direction
        self.field = field
        self.detail = detail
        super().__init__(
            f"Agent '{agent}' {direction} contract violation on field '{field}': {detail}"
        )


class ConfigError(XPIError):
    """Raised when required configuration (e.g., API tokens) is missing."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

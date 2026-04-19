"""MCP server entry point — registers NASA data gateway tools."""

from __future__ import annotations

from typing import Any

from src.errors import ToolNotFoundError

REGISTERED_TOOLS = [
    "get_light_curve",
    "get_stellar_properties",
]

# Tool registry: name -> callable
_TOOL_REGISTRY: dict[str, Any] = {}


def register_tool(name: str, fn: Any) -> None:
    """Register a tool by name."""
    _TOOL_REGISTRY[name] = fn


def call_tool(tool_name: str, **kwargs: Any) -> dict:
    """Dispatch a tool call by name.

    Args:
        tool_name: The registered MCP tool name.
        **kwargs: Tool-specific keyword arguments.

    Returns:
        Tool output dict.

    Raises:
        ToolNotFoundError: If the tool is not in the registry.
    """
    if tool_name not in _TOOL_REGISTRY:
        raise ToolNotFoundError(tool_name)
    return _TOOL_REGISTRY[tool_name](**kwargs)


def get_registered_tools() -> list[str]:
    """Return the list of registered tool names."""
    return list(_TOOL_REGISTRY.keys())


def _setup_default_tools() -> None:
    """Register the default NASA data tools."""
    from src.mcp.tools.archive_tool import get_stellar_properties
    from src.mcp.tools.lightkurve_tool import get_light_curve

    register_tool("get_light_curve", get_light_curve)
    register_tool("get_stellar_properties", get_stellar_properties)


# Register default tools at import time
_setup_default_tools()


if __name__ == "__main__":
    import sys
    print(f"XPI MCP Server — registered tools: {REGISTERED_TOOLS}")
    print("Server ready. Tools registered:")
    for t in get_registered_tools():
        print(f"  - {t}")
    sys.exit(0)

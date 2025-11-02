"""Tool Registry.

Deliverable #3: Tool registry with capability filtering ✅
"""

from typing import Any


class ToolRegistry:
    """Tool registry with capability-based lookup."""

    def __init__(self):
        self._tools: dict[str, Any] = {}

    def register(self, tool: Any) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Any | None:
        """Get tool by name."""
        return self._tools.get(name)

    def filter_by_capability(self, capability: str) -> list[Any]:
        """Filter tools by capability tag."""
        return [t for t in self._tools.values() if capability in t.metadata.capabilities]

"""Tool Interface & Metadata.

Deliverable #3: Tool interface with schemas, metadata ✅
"""

from typing import Any, Protocol

from pydantic import BaseModel


class ToolMetadata(BaseModel):
    """Tool capability metadata."""

    requires_approval: bool = False
    dry_run_supported: bool = False
    idempotent: bool = False
    capabilities: list[str] = []
    risk_level: str = "low"


class Tool(Protocol):
    """Tool interface."""

    name: str
    description: str
    metadata: ToolMetadata

    async def execute(self, ctx: dict, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute tool action."""
        ...

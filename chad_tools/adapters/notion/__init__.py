"""Notion adapter for Chad-Core.

Provides tools for interacting with Notion as a knowledge base:
- Search workspace
- Read page content
- Create pages
- Query databases

Usage:
    from chad_tools.adapters.notion import register_notion_tools
    from chad_tools.registry import ToolRegistry

    registry = ToolRegistry()
    register_notion_tools(registry, api_key="secret_...")
"""

from .client import NotionClientWrapper
from .exceptions import (
    NotionAdapterError,
    NotionAuthError,
    NotionRateLimitError,
    NotionResourceNotFoundError,
    NotionValidationError,
)
from .schemas import (
    NotionSearchInput,
    NotionSearchOutput,
    NotionSearchResult,
    NotionReadPageInput,
    NotionReadPageOutput,
    NotionBlock,
    NotionCreatePageInput,
    NotionCreatePageOutput,
    NotionQueryDatabaseInput,
    NotionQueryDatabaseOutput,
    NotionDatabaseEntry,
)
from .tools import (
    NotionSearchTool,
    NotionReadPageTool,
    NotionCreatePageTool,
    NotionQueryDatabaseTool,
)

__all__ = [
    # Client
    "NotionClientWrapper",
    # Exceptions
    "NotionAdapterError",
    "NotionAuthError",
    "NotionRateLimitError",
    "NotionResourceNotFoundError",
    "NotionValidationError",
    # Schemas
    "NotionSearchInput",
    "NotionSearchOutput",
    "NotionSearchResult",
    "NotionReadPageInput",
    "NotionReadPageOutput",
    "NotionBlock",
    "NotionCreatePageInput",
    "NotionCreatePageOutput",
    "NotionQueryDatabaseInput",
    "NotionQueryDatabaseOutput",
    "NotionDatabaseEntry",
    # Tools
    "NotionSearchTool",
    "NotionReadPageTool",
    "NotionCreatePageTool",
    "NotionQueryDatabaseTool",
]


def register_notion_tools(registry, api_key: str) -> None:
    """Register all Notion tools with the tool registry.

    Args:
        registry: ToolRegistry instance
        api_key: Notion API key

    Example:
        from chad_tools.registry import ToolRegistry
        from chad_tools.adapters.notion import register_notion_tools

        registry = ToolRegistry()
        register_notion_tools(registry, api_key="secret_...")
    """
    registry.register(NotionSearchTool(api_key=api_key))
    registry.register(NotionReadPageTool(api_key=api_key))
    registry.register(NotionCreatePageTool(api_key=api_key))
    registry.register(NotionQueryDatabaseTool(api_key=api_key))

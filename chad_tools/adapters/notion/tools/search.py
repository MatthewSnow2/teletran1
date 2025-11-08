"""Notion Search Tool.

Search across Notion workspace for pages and databases.
"""

from typing import Any

from chad_tools.base import ToolMetadata
from chad_tools.adapters.notion.client import NotionClientWrapper
from chad_tools.adapters.notion.schemas import (
    NotionSearchInput,
    NotionSearchOutput,
    NotionSearchResult,
)
from chad_tools.adapters.notion.exceptions import NotionAdapterError


class NotionSearchTool:
    """Tool for searching Notion workspace.

    Capabilities:
    - Search for pages and databases
    - Filter by object type
    - Return structured results with URLs

    Use Cases:
    - "Find all pages about Python"
    - "Search for customer database"
    - "Locate pages modified this week"
    """

    name = "notion.search"
    description = "Search across Notion workspace for pages and databases"

    metadata = ToolMetadata(
        requires_approval=False,
        dry_run_supported=True,
        idempotent=True,  # Same query → same results
        capabilities=["notion.search", "notion.read"],
        risk_level="low",
    )

    def __init__(self, api_key: str, **kwargs):
        """Initialize NotionSearchTool.

        Args:
            api_key: Notion API key
            **kwargs: Additional client configuration
        """
        self.client = NotionClientWrapper(api_key=api_key, **kwargs)

    def _extract_title(self, page: dict[str, Any]) -> str:
        """Extract title from Notion page object.

        Args:
            page: Notion page/database object

        Returns:
            Page title string
        """
        try:
            # Try page title
            if "properties" in page:
                title_prop = page["properties"].get("title")
                if title_prop and title_prop.get("title"):
                    title_parts = title_prop["title"]
                    if title_parts:
                        return "".join([t.get("plain_text", "") for t in title_parts])

            # Try database title
            if "title" in page:
                title_parts = page["title"]
                if isinstance(title_parts, list) and title_parts:
                    return "".join([t.get("plain_text", "") for t in title_parts])
                elif isinstance(title_parts, str):
                    return title_parts

            # Fallback
            return "Untitled"
        except Exception:
            return "Untitled"

    def _extract_parent_type(self, page: dict[str, Any]) -> str:
        """Extract parent type from page object.

        Args:
            page: Notion page object

        Returns:
            Parent type: "workspace", "page", or "database"
        """
        try:
            parent = page.get("parent", {})
            if "workspace" in parent:
                return "workspace"
            elif "page_id" in parent:
                return "page"
            elif "database_id" in parent:
                return "database"
            else:
                return "unknown"
        except Exception:
            return "unknown"

    async def execute(
        self, ctx: dict[str, Any], input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute search query.

        Args:
            ctx: Execution context (actor, trace_id, etc.)
            input_data: Tool input matching NotionSearchInput schema

        Returns:
            Search results matching NotionSearchOutput schema

        Raises:
            NotionAdapterError: API errors
        """
        # Validate input
        input_obj = NotionSearchInput(**input_data)

        # Handle dry-run mode
        if input_obj.dry_run:
            return self._dry_run_response(input_obj)

        try:
            # Execute search
            response = await self.client.search(
                query=input_obj.query,
                filter_type=input_obj.filter_type,
                page_size=input_obj.max_results,
            )

            # Parse results
            results = []
            for item in response.get("results", []):
                result = NotionSearchResult(
                    id=item["id"],
                    type=item["object"],  # "page" or "database"
                    title=self._extract_title(item),
                    url=item["url"],
                    created_time=item["created_time"],
                    last_edited_time=item["last_edited_time"],
                    parent_type=self._extract_parent_type(item),
                )
                results.append(result)

            # Build output
            output = NotionSearchOutput(
                results=results,
                total_count=len(results),
                has_more=response.get("has_more", False),
                status="success",
            )

            return output.model_dump()

        except NotionAdapterError:
            raise
        except Exception as e:
            raise NotionAdapterError(f"Unexpected error during search: {str(e)}")

    def _dry_run_response(self, input_obj: NotionSearchInput) -> dict[str, Any]:
        """Generate dry-run mock response.

        Args:
            input_obj: Validated input

        Returns:
            Mock response matching NotionSearchOutput schema
        """
        mock_result = NotionSearchResult(
            id="mock-uuid-12345678",
            type="page",
            title=f"Mock result for query: '{input_obj.query}'",
            url="https://notion.so/mock-page-12345678",
            created_time="2025-11-03T00:00:00.000Z",
            last_edited_time="2025-11-03T12:00:00.000Z",
            parent_type="workspace",
        )

        output = NotionSearchOutput(
            results=[mock_result],
            total_count=1,
            has_more=False,
            status="dry_run",
        )

        return {
            **output.model_dump(),
            "warning": "This is a dry-run response; no real Notion API call was made",
            "would_execute": f"notion.search(query='{input_obj.query}', filter={input_obj.filter_type})",
        }

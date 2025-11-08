"""Notion Query Database Tool.

Query Notion databases with filters and sorting.
"""

from typing import Any

from chad_tools.base import ToolMetadata
from chad_tools.adapters.notion.client import NotionClientWrapper
from chad_tools.adapters.notion.schemas import (
    NotionQueryDatabaseInput,
    NotionQueryDatabaseOutput,
    NotionDatabaseEntry,
)
from chad_tools.adapters.notion.exceptions import NotionAdapterError


class NotionQueryDatabaseTool:
    """Tool for querying Notion databases.

    Capabilities:
    - Query databases with filters
    - Sort results
    - Extract properties (text, dates, select, etc.)
    - Paginate through results

    Use Cases:
    - "Get all tasks with status 'In Progress'"
    - "List projects sorted by priority"
    - "Find entries modified this week"
    """

    name = "notion.databases.query"
    description = "Query Notion databases with filters and sorting"

    metadata = ToolMetadata(
        requires_approval=False,
        dry_run_supported=True,
        idempotent=True,  # Same query → same results
        capabilities=["notion.databases.query", "notion.databases.read", "notion.read"],
        risk_level="low",
    )

    def __init__(self, api_key: str, **kwargs):
        """Initialize NotionQueryDatabaseTool.

        Args:
            api_key: Notion API key
            **kwargs: Additional client configuration
        """
        self.client = NotionClientWrapper(api_key=api_key, **kwargs)

    def _extract_property_value(self, prop: dict[str, Any]) -> Any:
        """Extract value from Notion property object.

        Args:
            prop: Notion property object

        Returns:
            Extracted value (simplified)
        """
        prop_type = prop.get("type")

        if prop_type == "title":
            title_parts = prop.get("title", [])
            return "".join([t.get("plain_text", "") for t in title_parts])

        elif prop_type == "rich_text":
            text_parts = prop.get("rich_text", [])
            return "".join([t.get("plain_text", "") for t in text_parts])

        elif prop_type == "number":
            return prop.get("number")

        elif prop_type == "select":
            select_obj = prop.get("select")
            return select_obj.get("name") if select_obj else None

        elif prop_type == "multi_select":
            items = prop.get("multi_select", [])
            return [item.get("name") for item in items]

        elif prop_type == "date":
            date_obj = prop.get("date")
            if date_obj:
                start = date_obj.get("start")
                end = date_obj.get("end")
                return {"start": start, "end": end} if end else start
            return None

        elif prop_type == "checkbox":
            return prop.get("checkbox", False)

        elif prop_type == "url":
            return prop.get("url")

        elif prop_type == "email":
            return prop.get("email")

        elif prop_type == "phone_number":
            return prop.get("phone_number")

        elif prop_type == "status":
            status_obj = prop.get("status")
            return status_obj.get("name") if status_obj else None

        elif prop_type == "people":
            people = prop.get("people", [])
            return [p.get("name") for p in people]

        elif prop_type == "files":
            files = prop.get("files", [])
            return [f.get("name") for f in files]

        elif prop_type == "relation":
            relations = prop.get("relation", [])
            return [r.get("id") for r in relations]

        else:
            # Unsupported property type - return raw
            return {"type": prop_type, "raw": prop}

    def _simplify_properties(self, properties: dict[str, Any]) -> dict[str, Any]:
        """Simplify Notion properties to plain values.

        Args:
            properties: Raw Notion properties object

        Returns:
            Simplified properties dict
        """
        simplified = {}
        for key, value in properties.items():
            simplified[key] = self._extract_property_value(value)
        return simplified

    async def execute(
        self, ctx: dict[str, Any], input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute database query.

        Args:
            ctx: Execution context
            input_data: Tool input matching NotionQueryDatabaseInput schema

        Returns:
            Query results matching NotionQueryDatabaseOutput schema
        """
        # Validate input
        input_obj = NotionQueryDatabaseInput(**input_data)

        # Handle dry-run mode
        if input_obj.dry_run:
            return self._dry_run_response(input_obj)

        try:
            # Execute query
            response = await self.client.query_database(
                database_id=input_obj.database_id,
                filter_obj=input_obj.filter_conditions,
                sorts=input_obj.sorts,
                page_size=input_obj.max_results,
            )

            # Parse results
            entries = []
            for page in response.get("results", []):
                # Simplify properties
                simplified_props = self._simplify_properties(page.get("properties", {}))

                entry = NotionDatabaseEntry(
                    page_id=page["id"],
                    url=page["url"],
                    properties=simplified_props,
                    created_time=page["created_time"],
                    last_edited_time=page["last_edited_time"],
                )
                entries.append(entry)

            # Build output
            output = NotionQueryDatabaseOutput(
                results=entries,
                total_count=len(entries),
                has_more=response.get("has_more", False),
                status="success",
            )

            return output.model_dump()

        except NotionAdapterError:
            raise
        except Exception as e:
            raise NotionAdapterError(f"Unexpected error querying database: {str(e)}")

    def _dry_run_response(self, input_obj: NotionQueryDatabaseInput) -> dict[str, Any]:
        """Generate dry-run mock response."""
        mock_entry = NotionDatabaseEntry(
            page_id="mock-entry-id-12345",
            url="https://notion.so/mock-entry-12345",
            properties={
                "Name": "Mock Database Entry",
                "Status": "In Progress",
                "Priority": "High",
                "Created": "2025-11-03",
            },
            created_time="2025-11-03T00:00:00.000Z",
            last_edited_time="2025-11-03T12:00:00.000Z",
        )

        output = NotionQueryDatabaseOutput(
            results=[mock_entry],
            total_count=1,
            has_more=False,
            status="dry_run",
        )

        return {
            **output.model_dump(),
            "warning": "This is a dry-run response; no real Notion API call was made",
            "would_execute": f"notion.databases.query('{input_obj.database_id}', filters={bool(input_obj.filter_conditions)})",
        }

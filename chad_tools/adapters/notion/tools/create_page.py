"""Notion Create Page Tool.

Create new Notion pages with structured content from markdown.
"""

from typing import Any

from chad_tools.base import ToolMetadata
from chad_tools.adapters.notion.client import NotionClientWrapper
from chad_tools.adapters.notion.schemas import (
    NotionCreatePageInput,
    NotionCreatePageOutput,
)
from chad_tools.adapters.notion.exceptions import NotionAdapterError


class NotionCreatePageTool:
    """Tool for creating new Notion pages.

    Capabilities:
    - Create pages in workspace or as subpages
    - Create database entries with properties
    - Convert markdown to Notion blocks
    - Set page icons and properties

    Use Cases:
    - "Create a summary page for research findings"
    - "Add new entry to project database"
    - "Generate meeting notes page"
    """

    name = "notion.pages.create"
    description = "Create new Notion pages with content from markdown"

    metadata = ToolMetadata(
        requires_approval=True,  # Writing requires approval
        dry_run_supported=True,
        idempotent=False,  # Creates new page each time
        capabilities=["notion.pages.create", "notion.write"],
        risk_level="medium",
    )

    def __init__(self, api_key: str, **kwargs):
        """Initialize NotionCreatePageTool.

        Args:
            api_key: Notion API key
            **kwargs: Additional client configuration
        """
        self.client = NotionClientWrapper(api_key=api_key, **kwargs)

    def _markdown_to_blocks(self, markdown: str) -> list[dict[str, Any]]:
        """Convert markdown to Notion blocks.

        Args:
            markdown: Markdown content string

        Returns:
            List of Notion block objects

        Note:
            This is a simplified converter. For production, consider using
            a dedicated markdown-to-notion library like notion-md.
        """
        blocks = []
        lines = markdown.split("\n")
        current_list_type = None

        for line in lines:
            line = line.rstrip()

            # Skip empty lines
            if not line:
                current_list_type = None
                continue

            # Heading 1
            if line.startswith("# "):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    },
                })
                current_list_type = None

            # Heading 2
            elif line.startswith("## "):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                    },
                })
                current_list_type = None

            # Heading 3
            elif line.startswith("### "):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                    },
                })
                current_list_type = None

            # Bulleted list
            elif line.startswith("- ") or line.startswith("* "):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    },
                })
                current_list_type = "bulleted"

            # Numbered list
            elif line.startswith("1. ") or line.startswith("2. ") or line.startswith("3. "):
                # Extract content after number
                content = line.split(". ", 1)[1] if ". " in line else line
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    },
                })
                current_list_type = "numbered"

            # Code block (simplified - doesn't handle multiline)
            elif line.startswith("```"):
                # Skip code fence markers for now
                # TODO: Implement proper code block handling
                current_list_type = None
                continue

            # Quote
            elif line.startswith("> "):
                blocks.append({
                    "object": "block",
                    "type": "quote",
                    "quote": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    },
                })
                current_list_type = None

            # Divider
            elif line.strip() == "---":
                blocks.append({"object": "block", "type": "divider", "divider": {}})
                current_list_type = None

            # Paragraph (default)
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line}}]
                    },
                })
                current_list_type = None

        return blocks

    async def execute(
        self, ctx: dict[str, Any], input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute page creation.

        Args:
            ctx: Execution context
            input_data: Tool input matching NotionCreatePageInput schema

        Returns:
            Created page matching NotionCreatePageOutput schema
        """
        # Validate input
        input_obj = NotionCreatePageInput(**input_data)

        # Handle dry-run mode
        if input_obj.dry_run:
            return self._dry_run_response(input_obj)

        try:
            # Build parent reference
            parent = {}
            if input_obj.parent_type == "page_id":
                parent = {"page_id": input_obj.parent_id}
            else:
                parent = {"database_id": input_obj.parent_id}

            # Build properties
            # For pages: title is required
            # For database entries: properties come from input_obj.properties
            properties = {}

            if input_obj.parent_type == "page_id":
                # Creating a regular page (not database entry)
                properties = {
                    "title": [{"type": "text", "text": {"content": input_obj.title}}]
                }
            else:
                # Creating database entry - use provided properties
                # Title handling for database entries
                if "title" not in input_obj.properties and "Name" not in input_obj.properties:
                    # Add title/Name property if not provided
                    properties = {
                        "Name": {
                            "title": [{"type": "text", "text": {"content": input_obj.title}}]
                        },
                        **input_obj.properties,
                    }
                else:
                    properties = input_obj.properties

            # Convert markdown to blocks
            children = []
            if input_obj.content_markdown:
                children = self._markdown_to_blocks(input_obj.content_markdown)

            # Build icon
            icon = None
            if input_obj.icon_emoji:
                icon = {"type": "emoji", "emoji": input_obj.icon_emoji}

            # Create page
            response = await self.client.create_page(
                parent=parent,
                properties=properties,
                children=children,
                icon=icon,
            )

            # Build output
            output = NotionCreatePageOutput(
                page_id=response["id"],
                url=response["url"],
                title=input_obj.title,
                created_time=response["created_time"],
                status="created",
            )

            return output.model_dump()

        except NotionAdapterError:
            raise
        except Exception as e:
            raise NotionAdapterError(f"Unexpected error creating page: {str(e)}")

    def _dry_run_response(self, input_obj: NotionCreatePageInput) -> dict[str, Any]:
        """Generate dry-run mock response."""
        output = NotionCreatePageOutput(
            page_id="mock-created-page-id-12345",
            url=f"https://notion.so/mock-created-page-12345",
            title=input_obj.title,
            created_time="2025-11-03T12:00:00.000Z",
            status="dry_run",
        )

        return {
            **output.model_dump(),
            "warning": "This is a dry-run response; no real page was created",
            "would_execute": f"notion.pages.create(parent={input_obj.parent_type}:'{input_obj.parent_id}', title='{input_obj.title}')",
            "preview": {
                "title": input_obj.title,
                "content_length": len(input_obj.content_markdown),
                "icon": input_obj.icon_emoji,
                "parent_type": input_obj.parent_type,
            },
        }

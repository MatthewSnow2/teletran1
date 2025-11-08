"""Notion Read Page Tool.

Retrieve full content of Notion pages including blocks and convert to markdown.
"""

from typing import Any

from chad_tools.base import ToolMetadata
from chad_tools.adapters.notion.client import NotionClientWrapper
from chad_tools.adapters.notion.schemas import (
    NotionReadPageInput,
    NotionReadPageOutput,
    NotionBlock,
)
from chad_tools.adapters.notion.exceptions import NotionAdapterError


class NotionReadPageTool:
    """Tool for reading Notion page content.

    Capabilities:
    - Retrieve full page content
    - Parse blocks (paragraphs, headings, code, etc.)
    - Convert to markdown
    - Handle nested blocks

    Use Cases:
    - "Read the 'Project Guidelines' page"
    - "Extract code snippets from API docs"
    - "Get content from page ID abc123"
    """

    name = "notion.pages.read"
    description = "Retrieve full content of a Notion page including all blocks"

    metadata = ToolMetadata(
        requires_approval=False,
        dry_run_supported=True,
        idempotent=True,
        capabilities=["notion.pages.read", "notion.read"],
        risk_level="low",
    )

    def __init__(self, api_key: str, **kwargs):
        """Initialize NotionReadPageTool.

        Args:
            api_key: Notion API key
            **kwargs: Additional client configuration
        """
        self.client = NotionClientWrapper(api_key=api_key, **kwargs)

    def _extract_text(self, rich_text: list[dict[str, Any]]) -> str:
        """Extract plain text from Notion rich_text array.

        Args:
            rich_text: Notion rich_text array

        Returns:
            Plain text string
        """
        if not rich_text:
            return ""
        return "".join([text.get("plain_text", "") for text in rich_text])

    def _block_to_markdown(self, block: dict[str, Any]) -> str:
        """Convert Notion block to markdown.

        Args:
            block: Notion block object

        Returns:
            Markdown string
        """
        block_type = block.get("type", "")
        block_data = block.get(block_type, {})

        # Paragraph
        if block_type == "paragraph":
            text = self._extract_text(block_data.get("rich_text", []))
            return f"{text}\n\n" if text else ""

        # Headings
        elif block_type == "heading_1":
            text = self._extract_text(block_data.get("rich_text", []))
            return f"# {text}\n\n"
        elif block_type == "heading_2":
            text = self._extract_text(block_data.get("rich_text", []))
            return f"## {text}\n\n"
        elif block_type == "heading_3":
            text = self._extract_text(block_data.get("rich_text", []))
            return f"### {text}\n\n"

        # Bulleted list
        elif block_type == "bulleted_list_item":
            text = self._extract_text(block_data.get("rich_text", []))
            return f"- {text}\n"

        # Numbered list
        elif block_type == "numbered_list_item":
            text = self._extract_text(block_data.get("rich_text", []))
            return f"1. {text}\n"

        # Code block
        elif block_type == "code":
            text = self._extract_text(block_data.get("rich_text", []))
            language = block_data.get("language", "")
            return f"```{language}\n{text}\n```\n\n"

        # Quote
        elif block_type == "quote":
            text = self._extract_text(block_data.get("rich_text", []))
            return f"> {text}\n\n"

        # Divider
        elif block_type == "divider":
            return "---\n\n"

        # Callout
        elif block_type == "callout":
            text = self._extract_text(block_data.get("rich_text", []))
            icon = block_data.get("icon", {}).get("emoji", "💡")
            return f"{icon} {text}\n\n"

        # Toggle
        elif block_type == "toggle":
            text = self._extract_text(block_data.get("rich_text", []))
            return f"▶ {text}\n\n"

        # To-do
        elif block_type == "to_do":
            text = self._extract_text(block_data.get("rich_text", []))
            checked = block_data.get("checked", False)
            checkbox = "[x]" if checked else "[ ]"
            return f"{checkbox} {text}\n"

        # Unsupported blocks
        else:
            return f"[Unsupported block type: {block_type}]\n\n"

    async def _parse_blocks(
        self,
        block_id: str,
        max_depth: int,
        current_depth: int = 0,
    ) -> tuple[list[NotionBlock], str]:
        """Recursively parse blocks and convert to structured format.

        Args:
            block_id: Block/page ID to retrieve children
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth

        Returns:
            Tuple of (structured blocks, markdown string)
        """
        if current_depth >= max_depth:
            return [], ""

        try:
            response = await self.client.get_blocks(block_id)
            blocks = response.get("results", [])

            parsed_blocks = []
            markdown_parts = []

            for block_data in blocks:
                block_type = block_data.get("type", "")
                block_content = block_data.get(block_type, {})

                # Extract text content
                rich_text = block_content.get("rich_text", [])
                content_text = self._extract_text(rich_text)

                # Convert to markdown
                markdown = self._block_to_markdown(block_data)
                markdown_parts.append(markdown)

                # Check for children
                children = []
                children_markdown = ""
                has_children = block_data.get("has_children", False)

                if has_children:
                    children, children_markdown = await self._parse_blocks(
                        block_data["id"],
                        max_depth,
                        current_depth + 1,
                    )
                    markdown_parts.append(children_markdown)

                # Create structured block
                notion_block = NotionBlock(
                    id=block_data["id"],
                    type=block_type,
                    content=content_text,
                    metadata=block_content,
                    children=children,
                )
                parsed_blocks.append(notion_block)

            return parsed_blocks, "".join(markdown_parts)

        except Exception as e:
            raise NotionAdapterError(f"Failed to parse blocks: {str(e)}")

    async def execute(
        self, ctx: dict[str, Any], input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute page read.

        Args:
            ctx: Execution context
            input_data: Tool input matching NotionReadPageInput schema

        Returns:
            Page content matching NotionReadPageOutput schema
        """
        # Validate input
        input_obj = NotionReadPageInput(**input_data)

        # Handle dry-run mode
        if input_obj.dry_run:
            return self._dry_run_response(input_obj)

        try:
            # Get page metadata
            page = await self.client.get_page(input_obj.page_id)

            # Extract title
            title = "Untitled"
            if "properties" in page:
                title_prop = page["properties"].get("title")
                if title_prop and title_prop.get("title"):
                    title_parts = title_prop["title"]
                    if title_parts:
                        title = "".join([t.get("plain_text", "") for t in title_parts])

            # Parse blocks
            blocks, markdown = await self._parse_blocks(
                input_obj.page_id,
                input_obj.max_depth if input_obj.include_children else 1,
            )

            # Build output
            output = NotionReadPageOutput(
                page_id=page["id"],
                title=title,
                url=page["url"],
                properties=page.get("properties", {}),
                content=blocks,
                markdown=markdown,
                created_time=page["created_time"],
                last_edited_time=page["last_edited_time"],
                status="success",
            )

            return output.model_dump()

        except NotionAdapterError:
            raise
        except Exception as e:
            raise NotionAdapterError(f"Unexpected error reading page: {str(e)}")

    def _dry_run_response(self, input_obj: NotionReadPageInput) -> dict[str, Any]:
        """Generate dry-run mock response."""
        mock_block = NotionBlock(
            id="mock-block-id",
            type="paragraph",
            content="This is mock page content for testing purposes.",
            metadata={},
            children=[],
        )

        output = NotionReadPageOutput(
            page_id=input_obj.page_id,
            title="Mock Page Title",
            url=f"https://notion.so/{input_obj.page_id}",
            properties={},
            content=[mock_block],
            markdown="# Mock Page Title\n\nThis is mock page content for testing purposes.\n\n",
            created_time="2025-11-03T00:00:00.000Z",
            last_edited_time="2025-11-03T12:00:00.000Z",
            status="dry_run",
        )

        return {
            **output.model_dump(),
            "warning": "This is a dry-run response; no real Notion API call was made",
            "would_execute": f"notion.pages.retrieve('{input_obj.page_id}')",
        }

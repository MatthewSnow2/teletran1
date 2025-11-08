"""N8N Workflow Discovery & Registration."""

import json
import re
from typing import Any

from chad_tools.registry import ToolRegistry
from chad_tools.adapters.notion import NotionClientWrapper

from .tool import N8nWorkflowTool
from .schemas import N8nWorkflowMetadata


class N8nWorkflowRegistry:
    """Discovers n8n workflows from Notion and registers as tools."""

    def __init__(
        self,
        notion_client: NotionClientWrapper,
        tool_registry: ToolRegistry,
        api_key: str | None = None,
    ):
        """Initialize n8n workflow registry.

        Args:
            notion_client: Notion client for reading documentation
            tool_registry: Tool registry to register workflows into
            api_key: Optional API key for n8n webhook authentication
        """
        self.notion_client = notion_client
        self.tool_registry = tool_registry
        self.api_key = api_key
        self.workflows: dict[str, N8nWorkflowMetadata] = {}

    async def discover_and_register(
        self,
        notion_folder_id: str | None = None,
    ) -> int:
        """Discover workflows in Notion and register as tools.

        Args:
            notion_folder_id: Notion page ID of "n8n Workflows" folder
                             If None, searches for folder by name

        Returns:
            Number of workflows registered
        """
        # Step 1: Find "n8n Workflows" folder
        if not notion_folder_id:
            notion_folder_id = await self._find_workflows_folder()

        if not notion_folder_id:
            raise ValueError("Could not find 'n8n Workflows' folder in Notion")

        # Step 2: Get all child pages
        workflow_pages = await self._get_workflow_pages(notion_folder_id)

        # Step 3: Parse each workflow page
        registered_count = 0
        for page in workflow_pages:
            try:
                metadata = await self._parse_workflow_page(page)
                self._register_workflow(metadata)
                registered_count += 1
            except Exception as e:
                # Log warning but continue with other workflows
                print(
                    f"Warning: Failed to register workflow {page.get('id')}: {e}"
                )

        return registered_count

    async def _find_workflows_folder(self) -> str | None:
        """Find 'n8n Workflows' folder in Notion workspace."""
        results = await self.notion_client.search("n8n Workflows")

        for result in results.get("results", []):
            if result.get("object") == "page":
                # Check if title matches
                title_prop = result.get("properties", {}).get("title", {})
                title_items = title_prop.get("title", [])
                if title_items:
                    title = title_items[0].get("plain_text", "")
                    if title == "n8n Workflows":
                        return result["id"]

        return None

    async def _get_workflow_pages(self, folder_id: str) -> list[dict]:
        """Get all child pages of workflows folder."""
        # Use Notion's blocks API to get child pages
        response = await self.notion_client.client.blocks.children.list(folder_id)

        workflow_pages = []
        for block in response.get("results", []):
            if block.get("type") == "child_page":
                # Get full page details
                page_id = block["id"]
                page = await self.notion_client.client.pages.retrieve(page_id)
                workflow_pages.append(page)

        return workflow_pages

    async def _parse_workflow_page(self, page: dict) -> N8nWorkflowMetadata:
        """Parse workflow documentation page into metadata.

        Expected page structure (markdown):

        # n8n Workflow: [Name]

        **Workflow ID**: `workflow_send_notification`
        **Webhook URL**: `https://...`
        **Async**: No
        **Risk Level**: low

        ## Purpose
        [Description]

        ## Input Parameters
        ```json
        { JSON Schema }
        ```

        ## Capabilities
        - capability1
        - capability2
        """
        # Get page title
        title_prop = page.get("properties", {}).get("title", {})
        title_items = title_prop.get("title", [])
        display_name = (
            title_items[0].get("plain_text", "") if title_items else "Unknown"
        )

        # Read page content
        page_id = page["id"]
        blocks = await self.notion_client.client.blocks.children.list(page_id)
        content = self._blocks_to_text(blocks.get("results", []))

        # Parse metadata fields
        workflow_id = self._extract_field(content, "Workflow ID")
        webhook_url = self._extract_field(content, "Webhook URL")
        is_async = self._extract_field(content, "Async", default="No") == "Yes"
        risk_level = self._extract_field(content, "Risk Level", default="low")

        # Parse purpose/description
        description = self._extract_section(content, "Purpose")

        # Parse input schema
        input_schema_json = self._extract_code_block(content, "Input Parameters")
        input_params = json.loads(input_schema_json) if input_schema_json else {}

        # Parse capabilities
        capabilities_text = self._extract_section(content, "Capabilities")
        capabilities = [
            line.strip("- ").strip()
            for line in capabilities_text.split("\n")
            if line.strip().startswith("-")
        ]

        return N8nWorkflowMetadata(
            workflow_id=workflow_id,
            display_name=display_name,
            webhook_url=webhook_url,
            description=description,
            input_params=input_params,
            is_async=is_async,
            risk_level=risk_level,
            capabilities=capabilities,
        )

    def _blocks_to_text(self, blocks: list[dict]) -> str:
        """Convert Notion blocks to plain text."""
        lines = []
        for block in blocks:
            block_type = block.get("type")

            if block_type == "paragraph":
                text = self._get_rich_text(block["paragraph"].get("rich_text", []))
                lines.append(text)
            elif block_type == "heading_1":
                text = self._get_rich_text(block["heading_1"].get("rich_text", []))
                lines.append(f"# {text}")
            elif block_type == "heading_2":
                text = self._get_rich_text(block["heading_2"].get("rich_text", []))
                lines.append(f"## {text}")
            elif block_type == "code":
                code = self._get_rich_text(block["code"].get("rich_text", []))
                lines.append(f"```\n{code}\n```")
            elif block_type == "bulleted_list_item":
                text = self._get_rich_text(
                    block["bulleted_list_item"].get("rich_text", [])
                )
                lines.append(f"- {text}")

        return "\n".join(lines)

    def _get_rich_text(self, rich_text: list[dict]) -> str:
        """Extract plain text from rich text array."""
        return "".join(item.get("plain_text", "") for item in rich_text)

    def _extract_field(
        self, content: str, field_name: str, default: str = ""
    ) -> str:
        """Extract field value from markdown content.

        Example: **Workflow ID**: `workflow_send_notification`
        Or: Workflow ID: workflow_send_notification
        """
        # Try with markdown bold formatting first
        pattern = rf"\*\*{field_name}\*\*:\s*`?([^`\n]+)`?"
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()

        # Fall back to plain text field name
        pattern = rf"{field_name}:\s*(.+?)(?:\n|$)"
        match = re.search(pattern, content)
        return match.group(1).strip() if match else default

    def _extract_section(self, content: str, heading: str) -> str:
        """Extract text under a heading until next heading."""
        pattern = rf"##\s+{heading}\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_code_block(self, content: str, heading: str) -> str | None:
        """Extract code block content under a heading."""
        section = self._extract_section(content, heading)
        match = re.search(r"```(?:json)?\n(.*?)\n```", section, re.DOTALL)
        return match.group(1).strip() if match else None

    def _register_workflow(self, metadata: N8nWorkflowMetadata) -> None:
        """Register workflow as tool."""
        tool = N8nWorkflowTool(
            workflow_metadata=metadata,
            api_key=self.api_key,
        )
        self.tool_registry.register(tool)
        self.workflows[metadata.workflow_id] = metadata

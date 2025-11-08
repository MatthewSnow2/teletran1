"""Integration tests for n8n workflow adapter."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from chad_tools.registry import ToolRegistry
from chad_tools.adapters.n8n import (
    N8nClient,
    N8nWorkflowTool,
    N8nWorkflowRegistry,
    N8nWorkflowMetadata,
    N8nWebhookResponse,
)


@pytest.mark.asyncio
async def test_n8n_client_call_webhook_success():
    """Test successful webhook call."""
    client = N8nClient(api_key="test-key")

    with patch.object(client.client, "post") as mock_post:
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "sent_to": ["slack"],
            "timestamp": "2025-11-06T12:00:00Z",
        }
        mock_post.return_value = mock_response

        result = await client.call_webhook(
            webhook_url="https://example.com/webhook/test",
            payload={"message": "test"},
        )

        assert result.success is True
        assert result.data is not None
        assert result.data["success"] is True
        assert "slack" in result.data["sent_to"]

        # Verify headers were set
        mock_post.assert_called_once()
        call_headers = mock_post.call_args[1]["headers"]
        assert call_headers["X-CHAD-API-KEY"] == "test-key"
        assert call_headers["Content-Type"] == "application/json"

    await client.close()


@pytest.mark.asyncio
async def test_n8n_client_call_webhook_http_error():
    """Test webhook call with HTTP error."""
    client = N8nClient()

    with patch.object(client.client, "post") as mock_post:
        # Mock HTTP error
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": "Invalid API key"}

        mock_post.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        result = await client.call_webhook(
            webhook_url="https://example.com/webhook/test",
            payload={"message": "test"},
        )

        assert result.success is False
        assert "401" in result.error
        assert "Invalid API key" in result.error

    await client.close()


@pytest.mark.asyncio
async def test_n8n_workflow_tool_execute_dry_run():
    """Test workflow tool execution in dry-run mode."""
    metadata = N8nWorkflowMetadata(
        workflow_id="test_workflow",
        display_name="Test Workflow",
        webhook_url="https://example.com/webhook/test",
        description="Test workflow description",
        input_params={
            "type": "object",
            "required": ["message"],
            "properties": {"message": {"type": "string"}},
        },
    )

    tool = N8nWorkflowTool(workflow_metadata=metadata)

    # Execute in dry-run mode
    result = await tool.execute(
        ctx={"dry_run": True},
        input_data={"message": "test"},
    )

    assert result["status"] == "dry_run"
    assert "Test Workflow" in result["message"]
    assert result["webhook_url"] == "https://example.com/webhook/test"


@pytest.mark.asyncio
async def test_n8n_workflow_tool_execute_validation_error():
    """Test workflow tool with missing required fields."""
    metadata = N8nWorkflowMetadata(
        workflow_id="test_workflow",
        display_name="Test Workflow",
        webhook_url="https://example.com/webhook/test",
        description="Test",
        input_params={
            "type": "object",
            "required": ["message", "channels"],
            "properties": {
                "message": {"type": "string"},
                "channels": {"type": "array"},
            },
        },
    )

    tool = N8nWorkflowTool(workflow_metadata=metadata)

    # Execute with missing required field
    result = await tool.execute(
        ctx={"dry_run": False},
        input_data={"message": "test"},  # Missing 'channels'
    )

    assert result["status"] == "error"
    assert "validation failed" in result["error"].lower()
    assert "channels" in result["error"]


@pytest.mark.asyncio
async def test_n8n_workflow_tool_execute_success():
    """Test successful workflow execution."""
    metadata = N8nWorkflowMetadata(
        workflow_id="test_workflow",
        display_name="Test Workflow",
        webhook_url="https://example.com/webhook/test",
        description="Test",
        input_params={
            "type": "object",
            "required": ["message"],
            "properties": {"message": {"type": "string"}},
        },
    )

    # Mock client
    mock_client = AsyncMock(spec=N8nClient)
    mock_client.call_webhook.return_value = N8nWebhookResponse(
        success=True,
        data={"result": "success", "sent_to": ["slack"]},
    )

    tool = N8nWorkflowTool(workflow_metadata=metadata, client=mock_client)

    # Execute workflow
    result = await tool.execute(
        ctx={"dry_run": False},
        input_data={"message": "test"},
    )

    assert result["status"] == "success"
    assert result["data"]["result"] == "success"

    # Verify webhook was called
    mock_client.call_webhook.assert_called_once()


@pytest.mark.asyncio
async def test_n8n_workflow_tool_execute_async_workflow():
    """Test async workflow with polling."""
    metadata = N8nWorkflowMetadata(
        workflow_id="test_async",
        display_name="Test Async Workflow",
        webhook_url="https://example.com/webhook/test",
        description="Test async workflow",
        input_params={"type": "object", "properties": {}},
        is_async=True,
    )

    # Mock client
    mock_client = AsyncMock(spec=N8nClient)

    # First call returns execution_id
    mock_client.call_webhook.return_value = N8nWebhookResponse(
        success=True,
        data={"status": "processing"},
        execution_id="exec_123",
    )

    # Polling returns completed status
    mock_client.poll_execution.return_value = N8nWebhookResponse(
        success=True,
        data={"status": "completed", "result": "done"},
    )

    tool = N8nWorkflowTool(workflow_metadata=metadata, client=mock_client)

    # Execute async workflow
    result = await tool.execute(
        ctx={"dry_run": False},
        input_data={},
    )

    assert result["status"] == "success"
    assert result["data"]["status"] == "completed"

    # Verify both webhook call and polling were executed
    mock_client.call_webhook.assert_called_once()
    mock_client.poll_execution.assert_called_once_with(
        webhook_url="https://example.com/webhook/test",
        execution_id="exec_123",
        api_key=None,
    )


@pytest.mark.asyncio
async def test_n8n_workflow_registry_parse_workflow():
    """Test parsing workflow metadata from Notion page."""
    # Mock Notion client
    mock_notion_client = MagicMock()

    # Mock page data
    page = {
        "id": "page_123",
        "properties": {
            "title": {
                "title": [{"plain_text": "Send Notification"}]
            }
        },
    }

    # Mock page content (simplified)
    mock_blocks = {
        "results": [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "plain_text": "**Workflow ID**: `workflow_send_notification`"
                        }
                    ]
                },
            },
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "plain_text": "**Webhook URL**: `https://example.com/webhook/test`"
                        }
                    ]
                },
            },
            {
                "type": "heading_2",
                "heading_2": {"rich_text": [{"plain_text": "Purpose"}]},
            },
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "Sends notifications"}]
                },
            },
        ]
    }

    mock_notion_client.client.blocks.children.list.return_value = mock_blocks

    tool_registry = ToolRegistry()
    registry = N8nWorkflowRegistry(
        notion_client=mock_notion_client,
        tool_registry=tool_registry,
    )

    # Parse the page
    metadata = await registry._parse_workflow_page(page)

    assert metadata.workflow_id == "workflow_send_notification"
    assert str(metadata.webhook_url) == "https://example.com/webhook/test/"
    assert metadata.display_name == "Send Notification"
    assert "notification" in metadata.description.lower()


@pytest.mark.asyncio
async def test_n8n_workflow_registry_register_workflow():
    """Test registering a workflow as a tool."""
    metadata = N8nWorkflowMetadata(
        workflow_id="test_workflow",
        display_name="Test Workflow",
        webhook_url="https://example.com/webhook/test",
        description="Test workflow",
        input_params={"type": "object"},
        capabilities=["notification"],
    )

    mock_notion_client = MagicMock()
    tool_registry = ToolRegistry()

    registry = N8nWorkflowRegistry(
        notion_client=mock_notion_client,
        tool_registry=tool_registry,
    )

    # Register the workflow
    registry._register_workflow(metadata)

    # Verify tool was registered
    assert "n8n_test_workflow" in tool_registry._tools
    tool = tool_registry.get("n8n_test_workflow")
    assert tool is not None
    assert tool.name == "n8n_test_workflow"
    assert "notification" in tool.metadata.capabilities

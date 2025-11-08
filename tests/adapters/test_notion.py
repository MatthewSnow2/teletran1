"""Unit tests for Notion adapter.

Tests all Notion tools with mocked API responses.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from chad_tools.adapters.notion import (
    NotionSearchTool,
    NotionReadPageTool,
    NotionCreatePageTool,
    NotionQueryDatabaseTool,
    register_notion_tools,
)
from chad_tools.adapters.notion.exceptions import (
    NotionAdapterError,
    NotionAuthError,
    NotionRateLimitError,
    NotionResourceNotFoundError,
)
from chad_tools.registry import ToolRegistry


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_api_key():
    """Fake API key for testing."""
    return "secret_test_key_12345"


@pytest.fixture
def search_tool(mock_api_key):
    """NotionSearchTool instance."""
    return NotionSearchTool(api_key=mock_api_key)


@pytest.fixture
def read_page_tool(mock_api_key):
    """NotionReadPageTool instance."""
    return NotionReadPageTool(api_key=mock_api_key)


@pytest.fixture
def create_page_tool(mock_api_key):
    """NotionCreatePageTool instance."""
    return NotionCreatePageTool(api_key=mock_api_key)


@pytest.fixture
def query_database_tool(mock_api_key):
    """NotionQueryDatabaseTool instance."""
    return NotionQueryDatabaseTool(api_key=mock_api_key)


# ============================================================================
# NOTION SEARCH TOOL TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_search_tool_dry_run(search_tool):
    """Test NotionSearchTool in dry-run mode."""
    result = await search_tool.execute(
        ctx={"actor": "test"},
        input_data={"query": "Python", "max_results": 5, "dry_run": True},
    )

    assert result["status"] == "dry_run"
    assert "warning" in result
    assert len(result["results"]) > 0
    assert result["results"][0]["type"] in ["page", "database"]


@pytest.mark.asyncio
async def test_search_tool_success(search_tool):
    """Test NotionSearchTool with mocked successful API response."""
    mock_response = {
        "results": [
            {
                "id": "page-123",
                "object": "page",
                "url": "https://notion.so/page-123",
                "created_time": "2025-11-03T00:00:00.000Z",
                "last_edited_time": "2025-11-03T12:00:00.000Z",
                "properties": {
                    "title": {
                        "title": [{"plain_text": "Test Page"}]
                    }
                },
                "parent": {"workspace": True},
            }
        ],
        "has_more": False,
    }

    with patch.object(search_tool.client, "search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response

        result = await search_tool.execute(
            ctx={"actor": "test"},
            input_data={"query": "Python", "max_results": 5},
        )

        assert result["status"] == "success"
        assert result["total_count"] == 1
        assert result["results"][0]["title"] == "Test Page"
        assert result["results"][0]["id"] == "page-123"
        assert result["has_more"] is False

        mock_search.assert_called_once()


@pytest.mark.asyncio
async def test_search_tool_with_filter(search_tool):
    """Test NotionSearchTool with type filter."""
    with patch.object(search_tool.client, "search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {"results": [], "has_more": False}

        await search_tool.execute(
            ctx={"actor": "test"},
            input_data={"query": "Test", "filter_type": "page", "max_results": 10},
        )

        mock_search.assert_called_once_with(
            query="Test",
            filter_type="page",
            page_size=10,
        )


def test_search_tool_metadata(search_tool):
    """Test NotionSearchTool metadata configuration."""
    assert search_tool.name == "notion.search"
    assert search_tool.metadata.requires_approval is False
    assert search_tool.metadata.dry_run_supported is True
    assert search_tool.metadata.idempotent is True
    assert "notion.search" in search_tool.metadata.capabilities
    assert search_tool.metadata.risk_level == "low"


# ============================================================================
# NOTION READ PAGE TOOL TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_read_page_tool_dry_run(read_page_tool):
    """Test NotionReadPageTool in dry-run mode."""
    result = await read_page_tool.execute(
        ctx={"actor": "test"},
        input_data={"page_id": "page-123", "dry_run": True},
    )

    assert result["status"] == "dry_run"
    assert "warning" in result
    assert result["title"] == "Mock Page Title"
    assert len(result["markdown"]) > 0
    assert len(result["content"]) > 0


@pytest.mark.asyncio
async def test_read_page_tool_success(read_page_tool):
    """Test NotionReadPageTool with mocked successful API response."""
    mock_page = {
        "id": "page-123",
        "url": "https://notion.so/page-123",
        "created_time": "2025-11-03T00:00:00.000Z",
        "last_edited_time": "2025-11-03T12:00:00.000Z",
        "properties": {
            "title": {
                "title": [{"plain_text": "Test Page"}]
            }
        },
    }

    mock_blocks = {
        "results": [
            {
                "id": "block-1",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"plain_text": "This is a test paragraph."}]
                },
                "has_children": False,
            }
        ]
    }

    with patch.object(read_page_tool.client, "get_page", new_callable=AsyncMock) as mock_get_page:
        with patch.object(read_page_tool.client, "get_blocks", new_callable=AsyncMock) as mock_get_blocks:
            mock_get_page.return_value = mock_page
            mock_get_blocks.return_value = mock_blocks

            result = await read_page_tool.execute(
                ctx={"actor": "test"},
                input_data={"page_id": "page-123"},
            )

            assert result["status"] == "success"
            assert result["title"] == "Test Page"
            assert result["page_id"] == "page-123"
            assert len(result["content"]) == 1
            assert "This is a test paragraph" in result["markdown"]


def test_read_page_tool_metadata(read_page_tool):
    """Test NotionReadPageTool metadata configuration."""
    assert read_page_tool.name == "notion.pages.read"
    assert read_page_tool.metadata.requires_approval is False
    assert read_page_tool.metadata.idempotent is True
    assert "notion.pages.read" in read_page_tool.metadata.capabilities


# ============================================================================
# NOTION CREATE PAGE TOOL TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_page_tool_dry_run(create_page_tool):
    """Test NotionCreatePageTool in dry-run mode."""
    result = await create_page_tool.execute(
        ctx={"actor": "test"},
        input_data={
            "parent_id": "workspace",
            "title": "New Test Page",
            "content_markdown": "# Hello\n\nThis is a test.",
            "dry_run": True,
        },
    )

    assert result["status"] == "dry_run"
    assert "warning" in result
    assert result["title"] == "New Test Page"
    assert "preview" in result


@pytest.mark.asyncio
async def test_create_page_tool_success(create_page_tool):
    """Test NotionCreatePageTool with mocked successful API response."""
    mock_response = {
        "id": "new-page-123",
        "url": "https://notion.so/new-page-123",
        "created_time": "2025-11-03T12:00:00.000Z",
    }

    with patch.object(create_page_tool.client, "create_page", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response

        result = await create_page_tool.execute(
            ctx={"actor": "test"},
            input_data={
                "parent_id": "workspace",
                "title": "New Test Page",
                "content_markdown": "# Hello\n\nThis is a test.",
            },
        )

        assert result["status"] == "created"
        assert result["page_id"] == "new-page-123"
        assert result["title"] == "New Test Page"

        mock_create.assert_called_once()


def test_create_page_tool_metadata(create_page_tool):
    """Test NotionCreatePageTool metadata configuration."""
    assert create_page_tool.name == "notion.pages.create"
    assert create_page_tool.metadata.requires_approval is True  # Write operation
    assert create_page_tool.metadata.dry_run_supported is True
    assert create_page_tool.metadata.idempotent is False  # Creates new each time
    assert "notion.pages.create" in create_page_tool.metadata.capabilities
    assert create_page_tool.metadata.risk_level == "medium"


def test_create_page_markdown_to_blocks(create_page_tool):
    """Test markdown to blocks conversion."""
    markdown = """# Heading 1
## Heading 2
This is a paragraph.

- List item 1
- List item 2

> This is a quote
"""

    blocks = create_page_tool._markdown_to_blocks(markdown)

    # Check that various block types are created
    block_types = [b["type"] for b in blocks]
    assert "heading_1" in block_types
    assert "heading_2" in block_types
    assert "paragraph" in block_types
    assert "bulleted_list_item" in block_types
    assert "quote" in block_types


# ============================================================================
# NOTION QUERY DATABASE TOOL TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_query_database_tool_dry_run(query_database_tool):
    """Test NotionQueryDatabaseTool in dry-run mode."""
    result = await query_database_tool.execute(
        ctx={"actor": "test"},
        input_data={"database_id": "db-123", "dry_run": True},
    )

    assert result["status"] == "dry_run"
    assert "warning" in result
    assert len(result["results"]) > 0


@pytest.mark.asyncio
async def test_query_database_tool_success(query_database_tool):
    """Test NotionQueryDatabaseTool with mocked successful API response."""
    mock_response = {
        "results": [
            {
                "id": "entry-123",
                "url": "https://notion.so/entry-123",
                "created_time": "2025-11-03T00:00:00.000Z",
                "last_edited_time": "2025-11-03T12:00:00.000Z",
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"plain_text": "Task 1"}]
                    },
                    "Status": {
                        "type": "select",
                        "select": {"name": "In Progress"}
                    },
                },
            }
        ],
        "has_more": False,
    }

    with patch.object(query_database_tool.client, "query_database", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_response

        result = await query_database_tool.execute(
            ctx={"actor": "test"},
            input_data={"database_id": "db-123", "max_results": 10},
        )

        assert result["status"] == "success"
        assert result["total_count"] == 1
        assert result["results"][0]["properties"]["Name"] == "Task 1"
        assert result["results"][0]["properties"]["Status"] == "In Progress"


def test_query_database_tool_metadata(query_database_tool):
    """Test NotionQueryDatabaseTool metadata configuration."""
    assert query_database_tool.name == "notion.databases.query"
    assert query_database_tool.metadata.requires_approval is False
    assert query_database_tool.metadata.idempotent is True
    assert "notion.databases.query" in query_database_tool.metadata.capabilities


# ============================================================================
# TOOL REGISTRATION TESTS
# ============================================================================


def test_register_notion_tools(mock_api_key):
    """Test registering all Notion tools with registry."""
    registry = ToolRegistry()
    register_notion_tools(registry, api_key=mock_api_key)

    # Verify all 4 tools are registered
    assert registry.get("notion.search") is not None
    assert registry.get("notion.pages.read") is not None
    assert registry.get("notion.pages.create") is not None
    assert registry.get("notion.databases.query") is not None

    # Test capability filtering
    search_tools = registry.filter_by_capability("notion.search")
    assert len(search_tools) >= 1

    write_tools = registry.filter_by_capability("notion.write")
    assert len(write_tools) >= 1


def test_all_tools_have_required_attributes(mock_api_key):
    """Ensure all tools have required attributes."""
    tools = [
        NotionSearchTool(api_key=mock_api_key),
        NotionReadPageTool(api_key=mock_api_key),
        NotionCreatePageTool(api_key=mock_api_key),
        NotionQueryDatabaseTool(api_key=mock_api_key),
    ]

    for tool in tools:
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "metadata")
        assert hasattr(tool, "execute")
        assert callable(tool.execute)

        # Check metadata attributes
        assert hasattr(tool.metadata, "requires_approval")
        assert hasattr(tool.metadata, "dry_run_supported")
        assert hasattr(tool.metadata, "idempotent")
        assert hasattr(tool.metadata, "capabilities")
        assert hasattr(tool.metadata, "risk_level")

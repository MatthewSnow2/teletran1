"""Tool Registry Tests.

Deliverable #6: Tool registry tests ✅
"""

from chad_tools.base import ToolMetadata
from chad_tools.registry import ToolRegistry


class MockTool:
    name = "mock_tool"
    description = "Mock tool"
    metadata = ToolMetadata(capabilities=["test.mock"])


def test_register_and_retrieve_tool():
    """Test tool registration and retrieval."""
    registry = ToolRegistry()
    tool = MockTool()

    registry.register(tool)
    retrieved = registry.get("mock_tool")

    assert retrieved is not None
    assert retrieved.name == "mock_tool"


def test_filter_by_capability():
    """Test capability-based filtering."""
    registry = ToolRegistry()
    tool = MockTool()
    registry.register(tool)

    results = registry.filter_by_capability("test.mock")
    assert len(results) == 1
    assert results[0].name == "mock_tool"

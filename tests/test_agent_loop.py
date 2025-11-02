"""Agent Loop Tests.

Deliverable #6: Agent loop tests ✅
"""

import pytest

from chad_agents.graphs.graph_langgraph import execute_agent_loop


@pytest.mark.asyncio
async def test_agent_loop_happy_path():
    """Test agent loop executes successfully (stub)."""
    result = await execute_agent_loop(
        run_id="test",
        goal="Test goal",
        context={},
        autonomy_level="L2_ExecuteNotify",
        dry_run=False,
        max_steps=10
    )

    assert result["status"] == "completed_stub"
    assert "run_id" in result

"""Policy Guard Tests.

Deliverable #6: Policy guard tests ✅
"""

import pytest

from chad_agents.policies.autonomy import AutonomyLevel
from chad_agents.policies.policy_guard import policy_guard


@pytest.mark.asyncio
async def test_policy_guard_allows_valid_actor():
    """Test policy guard approves valid actor."""
    plan, violations, redactions, autonomy = await policy_guard(
        actor="test_actor",
        goal="Test goal",
        context={}
    )

    assert len(violations) == 0
    assert autonomy == AutonomyLevel.L2_ExecuteNotify


@pytest.mark.asyncio
async def test_policy_guard_returns_autonomy_level():
    """Test policy guard determines autonomy level."""
    _, _, _, autonomy = await policy_guard("test", "goal", {})
    assert isinstance(autonomy, AutonomyLevel)

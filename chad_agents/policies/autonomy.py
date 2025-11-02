"""Autonomy Levels Enum.

Deliverable #1: Autonomy L0-L3 ✅
Agent: agent-orchestration/context-manager
"""

from enum import Enum


class AutonomyLevel(str, Enum):
    """Autonomy levels for execution control."""

    L0_Ask = "L0_Ask"
    L1_Draft = "L1_Draft"
    L2_ExecuteNotify = "L2_ExecuteNotify"
    L3_ExecuteSilent = "L3_ExecuteSilent"

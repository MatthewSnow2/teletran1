"""Reflex Router - Pattern-based routing.

REFLEX_STRATEGY: rules (regex) | slm (small LLM)

Deliverable #3: Reflex rules module ✅
Agent: llm-application-dev/ai-engineer
"""

import re


def should_use_reflex(goal: str) -> bool:
    """
    Check if goal matches reflex patterns (no LLM needed).

    TODO: Implement regex pattern matching
    TODO: Add SLM strategy (small model classification)
    """
    trivial_patterns = [
        r"what time is it",
        r"ping (database|redis)",
        r"get run status",
    ]

    for pattern in trivial_patterns:
        if re.search(pattern, goal.lower()):
            return True

    return False


async def execute_reflex(goal: str, context: dict) -> dict:
    """Execute reflex action. TODO: Implement"""
    return {"result": "reflex_stub", "goal": goal}

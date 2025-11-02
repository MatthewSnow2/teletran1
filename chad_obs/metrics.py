"""
Prometheus Metrics Registration.

Custom metrics for Chad-Core business logic.

Agent: observability-monitoring/observability-engineer
Skill: observability-monitoring/skills/prometheus-configuration
Deliverable #4: Prometheus metrics ✅
"""

from prometheus_client import Counter, Histogram

# ============================================================================
# COUNTERS
# ============================================================================

tool_executions_total = Counter(
    "tool_executions_total",
    "Total tool executions",
    ["tool_name", "status"],  # success, failure
)

autonomy_level_total = Counter(
    "autonomy_level_total", "Autonomy level distribution", ["level"]  # L0, L1, L2, L3
)

policy_violations_total = Counter(
    "policy_violations_total", "Policy violations", ["rule", "severity"]
)

# ============================================================================
# HISTOGRAMS
# ============================================================================

tool_execution_duration = Histogram(
    "tool_execution_duration_seconds",
    "Tool execution duration",
    ["tool_name"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

agent_loop_duration = Histogram(
    "agent_loop_duration_seconds",
    "Complete agent loop duration",
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

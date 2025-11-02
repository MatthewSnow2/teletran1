"""
Prometheus Metrics Endpoint.

Exposes /metrics for Prometheus scraping.

Agent: observability-monitoring/observability-engineer
Skill: observability-monitoring/skills/prometheus-configuration
Deliverable #4: Prometheus /metrics endpoint ✅
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter()


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus metrics endpoint.

    Exposes metrics in Prometheus text format:
    - HTTP request counters (from OpenTelemetry instrumentation)
    - Tool execution counters (from chad_obs.metrics)
    - Autonomy level distribution (from chad_obs.metrics)
    - Error rates (from chad_obs.metrics)

    Example metrics:
    ```
    # HELP http_requests_total Total HTTP requests
    # TYPE http_requests_total counter
    http_requests_total{method="POST",endpoint="/act",status="202"} 42

    # HELP tool_executions_total Total tool executions
    # TYPE tool_executions_total counter
    tool_executions_total{tool="adapters_github.search_issues",status="success"} 15

    # HELP autonomy_level_total Autonomy level distribution
    # TYPE autonomy_level_total counter
    autonomy_level_total{level="L2_ExecuteNotify"} 30
    ```

    Returns:
        Prometheus text format metrics

    TODO: Register custom metrics in chad_obs.metrics
    TODO: Add business metrics (runs, steps, artifacts)
    """
    return generate_latest()

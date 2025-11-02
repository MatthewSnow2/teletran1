"""
FastAPI Routers.

Contains:
- act: POST /act (agent execution)
- runs: GET /runs, /runs/{id}, /runs/{id}/steps
- health: GET /healthz, /readyz
- metrics: GET /metrics

Agent: api-scaffolding/fastapi-pro
"""

__all__ = ["act", "runs", "health", "metrics"]

"""
Chad-Core FastAPI Application.

Main API server providing:
- /act: Agent execution endpoint
- /runs: Run viewer endpoints
- /healthz, /readyz: Health checks
- /metrics: Prometheus metrics

Agent: api-scaffolding/fastapi-pro
"""

__all__ = ["app"]

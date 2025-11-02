"""API Endpoint Tests.

Deliverable #6: Test /act, /healthz, /metrics ✅
Agent: tdd-workflows/tdd-orchestrator
"""

import pytest


def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Chad-Core API" in response.json()["name"]


def test_healthz_returns_200(client):
    """Test liveness probe."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readyz_returns_ready(client):
    """Test readiness probe."""
    response = client.get("/readyz")
    assert response.status_code == 200


def test_metrics_exposed(client):
    """Test Prometheus metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


def test_act_endpoint_validation(client):
    """Test /act validates request schema."""
    response = client.post("/act", json={})
    assert response.status_code == 422  # Validation error

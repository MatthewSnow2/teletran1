"""Pytest fixtures.

Deliverable #6: Test fixtures ✅
"""

import pytest
from fastapi.testclient import TestClient

from apps.core_api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_actor():
    """Mock authenticated actor."""
    return "test_actor"


@pytest.fixture
def mock_tools():
    """Mock tool registry."""
    from chad_tools.registry import ToolRegistry
    return ToolRegistry()

"""Pytest fixtures.

Deliverable #6: Test fixtures ✅
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from apps.core_api.main import app
from apps.core_api.auth import create_access_token


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


@pytest.fixture
def auth_token():
    """Generate valid auth token for testing."""
    return create_access_token("test_user", ["*"])


@pytest.fixture
def auth_headers(auth_token):
    """Generate auth headers with valid token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.setex = AsyncMock()
    mock.zremrangebyscore = AsyncMock()
    mock.zcard = AsyncMock(return_value=0)
    mock.zrange = AsyncMock(return_value=[])
    mock.zadd = AsyncMock()
    mock.expire = AsyncMock()
    return mock


@pytest.fixture(autouse=True)
def mock_redis_client(mock_redis):
    """Auto-mock Redis client for all tests."""
    with patch("apps.core_api.deps.get_redis_client", return_value=mock_redis):
        with patch("apps.core_api.auth.get_redis_client", return_value=mock_redis):
            yield mock_redis

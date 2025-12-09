"""Tests for LLM client implementations (Claude-only)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from chad_llm.client import (
    LLMClient,
    LLMError,
    LLMAuthError,
    LLMRateLimitError,
    LLMValidationError,
)
from chad_llm.anthropic_client import AnthropicClient


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_anthropic_api_key(monkeypatch):
    """Mock Anthropic API key in environment."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-12345")


@pytest.fixture
def anthropic_client(mock_anthropic_api_key):
    """Create Anthropic client with mocked API key."""
    return AnthropicClient(model="claude-sonnet-4-5-20250929")


# ============================================================================
# ANTHROPIC CLIENT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_anthropic_client_initialization(mock_anthropic_api_key):
    """Test Anthropic client initializes correctly."""
    client = AnthropicClient(model="claude-sonnet-4-5-20250929")

    assert client.model_name == "claude-sonnet-4-5-20250929"
    assert client.max_context_tokens == 250000
    assert client.api_key == "sk-ant-test-key-12345"


def test_anthropic_client_missing_api_key(monkeypatch):
    """Test Anthropic client raises error when API key missing."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(LLMAuthError, match="ANTHROPIC_API_KEY not found"):
        AnthropicClient()


@pytest.mark.asyncio
async def test_anthropic_generate_success(anthropic_client):
    """Test successful text generation."""
    mock_block = MagicMock()
    mock_block.text = "Generated response from Claude"

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    with patch.object(
        anthropic_client.client.messages,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_response

        result = await anthropic_client.generate(
            prompt="Test prompt",
            system_prompt="Test system",
            temperature=0.5,
        )

        assert result == "Generated response from Claude"
        mock_create.assert_called_once()

        # Verify call parameters
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-5-20250929"
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["system"] == "Test system"


@pytest.mark.asyncio
async def test_anthropic_generate_json_success(anthropic_client):
    """Test successful JSON generation."""
    json_response = '{"key": "value", "count": 42}'
    mock_block = MagicMock()
    mock_block.text = json_response

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    with patch.object(
        anthropic_client.client.messages,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_response

        schema = {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "count": {"type": "integer"},
            },
        }

        result = await anthropic_client.generate_json(
            prompt="Generate data",
            schema=schema,
        )

        assert result == {"key": "value", "count": 42}


@pytest.mark.asyncio
async def test_anthropic_generate_json_with_markdown(anthropic_client):
    """Test JSON generation with markdown code blocks."""
    json_response = "```json\n{\"key\": \"value\"}\n```"
    mock_block = MagicMock()
    mock_block.text = json_response

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    with patch.object(
        anthropic_client.client.messages,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_response

        schema = {"type": "object"}
        result = await anthropic_client.generate_json(
            prompt="Generate data",
            schema=schema,
        )

        assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_anthropic_count_tokens(anthropic_client):
    """Test token counting with API."""
    mock_response = MagicMock()
    mock_response.input_tokens = 42

    with patch.object(
        anthropic_client.client.messages,
        "count_tokens",
        new_callable=AsyncMock,
    ) as mock_count:
        mock_count.return_value = mock_response

        count = await anthropic_client.count_tokens("Test text")
        assert count == 42


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_anthropic_authentication_error(anthropic_client):
    """Test Anthropic authentication error handling."""
    from anthropic import AuthenticationError

    with patch.object(
        anthropic_client.client.messages,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.side_effect = AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body={"error": {"message": "Invalid API key"}},
        )

        with pytest.raises(LLMAuthError, match="Anthropic authentication failed"):
            await anthropic_client.generate(prompt="Test")


@pytest.mark.asyncio
async def test_anthropic_rate_limit_error(anthropic_client):
    """Test Anthropic rate limit error handling."""
    from anthropic import RateLimitError

    with patch.object(
        anthropic_client.client.messages,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429),
            body={"error": {"message": "Rate limit exceeded"}},
        )

        with pytest.raises(LLMRateLimitError, match="Anthropic rate limit exceeded"):
            await anthropic_client.generate(prompt="Test")


@pytest.mark.asyncio
async def test_anthropic_json_parse_error(anthropic_client):
    """Test JSON parse error handling."""
    mock_block = MagicMock()
    mock_block.text = "This is not valid JSON"

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    with patch.object(
        anthropic_client.client.messages,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_response

        with pytest.raises(LLMValidationError, match="Failed to parse JSON"):
            await anthropic_client.generate_json(
                prompt="Test",
                schema={"type": "object"},
            )

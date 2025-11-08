"""Tests for LLM client implementations."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from chad_llm.client import (
    LLMClient,
    LLMError,
    LLMAuthError,
    LLMRateLimitError,
    LLMValidationError,
)
from chad_llm.openai_client import OpenAIClient
from chad_llm.anthropic_client import AnthropicClient
from chad_llm.router import LLMRouter, TaskType


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_openai_api_key(monkeypatch):
    """Mock OpenAI API key in environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")


@pytest.fixture
def mock_anthropic_api_key(monkeypatch):
    """Mock Anthropic API key in environment."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-12345")


@pytest.fixture
def openai_client(mock_openai_api_key):
    """Create OpenAI client with mocked API key."""
    return OpenAIClient(model="gpt-5-2025-08-07")


@pytest.fixture
def anthropic_client(mock_anthropic_api_key):
    """Create Anthropic client with mocked API key."""
    return AnthropicClient(model="claude-sonnet-4-5-20250929")


@pytest.fixture
def llm_router(openai_client, anthropic_client):
    """Create LLM router with both clients."""
    return LLMRouter(
        openai_client=openai_client,
        anthropic_client=anthropic_client,
    )


# ============================================================================
# OPENAI CLIENT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_openai_client_initialization(mock_openai_api_key):
    """Test OpenAI client initializes correctly."""
    client = OpenAIClient(model="gpt-5-2025-08-07")

    assert client.model_name == "gpt-5-2025-08-07"
    assert client.max_context_tokens == 200000
    assert client.api_key == "sk-test-key-12345"


def test_openai_client_missing_api_key(monkeypatch):
    """Test OpenAI client raises error when API key missing."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMAuthError, match="OPENAI_API_KEY not found"):
        OpenAIClient()


@pytest.mark.asyncio
async def test_openai_generate_success(openai_client):
    """Test successful text generation."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Generated response text"))
    ]

    with patch.object(
        openai_client.client.chat.completions,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_response

        result = await openai_client.generate(
            prompt="Test prompt",
            system_prompt="Test system",
            temperature=0.5,
        )

        assert result == "Generated response text"
        mock_create.assert_called_once()

        # Verify call parameters
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-5-2025-08-07"
        assert call_kwargs["temperature"] == 0.5
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_openai_generate_json_success(openai_client):
    """Test successful JSON generation with function calling."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                function_call=MagicMock(arguments='{"key": "value", "count": 42}')
            )
        )
    ]

    with patch.object(
        openai_client.client.chat.completions,
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

        result = await openai_client.generate_json(
            prompt="Generate data",
            schema=schema,
        )

        assert result == {"key": "value", "count": 42}
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_openai_count_tokens(openai_client):
    """Test token counting approximation."""
    text = "This is a test prompt with about twenty tokens in it."
    count = await openai_client.count_tokens(text)

    # Should be approximately len(text) / 4
    expected = len(text) // 4
    assert count == expected


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
# LLM ROUTER TESTS
# ============================================================================


def test_router_initialization(openai_client, anthropic_client):
    """Test router initializes with clients."""
    router = LLMRouter(
        openai_client=openai_client,
        anthropic_client=anthropic_client,
    )

    assert router.chatgpt == openai_client
    assert router.claude == anthropic_client


def test_router_route_by_task_type(llm_router):
    """Test routing based on explicit task type."""
    # ChatGPT tasks
    assert llm_router.route(TaskType.USER_RESPONSE) == llm_router.chatgpt
    assert llm_router.route(TaskType.SUMMARIZATION) == llm_router.chatgpt
    assert llm_router.route(TaskType.FORMATTING) == llm_router.chatgpt

    # Claude tasks
    assert llm_router.route(TaskType.PLANNING) == llm_router.claude
    assert llm_router.route(TaskType.TECHNICAL_ANALYSIS) == llm_router.claude
    assert llm_router.route(TaskType.REFLECTION) == llm_router.claude


def test_router_route_from_prompt(llm_router):
    """Test routing based on prompt analysis."""
    # Claude prompts (technical/planning keywords)
    claude_prompts = [
        "Create a step-by-step plan for implementing this feature",
        "Analyze this code and evaluate its performance",
        "Reflect on the execution and decide next steps",
        "Provide technical reasoning for this architecture",
    ]

    for prompt in claude_prompts:
        client = llm_router.route_from_prompt(prompt)
        assert client == llm_router.claude

    # ChatGPT prompts (conversational/summarization keywords)
    chatgpt_prompts = [
        "Summarize this content for the user",
        "Explain this concept in a friendly way",
        "Format this data in a readable manner",
        "Describe the results to the user",
    ]

    for prompt in chatgpt_prompts:
        client = llm_router.route_from_prompt(prompt)
        assert client == llm_router.chatgpt


@pytest.mark.asyncio
async def test_router_generate_with_explicit_task(llm_router):
    """Test generate with explicit task type routing."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="ChatGPT response"))]

    with patch.object(
        llm_router.chatgpt.client.chat.completions,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_response

        result, model = await llm_router.generate(
            prompt="Test prompt",
            task_type=TaskType.USER_RESPONSE,
        )

        assert result == "ChatGPT response"
        assert model == "gpt-5-2025-08-07"


@pytest.mark.asyncio
async def test_router_generate_with_prompt_analysis(llm_router):
    """Test generate with automatic routing from prompt."""
    mock_block = MagicMock()
    mock_block.text = "Claude planning response"

    mock_response = MagicMock()
    mock_response.content = [mock_block]

    with patch.object(
        llm_router.claude.client.messages,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_response

        result, model = await llm_router.generate(
            prompt="Create a detailed plan for this workflow",
            # No explicit task_type - should route to Claude based on keywords
        )

        assert result == "Claude planning response"
        assert model == "claude-sonnet-4-5-20250929"


def test_router_get_client(llm_router):
    """Test getting client by task type."""
    chatgpt = llm_router.get_client(TaskType.SUMMARIZATION)
    assert chatgpt == llm_router.chatgpt

    claude = llm_router.get_client(TaskType.PLANNING)
    assert claude == llm_router.claude


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_openai_authentication_error(openai_client):
    """Test OpenAI authentication error handling."""
    from openai import AuthenticationError

    with patch.object(
        openai_client.client.chat.completions,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.side_effect = AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body={"error": {"message": "Invalid API key"}},
        )

        with pytest.raises(LLMAuthError, match="OpenAI authentication failed"):
            await openai_client.generate(prompt="Test")


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
async def test_openai_json_validation_error(openai_client):
    """Test JSON validation error when function call missing."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(function_call=None))]

    with patch.object(
        openai_client.client.chat.completions,
        "create",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_response

        with pytest.raises(LLMValidationError, match="did not return function call"):
            await openai_client.generate_json(
                prompt="Test",
                schema={"type": "object"},
            )


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

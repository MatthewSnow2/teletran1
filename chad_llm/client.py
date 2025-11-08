"""Base LLM client interface.

Defines the contract that all LLM clients must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        """Generate text completion from prompt.

        Args:
            prompt: User prompt or question
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters

        Returns:
            Generated text response

        Raises:
            LLMError: If generation fails
        """
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate structured JSON output matching schema.

        Args:
            prompt: User prompt requesting structured data
            schema: JSON schema defining expected output structure
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Additional model-specific parameters

        Returns:
            Parsed JSON object matching schema

        Raises:
            LLMError: If generation or parsing fails
            ValidationError: If output doesn't match schema
        """
        pass

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Count tokens in text using model's tokenizer.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier (e.g., 'gpt-4', 'claude-3-opus')."""
        pass

    @property
    @abstractmethod
    def max_context_tokens(self) -> int:
        """Return maximum context window size in tokens."""
        pass


class LLMError(Exception):
    """Base exception for LLM client errors."""

    pass


class LLMAuthError(LLMError):
    """Authentication error with LLM provider."""

    pass


class LLMRateLimitError(LLMError):
    """Rate limit exceeded."""

    pass


class LLMValidationError(LLMError):
    """Generated output failed validation."""

    pass

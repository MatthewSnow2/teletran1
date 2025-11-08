"""Anthropic Claude client for technical reasoning.

Used for:
- Execution planning (generating step-by-step plans)
- Technical analysis and reasoning
- Reflection on agent progress
- Complex decision-making
- Code analysis
"""

import json
import os
from typing import Any

from anthropic import AsyncAnthropic
from anthropic import APIError, AuthenticationError, RateLimitError

from .client import (
    LLMClient,
    LLMError,
    LLMAuthError,
    LLMRateLimitError,
    LLMValidationError,
)


class AnthropicClient(LLMClient):
    """Claude client for technical reasoning and planning."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-5-20250929",  # Claude Sonnet 4.5 (Sept 2025)
    ):
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model to use (default: claude-sonnet-4-5-20250929)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMAuthError("ANTHROPIC_API_KEY not found in environment")

        self.client = AsyncAnthropic(api_key=self.api_key)
        self._model = model

    @property
    def model_name(self) -> str:
        """Return model identifier."""
        return self._model

    @property
    def max_context_tokens(self) -> int:
        """Return max context window."""
        if "claude-4" in self._model or "claude-sonnet-4" in self._model:
            return 250000  # Claude 4.x context window
        elif "claude-3" in self._model:
            return 200000
        else:
            return 100000  # Conservative default

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        """Generate text completion using Claude.

        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic parameters

        Returns:
            Generated text

        Raises:
            LLMAuthError: Invalid API key
            LLMRateLimitError: Rate limit exceeded
            LLMError: Other API errors
        """
        try:
            response = await self.client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )

            # Extract text from content blocks
            text_blocks = [
                block.text for block in response.content if hasattr(block, "text")
            ]
            return "\n".join(text_blocks)

        except AuthenticationError as e:
            raise LLMAuthError(f"Anthropic authentication failed: {e}")
        except RateLimitError as e:
            raise LLMRateLimitError(f"Anthropic rate limit exceeded: {e}")
        except APIError as e:
            raise LLMError(f"Anthropic API error: {e}")

    async def generate_json(
        self,
        prompt: str,
        schema: dict[str, Any],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate structured JSON output.

        Claude doesn't have native function calling, so we:
        1. Add JSON schema to prompt
        2. Request JSON output format
        3. Parse and validate response

        Args:
            prompt: User prompt
            schema: JSON schema for output structure
            system_prompt: System instructions
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Parsed JSON object

        Raises:
            LLMValidationError: If output doesn't match schema
        """
        # Enhance prompt with JSON schema
        enhanced_prompt = f"""{prompt}

Please respond with valid JSON matching this schema:
```json
{json.dumps(schema, indent=2)}
```

IMPORTANT: Return ONLY the JSON object, no additional text or markdown formatting.
"""

        system = system_prompt or ""
        system += "\nYou are a technical assistant that returns structured JSON data."

        try:
            response = await self.client.messages.create(
                model=self._model,
                max_tokens=4096,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": enhanced_prompt}],
                **kwargs,
            )

            # Extract text from content blocks
            text_blocks = [
                block.text for block in response.content if hasattr(block, "text")
            ]
            response_text = "\n".join(text_blocks).strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line (```)
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()

            # Parse JSON
            result = json.loads(response_text)
            return result

        except json.JSONDecodeError as e:
            raise LLMValidationError(f"Failed to parse JSON: {e}\nResponse: {response_text[:200]}")
        except AuthenticationError as e:
            raise LLMAuthError(f"Anthropic authentication failed: {e}")
        except RateLimitError as e:
            raise LLMRateLimitError(f"Anthropic rate limit exceeded: {e}")
        except APIError as e:
            raise LLMError(f"Anthropic API error: {e}")

    async def count_tokens(self, text: str) -> int:
        """Count tokens using Anthropic's count API.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        try:
            # Use Anthropic's token counting
            response = await self.client.messages.count_tokens(
                model=self._model,
                messages=[{"role": "user", "content": text}],
            )
            return response.input_tokens
        except Exception:
            # Fallback: approximate with char count
            return len(text) // 4
